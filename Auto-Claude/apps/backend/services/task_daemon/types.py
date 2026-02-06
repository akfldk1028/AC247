"""
Task Daemon Types - Enums, Constants, and Data Classes
=======================================================

Module maintainability:
- All type definitions in one place
- Easy to add new task types/priorities
- Clear separation from business logic
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING
import subprocess

if TYPE_CHECKING:
    pass


# =============================================================================
# ENUMS
# =============================================================================


class TaskType(str, Enum):
    """Task types for large project orchestration.

    Plan Mode Tasks: Read-only exploration (design, analysis)
    Implementation Tasks: Code changes (impl, frontend, backend)
    """
    # Plan Mode Tasks (설계/분석 - read-only exploration)
    DESIGN = "design"              # 프로젝트/모듈 설계
    ARCHITECTURE = "architecture"  # 아키텍처 설계
    PLANNING = "planning"          # 구현 계획 수립
    RESEARCH = "research"          # 코드베이스 분석/조사
    REVIEW = "review"              # 코드 리뷰

    # Implementation Tasks (구현 - headless mode)
    IMPLEMENTATION = "impl"        # 구현
    FRONTEND = "frontend"          # 프론트엔드 구현
    BACKEND = "backend"            # 백엔드 구현
    DATABASE = "database"          # 데이터베이스 작업
    API = "api"                    # API 개발

    # Verification & Error-Check Tasks
    VERIFY = "verify"              # 구현 검증 (테스트/빌드/런타임)
    ERROR_CHECK = "error_check"    # 에러 수정

    # Other Tasks
    TEST = "test"                  # 테스트
    INTEGRATION = "integration"    # 통합
    DOCUMENTATION = "docs"         # 문서화
    DEFAULT = "default"            # 기본


class ExecutionMode(str, Enum):
    """Execution modes for Claude CLI integration."""
    PLAN = "plan"               # Plan mode (--permission-mode plan)
    HEADLESS = "headless"       # Headless mode (--dangerously-skip-permissions)
    STANDARD = "standard"       # Standard interactive mode


class TaskPriority(int, Enum):
    """Task priority levels (lower = higher priority)."""
    CRITICAL = 0    # 최우선 (설계, 아키텍처)
    HIGH = 1        # 높음 (핵심 모듈)
    NORMAL = 2      # 보통 (일반 구현)
    LOW = 3         # 낮음 (문서, 정리)


# =============================================================================
# CONSTANTS
# =============================================================================


# Task types that should use Plan mode (design/analysis)
PLAN_MODE_TASK_TYPES = frozenset({
    "design", "architecture", "planning", "research", "review",
    TaskType.DESIGN, TaskType.ARCHITECTURE, TaskType.PLANNING,
    TaskType.RESEARCH, TaskType.REVIEW,
})

# Task statuses that should trigger auto-start
QUEUE_STATUSES = frozenset({"queue", "backlog", "queued"})

# Task statuses that indicate task is already running or completed
RUNNING_STATUSES = frozenset({"in_progress", "ai_review", "human_review"})
COMPLETED_STATUSES = frozenset({"done", "completed", "merged", "pr_created"})
ERROR_STATUSES = frozenset({"error", "failed", "stuck"})

# All statuses that should NOT trigger auto-start
NO_START_STATUSES = RUNNING_STATUSES | COMPLETED_STATUSES | ERROR_STATUSES


# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class TaskState:
    """State tracking for a single running task."""

    spec_id: str
    spec_dir: Path
    process: subprocess.Popen | None = None
    pid: int | None = None
    started_at: datetime | None = None
    last_update: datetime | None = None
    status: str = "unknown"
    error_count: int = 0
    recovery_count: int = 0
    last_error: str | None = None

    # Large project support
    task_type: str = "default"
    priority: int = TaskPriority.NORMAL
    depends_on: list[str] = field(default_factory=list)
    parent_task: str | None = None
    child_tasks: list[str] = field(default_factory=list)

    # Worktree and execution mode support
    worktree_path: Path | None = None
    execution_mode: str = "standard"

    # Recovery coordination (prevents race between _read_output and _recover_task)
    recovering: bool = False

    def is_running(self) -> bool:
        """Check if task process is still running."""
        if self.process is None:
            return False
        return self.process.poll() is None

    def to_dict(self) -> dict:
        """Convert to dictionary for logging/status."""
        return {
            "spec_id": self.spec_id,
            "spec_dir": str(self.spec_dir),
            "pid": self.pid,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "error_count": self.error_count,
            "recovery_count": self.recovery_count,
            "last_error": self.last_error,
            "is_running": self.is_running(),
            "task_type": self.task_type,
            "priority": self.priority,
            "depends_on": self.depends_on,
            "parent_task": self.parent_task,
            "child_tasks": self.child_tasks,
            "worktree_path": str(self.worktree_path) if self.worktree_path else None,
            "execution_mode": self.execution_mode,
        }


@dataclass
class QueuedTask:
    """Task waiting in queue with priority."""

    spec_id: str
    spec_dir: Path
    priority: int = TaskPriority.NORMAL
    task_type: str = "default"
    depends_on: list[str] = field(default_factory=list)
    parent_task: str | None = None
    queued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __lt__(self, other: QueuedTask) -> bool:
        """For priority queue sorting (lower priority value = higher priority)."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.queued_at < other.queued_at


@dataclass
class DaemonState:
    """Persistent daemon state for recovery across restarts."""

    recovery_counts: dict[str, int] = field(default_factory=dict)
    error_counts: dict[str, int] = field(default_factory=dict)
    last_errors: dict[str, str] = field(default_factory=dict)
    completed_tasks: list[str] = field(default_factory=list)
    task_hierarchy: dict[str, list[str]] = field(default_factory=dict)
    started_at: str | None = None
    last_updated: str | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "recovery_counts": self.recovery_counts,
            "error_counts": self.error_counts,
            "last_errors": self.last_errors,
            "completed_tasks": self.completed_tasks,
            "task_hierarchy": self.task_hierarchy,
            "started_at": self.started_at,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DaemonState:
        """Create from dictionary."""
        return cls(
            recovery_counts=data.get("recovery_counts", {}),
            error_counts=data.get("error_counts", {}),
            last_errors=data.get("last_errors", {}),
            completed_tasks=data.get("completed_tasks", []),
            task_hierarchy=data.get("task_hierarchy", {}),
            started_at=data.get("started_at"),
            last_updated=data.get("last_updated"),
        )


# =============================================================================
# CONFIGURATION DEFAULTS
# =============================================================================


class DaemonConfig:
    """Default configuration values for TaskDaemon."""

    STUCK_TIMEOUT_SECONDS = 600
    CHECK_INTERVAL_SECONDS = 30
    MAX_RECOVERY_ATTEMPTS = 3
    MAX_CONCURRENT_TASKS = 1
    STATE_FILE_NAME = ".daemon_state.json"
    WORKTREE_DIR_NAME = ".worktrees"
    DEBOUNCE_SECONDS = 2.0
