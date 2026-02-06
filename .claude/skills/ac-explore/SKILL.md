---
name: ac-explore
description: |
  Auto-Claude 코드베이스 탐색. 아키텍처 이해, 코드 흐름 추적, 파일 찾기.
  사용 시점: (1) 코드 구조 파악, (2) 특정 기능의 구현 위치 찾기, (3) 데이터 흐름 추적
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob
user-invocable: false
---

# Auto-Claude Codebase Explorer

Auto-Claude 코드베이스를 읽기 전용으로 탐색합니다.

## Architecture Quick Reference

### Pipeline Flow
```
spec_runner.py → orchestrator.py → PhaseExecutor (6-8 phases)
  → run.py → planner.py → coder.py → reviewer.py → fixer.py
  → finalization.py (merge/review)
```

### Key Entry Points

| Entry | File | Purpose |
|-------|------|---------|
| Spec creation | `runners/spec_runner.py` | CLI → orchestrator |
| Build execution | `run.py` | Plan → Code → QA → Merge |
| Daemon | `runners/daemon_runner.py` | 24/7 task watcher |
| UI | `frontend/src/main/agent/agent-manager.ts` | Electron → Python |

### Backend Directory Map

```
apps/backend/
├── spec/              # Spec creation pipeline
│   ├── pipeline/      # orchestrator.py, agent_runner.py
│   ├── phases/        # 6 phase modules (discovery, requirements, spec, planning...)
│   └── validate_pkg/  # SpecValidator
├── agents/            # planner.py, coder.py, session management
├── qa/                # reviewer.py, fixer.py, loop logic
├── core/              # client.py, auth, workspace/, platform/
├── services/          # task_daemon/, spec_factory.py
├── prompts/           # Agent system prompts (.md files)
└── runners/           # CLI entry points
```

### Frontend Directory Map

```
apps/frontend/src/
├── main/              # Electron main process
│   ├── agent/         # Agent lifecycle management
│   ├── daemon-status-watcher.ts  # Daemon → UI bridge
│   ├── project-store.ts          # Task status mapping
│   └── task-state-manager.ts     # XState machine
├── renderer/          # React UI
│   ├── stores/        # 24+ Zustand stores
│   └── components/    # UI components
└── shared/            # Types, i18n, constants
```

### Status Field Locations

| Field | Written by | Read by |
|-------|-----------|---------|
| `status` | task_event.py | project-store.ts |
| `xstateState` | task_event.py | task-machine.ts |
| `planStatus` | task_event.py | project-store.ts |
| `executionPhase` | task_event.py | UI badges |
| `reviewReason` | finalization.py | task-detail panel |

## How to Search

### Find where an event is emitted
```
Grep for: emit_task_event.*EVENT_NAME
```

### Find where a status is set
```
Grep for: "status".*=.*"value"
```

### Find agent prompt
```
Glob: apps/backend/prompts/*.md
```

### Find phase implementation
```
Glob: apps/backend/spec/phases/*_phases.py
```
