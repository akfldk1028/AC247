# Auto Claude

**Autonomous multi-agent coding framework that plans, builds, and validates software for you.**

![Auto Claude Kanban Board](.github/assets/Auto-Claude-Kanban.png)

[![License](https://img.shields.io/badge/license-AGPL--3.0-green?style=flat-square)](./agpl-3.0.txt)
[![Discord](https://img.shields.io/badge/Discord-Join%20Community-5865F2?style=flat-square&logo=discord&logoColor=white)](https://discord.gg/KCXaPBr4Dj)
[![YouTube](https://img.shields.io/badge/YouTube-Subscribe-FF0000?style=flat-square&logo=youtube&logoColor=white)](https://www.youtube.com/@AndreMikalsen)
[![CI](https://img.shields.io/github/actions/workflow/status/AndyMik90/Auto-Claude/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/AndyMik90/Auto-Claude/actions)

---

## Download

### Stable Release

<!-- STABLE_VERSION_BADGE -->
[![Stable](https://img.shields.io/badge/stable-2.7.5-blue?style=flat-square)](https://github.com/AndyMik90/Auto-Claude/releases/tag/v2.7.5)
<!-- STABLE_VERSION_BADGE_END -->

<!-- STABLE_DOWNLOADS -->
| Platform | Download |
|----------|----------|
| **Windows** | [Auto-Claude-2.7.5-win32-x64.exe](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.5/Auto-Claude-2.7.5-win32-x64.exe) |
| **macOS (Apple Silicon)** | [Auto-Claude-2.7.5-darwin-arm64.dmg](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.5/Auto-Claude-2.7.5-darwin-arm64.dmg) |
| **macOS (Intel)** | [Auto-Claude-2.7.5-darwin-x64.dmg](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.5/Auto-Claude-2.7.5-darwin-x64.dmg) |
| **Linux** | [Auto-Claude-2.7.5-linux-x86_64.AppImage](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.5/Auto-Claude-2.7.5-linux-x86_64.AppImage) |
| **Linux (Debian)** | [Auto-Claude-2.7.5-linux-amd64.deb](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.5/Auto-Claude-2.7.5-linux-amd64.deb) |
| **Linux (Flatpak)** | [Auto-Claude-2.7.5-linux-x86_64.flatpak](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.5/Auto-Claude-2.7.5-linux-x86_64.flatpak) |
<!-- STABLE_DOWNLOADS_END -->

### Beta Release

> ⚠️ Beta releases may contain bugs and breaking changes. [View all releases](https://github.com/AndyMik90/Auto-Claude/releases)

<!-- BETA_VERSION_BADGE -->
[![Beta](https://img.shields.io/badge/beta-2.7.6--beta.2-orange?style=flat-square)](https://github.com/AndyMik90/Auto-Claude/releases/tag/v2.7.6-beta.2)
<!-- BETA_VERSION_BADGE_END -->

<!-- BETA_DOWNLOADS -->
| Platform | Download |
|----------|----------|
| **Windows** | [Auto-Claude-2.7.6-beta.2-win32-x64.exe](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6-beta.2/Auto-Claude-2.7.6-beta.2-win32-x64.exe) |
| **macOS (Apple Silicon)** | [Auto-Claude-2.7.6-beta.2-darwin-arm64.dmg](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6-beta.2/Auto-Claude-2.7.6-beta.2-darwin-arm64.dmg) |
| **macOS (Intel)** | [Auto-Claude-2.7.6-beta.2-darwin-x64.dmg](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6-beta.2/Auto-Claude-2.7.6-beta.2-darwin-x64.dmg) |
| **Linux** | [Auto-Claude-2.7.6-beta.2-linux-x86_64.AppImage](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6-beta.2/Auto-Claude-2.7.6-beta.2-linux-x86_64.AppImage) |
| **Linux (Debian)** | [Auto-Claude-2.7.6-beta.2-linux-amd64.deb](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6-beta.2/Auto-Claude-2.7.6-beta.2-linux-amd64.deb) |
| **Linux (Flatpak)** | [Auto-Claude-2.7.6-beta.2-linux-x86_64.flatpak](https://github.com/AndyMik90/Auto-Claude/releases/download/v2.7.6-beta.2/Auto-Claude-2.7.6-beta.2-linux-x86_64.flatpak) |
<!-- BETA_DOWNLOADS_END -->

> All releases include SHA256 checksums and VirusTotal scan results for security verification.

---

## Requirements

- **Claude Pro/Max subscription** - [Get one here](https://claude.ai/upgrade)
- **Claude Code CLI** - `npm install -g @anthropic-ai/claude-code`
- **Git repository** - Your project must be initialized as a git repo

---

## Quick Start

1. **Download and install** the app for your platform
2. **Open your project** - Select a git repository folder
3. **Connect Claude** - The app will guide you through OAuth setup
4. **Create a task** - Describe what you want to build
5. **Watch it work** - Agents plan, code, and validate autonomously

---

## Features

| Feature | Description |
|---------|-------------|
| **Autonomous Tasks** | Describe your goal; agents handle planning, implementation, and validation |
| **24/7 Daemon Mode** | Background daemon watches for tasks, executes in dependency order, auto-merges |
| **Design Decomposition** | Large projects auto-split into parallel child tasks with dependency ordering |
| **Parallel Execution** | Run up to 3 concurrent tasks with 12 agent terminals |
| **Isolated Workspaces** | All changes happen in git worktrees - your main branch stays safe |
| **QA Validators** | Auto dev server + headless Chromium screenshots, a11y tree, console error capture via Playwright; plus build/API/DB validators |
| **Self-Validating QA** | Built-in quality assurance loop catches issues before you review |
| **AI-Powered Merge** | Automatic conflict resolution when integrating back to main |
| **Memory Layer** | Graphiti-based knowledge graph retains insights across sessions |
| **Unified Agent Registry** | 50+ agents managed as self-contained nodes with tools, security, and execution config |
| **Custom Agent Plugins** | Add your own agents via `custom_agents/config.json` |
| **Multi-Account Swapping** | Register multiple Claude accounts; auto-switches on rate limits |
| **GitHub/GitLab Integration** | Import issues, investigate with AI, create merge requests |
| **Linear Integration** | Sync tasks with Linear for team progress tracking |
| **Cross-Platform** | Native desktop apps for Windows, macOS, and Linux |
| **Auto-Updates** | App updates automatically when new versions are released |

---

## Interface

### Kanban Board
Visual task management from planning through completion. Create tasks and monitor agent progress in real-time.

### Agent Terminals
AI-powered terminals with one-click task context injection. Spawn multiple agents for parallel work.

![Agent Terminals](.github/assets/Auto-Claude-Agents-terminals.png)

### Roadmap
AI-assisted feature planning with competitor analysis and audience targeting.

![Roadmap](.github/assets/Auto-Claude-roadmap.png)

### Additional Features
- **Insights** - Chat interface for exploring your codebase
- **Ideation** - Discover improvements, performance issues, and vulnerabilities
- **Changelog** - Generate release notes from completed tasks

---

## Architecture

Auto Claude uses an **n8n-style node pattern** where each agent is a self-contained module with clear inputs, outputs, and security boundaries.

```
User creates task
  └─> Spec Pipeline (gatherer → researcher → writer → critic)
        └─> Daemon picks up task (status: "queue")
              └─> Planner agent creates subtasks
                    └─> Coder agent implements (parallel subagents)
                          └─> QA Validators (build → browser/API/DB in parallel)
                                └─> QA Reviewer validates against spec
                                      └─> QA Fixer resolves issues (loop)
                                            └─> Auto-merge to main branch
```

**Key modules:**

| Module | Purpose |
|--------|---------|
| `core/agent_registry.py` | Unified registry for all 50+ agents (tools, security, execution) |
| `core/pipeline.py` | Declarative pipeline engine with DAG execution |
| `core/exec_policy.py` | Per-agent bash security levels (DENY/READONLY/ALLOWLIST/FULL) |
| `core/tool_policy.py` | Standard tool groups and profiles (MINIMAL/READONLY/CODING/QA/FULL) |
| `qa/validators/` | Independent validators: build (lint/compile/test), browser (Playwright headless), API, DB |
| `qa/validator_orchestrator.py` | Selects and runs validators based on project capabilities |
| `services/task_daemon/` | 24/7 background daemon with WebSocket + file-based status |

## Project Structure

```
Auto-Claude/
├── apps/
│   ├── backend/              # Python backend
│   │   ├── core/             # Registry, pipeline, client, auth, security policies
│   │   ├── agents/           # Planner, coder, session management
│   │   ├── qa/               # Reviewer, fixer, loop, validators/
│   │   ├── spec/             # Spec creation pipeline
│   │   ├── security/         # Command allowlisting, hooks
│   │   ├── services/         # Task daemon, recovery
│   │   ├── prompts/          # Agent system prompts (.md)
│   │   └── runners/          # CLI entry points (spec, daemon, insights)
│   └── frontend/             # Electron desktop application
│       └── src/
│           ├── main/         # Agent lifecycle, terminal PTY, IPC handlers
│           ├── renderer/     # React UI (Kanban, terminals, settings)
│           └── shared/       # Types, i18n, state machines
├── guides/                   # Documentation
├── tests/                    # Backend test suite
└── scripts/                  # Build utilities
```

---

## CLI Usage

For headless operation, CI/CD integration, or terminal-only workflows:

```bash
cd apps/backend

# Create a spec interactively
python runners/spec_runner.py --interactive

# Create from task description (auto-executes)
python runners/spec_runner.py --task "Add login page" --project-dir /path/to/project --auto-merge

# Create spec only (daemon picks it up)
python runners/spec_runner.py --task "Add login page" --project-dir /path/to/project --no-build

# Design task (auto-decomposes into child tasks)
python runners/spec_runner.py --task "Build e-commerce platform" --project-dir /path --no-build --task-type design

# Run autonomous build
python run.py --spec 001

# Run QA validation only
python run.py --spec 001 --qa

# Merge completed build
python run.py --spec 001 --merge
```

### 24/7 Daemon Mode

The daemon watches `.auto-claude/specs/` and auto-executes tasks with `status: "queue"`:

```bash
cd apps/backend

# Start daemon (runs until Ctrl+C)
python runners/daemon_runner.py --project-dir /path/to/project \
  --status-file /path/to/project/.auto-claude/daemon_status.json

# Execution flow:
# spec_runner --no-build creates spec (status: "queue")
# → daemon detects → planner → coder → QA → auto-merge → done
# → daemon_status.json + WebSocket updated → UI Kanban card moves
```

See [guides/CLI-USAGE.md](guides/CLI-USAGE.md) for complete CLI documentation.

---

## Development

Want to build from source or contribute? See [CONTRIBUTING.md](CONTRIBUTING.md) for complete development setup instructions.

For Linux-specific builds (Flatpak, AppImage), see [guides/linux.md](guides/linux.md).

---

## Security

Auto Claude uses a **4-layer defense-in-depth** security model. Each layer runs independently — blocking at any layer stops the command.

```
Layer 1: Agent Exec Policy    Per-agent security level (DENY → READONLY → ALLOWLIST → FULL)
Layer 2: Security Hooks        Project-aware command allowlisting + specialized validators
Layer 3: SDK Permissions       File operations restricted to project directory
Layer 4: OS Sandbox            OS-level bash isolation via Claude Agent SDK
```

| Security Level | Agents | Access |
|---------------|--------|--------|
| **DENY** | spec_critic, commit_message, merge_resolver | No bash |
| **READONLY** | spec_gatherer, researcher, insights, ideation | Read-only commands (cat, ls, grep, git) |
| **FULL** | planner, coder, qa_reviewer, qa_fixer | Full (defers to project allowlist) |
| **ALLOWLIST** | Custom/unknown agents | Per-project command allowlist |

All releases are:
- Scanned with VirusTotal before publishing
- Include SHA256 checksums for verification
- Code-signed where applicable (macOS)

---

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run install:all` | Install all dependencies (backend + frontend) |
| `npm start` | Build and run the desktop app |
| `npm run dev` | Development mode with hot reload |
| `npm run package` | Package for current platform |
| `npm run package:mac` | Package for macOS |
| `npm run package:win` | Package for Windows |
| `npm run package:linux` | Package for Linux |
| `npm run package:flatpak` | Package as Flatpak (see [guides/linux.md](guides/linux.md)) |
| `npm run lint` | Run Biome linter (frontend) |
| `npm test` | Run frontend tests (Vitest) |
| `npm run test:backend` | Run backend tests (pytest) |
| `npm run typecheck` | TypeScript strict type check |

---

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup instructions
- Code style guidelines
- Testing requirements
- Pull request process

---

## Community

- **Discord** - [Join our community](https://discord.gg/KCXaPBr4Dj)
- **Issues** - [Report bugs or request features](https://github.com/AndyMik90/Auto-Claude/issues)
- **Discussions** - [Ask questions](https://github.com/AndyMik90/Auto-Claude/discussions)

---

## License

**AGPL-3.0** - GNU Affero General Public License v3.0

Auto Claude is free to use. If you modify and distribute it, or run it as a service, your code must also be open source under AGPL-3.0.

Commercial licensing available for closed-source use cases.

---

## Star History

[![GitHub Repo stars](https://img.shields.io/github/stars/AndyMik90/Auto-Claude?style=social)](https://github.com/AndyMik90/Auto-Claude/stargazers)

[![Star History Chart](https://api.star-history.com/svg?repos=AndyMik90/Auto-Claude&type=Date)](https://star-history.com/#AndyMik90/Auto-Claude&Date)
