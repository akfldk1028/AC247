# Project Analyzer Module

Dynamic security profile generation for Auto-Claude tasks.

## Overview

This module analyzes project structure to build security profiles that determine which commands are allowed during task execution. This prevents AI agents from running potentially dangerous commands while still allowing legitimate development operations.

## Components

| File | Purpose |
|------|---------|
| `analyzer.py` | Main orchestrator - coordinates all detection and builds profiles |
| `stack_detector.py` | Detects languages, package managers, databases, infrastructure |
| `framework_detector.py` | Detects frameworks from dependencies |
| `structure_analyzer.py` | Detects custom scripts and project structure |
| `config_parser.py` | Parses various config files (package.json, pyproject.toml, etc.) |
| `models.py` | Data models for security profiles and detected stack |
| `command_registry/` | Command allowlists organized by category |

## Key Features

### 1. Stack Detection
Analyzes project files to detect:
- Programming languages (Python, JavaScript, TypeScript, Rust, Go, etc.)
- Package managers (npm, pip, cargo, etc.)
- Frameworks (React, Django, FastAPI, etc.)
- Databases (PostgreSQL, MongoDB, Redis, etc.)
- Infrastructure (Docker, Kubernetes, Terraform, etc.)

### 2. Spec-Based Language Detection (New)

**Problem:** Empty/new projects have no source files, so language detection fails. This causes legitimate commands like `python` to be blocked even for Python projects.

**Solution:** `analyzer.py` now also scans spec files (`spec.md`, `requirements.json`) for language mentions.

```python
# In analyzer.py
def _detect_language_from_spec(self) -> None:
    """
    Detect languages mentioned in spec files.

    Scans:
    - .auto-claude/specs/*/spec.md
    - .auto-claude/specs/*/requirements.json
    - spec_dir/spec.md (for worktree case)

    Language patterns detected:
    - Python: python, .py, pip, pytest, django, flask, fastapi
    - JavaScript: javascript, .js, node.js, npm, react, vue
    - TypeScript: typescript, .ts, .tsx, tsconfig
    - Go: golang, .go, go.mod, go build/run/test
    - Rust: rust, cargo, .rs, rustc
    - Java: java, .java, maven, gradle, spring
    - Ruby: ruby, .rb, rails, bundler
    - Dart: dart, flutter, .dart, pubspec
    - C#: c#, csharp, .cs, dotnet, .net
    """
```

**Result:** If spec.md mentions "Python", the `python` command is automatically allowed.

### 3. Profile Caching

Profiles are cached to avoid re-analysis on every task:
- Stored in `.auto-claude-security.json`
- Hash-based invalidation when project files change
- Inherited profiles for worktrees (never re-analyzed)

## Usage

```python
from project.analyzer import ProjectAnalyzer

analyzer = ProjectAnalyzer(project_dir, spec_dir)
profile = analyzer.analyze()

# Check if a command is allowed
allowed = profile.get_all_allowed_commands()
if "python" in allowed:
    # Safe to run python commands
    pass
```

## Security Model

Commands are organized in tiers:
1. **Base Commands** - Always allowed (ls, cd, git, etc.)
2. **Stack Commands** - Allowed based on detected stack (python, npm, cargo, etc.)
3. **Script Commands** - Allowed based on detected scripts (npm run, make targets)
4. **Custom Commands** - User-defined allowlist in config

See [command_registry/README.md](command_registry/README.md) for full command lists.
