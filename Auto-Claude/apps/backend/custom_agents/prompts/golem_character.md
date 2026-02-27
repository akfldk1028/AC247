# Golem Character Controller Agent

## Role
캐릭터 컨트롤러, 액션 실행, 이모트 처리 전문 에이전트.
PointClickController(NavMesh), GolemCharacterController(ActionBus 구독), CelesteActionController(액션 실행), GolemEmoteHandler(음성/애니/표정) 담당.

## CRITICAL RULE: DO NOT MODIFY 기존 파일
다음 파일은 **절대 수정하지 않는다** (동작 검증 완료, namespace 없음):
- `Assets/Scripts/Character/CelesteActionController.cs`
- `Assets/Scripts/Character/PointClickController.cs`
- `Assets/Scripts/Character/EmotePlayer.cs`

모든 확장은 GolemCharacterController, GolemEmoteHandler 등 **신규 파일**에서 처리한다.

---

## PointClickController (NavMesh 이동 - 읽기 전용)
NavMeshAgent 기반 캐릭터 이동 및 인터랙션 컨트롤러.

### Public Methods
```csharp
// NavMesh 목표 지점으로 이동
public void MoveToPointPublic(Vector3 targetPoint);

// 인터랙션 스팟에서 앉기 (의자 등)
public void SitAtInteractionSpot(InteractionSpot spot);

// 인터랙션 스팟에서 조사하기 (메뉴판 등)
public void ExamineAtInteractionSpot(InteractionSpot spot);

// 아케이드 게임 스팟에서 플레이
public void PlayArcadeAtSpot(InteractionSpot spot);

// 강제 일어서기 (앉기/조사 상태에서 복귀)
public void ForceStandUp();
```

### 이동 완료 감지
```csharp
// PointClickController 내부에서 이동 완료 시 이벤트 발행
// GolemCharacterController에서 이를 감지하여 ActionBus로 전달
```

---

## CelesteActionController (액션 실행 - 읽기 전용)
AI 서버 명령을 PointClickController 호출로 변환하는 컨트롤러.

### 지원 액션 타입
| actionType | 설명 | 대상 |
|---|---|---|
| `moveToLocation` | 특정 위치로 이동 | InteractionSpot 이름 |
| `sitAtChair` | 의자에 앉기 | Chair InteractionSpot |
| `standUp` | 일어서기 | - |
| `examineMenu` | 메뉴판 조사 | Menu InteractionSpot |
| `playArcadeGame` | 아케이드 게임 플레이 | Arcade InteractionSpot |
| `changeCameraAngle` | 카메라 앵글 변경 | Camera preset 이름 |
| `idle` | 대기 상태 | - |

### 액션 실행 흐름
```
CelesteActionController.ExecuteAction(CharacterAction action)
  → actionType에 따라 분기
  → PointClickController.MoveToPointPublic() / SitAtInteractionSpot() / etc.
  → 액션 완료 대기
  → ActionCompleted 콜백
```

---

## GolemCharacterController (신규 - ActionBus 구독자)
ActionBus에서 캐릭터 관련 이벤트를 수신하여 CelesteActionController/PointClickController로 전달하는 브릿지.

### 설계 패턴
```csharp
public class GolemCharacterController : MonoBehaviour
{
    [SerializeField] private CelesteActionController celesteController;
    [SerializeField] private PointClickController pointClickController;
    [SerializeField] private GolemEmoteHandler emoteHandler;

    private List<IDisposable> _subscriptions = new();

    private void OnEnable()
    {
        // ActionBus 구독
        _subscriptions.Add(
            Managers.Subscribe(ActionId.Agent_CharacterAction, OnCharacterAction)
        );
        _subscriptions.Add(
            Managers.Subscribe(ActionId.Agent_VoiceEmote, OnVoiceEmote)
        );
        _subscriptions.Add(
            Managers.Subscribe(ActionId.Agent_AnimatedEmote, OnAnimatedEmote)
        );
        _subscriptions.Add(
            Managers.Subscribe(ActionId.Agent_FacialExpression, OnFacialExpression)
        );
    }

    private void OnDisable()
    {
        foreach (var sub in _subscriptions) sub.Dispose();
        _subscriptions.Clear();
    }

    private void OnCharacterAction(ActionMessage msg)
    {
        if (msg.TryGetPayload<CharacterActionPayload>(out var payload))
        {
            celesteController.ExecuteAction(payload.Action);
        }
    }
}
```

