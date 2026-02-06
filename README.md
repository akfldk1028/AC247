# S3 Project - Multi-Agent Architecture

## Agent Architecture Overview


git 을보면 지들끼리 merge 해서 확인을 아하던데 이것도해결된건지
그리고 협업을하는건지

qa 나 검토 agent 도 붙어잇는건지
이제 설계만 완벽하게 하면되는건지


```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         S3 MULTI-AGENT SYSTEM                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │  ORCHESTRATOR   │    │   USER AGENT    │    │  ADMIN AGENT    │         │
│  │     AGENT       │◄──►│   (Frontend)    │◄──►│   (Dashboard)   │         │
│  │  (Auto-Claude)  │    │    Flutter      │    │    Flutter      │         │
│  └────────┬────────┘    └────────┬────────┘    └────────┬────────┘         │
│           │                      │                      │                   │
│           ▼                      ▼                      ▼                   │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                      API GATEWAY AGENT                          │       │
│  │                         (Backend)                               │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│           │                      │                      │                   │
│           ▼                      ▼                      ▼                   │
│  ┌─────────────────┐    ┌──────────────전───┐    ┌─────────────────┐         │
│  │   AI AGENTS     │    │  DATA AGENTS    │    │ SERVICE AGENTS  │         │
│  │                 │    │                 │    │                 │         │
│  │ - Planner       │    │ - DB Agent      │    │ - Auth Agent    │         │
│  │ - Coder         │    │ - Cache Agent   │    │ - Payment Agent │         │
│  │ - QA Reviewer   │    │ - Search Agent  │    │ - Notification  │         │
│  │ - QA Fixer      │    │                 │    │                 │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure (Agent-Oriented)

```
C:\DK\S3\S3\
│
├── README.md                 ← 현재 파일 (Master Index)
│
├── Auto-Claude/              ← ORCHESTRATOR AGENT (개발 자동화)
│   ├── README.md             ← Auto-Claude 사용 가이드
│   └── ...                   ← Kanban, Agent Terminals, Roadmap 활용
│
├── frontend/                 ← USER AGENT (Flutter 모바일/웹 앱)
│   ├── README.md             ← Frontend Agent 설계
│   ├── lib/
│   │   ├── agents/           ← 클라이언트 사이드 에이전트
│   │   ├── services/         ← API 통신 서비스
│   │   ├── models/           ← 데이터 모델
│   │   ├── screens/          ← UI 화면
│   │   └── widgets/          ← 재사용 컴포넌트
│   └── ...
│
├── backend/                  ← API GATEWAY + SERVICE AGENTS
│   ├── README.md             ← Backend Agent 설계
│   ├── agents/               ← 백엔드 에이전트 구현
│   │   ├── auth/             ← Auth Agent
│   │   ├── data/             ← Data Agent
│   │   ├── notification/     ← Notification Agent
│   │   └── orchestrator/     ← 에이전트 오케스트레이션
│   ├── api/                  ← REST/GraphQL API
│   ├── models/               ← 데이터 모델
│   └── services/             ← 외부 서비스 연동
│
└── ai/                       ← AI AGENTS (LLM 기반)
    ├── README.md             ← AI Agent 설계
    ├── agents/               ← Custom AI 에이전트
    │   ├── assistant/        ← 사용자 어시스턴트
    │   ├── analyzer/         ← 데이터 분석
    │   └── recommender/      ← 추천 시스템
    ├── prompts/              ← 프롬프트 템플릿
    └── models/               ← 로컬 모델 설정
