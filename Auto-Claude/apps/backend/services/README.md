# Services Module - 24/7 Background Task Daemon

Background services for autonomous task orchestration. Run Auto-Claude without UI for 24/7 headless operation.

> **Quick Start**: [DESIGN_TASK_TEMPLATE.md](DESIGN_TASK_TEMPLATE.md) - Design task로 대형 프로젝트 분해하기

## Overview

The services module provides:
- **Task Daemon**: 24/7 background task manager with auto-recovery
- **Service Orchestrator**: Coordinates multiple services
- **Recovery Manager**: Handles stuck task recovery

## Task Daemon

The `TaskDaemon` class watches the `.auto-claude/specs/` folder and automatically executes tasks.

> **CRITICAL: 프로젝트당 Daemon은 반드시 1개만 실행하세요.**
> 동일 프로젝트에 Daemon 2개 이상 실행하면 task 충돌, 파일 잠금(Permission denied), worktree 경합 등 예측 불가능한 문제가 발생합니다.
> Daemon을 재시작하려면 기존 프로세스를 반드시 먼저 종료해야 합니다.

### Features

| Feature | Description |
|---------|-------------|
| **Parallel Execution** | Run multiple tasks concurrently (`--max-concurrent`) |
| **Priority Queue** | Critical tasks execute first |
| **Task Dependencies** | Task B waits for Task A (`depends_on`) |
| **Hierarchical Tasks** | Design tasks spawn child implementation tasks |
| **Git Worktree Isolation** | Parallel tasks run in separate worktrees |
| **Auto-Recovery** | Stuck tasks automatically restart |
| **Claude CLI Integration** | Plan mode for design, headless for 24/7 |

### Quick Start

```bash
cd Auto-Claude/apps/backend

# ⚠️ 실행 전: 기존 daemon이 돌고 있는지 반드시 확인
# Windows:
tasklist | findstr python
# Linux/Mac:
ps aux | grep daemon_runner

# Basic: Sequential execution
python runners/daemon_runner.py --project-dir "C:\path\to\project"

# Parallel: 3 concurrent tasks with worktree isolation (권장)
python runners/daemon_runner.py --project-dir "..." \
    --max-concurrent 3 \
    --use-worktrees

# Full 24/7 Setup
python runners/daemon_runner.py --project-dir "..." \
    --max-concurrent 3 \
    --use-worktrees \
    --status-file daemon_status.json \
    --log-file daemon.log
```

### CLI Options

| Option | Default | Description |
|--------|---------|-------------|
| `--project-dir` | required | Project directory with `.auto-claude/specs/` |
| `--max-concurrent` | 1 | Maximum parallel tasks |
| `--use-worktrees` | false | Git worktree isolation for parallel tasks |
| `--headless` | true | Skip permission prompts (24/7 mode) |
| `--stuck-timeout` | 600 | Seconds before task is stuck |
| `--check-interval` | 60 | Seconds between stuck checks |
| `--max-recovery` | 3 | Recovery attempts before giving up |
| `--status-file` | none | JSON status file for monitoring |
| `--log-file` | none | Log file path |

### Task Types and Execution Modes

**Design/Analysis Tasks** (run.py pipeline with MCP tools):
| Task Type | Description | Execution |
|-----------|-------------|-----------|
| `design` | Project/module design, creates child tasks | run.py (MCP: `create_batch_child_specs`) |
| `architecture` | Architecture analysis and design | run.py (MCP tools) |

**Plan Mode Tasks** (Claude CLI `--permission-mode plan`):
| Task Type | Description | Execution |
|-----------|-------------|-----------|
| `planning` | Implementation planning | Claude CLI plan mode |
| `research` | Codebase analysis and investigation | Claude CLI plan mode |
| `review` | Code review | Claude CLI plan mode |

**Implementation Tasks** (run.py Auto-Claude pipeline):
| Task Type | Description | MCP Servers |
|-----------|-------------|-------------|
| `impl` | General implementation | default |
| `frontend` | Frontend development | puppeteer |
| `backend` | Backend development | context7 |
| `database` | Database work | context7 |
| `api` | API development | default |
| `test` | Test execution | default |
| `integration` | Integration tasks | default |
| `docs` | Documentation | default |

**Verification & Error-Check Tasks** (run.py, auto-queued after impl):
| Task Type | Description | MCP Servers |
|-----------|-------------|-------------|
| `verify` | 구현 검증 (코드 리뷰 + 빌드 + 테스트 + 런타임) | context7, auto-claude, browser (동적) |
| `error_check` | verify가 발견한 에러를 최소 변경으로 수정 | context7, graphiti, auto-claude |

### Task Priority Levels