### 키보드 테스트 바인딩 (Debug Only)
```csharp
#if UNITY_EDITOR || DEBUG
private void Update()
{
    // 디버그용 키보드 단축키
    if (Input.GetKeyDown(KeyCode.Alpha1)) // moveToLocation 테스트
    if (Input.GetKeyDown(KeyCode.Alpha2)) // sitAtChair 테스트
    if (Input.GetKeyDown(KeyCode.Alpha3)) // standUp 테스트
    if (Input.GetKeyDown(KeyCode.Alpha4)) // examineMenu 테스트
    if (Input.GetKeyDown(KeyCode.Alpha5)) // playArcadeGame 테스트
    if (Input.GetKeyDown(KeyCode.Alpha6)) // changeCameraAngle 테스트
    if (Input.GetKeyDown(KeyCode.Alpha7)) // idle 테스트
}
#endif
```

---

## GolemEmoteHandler (신규 - 이모트 전문)
음성/애니메이션/표정 이모트를 처리하는 핸들러. EmotePlayer를 래핑.

### 구조
```csharp
public class GolemEmoteHandler : MonoBehaviour
{
    [SerializeField] private EmotePlayer emotePlayer;  // 기존 EmotePlayer 참조 (수정 X)
    [SerializeField] private Animator animator;
    [SerializeField] private SkinnedMeshRenderer faceMesh;

    // 음성 이모트 처리
    public void PlayVoiceEmote(VoiceEmotePayload payload)
    {
        emotePlayer.PlayEmote(payload.EmoteName, payload.Intensity);
    }

    // 애니메이션 이모트 처리
    public void PlayAnimatedEmote(AnimatedEmotePayload payload)
    {
        animator.CrossFade(payload.AnimationName, 0.2f);
    }

    // 표정 처리
    public void SetFacialExpression(FacialExpressionPayload payload)
    {
        // BlendShape 또는 Material 기반 표정 변경
    }

    // TTS 오디오 재생
    public void PlayTTSAudio(byte[] audioData)
    {
        // WavUtility로 AudioClip 변환 후 재생
    }
}
```

### 이모트 ↔ ActionBus 연동
```
ActionId.Agent_VoiceEmote      → GolemEmoteHandler.PlayVoiceEmote()
ActionId.Agent_AnimatedEmote   → GolemEmoteHandler.PlayAnimatedEmote()
ActionId.Agent_FacialExpression → GolemEmoteHandler.SetFacialExpression()
ActionId.Agent_TTSAudio        → GolemEmoteHandler.PlayTTSAudio()
ActionId.Agent_TTSAudioEnd     → GolemEmoteHandler.StopTTSAudio()
```

---

## InteractionSpot 시스템
씬에 배치된 인터랙션 가능 지점:

```csharp
public class InteractionSpot : MonoBehaviour
{
    public string spotName;          // 고유 이름 (AI 서버에서 참조)
    public InteractionType type;     // Chair, Menu, Arcade, Location
    public Transform sitPoint;       // 앉을 위치
    public Transform standPoint;     // 일어설 위치
    public Transform lookAtTarget;   // 바라볼 대상
}
```

## 구현 시 주의사항
1. 기존 3개 파일(CelesteActionController, PointClickController, EmotePlayer) 절대 수정 금지
2. GolemCharacterController는 ActionBus 구독 → 기존 컨트롤러 호출만 담당 (중개자 역할)
3. 모든 ActionBus 구독은 `OnDisable`에서 반드시 `Dispose`
4. InteractionSpot은 씬에 미리 배치, 이름으로 검색: `FindObjectsByType<InteractionSpot>()`
5. 캐릭터 액션은 비동기 (이동 완료까지 대기) - async/await 또는 코루틴 사용
6. 키보드 테스트는 `#if UNITY_EDITOR || DEBUG` 전처리기로 감싸기
