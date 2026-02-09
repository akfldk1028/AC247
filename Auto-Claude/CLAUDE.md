# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

Auto Claude is an autonomous multi-agent coding framework that plans, builds, and validates software for you. It's a monorepo with a Python backend (CLI + agent logic) and an Electron/React frontend (desktop UI).

> **Deep-dive reference:** [ARCHITECTURE.md](shared_docs/ARCHITECTURE.md) | **All docs:** [docs/INDEX.md](docs/INDEX.md) | **Frontend contributing:** [apps/frontend/CONTRIBUTING.md](apps/frontend/CONTRIBUTING.md)

## Known Issues & Critical Fixes (Troubleshooting)

> **Read this before debugging the spec pipeline or daemon.** These are hard-won lessons from multi-session debugging.

### 1. Stale `spec_dir` after rename (CRITICAL)

**Symptom:** `phase_spec_writing` fails 3 times with "Agent did not create spec.md" even though the agent DID create it.

**Root cause:** After `_rename_spec_dir_from_requirements()` in `orchestrator.py`, the disk path changes from `001-pending` → `001-meaningful-name`. But `PhaseExecutor.spec_dir`, `PhaseExecutor.spec_validator`, and `TaskLogger` still point to the old `001-pending` path.

**Fix location:** `spec/pipeline/orchestrator.py` — after calling `_rename_spec_dir_from_requirements()`, ALL references must be synced:

```python
# After rename, sync all references:
self.validator = SpecValidator(self.spec_dir)
task_logger = get_task_logger(self.spec_dir)
phase_executor.spec_dir = self.spec_dir
phase_executor.spec_validator = self.validator
phase_executor.task_logger = task_logger
```

**Rule:** Any time `self.spec_dir` changes, **every component holding a copy must be updated.**

### 2. File-exists-but-success=False pattern

**Symptom:** Agent creates valid files (spec.md, implementation_plan.json, research.json) but the phase reports failure.

**Root cause:** `agent_runner.py:run_agent()` returns `(success=False, error_text)` when the SDK throws ANY exception (rate limit, timeout, network error) — even if the agent already created the target file before the error.

**Fix pattern:** Always check file existence FIRST, regardless of the `success` flag:

```python
if target_file.exists():
    result = validator.validate(target_file)
    if result.valid:
        if not success:
            log("Agent errored but file is valid, accepting")
        return PhaseResult(phase_name, True, ...)
else:
    error_detail = output[:200] if output else "unknown error"
    errors.append(f"Agent did not create {target_file.name} ({error_detail})")
```

**Applies to:** `spec_phases.py`, `planning_phases.py`, `requirements_phases.py`

### 3. Daemon status writer loop condition (Windows)

**Symptom:** Status writer thread doesn't stop cleanly on shutdown.

**Fix:** Use `while not daemon._stop_event.is_set()` (not `or` conditions). Also add retry for `temp_path.replace()` on Windows due to file locks from UI reading.

### 4. Windows platform gotchas

- **`subprocess.run()` instead of `os.execv()`** — `os.execv()` breaks Electron → Python connection on Windows
- **Always `encoding='utf-8'`** for file reads — Windows defaults to system locale encoding
- **File lock retry** — When replacing files that the UI may be reading, retry 2-3 times with 100ms delay

## Product Overview

Auto Claude is a desktop application (+ CLI) where users describe a goal and AI agents autonomously handle planning, implementation, and QA validation. All work happens in isolated git worktrees so the main branch stays safe.

**Core workflow:** User creates a task → Spec creation pipeline assesses complexity and writes a specification → Planner agent breaks it into subtasks → Coder agent implements (can spawn parallel subagents) → QA reviewer validates → QA fixer resolves issues → User reviews and merges.

**Main features:**

- **Autonomous Tasks** — Multi-agent pipeline (planner, coder, QA) that builds features end-to-end
- **Kanban Board** — Visual task management from planning through completion
- **Agent Terminals** — Up to 12 parallel AI-powered terminals with task context injection
- **Insights** — AI chat interface for exploring and understanding your codebase
- **Roadmap** — AI-assisted feature planning with strategic roadmap generation
- **Ideation** — Discover improvements, performance issues, and security vulnerabilities
- **GitHub/GitLab Integration** — Import issues, AI-powered investigation, PR/MR review and creation
- **Changelog** — Generate release notes from completed tasks
- **Memory System** — Graphiti-based knowledge graph retains insights across sessions
- **Isolated Workspaces** — Git worktree isolation for every build; AI-powered semantic merge
- **Flexible Authentication** — Use a Claude Code subscription (OAuth) or API profiles with any Anthropic-compatible endpoint (e.g., Anthropic API, z.ai for GLM models)
- **Multi-Account Swapping** — Register multiple Claude accounts; when one hits a rate limit, Auto Claude automatically switches to an available account
- **Cross-Platform** — Native desktop app for Windows, macOS, and Linux with auto-updates

