# Auto-Claude 프로젝트 완전 가이드

> **이 문서를 읽으면 다른 AI 에이전트가 이 프로젝트를 즉시 이해하고 작업할 수 있다.**
> 마지막 업데이트: 2026-02-09 | 버전: 2.7.6-beta.2

---

## 1. 한 줄 요약

**Auto-Claude** = 사용자가 목표를 말하면 AI 에이전트가 자율적으로 기획 → 구현 → QA → 머지까지 해주는 **데스크톱 앱(Electron) + CLI(Python)** 모노레포.

---

## 2. 프로젝트 구조

```
C:\DK\AC247\AC247\
├── Auto-Claude/                    # 메인 모노레포
│   ├── apps/
│   │   ├── backend/                # Python 백엔드 (CLI + 에이전트 로직)
│   │   │   ├── core/               # 핵심: agent_registry, pipeline, client, worktree
│   │   │   ├── agents/             # planner, coder, session management
│   │   │   ├── qa/                 # reviewer, fixer, loop, validators/
│   │   │   ├── mcts/               # Monte Carlo Tree Search
│   │   │   ├── spec/               # Spec 생성 파이프라인
│   │   │   ├── cli/                # CLI 명령어 (build, spec, workspace, qa)
│   │   │   ├── services/           # daemon, recovery, spec_factory
│   │   │   ├── security/           # 커맨드 보안 (allowlist, hooks)
│   │   │   ├── project/            # 프로젝트 분석, framework 감지
│   │   │   ├── prompts/            # 에이전트 시스템 프롬프트 (63개 .md)
│   │   │   ├── runners/            # 진입점: spec_runner, daemon_runner
│   │   │   ├── merge/              # semantic merge
│   │   │   ├── context/            # 태스크 컨텍스트 빌딩
│   │   │   ├── integrations/       # graphiti, linear
│   │   │   └── custom_agents/      # 커스텀 에이전트 플러그인
│   │   └── frontend/               # Electron 데스크톱 UI
│   │       └── src/
│   │           ├── main/           # Electron 메인 프로세스
│   │           ├── renderer/       # React UI (Zustand, Tailwind)
│   │           ├── preload/        # IPC 브릿지
│   │           └── shared/         # 공유 타입, i18n, 상수
│   ├── tests/                      # pytest 테스트
│   ├── docs/                       # 문서
│   ├── CLAUDE.md                   # Claude용 가이드 (필독)
│   └── package.json                # npm workspace
├── .auto-claude/                   # 프로젝트별 데이터 (gitignored)
│   ├── specs/                      # 태스크 사양들
│   ├── worktrees/                  # git worktree 격리 작업공간
│   └── daemon_status.json          # 데몬 상태 (UI 폴링)
└── model.md                        # 모델 설정 레퍼런스
```

---

## 3. 핵심 파이프라인 (반드시 이해)

### 3.1 전체 흐름

```
사용자 → spec_runner.py --task "..." → [Spec 생성 파이프라인]
                                           ↓
                              .auto-claude/specs/001-xxx/
                              ├── spec.md
                              ├── requirements.json
                              └── implementation_plan.json (status: "queue")
                                           ↓
                              daemon_runner.py (감시 중)
                                           ↓
                              run.py --spec 001 --auto-merge
                                           ↓
                    ┌──────────────────────────────────────────┐
                    │  Planner → Coder → QA Reviewer           │
                    │     ↑          ↓        ↓ (실패시)       │
                    │     └── QA Fixer ←──────┘                │
                    │           (max 3회 반복)                   │
                    └──────────────────────────────────────────┘
                                           ↓
                              Auto-merge → master 반영 → 완료
```

### 3.2 세 가지 실행 모드

| 모드 | 명령어 | 설명 |
|------|--------|------|
| **Standard** | `--task "..."` | 단일 기능 구현 (planner→coder→QA→merge) |
| **Design** | `--task "..." --task-type design` | 큰 프로젝트를 자식 태스크들로 분해 |
| **MCTS** | `--task "..." --task-type mcts` | 여러 접근법을 병렬 탐색 후 최선 선택 |

### 3.3 상태 흐름 (implementation_plan.json)

```
queue → planning → coding → qa_review ──→ human_review → done
                                ↓ (실패)
                           qa_fixing → qa_review (반복)
```

