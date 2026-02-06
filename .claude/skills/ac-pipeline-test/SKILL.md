---
name: ac-pipeline-test
description: |
  Auto-Claude 파이프라인 E2E 테스트. spec 생성 → daemon 실행 → QA → 완료까지 전체 검증.
  사용 시점: (1) 코드 수정 후 파이프라인 검증, (2) 새 프로젝트에서 Auto-Claude 동작 확인, (3) 버그 수정 후 회귀 테스트
argument-hint: "[project-path] [--task description]"
---

# Auto-Claude Pipeline E2E Test

전체 파이프라인을 end-to-end로 테스트합니다.

## When to Use
- Auto-Claude 백엔드 코드 수정 후 파이프라인 전체 검증
- 새 프로젝트에서 Auto-Claude가 정상 동작하는지 확인
- 버그 수정 후 회귀 테스트

## When NOT to Use
- 단순 코드 리뷰 → 직접 Read/Grep 사용
- UI만 테스트 → `npm run dev` 직접 실행
- 단일 phase만 테스트 → 해당 phase 직접 실행

## Test Process

### Step 1: 테스트 프로젝트 준비

```bash
# 클린 테스트 디렉토리 생성
mkdir -p C:\DK\test-pipeline
cd C:\DK\test-pipeline
git init
mkdir -p .auto-claude/specs
```

### Step 2: Spec 생성 테스트

```bash
cd C:\DK\AC247\AC247\Auto-Claude\apps\backend
python runners/spec_runner.py \
  --project-dir "C:\DK\test-pipeline" \
  --task "Python 계산기: 사칙연산 클래스(calculator.py), CLI(main.py), pytest(test_calculator.py)" \
  --auto-approve --no-build --direct
```

**검증 포인트:**
- [ ] `001-pending` → `001-meaningful-name` 으로 rename 됨
- [ ] `spec.md` 생성됨 (>100줄)
- [ ] `requirements.json` 생성됨
- [ ] `implementation_plan.json` 생성됨 (status: "queue")
- [ ] `complexity_assessment.json` 생성됨

### Step 3: Daemon 실행 테스트

```bash
python runners/daemon_runner.py \
  --project-dir "C:\DK\test-pipeline" \
  --status-file "C:\DK\test-pipeline\.auto-claude\daemon_status.json"
```

**검증 포인트:**
- [ ] Daemon이 spec을 자동으로 pickup
- [ ] 모든 subtask 완료
- [ ] QA 통과 (qa_signoff.status == "approved")
- [ ] implementation_plan.json → status: "done"
- [ ] daemon_status.json → completed: 1

### Step 4: 결과 검증

```bash
# Plan 상태 확인
python -c "import json; d=json.load(open('.auto-claude/specs/*/implementation_plan.json')); print(d['status'])"

# 생성된 파일 확인
ls *.py

# 테스트 실행
pytest test_calculator.py -v
```

## Known Gotchas

1. **Stale spec_dir**: spec rename 후 PhaseExecutor가 옛날 경로 참조 → orchestrator.py 참조
2. **File-exists-but-success=False**: agent가 파일 만들고 SDK 에러나도 파일은 유효 → 파일 존재 먼저 체크
3. **Windows file lock**: daemon_status.json replace 시 UI가 읽고 있으면 실패 → retry 로직 있음

## Quick Validation (코드만 검증)

파이프라인 실행 없이 import만 검증:
```bash
cd C:\DK\AC247\AC247\Auto-Claude\apps\backend
python -c "
from spec.phases import PhaseExecutor, PhaseResult
from spec.pipeline.orchestrator import SpecOrchestrator
from spec.pipeline.agent_runner import run_agent
from services.task_daemon import TaskDaemon
print('All imports OK')
"
```
