# S3 Skill Ideas & Templates

> AI 또는 사용자가 새 Skills/Agents를 추가할 때 참조하는 아이디어 저장소

---

## 폴더 용도

| 폴더 | 용도 |
|------|------|
| `skill/` (여기) | 스킬 아이디어, 템플릿, 계획 |
| `.claude/skills/` | 실제 Claude Skills (SKILL.md) |
| `Auto-Claude/apps/backend/custom_agents/` | Auto-Claude Agents |

---

## 빠른 추가 가이드

### 새 Skill 아이디어 추가
```bash
# 1. 이 폴더에 아이디어 문서 생성
echo "# 스킬 아이디어" > skill/ideas/new-skill-idea.md

# 2. 구현 준비되면 .claude/skills/로 이동
mkdir -p .claude/skills/new-skill/{scripts,references}
# SKILL.md 작성
```

### 새 Agent 아이디어 추가
```bash
# 1. 이 폴더에 아이디어 문서 생성
echo "# 에이전트 아이디어" > skill/ideas/new-agent-idea.md

# 2. 구현 시 custom_agents에 추가
# config.json + prompts/*.md
```

---

## 구현 완료된 Skills

| 이름 | 명령어 | 설명 | 상태 |
|------|--------|------|------|
| s3-auto-task | `/s3-auto-task` | Auto-Claude task 생성 및 자동 빌드 | ✅ 완료 |
| s3-build | `/s3-build` | Flutter/Python 빌드 | ✅ 완료 |
| s3-test | `/s3-test` | 테스트 실행 | ✅ 완료 |
| s3-deploy | `/s3-deploy` | 프로덕션 배포 | ✅ 완료 |

---

## 추가 예정 Skills (아이디어)

### 개발 도구
| 이름 | 명령어 | 설명 | 우선순위 |
|------|--------|------|----------|
| s3-db | `/s3-db` | DB 마이그레이션, 스키마 관리 | 높음 |
| s3-api | `/s3-api` | API 문서 생성, OpenAPI 스펙 | 중간 |
| s3-lint | `/s3-lint` | 코드 린트, 포맷팅 | 중간 |
| s3-docs | `/s3-docs` | 문서 자동 생성 | 낮음 |

### 분석 도구
| 이름 | 명령어 | 설명 | 우선순위 |
|------|--------|------|----------|
| s3-perf | `/s3-perf` | 성능 분석, 프로파일링 | 중간 |
| s3-security | `/s3-security` | 보안 스캔, 취약점 검사 | 높음 |
| s3-deps | `/s3-deps` | 의존성 분석, 업데이트 | 낮음 |

### DevOps
| 이름 | 명령어 | 설명 | 우선순위 |
|------|--------|------|----------|
| s3-ci | `/s3-ci` | CI/CD 파이프라인 관리 | 높음 |
| s3-docker | `/s3-docker` | Docker 이미지 빌드 | 중간 |
| s3-k8s | `/s3-k8s` | Kubernetes 배포 | 낮음 |

---

## 추가 예정 Agents (아이디어)

### Backend
| 이름 | 설명 | 우선순위 |
|------|------|----------|
| s3_backend_cache | Redis/Memcached 캐싱 | 중간 |
| s3_backend_queue | 메시지 큐 (RabbitMQ, Kafka) | 중간 |
| s3_backend_file | 파일 업로드, S3 스토리지 | 높음 |
| s3_backend_search | Elasticsearch 검색 | 낮음 |
| s3_backend_payment | 결제 시스템 연동 | 높음 |

### AI/ML
| 이름 | 설명 | 우선순위 |
|------|------|----------|
| s3_ai_vision | 이미지 분석 (OCR, 객체 감지) | 중간 |
| s3_ai_voice | 음성 인식/합성 | 낮음 |
| s3_ai_embedding | 벡터 임베딩, 유사도 검색 | 중간 |
| s3_ai_chat | 채팅봇 구현 | 높음 |