## Critical Rules

**Claude Agent SDK only** — All AI interactions use `claude-agent-sdk`. NEVER use `anthropic.Anthropic()` directly. Always use `create_client()` from `core.client`.

**i18n required** — All frontend user-facing text MUST use `react-i18next` translation keys. Never hardcode strings in JSX/TSX. Add keys to both `en/*.json` and `fr/*.json`.

**Platform abstraction** — Never use `process.platform` directly. Import from `apps/frontend/src/main/platform/` or `apps/backend/core/platform/`. CI tests all three platforms.

**No time estimates** — Never provide duration predictions. Use priority-based ordering instead.

**PR target** — Always target the `develop` branch for PRs to AndyMik90/Auto-Claude, NOT `main`.

## Project Structure

```
autonomous-coding/
├── apps/
│   ├── backend/                 # Python backend/CLI — ALL agent logic
│   │   ├── core/                # agent_registry.py, pipeline.py, client.py, auth.py, platform/
│   │   ├── security/            # Command allowlisting, validators, hooks
│   │   ├── agents/              # planner, coder, session management
│   │   ├── qa/                  # reviewer, fixer, loop, criteria, validators/
│   │   ├── spec/                # Spec creation pipeline
│   │   ├── cli/                 # CLI commands (spec, build, workspace, QA)
│   │   ├── context/             # Task context building, semantic search
│   │   ├── runners/             # Standalone runners (spec, roadmap, insights, github)
│   │   ├── services/            # Background services, recovery orchestration
│   │   ├── integrations/        # graphiti/, linear, github
│   │   ├── project/             # Project analysis, security profiles
│   │   ├── merge/               # Intent-aware semantic merge for parallel agents
│   │   └── prompts/             # Agent system prompts (.md)
│   └── frontend/                # Electron desktop UI
│       └── src/
│           ├── main/            # Electron main process
│           │   ├── agent/       # Agent queue, process, state, events
│           │   ├── claude-profile/ # Multi-profile credentials, token refresh, usage
│           │   ├── terminal/    # PTY daemon, lifecycle, Claude integration
│           │   ├── platform/    # Cross-platform abstraction
│           │   ├── ipc-handlers/# 40+ handler modules by domain
│           │   ├── services/    # SDK session recovery, profile service
│           │   └── changelog/   # Changelog generation and formatting
│           ├── preload/         # Electron preload scripts (electronAPI bridge)
│           ├── renderer/        # React UI
│           │   ├── components/  # UI components (onboarding, settings, task, terminal, github, etc.)
│           │   ├── stores/      # 24+ Zustand state stores
│           │   ├── contexts/    # React contexts (ViewStateContext)
│           │   ├── hooks/       # Custom hooks (useIpc, useTerminal, etc.)
│           │   ├── styles/      # CSS / Tailwind styles
│           │   └── App.tsx      # Root component
│           ├── shared/          # Shared types, i18n, constants, utils
│           │   ├── i18n/locales/# en/*.json, fr/*.json
│           │   ├── constants/   # themes.ts, etc.
│           │   ├── types/       # 19+ type definition files
│           │   └── utils/       # ANSI sanitizer, shell escape, provider detection
│           └── types/           # TypeScript type definitions
├── guides/                      # Documentation
├── tests/                       # Backend test suite
└── scripts/                     # Build and utility scripts
```

## Commands Quick Reference

### Setup
```bash
npm run install:all              # Install all dependencies from root
# Or separately:
cd apps/backend && uv venv && uv pip install -r requirements.txt
cd apps/frontend && npm install
```

### Backend
```bash
cd apps/backend
python runners/spec_runner.py --interactive            # Create spec interactively
python runners/spec_runner.py --task "description"      # Create from task
python runners/spec_runner.py --task "desc" --task-type design  # Design task (creates child tasks)
python run.py --spec 001                        # Run autonomous build
python run.py --spec 001 --qa                   # Run QA validation
python run.py --spec 001 --merge                # Merge completed build
python run.py --list                            # List all specs
```

### Daemon Automation (Full End-to-End)

The daemon watches `.auto-claude/specs/` and auto-executes tasks with `status: "queue"`.

```bash
cd apps/backend

# Step 1: Create spec (--no-build sets status to "queue" for daemon pickup)
python runners/spec_runner.py --task "description" --project-dir /path/to/project --no-build

# Step 1b: Create DESIGN task (auto-decomposes into child tasks visible in UI Kanban)
python runners/spec_runner.py --task "description" --project-dir /path --no-build --task-type design

# Step 2: Start daemon (watches specs/, auto-executes, writes daemon_status.json for UI)
python runners/daemon_runner.py --project-dir /path/to/project \
  --status-file /path/to/project/.auto-claude/daemon_status.json

# Full auto pipeline (spec_runner creates spec + immediately executes + auto-merges)
python runners/spec_runner.py --task "description" --project-dir /path --auto-merge
```

