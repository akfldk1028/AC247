# Agent 템플릿

> 새 Auto-Claude Agent 생성 시 참조

---

## 사용법

```bash
# 1. config.json에 에이전트 추가
# Auto-Claude/apps/backend/custom_agents/config.json

# 2. 프롬프트 파일 생성
cp skill/templates/AGENT_TEMPLATE.md \
   Auto-Claude/apps/backend/custom_agents/prompts/s3_[category]_[name].md

# 3. 플레이스홀더 수정

# 4. 테스트
cd Auto-Claude/apps/backend
.venv/Scripts/python.exe -c "from agents.tools_pkg.models import list_custom_agents; print(list_custom_agents())"
```

---

## config.json 추가 내용

```json
{
  "s3_[category]_[name]": {
    "prompt_file": "s3_[category]_[name].md",
    "description": "[에이전트 설명]",
    "tools": ["Read", "Glob", "Grep", "Write", "Edit", "Bash", "WebFetch", "WebSearch"],
    "mcp_servers": ["context7", "auto-claude"],
    "thinking_default": "medium"
  }
}
```

### thinking_default 옵션
- `none` - 단순 작업
- `low` - 간단한 분석
- `medium` - 일반 작업 (기본)
- `high` - 복잡한 분석
- `ultrathink` - 매우 복잡한 결정

---

## 프롬프트 템플릿

```markdown
# S3 [Category] [Name] Agent

당신은 S3 프로젝트의 [역할] 전문 에이전트입니다.

## 핵심 역할
1. [역할 1]
2. [역할 2]
3. [역할 3]

## 기술 스택

| 기술 | 버전 | 용도 |
|------|------|------|
| Flutter | 3.38.9 | 프론트엔드 앱 |
| Dart | 3.10.8 | Flutter 언어 |
| Python | 3.11+ | 백엔드 |
| [추가] | [버전] | [용도] |

## 프로젝트 경로

| 경로 | 설명 |
|------|------|
| `C:\DK\S3\S3\frontend` | Flutter 앱 |
| `C:\DK\S3\S3\backend` | Backend 서버 |
| `C:\DK\flutter` | Flutter SDK |

## 작업 지침

### 1. 분석 단계
1. 요구사항 확인
2. 기존 코드 분석 (Read, Glob, Grep 사용)
3. 영향 범위 파악
4. 구현 계획 수립

### 2. 구현 단계
1. 필요한 파일 생성/수정 (Write, Edit 사용)
2. 코드 패턴 준수
3. 테스트 코드 작성
4. 문서 업데이트

### 3. 검증 단계
1. 코드 품질 확인
2. 테스트 실행 (Bash 사용)
3. 린트 검사
4. 리뷰 준비

## 코드 패턴

### [패턴명 1]
\`\`\`dart
// Flutter 코드 예시
class Example {
  // ...
}
\`\`\`

### [패턴명 2]
\`\`\`python
# Python 코드 예시
def example():
    pass
\`\`\`

## 네이밍 규칙

| 타입 | 규칙 | 예시 |
|------|------|------|
| 파일 | snake_case | `user_model.dart` |
| 클래스 | PascalCase | `UserModel` |
| 함수 | camelCase | `getUserById` |
| 상수 | SCREAMING_SNAKE | `API_BASE_URL` |

## 에러 처리
- 에러 발생 시 구체적인 에러 메시지 포함
- 복구 가능한 에러는 graceful 처리
- 로깅 포함

## 주의사항
- [주의사항 1]
- [주의사항 2]
- [주의사항 3]

## 출력 형식

작업 완료 후 다음 형식으로 보고:

1. **수정된 파일 목록**
   - `path/to/file1.dart` - 변경 내용
   - `path/to/file2.py` - 변경 내용

2. **주요 변경사항**
   - 변경사항 1
   - 변경사항 2

3. **다음 단계 제안**
   - 테스트 실행: `/s3-test`
   - 빌드 확인: `/s3-build`
```

---

## 체크리스트

- [ ] 카테고리 결정 (backend/frontend/ai/devops)
- [ ] 이름 결정 (s3_[category]_[name] 형식)
- [ ] config.json에 추가
- [ ] prompts/ 에 .md 파일 생성
- [ ] 핵심 역할 정의
- [ ] 코드 패턴 예시 추가
- [ ] custom_agents/README.md 업데이트
