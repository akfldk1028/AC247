# Auto-Claude Model 설정 위치 총정리

> 모델 변경 시 이 문서 참고. 우선순위: CLI > per-spec > global custom > agent profile > env var > hardcoded

## !! Opus 4.6 업데이트 (2026-02-05 출시)

새 모델 ID: `claude-opus-4-6`
- 1M context window (beta)
- Agent Teams 기능 추가
- 가격: $5/$25 per MTok (200k 초과 시 $10/$37.50)

**업데이트 필요한 파일들:**
1. `Auto-Claude\apps\backend\phase_config.py` line 16 → `"opus": "claude-opus-4-6"`
2. `Auto-Claude\apps\frontend\src\shared\constants\models.ts` line 20 → `opus: 'claude-opus-4-6'`
3. `.env` (선택) → `ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-6`

---

## 1. 앱 전역 설정 (가장 먼저 바꿀 곳)

**파일**: `C:\Users\User\AppData\Roaming\auto-claude-ui\settings.json`

| 필드 | 현재값 | 설명 |
|------|--------|------|
| `defaultModel` | `"haiku"` | 레거시 기본 모델 (프로필에 의해 덮어씌워짐) |
| `selectedAgentProfile` | `"auto"` | 프리셋 선택: `auto`/`complex`/`balanced`/`quick` |
| `customPhaseModels` | (없음) | Phase별 모델 오버라이드 `{"spec":"opus","planning":"sonnet","coding":"haiku","qa":"sonnet"}` |
| `customPhaseThinking` | (없음) | Phase별 thinking `{"spec":"ultrathink","planning":"high","coding":"medium","qa":"high"}` |
| `featureModels` | (없음) | 비파이프라인 기능 모델 (insights, ideation, roadmap 등) |

### Agent Profile 프리셋 기본값

| 프리셋 | 모델 | thinking |
|--------|------|----------|
| **auto** (현재) | 전부 `opus` | spec=ultrathink, planning=high, coding=low, qa=low |
| **complex** | 전부 `opus` | 전부 `ultrathink` |
| **balanced** | 전부 `sonnet` | 전부 `medium` |
| **quick** | 전부 `haiku` | 전부 `low` |

**가장 싸게 테스트**: `selectedAgentProfile` → `"quick"` 으로 변경

---

## 2. 프로젝트별 설정

**파일**: `C:\Users\User\AppData\Roaming\auto-claude-ui\store\projects.json`

| 필드 | 위치 | 설명 |
|------|------|------|
| `projects[N].settings.model` | 각 프로젝트 | 레거시 프로젝트별 모델 |

---

## 3. Backend 환경변수

**파일**: `C:\DK\AC247\AC247\Auto-Claude\apps\backend\.env`

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `AUTO_BUILD_MODEL` | `claude-opus-4-5-20251101` | 전역 모델 오버라이드 |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `claude-haiku-4-5-20251001` | "haiku" 매핑 |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | `claude-sonnet-4-5-20250929` | "sonnet" 매핑 |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | `claude-opus-4-5-20251101` | "opus" 매핑 |
| `UTILITY_MODEL_ID` | `claude-haiku-4-5-20251001` | 유틸리티(커밋메시지 등) |

---

## 4. Backend 하드코딩 기본값

**파일**: `Auto-Claude\apps\backend\phase_config.py`

```python
MODEL_ID_MAP = {          # line 15-19
    "opus":   "claude-opus-4-5-20251101",
    "sonnet": "claude-sonnet-4-5-20250929",
    "haiku":  "claude-haiku-4-5-20251001",
}

DEFAULT_PHASE_MODELS = {  # line 51-56 (프로필 없을 때 폴백)
    "spec": "sonnet", "planning": "sonnet",
    "coding": "sonnet", "qa": "sonnet",
}
```

---

## 5. Frontend 하드코딩 기본값

**파일**: `Auto-Claude\apps\frontend\src\shared\constants\models.ts`

- Agent Profile 프리셋 정의 (line 154-195)
- Feature Models 기본값 (line 123-140)

---

## 6. Per-Spec (태스크별)

**파일**: `.auto-claude/specs/XXX-name/task_metadata.json`

| 필드 | 설명 |
|------|------|
| `model` | 단일 모델 (isAutoProfile=false 일 때) |
| `phaseModels` | Phase별 모델 `{"spec":"opus","planning":"sonnet",...}` |
| `phaseThinking` | Phase별 thinking |
| `isAutoProfile` | true면 phase별 설정 사용 |

---

## 7. CLI 오버라이드 (최우선)

```bash
python run.py --spec 001 --model haiku
```

---

## 빠른 변경 체크리스트

### 전부 haiku로 바꾸려면:

1. `settings.json` → `"selectedAgentProfile": "quick"` (haiku + low thinking)
2. `projects.json` → 각 프로젝트 `"model": "haiku"`
3. `.env` → `AUTO_BUILD_MODEL=claude-haiku-4-5-20251001` (선택사항)
4. CLI → `--model haiku` (1회성)

### 우선순위 (높은것이 이김):
```
CLI --model > per-spec task_metadata > global customPhaseModels > agent profile > AUTO_BUILD_MODEL env > hardcoded defaults
```
