# S3 Custom Agents for Auto-Claude

> AI가 새로운 에이전트를 쉽게 추가할 수 있도록 하는 가이드

---

## 개요

이 폴더는 S3 프로젝트 전용 커스텀 에이전트를 정의합니다.
`config.json`과 `prompts/*.md` 파일로 구성되며, Auto-Claude 시작 시 자동 로드됩니다.

---

## 폴더 구조

```
custom_agents/
├── README.md           # 이 파일
├── config.json         # 에이전트 설정 (필수)
└── prompts/            # 에이전트 프롬프트들
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

## 새 에이전트 추가 방법

### Step 1: config.json 수정

```json
{
  "agents": {
    "s3_new_agent": {
      "prompt_file": "s3_new_agent.md",
      "description": "에이전트 설명",
      "tools": ["Read", "Glob", "Grep", "Write", "Edit", "Bash", "WebFetch", "WebSearch"],
      "mcp_servers": ["context7", "auto-claude"],
      "thinking_default": "medium"
    }
  }
}
```

### Step 2: prompts/s3_new_agent.md 생성

```markdown
# S3 [Name] Agent

당신은 S3 프로젝트의 [역할] 전문 에이전트입니다.

## 역할
- 역할 1
- 역할 2

## 기술 스택
| 기술 | 용도 |
|------|------|
| Flutter | 프론트엔드 |
| Python | 백엔드 |

## 작업 지침

### 분석
1. 요구사항 파악
2. 기존 코드 분석

### 구현
1. 코드 작성
2. 테스트 작성

### 검증
1. 테스트 실행
2. 리뷰 준비

## 코드 패턴

\`\`\`dart
// Flutter 예시
\`\`\`

\`\`\`python
# Python 예시
\`\`\`

## 주의사항
- 주의 1
- 주의 2
```

---

## config.json 설정 상세

### 필수 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `prompt_file` | string | prompts/ 폴더 내 .md 파일명 |
| `description` | string | 에이전트 설명 |
| `tools` | array | 사용 가능한 도구 목록 |
| `mcp_servers` | array | MCP 서버 연결 |
| `thinking_default` | string | 사고 수준 |

### thinking_default 옵션

| 값 | 설명 | 용도 |
|-----|------|------|
| `none` | 사고 없음 | 단순 작업 |
| `low` | 낮음 | 간단한 분석 |
| `medium` | 중간 (기본) | 일반 작업 |
| `high` | 높음 | 복잡한 분석 |
| `ultrathink` | 최대 | 매우 복잡한 결정 |

### 사용 가능한 Tools

```
# 읽기 전용
Read        - 파일 읽기
Glob        - 파일 패턴 검색
Grep        - 내용 검색

# 쓰기 가능
Write       - 파일 생성
Edit        - 파일 수정
Bash        - 명령 실행

# 웹
WebFetch    - URL 내용 가져오기
WebSearch   - 웹 검색
```

### 사용 가능한 MCP Servers

```
context7     - 문서 검색 (docs lookup)
auto-claude  - 빌드 관리 (필수)
graphiti     - 메모리/지식 그래프
linear       - Linear 프로젝트 관리
puppeteer    - 브라우저 자동화
electron     - Electron 앱 테스트
```

---

## 현재 에이전트 목록

### Backend Agents

| 이름 | 역할 | thinking |
|------|------|----------|
| s3_backend_auth | JWT, OAuth, Session 인증 | medium |
| s3_backend_data | CRUD, Query, Cache | medium |
| s3_backend_notification | Push, Email, SMS 알림 | medium |

### AI Agents

| 이름 | 역할 | thinking |
|------|------|----------|
| s3_ai_assistant | LLM 기반 어시스턴트 | high |
| s3_ai_analyzer | 데이터 분석, 요약, 분류 | high |
| s3_ai_recommender | 추천 시스템 | high |

### Frontend Agents

| 이름 | 역할 | thinking |
|------|------|----------|
| s3_frontend_auth | Flutter 인증 UI | medium |
| s3_frontend_data | Flutter 데이터 동기화 | medium |

---

## 에이전트 프롬프트 템플릿

### 기본 구조

```markdown
# S3 [Category] [Name] Agent

당신은 S3 프로젝트의 [역할] 전문 에이전트입니다.

## 핵심 역할
[이 에이전트의 주요 책임 3-5개]

## 기술 스택
[사용하는 기술들]

## 프로젝트 경로
- Frontend: `C:\DK\S3\S3\frontend`
- Backend: `C:\DK\S3\S3\backend`
- Flutter SDK: `C:\DK\flutter`

## 작업 지침

### 1. 분석 단계
[분석 절차]

### 2. 구현 단계
[구현 절차]

### 3. 검증 단계
[검증 절차]

## 코드 패턴

### [패턴명]
[코드 예시]

## 네이밍 규칙
[파일/클래스/함수 네이밍]

## 테스트 작성
[테스트 패턴]

## 주의사항
[중요 주의사항]

## 출력 형식
[작업 완료 시 출력 형식]
```

---

## 확장 아이디어

### 추가 추천 Agents

| 이름 | 역할 |
|------|------|
| s3_backend_cache | Redis/Memcached 캐싱 |
| s3_backend_queue | 메시지 큐 처리 |
| s3_backend_file | 파일 업로드/S3 스토리지 |
| s3_backend_search | Elasticsearch 검색 |
| s3_ai_vision | 이미지 분석 (OCR, 객체 감지) |
| s3_ai_voice | 음성 인식/합성 |
| s3_ai_embedding | 벡터 임베딩/유사도 검색 |
| s3_frontend_animation | 복잡한 애니메이션 |
| s3_frontend_chart | 차트/그래프 시각화 |
| s3_frontend_form | 복잡한 폼 처리 |
| s3_devops_docker | Docker 컨테이너 관리 |
| s3_devops_k8s | Kubernetes 배포 |
| s3_devops_ci | CI/CD 파이프라인 |

---

## 에이전트 로드 확인

Auto-Claude 시작 시 로그에서 확인:

```
INFO     Registered custom agent: s3_backend_auth
INFO     Registered custom agent: s3_backend_data
...
INFO     Loaded 8 custom agents: ['s3_backend_auth', ...]
```

또는 Python으로 확인:

```python
cd C:\DK\S3\S3\Auto-Claude\apps\backend
.venv\Scripts\python.exe -c "
from agents.tools_pkg.models import list_custom_agents
for a in list_custom_agents():
    print(f'{a[\"agent_type\"]:30} - {a[\"description\"]}')"
```

---

## 이름 규칙

에이전트 이름은 `s3_` 접두사를 사용하여 내장 에이전트와 충돌 방지:

```
s3_[category]_[name]

카테고리:
- backend    - 백엔드 서비스
- frontend   - 프론트엔드 UI
- ai         - AI/ML 기능
- devops     - 인프라/배포
- data       - 데이터 처리
```

---

## 관련 문서

- Claude Skills 가이드: `C:\DK\S3\S3\.claude\skills\README.md`
- 개발 계획: `C:\DK\S3\S3\SKILLS_DEVELOPMENT_PLAN.md`
- Auto-Claude 문서: `C:\DK\S3\S3\Auto-Claude\CLAUDE.md`

---

*이 문서는 AI가 S3 프로젝트의 커스텀 에이전트를 추가할 때 참조합니다.*
*새 에이전트 추가 시 이 README도 업데이트해주세요.*
