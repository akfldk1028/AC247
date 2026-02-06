"""
Services Module
===============

Background services and orchestration for Auto Claude.

Architecture:
-------------
services/
├── __init__.py           # Public API (this file)
├── task_daemon/          # Modular 24/7 daemon (package)
│   ├── __init__.py      # TaskDaemon class
│   ├── types.py         # Enums, constants, data classes
│   ├── watcher.py       # File system watching
│   ├── executor.py      # Task execution (run.py, Claude CLI)
│   └── state.py         # State persistence
├── spec_factory.py       # Programmatic spec creation
├── orchestrator.py       # Service coordination
├── recovery.py           # Recovery utilities
└── context.py            # Service context

Key Components:
- TaskDaemon: 24/7 headless task manager with parallel execution
- SpecFactory: Programmatic spec creation for design agents
- ServiceOrchestrator: Service coordination

Maintainability:
- Each module has single responsibility
- Clean interfaces between modules
- Type hints throughout
"""

from .context import ServiceContext
from .orchestrator import ServiceOrchestrator
from .recovery import RecoveryManager
from .spec_factory import SpecFactory, create_spec_factory

# Import from modular task_daemon package
from .task_daemon import (
    TaskDaemon,
    create_daemon,
    TaskType,
    TaskPriority,
    ExecutionMode,
    TaskState,
    QueuedTask,
    DaemonState,
    DaemonConfig,
)

__all__ = [
    # Services
    "ServiceContext",
    "ServiceOrchestrator",
    "RecoveryManager",
    # Task Daemon
    "TaskDaemon",
    "create_daemon",
    "TaskType",
    "TaskPriority",
    "ExecutionMode",
    "TaskState",
    "QueuedTask",
    "DaemonState",
    "DaemonConfig",
    # Spec Factory
    "SpecFactory",
    "create_spec_factory",
]
