"""
Task Daemon State - State Persistence
=====================================

Handles saving and loading daemon state.

Module maintainability:
- Single responsibility: state persistence
- Atomic file writes
- Recovery count tracking
- Thread-safe: all mutations protected by internal lock
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from .types import DaemonState, DaemonConfig

if TYPE_CHECKING:
    from logging import Logger


class StateManager:
    """
    Manages daemon state persistence.

    Features:
    - Thread-safe: internal lock protects all mutations
    - Atomic file writes with unique temp files
    - Recovery count tracking
    - Task completion tracking with O(1) lookups
    """

    def __init__(
        self,
        specs_dir: Path,
        state_file_name: str = DaemonConfig.STATE_FILE_NAME,
        logger: Logger | None = None,
    ):
        self.specs_dir = specs_dir
        self.state_file_name = state_file_name
        self._logger = logger
        self._state = DaemonState()
        self._lock = threading.Lock()
        # O(1) lookup shadow set for completed_tasks (BUG 12)
        self._completed_set: set[str] = set()

    def _log(self, level: str, message: str) -> None:
        if self._logger:
            getattr(self._logger, level)(message)

    @property
    def state(self) -> DaemonState:
        return self._state

    def _get_state_file_path(self) -> Path:
        return self.specs_dir / self.state_file_name

    def load(self) -> DaemonState:
        state_file = self._get_state_file_path()

        if not state_file.exists():
            self._state = DaemonState()
            self._completed_set = set()
            return self._state

        try:
            with open(state_file, encoding="utf-8-sig") as f:
                data = json.load(f)
            self._state = DaemonState.from_dict(data)
            self._completed_set = set(self._state.completed_tasks)
            self._log("info", f"State restored: {len(self._state.completed_tasks)} completed tasks")
        except (OSError, json.JSONDecodeError) as e:
            self._log("warning", f"Failed to load state: {e}")
            self._state = DaemonState()
            self._completed_set = set()

        return self._state

    def save(self) -> bool:
        """Save state to file (atomic write with unique temp file)."""
        state_file = self._get_state_file_path()

        try:
            self._state.last_updated = datetime.now(timezone.utc).isoformat()
            # Unique temp file per thread to prevent concurrent write conflicts (BUG 13)
            temp_path = state_file.with_suffix(
                f".tmp.{os.getpid()}.{threading.get_ident()}"
            )

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._state.to_dict(), f, indent=2)

            temp_path.replace(state_file)
            return True
        except Exception as e:
            self._log("warning", f"Failed to save state: {e}")
            # Clean up temp file on failure
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
            return False

    # -------------------------------------------------------------------------
    # Recovery count management (all thread-safe)
    # -------------------------------------------------------------------------

    def get_recovery_count(self, spec_id: str) -> int:
        with self._lock:
            return self._state.recovery_counts.get(spec_id, 0)

    def increment_recovery_count(self, spec_id: str) -> int:
        with self._lock:
            count = self._state.recovery_counts.get(spec_id, 0) + 1
            self._state.recovery_counts[spec_id] = count
            self.save()
            return count

    def reset_recovery_count(self, spec_id: str) -> None:
        with self._lock:
            self._state.recovery_counts.pop(spec_id, None)
            self._state.error_counts.pop(spec_id, None)
            self._state.last_errors.pop(spec_id, None)
            self.save()

    # -------------------------------------------------------------------------
    # Error tracking (thread-safe)
    # -------------------------------------------------------------------------

    def record_error(self, spec_id: str, error: str) -> None:
        with self._lock:
            self._state.error_counts[spec_id] = (
                self._state.error_counts.get(spec_id, 0) + 1
            )
            self._state.last_errors[spec_id] = error
            self.save()

    def get_last_error(self, spec_id: str) -> str | None:
        with self._lock:
            return self._state.last_errors.get(spec_id)

    # -------------------------------------------------------------------------
    # Task completion tracking (thread-safe, O(1) lookups)
    # -------------------------------------------------------------------------

    def mark_completed(self, spec_id: str) -> None:
        with self._lock:
            if spec_id not in self._completed_set:
                self._completed_set.add(spec_id)
                self._state.completed_tasks.append(spec_id)
                self.save()

    def is_completed(self, spec_id: str) -> bool:
        with self._lock:
            return spec_id in self._completed_set

    def are_dependencies_met(self, depends_on: list[str]) -> bool:
        with self._lock:
            if not depends_on:
                return True
            return all(self._is_dep_met(dep) for dep in depends_on)

    def _is_dep_met(self, dep: str) -> bool:
        """Check if a single dependency is met.

        Uses a 3-tier matching strategy so that unresolved or truncated
        dependency references still match their completed spec IDs:

        1. Exact match (fastest, covers resolved deps)
        2. Number-prefix match: "002-core-calc" matches "002-core-calc-impl-arith..."
           by checking if any completed spec shares the same leading number
        3. Prefix/substring match: dep is a prefix of a completed spec ID
        """
        # 1. Exact match
        if dep in self._completed_set:
            return True

        # 2. Number-prefix + slug-prefix match
        #    e.g., "002-core-calculator-implementation" matches
        #    "002-core-calculator-implementation-arithmetic-operatio"
        num_match = re.match(r"^(\d+)", dep)
        if num_match:
            prefix = num_match.group(1).zfill(3)  # normalize to 3-digit
            dep_lower = dep.lower()
            for completed in self._completed_set:
                completed_lower = completed.lower()
                # Same number prefix AND dep is a prefix of (or equal to) completed
                if completed_lower.startswith(prefix + "-"):
                    if completed_lower.startswith(dep_lower):
                        return True
                    # Also match pure number refs: dep="002" matches "002-anything"
                    if dep_lower == prefix:
                        return True

        # 3. General prefix match (no number prefix)
        dep_lower = dep.lower()
        if len(dep_lower) >= 3:  # avoid too-short matches
            for completed in self._completed_set:
                if completed.lower().startswith(dep_lower):
                    return True

        return False

    # -------------------------------------------------------------------------
    # Task hierarchy (thread-safe)
    # -------------------------------------------------------------------------

    def add_child_task(self, parent_id: str, child_id: str) -> None:
        with self._lock:
            if parent_id not in self._state.task_hierarchy:
                self._state.task_hierarchy[parent_id] = []
            if child_id not in self._state.task_hierarchy[parent_id]:
                self._state.task_hierarchy[parent_id].append(child_id)
                self.save()

    def get_child_tasks(self, parent_id: str) -> list[str]:
        with self._lock:
            return list(self._state.task_hierarchy.get(parent_id, []))

    # -------------------------------------------------------------------------
    # Startup tracking
    # -------------------------------------------------------------------------

    def set_started_at(self) -> None:
        with self._lock:
            self._state.started_at = datetime.now(timezone.utc).isoformat()
            self.save()

    def get_started_at(self) -> str | None:
        with self._lock:
            return self._state.started_at
