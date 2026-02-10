# Auto-Claude 프로젝트 관리 가이드

> **새 프로젝트를 AC247에 연결할 때 반드시 이 문서를 읽어라.**
> 이전 프로젝트(GMA, S3)의 시행착오를 모두 반영한 가이드.

---

## 1. 핵심 규칙: 프로젝트 단위 관리

> **프로젝트 전용 스킬/에이전트는 반드시 해당 프로젝트 루트에서 관리한다.**
> **AC247 엔진에 프로젝트 전용 파일을 절대 넣지 않는다.**

```
✅ 올바른 구조:
C:\DK\{프로젝트}\
├── .claude\skills\           ← 프로젝트 전용 스킬 (여기!)
│   ├── {proj}-build/
│   ├── {proj}-test/
│   ├── {proj}-feature/
│   ├── {proj}-auto-task/
│   └── ac-*/                ← 엔진 공통 스킬 (복사)
├── frontend\                ← 앱 코드
└── clone\AC247\Auto-Claude\ ← AC247 엔진 clone
    └── .claude\skills\      ← ac-* 공통만. 프로젝트 스킬 금지!

❌ 잘못된 구조:
clone\AC247\.claude\skills\s3-build\   ← S3 스킬이 엔진에 있으면 안됨
clone\AC247\.claude\skills\gma-build\  ← GMA 스킬도 마찬가지
```

### 왜 프로젝트 단위인가?
1. **격리** — A 프로젝트 스킬이 B 프로젝트에 딸려오는 문제 방지
2. **자율성** — 각 프로젝트가 독립적으로 스킬 관리
3. **명확성** — Claude Code 실행 시 해당 프로젝트 스킬만 보임
4. **확장성** — 새 프로젝트 추가 시 엔진 수정 불필요

---

## 2. 새 프로젝트 추가 체크리스트

### Step 1: project.json 생성

```bash
mkdir -p Auto-Claude/projects/{PROJECT_NAME}/custom_agents
```

```json
{
  "name": "{PROJECT_NAME}",
  "project_dir": "C:\\DK\\{PROJECT_NAME}\\frontend",
  "description": "프로젝트 설명",
  "framework": "Flutter",
  "skills_dir": "C:\\DK\\{PROJECT_NAME}\\.claude\\skills",
  "clone_dir": "C:\\DK\\{PROJECT_NAME}\\clone\\AC247\\Auto-Claude",
  "env_vars": {
    "PYTHONUTF8": "1",
    "USE_CLAUDE_MD": "true"
  }
}
```

### Step 2: 프로젝트 스킬 생성

```bash
mkdir -p C:\DK\{PROJECT_NAME}\.claude\skills
```

- `_templates/` 폴더의 템플릿을 복사하여 adapt
- `{PROJECT_NAME}`, `{PROJECT_DIR}`, `{CLONE_DIR}` placeholder 치환
- `ac-*` 공통 스킬도 복사

### Step 3: AC247 clone 설정

```bash
# 프로젝트 디렉토리에 AC247 clone
git clone <ac247-repo> C:\DK\{PROJECT_NAME}\clone\AC247

# projects/ 동기화
cp -r Auto-Claude/projects/{PROJECT_NAME} clone/Auto-Claude/projects/
```

### Step 4: CLAUDE.md 작성

프로젝트 루트 또는 frontend/에 `CLAUDE.md` 작성:
- 프로젝트 요약, 기술스택, 참조 코드 경로
- **에이전트가 이 파일을 읽어야 프로젝트를 이해함**

### Step 5: 데몬 실행

아래 §3의 필수 사항을 모두 확인한 후:
```bash
cd C:\DK\{PROJECT_NAME}\clone\AC247\Auto-Claude\apps\backend
PYTHONUTF8=1 USE_CLAUDE_MD=true .venv/Scripts/python.exe runners/daemon_runner.py \
  --project-dir "C:\DK\{PROJECT_NAME}\frontend" \
  --status-file "C:\DK\{PROJECT_NAME}\frontend\.auto-claude\daemon_status.json"
```

---

## 3. 데몬 실행 필수 사항 & 시행착오 교훈

> **아래 내용은 GMA, S3 프로젝트에서 실제로 겪은 문제들이다. 새 프로젝트에서 반복하지 마라.**

### 필수 환경변수

| 변수 | 값 | 빠뜨리면? |
|------|-----|----------|
| `PYTHONUTF8` | `1` | Windows에서 한글 깨짐, JSON 파싱 에러 |
| `USE_CLAUDE_MD` | `true` | 에이전트가 CLAUDE.md 못 읽음 → 참조 레포 경로 모름 → 엉뚱한 코드 생성 |

### Bug #1: Stale spec_dir after rename (Critical)