```

## Auto-Claude Workflow (개발 자동화)

```
┌─────────────────────────────────────────────────────────────────┐
│                    AUTO-CLAUDE KANBAN BOARD                      │
├──────────┬──────────┬──────────┬──────────┬──────────┬─────────┤
│ BACKLOG  │ PLANNING │ BUILDING │   QA     │ REVIEW   │  DONE   │
├──────────┼──────────┼──────────┼──────────┼──────────┼─────────┤
│ Task 1   │ Task 2   │ Task 3   │ Task 4   │ Task 5   │ Task 6  │
│ Task 7   │          │ Task 8   │          │          │ Task 9  │
│          │          │ Task 10  │          │          │         │
└──────────┴──────────┴──────────┴──────────┴──────────┴─────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              AGENT TERMINALS (최대 12개 병렬 실행)               │
├─────────────────┬─────────────────┬─────────────────────────────┤
│ Terminal 1      │ Terminal 2      │ Terminal 3                  │
│ [frontend/auth] │ [backend/api]   │ [ai/assistant]              │
│ > flutter run   │ > python run.py │ > python agent.py           │
│ ...             │ ...             │ ...                         │
├─────────────────┼─────────────────┼─────────────────────────────┤
│ Terminal 4      │ Terminal 5      │ Terminal 6                  │
│ [tests]         │ [database]      │ [deployment]                │
│ > pytest        │ > migrate       │ > docker build              │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## Roadmap (Auto-Claude Roadmap 기능 활용)

### Phase 1: Foundation (현재)
- [x] Flutter SDK 설치 및 세팅
- [x] Auto-Claude 연동
- [x] 프로젝트 구조 설계
- [ ] Backend 기본 구조 생성
- [ ] AI Agent 기본 구조 생성

### Phase 2: Core Agents
- [ ] Auth Agent 구현
- [ ] Data Agent 구현
- [ ] API Gateway 구현
- [ ] Frontend-Backend 연동

### Phase 3: AI Integration
- [ ] Assistant Agent 구현
- [ ] Analyzer Agent 구현
- [ ] Recommender Agent 구현
- [ ] Agent 간 통신 프로토콜

### Phase 4: Production
- [ ] 테스트 자동화
- [ ] CI/CD 파이프라인
- [ ] 모니터링 시스템
- [ ] 배포

## Quick Start

### 1. Auto-Claude 실행 (개발 오케스트레이터)
```powershell
cd C:\DK\S3\S3\Auto-Claude
npm run dev
# → Kanban Board에서 태스크 관리
# → Agent Terminals로 병렬 개발
# → Roadmap으로 진행 상황 추적
```

### 2. Frontend Agent 실행
```powershell
cd C:\DK\S3\S3\frontend
flutter run
```

### 3. Backend Agent 실행 (구현 후)
```powershell
cd C:\DK\S3\S3\backend
python -m uvicorn main:app --reload
```

### 4. AI Agent 실행 (구현 후)
```powershell
cd C:\DK\S3\S3\ai
python -m agents.assistant
```

## Module README Index

| 모듈 | README 경로 | 역할 | 상태 |
|------|-------------|------|------|
| **Orchestrator** | [Auto-Claude/README.md](Auto-Claude/README.md) | 개발 자동화, 태스크 오케스트레이션 | Ready |
| **Frontend** | [frontend/README.md](frontend/README.md) | User Agent (Flutter 앱) | Ready |
| **Backend** | [backend/README.md](backend/README.md) | API Gateway + Service Agents | Setup Required |
| **AI** | [ai/README.md](ai/README.md) | AI Agents (LLM 기반) | Setup Required |

## Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Orchestrator | Auto-Claude (Electron + Python) | 2.7.6-beta.2 |
| Frontend | Flutter / Dart | 3.38.9 / 3.10.8 |
| Backend | FastAPI / Python | 0.115+ / 3.11+ |
| AI | Claude Agent SDK | 0.1.27 |
| Database | PostgreSQL / Redis | 16+ / 7+ |
| Runtime | Node.js | 24.13.0 |

## Environment Setup

| Variable | Value |
|----------|-------|
| `FLUTTER_HOME` | `C:\DK\flutter` |
| `JAVA_HOME` | `C:\Program Files\Android\Android Studio\jbr` |
| `ANDROID_HOME` | `C:\Users\User\AppData\Local\Android\Sdk` |
| `AUTO_CLAUDE_HOME` | `C:\DK\S3\S3\Auto-Claude` |