**Execution flow:**
```
spec_runner.py --no-build → creates spec (status: "queue")
  → daemon detects new spec → executor.py spawns run.py --auto-merge
    → planner → coder → QA reviewer → QA fixer (if needed) → auto-merge → done
  → daemon_status.json updated → UI DaemonStatusWatcher detects → Kanban card moves
```

**Critical rules for AI agents:**
- **NEVER manually create spec files** (spec.md, requirements.json, implementation_plan.json)
- **Always use spec_runner.py** to create specs — it runs the full spec creation pipeline (gatherer → researcher → writer → critic)
- **--no-build** flag: creates spec only, sets status to "queue" for daemon pickup
- **--auto-merge** flag: auto-merges worktree to project after QA passes (no manual intervention)
- **daemon_runner.py** is needed for the UI to show real-time task progress (writes daemon_status.json)

### Daemon Infrastructure (Real-Time Communication)

The daemon uses a layered communication architecture for sub-second UI updates:

```
┌───────────────────────────────┐
│  Task Daemon (__init__.py)    │
│  _notify_status_change()      │ ← Fires on every state transition
│  _status_dirty (Event)        │
└──────┬────────────────────────┘
       │ immediate wake
┌──────▼────────────────────────┐
│  Status Writer Thread         │
│  daemon_runner.py             │
│  (event-driven + 30s heartbeat│
│   writes daemon_status.json)  │
│  + ws_server.broadcast()      │ ← WebSocket push to connected UIs
└──────┬───────────┬────────────┘
       │ file      │ ws://127.0.0.1:18800
┌──────▼───────────▼────────────┐
│  DaemonStatusWatcher (TS)     │
│  daemon-status-watcher.ts     │
│  chokidar (100ms) + WS client │ ← Auto-discovers WS from ws_port
│  processFile() → IPC → UI     │
└───────────────────────────────┘
```

**Key modules:**

| Module | Role |
|--------|------|
| `services/task_daemon/__init__.py` | Daemon core: task lifecycle, `_notify_status_change()` |
| `services/task_daemon/ws_server.py` | WebSocket server (port 18800-18809 auto-bind) |
| `services/task_daemon/executor.py` | Agent registry + task command builder |
| `runners/daemon_runner.py` | CLI entry, status writer thread, WS startup |
| `frontend/src/main/daemon-status-watcher.ts` | UI bridge: file polling + WS auto-connect |

**Resilience features (OpenClaw patterns):**

| Feature | Module | Description |
|---------|--------|-------------|
| JSONL event log | `core/task_event.py` | Append-only `events.jsonl` — immutable event history |
| Schema validation | `core/schema.py` | Validates plan/requirements/metadata before write |
| Exponential backoff | `spec/phases/models.py` | `retry_backoff()` — 2s, 4s delays for transient errors |
| Retryable error detection | `spec/phases/models.py` | `is_retryable_error()` — rate limits, timeouts, 429/503 |
| Session logging | `core/session_logger.py` | AGENT_SESSION_START/END events in events.jsonl |
| Unified agent registry | `core/agent_registry.py` | Single source of truth for all 54 agents (tools, security, execution) |
| Declarative pipeline | `core/pipeline.py` + `core/pipelines.py` | DAG-based pipeline engine with conditions, parallelism, retry |
| QA validators | `qa/validators/` + `qa/validator_orchestrator.py` | Independent build/browser/API/DB validators, parallel execution |
| Custom agent plugins | `core/agent_registry.py` | `custom_agents/config.json` → auto-registered in unified registry |
| Per-agent exec policy | `core/exec_policy.py` | Agent-level bash restrictions (DENY/READONLY/ALLOWLIST/FULL) |
| Standard tool groups | `core/tool_policy.py` | 10 built-in `@group` references + 5 ToolProfile presets |
| Hook sync emit | `core/hooks.py` | `emit_hook_sync()` for tool-call hot paths |

### Security Architecture (4-Layer Defense in Depth)

Auto-Claude enforces bash command security through 4 layers. Each layer runs independently — blocking at any layer stops the command.

```
Layer 1: Agent Exec Policy  (core/exec_policy.py — NEW)
   │  Per-agent SecurityLevel: DENY → READONLY → ALLOWLIST → FULL
   │  DENY agents can't run ANY bash. READONLY allows only safe read binaries.
   ▼
Layer 2: Security Hook       (security/hooks.py — EXISTING, untouched)
   │  Project-aware command allowlisting (detected stack + custom allowlist)
   │  Specialized validators: git identity, secret scanning, process kill, etc.
   ▼
Layer 3: SDK Permissions     (create_client() — EXISTING)
   │  File operations restricted to project_dir only
   ▼
Layer 4: OS Sandbox          (Claude Agent SDK sandbox — EXISTING)
      OS-level bash isolation
```

