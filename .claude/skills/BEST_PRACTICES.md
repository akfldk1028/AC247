# Claude Skills Best Practices

> 공식 문서, GitHub, 커뮤니티에서 수집한 최적의 Skills 작성 가이드

---

## 핵심 원칙 (Official)

### 1. Context is Currency
- **Context window는 공유 자원**: 시스템 프롬프트, 대화 기록, 다른 Skills가 함께 사용
- **Claude는 이미 똑똑함**: 과도한 설명 불필요
- Claude가 모르는 정보만 추가
- 장황한 설명보다 간결한 예시 선호

### 2. Progressive Disclosure (3단계 로딩)

| 단계 | 내용 | 로딩 시점 | 권장 크기 |
|------|------|----------|----------|
| **1. Metadata** | name + description | 항상 | ~100 단어 |
| **2. SKILL.md** | 본문 지침 | 스킬 트리거 시 | <500줄 / <5000단어 |
| **3. Resources** | references/, scripts/ | 필요할 때 | 무제한 |

### 3. Description이 트리거 메커니즘

```yaml
# 나쁜 예
description: 배포 스킬

# 좋은 예
description: "프로덕션 배포 자동화. Flutter web/apk 빌드, 환경설정 관리.
사용 시점: (1) 배포 준비 완료 시, (2) 빌드 후 배포 필요 시, (3) CI/CD 실행 시"
```

---

## SKILL.md 구조 (Official Template)

```markdown
---
name: skill-name
description: |
  무엇을 하는지 + 언제 사용하는지 상세히 작성.
  이 description이 Claude가 스킬을 선택하는 기준이 됨.
---

# Skill Name

[1-2문장 요약]

## When to Use
- 사용해야 하는 상황 1
- 사용해야 하는 상황 2

## When NOT to Use
- 사용하지 말아야 하는 상황
- 다른 스킬이 더 적합한 경우

## Quick Start
[가장 일반적인 사용 예시 1개]

## Usage
\`\`\`
/skill-name [arguments]
\`\`\`

## Process
### Step 1: [단계명]
[간결한 지침]

### Step 2: [단계명]
[간결한 지침]

## Advanced Features
- **기능 A**: See [references/feature-a.md](references/feature-a.md)
- **기능 B**: See [references/feature-b.md](references/feature-b.md)

## Related Skills
- `/other-skill` - 관련 작업
```

---

## 폴더 구조 (Official)

```
skill-name/
├── SKILL.md              # 필수: 핵심 지침만 (<500줄)
├── scripts/              # 선택: 실행 가능한 스크립트
│   └── run.py            # 반복적/오류가 발생하기 쉬운 작업
├── references/           # 선택: 상세 문서 (필요시 로드)
│   ├── api-docs.md       # API 문서
│   ├── troubleshooting.md # 문제 해결
│   └── patterns.md       # 코드 패턴
└── assets/               # 선택: 출력에 사용되는 파일
    └── template.html     # 템플릿 파일
```

### 포함하지 말 것
- README.md (SKILL.md가 이 역할)
- INSTALLATION_GUIDE.md
- CHANGELOG.md
- 보조 문서들

---

## Frontmatter 옵션 (Complete Reference)

```yaml
---
# 필수
name: skill-name                    # 슬래시 명령어 이름 (소문자, 하이픈)
description: |                      # 트리거 기준 (상세히!)
  무엇을 하는지, 언제 사용하는지

# 선택 - 호출 제어
disable-model-invocation: true      # Claude 자동 호출 방지 (deploy 등)
user-invocable: false               # /메뉴에서 숨김 (백그라운드 지식)

# 선택 - 실행 환경
allowed-tools: Read, Grep, Bash     # 사용 가능한 도구 제한
model: claude-opus-4-5-20251101     # 특정 모델 사용
context: fork                       # 서브에이전트에서 실행
agent: Explore                      # 서브에이전트 타입

# 선택 - 인수 힌트
argument-hint: "[issue-number]"     # 자동완성 힌트
---
```

### 주요 조합 패턴