| Priority | Value | Use Case |
|----------|-------|----------|
| CRITICAL | 0 | Design, architecture tasks |
| HIGH | 1 | Core module implementation |
| NORMAL | 2 | Standard implementation |
| LOW | 3 | Documentation, cleanup |

### Implementation Plan JSON Schema

Tasks are configured via `implementation_plan.json`:

```json
{
  "status": "queue",
  "taskType": "impl",
  "priority": 2,
  "dependsOn": ["001-design"],
  "parentTask": "001-design",
  "xstateState": "backlog"
}
```

### Large Project Workflow

```
1. Design Task (priority: 0, type: design)
   └── Plan mode exploration
   └── Creates child tasks for each module

2. Module Tasks (priority: 1-2, type: impl)
   └── Run in parallel with worktree isolation
   └── Each task has dependencies

3. Integration Task (priority: 2, type: integration)
   └── Waits for all module tasks
   └── Merges and validates
```

### Auto-Verify Pipeline (impl 완료 후 자동 검증)

impl 계열 task가 성공적으로 완료되면 daemon이 자동으로 verify task를 생성합니다.

```
impl task 완료 (성공)
  │
  ▼
daemon._auto_queue_verify()
  → verify spec 생성 (verify-{spec_id}, priority: HIGH, dependsOn: [spec_id])
  │
  ▼
verify agent 실행
  → Phase 1: 코드 리뷰 (로직 에러, 보안, edge case)
  → Phase 2: 빌드/정적 분석 (프로젝트 타입 자동 감지)
  → Phase 3: 테스트 실행
  → Phase 4: 런타임 검증 (웹: 브라우저, Flutter: flutter build, Unity: N/A)
  │
  ├── 에러 없음 → PASS → verify_report.md 작성 → 완료
  │
  └── 에러 발견 → FAIL
        → create_batch_child_specs(type="error_check", priority=HIGH)
        → verify_report.md에 에러 상세 기록
        │
        ▼
      error_check agent 실행
        → verify_report.md 읽고 에러 파악
        → 최소한의 코드 변경으로 수정
        → 수정 후 빌드/테스트 재실행
        │
        ▼
      error_check 성공 완료
        → daemon이 부모 impl의 re-verify 자동 큐잉
        → verify-{spec_id}-2 생성 (최대 MAX_VERIFY_ATTEMPTS=3회)
```

**무한 루프 방지:**
- `IMPL_TASK_TYPES = {"impl", "frontend", "backend", "database", "api"}` — verify/error_check 제외
- verify spec ID에 attempt 번호 부여: `verify-{id}`, `verify-{id}-2`, `verify-{id}-3`
- `MAX_VERIFY_ATTEMPTS = 3` 초과 시 중단

**프로젝트 타입별 검증 방식:**

| 프로젝트 | 빌드 검증 | 테스트 | 런타임 검증 |
|----------|----------|--------|------------|
| Flutter | `flutter analyze` | `flutter test` | `flutter build apk --debug` |
| React/Vue | `npm run typecheck` + `npm run build` | `npm test` | 브라우저 MCP (Puppeteer/Playwright) |
| Python | `ruff check` + `mypy` | `pytest` | 서버 시작 + API 체크 |
| Unity | `dotnet build` | Unity Editor CLI | N/A (headless 불가) |
| Go | `go build` + `go vet` | `go test` | 바이너리 실행 |

verify agent는 `project_index.json`의 capabilities를 통해 프로젝트 타입을 자동 감지합니다.

### Programmatic Usage

```python
from services import TaskDaemon, create_daemon

# Create daemon
daemon = TaskDaemon(
    project_dir=Path("C:/path/to/project"),
    max_concurrent_tasks=4,
    use_worktrees=True,
    headless_mode=True,
    on_task_complete=lambda spec_id, success: print(f"{spec_id}: {success}"),
)

# Start (blocking)
daemon.start()

# Or get status
status = daemon.get_status()
print(f"Running: {status['stats']['running']}")
print(f"Queued: {status['stats']['queued']}")
```

### Background Execution

**Linux/Mac:**
```bash
nohup python runners/daemon_runner.py --project-dir "..." > daemon.log 2>&1 &
```

**Windows (PowerShell):**
```powershell
Start-Process -NoNewWindow python "runners/daemon_runner.py --project-dir ..."
```

**Windows Service (NSSM):**
```bash
nssm install AutoClaudeDaemon "python.exe" "runners/daemon_runner.py --project-dir ..."
nssm start AutoClaudeDaemon
```

### Monitoring

Check daemon status via status file:
```bash
# Enable status file
python runners/daemon_runner.py --project-dir "..." --status-file status.json

# Monitor
watch cat status.json
```

Status file contains:
- Running tasks with PIDs
- Queued tasks with priorities
- Completed task count
- Configuration settings

## Architecture