**Key files:**

| File | Role |
|------|------|
| `core/agent_registry.py` | `AgentDefinition.security_level` — canonical security level per agent |
| `core/exec_policy.py` | `SecurityLevel` enum, `AGENT_EXEC_POLICIES` (shim → registry), `evaluate_exec_policy()` |
| `core/tool_policy.py` | `STANDARD_GROUPS`, `ToolProfile` enum, `get_profile_tools()` |
| `core/hooks.py` | `emit_hook_sync()`, `TOOL_BEFORE_CALL`/`TOOL_AFTER_CALL`/`TOOL_BLOCKED` |
| `core/client.py` | `_create_exec_policy_hook()` closure — wires exec_policy into SDK PreToolUse |
| `security/*` | Untouched — Layer 2 operates independently below exec_policy |

**Agent policy mapping (exec_policy.py):**

| Level | Agents | Bash Access |
|-------|--------|-------------|
| DENY | spec_critic, commit_message, pr_template_filler, merge_resolver | None |
| READONLY | spec_gatherer, spec_researcher, spec_writer, insights, analysis, pr_reviewer, ideation, etc. | cat, ls, grep, git, jq, etc. only |
| FULL | planner, coder, qa_reviewer, qa_fixer, verify, error_check | Full (defers to SecurityProfile) |
| ALLOWLIST (default) | Unknown/custom agents | Full (defers to SecurityProfile) |

**Spec-level override:** Add `execPolicy` to `task_metadata.json` to override an agent's built-in policy:
```json
{
  "execPolicy": {
    "coder": { "securityLevel": "readonly", "extraAllow": ["npm"], "extraDeny": ["rm"] }
  }
}
```

**Standard tool groups (tool_policy.py):**

| Group | Tools |
|-------|-------|
| `@fs_read` | Read, Glob, Grep |
| `@fs_write` | Write, Edit |
| `@runtime` | Bash |
| `@web` | WebFetch, WebSearch |
| `@memory` | mcp__graphiti-memory__*, mcp__auto-claude__record_* |
| `@docs` | mcp__context7__* |
| `@browser` | mcp__playwright__*, mcp__electron__*, mcp__marionette__* |
| `@progress` | mcp__auto-claude__get_build_progress, update_subtask_status |
| `@qa` | mcp__auto-claude__update_qa_status |
| `@design` | mcp__auto-claude__create_child_spec, create_batch_child_specs |

**Tool profiles:** `MINIMAL` (@fs_read, @web), `READONLY` (+@docs), `CODING` (+@fs_write, @runtime, @memory, @progress), `QA` (+@browser, @qa), `FULL` (wildcard `*`).

### Frontend
```bash
cd apps/frontend
npm run dev              # Dev mode (Electron + Vite HMR)
npm run build            # Production build
npm run test             # Vitest unit tests
npm run test:watch       # Vitest watch mode
npm run lint             # Biome check
npm run lint:fix         # Biome auto-fix
npm run typecheck        # TypeScript strict check
npm run package          # Package for distribution
```

### Testing

| Stack | Command | Tool |
|-------|---------|------|
| Backend | `apps/backend/.venv/bin/pytest tests/ -v` | pytest |
| Frontend unit | `cd apps/frontend && npm test` | Vitest |
| Frontend E2E | `cd apps/frontend && npm run test:e2e` | Playwright |
| All backend | `npm run test:backend` (from root) | pytest |

### Releases
```bash
node scripts/bump-version.js patch|minor|major  # Bump version
git push && gh pr create --base main             # PR to main triggers release
```

See [RELEASE.md](RELEASE.md) for full release process.

## Backend Development

### Claude Agent SDK Usage

Client: `apps/backend/core/client.py` — `create_client()` returns a configured `ClaudeSDKClient` with security hooks, tool permissions, and MCP server integration.

Model and thinking level are user-configurable (via the Electron UI settings or CLI override). Use `phase_config.py` helpers to resolve the correct values:

```python
from core.client import create_client
from phase_config import get_phase_model, get_phase_thinking_budget

# Resolve model/thinking from user settings (Electron UI or CLI override)
phase_model = get_phase_model(spec_dir, "coding", cli_model=None)
phase_thinking = get_phase_thinking_budget(spec_dir, "coding", cli_thinking=None)

client = create_client(
    project_dir=project_dir,
    spec_dir=spec_dir,
    model=phase_model,
    agent_type="coder",          # planner | coder | qa_reviewer | qa_fixer
    max_thinking_tokens=phase_thinking,
)

# Run agent session (uses context manager + run_agent_session helper)
async with client:
    status, response = await run_agent_session(client, prompt, spec_dir)
```

Working examples: `agents/planner.py`, `agents/coder.py`, `qa/reviewer.py`, `qa/fixer.py`, `spec/`

### Agent Prompts (`apps/backend/prompts/`)

