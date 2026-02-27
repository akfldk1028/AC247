# New Emote Type: {EMOTE_NAME}

## Overview
Add a new emote type `{EMOTE_NAME}` to the Golem AI Agent System.
{EMOTE_DESCRIPTION}

## Workflow Type
feature

## Task Scope

### 1. ActionId 추가
- `Assets/Scripts/Infrastructure/Messages/ActionId.cs`
  - Agent 카테고리 (2000번대)에 `Agent_{EMOTE_NAME} = {EMOTE_ID_NUMBER}` 추가

### 2. Payload 추가
- `Assets/Scripts/Infrastructure/Messages/ActionPayloads.cs`
  - `{EMOTE_NAME}Payload : IActionPayload` readonly struct 추가
  - 필드: AgentId, {EMOTE_SPECIFIC_FIELDS}

### 3. AINetworkManager 핸들러
- `Assets/Scripts/Systems/Networking/AINetworkManager.cs`
  - CFConnector의 `On{EMOTE_NAME}` 이벤트 구독 추가 (OnEnable/OnDisable)
  - `Handle{EMOTE_NAME}()` → `Managers.PublishAction(ActionId.Agent_{EMOTE_NAME}, payload)` 브릿지

### 4. GolemEmoteHandler 처리
- `Assets/Scripts/Character/GolemEmoteHandler.cs`
  - `ActionId.Agent_{EMOTE_NAME}` 구독 추가
  - `Play{EMOTE_NAME}({EMOTE_NAME}Payload payload)` 메서드 구현
  - EmotePlayer 또는 Animator 호출로 실제 재생

## Dependencies
- Phase 1-5 Infrastructure 완료 필수
- CFConnector에 해당 이벤트가 정의되어 있어야 함

## Critical Constraints
- **DO NOT modify** CFConnector.cs, EmotePlayer.cs
- ActionId 번호 대역: Agent = 2000번대
- Payload는 `readonly struct`
- 모든 구독 OnDisable에서 Dispose

## Success Criteria
- [ ] ActionId enum에 새 이모트 ID 추가
- [ ] Payload struct 생성
- [ ] AINetworkManager 브릿지 추가
- [ ] GolemEmoteHandler에서 처리
- [ ] Unity 컴파일 에러 없음

## Placeholder Guide
- `{EMOTE_NAME}` → PascalCase (예: BodyLanguage, Gesture)
- `{EMOTE_ID_NUMBER}` → 2000번대 미사용 번호
- `{EMOTE_DESCRIPTION}` → 설명
- `{EMOTE_SPECIFIC_FIELDS}` → 이모트 고유 필드
