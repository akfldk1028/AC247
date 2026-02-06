---
name: ac-debug
description: |
  Auto-Claude 파이프라인 디버깅. 실패한 spec/task의 원인 분석 및 해결.
  사용 시점: (1) spec 생성 실패, (2) daemon task 실패, (3) QA 무한루프, (4) Kanban 카드 안 움직임
argument-hint: "[spec-dir-or-symptom]"
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob, Bash
---

# Auto-Claude Debug Skill

파이프라인 실패를 진단하고 해결합니다.

## When to Use
- Spec 생성 실패 ("Agent did not create spec.md" 등)
- Daemon task가 stuck 상태
- QA 무한 루프 (max iterations)
- Kanban 카드가 올바른 컬럼에 안 표시됨
- implementation_plan.json status 불일치

## When NOT to Use
- 정상 동작하는 파이프라인 탐색 → `/ac-explore` 사용
- 코드 수정이 필요한 경우 → 직접 수정
- UI 디자인 문제 → frontend dev tools 사용

## Diagnostic Checklist

### 증상 1: "Agent did not create spec.md" (3회 retry 후 실패)

**원인 A: Stale spec_dir (가장 흔함)**
```bash
# spec 디렉토리 확인 - rename 되었는지?
ls .auto-claude/specs/

# 001-pending이 남아있으면 stale path 문제
# orchestrator.py의 post-rename sync 확인
```

**원인 B: agent가 파일을 만들었지만 success=False**
```bash
# spec.md가 실제로 존재하는지 확인
ls .auto-claude/specs/*/spec.md

# agent_runner.py의 exception 로그 확인
# rate limit, timeout 등이 원인일 수 있음
```

**해결:** `orchestrator.py`에서 rename 후 sync 코드 확인:
- File: `apps/backend/spec/pipeline/orchestrator.py`
- 검색: `_rename_spec_dir_from_requirements`
- 바로 아래에 5줄의 sync 코드가 있어야 함

### 증상 2: Daemon이 task를 pickup 안 함

```bash
# 1. Plan status 확인
cat .auto-claude/specs/*/implementation_plan.json | grep '"status"'
# → "queue"여야 함

# 2. daemon_status.json 확인
cat .auto-claude/daemon_status.json
# → running: true, queued_tasks 에 있어야 함

# 3. Daemon 프로세스 확인
tasklist | findstr python
```

### 증상 3: QA 무한 루프

```bash
# qa_iteration_history 확인
cat .auto-claude/specs/*/implementation_plan.json | python -c "
import json, sys
d = json.load(sys.stdin)
print(f'QA iterations: {d.get(\"qa_stats\", {}).get(\"total_iterations\", 0)}')
for h in d.get('qa_iteration_history', []):
    print(f'  #{h[\"iteration\"]}: {h[\"status\"]} - {len(h.get(\"issues\", []))} issues')
"
```

### 증상 4: Kanban 카드 wrong column

```bash
# Status mapping 확인
cat .auto-claude/specs/*/implementation_plan.json | python -c "
import json, sys
d = json.load(sys.stdin)
print(f'status: {d.get(\"status\")}')
print(f'xstateState: {d.get(\"xstateState\")}')
print(f'planStatus: {d.get(\"planStatus\")}')
print(f'executionPhase: {d.get(\"executionPhase\")}')
print(f'reviewReason: {d.get(\"reviewReason\")}')
"
```

**Status → Column 매핑:**
| status | xstateState | Column |
|--------|-------------|--------|
| queue | backlog | Backlog |
| in_progress | planning/coding | In Progress |
| ai_review | qa_review | AI Review |
| human_review | human_review | Human Review |
| done | done | Done |

## Key Files for Debugging

| File | What to check |
|------|--------------|
| `spec/pipeline/orchestrator.py` | Post-rename sync, phase ordering |
| `spec/phases/spec_phases.py` | File-exists check, retry logic |
| `spec/pipeline/agent_runner.py` | (success, output) return values |
| `core/task_event.py` | Event → status persistence |
| `services/task_daemon/__init__.py` | Task pickup, stuck detection |
| `services/task_daemon/executor.py` | Command building, env vars |

## References
- [Known Bug Patterns](references/known-bugs.md)