| Prompt | Purpose |
|--------|---------|
| planner.md | Implementation plan with subtasks |
| coder.md / coder_recovery.md | Subtask implementation / recovery |
| qa_reviewer.md / qa_fixer.md | Acceptance validation / issue fixes |
| spec_gatherer/researcher/writer/critic.md | Spec creation pipeline |
| complexity_assessor.md | AI-based complexity assessment |

**Code quality policies embedded in prompts:**
- **coder.md**: `HIGH-RISK-UNREVIEWED` annotation for security functions (auth, payment, crypto, sql, etc.) + code annotation policy (TODO/FIXME/HACK rules)
- **qa_reviewer.md §6.1.5**: High-risk function audit — scans diff for missing `HIGH-RISK` annotations on security functions
- **qa_reviewer.md §6.1.7**: Code annotation scan — flags bare `TODO`, `FIXME`, `HACK`, `XXX` in diff

### Runtime Validation Docs (`apps/backend/prompts/mcp_tools/`)

QA agents dynamically receive validation documentation based on detected project type. The routing logic is in `prompts_pkg/project_context.py:get_mcp_tools_for_project()`.

| Validation Doc | Triggered By | Strategy |
|----------------|-------------|----------|
| `electron_validation.md` | `is_electron` | Electron MCP (screenshot, click, evaluate) |
| `tauri_validation.md` | `is_tauri` | Playwright on frontend + `cargo check/test` for Rust backend |
| `flutter_validation.md` | `is_flutter` | `flutter analyze` + Marionette MCP (widget-level) + Playwright (screenshots) |
| `unity_validation.md` | `is_unity` | Unity batch CLI (EditMode/PlayMode tests) + `dotnet build` fallback |
| `react_native_validation.md` | `is_react_native` or `is_expo` | Expo web mode via Playwright (port 8081) or native build fallback |
| `playwright_browser.md` | `is_web_frontend` or `is_flutter` or `is_expo` (not Electron) | Playwright MCP browser automation (a11y snapshots) |
| `database_validation.md` | `has_database` | Migration checks, schema verification |
| `api_validation.md` | `has_api` | API endpoint testing |

**Capability detection** happens in `detect_project_capabilities()` from `project_index.json`. Backend-type services automatically get `has_api=True`.

**Adding a new validation type:**
1. Create `prompts/mcp_tools/new_validation.md` following existing pattern (Tool table → Step flow → Document Findings)
2. Add capability flag in `detect_project_capabilities()` if needed
3. Add routing in `get_mcp_tools_for_project()`
4. Update `qa_reviewer.md` marker comment block (between `<!-- PROJECT-SPECIFIC ... -->` and `<!-- END ... -->`)

### Spec Directory Structure

Each spec in `.auto-claude/specs/XXX-name/` contains: `spec.md`, `requirements.json`, `context.json`, `implementation_plan.json`, `qa_report.md`, `QA_FIX_REQUEST.md`, `events.jsonl`

### Unified Agent Registry (`core/agent_registry.py`)

**Single source of truth for all agent definitions.** Previously agent config was scattered across 4 files — now one `AgentDefinition` = one agent.

```python
from core.agent_registry import AgentRegistry

reg = AgentRegistry.instance()
coder = reg.get("coder")
assert coder.security_level == "full"
assert coder.tool_profile == "CODING"

# List by category
qa_agents = reg.list_by_category("qa")
```

**`AgentDefinition` fields** (merged from 4 old registries):
- **Tools**: `tools`, `mcp_servers`, `mcp_servers_optional`, `auto_claude_tools`, `thinking_default`
- **Security**: `security_level` (deny/readonly/allowlist/full), `extra_allow`, `extra_deny`
- **Execution**: `script`, `use_claude_cli`, `prompt_template`, `system_prompt`, `execution_mode`
- **Tool Profile**: `tool_profile` (MINIMAL/READONLY/CODING/QA/FULL)

**Backward-compatible shims** — old modules read from registry:

| Old Module | Old Dict | Now |
|-----------|----------|-----|
| `agents/tools_pkg/models.py` | `AGENT_CONFIGS` | `_build_agent_configs()` → registry shim |
| `core/exec_policy.py` | `AGENT_EXEC_POLICIES` | `_build_exec_policies()` → registry shim |
| `services/task_daemon/executor.py` | `AGENT_REGISTRY` | `_build_agent_registry()` → registry shim |

**Adding a new agent**: Add one entry to `BUILTIN_AGENTS` dict in `core/agent_registry.py`. All shims auto-populate.

### Declarative Pipeline Engine (`core/pipeline.py`)

Pipeline stages defined as data, not hardcoded function calls. Supports topological ordering, conditional execution, parallel stages, and retry.

```python
from core.pipeline import PipelineEngine
from core.pipelines import get_pipeline

pipeline = get_pipeline("default")   # or "design", "qa_only"
engine = PipelineEngine(pipeline, {"working_dir": ..., "spec_dir": ..., "model": ...})
result = await engine.run()
```

