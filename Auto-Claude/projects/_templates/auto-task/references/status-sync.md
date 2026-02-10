# Status Synchronization Guide

Auto-Claude Backend와 Frontend UI 간의 상태 동기화 메커니즘.

## Overview

Auto-Claude는 XState를 사용하여 task 상태를 관리합니다.

### 동기화 방식 (2가지)

1. **Real-time (UI 실행 중)**: Backend → stdout 이벤트 → Frontend XState → Kanban 이동
2. **Deferred (CLI-only)**: Backend → implementation_plan.json 저장 → 나중에 UI 열 때 복원

## Key Events

| Event | Trigger | XState Transition |
|-------|---------|-------------------|
| `PLANNING_STARTED` | spec_runner.py 시작 | backlog → planning |
| `PLANNING_COMPLETE` | Spec 생성 완료 | planning → plan_review |
| `ALL_SUBTASKS_DONE` | 모든 subtask 완료 | coding → qa_review |
| `QA_PASSED` | QA 승인 | qa_review → human_review |
| `QA_FAILED` | QA 거부 | qa_review → qa_fixing |

## implementation_plan.json Status Fields

```json
{
  "status": "human_review",
  "xstateState": "human_review",
  "reviewReason": "completed",
  "executionPhase": "complete",
  "updated_at": "2026-02-03T..."
}
```

## Status Values

| status | xstateState | Description |
|--------|-------------|-------------|
| `backlog` | `backlog` | 아직 시작 안 함 |
| `in_progress` | `planning` | Spec 생성 중 |
| `human_review` | `plan_review` | Plan 검토 대기 |
| `in_progress` | `coding` | 코딩 진행 중 |
| `ai_review` | `qa_review` | QA 검증 중 |
| `human_review` | `human_review` | 완료 검토 대기 |
| `done` | `done` | 완료 |

## Troubleshooting

### Event Not Processed
- stdout에서 `__TASK_EVENT__` 확인
- `lastEvent.sequence` 확인

### Kanban Card Wrong Column
- `status`와 `xstateState` 일치 확인
- Frontend는 `xstateState`를 우선 사용
- UI refresh (F5)
