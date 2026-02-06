# DaemonStatusBridge: CLI → UI 실시간 연동 시스템

## 전체 개요

외부 터미널에서 `run.py`를 직접 실행할 때 Electron UI에 실시간으로 빌드 진행 상황을 표시하는 시스템.

### 핵심 문제

`run.py`를 외부에서 실행하면 `daemon_status.json`을 안 써서, UI의 `DaemonStatusWatcher`가 감시를 시작하지 않음 → Kanban 카드가 Backlog에서 안 움직임.

### 해결 구조

```
run.py (외부 터미널)
  │
  └── DaemonStatusBridge (Python)
        │
        ├── start()    → daemon_status.json 생성
        ├── update()   → subtask/phase/session 업데이트
        ├── complete() → stats.completed +1
        └── close()    → finally 블록에서 항상 호출
        │
        ▼
  daemon_status.json (프로젝트 루트)
        │
        ▼
  Electron Main Process
        │
        ├── agent-events-handlers.ts: 5초 폴링으로 daemon_status.json 감지
        │
        └── DaemonStatusWatcher (TypeScript)
              │
              ├── chokidar: 파일 변경 감지 → processFile()
              ├── setInterval 5s: 주기적 재전송 (forceRefresh 복구용)
              │
              └── processFile()
                    ├── TASK_STATUS_CHANGE → Kanban 카드 In Progress 이동
                    └── TASK_EXECUTION_PROGRESS → phase badge 표시 (planning, coding 등)
              │
              ▼
        Renderer (Zustand task store) → Kanban UI 업데이트
```

---

## 수정된 파일 목록

| 파일 | 변경 유형 | 역할 |
|------|----------|------|
| `backend/core/daemon_status_bridge.py` | **신규** (~247줄) | daemon_status.json 작성 브릿지 |
| `backend/agents/coder.py` | 수정 (~15줄 추가) | bridge 연동 4개 지점 |
| `backend/cli/build_commands.py` | 수정 (~3줄 추가) | original_project_dir 전달 |
| `frontend/.../daemon-status-watcher.ts` | 수정 (리팩토링) | 다중 프로젝트 + 주기적 재전송 + execution progress |
| `frontend/.../agent-events-handlers.ts` | 수정 (break 제거 + 폴링 추가) | 5초 폴링으로 daemon_status.json 감지 |
| `frontend/.../execution-handlers.ts` | 수정 | worktree cleanup → cleanupWorktree() 유틸 사용 |

---

## 1. Backend: `core/daemon_status_bridge.py`

### 클래스 구조

```python
class DaemonStatusBridge:
    def __init__(self, project_dir, spec_id, spec_dir)
    def start() → daemon_status.json 생성 (이중 쓰기 방지 포함)
    def update(subtask_id, phase, session) → running_tasks 업데이트
    def complete() → stats.completed +1, running_tasks에서 제거
    def close() → 빌드 종료/실패 시 정리

    # Internal
    def _make_task_info() → TaskDaemon 호환 포맷
    def _make_status() → 전체 daemon_status.json 포맷
    def _read_existing() → 기존 파일 읽기
    def _write(data) → atomic write (.tmp → rename)
    @staticmethod _is_pid_alive(pid) → Windows-safe PID 체크
```

### 핵심 설계 결정

1. **이중 쓰기 방지**: `start()` 시 기존 daemon_status.json의 PID 체크
   - 살아있는 daemon이 해당 task를 관리 중이면 skip
   - 죽은 PID이면 덮어씀

2. **Windows 호환**: `_is_pid_alive()`
   - Unix: `os.kill(pid, 0)` — signal 0은 존재만 확인
   - **Windows**: `ctypes.windll.kernel32.OpenProcess()` + `CloseHandle()`
   - **주의**: Windows에서 `os.kill(pid, 0)`은 `TerminateProcess`를 호출해서 프로세스를 **죽임**

3. **Atomic write**: `.tmp` 파일에 먼저 쓰고 `os.replace()`로 이동
   - 파일 읽기 중간에 partial read 방지

4. **Merge 지원**: daemon이 이미 실행 중이면 `running_tasks`에 merge (기존 task 유지)

### daemon_status.json 포맷

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

