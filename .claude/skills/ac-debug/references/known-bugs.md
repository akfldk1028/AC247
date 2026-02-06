# Known Bug Patterns (Auto-Claude)

이 문서는 Auto-Claude 개발 중 발견된 버그 패턴을 기록합니다. 같은 실수를 반복하지 않기 위한 참조용입니다.

## Bug #1: Stale spec_dir after rename

**발견일:** 2026-02-06
**심각도:** Critical (파이프라인 완전 중단)
**영향:** spec_writing phase가 3회 retry 후 실패

### 증상
```
✗ Phase 'spec_writing' failed after 3 retries
  → Attempt 1: Agent did not create spec.md
  → Attempt 2: Agent did not create spec.md
  → Attempt 3: Agent did not create spec.md
```

Agent 로그를 보면 spec.md를 성공적으로 Write한 것으로 나옴.

### 원인
`orchestrator.py`의 `_rename_spec_dir_from_requirements()` 가 `self.spec_dir`을 업데이트하지만, 이미 생성된 `PhaseExecutor`, `SpecValidator`, `TaskLogger` 인스턴스는 여전히 옛날 `001-pending` 경로를 참조.

### 해결
```python
# orchestrator.py - _rename_spec_dir_from_requirements() 직후:
self.validator = SpecValidator(self.spec_dir)
task_logger = get_task_logger(self.spec_dir)
phase_executor.spec_dir = self.spec_dir
phase_executor.spec_validator = self.validator
phase_executor.task_logger = task_logger
```

### 예방 규칙
- `spec_dir` 경로가 바뀌는 곳을 수정할 때, 반드시 모든 참조를 grep으로 찾아서 업데이트

---

## Bug #2: File-exists-but-success=False

**발견일:** 2026-02-06
**심각도:** High (phase 실패로 3회 불필요한 retry)

### 증상
Agent가 파일을 생성했는데 phase가 실패로 보고함.

### 원인
`agent_runner.py:run_agent()` 는 SDK exception 발생 시 `(False, str(e))` 를 반환. Rate limit, timeout, network error가 agent 작업 완료 후에 발생할 수 있음. 코드가 `if not success: error` 패턴이면 유효한 파일을 무시.

### 해결 패턴
```python
# BEFORE (잘못된 패턴)
if not success:
    errors.append("Agent failed")

# AFTER (올바른 패턴)
if target_file.exists():
    result = validator.validate(target_file)
    if result.valid:
        return PhaseResult(phase, True, ...)
else:
    error_detail = output[:200] if output else "unknown"
    errors.append(f"File not created ({error_detail})")
```

---

## Bug #3: Daemon status writer loop condition

**발견일:** 2026-02-06
**심각도:** Medium (shutdown 시 thread가 안 멈춤)

### 원인
```python
# WRONG: or 조건 - stop_event가 set되어도 is_healthy()가 True면 계속 실행
while daemon.is_healthy() or not daemon._stop_event.is_set():

# CORRECT:
while not daemon._stop_event.is_set():
```

---

## Bug #4: Windows file lock on temp_path.replace()

**발견일:** 2026-02-06
**심각도:** Low (간헐적 실패, 다음 주기에 복구)

### 원인
UI(Electron)가 `daemon_status.json` 을 읽는 동안 `temp_path.replace(target)` 실행하면 `PermissionError`.

### 해결
```python
for attempt in range(3):
    try:
        temp_path.replace(target)
        break
    except PermissionError:
        if attempt < 2:
            time.sleep(0.1)
```
