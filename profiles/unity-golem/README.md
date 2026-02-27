# Unity-Golem Profile for AC247 Auto-Claude

## Overview
Golem AI Agent System 전용 프로파일. 가상 AI 에이전트 캐릭터 시스템 구현에 특화.

- **Golem 프로젝트**: `C:/DK/GL/Golem` (Unity 6000.3.3f1, URP, Mono)
- **참조 아키텍처**: `C:/DK/GL/MB_N2N` (Service Locator, ActionMessageBus, StateMachine 패턴 검증 완료)
- **기반 프로파일**: `profiles/unity/` (범용 Unity 에이전트 상속)

## 시스템 아키텍처
```
AI Server (WebSocket)
  ↕ JSON RPC
CFConnector (WebSocket 클라이언트)
  ↓ C# Events (OnMessage, OnCharacterAction, OnVoiceEmote, ...)
AINetworkManager (Bridge Layer)
  ↓ ActionMessageBus Publish
ActionBus (ActionId 기반 글로벌 이벤트)
  ↓ Subscribe
GolemCharacterController → PointClickController (NavMesh 이동)
                         → GolemEmoteHandler (음성/애니/표정)
                         → CelesteActionController (액션 실행)
  ↓ ActionCompleted
AgentFeedbackReporter → CFConnector.SendRpc → AI Server
```

## 에이전트 구성

| Agent | 역할 | 프롬프트 |
|-------|------|---------|
| `golem_cfconnector` | WebSocket/CFConnector 통신 전문가 | `golem_cfconnector.md` |
| `golem_character` | 캐릭터 컨트롤러/액션/이모트 전문가 | `golem_character.md` |
| `golem_ai_bridge` | AINetworkManager 브릿지/상태관리 전문가 | `golem_ai_bridge.md` |

## 디렉토리 구조
```
profiles/unity-golem/
  ├── README.md                          # 이 파일
  ├── agents/
  │   └── golem-agents.json              # Golem 특화 에이전트 설정
  ├── prompts/
  │   ├── golem_cfconnector.md           # WebSocket/CFConnector 전문
  │   ├── golem_character.md             # 캐릭터 컨트롤러 전문
  │   └── golem_ai_bridge.md             # AINetworkManager 브릿지 전문
  └── spec-templates/
      ├── new-character-action/          # 새 캐릭터 액션 추가 (moveToLocation 같은)
      ├── new-emote-type/                # 새 이모트 타입 추가 (VoiceEmote 같은)
      ├── new-interaction-spot/          # 새 인터랙션 스팟 추가 (의자, 아케이드 같은)
      ├── feedback-reporter/             # AI 서버 피드백 루프 구현
      └── agent-behavior/               # 자율 행동 추가 (Wander, LookAround 같은)
```

## 수정 불가 파일 (DO NOT MODIFY)
기존 동작 검증 완료된 파일 - 절대 수정하지 않고 wrapper/bridge로 연결:
- `Assets/Scripts/Systems/Networking/CFConnector.cs`
- `Assets/Scripts/Character/CelesteActionController.cs`
- `Assets/Scripts/Character/PointClickController.cs`
- `Assets/Scripts/Character/EmotePlayer.cs`
- `Assets/Scripts/Systems/Camera/CameraStateMachine.cs`
- `Assets/Scripts/Utils/WavUtility.cs`

## 네임스페이스 규칙
- 기존 파일: namespace 없음 (그대로 유지)
- 신규 파일: `Golem.Infrastructure.Messages`, `Golem.Infrastructure.State` 등 사용

## 참조 프로젝트 (MB_N2N)
포팅할 패턴의 원본 소스:
- `Assets/@Scripts/Infrastructure/Messages/` - ActionMessageBus, ActionId, IActionPayload
- `Assets/@Scripts/Infrastructure/State/` - StateMachine, IState
- `Assets/@Scripts/Managers/` - Service Locator, Managers 싱글턴

## 사용법

### 1. Golem 프로젝트에 적용
```bash
# project.json은 이미 존재: C:/DK/GL/Golem/.auto-claude/project.json
# 이 프로파일의 에이전트를 custom_agents로 등록

# daemon 실행
python daemon_runner.py --project-dir C:/DK/GL/Golem --profile unity-golem
```

### 2. spec-templates 사용 (재탕삼탕)
```bash
# 예: 새 캐릭터 액션 "pickUpItem" 추가
cp -r profiles/unity-golem/spec-templates/new-character-action \
  C:/DK/GL/Golem/.auto-claude/specs/009-pick-up-item

# spec.md에서 placeholder 치환
sed -i 's/{ACTION_NAME}/PickUpItem/g' .../009-pick-up-item/spec.md
sed -i 's/{ACTION_TYPE_STRING}/pickUpItem/g' .../009-pick-up-item/spec.md
# ... 나머지 placeholder도 치환

# daemon이 자동으로 감지 → 빌드 → QA → 완료
```

### 5개 템플릿 요약

| 템플릿 | 용도 | 수정 파일 수 |
|--------|------|-------------|
| `new-character-action` | AI 명령으로 실행하는 새 행동 | 4개 (ActionId, Payloads, AINetworkManager, GolemCharacterController) |
| `new-emote-type` | 음성/애니/표정 새 타입 | 4개 (ActionId, Payloads, AINetworkManager, GolemEmoteHandler) |
| `new-interaction-spot` | 씬 내 새 상호작용 포인트 | 5개 (InteractionType, ActionId, PointClick, AINet, GolemCC) |
| `feedback-reporter` | AI 서버 피드백 루프 | 3개 (FeedbackReporter 신규, GolemCC, GolemBootstrap) |
| `agent-behavior` | 자율 행동 (명령 없이 스스로) | 3개 (StateId, BehaviorState 신규, GolemBootstrap) |

### 3. 기반 프로파일과 함께 사용
unity-golem 에이전트는 기반 unity 프로파일의 에이전트(unity_managers, unity_infrastructure 등)와 함께 동작.
Golem 특화 작업은 golem_* 에이전트가, 범용 Unity 작업은 unity_* 에이전트가 처리.
