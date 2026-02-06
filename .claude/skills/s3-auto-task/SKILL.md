---
name: s3-auto-task
description: |
  Auto-Claude로 task 생성 및 자동 빌드. Kanban 카드 자동 이동.
  사용 시점: (1) 새 기능 개발 시작, (2) 버그 수정 요청, (3) 24/7 자동 빌드
argument-hint: "[task-description] [--project path] [--auto-approve]"
---

# S3 Auto-Task Skill

Auto-Claude를 통해 task를 생성하고 자동으로 빌드합니다.
**XState 기반으로 Kanban 카드가 자동으로 이동합니다.**

## Architecture Overview

```
Claude Code CLI (이 Skill)
        │
        ▼
    spec_runner.py (Python Backend)
        │
        ├── stdout: __TASK_EVENT__:{json}  ← XState 프로토콜 (UI 실행 중)
        │
        └── implementation_plan.json에 status 자동 저장 ← CLI-only 지원
        │
        ▼
    [UI 실행 중일 때]
    Electron Main Process
        │
        └── TaskStateManager → XState Actor
        │
        ▼
    IPC: TASK_STATUS_CHANGE
        │
        ▼
    Renderer (Zustand store)
        │
        ▼
    Kanban UI 카드 이동

    [UI 없이 CLI만 실행할 때]
    implementation_plan.json에 저장된 status로
    나중에 UI 열 때 올바른 컬럼에 표시됨
```

### CLI-Only 실행 지원

**v2026.02+ 부터** CLI만 실행해도 status가 자동 저장됩니다:
- `PLANNING_STARTED` → `status: in_progress, xstateState: planning`
- `PLANNING_COMPLETE` → `status: human_review, xstateState: plan_review`
- `ALL_SUBTASKS_DONE` → `status: ai_review, xstateState: qa_review`
- `QA_PASSED` → `status: human_review, xstateState: human_review`

UI 없이 CLI로 빌드 완료 후, 나중에 UI를 열면 카드가 올바른 컬럼에 표시됩니다.

## When to Use

- 새 기능을 Auto-Claude로 자동 개발할 때
- 버그 수정을 자동화하고 싶을 때
- 24/7 자동 빌드 파이프라인 구축 시
- CI/CD 파이프라인에서 task 자동 생성

## When NOT to Use

- 간단한 1줄 수정 → 직접 수정이 빠름
- 복잡한 아키텍처 설계 필요 → 먼저 설계 후 사용
- UI에서 직접 task 관리 원할 때 → Auto-Claude UI 사용

## Quick Start

```bash
# Task 생성 + 자동 빌드
/s3-auto-task "Add user authentication with JWT"

# Task만 생성 (UI에서 Start)
/s3-auto-task "Add feature X" --no-build
```

## Usage

```
/s3-auto-task [task-description] [options]
```

### Options

| 옵션 | 설명 |
|------|------|
| `--project <path>` | 프로젝트 경로 (기본: 현재 S3/frontend) |
| `--no-build` | Task만 생성, 빌드 안 함 (UI에서 Start) |
| `--auto-approve` | Review checkpoint 자동 승인 |
| `--complexity <level>` | simple / standard / complex |

## Complete Workflow

### Step 1: Task 생성 (Spec Creation)

```bash
cd C:\DK\S3\S3\Auto-Claude\apps\backend
.venv\Scripts\python.exe runners\spec_runner.py \
  --project-dir "C:\DK\S3\S3\frontend" \
  --task "Add user authentication" \
  --auto-approve
```

**이벤트 발행:**
- `PLANNING_STARTED` → Kanban: Backlog → In Progress
- `PLANNING_COMPLETE` → Kanban: In Progress → Human Review (plan_review)

### Step 2: 자동 빌드 실행

```bash
.venv\Scripts\python.exe run.py \
  --project-dir "C:\DK\S3\S3\frontend" \
  --spec 001-add-auth
```

**이벤트 발행:**
- Planning subtasks → Coding phase
- `ALL_SUBTASKS_DONE` → QA Review 시작

### Step 3: QA 검증

```bash
.venv\Scripts\python.exe run.py \
  --project-dir "C:\DK\S3\S3\frontend" \
  --spec 001-add-auth \
  --qa
```

**이벤트 발행:**
- `QA_STARTED` → AI Review phase
- `QA_PASSED` → Human Review (completed)
- `QA_FAILED` → QA Fixing phase