| 용도 | 설정 |
|------|------|
| 자동 + 수동 (기본) | (기본값) |
| 수동만 (deploy 등) | `disable-model-invocation: true` |
| 자동만 (백그라운드 지식) | `user-invocable: false` |
| 읽기 전용 | `allowed-tools: Read, Grep, Glob` |
| 격리 실행 | `context: fork` |

---

## 문자열 치환

| 변수 | 설명 |
|------|------|
| `$ARGUMENTS` | 전달된 모든 인수 |
| `$ARGUMENTS[0]`, `$0` | 첫 번째 인수 |
| `$ARGUMENTS[1]`, `$1` | 두 번째 인수 |
| `${CLAUDE_SESSION_ID}` | 세션 ID |
| `` !`command` `` | 명령 실행 결과 주입 |

예시:
```yaml
---
name: fix-issue
---
GitHub issue $0 수정하기. 다음 단계 따르기:
1. 이슈 읽기: !`gh issue view $0`
2. 분석 및 수정
```

---

## 작성 스타일 가이드

### DO (해야 할 것)

1. **명령형/동사원형 사용**
   ```
   ✅ "테스트 실행하기"
   ✅ "파일 분석하기"
   ❌ "테스트를 실행해야 합니다"
   ❌ "파일을 분석하세요"
   ```

2. **When to Use / When NOT to Use 포함**
   ```markdown
   ## When to Use
   - 새 기능 개발 시
   - 리팩토링 시

   ## When NOT to Use
   - 단순 버그 수정 (직접 수정)
   - 문서만 수정할 때
   ```

3. **간결한 예시 우선**
   ```markdown
   ## Quick Start
   \`\`\`bash
   /s3-build web
   \`\`\`
   ```

4. **상세 내용은 references/로**
   ```markdown
   ## Advanced
   - 상세 설정: [references/config.md](references/config.md)
   ```

### DON'T (하지 말 것)

1. **과도한 설명**
   ```
   ❌ "이 스킬은 매우 중요한 배포 작업을 수행합니다..."
   ✅ "프로덕션 배포 실행"
   ```

2. **중복 정보**
   ```
   ❌ SKILL.md와 references/ 양쪽에 같은 내용
   ✅ SKILL.md에 요약, references/에 상세
   ```

3. **깊은 중첩**
   ```
   ❌ references/level1/level2/level3.md
   ✅ references/topic.md (한 단계만)
   ```

---

## 보안 고려사항

> ⚠️ "Skills can execute arbitrary code. Only install from trusted sources."

### 체크리스트
- [ ] 신뢰할 수 있는 소스만 설치
- [ ] SKILL.md와 모든 스크립트 리뷰
- [ ] 팀 배포 전 피어 리뷰
- [ ] 최소 권한 원칙 적용
- [ ] 정기적 감사
- [ ] 비프로덕션 환경에서 먼저 테스트

### 안전한 스킬 예시
```yaml
---
name: safe-reader
allowed-tools: Read, Grep, Glob  # 읽기만 허용
---
```

---

## S3 프로젝트 적용

### 현재 스킬 개선점

| 스킬 | 개선 사항 |
|------|----------|
| s3-build | ✅ 이미 적용됨 |
| s3-test | When NOT to Use 추가 필요 |
| s3-feature | references/ 분리 필요 |
| s3-deploy | disable-model-invocation 추가 필요 |

### 추천 구조

```
s3-build/
├── SKILL.md              # 500줄 미만으로 간결하게
├── scripts/
│   └── build.ps1         # 빌드 스크립트
└── references/
    └── troubleshooting.md # 문제 해결 가이드 (분리)
```

---

## 참고 자료

### 공식 문서
- [Claude Code Skills Docs](https://code.claude.com/docs/en/skills)
- [Anthropic Skills Repository](https://github.com/anthropics/skills)
- [Agent Skills Spec](https://agentskills.io)

### 커뮤니티
- [awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills)
- [VoltAgent Skills](https://github.com/VoltAgent/awesome-agent-skills)

### 공식 예시 스킬
- `skill-creator` - 스킬 생성 가이드
- `docx`, `pdf`, `xlsx` - 문서 처리
- `mcp-builder` - MCP 서버 생성

---

*Sources: code.claude.com/docs, github.com/anthropics/skills, github.com/travisvn/awesome-claude-skills*
