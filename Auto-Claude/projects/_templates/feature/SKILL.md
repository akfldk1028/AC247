---
name: {SKILL_PREFIX}-feature
description: |
  {PROJECT_NAME} 새 기능 개발 워크플로우. Feature-First 구조로 파일 생성, Freezed 모델, Riverpod 상태관리 포함.
  사용 시점: (1) 새 기능 추가 시, (2) 새 화면 개발 시, (3) API 연동 기능 구현 시
  사용 금지: 기존 기능 수정, 단순 UI 수정, 버그 수정, 리팩토링
argument-hint: "[기능 설명]"
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# {PROJECT_NAME} Feature Development Skill

Feature-First 아키텍처로 새 기능을 개발합니다.

## When to Use
- 새로운 화면/기능 추가할 때
- CRUD 기능 구현 시
- API 연동이 필요한 기능 개발 시

## When NOT to Use
- 기존 기능 수정 → 직접 파일 수정
- 단순 UI 수정 → 직접 위젯 수정
- 버그 수정 → 해당 파일 직접 수정

## Quick Start
```bash
/{SKILL_PREFIX}-feature "기능 설명"
```

## 워크플로우

### Phase 1: 요구사항 분석
1. 기능 범위 파악
2. 필요한 데이터 모델 설계
3. 화면 구조 설계

### Phase 2: 파일 구조 생성

#### Flutter Feature-First Architecture
```
{PROJECT_DIR}/lib/features/[feature_name]/
├── models/
│   └── [feature]_model.dart          # Freezed 모델
├── mutations/
│   └── [action]_mutation.dart        # POST/PUT/DELETE
├── queries/
│   └── get_[data]_query.dart         # GET 요청
└── pages/
    ├── providers/
    │   └── [feature]_provider.dart   # Riverpod 상태
    ├── screens/
    │   └── [feature]_screen.dart     # 화면 위젯
    └── widgets/
        └── [component].dart          # 재사용 위젯
```

### Phase 3: 코드 생성
1. Freezed 모델 생성
2. Riverpod provider 생성
3. UI 컴포넌트 (Shadcn UI)

### Phase 4: Auto-Claude 연동

복잡한 기능은 전문 에이전트 활용:

| 작업 | 에이전트 |
|------|---------|
| (프로젝트에 맞게 채우기) | `{SKILL_PREFIX}_agent_name` |

## 코드 생성 후

파일 생성 후 반드시 실행:
```bash
cd {PROJECT_DIR}
dart run build_runner build --delete-conflicting-outputs
```

## 관련 Skills

- `/{SKILL_PREFIX}-build` - 빌드 실행
- `/{SKILL_PREFIX}-test` - 테스트 실행

## Auto-Claude Spec 생성

대규모 기능 개발 시 Auto-Claude spec 생성:
```bash
cd {CLONE_DIR}/apps/backend
PYTHONUTF8=1 USE_CLAUDE_MD=true .venv\Scripts\python.exe runners\spec_runner.py \
  --project-dir "{PROJECT_DIR}" \
  --task "[기능 설명]"
```