```
services/
├── __init__.py              # Public API (re-exports all)
├── task_daemon/             # Modular daemon package
│   ├── __init__.py         # TaskDaemon class (slim orchestration)
│   ├── types.py            # Enums, constants, data classes
│   ├── watcher.py          # File system watching (SpecsWatcher)
│   ├── executor.py         # Task execution (run.py, Claude CLI)
│   └── state.py            # State persistence (StateManager)
├── spec_factory.py          # Programmatic spec creation
├── orchestrator.py          # Service coordination
├── recovery.py              # Recovery utilities
└── context.py               # Service context

runners/
└── daemon_runner.py         # CLI entry point

prompts/
└── design_architect.md      # Design agent prompt
```

### Module Responsibilities

| Module | Responsibility | Lines |
|--------|----------------|-------|
| `types.py` | Enums, constants, data classes | ~200 |
| `watcher.py` | File system watching, debouncing | ~100 |
| `executor.py` | Command building, process spawning | ~200 |
| `state.py` | State persistence, recovery counts | ~150 |
| `__init__.py` | Orchestration, lifecycle | ~400 |

### Benefits of Modular Structure

1. **Single Responsibility**: Each module handles one concern
2. **Easy Testing**: Test individual modules in isolation
3. **Easy Extension**: Add new executors without touching other code
4. **Maintainability**: Smaller files are easier to understand
5. **Reusability**: StateManager can be used elsewhere

## Spec Factory (For Large Architecture Projects)

The `SpecFactory` enables design agents to create multiple child specs programmatically:

```python
from services import SpecFactory

factory = SpecFactory(project_dir)

# Single child spec
spec_dir = await factory.create_child_spec(
    parent_spec_id="001-design",
    task_description="Implement user auth module",
    priority=1,
    depends_on=["002-database"],
)

# Batch creation (recommended)
specs = await factory.create_batch_specs(
    parent_spec_id="001-design",
    specs=[
        {"task": "Database schema", "priority": 0},
        {"task": "Backend API", "priority": 1, "depends_on": ["002-database"]},
        {"task": "Frontend UI", "priority": 1, "depends_on": ["002-database"]},
        {"task": "Integration tests", "priority": 2, "depends_on": ["003-backend", "004-frontend"]},
    ]
)
```

### Agent Tools

Design agents have access to these tools via `subtask.py`:

| Tool | Description |
|------|-------------|
| `create_child_spec` | Create single child spec |
| `create_batch_child_specs` | Create multiple specs at once |
| `update_subtask_status` | Update subtask status |

### Large Project Workflow

```
1. User creates "design" task
   └── taskType: "design", priority: 0

2. Design Agent analyzes project
   └── Uses plan mode (read-only exploration)

3. Design Agent calls create_batch_child_specs
   └── Creates N child specs with dependencies

4. Task Daemon picks up child specs
   └── Runs them in parallel (respecting dependencies)

5. All child specs complete
   └── Integration task runs (if configured)
```

## Agent Invocation Flow (How Tasks Are Automatically Executed)

**핵심: Daemon이 specs 폴더를 감시하고, status가 "queue"인 task를 자동으로 실행합니다.**

