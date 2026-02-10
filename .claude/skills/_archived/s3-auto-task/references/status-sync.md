# Status Synchronization Guide

Auto-Claude Backend와 Frontend UI 간의 상태 동기화 메커니즘 상세 가이드.

## Overview

Auto-Claude는 XState를 사용하여 task 상태를 관리합니다.

### 동기화 방식 (2가지)

1. **Real-time (UI 실행 중)**: Backend → stdout 이벤트 → Frontend XState → Kanban 이동
2. **Deferred (CLI-only)**: Backend → implementation_plan.json 저장 → 나중에 UI 열 때 복원

**2026.02+ 버전부터** CLI만 실행해도 `implementation_plan.json`에 status가 자동 저장됩니다.
UI 없이 빌드 완료 후, 나중에 UI를 열면 카드가 올바른 컬럼에 표시됩니다.

## Event Protocol

### Format

```
__TASK_EVENT__:{"type":"EVENT_NAME","taskId":"xxx","sequence":0,...}
```

### Event Structure

```typescript
interface TaskEventPayload {
  type: string;           // Event type (e.g., "PLANNING_COMPLETE")
  taskId: string;         // Task identifier
  specId: string;         // Spec directory name
  projectId: string;      // Project identifier
  timestamp: string;      // ISO 8601 timestamp
  eventId: string;        // UUID for deduplication
  sequence: number;       // Monotonic sequence number
  [key: string]: any;     // Event-specific payload
}
```

### Sequence Number

- 각 task마다 별도의 sequence 카운터 유지
- 이전 sequence보다 작거나 같은 이벤트는 무시됨
- `implementation_plan.json`의 `lastEvent.sequence`에서 복원

## Key Events

### Planning Phase

| Event | Trigger | XState Transition |
|-------|---------|-------------------|
| `PLANNING_STARTED` | spec_runner.py 시작 | backlog → planning |
| `PLANNING_COMPLETE` | Spec 생성 완료 | planning → plan_review |
| `PLANNING_FAILED` | Spec 생성 실패 | planning → error |

### Coding Phase

| Event | Trigger | XState Transition |
|-------|---------|-------------------|
| `PLAN_APPROVED` | UI에서 승인 | plan_review → coding |
| `ALL_SUBTASKS_DONE` | 모든 subtask 완료 | coding → qa_review |
| `CODING_FAILED` | 빌드 실패 | coding → error |

### QA Phase

| Event | Trigger | XState Transition |
|-------|---------|-------------------|
| `QA_STARTED` | QA 검증 시작 | coding → qa_review |
| `QA_PASSED` | QA 승인 | qa_review → human_review |
| `QA_FAILED` | QA 거부 | qa_review → qa_fixing |
| `QA_FIXING_COMPLETE` | Fix 적용 완료 | qa_fixing → qa_review |
| `QA_MAX_ITERATIONS` | Max iterations 도달 | qa_review → human_review |

### Completion

| Event | Trigger | XState Transition |
|-------|---------|-------------------|
| `MARK_DONE` | UI에서 Done 클릭 | human_review → done |
| `PR_CREATED` | PR 생성 완료 | human_review → pr_created |

## implementation_plan.json

### Status Fields

Frontend `TaskStateManager`가 자동으로 저장하는 필드:

```json
{
  "feature": "Add authentication",
  "phases": [...],

  // XState sync fields (자동 저장)
  "status": "human_review",
  "xstateState": "human_review",
  "reviewReason": "completed",
  "executionPhase": "complete",
  "updated_at": "2026-02-03T10:30:00.000Z",

  // Event tracking
  "lastEvent": {
    "eventId": "uuid",
    "sequence": 5,
    "type": "QA_PASSED",
    "timestamp": "2026-02-03T10:30:00.000Z"
  }
}
```

### Status Values

| status | xstateState | reviewReason | Description |
|--------|-------------|--------------|-------------|
| `backlog` | `backlog` | - | 아직 시작 안 함 |
| `in_progress` | `planning` | - | Spec 생성 중 |
| `human_review` | `plan_review` | `plan_review` | Plan 검토 대기 |
| `in_progress` | `coding` | - | 코딩 진행 중 |
| `ai_review` | `qa_review` | - | QA 검증 중 |
| `human_review` | `human_review` | `completed` | 완료 검토 대기 |
| `pr_created` | `pr_created` | - | PR 생성됨 |
| `done` | `done` | - | 완료 |
| `error` | `error` | `errors` | 오류 발생 |

## Backend Event Emission

### Python Code Example

