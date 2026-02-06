# Phases Module Refactoring

## Overview

The `phases.py` file (originally 720 lines) has been refactored into a well-organized subpackage for improved maintainability and code quality.

## Structure

### Before Refactoring
```
auto-claude/spec/
└── phases.py (720 lines)
    ├── PhaseResult dataclass
    ├── PhaseExecutor class with 12 phase methods
    └── Helper methods
```

### After Refactoring
```
auto-claude/spec/
├── phases.py (14 lines - entry point)
└── phases/
    ├── __init__.py (19 lines)
    ├── models.py (23 lines)
    ├── executor.py (76 lines)
    ├── discovery_phases.py (108 lines)
    ├── requirements_phases.py (244 lines)
    ├── spec_phases.py (199 lines)
    ├── planning_phases.py (172 lines)
    ├── utils.py (51 lines)
    └── README.md
```

## Module Responsibilities

### `models.py`
- `PhaseResult` dataclass for phase execution results
- `MAX_RETRIES` constant

### `executor.py`
- `PhaseExecutor` class that combines all phase mixins
- Initialization and script execution delegation

### `discovery_phases.py` (DiscoveryPhaseMixin)
- `phase_discovery()` - Project structure analysis
- `phase_context()` - Relevant file discovery

### `requirements_phases.py` (RequirementsPhaseMixin)
- `phase_historical_context()` - Graphiti knowledge graph integration
- `phase_requirements()` - Interactive and automated requirements gathering
- `phase_research()` - External integration validation

### `spec_phases.py` (SpecPhaseMixin)
- `phase_quick_spec()` - Simple task spec creation
- `phase_spec_writing()` - Full spec.md document creation
- `phase_self_critique()` - AI-powered spec validation

### `planning_phases.py` (PlanningPhaseMixin)
- `phase_planning()` - Implementation plan generation
- `phase_validation()` - Final validation with auto-fix

### `utils.py`
- `run_script()` - Helper for executing Python scripts

## Backward Compatibility

The main `phases.py` file re-exports all public APIs, ensuring existing imports continue to work:

```python
from spec.phases import PhaseExecutor, PhaseResult, MAX_RETRIES
```

## Design Pattern

The refactoring uses the **Mixin Pattern** to separate concerns:
- Each mixin handles a logical group of related phases
- The `PhaseExecutor` class inherits from all mixins
- Shared utilities are extracted to separate modules

## Benefits

1. **Modularity**: Each file has a clear, focused responsibility
2. **Maintainability**: Easier to locate and modify specific phase logic
3. **Readability**: Smaller files are easier to understand
4. **Testability**: Individual mixins can be tested in isolation
5. **Extensibility**: New phases can be added without modifying existing code
6. **Type Safety**: Proper type hints throughout

## Critical Development Gotchas

> **MUST READ before modifying any phase code.**

### Gotcha 1: Stale `spec_dir` after spec folder rename

The orchestrator renames the spec folder after the requirements phase (`001-pending` → `001-meaningful-name`). The `PhaseExecutor` stores `spec_dir`, `spec_validator`, and `task_logger` as instance attributes.

**If you don't update these after rename, all subsequent phases check the WRONG path.**

The fix is in `orchestrator.py` — after `_rename_spec_dir_from_requirements()`, all references are synced. **Never add a new stateful reference to spec_dir without also updating it in the orchestrator's post-rename block.**

### Gotcha 2: Agent `success=False` does NOT mean file wasn't created

`agent_runner.py:run_agent()` returns `(False, error_text)` when the SDK throws ANY exception — even if the agent already created the target file. Common causes: rate limit hit after file write, timeout after file write, network error after file write.

**Rule:** In ALL phase methods that use agents, check file existence FIRST:

```python
# CORRECT pattern:
if target_file.exists():
    result = validator.validate(target_file)
    if result.valid:
        return PhaseResult(phase, True, ...)  # Accept even if success=False
else:
    errors.append(f"File not created ({output[:200]})")

# WRONG pattern:
if not success:
    errors.append("Agent failed")  # ← NEVER do this without checking file
```

This pattern is implemented in: `spec_phases.py`, `planning_phases.py`, `requirements_phases.py`.

### Gotcha 3: Phase retry with existing files

When a phase retries (up to `MAX_RETRIES=3`), the file from a previous attempt may already exist. The file-existence check handles this naturally — if attempt 1 created a valid file but returned `success=False`, attempt 2's file-existence check will find it and succeed.

### Gotcha 4: Error messages must include detail

When an agent fails, include `output[:200]` in the error message. Without this, debugging is impossible because "Agent did not create spec.md" gives no clue about what actually went wrong.

## File Size Comparison

- **Original**: 720 lines in single file
- **Refactored**: 14-line entry point + 8 modular files (892 total lines including docs)
- **Main Entry Point Reduction**: 98% smaller (720 → 14 lines)
