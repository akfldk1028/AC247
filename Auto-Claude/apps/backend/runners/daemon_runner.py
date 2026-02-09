#!/usr/bin/env python3
"""
Daemon Runner - CLI for Task Daemon
===================================

24/7 Task Daemon을 실행하는 CLI 스크립트.

Usage:
    # 포그라운드 실행
    python runners/daemon_runner.py --project-dir "C:\\DK\\S3\\S3\\calculator"

    # 백그라운드 (nohup) 실행
    nohup python runners/daemon_runner.py --project-dir "..." &

    # Windows 서비스로 등록 (NSSM)
    nssm install AutoClaudeDaemon "python.exe" "runners/daemon_runner.py --project-dir ..."
    nssm start AutoClaudeDaemon

Features:
    - specs 폴더 watching
    - 새 task 감지 → 자동 빌드
    - Stuck 감지 → 자동 복구
    - Graceful shutdown (SIGINT/SIGTERM)
"""

import argparse
import io
import json
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

# Python version check
if sys.version_info < (3, 10):  # noqa: UP036
    sys.exit(
        f"Error: Auto Claude requires Python 3.10 or higher.\n"
        f"You are running Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}\n"
        f"\n"
        f"Please upgrade Python: https://www.python.org/downloads/"
    )

# Configure safe encoding on Windows
if sys.platform == "win32":
    for _stream_name in ("stdout", "stderr"):
        _stream = getattr(sys, _stream_name)
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
                continue
            except (AttributeError, io.UnsupportedOperation, OSError):
                pass
        try:
            if hasattr(_stream, "buffer"):
                _new_stream = io.TextIOWrapper(
                    _stream.buffer,
                    encoding="utf-8",
                    errors="replace",
                    line_buffering=True,
                )
                setattr(sys, _stream_name, _new_stream)
        except (AttributeError, io.UnsupportedOperation, OSError):
            pass
    del _stream_name, _stream
    if "_new_stream" in dir():
        del _new_stream

# Add backend to path
_BACKEND_DIR = Path(__file__).parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from services.task_daemon.types import DaemonConfig


