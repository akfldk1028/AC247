"""
Task Daemon Package - 24/7 Headless Task Manager
================================================

A modular task daemon for large-scale project automation.

Module Structure:
-----------------
task_daemon/
├── __init__.py    # Public API (this file)
├── types.py       # Enums, constants, data classes
├── watcher.py     # File system watching
├── executor.py    # Task execution (run.py, Claude CLI)
├── state.py       # State persistence

Usage:
------
    from services.task_daemon import TaskDaemon, create_daemon

    daemon = TaskDaemon(
        project_dir=Path("C:/path/to/project"),
        max_concurrent_tasks=4,
    )
    daemon.start()

Maintainability:
---------------
- Each module has single responsibility
- Clean interfaces between modules
- Easy to extend or modify individual components
- Type hints throughout
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

# Import from submodules
from .types import (
    TaskType,
    TaskPriority,
    ExecutionMode,
    TaskState,
    QueuedTask,
    DaemonState,
    DaemonConfig,
    QUEUE_STATUSES,
    NO_START_STATUSES,
    COMPLETED_STATUSES,
    PLAN_MODE_TASK_TYPES,
)
from .watcher import SpecsWatcher, check_watchdog_available
from .executor import TaskExecutor, find_auto_claude_backend
from .state import StateManager


# Task types that trigger auto-verify after successful completion
IMPL_TASK_TYPES = frozenset({"impl", "frontend", "backend", "database", "api"})

# Maximum verify→error_check→verify cycles before giving up
MAX_VERIFY_ATTEMPTS = 3

__all__ = [
    # Main class
    "TaskDaemon",
    "create_daemon",
    # Types
    "TaskType",
    "TaskPriority",
    "ExecutionMode",
    "TaskState",
    "QueuedTask",
    "DaemonState",
    "DaemonConfig",
    # Submodules
    "SpecsWatcher",
    "TaskExecutor",
    "StateManager",
]


class TaskDaemon:
    """
    24/7 Task Daemon - Headless background task manager.

    Features:
    - Parallel task execution (max_concurrent_tasks)
    - Task dependencies (depends_on)
    - Priority queue (priority field)
    - Git worktree isolation (use_worktrees)
    - Claude CLI integration (plan mode, headless mode)
    - Auto-recovery for stuck tasks

    Architecture:
    - Watcher: Monitors specs folder for changes
    - Scheduler: Manages task queue and parallel execution
    - Executor: Builds and runs task commands
    - StateManager: Persists state across restarts
    """

    def __init__(
        self,
        project_dir: Path,
        *,
        stuck_timeout: int | None = None,
        check_interval: int | None = None,
        max_recovery: int | None = None,
        max_concurrent_tasks: int | None = None,
        use_worktrees: bool = False,
        headless_mode: bool = True,
        use_claude_cli: bool = False,
        claude_cli_path: str | None = None,
        log_file: Path | None = None,
        on_task_start: Callable[[str], None] | None = None,
        on_task_complete: Callable[[str, bool], None] | None = None,
        on_task_stuck: Callable[[str], None] | None = None,
        on_task_recovered: Callable[[str, int], None] | None = None,
        on_all_tasks_complete: Callable[[], None] | None = None,
    ):
        """Initialize Task Daemon."""
        self.project_dir = Path(project_dir).resolve()
        self.specs_dir = self.project_dir / ".auto-claude" / "specs"
        self.worktrees_dir = self.project_dir / DaemonConfig.WORKTREE_DIR_NAME
        self.auto_claude_dir = find_auto_claude_backend(self.project_dir)

        # Configuration
        self.stuck_timeout = stuck_timeout or DaemonConfig.STUCK_TIMEOUT_SECONDS
        self.check_interval = check_interval or DaemonConfig.CHECK_INTERVAL_SECONDS
        self.max_recovery = max_recovery or DaemonConfig.MAX_RECOVERY_ATTEMPTS
        self.max_concurrent_tasks = max_concurrent_tasks or DaemonConfig.MAX_CONCURRENT_TASKS
        self.use_worktrees = use_worktrees
        self.headless_mode = headless_mode
        self.use_claude_cli = use_claude_cli

        # Callbacks
        self._on_task_start = on_task_start
        self._on_task_complete = on_task_complete
        self._on_task_stuck = on_task_stuck
        self._on_task_recovered = on_task_recovered
        self._on_all_tasks_complete = on_all_tasks_complete

        # Setup logging
        self._setup_logging(log_file)

        # Initialize components
        self._state_manager = StateManager(self.specs_dir, logger=self._logger)
        self._executor = TaskExecutor(
            self.project_dir,
            self.specs_dir,
            self.auto_claude_dir,
            use_claude_cli=use_claude_cli,
            claude_cli_path=claude_cli_path,
            headless_mode=headless_mode,
            logger=self._logger,
        )

        # Runtime state
        self.running_tasks: dict[str, TaskState] = {}
        self.task_queue: list[QueuedTask] = []
        self._watcher: SpecsWatcher | None = None
        self._checker_thread: threading.Thread | None = None
        self._scheduler_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._queue_condition = threading.Condition(self._lock)
        self._all_complete_fired = False  # Guard against double-firing (BUG 5)

        # Event-driven status writes (OpenClaw pattern: real-time updates)
        # Set by any state change; the status writer thread wakes immediately.
        self._status_dirty = threading.Event()

    def _setup_logging(self, log_file: Path | None) -> None:
        """Setup logging configuration."""
        self._logger = logging.getLogger(f"TaskDaemon-{self.project_dir.name}")
        self._logger.setLevel(logging.DEBUG)

        if self._logger.handlers:
            return

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(
            logging.DEBUG if os.environ.get("DEBUG") else logging.INFO
        )
        console_format = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_format)
        self._logger.addHandler(console_handler)

        if log_file:
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_format)
            self._logger.addHandler(file_handler)

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Start the daemon (blocking)."""
        if not check_watchdog_available():
            raise ImportError("watchdog package is required")

        if not self.specs_dir.exists():
            self._logger.info(f"Creating specs directory: {self.specs_dir}")
            self.specs_dir.mkdir(parents=True, exist_ok=True)

        if not self.auto_claude_dir and not self._executor.claude_cli_path:
            raise FileNotFoundError("Neither Auto-Claude backend nor Claude CLI found")

        self._logger.info(f"Starting daemon: {self.project_dir}")

        # Load state
        self._state_manager.load()
        self._state_manager.set_started_at()

        # Scan existing tasks
        self._scan_existing_tasks()

        # Start components
        self._start_watcher()
        self._start_scheduler()
        self._start_stuck_checker()

        self._logger.info("Daemon started")

        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(timeout=1.0)
        except KeyboardInterrupt:
            self._logger.info("Received interrupt")
            self.stop()

    def stop(self) -> None:
        """Stop the daemon gracefully."""
        self._logger.info("Stopping daemon...")
        self._stop_event.set()

        with self._queue_condition:
            self._queue_condition.notify_all()

        if self._watcher:
            self._watcher.stop()
            self._watcher = None

        if self._checker_thread and self._checker_thread.is_alive():
            self._checker_thread.join(timeout=5.0)

        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5.0)

        with self._lock:
            for spec_id, state in list(self.running_tasks.items()):
                if state.is_running():
                    self._kill_task(state)

        self._state_manager.save()
        self._logger.info("Daemon stopped")

    def _start_watcher(self) -> None:
        """Start file system watcher."""
        self._watcher = SpecsWatcher(
            self.specs_dir,
            self._on_spec_change,
        )
        self._watcher.start()

    def _start_scheduler(self) -> None:
        """Start task scheduler thread."""
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="TaskScheduler",
            daemon=True,
        )
        self._scheduler_thread.start()

    def _start_stuck_checker(self) -> None:
        """Start stuck task checker thread."""
        self._checker_thread = threading.Thread(
            target=self._stuck_checker_loop,
            name="StuckChecker",
            daemon=True,
        )
        self._checker_thread.start()

    # -------------------------------------------------------------------------
    # Task Discovery
    # -------------------------------------------------------------------------

    def _scan_existing_tasks(self) -> None:
        """Scan for existing tasks and queue them.

        Also discovers externally-completed tasks (e.g., completed by a
        previous daemon instance or manual execution) and adds them to
        _completed_set so that dependency checks work correctly.
        """
        if not self.specs_dir.exists():
            return

        # Repair broken dependency references before scanning
        # This fixes internal refs (e.g., "002-foo") → actual spec IDs (e.g., "135-foo-...")
        self._repair_dependencies()

        self._logger.info("Scanning existing specs...")
        queued_count = 0
        discovered_completed = 0

        for spec_dir in sorted(self.specs_dir.iterdir()):
            if not spec_dir.is_dir() or spec_dir.name.startswith("."):
                continue

            plan_path = spec_dir / "implementation_plan.json"
            if plan_path.exists():
                plan = self._load_plan(spec_dir)
                if plan:
                    status = plan.get("status", "").lower()
                    if status in QUEUE_STATUSES:
                        self._enqueue_task(spec_dir.name, spec_dir, plan)
                        queued_count += 1
                    elif status in COMPLETED_STATUSES:
                        # Track externally-completed tasks so dependency
                        # checks work even after daemon restart
                        if not self._state_manager.is_completed(spec_dir.name):
                            self._state_manager.mark_completed(spec_dir.name)
                            discovered_completed += 1

        if discovered_completed:
            self._logger.info(
                f"Discovered {discovered_completed} externally-completed tasks"
            )
        self._logger.info(f"Scan complete: {queued_count} tasks queued")

    def _repair_dependencies(self) -> None:
        """Repair broken dependency references using SpecFactory."""
        try:
            from services.spec_factory import SpecFactory
            factory = SpecFactory(self.project_dir)
            repaired = factory.repair_all_dependencies()
            if repaired > 0:
                self._logger.info(f"Repaired dependency references in {repaired} specs")
        except Exception as e:
            self._logger.warning(f"Failed to repair dependencies: {e}")

    def _on_spec_change(self, spec_id: str, spec_dir: Path) -> None:
        """Handle spec change event."""
        plan = self._load_plan(spec_dir)
        if not plan:
            return

        status = plan.get("status", "").lower()

        with self._lock:
            if spec_id in self.running_tasks:
                self.running_tasks[spec_id].last_update = datetime.now(timezone.utc)
                self.running_tasks[spec_id].status = status
                return

            if any(t.spec_id == spec_id for t in self.task_queue):
                return

            if self._should_queue_task(status, spec_id):
                self._enqueue_task(spec_id, spec_dir, plan)

    def _should_queue_task(self, status: str, spec_id: str) -> bool:
        """Check if task should be queued."""
        if status in NO_START_STATUSES:
            return False
        if status not in QUEUE_STATUSES:
            return False
        if self._state_manager.get_recovery_count(spec_id) >= self.max_recovery:
            return False
        return True

    @staticmethod
    def _normalize_depends_on(raw: Any) -> list[str]:
        """Normalize dependsOn which may be a string-encoded JSON array."""
        if isinstance(raw, list):
            return raw
        if isinstance(raw, str):
            raw = raw.strip()
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
            # Comma-separated string
            if "," in raw:
                return [d.strip() for d in raw.split(",") if d.strip()]
            if raw:
                return [raw]
        return []

    def _enqueue_task(self, spec_id: str, spec_dir: Path, plan: dict) -> None:
        """Add task to priority queue."""
        task_type = plan.get("taskType", plan.get("task_type", "default"))
        priority = plan.get("priority", TaskPriority.NORMAL)
        raw_deps = plan.get("dependsOn", plan.get("depends_on", []))
        depends_on = self._normalize_depends_on(raw_deps)
        parent_task = plan.get("parentTask", plan.get("parent_task"))

        queued_task = QueuedTask(
            spec_id=spec_id,
            spec_dir=spec_dir,
            priority=priority,
            task_type=task_type,
            depends_on=depends_on,
            parent_task=parent_task,
        )

        with self._queue_condition:
            self.task_queue.append(queued_task)
            self.task_queue.sort()
            self._all_complete_fired = False  # Reset so callback fires again
            self._queue_condition.notify()

        self._logger.info(f"Queued: {spec_id} (priority={priority}, type={task_type})")
        self._notify_status_change()

    def _load_plan(self, spec_dir: Path) -> dict | None:
        """Load implementation plan.

        Retries once after a short delay on PermissionError (Windows file
        locking when run.py is writing to the same file concurrently).
        """
        plan_path = spec_dir / "implementation_plan.json"
        if not plan_path.exists():
            return None
        for attempt in range(2):
            try:
                with open(plan_path, encoding="utf-8-sig") as f:
                    return json.load(f)
            except PermissionError:
                if attempt == 0:
                    import time
                    time.sleep(0.1)  # 100ms retry for Windows file lock
                    continue
                if self._logger:
                    self._logger.warning(f"PermissionError loading plan {plan_path} (after retry)")
                return None
            except (OSError, json.JSONDecodeError) as e:
                if self._logger:
                    self._logger.warning(f"Failed to load plan {plan_path}: {e}")
                return None
        return None

    def _update_plan_status(
        self,
        spec_dir: Path,
        status: str,
        xstate_state: str | None = None,
        error_message: str | None = None,
    ) -> bool:
        """Update plan status."""
        plan_path = spec_dir / "implementation_plan.json"
        try:
            plan = self._load_plan(spec_dir) or {}
            plan["status"] = status
            plan["updated_at"] = datetime.now(timezone.utc).isoformat()
            if xstate_state:
                plan["xstateState"] = xstate_state
            if error_message:
                plan["lastError"] = error_message
            temp_path = plan_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)
            temp_path.replace(plan_path)
            return True
        except Exception:
            return False

    # -------------------------------------------------------------------------
    # Scheduler
    # -------------------------------------------------------------------------

    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while not self._stop_event.is_set():
            next_task = None

            with self._queue_condition:
                while not self._stop_event.is_set():
                    if len(self.running_tasks) >= self.max_concurrent_tasks:
                        self._queue_condition.wait(timeout=1.0)
                        continue

                    next_task = self._get_next_ready_task()
                    if next_task:
                        break

                    self._queue_condition.wait(timeout=1.0)

                if self._stop_event.is_set():
                    break

            if next_task:
                self._start_task(next_task)

    def _get_next_ready_task(self) -> QueuedTask | None:
        """Get next task with dependencies met.

        Also cleans up stale queue entries: tasks whose plan status has
        changed externally (e.g., completed by another process) are removed
        from the queue and tracked as completed if appropriate.
        """
        stale_indices = []
        ready_index = None

        for i, task in enumerate(self.task_queue):
            # Re-read plan to detect externally-completed tasks
            plan = self._load_plan(task.spec_dir)
            if plan:
                status = plan.get("status", "").lower()
                if status in COMPLETED_STATUSES:
                    # Task was completed externally — remove from queue
                    stale_indices.append(i)
                    if not self._state_manager.is_completed(task.spec_id):
                        self._state_manager.mark_completed(task.spec_id)
                    self._logger.info(
                        f"Removed stale queue entry: {task.spec_id} (status={status})"
                    )
                    continue
                if status in NO_START_STATUSES:
                    # Already running or in error — skip but don't remove
                    # (might be recovering or externally managed)
                    continue

            if ready_index is None and self._state_manager.are_dependencies_met(task.depends_on):
                ready_index = i

        # Remove stale entries (reverse order to preserve indices)
        for idx in reversed(stale_indices):
            self.task_queue.pop(idx)
            # Adjust ready_index if it was shifted
            if ready_index is not None and idx < ready_index:
                ready_index -= 1

        if ready_index is not None:
            return self.task_queue.pop(ready_index)
        return None

    # -------------------------------------------------------------------------
    # Task Execution
    # -------------------------------------------------------------------------

    def _start_task(self, queued_task: QueuedTask) -> bool:
        """Start a task."""
        spec_id = queued_task.spec_id
        spec_dir = queued_task.spec_dir

        with self._lock:
            if spec_id in self.running_tasks:
                return False

        # Re-read plan status before spawning — another process may have
        # completed this task while it was waiting in the queue
        plan = self._load_plan(spec_dir)
        if plan:
            current_status = plan.get("status", "").lower()
            if current_status in COMPLETED_STATUSES:
                self._logger.info(
                    f"Skipping {spec_id}: already completed (status={current_status})"
                )
                self._state_manager.mark_completed(spec_id)
                return False
            if current_status not in QUEUE_STATUSES and current_status not in ("in_progress",):
                self._logger.info(
                    f"Skipping {spec_id}: unexpected status '{current_status}'"
                )
                return False

        execution_mode = self._executor.get_execution_mode(queued_task.task_type)
        cmd, cwd = self._executor.build_command(
            spec_id, self.project_dir, execution_mode,
            task_type=queued_task.task_type,
        )

        if cmd is None:
            self._logger.error(f"Failed to build command for: {spec_id}")
            return False

        self._logger.info(f"Starting: {spec_id} (mode={execution_mode})")

        try:
            process = self._executor.spawn_process(cmd, cwd)

            state = TaskState(
                spec_id=spec_id,
                spec_dir=spec_dir,
                process=process,
                pid=process.pid,
                started_at=datetime.now(timezone.utc),
                last_update=datetime.now(timezone.utc),
                status="in_progress",
                task_type=queued_task.task_type,
                priority=queued_task.priority,
                depends_on=queued_task.depends_on,
                parent_task=queued_task.parent_task,
                execution_mode=execution_mode,
            )

            with self._lock:
                self.running_tasks[spec_id] = state

            self._update_plan_status(spec_dir, "in_progress", "coding")

            threading.Thread(
                target=self._read_output,
                args=(spec_id, process),
                name=f"Output-{spec_id}",
                daemon=True,
            ).start()

            if self._on_task_start:
                try:
                    self._on_task_start(spec_id)
                except Exception:
                    pass

            self._notify_status_change()
            return True

        except Exception as e:
            self._logger.error(f"Failed to start: {spec_id} - {e}")
            self._state_manager.record_error(spec_id, str(e))
            self._notify_status_change()
            return False

    def _read_output(self, spec_id: str, process: subprocess.Popen) -> None:
        """Read process output line-by-line.

        Uses readline() instead of iterator to avoid Python's read-ahead
        buffer which blocks real-time output. This ensures last_update
        stays current and prevents false stuck detection.

        If the task is being recovered (_recover_task sets state.recovering),
        this thread exits without cleanup since _recover_task handles it (BUG 2).
        """
        lines_read = 0
        try:
            while True:
                # Guard against closed pipe (BUG 10)
                if process.stdout is None or process.stdout.closed:
                    break

                line = process.stdout.readline()
                if not line:
                    break  # EOF - process closed stdout
                lines_read += 1
                line = line.rstrip()
                if line:
                    self._logger.debug(f"[{spec_id}] {line[:200]}")
                with self._lock:
                    if spec_id in self.running_tasks:
                        self.running_tasks[spec_id].last_update = datetime.now(timezone.utc)
        except (ValueError, OSError):
            # ValueError: I/O operation on closed file (stdout closed by _kill_task)
            # OSError: other I/O errors on the pipe
            pass
        except Exception as e:
            self._logger.warning(f"[{spec_id}] Output reader error after {lines_read} lines: {e}")

        self._logger.info(f"[{spec_id}] Output reader finished ({lines_read} lines read)")

        # If task is being recovered, _recover_task handles cleanup (BUG 2)
        with self._lock:
            task = self.running_tasks.get(spec_id)
            if task and task.recovering:
                self._logger.debug(f"[{spec_id}] Recovery in progress, skipping cleanup")
                return

        return_code = process.wait()
        success = return_code == 0

        self._logger.info(f"Completed: {spec_id} (success={success})")

        task_type = None
        spec_dir = None
        with self._lock:
            if spec_id in self.running_tasks:
                state = self.running_tasks[spec_id]
                task_type = state.task_type
                spec_dir = state.spec_dir

                if success:
                    self._state_manager.reset_recovery_count(spec_id)
                    self._state_manager.mark_completed(spec_id)
                    # Don't overwrite "complete" status set by design tasks
                    # (create_batch_child_specs sets parent to "complete")
                    current_plan = self._load_plan(state.spec_dir)
                    current_status = (current_plan or {}).get("status", "").lower()
                    if current_status not in ("complete", "done"):
                        self._update_plan_status(state.spec_dir, "human_review", "human_review")
                else:
                    # Don't overwrite "complete" even on non-zero exit.
                    # Design tasks may exit non-zero after successfully creating
                    # child specs (e.g., worktree cleanup failure).
                    current_plan = self._load_plan(state.spec_dir)
                    current_status = (current_plan or {}).get("status", "").lower()
                    if current_status == "complete":
                        self._state_manager.mark_completed(spec_id)
                        self._logger.info(f"Task {spec_id} already complete despite non-zero exit")
                    else:
                        self._state_manager.record_error(spec_id, f"Exit code {return_code}")
                        self._update_plan_status(state.spec_dir, "error", "error")

                del self.running_tasks[spec_id]

        # Auto-queue verify for successful impl tasks
        if success and task_type in IMPL_TASK_TYPES and spec_dir is not None:
            self._auto_queue_verify(spec_id, spec_dir)

        # After error_check succeeds, re-verify the parent impl task
        if success and task_type == "error_check" and spec_dir is not None:
            parent_spec_id = self._get_parent_spec_id(spec_id, spec_dir)
            if parent_spec_id:
                parent_spec_dir = self.specs_dir / parent_spec_id
                if parent_spec_dir.exists():
                    self._auto_queue_verify(parent_spec_id, parent_spec_dir)

        with self._queue_condition:
            self._queue_condition.notify()

        self._notify_status_change()

        if self._on_task_complete:
            try:
                self._on_task_complete(spec_id, success)
            except Exception:
                pass

        self._check_all_complete()

    def _check_all_complete(self) -> None:
        """Check if all tasks complete (fires callback at most once per cycle, BUG 5)."""
        with self._lock:
            if len(self.running_tasks) == 0 and len(self.task_queue) == 0:
                if self._all_complete_fired:
                    return  # Already fired, don't fire again
                self._all_complete_fired = True
                if self._on_all_tasks_complete:
                    try:
                        self._on_all_tasks_complete()
                    except Exception:
                        pass

    # -------------------------------------------------------------------------
    # Auto-Verify Pipeline
    # -------------------------------------------------------------------------

    def _get_parent_spec_id(self, spec_id: str, spec_dir: Path) -> str | None:
        """Get the parent task ID from a child spec's implementation_plan.json."""
        plan = self._load_plan(spec_dir)
        if not plan:
            return None
        return plan.get("parentTask", plan.get("parent_task"))

    def _auto_queue_verify(self, spec_id: str, spec_dir: Path) -> None:
        """
        Auto-queue a verify task after a successful impl task.

        Creates a verify spec in the specs directory that depends on the
        completed impl spec. The watcher will pick it up and the scheduler
        will queue it once dependencies are met.

        Prevents infinite loops by:
        - Only triggering for IMPL_TASK_TYPES (verify/error_check excluded)
        - Limiting verify attempts via MAX_VERIFY_ATTEMPTS
        """
        # Count existing verify specs for this parent to prevent infinite loops
        verify_count = 0
        for child_dir in self.specs_dir.iterdir():
            if not child_dir.is_dir():
                continue
            child_plan_path = child_dir / "implementation_plan.json"
            if child_plan_path.exists():
                try:
                    with open(child_plan_path, encoding="utf-8-sig") as f:
                        child_plan = json.load(f)
                    if (
                        child_plan.get("taskType", child_plan.get("task_type")) == "verify"
                        and spec_id in child_plan.get("dependsOn", child_plan.get("depends_on", []))
                    ):
                        verify_count += 1
                except (OSError, json.JSONDecodeError):
                    pass

        if verify_count >= MAX_VERIFY_ATTEMPTS:
            self._logger.warning(
                f"Max verify attempts ({MAX_VERIFY_ATTEMPTS}) reached for {spec_id}, skipping"
            )
            return

        # Generate verify spec ID with attempt number for re-verify support
        attempt = verify_count + 1
        verify_spec_id = f"verify-{spec_id}" if attempt == 1 else f"verify-{spec_id}-{attempt}"
        verify_dir = self.specs_dir / verify_spec_id

        if verify_dir.exists():
            self._logger.debug(f"Verify spec already exists: {verify_spec_id}")
            return

        verify_dir.mkdir(parents=True, exist_ok=True)

        # Read the original spec for context
        original_spec_path = spec_dir / "spec.md"
        original_spec = ""
        if original_spec_path.exists():
            try:
                original_spec = original_spec_path.read_text(encoding="utf-8-sig")
            except OSError:
                pass

        # Create verify spec.md
        verify_spec_content = (
            f"# Verify: {spec_id}\n\n"
            f"Verify the implementation of `{spec_id}` by running tests, "
            f"checking for build errors, and performing runtime validation.\n\n"
            f"## Original Spec\n\n{original_spec}\n"
        )
        (verify_dir / "spec.md").write_text(verify_spec_content, encoding="utf-8")

        # Create implementation_plan.json for the verify task
        verify_plan = {
            "status": "queue",
            "taskType": "verify",
            "priority": TaskPriority.HIGH,
            "dependsOn": [spec_id],
            "parentTask": spec_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "phases": [],
        }
        plan_path = verify_dir / "implementation_plan.json"
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump(verify_plan, f, indent=2)

        self._logger.info(f"Auto-queued verify task: {verify_spec_id} (parent: {spec_id})")

    # -------------------------------------------------------------------------
    # Stuck Detection
    # -------------------------------------------------------------------------

    def _stuck_checker_loop(self) -> None:
        """Check for stuck tasks."""
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self.check_interval)
            if self._stop_event.is_set():
                break
            self._check_stuck_tasks()

    def _check_stuck_tasks(self) -> None:
        """Check for stuck tasks."""
        now = datetime.now(timezone.utc)
        tasks_to_recover = []

        with self._lock:
            for spec_id, state in list(self.running_tasks.items()):
                if not state.is_running():
                    continue
                if state.last_update:
                    elapsed = (now - state.last_update).total_seconds()
                    if elapsed > self.stuck_timeout:
                        tasks_to_recover.append((spec_id, state))

        for spec_id, state in tasks_to_recover:
            self._recover_task(spec_id, state)

    def _recover_task(self, spec_id: str, state: TaskState) -> None:
        """Recover a stuck task.

        Sets state.recovering to prevent _read_output from doing cleanup (BUG 2).
        Uses _stop_event.wait() instead of time.sleep() for fast shutdown (BUG 1).
        """
        recovery_count = self._state_manager.increment_recovery_count(spec_id)

        if recovery_count > self.max_recovery:
            self._logger.error(f"Max recovery reached: {spec_id}")
            self._update_plan_status(state.spec_dir, "error", "error", "Max recovery")
            with self._lock:
                self.running_tasks.pop(spec_id, None)
            self._notify_status_change()
            if self._on_task_stuck:
                try:
                    self._on_task_stuck(spec_id)
                except Exception:
                    pass
            return

        self._logger.info(f"Recovering: {spec_id} (attempt {recovery_count})")

        # Signal _read_output to skip cleanup (BUG 2)
        with self._lock:
            state.recovering = True

        self._kill_task(state)

        # Wait for process cleanup; use _stop_event.wait so daemon can
        # shut down without blocking on time.sleep() (BUG 1)
        self._stop_event.wait(timeout=5)
        if self._stop_event.is_set():
            return  # Daemon is shutting down, abort recovery

        with self._lock:
            self.running_tasks.pop(spec_id, None)

        self._update_plan_status(state.spec_dir, "queue", "backlog")

        plan = self._load_plan(state.spec_dir) or {}
        self._enqueue_task(spec_id, state.spec_dir, plan)

        if self._on_task_recovered:
            try:
                self._on_task_recovered(spec_id, recovery_count)
            except Exception:
                pass

    def _kill_task(self, state: TaskState) -> None:
        """Kill a task process and its entire process tree.

        On Windows, terminate() only kills the direct child process.
        Uses taskkill /F /T to kill the full tree (BUG 8).
        Closes stdout pipe to unblock _read_output thread (BUG 10).
        """
        if state.process is None:
            return
        try:
            pid = state.process.pid
            if sys.platform == "win32":
                # taskkill /F /T kills entire process tree on Windows
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=15,
                )
            else:
                # Unix: kill process group
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, 15)  # SIGTERM
                except (ProcessLookupError, PermissionError):
                    state.process.terminate()
                try:
                    state.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        pgid = os.getpgid(pid)
                        os.killpg(pgid, 9)  # SIGKILL
                    except (ProcessLookupError, PermissionError):
                        state.process.kill()
                    state.process.wait(timeout=5)
        except Exception:
            pass
        finally:
            # Close stdout pipe to unblock _read_output readline() (BUG 10)
            try:
                if state.process and state.process.stdout:
                    state.process.stdout.close()
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    def _notify_status_change(self) -> None:
        """Signal that daemon status has changed (triggers immediate file write)."""
        self._status_dirty.set()

    def get_status(self) -> dict:
        """Get daemon status."""
        with self._lock:
            return {
                "project_dir": str(self.project_dir),
                "running": not self._stop_event.is_set(),
                "started_at": self._state_manager.get_started_at(),
                "config": {
                    "max_concurrent_tasks": self.max_concurrent_tasks,
                    "stuck_timeout": self.stuck_timeout,
                    "headless_mode": self.headless_mode,
                },
                "running_tasks": {
                    k: v.to_dict() for k, v in self.running_tasks.items()
                },
                "queued_tasks": [
                    {"spec_id": t.spec_id, "priority": t.priority}
                    for t in self.task_queue
                ],
                "stats": {
                    "running": len(self.running_tasks),
                    "queued": len(self.task_queue),
                    "completed": len(self._state_manager.state.completed_tasks),
                },
            }

    def is_healthy(self) -> bool:
        """Check daemon health."""
        return (
            not self._stop_event.is_set()
            and self._watcher is not None
            and self._watcher.is_running()
        )


def create_daemon(project_dir: str | Path, **kwargs) -> TaskDaemon:
    """Create a TaskDaemon instance."""
    return TaskDaemon(Path(project_dir), **kwargs)