---

## 4. 명령어 총정리

### 4.1 Spec 생성 (가장 많이 쓰는 명령어)

```bash
cd Auto-Claude/apps/backend

# 기본: spec 생성 + 즉시 빌드
python runners/spec_runner.py --task "로그인 기능 추가" --project-dir C:\path\to\project

# spec만 생성 (데몬이 나중에 빌드) — UI Kanban에 표시됨
python runners/spec_runner.py --task "로그인 기능 추가" --project-dir C:\path\to\project --no-build

# 자동 머지까지 풀오토
python runners/spec_runner.py --task "로그인 기능 추가" --project-dir C:\path\to\project --auto-merge

# 디자인 태스크 (대형 프로젝트 분해)
python runners/spec_runner.py --task "SNS 앱 전체" --project-dir C:\path --task-type design --no-build

# MCTS (여러 접근법 탐색)
python runners/spec_runner.py --task "검색 최적화" --project-dir C:\path --task-type mcts --no-build

# 대화형 모드
python runners/spec_runner.py --interactive --project-dir C:\path
```

### 4.2 데몬 (24/7 자동 실행)

```bash
# 데몬 시작 — specs/ 감시 + 자동 실행 + UI 상태 동기화
python runners/daemon_runner.py --project-dir C:\path\to\project \
  --status-file C:\path\to\project\.auto-claude\daemon_status.json
```

### 4.3 수동 빌드/QA

```bash
# 특정 spec 빌드
python run.py --spec 001

# QA만 실행
python run.py --spec 001 --qa

# 머지만 실행
python run.py --spec 001 --merge

# spec 목록 보기
python run.py --list

# 모델 오버라이드
python run.py --spec 001 --model haiku
```

### 4.4 프론트엔드 (Electron)

```bash
cd Auto-Claude/apps/frontend

npm run dev          # 개발 모드 (HMR)
npm start            # 프로덕션
npm run build        # 빌드
npm run test         # Vitest
npm run lint         # Biome
npm run typecheck    # TypeScript 체크
npm run package      # 배포 패키징
```

### 4.5 테스트

```bash
# 백엔드 (pytest)
cd Auto-Claude && python -m pytest tests/ -v

# 프론트엔드 (Vitest)
cd Auto-Claude/apps/frontend && npm test

# E2E (Playwright)
cd Auto-Claude/apps/frontend && npm run test:e2e
```

### 4.6 설치

```bash
# 전체 설치
npm run install:all

# 또는 개별
cd apps/backend && uv venv && uv pip install -r requirements.txt
cd apps/frontend && npm install
```

---

## 5. 아키텍처 핵심 개념

### 5.1 Unified Agent Registry (단일 진실 소스)

`core/agent_registry.py` — **54개 에이전트** 전부 여기서 정의.

```python
from core.agent_registry import AgentRegistry

reg = AgentRegistry.instance()
coder = reg.get("coder")
# → security_level="full", tool_profile="CODING", tools=["Read","Write","Edit","Bash",...]
```

**AgentDefinition 필드:**
- **Tools**: `tools`, `mcp_servers`, `auto_claude_tools`, `thinking_default`
- **Security**: `security_level` (deny/readonly/allowlist/full), `extra_allow`, `extra_deny`
- **Execution**: `system_prompt`, `use_claude_cli`, `prompt_template`
- **Tool Profile**: MINIMAL / READONLY / CODING / QA / FULL

**에이전트 카테고리 (54개):**

| 카테고리 | 에이전트들 |
|----------|-----------|
| **Build** | planner, coder |
| **QA** | qa_reviewer, qa_fixer |
| **Spec** | spec_gatherer, spec_researcher, spec_writer, spec_critic, ... (8개) |
| **Design** | design, architecture, research, review, ... (5개) |
| **MCTS** | mcts_idea_generator, mcts_improver, mcts_debugger, mcts_lesson_extractor |
| **Impl** | impl, frontend, backend, database, api, test, integration (7개) |
| **PR** | pr_reviewer, pr_orchestrator, pr_followup, ... (5개) |
| **Utility** | docs, insights, merge_resolver, commit_message, ... (10개) |
| **Analysis** | batch_planning, batch_analysis, roadmap_discovery, ... (6개) |