**Built-in pipelines** (`core/pipelines.py`):

| Pipeline | Stages | Use Case |
|----------|--------|----------|
| `default` | build → qa (if not skip_qa) → merge | Standard task execution |
| `design` | decompose | Design task decomposition |
| `qa_only` | qa | Resume QA validation |

**Programmatic invocation** via `cli/build_commands.py:run_pipeline()`.

### QA Validators (`qa/validators/`)

Independent validator modules — each validator = one n8n node that runs and reports results independently.

```
qa/validators/
├── __init__.py           # ValidatorResult, BaseValidator
├── build_validator.py    # Build, lint, test commands
├── browser_validator.py  # Real Playwright browser validation (auto dev server + headless Chromium)
├── api_validator.py      # API endpoint testing
└── db_validator.py       # Database migration/schema
```

**Orchestrator** (`qa/validator_orchestrator.py`):
1. `select_validators(capabilities)` — filter by project type
2. Build validator runs first (sequential, must pass)
3. Runtime validators (browser, API, DB) run in parallel
4. Results aggregated as `list[ValidatorResult]`

**Integration with QA loop** (`qa/loop.py`):
- Before the QA while-loop, `run_validators()` runs all applicable validators
- First QA iteration uses `review_with_results()` to inject validator evidence into the reviewer prompt
- Subsequent iterations (after fixer) use standard `run_qa_agent_session()` — validators only run once
- Entire validator block is non-blocking: if validators fail to run, QA falls back to standard flow

**Integration with QA reviewer** (`qa/reviewer.py`):
- `review_with_results(client, ..., validator_results)` — passes pre-computed results to reviewer
- Reviewer focuses on spec compliance using validator evidence

**Browser validator** (`qa/validators/browser_validator.py`):
- Uses Python `playwright` package directly (NOT the MCP server) — self-contained n8n node
- Autonomously starts dev server, polls port (120s timeout), launches Chromium (visible by default)
- Visible mode: `AUTO_CLAUDE_HEADLESS_BROWSER=true` for CI/unattended mode
- Flutter: auto-replaces `-d chrome` with `-d web-server`, stdout-based ready detection
- Flutter: auto-injects `marionette_flutter` + `MarionetteBinding` for Marionette MCP support
- Screenshots saved to `spec_dir/screenshots/01-initial-load.png`
- Interactive UI exploration: Tab+Enter navigation, DOM clicks, Flutter semantics
- Console errors captured and reported as issues
- Only `passed=False` when navigation completely fails — everything else is evidence for QA reviewer
- `finally` block always cleans up: close browser → stop playwright → kill dev server tree
- Graceful skip when playwright not installed or no dev server config found
- Cross-platform: Windows `CREATE_NEW_PROCESS_GROUP` + `taskkill /F /T`, Unix `killpg(SIGTERM/SIGKILL)`
- Requires: `pip install playwright && playwright install chromium`

**Marionette MCP** (Flutter widget-level interaction):
- Auto-enabled for Flutter projects (opt-out via `MARIONETTE_MCP_DISABLED=true`)
- Provides 9 tools: connect, disconnect, get_interactive_elements, tap, enter_text, scroll_to, get_logs, take_screenshots, hot_reload
- Requires: `dart pub global activate marionette_mcp` (one-time install)
- browser_validator auto-injects `marionette_flutter` + patches `main.dart` in worktree
- QA agent connects via VM service URI and interacts with widgets directly
- Works with CanvasKit renderer (no DOM dependency)

**Build validator command source** (`qa/validators/build_validator.py`):
- Reads lint/build/test commands from `project_index.json` (written by `framework_analyzer.py`)
- Does NOT import from `command_registry` — those modules are security allowlists, not command detectors

**Lint/test command detection** (`analysis/analyzers/framework_analyzer.py`):
- Python: `ruff check .` / `flake8 .` / `mypy .` (config-file priority) + `pytest`
- Node.js: `npm run lint` / `npx eslint .` / `npx tsc --noEmit` + `npm run test`
- Go: `go vet ./...` + `go test ./...`
- Rust: `cargo clippy -- -D warnings` + `cargo test`
- Flutter: `flutter analyze` + `flutter test`

### Custom Agent Plugins

Add custom agents by creating `custom_agents/config.json` in the backend directory. Custom agents are auto-registered into the unified `AgentRegistry` at startup.

```json
{
  "agents": {
    "my_custom_agent": {
      "prompt_file": "my_agent.md",
      "description": "Custom agent for X",
      "tools": ["Read", "Write", "Bash", "Grep"],
      "mcp_servers": ["context7"],
      "thinking_default": "medium",
      "use_claude_cli": false,
      "script": null,
      "extra_args": []
    }
  }
}
```

