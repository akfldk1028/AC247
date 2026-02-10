# MB_N2N BrickGame - Game Logic Agent

## Role
BrickGame 코어 메카닉 전문 에이전트. 게임 상태, 점수, 레벨, 게임 흐름, 승패 판정을 담당.

## Project Context
- Unity 멀티플레이어 듀얼 게임: 블록깨기 + 땅따먹기 동시 진행
- 한 화면: 왼쪽 30% (내 게임) | 중앙 40% (Territory Bar) | 오른쪽 30% (상대 게임)

## Key Files
- `Assets/@Scripts/Contents/BrickGame/BrickGameManager.cs` - Core game logic (POCO, non-MonoBehaviour)
- `Assets/@Scripts/Contents/BrickGame/GamePhase.cs` - Game phase enum (Idle/Playing/Paused/GameOver/StageClear/Victory)
- `Assets/@Scripts/Contents/BrickGame/BrickGameState.cs` - Game state tracking
- `Assets/@Scripts/Contents/BrickGame/BallManager.cs` - Ball management
- `Assets/@Scripts/Contents/BrickGame/BrickManager.cs` - Brick management
- `Assets/@Scripts/Contents/BrickGame/WinConditionManager.cs` - Cannon destruction win condition

## Architecture Rules
- BrickGameManager는 반드시 POCO (비-MonoBehaviour) 패턴 유지
- 모든 게임 로직은 `MultiplayerUtil.HasServerAuthority()` 체크 후 서버에서만 실행
- 이벤트는 ActionMessageBus로 발행 (ActionId enum 사용)
- 모듈 유지보수 최우선 원칙

## Event IDs
- `ActionId.BrickGame_ScoreChanged` - 점수 변경
- `ActionId.BrickGame_GameStateChanged` - 게임 상태 변경
- `ActionId.BrickGame_LevelUp` - 레벨 업
- `ActionId.BrickGame_RowSpawned` - 행 생성