### 5.2 Declarative Pipeline Engine

`core/pipeline.py` + `core/pipelines.py` — DAG 기반 실행 엔진.

```python
from core.pipelines import get_pipeline
pipeline = get_pipeline("default")  # "design", "qa_only", "mcts"
```

| 파이프라인 | 스테이지 | 용도 |
|-----------|---------|------|
| **default** | build → qa → merge | 일반 태스크 |
| **design** | decompose | 대형 프로젝트 분해 |
| **qa_only** | qa | QA만 재실행 |
| **mcts** | mcts_search → merge_best | 멀티패스 탐색 |

### 5.3 4계층 보안 아키텍처

```
Layer 1: Agent Exec Policy   (core/exec_policy.py)
   ↓  에이전트별 Bash 권한: DENY → READONLY → ALLOWLIST → FULL
Layer 2: Security Hook        (security/hooks.py)
   ↓  프로젝트 기반 커맨드 화이트리스트
Layer 3: SDK Permissions      (core/client.py)
   ↓  파일 작업을 project_dir로 제한
Layer 4: OS Sandbox           (Claude Agent SDK)
      OS 수준 격리
```

### 5.4 QA Validators (자동 검증)

```
qa/validators/
├── build_validator.py    → 빌드/린트/테스트 (project_index.json에서 명령어 읽음)
├── browser_validator.py  → Playwright 브라우저 자동화 (스크린샷)
├── api_validator.py      → API 엔드포인트 테스트
└── db_validator.py       → DB 스키마 검증
```

**실행 순서:**
1. Build 검증 (순차 — 반드시 통과)
2. Browser + API + DB 검증 (병렬)
3. 결과를 QA Reviewer에게 증거로 전달

### 5.5 Git Worktree 격리

모든 빌드 작업은 **독립 worktree**에서 수행 → master 안전.

```
.auto-claude/worktrees/tasks/
├── 001-feature-x/     ← 독립 브랜치: auto-claude/001-feature-x
└── 002-feature-y/     ← 독립 브랜치: auto-claude/002-feature-y
```

**중요:** 유효한 worktree는 `.git` **파일**(디렉토리 아님)이 있어야 함.
→ `<repo>/.git/worktrees/<name>/`을 가리킴.

### 5.6 MCTS (멀티패스 탐색)

```
INITIALIZE → tree 로드/생성
EXPAND     → idea_generator가 N개 아이디어 생성 → 자식 spec 생성
SIMULATE   → 데몬이 자식 실행 (planner→coder→QA)
EVALUATE   → 점수: build(0.3) + test(0.3) + lint(0.1) + QA(0.3)
BACKPROP   → 점수 트리 역전파
LESSONS    → 성공/실패 비교, 교훈 추출
SELECT     → UCB1로 다음 노드 선택
REPEAT     → 예산 소진 또는 수렴까지
FINALIZE   → 최고 브랜치 머지
```

저장: `spec_dir/mcts_tree.json`, `spec_dir/mcts_lessons.json`

---

## 6. 핵심 파일 레퍼런스

### 6.1 백엔드 진입점

| 파일 | 역할 |
|------|------|
| `runners/spec_runner.py` | Spec 생성 CLI |
| `runners/daemon_runner.py` | 24/7 데몬 |
| `run.py` | 빌드 실행 CLI |
| `cli/build_commands.py` | 빌드 명령어 로직 |
| `cli/main.py` | CLI 파서 + 라우팅 |

### 6.2 코어 프레임워크

| 파일 | 역할 |
|------|------|
| `core/agent_registry.py` | 54개 에이전트 정의 (단일 진실 소스) |
| `core/pipeline.py` | DAG 파이프라인 엔진 |
| `core/pipelines.py` | 빌트인 파이프라인 정의 |
| `core/client.py` | Claude SDK 클라이언트 팩토리 |
| `core/worktree.py` | Git worktree 관리 |
| `core/exec_policy.py` | 에이전트별 Bash 보안 |
| `core/tool_policy.py` | 툴 그룹/프로필 |
| `core/task_event.py` | 이벤트 로깅 (`__TASK_EVENT__`) |
| `core/schema.py` | JSON 스키마 검증 |
| `phase_config.py` | Phase별 모델/thinking 설정 |