Prompt files go in `custom_agents/prompts/`. Each agent is a self-contained module (n8n node pattern): clear inputs (prompt, spec, tools), clear outputs (files, status), well-defined boundaries.

**Key files:**

| File | Role |
|------|------|
| `core/agent_registry.py` | `_load_custom_agents()` — loads from config.json into unified registry |
| `agents/tools_pkg/models.py` | `get_custom_agent_prompt()`, `list_custom_agents()` — public API |
| `custom_agents/config.json` | Agent definitions |
| `custom_agents/prompts/` | Agent prompt files (.md) |

### Design Tasks (Large Project Decomposition)

For large projects that need to be split into multiple parallel tasks, use **`taskType: "design"`**. This triggers a special agent pipeline that auto-decomposes one task into multiple child specs.

**How it works:**
1. Create a spec with `"taskType": "design"` in `implementation_plan.json`
2. The Task Daemon picks it up and runs a **Planner Agent** with `design_architect.md` prompt
3. The agent calls `create_batch_child_specs` (or `create_child_spec`) MCP tool
4. Child specs are created as individual folders in `.auto-claude/specs/`
5. Each child spec appears as a **separate Kanban card** in the UI
6. The Task Daemon automatically picks up child specs and runs them in dependency order

**Required files for a design task:**

```
.auto-claude/specs/001-my-design-task/
├── spec.md                   # High-level project description
├── requirements.json         # Task metadata
├── implementation_plan.json  # MUST have "taskType": "design"
└── context.json              # Optional context
```

**implementation_plan.json (design task):**
```json
{
  "status": "queue",
  "planStatus": "queue",
  "xstateState": "backlog",
  "executionPhase": "backlog",
  "taskType": "design",
  "priority": 1,
  "complexity": "standard",
  "phases": [],
  "subtasks": []
}
```

**Key files in the automation chain:**

| File | Role |
|------|------|
| `services/task_daemon/__init__.py` | Daemon: picks up tasks, manages lifecycle |
| `services/task_daemon/executor.py` | Builds run commands, agent registry |
| `agents/coder.py` | Main agent loop (planner → coder → QA) |
| `agents/tools_pkg/tools/subtask.py` | MCP tools: `create_batch_child_specs`, `create_child_spec` |
| `agents/tools_pkg/models.py` | Agent configs with tool permissions |
| `services/spec_factory.py` | Creates child spec folders with dependency resolution |
| `prompts/design_architect.md` | Design agent system prompt |
| `prompts_pkg/prompt_generator.py` | Routes design tasks to design_architect.md |
| `prompts_pkg/prompts.py` | `is_first_run()` detects design task completion |

**Execution flow:**
```
taskType="design" → Daemon → run.py → coder.py (planner agent)
→ design_architect.md prompt → create_batch_child_specs tool
→ Child specs created → Parent marked "complete"
→ Daemon picks up children → dependency-ordered execution
→ Each child: Planner → Coder → QA Reviewer → QA Fixer
```