---

## 2. Backend: `agents/coder.py` 연동

### 구조 변경

기존 `run_autonomous_agent()` 함수를 2단계로 분리:

```python
async def run_autonomous_agent(..., original_project_dir=None):
    bridge = DaemonStatusBridge(original_project_dir or project_dir, ...)
    bridge.start()
    try:
        await _run_autonomous_agent_inner(..., bridge=bridge)
    finally:
        bridge.close()  # 항상 실행 (예외/인터럽트 무관)

async def _run_autonomous_agent_inner(..., bridge):
    # 원래의 모든 로직
```

### 연동 4개 지점

| 시점 | 위치 | 동작 |
|------|------|------|
| **빌드 시작** | `run_autonomous_agent()` 진입 | `bridge.start()` |
| **subtask 진행** | 세션 header 출력 후 (~line 334) | `bridge.update(subtask_id, phase, session)` |
| **빌드 성공** | ALL_SUBTASKS_DONE 후 (~line 600) | `bridge.complete()` |
| **항상 (finally)** | try/finally 블록 | `bridge.close()` |

### `original_project_dir` 파라미터

worktree 모드에서 `project_dir`은 worktree 경로이지만, `daemon_status.json`은 **원본** 프로젝트 루트에 써야 합니다.

```python
# build_commands.py에서 전달:
original_project_dir=project_dir if working_dir != project_dir else None
```

---

## 3. Frontend: `daemon-status-watcher.ts`

### 구조 변경: 단일 → 다중 프로젝트

```typescript
// 이전: 단일 watcher
private watcher: FSWatcher | null = null;

// 현재: 프로젝트별 watcher Map
private watchers: Map<string, ProjectWatcher> = new Map();

interface ProjectWatcher {
  watcher: FSWatcher;           // chokidar 파일 감시
  statusFilePath: string;       // daemon_status.json 경로
  projectId: string;            // 프로젝트 ID
  watchedTasks: Set<string>;    // fileWatcher로 감시 중인 task
  previousRunningIds: Set<string>;  // 이전 상태 비교용
  previousCompleted: number;    // completed 카운트 비교용
  rendererReady: boolean;       // renderer 마운트 대기
  readyTimer: ReturnType<typeof setTimeout> | null;
  resendTimer: ReturnType<typeof setInterval> | null;  // 주기적 재전송
}
```

### 주요 기능

1. **chokidar 파일 감시**: daemon_status.json 변경 감지 → `processFile()`
2. **5초 주기적 재전송**: `setInterval` → forceRefresh 후에도 In Progress 유지
3. **TASK_STATUS_CHANGE**: Kanban 카드 이동 (in_progress, human_review, error)
4. **TASK_EXECUTION_PROGRESS**: phase badge (planning, coding 등) + current_subtask
5. **fileWatcher 연동**: implementation_plan.json 변경 감시 → subtask 진행률 표시
6. **다중 프로젝트**: 여러 프로젝트 동시 감시 가능

### 주기적 재전송이 필요한 이유

UI에서 채팅 입력 등 인터랙션 시 `TASK_LIST`의 `forceRefresh`가 호출됨
→ `TaskStateManager`가 클리어됨
→ `implementation_plan.json`에서 다시 로딩 (`status: "queue"`)
→ 카드가 Queue로 돌아감

5초마다 `processFile()`을 호출해서 daemon_status.json에서 다시 `in_progress`를 전송하면,
forceRefresh 후에도 카드가 In Progress로 복구됨.

### 정리 순서 (stopProject)

```typescript
// 1. daemon-managed entries 정리 (BEFORE clearing sets)
for (const specId of pw.watchedTasks) {
  fileWatcher.unwatch(specId);
  daemonManagedTasks.delete(specId);
}
for (const specId of pw.previousRunningIds) {
  daemonManagedTasks.delete(specId);
}
// 2. THEN clear sets
pw.watchedTasks.clear();
pw.previousRunningIds.clear();
```

**주의**: 순서가 바뀌면 clear() 후에는 Set이 비어있어서 cleanup이 안 됨.

---

## 4. Frontend: `agent-events-handlers.ts`

### 변경 사항