### 전체 흐름도

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          TaskDaemon.start()                              │
│                               │                                          │
│                               ▼                                          │
│                     ┌─────────────────────┐                              │
│                     │  specs 폴더 감시     │  ← watchdog (file watcher)   │
│                     │  (SpecsWatcher)     │                              │
│                     └─────────────────────┘                              │
│                               │                                          │
│                               ▼                                          │
│               implementation_plan.json 변경 감지                          │
│                               │                                          │
│                               ▼                                          │
│              ┌────────────────────────────────┐                           │
│              │  status == "queue"?            │                           │
│              │  + AGENT_REGISTRY 조회         │                           │
│              │  (task_type → AgentConfig)     │                           │
│              └────────────────────────────────┘                           │
│                    │              │              │                        │
│     ┌──────────────┘              │              └──────────────┐         │
│     ▼                             ▼                             ▼         │
│ ┌──────────────────┐  ┌──────────────────────┐  ┌──────────────────┐     │
│ │ Design/Arch      │  │ Plan Mode Tasks      │  │ Implementation   │     │
│ │ (design, arch)   │  │ (research, review,   │  │ (impl, frontend, │     │
│ │                  │  │  planning)           │  │  backend, etc.)  │     │
│ └──────────────────┘  └──────────────────────┘  └──────────────────┘     │
│          │                        │                        │              │
│          ▼                        ▼                        ▼              │
│ ┌──────────────────┐  ┌──────────────────────┐  ┌──────────────────┐     │
│ │ run.py 호출      │  │ Claude CLI 직접      │  │ run.py 호출      │     │
│ │ (Auto-Claude)    │  │ --permission-mode    │  │ (Auto-Claude     │     │
│ │                  │  │ plan                 │  │  agent pipeline) │     │
│ │ create_client()  │  │                      │  │                  │     │
│ │ → MCP server 연결│  │ Read-only 탐색       │  │ planner → coder  │     │
│ │ → MCP tool 사용  │  │ 코드 변경 불가       │  │ → QA → fixer     │     │
│ └──────────────────┘  └──────────────────────┘  └──────────────────┘     │
│          │                        │                        │              │
│          ▼                        ▼                        ▼              │
│  create_batch_child_specs   분석/리뷰 결과            코드 구현 완료      │
│  → 자식 task 자동 생성       작성                                         │
│  → Daemon이 감지 & 실행                                                   │
└──────────────────────────────────────────────────────────────────────────┘
```

### 자동 실행 조건

Task가 자동으로 실행되려면:

| 조건 | 값 | 설명 |
|------|-----|------|
| `status` | `"queue"` 또는 `"backlog"` | 대기 상태여야 함 |
| `dependsOn` | `[]` 또는 모든 의존성 완료 | 선행 task 완료 필요 |
| recovery_count | < max_recovery (기본 3) | 실패 횟수 초과 안됨 |

**자동 실행 안되는 status:**
- `in_progress` - 이미 실행 중
- `human_review` - 사람 검토 대기
- `done`, `completed`, `merged` - 이미 완료
- `error`, `failed` - 실패 상태

### Task Type별 실행 방식

#### Design/Architecture Tasks (run.py + MCP tools)

| Task Type | 실행 방식 | 특징 |
|-----------|----------|------|
| `design` | run.py → create_client() → MCP | `create_batch_child_specs` tool로 자식 task 생성 |
| `architecture` | run.py → create_client() → MCP | 구조 설계 + MCP tool 접근 |

**Design Agent가 할 수 있는 것:**
- 코드 읽기/분석
- `create_batch_child_specs` tool로 자식 task 생성
- MCP server (context7, graphiti 등) 사용
- 전문 프롬프트 (prompt_template) 적용

#### Plan Mode Tasks (Claude CLI)

```python
# types.py에서 정의
PLAN_MODE_TASK_TYPES = {"design", "architecture", "planning", "research", "review"}
```

| Task Type | 실행 방식 | 특징 |
|-----------|----------|------|
| `planning` | Claude CLI `--permission-mode plan` | 구현 계획 수립 |
| `research` | Claude CLI `--permission-mode plan` | 코드베이스 조사 |
| `review` | Claude CLI `--permission-mode plan` | 코드 리뷰 |

**Plan Mode에서 할 수 있는 것:**
- 코드 읽기 (Read)
- 파일 검색 (Glob, Grep)
- 분석 및 계획 작성

**Plan Mode에서 못하는 것:**
- 파일 쓰기/수정
- 명령어 실행 (npm, python 등)
- MCP tool 사용 (auto-claude MCP server 미연결)

#### Implementation Tasks (run.py pipeline)

```python
# 나머지 모든 task type
IMPL_TASK_TYPES = {"impl", "frontend", "backend", "database", "api", "test", "integration", "docs"}
```

| Task Type | 실행 방식 | MCP Servers |
|-----------|----------|-------------|
| `impl` | run.py → Auto-Claude pipeline | default |
| `frontend` | run.py → Auto-Claude pipeline | puppeteer |
| `backend` | run.py → Auto-Claude pipeline | context7 |
| `database` | run.py → Auto-Claude pipeline | context7 |
| `api` | run.py → Auto-Claude pipeline | default |
| `test` | run.py → Auto-Claude pipeline | default |

**Implementation Mode에서:**
- 기존 Auto-Claude agent pipeline 사용
- `planner.py` → `coder.py` → `qa/reviewer.py` → `qa/fixer.py`
- 코드 읽기/쓰기 모두 가능
- 모든 MCP tool 사용 가능 (context7, graphiti 등)

### 코드 레벨 설명

#### executor.py - AGENT_REGISTRY 기반 실행 방식 결정

```python
# executor.py - build_command()
def build_command(self, spec_id, work_dir, execution_mode, task_type="default"):
    agent_config = get_agent_config(task_type)  # AGENT_REGISTRY 조회

    # 1. Agent에 custom script 있으면 → 해당 스크립트 실행
    if agent_config.script:
        return self._build_custom_agent_command(...)

    # 2. Agent가 Claude CLI 강제 → Claude CLI (prompt_template 적용)
    if agent_config.use_claude_cli:
        cmd = self._build_claude_cli_command(..., agent_config)
        return cmd, work_dir

    # 3. Plan mode → Claude CLI
    if execution_mode == ExecutionMode.PLAN:
        cmd = self._build_claude_cli_command(..., agent_config)
        return cmd, work_dir

    # 4. 기본값 → run.py (Auto-Claude pipeline + MCP tools)
    cmd = self._build_run_py_command(...)
    return cmd, self.auto_claude_dir