**Design task constraints:**
- Max depth = 2 by default (configurable via `AUTO_CLAUDE_MAX_CHILD_DEPTH` env var). Design/architecture types blocked at depth >= 2 to prevent unbounded decomposition.
- Child specs use 1-based index for `dependsOn` references (e.g., `"1"`, `"2"`)
- The `SpecFactory` uses 2-pass dependency resolution to map internal refs to actual spec IDs
- Design tasks skip plan validation (they don't produce phases/subtasks)

### Memory System (Graphiti)

Graph-based semantic memory in `integrations/graphiti/`. Configured through the Electron app's onboarding/settings UI (CLI users can alternatively set `GRAPHITI_ENABLED=true` in `.env`). See [ARCHITECTURE.md](shared_docs/ARCHITECTURE.md#memory-system) for details.

## Frontend Development

### Tech Stack

React 19, TypeScript (strict), Electron 39, Zustand 5, Tailwind CSS v4, Radix UI, xterm.js 6, Vite 7, Vitest 4, Biome 2, Motion (Framer Motion)

### Path Aliases (tsconfig.json)

| Alias | Maps to |
|-------|---------|
| `@/*` | `src/renderer/*` |
| `@shared/*` | `src/shared/*` |
| `@preload/*` | `src/preload/*` |
| `@features/*` | `src/renderer/features/*` |
| `@components/*` | `src/renderer/shared/components/*` |
| `@hooks/*` | `src/renderer/shared/hooks/*` |
| `@lib/*` | `src/renderer/shared/lib/*` |

### State Management (Zustand)

All state lives in `src/renderer/stores/`. Key stores:

- `project-store.ts` — Active project, project list
- `task-store.ts` — Tasks/specs management
- `terminal-store.ts` — Terminal sessions and state
- `settings-store.ts` — User preferences
- `github/issues-store.ts`, `github/pr-review-store.ts` — GitHub integration
- `insights-store.ts`, `roadmap-store.ts`, `kanban-settings-store.ts`

Main process also has stores: `src/main/project-store.ts`, `src/main/terminal-session-store.ts`

### Styling

- **Tailwind CSS v4** with `@tailwindcss/postcss` plugin
- **7 color themes** (Default, Dusk, Lime, Ocean, Retro, Neo + more) defined in `src/shared/constants/themes.ts`
- Each theme has light/dark mode variants via CSS custom properties
- Utility: `clsx` + `tailwind-merge` via `cn()` helper
- Component variants: `class-variance-authority` (CVA)

### IPC Communication

Main ↔ Renderer communication via Electron IPC:
- **Handlers:** `src/main/ipc-handlers/` — organized by domain (github, gitlab, ideation, context, etc.)
- **Preload:** `src/preload/` — exposes safe APIs to renderer
- Pattern: renderer calls via `window.electronAPI.*`, main handles in IPC handler modules

### Agent Management (`src/main/agent/`)

The frontend manages agent lifecycle end-to-end:
- **`agent-queue.ts`** — Queue routing, prioritization, spec number locking
- **`agent-process.ts`** — Spawns and manages agent subprocess communication
- **`agent-state.ts`** — Tracks running agent state and status
- **`agent-events.ts`** — Agent lifecycle events and state transitions

### Claude Profile System (`src/main/claude-profile/`)

Multi-profile credential management for switching between Claude accounts:
- **`credential-utils.ts`** — OS credential storage (Keychain/Windows Credential Manager)
- **`token-refresh.ts`** — OAuth token lifecycle and automatic refresh
- **`usage-monitor.ts`** — API usage tracking and rate limiting per profile
- **`profile-scorer.ts`** — Scores profiles by usage and availability

### Terminal System (`src/main/terminal/`)

Full PTY-based terminal integration:
- **`pty-daemon.ts`** / **`pty-manager.ts`** — Background PTY process management
- **`terminal-lifecycle.ts`** — Session creation, cleanup, event handling
- **`claude-integration-handler.ts`** — Claude SDK integration within terminals
- Renderer: xterm.js 6 with WebGL, fit, web-links, serialize addons. Store: `terminal-store.ts`

## Code Quality

### Frontend
- **Linting:** Biome (`npm run lint` / `npm run lint:fix`)
- **Type checking:** `npm run typecheck` (strict mode)
- **Pre-commit:** Husky + lint-staged runs Biome on staged `.ts/.tsx/.js/.jsx/.json`
- **Testing:** Vitest + React Testing Library + jsdom

### Backend
- **Linting:** Ruff
- **Testing:** pytest (`apps/backend/.venv/bin/pytest tests/ -v`)

## i18n Guidelines

All frontend UI text uses `react-i18next`. Translation files: `apps/frontend/src/shared/i18n/locales/{en,fr}/*.json`

**Namespaces:** `common`, `navigation`, `settings`, `dialogs`, `tasks`, `errors`, `onboarding`, `welcome`

```tsx
import { useTranslation } from 'react-i18next';
const { t } = useTranslation(['navigation', 'common']);

<span>{t('navigation:items.githubPRs')}</span>     // CORRECT
<span>GitHub PRs</span>                             // WRONG

// With interpolation:
<span>{t('errors:task.parseError', { error })}</span>
```

When adding new UI text: add keys to ALL language files, use `namespace:section.key` format.

## Cross-Platform

Supports Windows, macOS, Linux. CI tests all three.

**Platform modules:** `apps/frontend/src/main/platform/` and `apps/backend/core/platform/`

| Function | Purpose |
|----------|---------|
| `isWindows()` / `isMacOS()` / `isLinux()` | OS detection |
| `getPathDelimiter()` | `;` (Win) or `:` (Unix) |
| `findExecutable(name)` | Cross-platform executable lookup |
| `requiresShell(command)` | `.cmd/.bat` shell detection (Win) |

Never hardcode paths. Use `findExecutable()` and `joinPaths()`. See [ARCHITECTURE.md](shared_docs/ARCHITECTURE.md#cross-platform-development) for extended guide.

## E2E Testing (Electron MCP)

QA agents can interact with the running Electron app via Chrome DevTools Protocol:

1. Start app: `npm run dev:debug` (debug mode for AI self-validation via Electron MCP)
2. Set `ELECTRON_MCP_ENABLED=true` in `apps/backend/.env`
3. Run QA: `python run.py --spec 001 --qa`

Tools: `take_screenshot`, `click_by_text`, `fill_input`, `get_page_structure`, `send_keyboard_shortcut`, `eval`. See [ARCHITECTURE.md](shared_docs/ARCHITECTURE.md#end-to-end-testing) for full capabilities.

## Running the Application

```bash
# CLI only
cd apps/backend && python run.py --spec 001

# Desktop app
npm start          # Production build + run
npm run dev        # Development mode with HMR

# Project data: .auto-claude/specs/ (gitignored)
```