```typescript
// 이전: 첫 번째 프로젝트만 감시 (break)
for (const p of projects) {
  const statusPath = path.join(p.path, 'daemon_status.json');
  if (existsSync(statusPath)) {
    daemonStatusWatcher.start(statusPath, getMainWindow, p.id);
    break;  // ← 이거 때문에 하나만 감시
  }
}

// 현재: 모든 프로젝트 감시 + 5초 폴링
const scanDaemonStatusFiles = () => {
  const allProjects = projectStore.getProjects();
  for (const p of allProjects) {
    const statusPath = path.join(p.path, 'daemon_status.json');
    if (existsSync(statusPath)) {
      daemonStatusWatcher.start(statusPath, getMainWindow, p.id);
      // break 제거 → 모든 프로젝트 watch
    }
  }
};
scanDaemonStatusFiles();
setInterval(scanDaemonStatusFiles, 5000);  // UI 부팅 후 생성된 파일도 감지
```

### 5초 폴링이 필요한 이유

UI 부팅 시 daemon_status.json이 아직 없을 수 있음 (run.py가 나중에 시작).
폴링으로 나중에 생성된 파일도 자동 감지.

---

## 5. 알려진 이슈 및 해결 상태

### 해결 완료

| 이슈 | 원인 | 해결 |
|------|------|------|
| Windows `os.kill(pid, 0)` 프로세스 종료 | Windows에서 signal 0이 TerminateProcess 호출 | `ctypes.windll.kernel32.OpenProcess` 사용 |
| `stopProject()` cleanup 안 됨 | `clear()` 후 빈 Set 순회 | cleanup을 clear() 전에 실행 |
| Early return에서 bridge 미정리 | try/finally 없음 | outer/inner 함수 분리 + try/finally |
| resume 시 파라미터 누락 | `original_project_dir`, `source_spec_dir` 미전달 | 두 파라미터 모두 전달 |
| UI 부팅 후 daemon_status.json 미감지 | 부팅 시 1회만 체크 | 5초 폴링 추가 |
| forceRefresh 후 카드 Queue로 복귀 | store 클리어 후 implementation_plan.json 재로딩 | 5초 주기적 재전송 |
| phase badge 미표시 | TASK_EXECUTION_PROGRESS 미전송 | processFile에서 phase 정보 전송 추가 |
| 빌드 완료 후 무한 in_progress 루프 | scanDaemonStatusFiles(5s)가 stopProject 후 watcher 재생성 | `start()`에서 `running: false`인 파일 무시 |

### 알려진 제한사항

| 제한 | 설명 | 잠재적 해결 |
|------|------|-------------|
| MCP tool 권한 (`create_batch_child_specs`) | run.py에서 Claude SDK 사용 시 MCP tool 자동 승인 안 됨 | `.claude_settings.json`에 allowed_tools 추가 또는 SDK 레벨 permission 설정 |
| Worktree cleanup EBUSY | 빌드 프로세스가 디렉토리 잠금 시 삭제 불가 | 프로세스 종료 후 재시도 또는 Windows에서 MoveFileEx 사용 |
| daemon_status.json bridge.update() 빈도 | session 전환 시에만 update → 긴 subtask 중에는 phase가 안 바뀜 | subtask 완료마다 update 호출 추가 |

---

## 6. 테스트 방법

### 기본 테스트 (CLI → UI 실시간 연동)

```bash
# Terminal 1: UI 실행
cd Auto-Claude/apps/frontend && npm run dev

# Terminal 2: CLI 빌드 (UI 부팅 후)
cd Auto-Claude/apps/backend
.venv\Scripts\python.exe run.py \
  --project-dir "C:\path\to\project" \
  --spec 001-spec-id \
  --force --auto-continue --max-iterations 3
```

### 검증 체크리스트

- [ ] daemon_status.json 자동 생성
- [ ] UI에서 5초 이내 In Progress 카드 표시
- [ ] phase badge 표시 (planning → coding)
- [ ] 채팅 입력 후에도 카드가 In Progress 유지 (forceRefresh 복구)
- [ ] subtask 진행률 표시 (implementation_plan.json 파일 감시)
- [ ] 빌드 완료 시 Human Review로 이동
- [ ] 빌드 실패 시 Error 표시
- [ ] daemon_status.json cleanup (running: false)
- [ ] 다중 프로젝트 동시 빌드 → 각각 UI에 표시