```

#### __init__.py - task_type 전달

```python
# __init__.py - _start_task()
execution_mode = self._executor.get_execution_mode(queued_task.task_type)
cmd, cwd = self._executor.build_command(
    spec_id, self.project_dir, execution_mode,
    task_type=queued_task.task_type,  # AGENT_REGISTRY 활용
)
```

#### AGENT_REGISTRY - Task Type별 Agent 설정

```python
AGENT_REGISTRY = {
    # Design/Architecture → run.py (MCP tool 접근 필요)
    "design": AgentConfig(use_claude_cli=False, system_prompt="design_architect.md"),
    "architecture": AgentConfig(use_claude_cli=False),

    # Research/Review → Claude CLI plan mode
    "research": AgentConfig(use_claude_cli=True, execution_mode="plan"),
    "review": AgentConfig(use_claude_cli=True, execution_mode="plan"),

    # Implementation → run.py (Auto-Claude pipeline)
    "frontend": AgentConfig(mcp_servers=["puppeteer"]),
    "backend": AgentConfig(mcp_servers=["context7"]),
    "database": AgentConfig(mcp_servers=["context7"]),
    "impl": AgentConfig(),  # default
}
```

### 예시: 대형 프로젝트 (쇼핑몰)

```
.auto-claude/specs/
├── 001-design/               # taskType: design → run.py (MCP tools)
│   └── implementation_plan.json    → create_batch_child_specs로 자식 생성
│
├── 002-database-schema/      # taskType: database, dependsOn: []
│   └── implementation_plan.json    → run.py (Auto-Claude pipeline)
│
├── 003-backend-api/          # taskType: backend, dependsOn: [002]
│   └── implementation_plan.json    → 002 완료 후 실행
│
├── 004-frontend-ui/          # taskType: frontend, dependsOn: [002]
│   └── implementation_plan.json    → 002 완료 후 실행 (003과 병렬)
│
└── 005-integration-tests/    # taskType: integration, dependsOn: [003, 004]
    └── implementation_plan.json    → 003, 004 모두 완료 후 실행
```

## Claude CLI Integration

The daemon leverages Claude CLI features:

| Feature | Usage |
|---------|-------|
| Plan Mode | `--permission-mode plan` for research/review tasks |
| Headless | `--dangerously-skip-permissions` for 24/7 |
| Git Worktrees | Complete isolation for parallel tasks |
| Fan-out | Distribute work across Claude sessions |

## Agent + MCP 연결 아키텍처

### 핵심 설계 결정

Design/Architecture task는 Claude CLI가 아닌 **run.py**를 통해 실행됩니다:

- **run.py 경로**: `create_client()` → auto-claude MCP server 연결 → `create_batch_child_specs` tool 사용 가능
- **Claude CLI 경로**: MCP server 미연결 → `create_batch_child_specs` tool 사용 불가

따라서 자식 task를 생성해야 하는 design/architecture agent는 반드시 run.py를 사용해야 합니다.

### AgentConfig 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `script` | `str \| None` | 커스텀 agent 스크립트 경로 |
| `extra_args` | `list[str]` | 스크립트 추가 인자 |
| `use_claude_cli` | `bool` | Claude CLI 사용 여부 |
| `prompt_template` | `str \| None` | 전문 프롬프트 (변수: `{spec_id}`, `{task}`, `{spec_content}`) |
| `system_prompt` | `str \| None` | 시스템 프롬프트 파일 |
| `execution_mode` | `str \| None` | 실행 모드 오버라이드 |
| `mcp_servers` | `list[str]` | 향후 확장용 MCP 서버 목록 |
| `pre_hook` | `Callable \| None` | 실행 전 훅 |
| `post_hook` | `Callable \| None` | 실행 후 훅 |

### 대형 프로젝트 전체 흐름

```
사용자: "쇼핑몰 앱 만들어줘"
    │
    ▼
Spec 생성 (status: queue, taskType: design, priority: 0)
    │
    ▼
TaskDaemon 감지 → _start_task(task_type="design")
    │
    ├── AGENT_REGISTRY["design"] → AgentConfig(use_claude_cli=False)
    ├── run.py 사용 → create_client(agent_type="planner")
    └── auto-claude MCP server 연결 → create_batch_child_specs 사용 가능
    │
    ▼
Design Agent가 프로젝트 분석 후 child spec 생성:
    ├── 002-database-schema    (priority:0, type:database, depends:[])
    ├── 003-backend-api        (priority:1, type:backend,  depends:[002])
    ├── 004-frontend-ui        (priority:1, type:frontend, depends:[002])
    └── 005-integration-tests  (priority:2, type:integration, depends:[003,004])
    │
    ▼
