# Design Task Template

Design task를 사용하면 대형 프로젝트를 자동으로 분해해서 **병렬 실행**할 수 있습니다.

## Quick Start

1. `.auto-claude/specs/` 폴더에 새 spec 폴더 생성
2. 아래 4개 파일 복사
3. UI에서 task 시작 (또는 daemon이 자동 감지)

## 필수 파일 (4개)

### 1. spec.md
```markdown
# [프로젝트 이름]

## Overview
[프로젝트 설명]

## Requirements
1. [기능 1]
2. [기능 2]
3. [기능 3]

## Technical Constraints
- [기술 제약 사항]
```

### 2. requirements.json
```json
{
  "task": "[프로젝트 이름]",
  "description": "[간단한 설명]",
  "acceptance_criteria": [
    "[완료 조건 1]",
    "[완료 조건 2]"
  ]
}
```

### 3. implementation_plan.json (핵심!)
```json
{
  "status": "queue",
  "planStatus": "queue",
  "xstateState": "backlog",
  "executionPhase": "backlog",
  "taskType": "design",
  "priority": 0
}
```

**중요: `"taskType": "design"`이 핵심입니다!**

### 4. context.json
```json
{
  "task_description": "[프로젝트 이름]",
  "project_type": "greenfield",
  "files_to_create": [],
  "files_to_modify": [],
  "patterns": {},
  "existing_implementations": {},
  "created_at": "2026-01-01T00:00:00Z"
}
```

## 폴더 구조 예시

```
.auto-claude/specs/
└── 001-shopping-app-design/
    ├── spec.md
    ├── requirements.json
    ├── implementation_plan.json    ← taskType: "design"
    └── context.json
```

## 실행 후 결과

Design agent가 `create_batch_child_specs` 도구를 호출해서 child spec을 자동 생성합니다:

```
.auto-claude/specs/
├── 001-shopping-app-design/       (부모 - 완료됨)
├── 002-database-schema/           (자식 - 자동 생성됨)
├── 003-backend-api/               (자식 - 자동 생성됨)
├── 004-frontend-ui/               (자식 - 자동 생성됨)
└── 005-integration-tests/         (자식 - 자동 생성됨)
```

## 전체 자동화 흐름

```
Design Task 생성
    ↓
Task Daemon 감지 → run.py 실행 (worktree isolated)
    ↓
Planner Agent (design_architect.md 프롬프트)
    ↓
create_batch_child_specs 도구 호출
    ↓
SpecFactory: child specs 생성 (원본 프로젝트 dir에!)
    + 2-pass 의존성 해결 (내부 1-based index → 실제 spec ID)
    ↓
coder.py: 디스크 스캔으로 child spec 감지 → parent "complete"
    + worktree plan + 원본 plan 양쪽 업데이트
    ↓
Daemon: "complete" 보존 → child specs pick up
    ↓
각 Child Spec 실행 (의존성 순서):
    Planner → Coder → QA Reviewer → QA Fixer
```

## ⚠️ 주의사항 및 알려진 함정 (CRITICAL!)

### 1. taskType은 반드시 "design"
- `"taskType": "design"` 또는 `"taskType": "architecture"` 필수
- 이것이 없으면 일반 task로 처리되어 plan validation에서 실패

### 2. phases와 subtasks는 반드시 빈 배열
- design task는 child specs를 생성하지, phases/subtasks를 만들지 않음
- `"phases": []`, `"subtasks": []` 로 설정
- phases에 뭔가 있으면 일반 task의 validation 로직을 탐

### 3. status는 반드시 "queue"
- `"status": "queue"` 여야 daemon이 pick up 함
- "in_progress", "complete", "error" 등은 daemon이 무시

### 4. depends_on은 1-based batch index 사용
- Agent가 create_batch_child_specs를 호출할 때
- `"depends_on": ["1", "2"]` → batch 배열의 1번째, 2번째 spec
- 실제 spec ID (예: "002-xxx")가 아님!
- SpecFactory가 2-pass로 자동 변환