### 검증 명령어

```bash
# daemon_status.json 확인
cat calculator/daemon_status.json | python -m json.tool

# UI 로그에서 DaemonStatusWatcher 확인
# Electron DevTools > Console에서:
# [DaemonStatusWatcher] Task XXX → in_progress
```

---

## 7. 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                     External Terminal                             │
│                                                                   │
│  run.py --spec 001 --force --auto-continue                       │
│    │                                                              │
│    ├── coder.py: run_autonomous_agent()                          │
│    │     │                                                        │
│    │     ├── bridge = DaemonStatusBridge(project_dir, ...)        │
│    │     ├── bridge.start()  ──────────────────────┐              │
│    │     │                                          │              │
│    │     ├── try:                                   │              │
│    │     │   ├── planner session                    │              │
│    │     │   │   └── bridge.update(phase=planning)  │              │
│    │     │   ├── coder sessions (loop)              │              │
│    │     │   │   └── bridge.update(phase=coding)    │              │
│    │     │   └── bridge.complete()                  │              │
│    │     │                                          ▼              │
│    │     └── finally: bridge.close()        daemon_status.json    │
│    │                                        (프로젝트 루트)       │
└────┼────────────────────────────────────────────────┼─────────────┘
     │                                                │
     │                                                │ chokidar watch
     │                                                │ + 5s interval
     │                                                ▼
┌────┼──────────────────────────────────────────────────────────────┐
│    │              Electron Main Process                            │
│    │                                                              │
│    │  agent-events-handlers.ts                                    │
│    │    └── setInterval(scanDaemonStatusFiles, 5000)              │
│    │          └── daemonStatusWatcher.start(statusPath, ...)      │
│    │                                                              │
│    │  DaemonStatusWatcher                                         │
│    │    ├── processFile()                                         │
│    │    │   ├── IPC: TASK_STATUS_CHANGE → in_progress             │
│    │    │   ├── IPC: TASK_EXECUTION_PROGRESS → phase badge        │
│    │    │   └── fileWatcher.watch(specId, specDir) → subtask 진행 │
│    │    │                                                         │
│    │    └── resendTimer (5s) → processFile() 재호출               │
│    │                                                              │
└────┼──────────────────────────────────────────────────────────────┘
     │                        │ IPC
     │                        ▼
┌────┼──────────────────────────────────────────────────────────────┐
│    │              Electron Renderer                                │
│    │                                                              │
│    │  Zustand task store                                          │
│    │    ├── TASK_STATUS_CHANGE → task.status = 'in_progress'      │
│    │    ├── TASK_EXECUTION_PROGRESS → task.phase = 'coding'       │
│    │    └── TASK_PROGRESS → task.subtasks (진행률)                 │
│    │                                                              │
│    │  Kanban Board                                                │
│    │    └── 카드가 In Progress 컬럼으로 이동                      │
│    │        + phase badge (planning/coding) 표시                  │
│    │        + subtask 진행률 표시 (3/24)                           │
│    │                                                              │
└───────────────────────────────────────────────────────────────────┘
```

---

## 8. 다음 AI를 위한 핵심 참고사항

1. **`daemon_status.json`은 프로젝트 루트에 생성됨** (worktree 아닌 원본)
2. **`bridge.close()`는 try/finally로 보장됨** — 수정 시 이 패턴 유지 필수
3. **Windows에서 절대 `os.kill(pid, 0)` 사용 금지** — ctypes 패턴 사용
4. **`stopProject()`에서 cleanup → clear 순서 중요** — 순서 바뀌면 메모리 누수
5. **5초 재전송은 성능 영향 없음** — task store가 동일 업데이트 dedup
6. **MCP tool 권한**: `create_batch_child_specs` 사용하려면 `.claude_settings.json`에 tool 허용 필요
7. **implementation_plan.json의 status 필드**: CLI 빌드 시 bridge가 이 파일을 수정하지 않음. status는 daemon_status.json → DaemonStatusWatcher → IPC로만 전달