```python
from core.task_event import TaskEventEmitter

# Create emitter from spec directory
emitter = TaskEventEmitter.from_spec_dir(spec_dir)

# Emit event - 자동으로 implementation_plan.json에도 저장됨!
emitter.emit("PLANNING_COMPLETE", {
    "hasSubtasks": False,
    "subtaskCount": 0,
    "requireReviewBeforeCoding": True
})
# 위 호출 시 자동으로:
# - stdout에 __TASK_EVENT__:{...} 출력 (UI 동기화용)
# - implementation_plan.json에 status, xstateState 저장 (CLI-only 지원)

# Use convenience method for custom status changes
emitter.emit_status_change(
    status="human_review",
    review_reason="completed",
    execution_phase="complete"
)
```

### Auto-Persist Events

다음 이벤트 발행 시 자동으로 `implementation_plan.json`에 status가 저장됩니다:

| Event | status | xstateState | reviewReason |
|-------|--------|-------------|--------------|
| `PLANNING_STARTED` | in_progress | planning | - |
| `PLANNING_COMPLETE` | human_review | plan_review | plan_review |
| `ALL_SUBTASKS_DONE` | ai_review | qa_review | - |
| `QA_PASSED` | human_review | human_review | completed |
| `QA_FAILED` | in_progress | qa_fixing | - |
| `QA_MAX_ITERATIONS` | human_review | human_review | max_iterations |

### Files That Emit Events

| File | Events |
|------|--------|
| `spec/pipeline/orchestrator.py` | PLANNING_STARTED, PLANNING_COMPLETE |
| `agents/coder.py` | ALL_SUBTASKS_DONE |
| `qa/loop.py` | QA_STARTED, QA_PASSED, QA_FAILED, QA_FIXING_* |

## Frontend Event Handling

### TaskStateManager (Electron Main)

Location: `apps/frontend/src/main/task-state-manager.ts`

```typescript
// Event handling
handleTaskEvent(taskId, event, task, project) {
  if (!this.isNewSequence(taskId, event.sequence)) {
    return false; // Duplicate event ignored
  }

  const actor = this.getOrCreateActor(taskId);
  actor.send(event); // XState transition

  // Persist to implementation_plan.json
  this.persistStatus(task, project, status, reviewReason, xstateState);

  // Emit IPC to renderer
  this.emitStatus(taskId, status, reviewReason, projectId);
}
```

### IPC Channels

| Channel | Direction | Payload |
|---------|-----------|---------|
| `TASK_STATUS_CHANGE` | Main → Renderer | taskId, status, projectId, reviewReason |
| `TASK_EXECUTION_PROGRESS` | Main → Renderer | taskId, progress object, projectId |

## Troubleshooting

### Event Not Processed

1. **Check stdout format**
   ```bash
   # Backend 출력에서 이벤트 확인
   grep "__TASK_EVENT__" output.log
   ```

2. **Check sequence**
   ```bash
   # lastEvent.sequence 확인
   cat implementation_plan.json | jq '.lastEvent'
   ```

3. **Check XState actor**
   - Frontend 콘솔에서 `[TaskStateManager]` 로그 확인

### Status Not Persisted

1. **Check file permissions**
   ```bash
   ls -la implementation_plan.json
   ```

2. **Check JSON validity**
   ```bash
   cat implementation_plan.json | jq .
   ```

### Kanban Card Wrong Column

1. **Check xstateState**
   - `status`와 `xstateState`가 일치하는지 확인
   - Frontend는 `xstateState`를 우선 사용

2. **Force refresh**
   - UI에서 task 목록 새로고침
   - 또는 앱 재시작

## Manual Status Update

**참고:** 2026.02+ 버전에서는 CLI 실행 시 자동으로 status가 저장됩니다.
아래는 레거시 빌드나 특수한 상황에서만 필요합니다.

```bash
# implementation_plan.json 수정 (레거시 빌드용)
jq '. + {
  "status": "human_review",
  "xstateState": "human_review",
  "reviewReason": "completed",
  "executionPhase": "complete"
}' implementation_plan.json > tmp.json && mv tmp.json implementation_plan.json
```

### Python으로 수동 업데이트

```python
from core.task_event import _persist_status_to_plan
from pathlib import Path

_persist_status_to_plan(
    spec_dir=Path(".auto-claude/specs/001-my-task"),
    status="human_review",
    xstate_state="human_review",
    review_reason="completed",
    execution_phase="complete"
)
```

## Related Files

| Component | File |
|-----------|------|
| Event Emitter | `apps/backend/core/task_event.py` |
| Spec Orchestrator | `apps/backend/spec/pipeline/orchestrator.py` |
| Coder Agent | `apps/backend/agents/coder.py` |
| QA Loop | `apps/backend/qa/loop.py` |
| State Manager | `apps/frontend/src/main/task-state-manager.ts` |
| Plan Utils | `apps/frontend/src/main/ipc-handlers/task/plan-file-utils.ts` |
| XState Machine | `apps/frontend/src/shared/state-machines/task-machine.ts` |
