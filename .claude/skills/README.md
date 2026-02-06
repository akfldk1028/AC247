# S3 Claude Skills & Auto-Claude Agents Guide

> AI가 새로운 Skills/Agents를 쉽게 추가할 수 있도록 하는 가이드

**반드시 먼저 읽기**: [BEST_PRACTICES.md](BEST_PRACTICES.md) - 공식 문서 기반 최적의 작성법

---

## 목차

1. [개요](#1-개요)
2. [Claude Skills 추가하기](#2-claude-skills-추가하기)
3. [Auto-Claude Custom Agents 추가하기](#3-auto-claude-custom-agents-추가하기)
4. [Skills + Agents 연동 패턴](#4-skills--agents-연동-패턴)
5. [기존 Skills/Agents 목록](#5-기존-skillsagents-목록)
6. [확장 아이디어](#6-확장-아이디어)

---

## 1. 개요

S3 프로젝트는 두 가지 AI 확장 시스템을 사용합니다:

| 시스템 | 위치 | 용도 |
|--------|------|------|
| **Claude Skills** | `.claude/skills/` | 사용자 명령어 (`/s3-build` 등) |
| **Auto-Claude Agents** | `Auto-Claude/apps/backend/custom_agents/` | 전문 AI 에이전트 |

### 차이점

- **Skills**: 사용자가 직접 호출하는 명령어. 간단한 워크플로우 자동화.
- **Agents**: 복잡한 작업을 수행하는 특화된 AI. Auto-Claude 파이프라인에서 사용.

### 시너지

```
사용자 → /s3-feature "기능" → Skill이 분석 → 적절한 Agent 호출
```

---

## 2. Claude Skills 추가하기

### Step 1: 폴더 생성

```powershell
# 새 스킬 폴더 생성
$skillName = "s3-newskill"
$basePath = "C:\DK\S3\S3\.claude\skills\$skillName"

New-Item -ItemType Directory -Force -Path "$basePath\scripts"
New-Item -ItemType Directory -Force -Path "$basePath\references"
```

### Step 2: SKILL.md 작성 (필수)

```markdown
---
name: s3-newskill
description: 스킬 설명 (10단어 이내)
---

# 스킬 제목

## 사용법
\`\`\`
/s3-newskill [옵션]
\`\`\`

## 옵션
- `option1` - 설명
- `option2` - 설명

## 프로세스

### Step 1: 첫 번째 단계
설명...

### Step 2: 두 번째 단계
설명...

## 명령어 예시
\`\`\`bash
# 실제 실행할 명령어들
\`\`\`

## 관련 Skills
- `/s3-build` - 빌드
- `/s3-test` - 테스트
```

### Step 3: 스크립트 추가 (선택)

`scripts/` 폴더에 자동화 스크립트 추가:

```powershell
# scripts/run.ps1
param([string]$Option = "default")

$ErrorActionPreference = "Stop"

switch ($Option) {
    "option1" { ... }
    "option2" { ... }
    default { ... }
}
```

### Step 4: 참조 문서 추가 (선택)

`references/` 폴더에 상세 문서:
- `troubleshooting.md` - 문제 해결
- `examples.md` - 사용 예시
- `api.md` - API 문서

### 완성된 구조

```
.claude/skills/s3-newskill/
├── SKILL.md           # 필수: 스킬 정의
├── scripts/
│   └── run.ps1        # 선택: 자동화 스크립트
└── references/
    └── guide.md       # 선택: 참조 문서
```

---

## 3. Auto-Claude Custom Agents 추가하기

### Step 1: config.json에 에이전트 추가

파일: `C:\DK\S3\S3\Auto-Claude\apps\backend\custom_agents\config.json`

```json
{
  "agents": {
    "기존 에이전트들...": {},

    "s3_new_agent": {
      "prompt_file": "s3_new_agent.md",
      "description": "새 에이전트 설명",
      "tools": [
        "Read", "Glob", "Grep",
        "Write", "Edit", "Bash",
        "WebFetch", "WebSearch"
      ],
      "mcp_servers": ["context7", "auto-claude"],
      "thinking_default": "medium"
    }
  }
}
```

### Step 2: 프롬프트 파일 생성

파일: `C:\DK\S3\S3\Auto-Claude\apps\backend\custom_agents\prompts\s3_new_agent.md`

```markdown
# S3 New Agent

당신은 S3 프로젝트의 [역할] 전문 에이전트입니다.

## 역할
- 주요 책임 1
- 주요 책임 2
- 주요 책임 3

## 기술 스택
- **언어**: Python, Dart
- **프레임워크**: Flutter, FastAPI
- **도구**: [관련 도구들]

## 작업 지침

### 1. 분석 단계
1. 요구사항 파악
2. 기존 코드 분석
3. 영향 범위 확인

### 2. 구현 단계
1. 필요한 파일 생성/수정
2. 테스트 작성
3. 문서화

### 3. 검증 단계
1. 코드 품질 확인
2. 테스트 실행
3. 리뷰 준비

## 코드 패턴

### 패턴 1: [이름]
\`\`\`dart
// 예시 코드
\`\`\`

### 패턴 2: [이름]
\`\`\`python
# 예시 코드
\`\`\`

## 주의사항
- 중요 사항 1
- 중요 사항 2

## 출력 형식
작업 완료 후 다음 형식으로 보고:
1. 수정된 파일 목록
2. 주요 변경사항
3. 다음 단계 제안
```

### Agent 설정 옵션

| 옵션 | 값 | 설명 |
|------|-----|------|
| `tools` | 배열 | 사용 가능한 도구 |
| `mcp_servers` | 배열 | MCP 서버 연결 |
| `thinking_default` | `none`/`low`/`medium`/`high`/`ultrathink` | 사고 수준 |

### 사용 가능한 Tools

```
기본 읽기: Read, Glob, Grep
기본 쓰기: Write, Edit, Bash
웹: WebFetch, WebSearch
```

### 사용 가능한 MCP Servers

```
context7     - 문서 검색
auto-claude  - 빌드 관리
graphiti     - 메모리 시스템
linear       - 프로젝트 관리
```

---

## 4. Skills + Agents 연동 패턴

### 패턴 A: Skill이 Agent 호출

```markdown
# SKILL.md에서

## Auto-Claude 연동

복잡한 작업은 전문 에이전트 활용:

\`\`\`bash
cd C:\DK\S3\S3\Auto-Claude\apps\backend
.venv\Scripts\python.exe run.py --task "[작업 내용]"
\`\`\`

### 추천 에이전트
| 작업 | 에이전트 |
|------|---------|
| 인증 구현 | s3_backend_auth |
| 데이터 처리 | s3_backend_data |
```

### 패턴 B: Skill 내 Python 스크립트로 연동

```python
# scripts/invoke_agent.py
import subprocess

def invoke_agent(agent_type: str, task: str):
    cmd = [
        "C:/DK/S3/S3/Auto-Claude/apps/backend/.venv/Scripts/python.exe",
        "C:/DK/S3/S3/Auto-Claude/apps/backend/run.py",
        "--agent", agent_type,
        "--task", task,
    ]
    return subprocess.run(cmd, capture_output=True, text=True)
```

### 패턴 C: Feature별 Agent 매핑

```
/s3-feature "인증" → s3_backend_auth + s3_frontend_auth
/s3-feature "데이터" → s3_backend_data + s3_frontend_data
/s3-feature "AI" → s3_ai_assistant + s3_ai_analyzer
```

---

## 5. 기존 Skills/Agents 목록

### Claude Skills (5개)

| 이름 | 명령어 | 용도 |
|------|--------|------|
| s3-auto-task | `/s3-auto-task "설명"` | Auto-Claude task 생성/빌드 |
| s3-build | `/s3-build [target]` | 빌드 자동화 |
| s3-test | `/s3-test [scope]` | 테스트 실행 |
| s3-feature | `/s3-feature "설명"` | 기능 개발 워크플로우 |
| s3-deploy | `/s3-deploy [target]` | 배포 자동화 |

### Auto-Claude Custom Agents (8개)

| 이름 | 설명 |
|------|------|
| s3_backend_auth | Backend 인증 (JWT, OAuth, Session) |
| s3_backend_data | Backend 데이터 (CRUD, Query, Cache) |
| s3_backend_notification | Backend 알림 (Push, Email, SMS) |
| s3_ai_assistant | AI 어시스턴트 (LLM 기반) |
| s3_ai_analyzer | AI 분석기 (데이터 분석, 요약) |
| s3_ai_recommender | AI 추천 시스템 |
| s3_frontend_auth | Frontend 인증 UI (Flutter) |
| s3_frontend_data | Frontend 데이터 동기화 (Flutter) |

---

## 6. 확장 아이디어

### 추가할 만한 Skills

| 이름 | 명령어 | 용도 |
|------|--------|------|
| s3-db | `/s3-db [action]` | DB 마이그레이션 관리 |
| s3-api | `/s3-api [action]` | API 문서 생성/검증 |
| s3-docs | `/s3-docs [target]` | 문서 자동 생성 |
| s3-lint | `/s3-lint [target]` | 코드 린트 및 포맷 |
| s3-perf | `/s3-perf [target]` | 성능 분석 |
| s3-security | `/s3-security` | 보안 스캔 |

### 추가할 만한 Agents

| 이름 | 용도 |
|------|------|
| s3_backend_cache | Redis/Memcached 캐싱 |
| s3_backend_queue | 메시지 큐 (RabbitMQ, Kafka) |
| s3_backend_file | 파일 업로드/스토리지 |
| s3_ai_vision | 이미지/비디오 분석 |
| s3_ai_voice | 음성 인식/합성 |
| s3_frontend_animation | 애니메이션 구현 |
| s3_frontend_chart | 차트/그래프 구현 |
| s3_devops_ci | CI/CD 파이프라인 |
| s3_devops_monitor | 모니터링/로깅 |

---

## 빠른 참조: 새 Skill/Agent 추가 체크리스트

### Skill 추가 체크리스트

- [ ] `.claude/skills/[name]/` 폴더 생성
- [ ] `SKILL.md` 작성 (frontmatter + 지침)
- [ ] (선택) `scripts/` 자동화 스크립트
- [ ] (선택) `references/` 참조 문서
- [ ] 이 README에 목록 추가

### Agent 추가 체크리스트

- [ ] `custom_agents/config.json`에 에이전트 추가
- [ ] `custom_agents/prompts/[name].md` 프롬프트 작성
- [ ] 이 README에 목록 추가
- [ ] (선택) 관련 Skill에서 연동 추가

---

## 파일 경로 요약

```
C:\DK\S3\S3\
├── .claude\
│   └── skills\                              # Claude Skills
│       ├── README.md                        # 이 파일
│       ├── s3-build\SKILL.md
│       ├── s3-test\SKILL.md
│       ├── s3-feature\SKILL.md
│       └── s3-deploy\SKILL.md
│
└── Auto-Claude\apps\backend\
    └── custom_agents\                       # Auto-Claude Agents
        ├── config.json                      # 에이전트 설정
        └── prompts\                         # 에이전트 프롬프트
            ├── s3_backend_auth.md
            ├── s3_backend_data.md
            ├── s3_backend_notification.md
            ├── s3_ai_assistant.md
            ├── s3_ai_analyzer.md
            ├── s3_ai_recommender.md
            ├── s3_frontend_auth.md
            └── s3_frontend_data.md
```

---

*이 문서는 AI가 S3 프로젝트를 확장할 때 참조하는 가이드입니다.*
*새 Skill이나 Agent 추가 시 이 문서도 함께 업데이트해주세요.*