### Step 4: Merge

```bash
.venv\Scripts\python.exe run.py \
  --project-dir "C:\DK\S3\S3\frontend" \
  --spec 001-add-auth \
  --merge
```

## Task Event Protocol

Backend는 `__TASK_EVENT__:{json}` 형식으로 stdout에 이벤트를 발행합니다.

### Key Events

| Event | Description | Kanban Transition |
|-------|-------------|-------------------|
| `PLANNING_STARTED` | Spec 생성 시작 | Backlog → In Progress |
| `PLANNING_COMPLETE` | Spec 완료 | In Progress → Human Review |
| `ALL_SUBTASKS_DONE` | 코딩 완료 | In Progress → AI Review |
| `QA_PASSED` | QA 승인 | AI Review → Human Review |
| `QA_FAILED` | QA 거부 | AI Review → In Progress (fixing) |

### implementation_plan.json Status Fields

```json
{
  "phases": [...],
  "status": "human_review",
  "xstateState": "human_review",
  "reviewReason": "completed",
  "executionPhase": "complete",
  "updated_at": "2026-02-03T..."
}
```

## UI Integration Test

### Terminal 1: Auto-Claude UI 실행

```bash
cd C:\DK\S3\S3\Auto-Claude\apps\frontend
npm run dev
```

### Terminal 2: CLI로 task 생성

```bash
cd C:\DK\S3\S3\Auto-Claude\apps\backend
.venv\Scripts\python.exe runners\spec_runner.py \
  --project-dir "C:\DK\S3\S3\frontend" \
  --task "Test auto-sync feature" \
  --auto-approve
```

### 기대 결과

1. UI Kanban에 새 카드 생성 (In Progress)
2. 빌드 진행 중 phase badge 표시
3. 완료 시 Human Review 컬럼으로 이동

## Troubleshooting

### 카드가 안 움직임

**증상:** CLI 빌드 완료 후에도 Kanban 카드가 그대로

**원인 1: UI가 실행되지 않음**
```bash
# UI 실행 확인
cd C:\DK\S3\S3\Auto-Claude\apps\frontend && npm run dev
```

**원인 2: 이벤트 sequence 문제**
```bash
# implementation_plan.json의 lastEvent.sequence 확인
cat .auto-claude/specs/XXX/implementation_plan.json | grep -A5 lastEvent
```

**해결:** UI refresh (F5) 또는 task 목록 강제 새로고침

### 빌드가 멈춤

**원인:** Review checkpoint에서 Enter 대기

**해결:** `--auto-approve` 플래그 사용
```bash
.venv\Scripts\python.exe runners\spec_runner.py \
  --project-dir "..." \
  --task "..." \
  --auto-approve
```

### QA 무한 루프

**원인:** 반복되는 이슈로 max iterations 도달

**해결:**
1. `QA_FIX_REQUEST.md` 확인
2. 수동으로 이슈 해결
3. QA 재실행

### Status 필드 누락 (레거시 빌드)

**원인:** 2026.02 이전 버전 Backend로 빌드된 task

**확인:**
```bash
# implementation_plan.json에 status 필드가 있는지 확인
cat .auto-claude/specs/XXX/implementation_plan.json | grep -E '"status"|"xstateState"'
```

**수동 해결 (레거시 빌드만):**
```bash
# implementation_plan.json에 status 필드 추가
# JSON 끝에:
{
  ...,
  "status": "human_review",
  "xstateState": "human_review",
  "reviewReason": "completed"
}
```

**참고:** 2026.02+ 버전에서는 CLI 실행 시 자동으로 status가 저장됩니다.

## Auto-Claude Paths

| 항목 | 경로 |
|------|------|
| Backend | `C:\DK\S3\S3\Auto-Claude\apps\backend` |
| Frontend | `C:\DK\S3\S3\Auto-Claude\apps\frontend` |
| Python | `.venv\Scripts\python.exe` |
| Spec Runner | `runners\spec_runner.py` |
| Run | `run.py` |

## Related Skills

- `/s3-build` - Flutter/Python 빌드
- `/s3-test` - 테스트 실행
- `/s3-feature` - Feature-First 구조 생성

## References

- [Status Sync Guide](references/status-sync.md)
- [Auto-Claude ARCHITECTURE.md](../../../Auto-Claude/shared_docs/ARCHITECTURE.md)