### Frontend
| 이름 | 설명 | 우선순위 |
|------|------|----------|
| s3_frontend_animation | 복잡한 애니메이션 | 낮음 |
| s3_frontend_chart | 차트/그래프 시각화 | 중간 |
| s3_frontend_form | 복잡한 폼 처리 | 중간 |
| s3_frontend_offline | 오프라인 지원 | 낮음 |

---

## 템플릿

### SKILL.md 템플릿

```markdown
---
name: s3-[name]
description: |
  [설명]. [언제 사용하는지].
  사용 시점: (1) ..., (2) ..., (3) ...
argument-hint: "[옵션들]"
# disable-model-invocation: true  # 수동만 허용시
---

# S3 [Name] Skill

[1줄 요약]

## When to Use
- 상황 1
- 상황 2

## When NOT to Use
- 상황 1 → 대안
- 상황 2 → 대안

## Quick Start
\`\`\`bash
/s3-[name] [example]
\`\`\`

## Usage
\`\`\`
/s3-[name] [options]
\`\`\`

### Options
| 옵션 | 설명 |
|------|------|
| `opt1` | 설명 |

## Process

### Step 1: [단계명]
\`\`\`bash
# 명령어
\`\`\`

## Related Skills
- `/s3-build` - 빌드
- `/s3-test` - 테스트
```

### Agent config.json 템플릿

```json
{
  "s3_category_name": {
    "prompt_file": "s3_category_name.md",
    "description": "설명",
    "tools": ["Read", "Glob", "Grep", "Write", "Edit", "Bash", "WebFetch", "WebSearch"],
    "mcp_servers": ["context7", "auto-claude"],
    "thinking_default": "medium"
  }
}
```

### Agent Prompt 템플릿

```markdown
# S3 [Category] [Name] Agent

당신은 S3 프로젝트의 [역할] 전문 에이전트입니다.

## 핵심 역할
1. [역할 1]
2. [역할 2]

## 기술 스택
- Flutter 3.38.9
- Python 3.11+
- [추가 기술]

## 프로젝트 경로
- Frontend: `C:\DK\S3\S3\frontend`
- Backend: `C:\DK\S3\S3\backend`

## 작업 지침

### 분석 단계
1. 요구사항 파악
2. 기존 코드 분석

### 구현 단계
1. 코드 작성
2. 테스트 작성

## 코드 패턴
[예시 코드]

## 주의사항
- 주의 1
- 주의 2
```

---

## 파일 구조

```
skill/
├── README.md              # 이 파일
├── ideas/                 # 아이디어 문서
│   ├── s3-db.md
│   ├── s3-security.md
│   └── ...
├── templates/             # 템플릿 파일
│   ├── skill-template.md
│   └── agent-template.md
└── drafts/                # 작업 중인 스킬
    └── ...
```

---

## AI 확장 체크리스트

### Skill 추가 시
- [ ] `skill/ideas/`에 아이디어 문서 작성
- [ ] 우선순위 결정
- [ ] `.claude/skills/[name]/SKILL.md` 작성
- [ ] `scripts/`, `references/` 필요시 추가
- [ ] `.claude/skills/README.md` 목록 업데이트
- [ ] 테스트

### Agent 추가 시
- [ ] `skill/ideas/`에 아이디어 문서 작성
- [ ] 우선순위 결정
- [ ] `custom_agents/config.json`에 추가
- [ ] `custom_agents/prompts/[name].md` 작성
- [ ] `custom_agents/README.md` 목록 업데이트
- [ ] 테스트

---

## 관련 문서

| 문서 | 경로 | 내용 |
|------|------|------|
| Skills Best Practices | `.claude/skills/BEST_PRACTICES.md` | 공식 작성 가이드 |
| Skills README | `.claude/skills/README.md` | Skills 상세 가이드 |
| Agents README | `Auto-Claude/.../custom_agents/README.md` | Agents 상세 가이드 |
| 개발 계획 | `SKILLS_DEVELOPMENT_PLAN.md` | 전체 계획 |

---

*이 폴더는 AI가 자유롭게 아이디어를 추가하고 계획할 수 있는 공간입니다.*
