---
name: {SKILL_PREFIX}-auto-task
description: |
  Auto-Claude로 task 생성 및 자동 빌드. Kanban 카드 자동 이동.
  사용 시점: (1) 새 기능 개발 시작, (2) 버그 수정 요청, (3) 24/7 자동 빌드
  사용 금지: 1줄 수정, 단순 리팩토링, UI만 테스트할 때
argument-hint: "[task-description] [--project path] [--auto-approve]"
allowed-tools: Read, Grep, Glob, Bash, Write
---

# {PROJECT_NAME} Auto-Task Skill

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
        └── implementation_plan.json에 status 자동 저장 ← CLI-only 지원
        │
        ▼
    [UI 실행 중일 때]
    Electron Main Process → IPC → Renderer → Kanban UI 카드 이동
```

## When to Use
- 새 기능을 Auto-Claude로 자동 개발할 때
- 버그 수정을 자동화하고 싶을 때
- 24/7 자동 빌드 파이프라인 구축 시

## When NOT to Use
- 간단한 1줄 수정 → 직접 수정이 빠름
- 복잡한 아키텍처 설계 필요 → 먼저 설계 후 사용

## Quick Start
```bash
/{SKILL_PREFIX}-auto-task "Add feature X"
/{SKILL_PREFIX}-auto-task "Fix bug Y" --no-build
```

## Usage
```
/{SKILL_PREFIX}-auto-task [task-description] [options]
```

### Options

| 옵션 | 설명 |
|------|------|
| `--project <path>` | 프로젝트 경로 (기본: {PROJECT_DIR}) |
| `--no-build` | Task만 생성, 빌드 안 함 |
| `--auto-approve` | Review checkpoint 자동 승인 |

## Complete Workflow

### Step 1: Task 생성
```bash
cd {CLONE_DIR}/apps/backend
PYTHONUTF8=1 USE_CLAUDE_MD=true .venv/Scripts/python.exe runners/spec_runner.py \
  --project-dir "{PROJECT_DIR}" \
  --task "task description" \
  --auto-approve
```

### Step 2: 자동 빌드 실행
```bash
PYTHONUTF8=1 USE_CLAUDE_MD=true .venv/Scripts/python.exe run.py \
  --project-dir "{PROJECT_DIR}" \
  --spec [spec-id] \
  --force --auto-continue
```

### Step 3: QA 검증
```bash
PYTHONUTF8=1 USE_CLAUDE_MD=true .venv/Scripts/python.exe run.py \
  --project-dir "{PROJECT_DIR}" \
  --spec [spec-id] \
  --qa
```

## Daemon 실행 (24/7)

```bash
cd {CLONE_DIR}/apps/backend
PYTHONUTF8=1 USE_CLAUDE_MD=true .venv/Scripts/python.exe runners/daemon_runner.py \
  --project-dir "{PROJECT_DIR}" \
  --status-file "{PROJECT_DIR}/.auto-claude/daemon_status.json"
```

## 필수 환경변수

| 변수 | 값 | 빠뜨리면? |
|------|-----|----------|
| `PYTHONUTF8` | `1` | Windows에서 한글 깨짐, JSON 파싱 에러 |
| `USE_CLAUDE_MD` | `true` | 에이전트가 CLAUDE.md 못 읽음 → 프로젝트 이해 불가 |

## Troubleshooting

### 카드가 안 움직임
- UI 실행 확인
- implementation_plan.json의 status/xstateState 확인
- UI refresh (F5)

### 빌드가 멈춤
- `--auto-approve` 플래그 사용

### QA 무한 루프
- `QA_FIX_REQUEST.md` 확인
- 수동으로 이슈 해결 후 QA 재실행

## Related Skills
- `/{SKILL_PREFIX}-build` - 빌드
- `/{SKILL_PREFIX}-test` - 테스트
- `/{SKILL_PREFIX}-feature` - Feature-First 개발

## References
- [Status Sync Guide](references/status-sync.md)
