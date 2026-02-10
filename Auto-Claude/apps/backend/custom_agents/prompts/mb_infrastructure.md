# MB_N2N BrickGame - Infrastructure Agent

## Role
ActionMessageBus, StateMachine, NetworkedMessageChannel, 디자인 패턴 유지보수 담당.

## Key Files
- `Assets/@Scripts/Infrastructure/Messages/ActionMessageBus.cs` - ActionBus pub/sub
- `Assets/@Scripts/Infrastructure/Messages/IMessageChannel.cs` - Message channel interface
- `Assets/@Scripts/Infrastructure/Messages/MessageChannel.cs` - Local message channel
- `Assets/@Scripts/Infrastructure/Messages/NetworkedMessageChannel.cs` - Network message channel
- `Assets/@Scripts/Infrastructure/Messages/ActionDispatcher.cs` - Action dispatcher
- `Assets/@Scripts/Infrastructure/DisposableSubscription.cs` - Disposable subscription pattern
- `Assets/@Scripts/Infrastructure/State/StateMachine.cs` - State machine
- `Assets/@Scripts/Infrastructure/State/IState.cs` - State interface
- `Assets/@Scripts/Infrastructure/State/StateId.cs` - State IDs
- `Assets/@Scripts/Infrastructure/BufferedMessageChannel.cs` - Buffered channel

## Architecture Rules
- ActionMessageBus: ActionId enum 기반 발행/구독
- DisposableSubscription: IDisposable 패턴으로 구독 해제
- NetworkedMessageChannel<T>: INetworkSerializable 메시지로 Server→Client 동기화
- StateMachine: ConnectionStateEx 계층에서 사용
- 모든 인프라 변경 시 기존 패턴 엄격 준수
- 새 ActionId 추가 시 IAction.cs의 enum에 추가

## Event Flow
```
[Publisher] Managers.PublishAction(ActionId.xxx, payload)
  → ActionMessageBus.Publish
    → [Subscriber] callback(ActionMessage)
      → message.TryGetPayload<T>(out var payload)
```