Daemon이 새 spec 감지 → Queue에 추가 (priority 순)
    │
    ▼
Scheduler 실행:
    T0:  002-database (deps 없음) → START
    T1:  002 완료 → 003 & 004 deps 충족
    T1:  003-backend + 004-frontend → START (병렬)
    T2:  003, 004 완료 → 005 deps 충족
    T2:  005-integration → START
    T3:  005 완료 → ALL COMPLETE
```

## CLI → UI 실시간 연동 (DaemonStatusBridge)

외부 터미널에서 `run.py`를 직접 실행할 때도 Electron UI에 실시간으로 진행 상황을 표시합니다.

### 문제

- `run.py`를 외부에서 실행하면 `daemon_status.json`을 안 씀
- UI의 `DaemonStatusWatcher`가 이 파일을 감시해서 IPC 전송하는 구조
- 파일이 없으면 UI에 아무것도 안 보임

### 해결 구조

```
run.py (외부 터미널)
  │
  └── DaemonStatusBridge (core/daemon_status_bridge.py)
        │
        ├── start()  → daemon_status.json 생성 (빌드 시작)
        ├── update() → running_tasks 업데이트 (subtask 진행)
        ├── complete() → stats.completed +1 (빌드 성공)
        └── close()  → 정리 (finally 블록에서 호출)
        │
        ▼
  daemon_status.json (프로젝트 루트)
        │
        ▼
  Electron Main Process
        │
        └── DaemonStatusWatcher (daemon-status-watcher.ts)
              │
              ├── chokidar: 파일 변경 감지 → processFile()
              ├── setInterval 5s: 주기적 재전송 (forceRefresh 복구용)
              └── processFile() → TASK_STATUS_CHANGE IPC 전송
              │
              ▼
        Renderer (Zustand task store)
              │
              └── Kanban 카드 In Progress로 이동
```

### daemon_status.json 포맷

TaskDaemon.get_status()와 동일한 포맷:

```json
{
  "project_dir": "C:\\path\\to\\project",
  "running": true,
  "started_at": "2026-02-04T15:16:25+00:00",
  "config": { "max_concurrent_tasks": 1, "headless_mode": true },
  "running_tasks": {
    "001-spec-id": {
      "spec_id": "001-spec-id",
      "spec_dir": "C:\\...\\specs\\001-spec-id",
      "status": "in_progress",
      "is_running": true,
      "started_at": "...",
      "last_update": "...",
      "task_type": "impl",
      "current_subtask": "subtask-1-1",
      "phase": "coding",
      "session": 1
    }
  },
  "stats": { "running": 1, "queued": 0, "completed": 0 }
}
```

### 수정된 파일

| 파일 | 역할 |
|------|------|
| `core/daemon_status_bridge.py` | **신규** - daemon_status.json 작성 브릿지 |
| `agents/coder.py` | bridge 연동 (start/update/complete/close) |
| `cli/build_commands.py` | original_project_dir 전달 (worktree 모드 지원) |
| `frontend/.../daemon-status-watcher.ts` | 다중 프로젝트 + 주기적 재전송 |
| `frontend/.../agent-events-handlers.ts` | 5초 폴링으로 daemon_status.json 감지 |

### 핵심 설계 결정

1. **이중 쓰기 방지**: bridge.start() 시 기존 daemon_status.json의 PID 체크. 살아있는 daemon이 있으면 merge (덮어쓰지 않음)
2. **Windows 호환**: `os.kill(pid, 0)` 대신 `ctypes.windll.kernel32.OpenProcess` 사용 (Windows에서 os.kill은 프로세스를 종료시킴)
3. **Atomic write**: `.tmp` → `os.replace()` 패턴으로 partial read 방지
4. **try/finally 보장**: coder.py에서 bridge.close()는 항상 실행 (예외/인터럽트 무관)
5. **주기적 재전송**: DaemonStatusWatcher가 5초마다 processFile() 호출 → UI forceRefresh로 스토어가 클리어되어도 자동 복구
6. **다중 프로젝트**: ProjectWatcher Map으로 여러 프로젝트 동시 감시

### coder.py 연동 지점

| 시점 | 메서드 | 설명 |
|------|--------|------|
| 빌드 시작 | `bridge.start()` | daemon_status.json 생성 |
| subtask 진행 | `bridge.update(subtask_id, phase, session)` | running_tasks 업데이트 |
| 빌드 성공 | `bridge.complete()` | stats.completed +1, running_tasks에서 제거 |
| 항상 (finally) | `bridge.close()` | running: false로 정리 |

### 테스트 방법

```bash
# Terminal 1: UI 실행
cd Auto-Claude/apps/frontend && npm run dev

