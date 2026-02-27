# Golem AI Bridge Agent (AINetworkManager)

## Role
AINetworkManager 브릿지 계층 전문 에이전트.
CFConnector(WebSocket) ↔ ActionBus 간 데이터 변환, AgentManager 멀티에이전트 관리, StateMachine 상태 전이, 피드백 리포팅을 담당한다.

---

## 전체 데이터 흐름
```
AI Server (WebSocket, JSON RPC)
    ↕
CFConnector (C# Events)
    ↓ OnCharacterAction, OnVoiceEmote, OnAgentState, ...
AINetworkManager (Bridge: CFConnector → ActionBus 변환)
    ↓ Managers.PublishAction(ActionId.Agent_XXX, payload)
ActionBus (ActionId 기반 글로벌 이벤트 버스)
    ↓ Subscribe
GolemCharacterController → PointClickController (NavMesh 이동 실행)
                         → CelesteActionController (액션 실행)
                         → GolemEmoteHandler (이모트 재생)
    ↓ 액션 완료
Agent_ActionCompleted (ActionBus 이벤트)
    ↓
AgentFeedbackReporter → CFConnector.SendRpc() → AI Server
```

---

## ActionId Enum (전체 이벤트 카테고리)

### System 카테고리 (1000번대)
```csharp
// 시스템 수준 이벤트
System_NetworkConnected     = 1001,  // WebSocket 연결 성공
System_NetworkDisconnected  = 1002,  // WebSocket 연결 끊김
System_NetworkError         = 1003,  // WebSocket 에러
System_Initialized          = 1010,  // 시스템 초기화 완료
System_Shutdown             = 1099,  // 시스템 종료
```

### Agent 카테고리 (2000번대)
```csharp
// 에이전트 관련 이벤트
Agent_Registered            = 2001,  // 에이전트 등록
Agent_Unregistered          = 2002,  // 에이전트 해제
Agent_StateChanged          = 2010,  // 에이전트 상태 변경
Agent_CharacterAction       = 2100,  // 캐릭터 액션 명령
Agent_ActionCompleted       = 2101,  // 액션 실행 완료
Agent_ActionFailed          = 2102,  // 액션 실행 실패
Agent_VoiceEmote            = 2200,  // 음성 이모트
Agent_AnimatedEmote         = 2201,  // 애니메이션 이모트
Agent_FacialExpression      = 2202,  // 표정 변화
Agent_TTSAudio              = 2300,  // TTS 오디오 데이터
Agent_TTSAudioEnd           = 2301,  // TTS 재생 완료
```

### Character 카테고리 (3000번대)
```csharp
// 캐릭터 물리적 행동 이벤트
Character_MoveStarted       = 3001,  // 이동 시작
Character_MoveCompleted     = 3002,  // 이동 완료
Character_SitDown           = 3010,  // 앉기
Character_StandUp           = 3011,  // 일어서기
Character_Interact          = 3020,  // 인터랙션 시작
Character_InteractComplete  = 3021,  // 인터랙션 완료
```

### Camera 카테고리 (4000번대)
```csharp
// 카메라 관련 이벤트
Camera_AngleChanged         = 4001,  // 카메라 앵글 변경
Camera_FollowTarget         = 4002,  // 카메라 추적 대상 변경
Camera_TransitionStart      = 4010,  // 카메라 전환 시작
Camera_TransitionComplete   = 4011,  // 카메라 전환 완료
```

---

## ActionPayload Types (IActionPayload 구현체)

### CharacterActionPayload
```csharp
public readonly struct CharacterActionPayload : IActionPayload
{
    public readonly string AgentId;
    public readonly string ActionType;    // "moveToLocation", "sitAtChair", etc.
    public readonly string Target;        // InteractionSpot 이름
    public readonly string[] Parameters;

    public CharacterActionPayload(CharacterAction action)
    {
        AgentId = action.agentId;
        ActionType = action.actionType;
        Target = action.target;
        Parameters = action.parameters;
    }
}
```

### VoiceEmotePayload
```csharp
public readonly struct VoiceEmotePayload : IActionPayload
{
    public readonly string AgentId;
    public readonly string EmoteName;
    public readonly float Intensity;

    public VoiceEmotePayload(VoiceEmote emote)
    {
        AgentId = emote.agentId;
        EmoteName = emote.emoteName;
        Intensity = emote.intensity;
    }
}
```

### AnimatedEmotePayload
```csharp
public readonly struct AnimatedEmotePayload : IActionPayload
{
    public readonly string AgentId;
    public readonly string AnimationName;
    public readonly float Duration;
}
```

### FacialExpressionPayload
```csharp
public readonly struct FacialExpressionPayload : IActionPayload
{
    public readonly string AgentId;
    public readonly string ExpressionName;
    public readonly float Intensity;
    public readonly float Duration;
}
```

