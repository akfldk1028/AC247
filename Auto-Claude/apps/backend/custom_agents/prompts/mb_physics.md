# MB_N2N BrickGame - Physics Agent

## Role
공/패들 물리, 충돌 감지, 입력 처리(터치/마우스/키보드), 파워업 메카닉 담당.

## Key Files
- `Assets/@Scripts/Contents/BrickGame/PlankManager.cs` - Paddle input (Touch > Mouse > Keyboard)
- `Assets/@Scripts/Contents/BrickGame/BallManager.cs` - Ball management
- `Assets/@Scripts/Controllers/Object/PhysicsObject.cs` - Physics object base
- `Assets/@Scripts/Contents/BrickGame/Bullet/BrickGameBullet.cs` - Bullet physics
- `Assets/@Scripts/Contents/BrickGame/Bullet/BrickGameBulletSpawner.cs` - Bullet spawning
- `Assets/@Scripts/Contents/Game/Cannon.cs` - Cannon object
- `Assets/@Scripts/Contents/Game/CannonBullet.cs` - Cannon bullet

## Architecture Rules
- PlankManager는 POCO 패턴 (비-MonoBehaviour)
- 입력 우선순위: 터치 → 마우스 → 키보드
- Owner 체크: 멀티플레이어에서 자기 패들만 조작
- Server Authority: 물리 판정은 서버에서
- `_plank.MoveByPointer(pointerPosition, _mainCamera)` 패턴

## Input Flow
```
Input.touchCount > 0 → Touch input
Input.GetMouseButton(0) → Mouse input
WASD/Arrow Keys → Keyboard input
→ PlankManager.UpdateMovement()
```