# Terminal 2: CLI 빌드 (UI가 부팅된 후)
cd Auto-Claude/apps/backend
.venv\Scripts\python.exe run.py --project-dir "C:\path\to\project" --spec 001 --force --auto-continue --max-iterations 3

# 기대 결과:
# 1. daemon_status.json 자동 생성
# 2. UI Kanban에서 카드가 In Progress로 이동 (5초 이내)
# 3. subtask 진행 시 daemon_status.json 업데이트
# 4. 빌드 완료 시 카드가 Human Review로 이동
```

## Custom MCP Server Configuration

프로젝트별로 커스텀 MCP 서버를 추가하여 agent에게 외부 도구를 제공할 수 있습니다.

**[MCP 공식 JSON 스키마](https://modelcontextprotocol.io/quickstart/user)**를 따르며, Auto-Claude 확장 필드를 추가로 지원합니다.

> **참고 문서:**
> - [MCP 공식 문서](https://modelcontextprotocol.io/quickstart/user)
> - [Claude Agent SDK - MCP 가이드](https://platform.claude.com/docs/en/agent-sdk/mcp)
> - [MCP Server 목록](https://github.com/modelcontextprotocol/servers)

### 설정 방법

#### 방법 1: `.auto-claude/.env` 파일 (권장)

```bash
# .auto-claude/.env
CUSTOM_MCP_SERVERS=[{"id":"github","command":"npx","args":["-y","@modelcontextprotocol/server-github"],"env":{"GITHUB_TOKEN":"${GITHUB_TOKEN}"},"tools":["list_issues"],"agents":["planner","coder"]}]
```

#### 방법 2: `.mcp.json` 파일 (MCP 표준)

프로젝트 루트에 `.mcp.json` 파일 생성 (Claude Agent SDK가 자동 로드):

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "supabase": {
      "type": "http",
      "url": "https://xxx.supabase.co/mcp",
      "headers": {
        "Authorization": "Bearer ${SUPABASE_KEY}"
      }
    }
  }
}
```

> **참고:** `.mcp.json`은 MCP 표준 필드만 지원합니다. Auto-Claude 확장 필드(`tools`, `agents`)를 사용하려면 `.auto-claude/.env` 방식을 사용하세요.

### MCP 서버 타입

#### 1. stdio 서버 (로컬 프로세스)

로컬에서 실행되는 MCP 서버. stdin/stdout으로 통신합니다.

```json
{
  "id": "github",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": { "GITHUB_TOKEN": "${GITHUB_TOKEN}" },
  "tools": ["list_issues", "create_issue"],
  "agents": ["planner", "coder"]
}
```

| 필드 | 출처 | 필수 | 설명 |
|------|------|------|------|
| `id` | Auto-Claude | 필수 | 서버 식별자 |
| `command` | MCP 표준 | 필수 | 실행 명령어 |
| `args` | MCP 표준 | 선택 | 명령어 인자 배열 |
| `env` | MCP 표준 | 선택 | 환경변수 (`${VAR}` 확장) |

#### 2. HTTP 서버 (원격)

HTTP 프로토콜로 통신하는 원격 MCP 서버.

```json
{
  "id": "supabase",
  "type": "http",
  "url": "https://xxx.supabase.co/mcp",
  "headers": { "Authorization": "Bearer ${SUPABASE_KEY}" },
  "tools": "*"
}
```

#### 3. SSE 서버 (원격 스트리밍)

Server-Sent Events로 스트리밍하는 원격 MCP 서버.

```json
{
  "id": "slack",
  "type": "sse",
  "url": "https://api.slack.com/mcp/sse",
  "headers": { "Authorization": "Bearer ${SLACK_TOKEN}" },
  "tools": ["post_message"],
  "agents": ["qa_reviewer"]
}
```

| 필드 | 출처 | 필수 | 설명 |
|------|------|------|------|
| `id` | Auto-Claude | 필수 | 서버 식별자 |
| `type` | MCP 표준 | 필수 | `"http"` 또는 `"sse"` |
| `url` | MCP 표준 | 필수 | 서버 URL |
| `headers` | MCP 표준 | 선택 | HTTP 요청 헤더 |

### Auto-Claude 확장 필드

MCP 표준 필드 외에 Auto-Claude 전용 확장 필드를 지원합니다:

| 필드 | 설명 | 예시 |
|------|------|------|
| `tools` | 허용할 tool 목록 | `"*"` (전체) 또는 `["tool1", "tool2"]` |
| `agents` | 허용할 agent 타입 | `"*"` (전체) 또는 `["planner", "coder"]` |
| `name` | UI 표시 이름 | `"GitHub Integration"` |
| `description` | 설명 | `"GitHub issue management"` |

### 예시: 전체 설정

