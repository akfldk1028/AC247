# MB_N2N BrickGame - Managers Agent

## Role
Service Locator (Managers.cs), DataManager, ResourceManager, PoolManager, UIManager, 초기화 흐름 담당.

## Key Files
- `Assets/@Scripts/Managers/Managers.cs` - Service Locator singleton (@Managers runtime GameObject)
- `Assets/@Scripts/Managers/Core/DataManager.cs` - Data loading
- `Assets/@Scripts/Managers/Core/ResourceManager.cs` - Resource management
- `Assets/@Scripts/Managers/Core/PoolManager.cs` - Object pooling
- `Assets/@Scripts/Managers/Core/UIManager.cs` - UI popup stack management
- `Assets/@Scripts/Managers/Core/SceneManagerEx.cs` - Scene transitions
- `Assets/@Scripts/Managers/Contents/GameManager.cs` - Game manager
- `Assets/@Scripts/Managers/Contents/ObjectManager.cs` - Object management
- `Assets/@Scripts/Managers/Contents/CameraManager.cs` - Camera management
- `Assets/@Scripts/Managers/Contents/MapManager.cs` - Map management
- `Assets/@Scripts/Managers/Contents/BrickGame/BrickGameSettings.cs` - BrickGame settings

## Architecture Rules
- @Managers GameObject는 런타임에만 존재 (DontDestroyOnLoad)
- Edit 모드에서 @Managers를 찾을 수 없음 (정상)
- Service Locator 접근: `Managers.Game.BrickGame`, `Managers.UI.BrickGame` 등
- 초기화 순서: Core Managers → Content Managers → Network → Game
- Managers.Subscribe() → DisposableSubscription 반환
- 새 Manager 추가 시 Managers.cs의 프로퍼티 + Init() 메서드에 등록

## Initialization Flow
```
Managers.Awake()
  → CreateManagers() [@Managers, @NetworkSystems]
  → DontDestroyOnLoad
  → Core: DataManager, ResourceManager, PoolManager, UIManager
  → Network: ConnectionManagerEx, LobbyServiceFacade
  → Game: GameManager, BrickGame
```
