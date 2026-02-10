# Sound System (SoundManager Module) - TEMPLATE

## Overview
모듈형 SoundManager를 Managers 패턴에 추가하여 BGM/SFX를 관리.
`Managers.Sound` 로 접근. POCO 클래스 (AudioSource는 별도 GO에 생성).

## Architecture Rules
- **MUST READ**: `{MANAGERS_FILE}` - Service Locator 패턴 참조
- **MUST READ**: `{EVENT_IDS_FILE}` - ActionId enum, IActionPayload 참조
- SoundManager는 POCO (MonoBehaviour 불필요)
- AudioClip은 Addressables(ResourceManager)로 로드
- ActionBus 이벤트 구독으로 자동 재생
- 볼륨은 PlayerPrefs 저장
- SoundManager = 범용 API, GameSoundBinder = 게임 특화 매핑

## 커스터마이징 가이드
1. `{MANAGERS_FILE}`의 Contents 섹션에 `_sound` 필드 추가
2. `{EVENT_IDS_FILE}`에서 게임별 이벤트 ID 확인
3. GameSoundBinder에서 게임 이벤트 → 사운드 매핑 정의
4. 오디오 파일은 `{RESOURCES_ROOT}/Audio/` 에 배치