```bash
# .auto-claude/.env

# GitHub (stdio) - planner, coder만 사용
# Supabase (http) - 모든 agent 사용
# Slack (sse) - qa_reviewer만 사용
CUSTOM_MCP_SERVERS=[{"id":"github","command":"npx","args":["-y","@modelcontextprotocol/server-github"],"env":{"GITHUB_TOKEN":"${GITHUB_TOKEN}"},"tools":["list_issues","search_issues","create_issue"],"agents":["planner","coder"],"name":"GitHub","description":"GitHub issue management"},{"id":"supabase","type":"http","url":"https://xxx.supabase.co/mcp","headers":{"Authorization":"Bearer ${SUPABASE_KEY}"},"tools":"*","agents":"*"},{"id":"slack","type":"sse","url":"https://api.slack.com/mcp/sse","headers":{"Authorization":"Bearer ${SLACK_TOKEN}"},"tools":["post_message"],"agents":["qa_reviewer"]}]
```

### Agent별 MCP 오버라이드

특정 agent에게만 MCP 추가/제거:

```bash
# .auto-claude/.env

# planner에게 GitHub MCP 추가
AGENT_MCP_planner_ADD=github

# coder에서 context7 제거
AGENT_MCP_coder_REMOVE=context7

# qa_reviewer에게 slack MCP 추가
AGENT_MCP_qa_reviewer_ADD=slack
```

### 보안 제한

**허용되는 stdio 명령어:**
- `npx`, `npm`, `node`, `python`, `python3`, `uv`, `uvx`

**차단되는 명령어:**
- `bash`, `sh`, `cmd`, `powershell`, `pwsh`, `zsh`, `fish`

**차단되는 플래그:**
- `--eval`, `-e`, `-c`, `--exec`, `-m`, `-p`, `--print`
- `--experimental-loader`, `--require`, `-r`

### Tool 이름 규칙

MCP tool 이름은 `mcp__{server_id}__{tool_name}` 형식:

```
mcp__github__list_issues     # github 서버의 list_issues tool
mcp__supabase__query         # supabase 서버의 query tool
mcp__slack__post_message     # slack 서버의 post_message tool
```

와일드카드 권한: `mcp__github__*` (해당 서버의 모든 tool 허용)

### 인증 설정

#### 환경변수 확장

`${VAR}` 문법으로 환경변수를 런타임에 확장합니다:

```json
{
  "env": { "GITHUB_TOKEN": "${GITHUB_TOKEN}" },
  "headers": { "Authorization": "Bearer ${API_KEY}" }
}
```

#### OAuth 인증

OAuth 플로우가 필요한 서버는 애플리케이션에서 토큰을 획득한 후 `headers`에 전달:

```json
{
  "type": "http",
  "url": "https://api.example.com/mcp",
  "headers": { "Authorization": "Bearer ${OAUTH_ACCESS_TOKEN}" }
}
```

### 실행 확인

Daemon 시작 시 커스텀 MCP 서버가 로드되면 콘솔에 표시됩니다:

```
Security settings: /path/to/project/.claude_settings.json
   - Sandbox enabled (OS-level bash isolation)
   - Filesystem restricted to: /path/to/project
   - MCP servers: context7 (documentation), auto-claude (coder tools), GitHub (GitHub issue management), Supabase (custom)
```

### 디버깅

MCP 서버 연결 실패 시:

1. **init 메시지 확인**: 연결 상태가 `system` init 메시지에 포함됨
2. **로그 확인**: `~/.claude/logs/mcp-server-{name}.log` (서버별 stderr)
3. **수동 테스트**: 명령어 직접 실행하여 에러 확인

```bash
# GitHub MCP 서버 수동 테스트
npx -y @modelcontextprotocol/server-github
```

### 인기 MCP 서버

| 서버 | 설명 | 패키지 |
|------|------|--------|
| GitHub | Issue, PR, 리포지토리 관리 | `@modelcontextprotocol/server-github` |
| Postgres | PostgreSQL 쿼리 | `@modelcontextprotocol/server-postgres` |
| Filesystem | 파일 시스템 접근 | `@modelcontextprotocol/server-filesystem` |
| Brave Search | 웹 검색 | `@modelcontextprotocol/server-brave-search` |
| Puppeteer | 브라우저 자동화 | `puppeteer-mcp-server` |

> **전체 목록**: [github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)

## Related Files

- `runners/daemon_runner.py` - CLI entry point
- `core/task_event.py` - Task event emission
- `core/daemon_status_bridge.py` - CLI → UI 실시간 연동 브릿지
- `core/client.py` - MCP 서버 설정 및 커스텀 서버 로드
- `agents/tools_pkg/models.py` - Agent별 MCP 서버 매핑
- `agents/tools_pkg/permissions.py` - Tool 권한 필터링
- `requirements.txt` - `watchdog>=4.0.0` dependency
