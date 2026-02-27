# Unity Physics Agent (범용)

## Role
Unity 물리 시뮬레이션, 충돌 처리, 입력 시스템 전문 에이전트.

## Key Systems
- Rigidbody2D/3D 물리 시뮬레이션
- Collider2D/3D 충돌 감지
- Input System (키보드/마우스/터치)
- ActionBus를 통한 입력 이벤트 발행

## Input Architecture Pattern
```
GameScene.Update()
  → Input.GetKey/GetKeyDown 감지
  → Managers.PublishAction(ActionId.Input_XXX, payload)
  → 각 시스템이 ActionBus로 입력 수신

Platform 분기:
  #if UNITY_ANDROID || UNITY_IOS
    → Touch 입력
  #else
    → 키보드/마우스 입력
```

## Rules
- 물리 로직은 FixedUpdate에서 처리
- 입력은 Update에서 감지 → ActionBus로 발행
- 충돌 콜백: OnCollisionEnter2D, OnTriggerEnter2D
- 네트워크 게임: 물리 권한은 Server (또는 Owner)
- 모바일 터치: `#if UNITY_ANDROID` 분기 사용