### 6.3 에이전트 + QA

| 파일 | 역할 |
|------|------|
| `agents/planner.py` | 구현 계획 생성 |
| `agents/coder.py` | 서브태스크 구현 |
| `qa/loop.py` | QA 루프 (review → fix → 반복) |
| `qa/reviewer.py` | Spec 준수 검증 |
| `qa/fixer.py` | 이슈 수정 |
| `qa/validator_orchestrator.py` | 검증기 선택 + 실행 |

### 6.4 Spec 파이프라인

| 파일 | 역할 |
|------|------|
| `spec/pipeline/orchestrator.py` | Spec 생성 오케스트레이션 |
| `spec/pipeline/agent_runner.py` | 에이전트 실행 + SDK 예외 처리 |
| `spec/phases/` | 각 Phase 구현 |

### 6.5 데몬

| 파일 | 역할 |
|------|------|
| `services/task_daemon/__init__.py` | 데몬 코어: 태스크 라이프사이클 |
| `services/task_daemon/executor.py` | 태스크 커맨드 빌더 |
| `services/task_daemon/ws_server.py` | WebSocket 서버 (18800-18809) |

### 6.6 프론트엔드 핵심

| 파일 | 역할 |
|------|------|
| `frontend/src/main/index.ts` | Electron 앱 라이프사이클 |
| `frontend/src/main/project-store.ts` | 프로젝트 + 태스크 영속성 |
| `frontend/src/main/daemon-status-watcher.ts` | 데몬↔UI 브릿지 |
| `frontend/src/shared/state-machines/task-machine.ts` | XState 태스크 상태머신 |
| `frontend/src/shared/constants/ipc.ts` | IPC 채널 정의 (55+) |

---

## 7. Spec 디렉토리 구조

각 태스크는 `.auto-claude/specs/XXX-name/` 폴더:

```
.auto-claude/specs/001-login-feature/
├── spec.md                    # 고수준 설명
├── requirements.json          # 메타데이터 (priority, complexity)
├── implementation_plan.json   # 상세 계획 (phases, subtasks, status)
├── task_metadata.json         # 모델/프로필 설정
├── context.json               # 코드베이스 컨텍스트
├── qa_report.md               # QA 검증 결과
├── QA_FIX_REQUEST.md          # QA가 발견한 이슈
├── events.jsonl               # 이벤트 로그 (append-only)
└── screenshots/               # 브라우저 검증 스크린샷
```

**implementation_plan.json 핵심 필드:**
```json
{
  "status": "queue|planning|coding|qa_review|human_review|done",
  "xstateState": "backlog|planning|coding|qa_review|human_review|done",
  "executionPhase": "backlog|planning|coding|qa|done",
  "planStatus": "queue|...",
  "taskType": "impl|design|mcts",
  "parentTask": "001-parent-name",
  "phases": [{ "subtasks": [{ "title": "...", "status": "pending|in_progress|completed" }] }]
}
```

---

## 8. 모델 설정

### 우선순위 (높은 것이 이김)

```
CLI --model > per-spec task_metadata.json > customPhaseModels > agent profile > AUTO_BUILD_MODEL env > hardcoded
```

### Agent Profile 프리셋

| 프리셋 | 모델 | Thinking |
|--------|------|----------|
| **auto** | 전부 opus | spec=ultrathink, planning=high, coding=low, qa=low |
| **complex** | 전부 opus | 전부 ultrathink |
| **balanced** | 전부 sonnet | 전부 medium |
| **quick** | 전부 haiku | 전부 low |

### 설정 파일 위치

| 파일 | 용도 |
|------|------|
| `%APPDATA%/auto-claude-ui/settings.json` | 앱 전역 (defaultModel, selectedAgentProfile) |
| `apps/backend/.env` | 환경변수 (AUTO_BUILD_MODEL, ANTHROPIC_DEFAULT_*) |
| `apps/backend/phase_config.py` | 하드코딩 기본값 |
| `.auto-claude/specs/XXX/task_metadata.json` | 태스크별 오버라이드 |

### 현재 모델 ID

```
opus:   claude-opus-4-6
sonnet: claude-sonnet-4-5-20250929
haiku:  claude-haiku-4-5-20251001
```

