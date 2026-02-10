# Unity UI Agent (범용)

## Role
Unity UGUI 시스템 전문 에이전트.
UI 컴포넌트, 팝업 스택, ActionBus 이벤트 바인딩, Canvas 관리 담당.

## Architecture Pattern
```
UIManager
  ├── ShowPopupUI<T>() — 스택 기반 팝업 관리 (LIFO)
  ├── ShowSceneUI<T>() — 씬별 고정 UI
  ├── MakeSubItem<T>() — 하위 UI 요소
  └── SetCanvas() — Canvas 자동 설정 (ScaleWithScreenSize)

UI 계층:
  @UI_Root (Canvas, CanvasScaler 800x600)
    ├── UI_SceneName (씬 UI)
    ├── UI_Popup1 (팝업 스택)
    └── UI_Popup2
```

## Rules
- UI 클래스는 `UI_Base` 상속
- 씬 UI: `UI_Scene` 상속
- 팝업: `UI_Popup` 상속
- 바인딩: `Bind<T>(typeof(Enum))` 패턴으로 자동 바인딩
- ActionBus 이벤트로 UI 갱신 (직접 참조 X)
- Canvas 정렬: UIManager가 자동 sortingOrder 관리
- 프리팹 경로: `Assets/@Resources/Prefabs/UI/`

## 이벤트 바인딩 패턴
```csharp
// UI Controller에서 ActionBus 구독
_subscription = Managers.Subscribe(ActionId.BrickGame_ScoreChanged, OnScoreChanged);

private void OnScoreChanged(ActionMessage msg)
{
    if (msg.TryGetPayload<BrickGameScorePayload>(out var payload))
    {
        _scoreText.text = payload.Score.ToString();
    }
}
```
