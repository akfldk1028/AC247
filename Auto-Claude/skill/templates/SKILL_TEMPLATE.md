# SKILL.md 템플릿

> 새 Skill 생성 시 복사해서 사용

---

## 사용법

```bash
# 1. 스킬 폴더 생성
mkdir -p .claude/skills/s3-[name]/{scripts,references}

# 2. 이 템플릿 복사
cp skill/templates/SKILL_TEMPLATE.md .claude/skills/s3-[name]/SKILL.md

# 3. [name], [설명] 등 플레이스홀더 수정

# 4. 테스트
```

---

## 템플릿 시작

```markdown
---
name: s3-[name]
description: |
  [무엇을 하는지]. [언제 사용하는지].
  사용 시점: (1) [상황1], (2) [상황2], (3) [상황3]
argument-hint: "[arg1|arg2|arg3]"
# disable-model-invocation: true  # 수동만 허용시 (deploy 등)
# user-invocable: false           # 메뉴 숨김시 (백그라운드 지식)
# allowed-tools: Read, Grep       # 도구 제한시
---

# S3 [Name] Skill

[1-2문장 요약]

## When to Use
- [사용해야 하는 상황 1]
- [사용해야 하는 상황 2]
- [사용해야 하는 상황 3]

## When NOT to Use
- [상황 1] → [대안]
- [상황 2] → [대안]

## Quick Start
\`\`\`bash
/s3-[name] [가장 일반적인 예시]
\`\`\`

## Usage
\`\`\`
/s3-[name] [options]
\`\`\`

### Options
| 옵션 | 설명 |
|------|------|
| `option1` | [설명] |
| `option2` | [설명] |

## Process

### Step 1: [단계명]
[설명]
\`\`\`bash
[명령어]
\`\`\`

### Step 2: [단계명]
[설명]
\`\`\`bash
[명령어]
\`\`\`

## Advanced Features
- **[기능 A]**: See [references/feature-a.md](references/feature-a.md)
- **[기능 B]**: See [references/feature-b.md](references/feature-b.md)

## Auto-Claude 연동

| 작업 | 에이전트 |
|------|---------|
| [작업1] | s3_xxx |
| [작업2] | s3_yyy |

## Related Skills
- `/s3-build` - 빌드
- `/s3-test` - 테스트
- `/s3-deploy` - 배포
```

---

## 체크리스트

- [ ] name 설정 (소문자, 하이픈)
- [ ] description 상세히 작성 (트리거 기준)
- [ ] When to Use 작성
- [ ] When NOT to Use 작성
- [ ] Quick Start 예시 추가
- [ ] 500줄 미만 유지
- [ ] references/ 분리 필요시 적용