---

## 9. 프론트엔드 기술 스택

| 기술 | 버전 | 용도 |
|------|------|------|
| Electron | 40 | 데스크톱 프레임워크 |
| React | 19 | UI |
| TypeScript | 5.9 (strict) | 타입 안전 |
| Zustand | 5 | 상태 관리 (24+ 스토어) |
| Tailwind CSS | v4 | 스타일링 |
| Radix UI | - | 컴포넌트 |
| xterm.js | 6 | 터미널 에뮬레이터 |
| Vite | 7 | 빌드 |
| Biome | 2 | 린터 |
| react-i18next | 16.5 | 국제화 (en/fr) |

### i18n 규칙 (필수)
```tsx
// ✅ 올바름
const { t } = useTranslation('settings');
<span>{t('general.title')}</span>

// ❌ 절대 하지 마
<span>General Settings</span>
```

### Path Alias
```
@/*          → src/renderer/*
@shared/*    → src/shared/*
@features/*  → src/renderer/features/*
@components/* → src/renderer/shared/components/*
```

---

## 10. 절대 규칙 (NEVER FORGET)

### 10.1 Spec 관련

- **NEVER 수동으로 spec 파일 생성** (spec.md, requirements.json, implementation_plan.json)
- **반드시 `spec_runner.py`로 생성** — 자동 파이프라인 (gatherer → researcher → writer → critic)
- spec_runner 완료 **전에** implementation_plan.json 편집하지 마라 (덮어씌워짐)

### 10.2 SDK 관련

- **Claude Agent SDK만 사용** — `anthropic.Anthropic()` 직접 사용 금지
- **항상** `create_client()` from `core.client` 사용
- `ClaudeSDKClient`에 `process_single_turn()` 없음 — `query()` + `receive_response()` 사용

### 10.3 Worktree 관련

- Worktree 안에서 **git merge/push/rebase/checkout main 금지** — git add/commit/status/diff만 허용
- 유효한 worktree = `.git` **파일**(디렉토리 아님)이 존재
- merge는 반드시 `merge_worktree()` (`--no-ff`) 경유

### 10.4 Windows 관련

- `subprocess.run()` 사용 (`os.execv()` 금지 — Electron 연결 끊김)
- 항상 `encoding='utf-8'` 지정
- 파일 교체 시 재시도 로직 (UI가 읽는 중이면 lock 걸림)
- `json.dump(..., ensure_ascii=False)` — 한국어 깨짐 방지

### 10.5 데몬/UI 관련

- 장시간 Phase는 반드시 `print()` heartbeat 출력 (stdout 없으면 데몬이 "stuck"으로 판단, 600초 후 kill)
- Worktree에서 작업 시 메인 spec dir로 주기적 sync 필요 (QA 이벤트가 UI에 안 보임)
- 데몬 2개 동시 실행 금지 — 항상 기존 데몬 종료 확인 후 시작

### 10.6 프론트엔드 관련

- 모든 UI 텍스트는 `react-i18next` 사용 (하드코딩 금지)
- `process.platform` 직접 사용 금지 → `platform/` 모듈 사용
- PR은 `develop` 브랜치 대상 (`main` 아님)

---

## 11. 치명적 버그 패턴 (학습된 교훈)

> 이 패턴들은 실제 디버깅에서 발견된 것. 같은 실수 반복하지 마라.

### #1 Stale spec_dir after rename
`orchestrator.py`가 `001-pending` → `001-name`으로 리네임 후, PhaseExecutor/SpecValidator/TaskLogger가 옛 경로를 참조.
→ **모든 참조를 업데이트해야 함**

### #2 File-exists-but-success=False
SDK 예외가 나도 에이전트가 이미 파일을 만들었을 수 있음.
→ **파일 존재 여부를 먼저 체크**, success 플래그 무시

### #3 build_validator.py 명령어 소스
`command_registry/`는 보안 allowlist임 (명령어 getter 아님).
→ 빌드 명령어는 `project_index.json`에서 읽음 (framework_analyzer.py가 작성)

### #4 Browser validator 인자 타입
`extract_dev_server_info()`는 dict를 받고 string을 반환함.
→ Path 객체 넘기면 AttributeError

