# New Character Action: {ACTION_NAME}

## Overview
Add a new character action type `{ACTION_TYPE_STRING}` to the Golem AI Agent System.
This action allows the AI agent to {ACTION_DESCRIPTION}.

## Workflow Type
feature

## Task Scope

### 1. ActionId 추가
- `Assets/Scripts/Infrastructure/Messages/ActionId.cs`
  - Character 카테고리 (3000번대)에 `Character_{ACTION_NAME} = {ACTION_ID_NUMBER}` 추가

### 2. ActionPayload 추가
- `Assets/Scripts/Infrastructure/Messages/ActionPayloads.cs`
  - `{ACTION_NAME}Payload : IActionPayload` readonly struct 추가
  - 필요한 필드: {PAYLOAD_FIELDS}

### 3. AINetworkManager 매핑
- `Assets/Scripts/Systems/Networking/AINetworkManager.cs`
  - `HandleCharacterAction()` 내 switch/case에 `"{ACTION_TYPE_STRING}"` → `ActionId.Character_{ACTION_NAME}` 매핑 추가
  - CFConnector.CharacterAction → {ACTION_NAME}Payload 변환 로직

### 4. GolemCharacterController 핸들러
- `Assets/Scripts/Character/GolemCharacterController.cs`
  - `ActionId.Character_{ACTION_NAME}` 구독 추가 (OnEnable)
  - 핸들러 메서드: `On{ACTION_NAME}(ActionMessage msg)` 구현
  - PointClickController 또는 CelesteActionController 호출로 실제 동작 실행

### 5. 키보드 테스트
- GolemCharacterController의 `#if UNITY_EDITOR || DEBUG` 블록에 테스트 키 바인딩 추가

## Dependencies
- Phase 1-5 Infrastructure 완료 필수
- PointClickController.cs 또는 CelesteActionController.cs에 해당 동작이 구현되어 있어야 함

## Critical Constraints
- **DO NOT modify** CFConnector.cs, CelesteActionController.cs, PointClickController.cs, EmotePlayer.cs
- ActionId 번호 대역: Character = 3000번대
- Payload는 `readonly struct` 사용 (GC 최소화)
- 모든 ActionBus 구독은 OnDisable에서 Dispose

## Success Criteria
- [ ] ActionId enum에 새 ID 추가됨
- [ ] Payload struct 생성됨
- [ ] AINetworkManager가 `{ACTION_TYPE_STRING}` → ActionId 매핑
- [ ] GolemCharacterController가 ActionBus 구독 및 핸들러 구현
- [ ] 키보드 테스트로 동작 확인 가능
- [ ] Unity 컴파일 에러 없음
- [ ] 기존 파일 수정 없음 (4개 읽기전용 파일)

## Placeholder Guide
Replace before use:
- `{ACTION_NAME}` → PascalCase 이름 (예: PickUpItem, OpenDoor)
- `{ACTION_TYPE_STRING}` → camelCase 문자열 (예: pickUpItem, openDoor)
- `{ACTION_ID_NUMBER}` → 3000번대 미사용 번호
- `{ACTION_DESCRIPTION}` → 액션 설명
- `{PAYLOAD_FIELDS}` → Payload 필드 목록
