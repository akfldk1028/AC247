# Agent Autonomous Behavior: {BEHAVIOR_NAME}

## Overview
Add autonomous behavior `{BEHAVIOR_NAME}` to the Golem AI agent.
에이전트가 AI 서버 명령 없이도 자율적으로 {BEHAVIOR_DESCRIPTION}를 수행하도록 합니다.

## Workflow Type
feature

## Task Scope

### 1. Behavior State 추가
- `Assets/Scripts/Infrastructure/State/StateId.cs`
  - `{BEHAVIOR_NAME} = {STATE_ID}` 추가

### 2. IState 구현
- `Assets/Scripts/Agent/Behaviors/{BEHAVIOR_NAME}State.cs` 신규 생성
  - `IState` 구현
  - Enter(): 행동 시작 조건 확인, 초기화
  - Update(): 매 프레임 행동 로직 (타이머, 조건 체크)
  - Exit(): 정리, 다음 상태 전이 준비
  - CanHandle(ActionMessage): 이 상태에서 처리 가능한 메시지 필터
  - Handle(ActionMessage): 인터럽트 처리 (AI 서버 명령이 오면 중단)

### 3. StateMachine에 등록
- `GolemBootstrap.cs` 또는 `AgentInstance` 초기화 시 새 State 등록
  - `stateMachine.AddState(StateId.{BEHAVIOR_NAME}, new {BEHAVIOR_NAME}State(controller))`

### 4. 전이 조건 설정
- Idle → {BEHAVIOR_NAME}: {IDLE_TO_BEHAVIOR_CONDITION}
- {BEHAVIOR_NAME} → Active: AI 서버 명령 수신 시
- {BEHAVIOR_NAME} → Idle: 행동 완료 시

### 5. ActionBus 연동
- 행동 중 발생하는 이벤트를 ActionBus로 발행
- 행동 완료 시 `Agent_ActionCompleted` 발행 (피드백 루프용)

## Dependencies
- Phase 1-8 Infrastructure 전부 완료 필수
- StateMachine, GolemCharacterController, PointClickController 동작 필수

## Critical Constraints
- **DO NOT modify** CFConnector.cs, CelesteActionController.cs, PointClickController.cs, EmotePlayer.cs
- 자율 행동은 AI 서버 명령에 의해 항상 인터럽트 가능해야 함
- State의 Update()에서 무거운 연산 금지 (프레임 드롭 방지)
- 상태 전이 시 항상 `Agent_StateChanged` 이벤트 발행

## Success Criteria
- [ ] {BEHAVIOR_NAME}State.cs 생성 (IState 구현)
- [ ] StateId에 새 상태 추가
- [ ] StateMachine에 등록
- [ ] 상태 전이 조건 동작
- [ ] AI 서버 명령으로 인터럽트 가능
- [ ] Unity 컴파일 에러 없음

## Placeholder Guide
- `{BEHAVIOR_NAME}` → PascalCase (예: Wander, LookAround, IdleAnimation)
- `{STATE_ID}` → 미사용 번호
- `{BEHAVIOR_DESCRIPTION}` → 행동 설명
- `{IDLE_TO_BEHAVIOR_CONDITION}` → Idle 상태에서 전이 조건 (예: 10초 경과, 랜덤 확률)
