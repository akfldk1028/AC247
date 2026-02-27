# New Interaction Spot Type: {SPOT_NAME}

## Overview
Add a new InteractionSpot type `{SPOT_NAME}` and corresponding character action to enable AI agents to {SPOT_DESCRIPTION}.

## Workflow Type
feature

## Task Scope

### 1. InteractionType 확장
- 기존 InteractionType enum에 `{SPOT_NAME}` 추가
- 또는 새 InteractionSpot 서브클래스 생성

### 2. ActionId + Payload
- `ActionId.cs`: `Character_{SPOT_ACTION_NAME} = {ACTION_ID}` 추가 (3000번대)
- `ActionPayloads.cs`: `{SPOT_ACTION_NAME}Payload` struct 추가
  - AgentId, SpotName, {SPOT_SPECIFIC_FIELDS}

### 3. PointClickController 확장
- `{SPOT_ACTION_NAME}AtInteractionSpot(InteractionSpot spot)` 메서드 추가
  - NavMesh 이동 → 도착 → 인터랙션 실행
  - 인터랙션 완료 콜백

### 4. AINetworkManager 매핑
- HandleCharacterAction에 `"{SPOT_TYPE_STRING}"` → `ActionId.Character_{SPOT_ACTION_NAME}` 추가

### 5. GolemCharacterController 핸들러
- `ActionId.Character_{SPOT_ACTION_NAME}` 구독
- InteractionSpot 이름으로 씬 검색: `FindObjectsByType<InteractionSpot>()`
- PointClickController.{SPOT_ACTION_NAME}AtInteractionSpot() 호출

### 6. 씬 배치 가이드
- InteractionSpot prefab 생성 가이드
- spotName 명명 규칙: `{SPOT_PREFIX}_{location}_{number}`

## Dependencies
- Phase 1-5 완료 필수
- InteractionSpot 시스템이 씬에 배치되어 있어야 함

## Critical Constraints
- **DO NOT modify** CFConnector.cs, CelesteActionController.cs, EmotePlayer.cs
- InteractionSpot은 씬 오브젝트 (코드만으로는 테스트 불가 → 에디터에서 확인)
- 비동기 액션: 이동 → 인터랙션 → 완료 콜백 순서 보장

## Success Criteria
- [ ] InteractionType 확장 또는 새 타입 생성
- [ ] ActionId + Payload 추가
- [ ] PointClickController에 실행 메서드 추가
- [ ] AINetworkManager 매핑
- [ ] GolemCharacterController 핸들러
- [ ] Unity 컴파일 에러 없음

## Placeholder Guide
- `{SPOT_NAME}` → PascalCase (예: Counter, Shelf, Bed)
- `{SPOT_ACTION_NAME}` → PascalCase 동사 (예: UseCounter, BrowseShelf, LieOnBed)
- `{SPOT_TYPE_STRING}` → camelCase (예: useCounter, browseShelf)
- `{ACTION_ID}` → 3000번대 미사용 번호
- `{SPOT_DESCRIPTION}` → 설명
- `{SPOT_SPECIFIC_FIELDS}` → 추가 필드
- `{SPOT_PREFIX}` → 소문자 접두사 (예: counter, shelf)
