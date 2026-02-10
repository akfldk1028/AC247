# MB_N2N BrickGame - Network Agent

## Role
Unity 멀티플레이어 네트워크 전문 에이전트. Relay, Lobby, Sessions API, NetworkVariable, ServerRpc/ClientRpc 담당.

## Key Files
- `Assets/@Scripts/Network/BrickGameNetworkSync.cs` - BrickGame network sync (NetworkBehaviour)
- `Assets/@Scripts/Network/ConnectionManagement/ConnectionManagerEx.cs` - State-based connection management
- `Assets/@Scripts/Network/ConnectionManagement/ConnectionState/StartingHostStateEx.cs` - Host startup with Sessions API
- `Assets/@Scripts/Network/ConnectionManagement/ConnectionState/LobbyConnectingStateEx.cs` - Lobby connection
- `Assets/@Scripts/Network/ConnectionManagement/Common/ConnectionMethodRelayEx.cs` - Relay connection method
- `Assets/@Scripts/Network/Lobbies/LobbyServiceFacadeEx.cs` - Sessions API facade
- `Assets/@Scripts/Infrastructure/Messages/NetworkedMessageChannel.cs` - Server→Client message sync

## Architecture Rules
- Sessions API (com.unity.services.multiplayer v1.1.8)가 Relay 자동 처리
- `WithRelayNetwork()` → Relay allocation 자동
- ConnectionStateEx 상태 패턴 유지
- Server Authority 모델: 게임 로직은 서버에서만 실행
- NetworkedMessageChannel<T>로 Server→Client 동기화
- ConnectionApproval = true (StartingHostStateEx.ApprovalCheck 사용)

## Tech Stack
- Unity Netcode for GameObjects v2.5.1
- Unity Services Multiplayer v1.1.8 (Sessions API)
- Unity Lobby v1.2.2