### AgentStatePayload
```csharp
public readonly struct AgentStatePayload : IActionPayload
{
    public readonly string AgentId;
    public readonly string State;
    public readonly string Context;
}
```

### ActionCompletedPayload
```csharp
public readonly struct ActionCompletedPayload : IActionPayload
{
    public readonly string AgentId;
    public readonly string ActionType;
    public readonly bool Success;
    public readonly string ErrorMessage;  // 실패 시 에러 메시지
}
```

### TTSAudioPayload
```csharp
public readonly struct TTSAudioPayload : IActionPayload
{
    public readonly string AgentId;
    public readonly byte[] AudioData;
}
```

---

## AgentManager (멀티 에이전트 관리)

### 구조
```csharp
public class AgentManager
{
    private Dictionary<string, AgentInstance> _agents = new();

    // 에이전트 등록 (AI 서버로부터 새 에이전트 접속 시)
    public void Register(string agentId, AgentInstance instance)
    {
        _agents[agentId] = instance;
        Managers.PublishAction(ActionId.Agent_Registered,
            new AgentRegisteredPayload(agentId));
    }

    // 에이전트 해제
    public void Unregister(string agentId)
    {
        if (_agents.Remove(agentId))
        {
            Managers.PublishAction(ActionId.Agent_Unregistered,
                new AgentUnregisteredPayload(agentId));
        }
    }

    // 에이전트 조회
    public AgentInstance GetAgent(string agentId)
    {
        return _agents.TryGetValue(agentId, out var agent) ? agent : null;
    }

    // 모든 에이전트 조회
    public IReadOnlyDictionary<string, AgentInstance> GetAllAgents() => _agents;

    // 에이전트 존재 여부
    public bool HasAgent(string agentId) => _agents.ContainsKey(agentId);
}
```

### AgentInstance 구조
```csharp
public class AgentInstance
{
    public string AgentId { get; }
    public string DisplayName { get; set; }
    public AgentStateMachine StateMachine { get; }
    public GameObject CharacterObject { get; set; }    // 씬 내 3D 캐릭터
    public GolemCharacterController Controller { get; set; }
    public GolemEmoteHandler EmoteHandler { get; set; }

    public AgentInstance(string agentId)
    {
        AgentId = agentId;
        StateMachine = new AgentStateMachine();
    }
}
```

### 멀티 에이전트 지원 패턴
```csharp
// AINetworkManager에서 에이전트별 이벤트 라우팅
private void HandleCharacterAction(CharacterAction action)
{
    var agent = Managers.Agent.GetAgent(action.agentId);
    if (agent == null)
    {
        Debug.LogWarning($"Unknown agent: {action.agentId}");
        return;
    }

    // 해당 에이전트의 컨트롤러로 액션 전달
    var payload = new CharacterActionPayload(action);
    Managers.PublishAction(ActionId.Agent_CharacterAction, payload);
}
```

### Managers 등록
```csharp
// Managers.cs에 AgentManager 추가
public class Managers : MonoBehaviour
{
    private AgentManager _agent = new AgentManager();
    public static AgentManager Agent => Instance?._agent;
}
```

---

## StateMachine (에이전트 상태 관리)

### 상태 목록
```csharp
public enum AgentStateType
{
    Boot,           // 최초 생성, 초기화 전
    Initializing,   // 초기화 진행 중 (리소스 로딩, 캐릭터 스폰)
    Connected,      // WebSocket 연결됨, 아직 활성화 전
    Disconnected,   // WebSocket 연결 끊김 (재연결 대기)
    Active,         // 활성 상태 (명령 수신 및 실행 가능)
    Idle,           // 대기 상태 (명령 대기 중)
    Performing      // 액션 수행 중 (이동, 인터랙션 등)
}
```

### 상태 전이 다이어그램
```
Boot → Initializing → Connected → Active ↔ Idle
                          ↓          ↓        ↓
                     Disconnected  Performing  Performing
                          ↓          ↓
                     Connected    Active/Idle
```

### 상태별 동작

| State | 진입 조건 | 동작 | 퇴장 조건 |
|-------|----------|------|----------|
| `Boot` | 에이전트 생성 | 초기 설정 | Init() 호출 |
| `Initializing` | Init() | 리소스 로딩, 캐릭터 스폰 | 초기화 완료 |
| `Connected` | WebSocket OnOpen | 서버 핸드셰이크 | 활성화 명령 수신 |
| `Disconnected` | WebSocket OnClose | 재연결 시도 (backoff) | 재연결 성공 |
| `Active` | 서버 활성화 명령 | 명령 수신 가능 | 명령 없음 → Idle |
| `Idle` | 일정 시간 명령 없음 | Idle 애니메이션 | 새 명령 수신 → Active |
| `Performing` | 액션 시작 | 액션 실행 중 | 액션 완료/실패 |

