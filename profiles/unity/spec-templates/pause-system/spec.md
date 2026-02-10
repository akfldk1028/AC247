# Pause System - TEMPLATE

## Overview
게임 중 일시정지 기능. Time.timeScale = 0 기반.
GamePhase에 Paused 추가, ActionBus로 Pause/Resume 이벤트 발행.

## Architecture Rules
- GamePhase enum에 Paused 상태 추가
- Game Manager에 PauseGame()/ResumeGame() 메서드 추가
- UI_PausePopup은 UIManager 팝업 스택 활용
- ActionBus로 GameStateChanged(Paused/Playing) 이벤트 발행
- Android 백 버튼, 앱 백그라운드 시 자동 일시정지

## UI_PausePopup
- "Continue" → ResumeGame()
- "Restart" → RestartGame()
- "Settings" → ShowPopupUI<UI_SettingsPopup>()
- "Exit" → LoadScene(StartUpScene)
