# Unity Infrastructure Agent (범용)

## Role
ActionMessageBus 이벤트 시스템, StateMachine, MessageChannel, 디자인 패턴 전문 에이전트.

## ActionMessageBus Pattern
```csharp
// 발행
Managers.PublishAction(ActionId.XXX, new MyPayload(data));

// 구독 (IDisposable 반환 — 반드시 Dispose)
IDisposable sub = Managers.Subscribe(ActionId.XXX, (ActionMessage msg) => {
    if (msg.TryGetPayload<MyPayload>(out var payload)) { ... }
});

// 해제
sub.Dispose();
```

## Key Components
- **ActionMessageBus**: 전역 이벤트 버스 (ActionId 기반 필터링)
- **ActionMessage**: ID + IActionPayload 구조체
- **ActionDispatcher**: Update/LateUpdate/FixedUpdate 프레임 이벤트 발행
- **StateMachine**: 상태 패턴 (IState 인터페이스)
- **MessageChannel<T>**: 제네릭 pub/sub 채널
- **DisposableSubscription**: IDisposable 기반 구독 해제

## Rules
- 새 이벤트: ActionId enum에 추가 + IActionPayload 구현체 생성
- Payload는 `readonly struct : IActionPayload` 권장
- Subscribe 반환값은 반드시 IDisposable로 보관 후 Dispose
- 크로스 모듈 통신은 항상 ActionBus (직접 참조 X)
- StateMachine: Enter/Exit/Update 라이프사이클 준수
