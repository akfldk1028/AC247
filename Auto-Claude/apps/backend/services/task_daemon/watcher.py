"""
Task Daemon Watcher - File System Watching
==========================================

Watches .auto-claude/specs/ folder for changes.

Module maintainability:
- Single responsibility: file watching only
- Debouncing to prevent duplicate events
- Clean callback interface
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Callable

# Try to import watchdog
try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    Observer = None  # type: ignore
    FileSystemEventHandler = object  # type: ignore
    FileSystemEvent = None  # type: ignore

from .types import DaemonConfig


class SpecsEventHandler(FileSystemEventHandler):
    """
    Watchdog event handler for specs folder changes.

    Features:
    - Watches for implementation_plan.json changes
    - Debouncing to prevent duplicate events
    - Callback-based notification
    """

    def __init__(
        self,
        callback: Callable[[str, Path], None],
        debounce_seconds: float = DaemonConfig.DEBOUNCE_SECONDS,
    ):
        """
        Initialize handler.

        Args:
            callback: Function to call with (spec_id, spec_dir)
            debounce_seconds: Time to wait before processing duplicate events
        """
        super().__init__()
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._last_events: dict[str, float] = {}
        self._lock = threading.Lock()

    def _should_process(self, spec_id: str) -> bool:
        """Check if event should be processed (debouncing)."""
        now = time.time()
        with self._lock:
            last_time = self._last_events.get(spec_id, 0)
            if now - last_time < self.debounce_seconds:
                return False
            self._last_events[spec_id] = now

            # Prune stale entries to prevent memory leak (BUG 15)
            if len(self._last_events) > 500:
                cutoff = now - 60.0  # Remove entries older than 60s
                self._last_events = {
                    k: v for k, v in self._last_events.items() if v > cutoff
                }

            return True

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        self._handle_event(event)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        self._handle_event(event)

    def _handle_event(self, event: FileSystemEvent) -> None:
        """Process file system event."""
        if event.is_directory:
            return

        # Only watch implementation_plan.json
        if not event.src_path.endswith("implementation_plan.json"):
            return

        spec_dir = Path(event.src_path).parent
        spec_id = spec_dir.name

        # Debounce
        if self._should_process(spec_id):
            self.callback(spec_id, spec_dir)


class SpecsWatcher:
    """
    High-level wrapper for file system watching.

    Usage:
        watcher = SpecsWatcher(specs_dir, on_change_callback)
        watcher.start()
        # ... do work ...
        watcher.stop()
    """

    def __init__(
        self,
        specs_dir: Path,
        callback: Callable[[str, Path], None],
        debounce_seconds: float = DaemonConfig.DEBOUNCE_SECONDS,
    ):
        """
        Initialize watcher.

        Args:
            specs_dir: Directory to watch (.auto-claude/specs/)
            callback: Function to call on changes
            debounce_seconds: Debounce time
        """
        if not HAS_WATCHDOG:
            raise ImportError("watchdog package is required for file watching")

        self.specs_dir = specs_dir
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._observer: Observer | None = None
        self._handler: SpecsEventHandler | None = None

    def start(self) -> None:
        """Start watching for changes."""
        if self._observer is not None:
            return

        self._handler = SpecsEventHandler(
            self.callback,
            self.debounce_seconds,
        )
        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            str(self.specs_dir),
            recursive=True,
        )
        self._observer.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Stop watching (safe to call multiple times, BUG 23)."""
        observer = self._observer
        if observer is None:
            return

        self._observer = None
        self._handler = None

        try:
            observer.stop()
            observer.join(timeout=timeout)
        except Exception:
            pass

    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._observer is not None and self._observer.is_alive()


def check_watchdog_available() -> bool:
    """Check if watchdog is available."""
    return HAS_WATCHDOG
