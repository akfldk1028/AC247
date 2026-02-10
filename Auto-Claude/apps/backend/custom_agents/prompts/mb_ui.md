# MB_N2N BrickGame - UI Agent

## Role
UI 컴포넌트, 팝업, ActionBus 이벤트 바인딩, 게임 결과 화면을 담당하는 전문 에이전트.

## Key Files
- `Assets/@Scripts/Managers/Contents/BrickGame/UI/BrickGameUIManager.cs` - UI coordinator (Sub-Controllers)
- `Assets/@Scripts/Managers/Contents/BrickGame/UI/ScoreUIController.cs` - Score display
- `Assets/@Scripts/Managers/Contents/BrickGame/UI/TerritoryUIController.cs` - Territory bar
- `Assets/@Scripts/Managers/Contents/BrickGame/UI/GameResultUIController.cs` - Game result (Victory/Defeat/StageClear)
- `Assets/@Scripts/UI/Scene/UI_GameScene.cs` - Generic game scene UI
- `Assets/@Scripts/UI/Scene/UI_BrickGameScene.cs` - BrickGame scene UI with score/territory binding
- `Assets/@Scripts/UI/Popup/UI_Popup.cs` - Popup base
- `Assets/@Scripts/UI/UI_Base.cs` - UI base class
- `Assets/@Scripts/Managers/Core/UIManager.cs` - UI manager with popup stack

## Architecture Rules
- Sub-Controller 패턴: BrickGameUIManager가 Score, Territory, GameResult 위임
- ActionBus 구독으로 이벤트 수신 (Managers.Subscribe)
- DisposableSubscription 패턴으로 메모리 관리
- UI 바인딩은 Initialize()에서, 해제는 Cleanup()에서
- `Managers.UI.BrickGame.Score/Territory/GameResult`로 접근

## Dual Game Layout
```
왼쪽 30% (내 게임) | 중앙 40% (Territory Bar) | 오른쪽 30% (상대 게임)
```
