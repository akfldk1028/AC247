# Auto-Claude Engine Skills Guide

> AC247 엔진 공통 스킬. 프로젝트별 스킬은 각 프로젝트의 `.claude/skills/`에 있습니다.

**반드시 먼저 읽기**: [BEST_PRACTICES.md](BEST_PRACTICES.md)

---

## !! 핵심 규칙: 프로젝트 단위 스킬 관리 !!

> **절대로 이 디렉토리(AC247 엔진)에 프로젝트 전용 스킬을 넣지 마라.**
> **프로젝트 전용 스킬은 반드시 해당 프로젝트 루트의 `.claude/skills/`에서 관리한다.**

| 규칙 | 설명 |
|------|------|
| **AC247 엔진** (`AC247/.claude/skills/`) | `ac-*` 공통 스킬 **만** 보관. 프로젝트 전용 스킬 금지. |
| **AC247 clone** (`clone/AC247/.claude/skills/`) | `ac-*` 공통 스킬 **만** 보관. 프로젝트 전용 스킬 금지. |
| **프로젝트 루트** (`C:\DK\{프로젝트}\.claude\skills\`) | 해당 프로젝트 전용 스킬 + `ac-*` 복사본 보관. |

### 왜 프로젝트 단위인가?

1. **격리**: GMA 스킬이 S3에 딸려오는 문제 방지
2. **자율성**: 각 프로젝트가 독립적으로 스킬 추가/삭제 가능
3. **명확성**: 프로젝트 디렉토리에서 Claude Code 실행 시 해당 프로젝트 스킬만 보임
4. **확장성**: 새 프로젝트 추가 시 엔진 수정 불필요

### 현재 프로젝트별 스킬 위치

| 프로젝트 | 스킬 위치 | 내용 |
|----------|----------|------|
| **GMA** | `C:\DK\GMA\.claude\skills\` | `gma-build`, `gma-test`, `gma-feature`, `gma-auto-task` + `ac-*` |
| **S3** | `C:\DK\S3\.claude\skills\` | `s3-build`, `s3-test`, `s3-feature`, `s3-auto-task` 등 + `ac-*` |

---

## 1. 구조

### 프로젝트별 스킬 분리

| 위치 | 내용 |
|------|------|
| **여기** (`AC247/.claude/skills/`) | 엔진 공통: `ac-debug`, `ac-explore`, `ac-pipeline-test` |
| `C:\DK\GMA\.claude\skills\` | GMA 전용: `gma-build`, `gma-test`, `gma-feature`, `gma-auto-task` |
| `C:\DK\S3\.claude\skills\` | S3 전용: `s3-build`, `s3-test`, `s3-feature`, `s3-auto-task` 등 |

### 프로젝트 메타데이터

프로젝트별 설정은 `Auto-Claude/projects/` 에서 관리:

```
Auto-Claude/projects/
├── GMA/
│   ├── project.json          # 프로젝트 경로, 기술스택, 환경변수
│   └── custom_agents/
│       └── config.json       # GMA 전용 에이전트
└── S3/
    ├── project.json
    └── custom_agents/
        └── config.json       # S3 전용 에이전트
```

---

## 2. 엔진 공통 Skills (3개)

| 이름 | 명령어 | 용도 |
|------|--------|------|
| ac-debug | `/ac-debug [증상]` | 파이프라인 디버깅 |
| ac-explore | (자동) | 코드베이스 탐색 (백그라운드) |
| ac-pipeline-test | `/ac-pipeline-test` | E2E 파이프라인 테스트 |

이 스킬들은 **프로젝트 무관**으로 어디서든 동작합니다.

---

## 3. 새 프로젝트 추가하기

### Step 1: projects/ 폴더 생성

```bash
mkdir -p Auto-Claude/projects/NEW_PROJECT/custom_agents
```

### Step 2: project.json 작성

```json
{
  "name": "NEW_PROJECT",
  "project_dir": "C:\\DK\\NEW_PROJECT\\frontend",
  "description": "프로젝트 설명",
  "framework": "Flutter",
  "skills_dir": "C:\\DK\\NEW_PROJECT\\.claude\\skills",
  "env_vars": {
    "PYTHONUTF8": "1",
    "USE_CLAUDE_MD": "true"
  }
}
```

### Step 3: 프로젝트 스킬 생성

```bash
mkdir -p C:\DK\NEW_PROJECT\.claude\skills
# GMA 또는 S3의 스킬을 복사하여 adapt
```

### Step 4: Clone 동기화

```bash
# 프로젝트의 AC247 clone에 동기화
cp -r Auto-Claude/projects/NEW_PROJECT path/to/clone/Auto-Claude/projects/
```

---

## 4. Daemon 실행

각 프로젝트에서 daemon 실행 시:

```bash
cd [clone]/Auto-Claude/apps/backend
PYTHONUTF8=1 USE_CLAUDE_MD=true .venv/Scripts/python.exe runners/daemon_runner.py \
  --project-dir "[project-dir]" \
  --status-file "[project-dir]/.auto-claude/daemon_status.json"
```

### 현재 등록된 프로젝트

| 프로젝트 | project_dir | clone |
|----------|-------------|-------|
| **GMA** | `C:\DK\GMA\frontend` | `C:\DK\GMA\clone\AC247\Auto-Claude` |
| **S3** | `C:\DK\S3\frontend` | `C:\DK\S3\clone\Auto-Claude` |

---

*프로젝트별 스킬은 각 프로젝트의 `.claude/skills/README.md`를 참조하세요.*
