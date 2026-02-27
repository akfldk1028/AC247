# Golem CFConnector Agent

## Role
WebSocket 통신 및 CFConnector 전문 에이전트.
AI 서버와의 실시간 양방향 통신, JSON RPC 프로토콜, 이벤트 디스패칭을 담당한다.

## CRITICAL RULE: DO NOT MODIFY CFConnector.cs
`Assets/Scripts/Systems/Networking/CFConnector.cs`는 **절대 수정하지 않는다**.
이 파일은 동작 검증이 완료된 기존 코드이며, namespace가 없다.
모든 확장은 AINetworkManager 또는 새로운 wrapper 클래스에서 처리한다.

## CFConnector Event List (12 Events)
CFConnector가 AI 서버로부터 수신하여 발행하는 C# 이벤트:

```csharp
// Connection 이벤트
public event Action OnOpen;                    // WebSocket 연결 성공
public event Action<string> OnClose;           // WebSocket 연결 종료 (reason)
public event Action<string> OnError;           // WebSocket 에러 (error message)

// Message 이벤트
public event Action<string> OnMessage;         // Raw JSON 메시지 수신

// Character/Agent 이벤트 (파싱된 구조체)
public event Action<VoiceEmote> OnVoiceEmote;              // 음성 이모트
public event Action<AnimatedEmote> OnAnimatedEmote;        // 애니메이션 이모트
public event Action<FacialExpression> OnFacialExpression;  // 표정 변화
public event Action<CharacterAction> OnCharacterAction;    // 캐릭터 액션 명령
public event Action<AgentState> OnAgentState;              // 에이전트 상태 변경

// TTS 이벤트
public event Action<byte[]> OnTTSAudio;        // TTS 오디오 데이터 수신
public event Action OnTTSAudioEnd;             // TTS 재생 완료 신호
```

## Data Types (7 Types)
CFConnector가 파싱하여 이벤트로 전달하는 데이터 구조체:

```csharp
// 캐릭터 액션 명령
public struct CharacterAction
{
    public string agentId;      // 대상 에이전트 ID
    public string actionType;   // "moveToLocation", "sitAtChair", "standUp", etc.
    public string target;       // 대상 위치/오브젝트 이름
    public string[] parameters; // 추가 파라미터
}

// 음성 이모트
public struct VoiceEmote
{
    public string agentId;
    public string emoteName;    // 이모트 이름
    public float intensity;     // 강도 0~1
}

// 애니메이션 이모트
public struct AnimatedEmote
{
    public string agentId;
    public string animationName;  // 애니메이션 클립 이름
    public float duration;        // 재생 시간
}

// 표정
public struct FacialExpression
{
    public string agentId;
    public string expressionName;  // 표정 이름
    public float intensity;        // 강도 0~1
    public float duration;         // 유지 시간
}

// 에이전트 상태
public struct AgentState
{
    public string agentId;
    public string state;          // "active", "idle", "thinking", etc.
    public string context;        // 추가 컨텍스트 정보
}
```

## RPC Methods (서버로 전송)
```csharp
// 응답을 기다리는 RPC 호출
public async Task<string> SendRpc(string method, object payload);

// Fire-and-forget RPC (응답 불필요)
public void SendRpcFireAndForget(string method, object payload);
```

### 주요 RPC 호출 패턴
```csharp
// 액션 완료 피드백
cfConnector.SendRpcFireAndForget("action_completed", new {
    agentId = agentId,
    actionType = actionType,
    success = true,
    timestamp = DateTime.UtcNow
});

// 에이전트 상태 보고
cfConnector.SendRpcFireAndForget("agent_state_update", new {
    agentId = agentId,
    state = "idle",
    position = new { x = pos.x, y = pos.y, z = pos.z }
});
```

## AINetworkManager Bridge 패턴
CFConnector 이벤트를 ActionBus로 브릿지하는 방식:

```csharp
// AINetworkManager에서 CFConnector 이벤트를 구독하여 ActionBus로 변환
public class AINetworkManager : MonoBehaviour
{
    [SerializeField] private CFConnector cfConnector;

    private void OnEnable()
    {
        cfConnector.OnCharacterAction += HandleCharacterAction;
        cfConnector.OnVoiceEmote += HandleVoiceEmote;
        cfConnector.OnAgentState += HandleAgentState;
        // ... 나머지 이벤트 구독
    }

    private void HandleCharacterAction(CharacterAction action)
    {
        // CFConnector 데이터 → ActionPayload 변환 → ActionBus 발행
        var payload = new CharacterActionPayload(action);
        Managers.PublishAction(ActionId.Agent_CharacterAction, payload);
    }
}
```

## WebSocket 연결 상태 관리
```
Disconnected → Connecting → Connected → Active
                    ↓           ↓
                  Error     Disconnected (재연결 시도)
```

- 연결 실패 시 자동 재연결 (exponential backoff)
- `OnOpen` → `ActionId.System_NetworkConnected` 발행
- `OnClose` → `ActionId.System_NetworkDisconnected` 발행
- `OnError` → `ActionId.System_NetworkError` 발행

## 구현 시 주의사항
1. CFConnector.cs는 읽기 전용. 모든 변경은 AINetworkManager 또는 새 파일에서
2. CFConnector 이벤트 핸들러는 메인 스레드에서 실행됨을 보장할 것
3. JSON 파싱 에러 핸들링 필수 (서버 메시지 형식 변경 대비)
4. RPC 전송 시 연결 상태 확인 후 전송
5. 대용량 TTS 오디오 데이터는 스트리밍 방식 고려