### #5 Worktree 감지 실패
`.git` 디렉토리가 있어도 **파일**이 아니면 가짜 worktree.
→ `.git` FILE 존재 + `_worktree_is_registered()` 확인 필수

### #6 Agent가 worktree에서 git merge 실행
Fast-forward merge로 orchestrator의 `--no-ff` 우회 → 코드 유실.
→ exec_policy_hook으로 worktree 내 merge/push 차단

### #7 flutter analyze 블로킹
`flutter analyze`가 warning에도 실패 → browser validator 진행 안 됨.
→ `flutter analyze --no-fatal-infos --no-fatal-warnings` 사용

### #8 Daemon stdout heartbeat 없음
Validator + QA가 10분+ 걸리는데 stdout이 없으면 데몬이 kill.
→ 장시간 작업은 `print()` heartbeat 필수

---

## 12. SDK 클라이언트 사용법

```python
from core.client import create_client
from phase_config import get_phase_model, get_phase_thinking_budget

# 모델/thinking 해석
model = get_phase_model(spec_dir, "coding", cli_model=None)
thinking = get_phase_thinking_budget(spec_dir, "coding", cli_thinking=None)

# 클라이언트 생성
client = create_client(
    project_dir=project_dir,
    spec_dir=spec_dir,
    model=model,
    agent_type="coder",            # planner | coder | qa_reviewer | qa_fixer
    max_thinking_tokens=thinking,
)

# 세션 실행
async with client:
    status, response = await run_agent_session(client, prompt, spec_dir)
```

**참고 파일:** `agents/planner.py`, `agents/coder.py`, `qa/reviewer.py`, `qa/fixer.py`

---

## 13. 커스텀 에이전트 추가

### 방법 1: agent_registry.py에 직접 추가

`BUILTIN_AGENTS` dict에 한 항목 추가 → 모든 shim 자동 반영.

### 방법 2: 플러그인 (custom_agents/)

```json
// custom_agents/config.json
{
  "agents": {
    "my_agent": {
      "prompt_file": "my_agent.md",
      "description": "...",
      "tools": ["Read", "Write", "Bash", "Grep"],
      "mcp_servers": ["context7"],
      "thinking_default": "medium"
    }
  }
}
```

프롬프트 파일: `custom_agents/prompts/my_agent.md`

---

## 14. 데몬 통신 아키텍처

```
Python 백엔드:
  daemon_runner.py
    → daemon_status.json (파일 기반)
    → ws_server.py (WebSocket, port 18800-18809)

Electron 프론트엔드:
  daemon-status-watcher.ts
    → chokidar (100ms 안정화) + WebSocket 자동 연결
    → processFile() → IPC → renderer
    → Kanban 카드 자동 이동
```

**이벤트 체인:**
```
에이전트 stdout → __TASK_EVENT__:{json}
  → task_event.py → events.jsonl 기록
  → implementation_plan.json status 업데이트
  → daemon_status.json 업데이트
  → DaemonStatusWatcher 감지
  → IPC → UI 업데이트
```

---

## 15. 프로젝트별 검증 시스템

### 자동 감지 (framework_analyzer.py)

| 프레임워크 | 린트 | 테스트 |
|-----------|------|--------|
| **Python** | ruff/flake8/mypy | pytest |
| **Node.js** | npm run lint / eslint / tsc | npm run test |
| **Go** | go vet | go test |
| **Rust** | cargo clippy | cargo test |
| **Flutter** | flutter analyze --no-fatal-infos --no-fatal-warnings | flutter test |

### Runtime 검증 문서 (QA 에이전트에게 자동 주입)

| 문서 | 트리거 | 전략 |
|------|--------|------|
| `flutter_validation.md` | `is_flutter` | Marionette MCP + Playwright |
| `electron_validation.md` | `is_electron` | Electron MCP (screenshot, click) |
| `playwright_browser.md` | `is_web_frontend` | Playwright 브라우저 자동화 |
| `tauri_validation.md` | `is_tauri` | Playwright + cargo check |
| `react_native_validation.md` | `is_react_native` | Expo web + Playwright |
| `database_validation.md` | `has_database` | 마이그레이션/스키마 체크 |
| `api_validation.md` | `has_api` | API 엔드포인트 테스트 |

---

## 16. 환경 변수 (.env)

