# Auto-Claude Skill Templates

> **새 프로젝트의 스킬을 만들 때 이 템플릿을 사용하라.**
> Placeholder를 프로젝트 값으로 치환하면 바로 사용 가능.

---

## Placeholder 변수

| Placeholder | 설명 | 예시 (GMA) | 예시 (S3) |
|-------------|------|------------|-----------|
| `{PROJECT_NAME}` | 프로젝트 이름 | `GMA` | `S3` |
| `{SKILL_PREFIX}` | 스킬 접두사 (소문자) | `gma` | `s3` |
| `{PROJECT_DIR}` | Flutter 앱 경로 | `C:\DK\GMA\frontend` | `C:\DK\S3\frontend` |
| `{CLONE_DIR}` | AC247 clone 경로 | `C:\DK\GMA\clone\AC247\Auto-Claude` | `C:\DK\S3\clone\Auto-Claude` |
| `{FLUTTER_CMD}` | Flutter 명령어 | `flutter` | `C:\DK\flutter\bin\flutter.bat` |

---

## 템플릿 목록

| 폴더 | 스킬 | 용도 |
|------|------|------|
| `build/` | `{SKILL_PREFIX}-build` | 빌드 자동화 (pub get, build_runner, web/apk) |
| `test/` | `{SKILL_PREFIX}-test` | 테스트 실행 (unit/widget/integration) |
| `feature/` | `{SKILL_PREFIX}-feature` | Feature-First 개발 워크플로우 |
| `auto-task/` | `{SKILL_PREFIX}-auto-task` | Auto-Claude task 생성 + 자동 빌드 |

---

## 사용법

### 1. 디렉토리 생성

```bash
mkdir -p C:\DK\{PROJECT_NAME}\.claude\skills
```

### 2. 템플릿 복사 + Placeholder 치환

```bash
# 예: build 스킬
cp -r _templates/build/ C:\DK\{PROJECT_NAME}\.claude\skills\{SKILL_PREFIX}-build/

# SKILL.md, scripts/, references/ 에서 placeholder 치환
# sed 또는 IDE의 Find & Replace 사용
```

### 3. 프로젝트 특화 내용 추가

- 기술스택 테이블 업데이트 (feature SKILL.md)
- 커스텀 에이전트 목록 업데이트 (feature scripts/invoke_autoclaude.py)
- feature_templates.md에 프로젝트 특화 모델 예시 추가

### 4. ac-* 공통 스킬 복사

```bash
# AC247 엔진에서 복사 (변경 없이 그대로)
cp -r AC247/.claude/skills/ac-debug/     C:\DK\{PROJECT_NAME}\.claude\skills\
cp -r AC247/.claude/skills/ac-explore/   C:\DK\{PROJECT_NAME}\.claude\skills\
cp -r AC247/.claude/skills/ac-pipeline-test/ C:\DK\{PROJECT_NAME}\.claude\skills\
cp AC247/.claude/skills/BEST_PRACTICES.md C:\DK\{PROJECT_NAME}\.claude\skills\
```

---

## 실제 어댑트 사례

### GMA (2026-02-10)

| 원본 | 변경 사항 |
|------|----------|
| `{PROJECT_DIR}` | `C:\DK\GMA\frontend` |
| `{CLONE_DIR}` | `C:\DK\GMA\clone\AC247\Auto-Claude` |
| `{FLUTTER_CMD}` | `flutter` (PATH에 있음) |
| feature 기술스택 | pdfrx, Hive, markdown, flutter_math_fork 추가 |
| feature 에이전트 | gma_pdf_viewer, gma_note_editor 등 |

### S3 (원본)

| 원본 | 값 |
|------|---|
| `{PROJECT_DIR}` | `C:\DK\S3\frontend` |
| `{CLONE_DIR}` | `C:\DK\S3\clone\Auto-Claude` |
| `{FLUTTER_CMD}` | `C:\DK\flutter\bin\flutter.bat` |
| feature 기술스택 | Supabase, Hono, Dio |
| feature 에이전트 | s3_backend_auth, s3_edge_api 등 |

---

*템플릿 원본은 S3 프로젝트 스킬을 기반으로 일반화한 것입니다.*
*프로젝트별 실제 스킬은 `_archived/` 또는 각 프로젝트의 `.claude/skills/`를 참조하세요.*