### StateMachine 구현 (MB_N2N 패턴 참조)
```csharp
public class AgentStateMachine
{
    private IState _currentState;
    private Dictionary<AgentStateType, IState> _states = new();

    public AgentStateType CurrentStateType { get; private set; }

    public void AddState(AgentStateType type, IState state)
    {
        _states[type] = state;
    }

    public void ChangeState(AgentStateType newState)
    {
        _currentState?.Exit();
        CurrentStateType = newState;
        _currentState = _states[newState];
        _currentState.Enter();

        // 상태 변경 이벤트 발행
        Managers.PublishAction(ActionId.Agent_StateChanged,
            new AgentStatePayload { State = newState.ToString() });
    }

    public void Update() => _currentState?.Update();
}
```

---

## AgentFeedbackReporter (피드백 루프)
액션 완료/실패를 AI 서버에 보고하는 컴포넌트.

```csharp
public class AgentFeedbackReporter : MonoBehaviour
{
    [SerializeField] private CFConnector cfConnector;
    private IDisposable _completedSub;
    private IDisposable _failedSub;

    private void OnEnable()
    {
        _completedSub = Managers.Subscribe(ActionId.Agent_ActionCompleted, OnActionCompleted);
        _failedSub = Managers.Subscribe(ActionId.Agent_ActionFailed, OnActionFailed);
    }

    private void OnDisable()
    {
        _completedSub?.Dispose();
        _failedSub?.Dispose();
    }

    private void OnActionCompleted(ActionMessage msg)
    {
        if (msg.TryGetPayload<ActionCompletedPayload>(out var payload))
        {
            cfConnector.SendRpcFireAndForget("action_completed", new {
                agentId = payload.AgentId,
                actionType = payload.ActionType,
                success = true
            });
        }
    }

    private void OnActionFailed(ActionMessage msg)
    {
        if (msg.TryGetPayload<ActionCompletedPayload>(out var payload))
        {
            cfConnector.SendRpcFireAndForget("action_completed", new {
                agentId = payload.AgentId,
                actionType = payload.ActionType,
                success = false,
                error = payload.ErrorMessage
            });
        }
    }
}
```

---

## AINetworkManager 전체 구조
```csharp
// namespace 없음 (기존 CFConnector와 동일 레벨)
// 또는 Golem.Systems.Networking namespace 사용 가능
public class AINetworkManager : MonoBehaviour
{
    [Header("References")]
    [SerializeField] private CFConnector cfConnector;

    private void OnEnable()
    {
        // CFConnector 이벤트 → ActionBus 브릿지 등록
        cfConnector.OnOpen += HandleOpen;
        cfConnector.OnClose += HandleClose;
        cfConnector.OnError += HandleError;
        cfConnector.OnCharacterAction += HandleCharacterAction;
        cfConnector.OnVoiceEmote += HandleVoiceEmote;
        cfConnector.OnAnimatedEmote += HandleAnimatedEmote;
        cfConnector.OnFacialExpression += HandleFacialExpression;
        cfConnector.OnAgentState += HandleAgentState;
        cfConnector.OnTTSAudio += HandleTTSAudio;
        cfConnector.OnTTSAudioEnd += HandleTTSAudioEnd;
    }

    private void OnDisable()
    {
        // 모든 이벤트 구독 해제
        cfConnector.OnOpen -= HandleOpen;
        cfConnector.OnClose -= HandleClose;
        // ... etc
    }

    // 브릿지 메서드들
    private void HandleOpen()
        => Managers.PublishAction(ActionId.System_NetworkConnected, default);

    private void HandleClose(string reason)
        => Managers.PublishAction(ActionId.System_NetworkDisconnected, default);

    private void HandleCharacterAction(CharacterAction action)
        => Managers.PublishAction(ActionId.Agent_CharacterAction,
            new CharacterActionPayload(action));

    private void HandleVoiceEmote(VoiceEmote emote)
        => Managers.PublishAction(ActionId.Agent_VoiceEmote,
            new VoiceEmotePayload(emote));

    // ... 나머지 핸들러 동일 패턴
}
```

## 구현 시 주의사항
1. CFConnector.cs는 절대 수정하지 않는다 - AINetworkManager가 래핑
2. 모든 Payload는 `readonly struct : IActionPayload` 권장 (GC 최소화)
3. ActionId enum에 새 ID 추가 시 카테고리별 번호 대역 준수
4. AgentManager는 Managers의 Service Locator에 등록 (`Managers.Agent`)
5. StateMachine 상태 전이 시 항상 `Agent_StateChanged` 이벤트 발행
6. 멀티 에이전트: agentId로 구분, 각 에이전트가 독립 StateMachine 보유
7. 피드백 루프: 모든 액션은 성공/실패 결과를 AI 서버에 반드시 보고
8. MB_N2N 참조 경로: `C:/DK/GL/MB_N2N/Assets/@Scripts/Infrastructure/` 패턴 따르기
