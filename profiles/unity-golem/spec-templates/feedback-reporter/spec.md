# Agent Feedback Reporter: {FEEDBACK_TYPE}

## Overview
Implement AgentFeedbackReporter to report {FEEDBACK_TYPE} results back to the AI server via CFConnector.SendRpc().
AI 서버와의 피드백 루프를 완성하여 에이전트가 자율적으로 행동-보고-다음행동 사이클을 돌 수 있게 합니다.

## Workflow Type
feature

## Task Scope

### 1. AgentFeedbackReporter MonoBehaviour
- `Assets/Scripts/Systems/Networking/AgentFeedbackReporter.cs` 신규 생성
  - MonoBehaviour, CFConnector 참조 (SerializeField)
  - ActionBus 구독: `Agent_ActionCompleted`, `Agent_ActionFailed`
  - 완료 시 → `cfConnector.SendRpcFireAndForget("action_completed", payload)`
  - 실패 시 → `cfConnector.SendRpcFireAndForget("action_completed", payload_with_error)`

### 2. ActionCompleted 발행 추가
- `GolemCharacterController.cs`에 액션 완료 시 `Agent_ActionCompleted` 발행
  - MoveToPointPublic 완료 → ActionCompleted(agentId, "moveToLocation", true)
  - SitAtInteractionSpot 완료 → ActionCompleted(agentId, "sitAtChair", true)
  - 각 액션 타입별 완료/실패 감지 및 발행

### 3. Payload
- `ActionPayloads.cs`에 ActionCompletedPayload가 이미 있으면 확인
  - AgentId, ActionType, Success, ErrorMessage 필드

### 4. GolemBootstrap에 등록
- AgentFeedbackReporter를 GolemBootstrap 초기화 흐름에 추가

## Data Flow
```
GolemCharacterController → 액션 실행
  → PointClickController.MoveToPointPublic() 완료
  → Managers.PublishAction(Agent_ActionCompleted, payload)
  → AgentFeedbackReporter.OnActionCompleted()
  → CFConnector.SendRpcFireAndForget("action_completed", json)
  → AI Server receives feedback
  → AI Server sends next action
  → CFConnector.OnCharacterAction → AINetworkManager → ActionBus → GolemCharacterController
  → (사이클 반복)
```

## Dependencies
- Phase 1-8 Infrastructure 전부 완료 필수
- CFConnector.SendRpcFireAndForget() 메서드 사용 가능

## Critical Constraints
- **DO NOT modify** CFConnector.cs
- JSON 직렬화: Unity JsonUtility 또는 anonymous object
- 실패 보고 시 ErrorMessage는 간결하게 (200자 이내)
- 비동기 발송: SendRpcFireAndForget (응답 대기 안 함)

## Success Criteria
- [ ] AgentFeedbackReporter.cs 생성
- [ ] ActionBus 구독 및 CFConnector 전송
- [ ] GolemCharacterController에서 액션 완료/실패 시 이벤트 발행
- [ ] GolemBootstrap에 등록
- [ ] 전체 피드백 루프 동작 (에디터 로그로 확인)
- [ ] Unity 컴파일 에러 없음