def log(level: str, message: str, **kwargs) -> None:
    """Log a message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    extra = " ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else ""
    prefix = f"[{timestamp}] [{level.upper()}]"
    if extra:
        print(f"{prefix} {message} | {extra}", flush=True)
    else:
        print(f"{prefix} {message}", flush=True)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="24/7 Task Daemon for Auto-Claude with Claude CLI Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic: Start daemon for a project (sequential execution)
    python daemon_runner.py --project-dir "C:\\DK\\S3\\S3\\calculator"

    # Parallel: Run up to 4 tasks concurrently with git worktree isolation
    python daemon_runner.py --project-dir "..." --max-concurrent 4 --use-worktrees

    # Large Project: Full parallel with all features
    python daemon_runner.py --project-dir "..." \\
        --max-concurrent 4 \\
        --use-worktrees \\
        --status-file daemon_status.json \\
        --log-file daemon.log

    # Claude CLI Direct: Use Claude CLI instead of run.py (experimental)
    python daemon_runner.py --project-dir "..." --use-claude-cli

    # Debug mode
    DEBUG=1 python daemon_runner.py --project-dir "..."

    # Windows background (PowerShell)
    Start-Process -NoNewWindow python "daemon_runner.py --project-dir ..."

    # Linux/Mac background
    nohup python daemon_runner.py --project-dir "..." > daemon.log 2>&1 &

    # Windows Service (NSSM)
    nssm install AutoClaudeDaemon "python.exe" "daemon_runner.py --project-dir ..."
    nssm start AutoClaudeDaemon

Claude CLI Features:
    - Plan Mode: Design/architecture tasks use read-only exploration
    - Headless Mode: Skip permission prompts for 24/7 operation
    - Git Worktrees: Complete isolation for parallel task execution
    - Fan-out Pattern: Distribute large projects across parallel sessions
        """,
    )

    parser.add_argument(
        "--project-dir",
        type=Path,
        required=True,
        help="Project directory to watch (containing .auto-claude/specs/)",
    )

    parser.add_argument(
        "--stuck-timeout",
        type=int,
        default=600,
        help="Seconds before a task is considered stuck (default: 600 = 10 min)",
    )

    parser.add_argument(
        "--check-interval",
        type=int,
        default=60,
        help="Seconds between stuck checks (default: 60 = 1 min)",
    )

    parser.add_argument(
        "--max-recovery",
        type=int,
        default=3,
        help="Maximum recovery attempts per task (default: 3)",
    )

    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=DaemonConfig.MAX_CONCURRENT_TASKS,
        help=f"Maximum parallel tasks (default: {DaemonConfig.MAX_CONCURRENT_TASKS})",
    )

    parser.add_argument(
        "--status-file",
        type=Path,
        default=None,
        help="Write daemon status to this JSON file periodically",
    )

    parser.add_argument(
        "--pid-file",
        type=Path,
        default=None,
        help="Write daemon PID to this file",
    )

    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="Write logs to this file (in addition to stdout)",
    )

    # Claude CLI Integration options
    parser.add_argument(
        "--use-worktrees",
        action="store_true",
        help="Use git worktrees for parallel task isolation (recommended for concurrent > 1)",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless mode for 24/7 unattended operation (default: True)",
    )

    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Disable headless mode (interactive prompts)",
    )

    parser.add_argument(
        "--use-claude-cli",
        action="store_true",
        help="Use Claude CLI directly instead of run.py (experimental)",
    )

    parser.add_argument(
        "--claude-cli-path",
        type=str,
        default=None,
        help="Custom path to claude CLI executable",
    )

    args = parser.parse_args()

    # Handle --no-headless flag
    if args.no_headless:
        args.headless = False

    # Validate project directory
    project_dir = args.project_dir.resolve()
    if not project_dir.exists():
        log("error", f"Project directory does not exist: {project_dir}")
        sys.exit(1)

    specs_dir = project_dir / ".auto-claude" / "specs"
    if not specs_dir.exists():
        log("info", f"Creating specs directory: {specs_dir}")
        specs_dir.mkdir(parents=True, exist_ok=True)

    # Write PID file if requested
    if args.pid_file:
        try:
            args.pid_file.write_text(str(os.getpid()))
            log("info", f"PID file written: {args.pid_file}", pid=os.getpid())
        except Exception as e:
            log("warning", f"Failed to write PID file: {e}")

    # Import daemon (after path setup)
    try:
        from services.task_daemon import TaskDaemon
    except ImportError as e:
        log("error", f"Failed to import TaskDaemon: {e}")
        log("error", "Make sure watchdog is installed: pip install watchdog")
        sys.exit(1)

    # Create daemon instance
    daemon = TaskDaemon(
        project_dir=project_dir,
        stuck_timeout=args.stuck_timeout,
        check_interval=args.check_interval,
        max_recovery=args.max_recovery,
        max_concurrent_tasks=args.max_concurrent,
        use_worktrees=args.use_worktrees,
        headless_mode=args.headless,
        use_claude_cli=args.use_claude_cli,
        claude_cli_path=args.claude_cli_path,
        log_file=args.log_file,
        on_task_start=lambda spec_id: log("event", f"Task started: {spec_id}"),
        on_task_complete=lambda spec_id, success: log(
            "event",
            f"Task completed: {spec_id}",
            success=success,
        ),
        on_task_stuck=lambda spec_id: log("event", f"Task stuck (max recovery): {spec_id}"),
        on_task_recovered=lambda spec_id, attempt: log(
            "event",
            f"Task recovered: {spec_id}",
            attempt=attempt,
        ),
        on_all_tasks_complete=lambda: log("event", "All tasks completed!"),
    )

    # Setup signal handlers for graceful shutdown (BUG 26)
    # Only set stop event; don't call daemon.stop() or sys.exit() here
    # because joining threads from a signal handler can deadlock.
    # The main loop detects _stop_event and calls stop() cleanly.
    def signal_handler(signum, frame):
        signal_name = signal.Signals(signum).name
        log("info", f"Received {signal_name}, shutting down...")
        daemon._stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Windows doesn't have SIGHUP
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, signal_handler)

    # WebSocket server for real-time UI communication (optional, graceful fallback)
    # MUST be initialized BEFORE status_thread starts (it references ws_server)
    ws_server = None
    try:
        from services.task_daemon.ws_server import DaemonWSServer

        ws_server = DaemonWSServer(port=18800)
        if ws_server.start():
            log("info", f"WebSocket server started on ws://127.0.0.1:{ws_server.actual_port}")
        else:
            log("warning", "WebSocket server failed to start (file polling will be used)")
            ws_server = None
    except ImportError:
        log("info", "websockets not installed, using file polling only")
    except Exception as e:
        log("warning", f"WebSocket server init failed: {e}")

    # Status file writer (if requested)
    # Uses event-driven writes: wakes immediately on state change, or every 30s as heartbeat.
    # Previous design wrote every 10s regardless; this reduces latency from ~10s to sub-second.
    if args.status_file:
        import threading

        def write_status_loop():
            while not daemon._stop_event.is_set():
                temp_path = args.status_file.with_suffix(".tmp")
                try:
                    status = daemon.get_status()
                    status["timestamp"] = datetime.now().isoformat()

                    # Include WS port in status file for UI auto-discovery
                    if ws_server and ws_server.is_running:
                        status["ws_port"] = ws_server.actual_port

                    with open(temp_path, "w", encoding="utf-8") as f:
                        json.dump(status, f, indent=2, ensure_ascii=False)
                    # Retry replace on Windows file lock or transient errors
                    for attempt in range(3):
                        try:
                            temp_path.replace(args.status_file)
                            break
                        except (PermissionError, OSError):
                            if attempt < 2:
                                import time
                                time.sleep(0.1)

                    # Also broadcast via WebSocket if available
                    if ws_server and ws_server.is_running:
                        ws_server.broadcast_status(status)

                except Exception as e:
                    log("warning", f"Failed to write status file: {e}")
                    try:
                        if temp_path.exists():
                            temp_path.unlink()
                    except Exception:
                        pass

                # Wait for either: status change (immediate) or heartbeat timeout (30s)
                daemon._status_dirty.wait(timeout=30)
                daemon._status_dirty.clear()

        status_thread = threading.Thread(
            target=write_status_loop,
            name="StatusWriter",
            daemon=True,
        )
        status_thread.start()
        log("info", f"Status file writer started (event-driven): {args.status_file}")

    # Print startup banner
    print("=" * 70)
    print("  Auto-Claude Task Daemon (24/7 Large Project Support)")
    print("=" * 70)
    print(f"  Project:        {project_dir}")
    print(f"  Specs:          {specs_dir}")
    print(f"  Max Concurrent: {args.max_concurrent} tasks")
    print(f"  Stuck Timeout:  {args.stuck_timeout}s ({args.stuck_timeout // 60} min)")
    print(f"  Check Interval: {args.check_interval}s")
    print(f"  Max Recovery:   {args.max_recovery} attempts")
    print(f"  PID:            {os.getpid()}")
    print("-" * 70)
    print("  Claude CLI Integration:")
    print(f"    Headless Mode:   {'Enabled' if args.headless else 'Disabled'}")
    print(f"    Git Worktrees:   {'Enabled' if args.use_worktrees else 'Disabled'}")
    print(f"    Claude CLI:      {'Enabled' if args.use_claude_cli else 'Using run.py'}")
    if args.claude_cli_path:
        print(f"    CLI Path:        {args.claude_cli_path}")
    if args.log_file:
        print(f"    Log File:        {args.log_file}")
    if args.status_file:
        print(f"    Status File:     {args.status_file}")
    if ws_server and ws_server.is_running:
        print(f"    WebSocket:       ws://127.0.0.1:{ws_server.actual_port}")
    print("=" * 70)
    print()
    print("Features:")
    print("  - Parallel execution with priority queue")
    print("  - Task dependencies and hierarchical tasks")
    print("  - Git worktree isolation (--use-worktrees)")
    print("  - Claude CLI plan mode for design tasks")
    print("  - Headless mode for 24/7 unattended operation")
    print("  - Auto-recovery for stuck tasks")
    print()
    print("Press Ctrl+C to stop")
    print()

    # Start daemon (blocking - exits when _stop_event is set)
    try:
        daemon.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log("error", f"Daemon error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Ensure clean shutdown (signal handler only sets _stop_event)
        daemon.stop()

        # Stop WebSocket server
        if ws_server:
            try:
                ws_server.stop()
            except Exception:
                pass

        # Cleanup PID file
        if args.pid_file and args.pid_file.exists():
            try:
                args.pid_file.unlink()
            except Exception:
                pass

    log("info", "Daemon exited")


if __name__ == "__main__":
    main()
