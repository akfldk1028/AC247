# Unity Profile for AC247 Auto-Claude

## Overview
Unity 게임 프로젝트용 범용 프로파일. 어떤 Unity 프로젝트에든 적용 가능.

## 사용법

### 1. 새 Unity 프로젝트에 적용
```bash
# 프로젝트에 .auto-claude 폴더 생성
mkdir -p <your-project>/.auto-claude/specs

# project.json 복사 후 수정
cp profiles/unity/project-template.json <your-project>/.auto-claude/project.json

# spec 템플릿 복사 후 프로젝트에 맞게 수정
cp -r profiles/unity/spec-templates/* <your-project>/.auto-claude/specs/
```

### 2. custom_agents 등록
```bash
# Unity 범용 에이전트를 custom_agents에 심볼릭 링크
# 또는 config.json에 직접 추가
```

### 3. 프로젝트 특화 프로파일 만들기
`profiles/unity-brickgame/` 처럼 게임별 프로파일 생성:
- agents/ - 게임 특화 에이전트
- prompts/ - 게임 특화 프롬프트
- spec-templates/ - 게임 특화 spec 템플릿

## 디렉토리 구조
```
profiles/unity/
  ├── README.md           # 이 파일
  ├── project-template.json  # 프로젝트 설정 템플릿
  ├── agents/
  │   └── unity-agents.json  # Unity 범용 에이전트 설정
  ├── prompts/
  │   ├── unity_managers.md  # Service Locator 패턴
  │   ├── unity_network.md   # Netcode/Relay 네트워킹
  │   ├── unity_ui.md        # UGUI/UI Toolkit
  │   └── unity_physics.md   # 물리/입력 처리
  └── spec-templates/
      ├── sound-system/      # 사운드 시스템 템플릿
      ├── vfx-system/        # VFX 시스템 템플릿
      ├── settings-screen/   # 설정 화면 템플릿
      ├── pause-system/      # 일시정지 템플릿
      ├── save-system/       # 저장 시스템 템플릿
      ├── mobile-polish/     # 모바일 최적화 템플릿
      └── tutorial-system/   # 튜토리얼 템플릿
```

## 재사용 ("재탕삼탕")
다른 Unity 프로젝트에서:
1. `project-template.json`을 복사 → 프로젝트 경로/이름 수정
2. `spec-templates/`에서 필요한 것만 복사
3. spec.md 내부의 파일 경로를 새 프로젝트에 맞게 수정
4. 데몬 실행: `python daemon_runner.py --project-dir <new-project>`