**증상:** `Agent did not create spec.md` 3회 retry 후 실패
**원인:** `orchestrator.py`가 spec_dir을 rename하지만 PhaseExecutor/SpecValidator가 옛 경로 참조
**교훈:** spec_dir 변경 시 **모든 참조 객체** 동기화 필수
**파일:** `spec/pipeline/orchestrator.py` → `_rename_spec_dir_from_requirements()` 직후 sync 코드

### Bug #2: File-exists-but-success=False (High)

**증상:** Agent가 파일 만들었는데 phase가 실패 보고
**원인:** SDK exception이 agent 작업 완료 후 발생 (rate limit, timeout)
**교훈:** `if not success` 대신 **파일 존재 여부 먼저 체크**

### Bug #3: MCP tool permissions 누락 (High)

**증상:** 에이전트가 auto-claude MCP 도구 사용 불가
**원인:** `create_client()`가 `.claude_settings.json` 생성 시 auto-claude MCP 도구 permissions 누락
**교훈:** `client.py`에서 모든 MCP 서버의 permissions 추출 확인

### Bug #4: SpecFactory comma-separated strings (Medium)

**증상:** acceptance_criteria가 단일 문자열로 저장
**원인:** MCP agent가 JSON 배열이 아닌 comma-separated string 전달
**교훈:** 입력 정규화 함수 필수 (`_normalize_list_field`)

### Bug #5: CLAUDE.md disabled for agents

**증상:** 에이전트가 프로젝트 구조를 전혀 이해 못함
**원인:** `should_use_claude_md()`가 환경변수만 읽음, `.auto-claude/.env` 안 읽음
**교훈:** **반드시 `USE_CLAUDE_MD=true` 환경변수로 전달**

### Rate Limit 교훈

**증상:** 3 concurrent 실행 → rate limit → 빈 세션 무한루프 (toolCount:0, ~1초)
**대응:** rate limit 발생 시 `--max-concurrent 1`로 축소
**예방:** 처음에는 1-2개로 시작, 안정되면 증가

### Daemon Task Queueing

- **pickup 조건:** status가 `queue`/`backlog`/`queued`여야 함
- **pickup 안되는 status:** `in_progress`, `ai_review`, `human_review`, `done`, `complete`
- **re-queue 방법:** `status → "queue"`, `xstateState → "backlog"`
- **Electron UI 주의:** UI가 status를 되돌릴 수 있음 → `sed -i`로 직접 수정

### .claude_settings.json 덮어쓰기

- `create_client()`가 **매 세션마다** `.claude_settings.json`을 새로 생성
- 수동으로 편집한 permissions는 다음 세션에 사라짐
- 해결: `client.py`의 permissions 로직 자체를 수정

---

## 4. 스킬 어댑트 가이드

### 템플릿 사용법

`_templates/` 폴더에 프로젝트 무관 스킬 템플릿이 있습니다:

```
_templates/
├── README.md              # 템플릿 사용법
├── build/SKILL.md         # 빌드 스킬 템플릿
├── test/SKILL.md          # 테스트 스킬 템플릿
├── feature/SKILL.md       # feature 개발 템플릿
└── auto-task/SKILL.md     # auto-task 템플릿
```

### 어댑트 절차

1. `_templates/{skill}/` 복사 → `프로젝트/.claude/skills/{proj}-{skill}/`
2. Placeholder 치환:
   - `{PROJECT_NAME}` → 프로젝트 이름 (GMA, S3 등)
   - `{PROJECT_DIR}` → 프로젝트 앱 경로 (`C:\DK\GMA\frontend`)
   - `{CLONE_DIR}` → AC247 clone 경로 (`C:\DK\GMA\clone\AC247\Auto-Claude`)
   - `{SKILL_PREFIX}` → 스킬 접두사 (`gma`, `s3`)
3. 프로젝트 기술스택에 맞게 내용 수정
4. `ac-*` 공통 스킬도 복사

### 실제 예시 참조

| 프로젝트 | 스킬 위치 | 참고용 |
|----------|----------|--------|
| GMA | `C:\DK\GMA\.claude\skills\` | Flutter + pdfrx + Hive |
| S3 | `C:\DK\S3\.claude\skills\` | Flutter + Supabase + Hono |

---

## 5. 현재 등록된 프로젝트

| 프로젝트 | project_dir | clone | 스킬 |
|----------|-------------|-------|------|
| **GMA** | `C:\DK\GMA\frontend` | `C:\DK\GMA\clone\AC247\Auto-Claude` | `gma-*` (4) + `ac-*` (3) |
| **S3** | `C:\DK\S3\frontend` | `C:\DK\S3\clone\Auto-Claude` | `s3-*` (8) + `ac-*` (3) |

---

*이 문서는 AC247 엔진 레벨. 프로젝트별 상세는 각 프로젝트의 `.claude/skills/README.md` 참조.*