### 5. 프로젝트는 git repo여야 함 (worktree 사용 시)
- `--auto-continue` 모드는 ISOLATED (worktree) 사용
- git init 되지 않은 프로젝트에서는 worktree 생성 실패 가능
- 실패 시 DIRECT 모드로 fallback됨

### 6. Child spec depth = 최대 2 (설정 가능)
- 기본값: 2단계 (root → child → grandchild 허용)
- `AUTO_CLAUDE_MAX_CHILD_DEPTH` 환경변수로 조정 가능
- depth guard가 parentTask 체인을 따라 올라가며 계산
- depth >= 2에서는 design/architecture 타입 생성 불가 (무한 분해 방지)

### 7. MCP tool 접근은 run.py에서만 가능
- Claude CLI 직접 실행으로는 MCP tool 접근 불가
- design task는 반드시 run.py를 통해 실행됨 (AGENT_REGISTRY 설정)

### 8. Worktree와 원본 경로 분리
- 실행 시 worktree 안에서 동작하므로 spec_dir이 worktree 경로
- Child specs는 `_get_original_project_dir()`로 원본에 생성됨
- Parent plan 업데이트는 coder.py에서 원본 dir에도 직접 write

## Task Type 참고

| taskType | 용도 | 실행 방식 |
|----------|------|----------|
| `design` | 프로젝트 분해, child spec 생성 | run.py (MCP tools) |
| `architecture` | 아키텍처 분석/설계 | run.py (MCP tools) |
| `impl` | 일반 구현 | run.py (Auto-Claude) |
| `frontend` | 프론트엔드 개발 | run.py + puppeteer |
| `backend` | 백엔드 개발 | run.py + context7 |
| `test` | 테스트 작성 | run.py |

## Priority 참고

| Priority | 값 | 용도 |
|----------|-----|------|
| CRITICAL | 0 | design, architecture (먼저 실행) |
| HIGH | 1 | 핵심 기능 |
| NORMAL | 2 | 일반 기능 |
| LOW | 3 | 문서, 정리 |

## 핵심 파일 위치

| 파일 | 역할 |
|------|------|
| `agents/coder.py` | Main loop: design task 감지, plan validation 스킵, 디스크 스캔 |
| `agents/tools_pkg/tools/subtask.py` | MCP tool: create_batch_child_specs, create_child_spec |
| `agents/tools_pkg/models.py` | planner에 MCP 도구 권한 부여 |
| `services/spec_factory.py` | Child spec 폴더 생성 + 2-pass 의존성 해결 |
| `prompts/design_architect.md` | Design agent 시스템 프롬프트 |
| `prompts_pkg/prompt_generator.py` | taskType="design" → design_architect.md 선택 |
| `prompts_pkg/prompts.py` | is_first_run(): design task 완료 감지 |
| `services/task_daemon/__init__.py` | Daemon: "complete" 보존, child specs pick up |

## 예시: E-Commerce App

```
# spec.md
# E-Commerce Mobile App

## Overview
Build a complete e-commerce mobile app with Flutter.

## Requirements
1. User authentication (login, register, password reset)
2. Product catalog with search and filters
3. Shopping cart with real-time sync
4. Checkout with payment integration
5. Order history and tracking

## Technical Stack
- Flutter 3.x
- Firebase Authentication
- Firestore for data
- Stripe for payments
```

```json
// implementation_plan.json
{
  "status": "queue",
  "planStatus": "queue",
  "xstateState": "backlog",
  "executionPhase": "backlog",
  "taskType": "design",
  "priority": 0
}
```

Design agent가 자동으로 다음과 같이 분해합니다:
- 002-firebase-auth (priority: 0, type: backend)
- 003-product-catalog (priority: 1, depends: [002])
- 004-shopping-cart (priority: 1, depends: [002])
- 005-checkout-flow (priority: 2, depends: [003, 004])
- 006-order-tracking (priority: 2, depends: [005])