```bash
# 필수
CLAUDE_CODE_OAUTH_TOKEN=...           # claude setup-token으로 설정

# 모델 (선택)
AUTO_BUILD_MODEL=claude-opus-4-6
ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-6
ANTHROPIC_DEFAULT_SONNET_MODEL=claude-sonnet-4-5-20250929
ANTHROPIC_DEFAULT_HAIKU_MODEL=claude-haiku-4-5-20251001

# 통합 (선택)
LINEAR_API_KEY=...
GITLAB_TOKEN=...
GRAPHITI_ENABLED=true
OPENAI_API_KEY=...                    # Graphiti LLM용

# 디버그 (선택)
DEBUG=true
DEBUG_LEVEL=1
AUTO_CLAUDE_HEADLESS_BROWSER=true     # CI용 헤드리스
MARIONETTE_MCP_DISABLED=true          # Flutter Marionette 비활성화
AUTO_CLAUDE_MAX_CHILD_DEPTH=2         # 최대 태스크 깊이
```

---

## 17. 실전 워크플로우 예시

### 예시 1: Flutter 앱에 새 기능 추가

```bash
cd Auto-Claude/apps/backend

# 1. Spec 생성 + 데몬 대기
python runners/spec_runner.py \
  --task "할일 목록 화면에 카테고리 필터 추가" \
  --project-dir C:\projects\my-flutter-app \
  --no-build

# 2. 데몬 시작 (이미 실행 중이면 스킵)
python runners/daemon_runner.py \
  --project-dir C:\projects\my-flutter-app \
  --status-file C:\projects\my-flutter-app\.auto-claude\daemon_status.json

# 3. UI에서 Kanban 보드 확인 → 자동 진행
# 4. human_review 상태가 되면 코드 확인 후 완료 처리
```

### 예시 2: 대형 프로젝트 설계 분해

```bash
# 디자인 태스크 → 자식 태스크들로 자동 분해
python runners/spec_runner.py \
  --task "소셜 미디어 앱: 인증, 피드, 메시징, 프로필, 알림" \
  --project-dir C:\projects\social-app \
  --task-type design \
  --no-build

# 결과: 5개+ 자식 태스크가 Kanban에 생성됨
# 데몬이 의존성 순서대로 자동 실행
```

### 예시 3: 최적 알고리즘 탐색 (MCTS)

```bash
# 여러 접근법을 병렬 탐색
python runners/spec_runner.py \
  --task "검색 자동완성을 트라이, 퍼지매칭, ElasticSearch 중 최적 구현" \
  --project-dir C:\projects\search-app \
  --task-type mcts \
  --no-build

# 결과: 3-5개 브랜치가 생성, 각각 빌드+테스트
# 점수 기반으로 최선 선택 → 자동 머지
```

---

## 18. 의존성

### Python (3.10+)
- `claude-agent-sdk>=0.1.25` — Anthropic Agent SDK
- `pydantic>=2.0.0` — 구조화된 출력
- `watchdog>=4.0.0` — 파일 감시 (데몬)
- `websockets>=12.0` — WebSocket 서버
- `playwright>=1.40.0` — 브라우저 자동화
- `python-dotenv>=1.0.0` — 환경 설정

### Node.js (24.0+)
- `electron 40` — 데스크톱
- `react 19` + `react-dom 19` — UI
- `zustand 5` — 상태 관리
- `tailwindcss 4` — 스타일링
- `xterm 6` — 터미널
- `vite 7` — 빌드

---

## 19. 요약 체크리스트

새 AI 에이전트가 이 프로젝트에서 작업하기 전:

- [ ] CLAUDE.md 읽음 (필수)
- [ ] 파이프라인 흐름 이해 (spec_runner → daemon → planner → coder → QA → merge)
- [ ] 절대 규칙 숙지 (§10)
- [ ] 치명적 버그 패턴 숙지 (§11)
- [ ] SDK 사용법 이해 (§12)
- [ ] 모델 설정 우선순위 이해 (§8)
- [ ] spec 파일을 수동으로 만들지 않음
- [ ] worktree에서 git merge 하지 않음
- [ ] 모든 UI 텍스트에 i18n 사용
- [ ] Windows 호환성 주의 (encoding, subprocess, file locks)
