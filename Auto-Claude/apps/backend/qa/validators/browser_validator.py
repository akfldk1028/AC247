"""
Browser Validator
==================

Validates UI/UX using Python Playwright (visible Chromium by default).
Triggered for web frontends, Flutter web, Expo web, and Tauri apps.

Autonomously starts dev server, launches Chromium (visible so the user
can watch), navigates, clicks buttons/links, takes screenshots after
each interaction, captures a11y tree and console errors.

Uses Python `playwright` package directly (NOT the MCP server).
MCP is for agent sessions; this validator is pure Python, self-contained
(n8n node pattern).

Visibility:
    Default: headed (visible) — user can watch the AI testing in real-time.
    Set AUTO_CLAUDE_HEADLESS_BROWSER=true for CI/unattended mode.

Node pattern:
    Input:  project_dir, spec_dir, capabilities
    Output: ValidatorResult with screenshots, interactions, a11y tree, console errors
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

from . import BaseValidator, ValidatorResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Config: headless vs visible mode
# ---------------------------------------------------------------------------

def _is_headless() -> bool:
    """Check if browser should run in headless mode.

    Default: visible (headed) so the user can watch AI testing.
    Set AUTO_CLAUDE_HEADLESS_BROWSER=true for CI/unattended mode.
    """
    return os.environ.get("AUTO_CLAUDE_HEADLESS_BROWSER", "").lower() in ("true", "1", "yes")

# ---------------------------------------------------------------------------
# Helper: parse dev server config from project_index.json
# ---------------------------------------------------------------------------

def _get_dev_server_config(project_dir: Path) -> dict | None:
    """Parse dev server config from project_index.json.

    Returns dict with keys: command, port, framework, setup_cmd, cwd
    or None if no dev server detected.
    """
    index_file = project_dir / ".auto-claude" / "project_index.json"
    if not index_file.exists():
        return None

    try:
        data = json.loads(index_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to read project_index.json: {e}")
        return None

    services = data.get("services", {})
    # Handle both dict and list formats (same as project_context.py:284-290)
    if isinstance(services, dict):
        service_items = list(services.items())
    elif isinstance(services, list):
        service_items = [(s.get("name", f"service_{i}"), s) for i, s in enumerate(services)]
    else:
        return None

    for name, service in service_items:
        if not isinstance(service, dict):
            continue

        dev_command = service.get("dev_command") or service.get("web_dev_command", "")
        if not dev_command:
            continue

        framework = service.get("framework", "unknown")
        port = service.get("default_port")

        # Extract port from command if not explicit
        if not port and dev_command:
            port_match = re.search(r"--(?:web-)?port[=\s]+(\d+)", dev_command)
            if port_match:
                port = int(port_match.group(1))
            else:
                port_match = re.search(r":(\d{4,5})", dev_command)
                if port_match:
                    port = int(port_match.group(1))

        if not port:
            # Framework defaults
            framework_ports = {
                "flutter": 8080,
                "next": 3000,
                "nuxt": 3000,
                "vite": 5173,
                "react": 3000,
                "angular": 4200,
                "vue": 8080,
                "expo": 8081,
                "svelte": 5173,
            }
            for fw_key, fw_port in framework_ports.items():
                if fw_key in framework.lower():
                    port = fw_port
                    break

        if not port:
            continue

        return {
            "command": dev_command,
            "port": int(port),
            "framework": framework,
            "setup_cmd": service.get("web_setup_command", ""),
            "cwd": str(project_dir),
            "name": name,
        }

    return None


# ---------------------------------------------------------------------------
# Helper: port conflict resolution
# ---------------------------------------------------------------------------

def _find_free_port(start: int = 18100, end: int = 18200) -> int:
    """Find an available TCP port in the given range."""
    for port in range(start, end):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", port))
            return port
        except OSError:
            continue
        finally:
            sock.close()
    # Fallback: let OS pick
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _is_port_in_use(port: int) -> bool:
    """Check if a port is currently bound (LISTENING)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect(("127.0.0.1", port))
        return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False
    finally:
        sock.close()


async def _kill_port_occupant(port: int) -> bool:
    """Kill any process listening on the given port. Returns True if freed."""
    if not _is_port_in_use(port):
        return True

    logger.info(f"Port {port} is occupied, attempting to free it")
    print(f"[browser] Port {port} occupied, killing occupant...")

    try:
        if sys.platform == "win32":
            # Use netstat to find PID, then taskkill
            proc = await asyncio.create_subprocess_shell(
                f'powershell -NoProfile -Command "netstat -ano | Select-String \':{port} \' | Select-String \'LISTENING\'"',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            output = stdout.decode("utf-8", errors="replace") if stdout else ""
            # Parse PID from netstat output (last column)
            for line in output.strip().split("\n"):
                parts = line.strip().split()
                if parts:
                    try:
                        pid = int(parts[-1])
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(pid)],
                            capture_output=True, timeout=10,
                        )
                        logger.info(f"Killed PID {pid} on port {port}")
                    except (ValueError, subprocess.TimeoutExpired):
                        continue
        else:
            # Unix: lsof to find PID
            proc = await asyncio.create_subprocess_shell(
                f"lsof -ti:{port}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            output = stdout.decode("utf-8", errors="replace") if stdout else ""
            for pid_str in output.strip().split("\n"):
                try:
                    pid = int(pid_str.strip())
                    os.kill(pid, 9)
                    logger.info(f"Killed PID {pid} on port {port}")
                except (ValueError, ProcessLookupError):
                    continue

        # Wait briefly for port to be released
        await asyncio.sleep(1)
        return not _is_port_in_use(port)

    except Exception as e:
        logger.warning(f"Failed to kill port {port} occupant: {e}")
        return False


# ---------------------------------------------------------------------------
# Helper: TCP port polling
# ---------------------------------------------------------------------------

async def _wait_for_port(port: int, host: str = "127.0.0.1", timeout: int = 120) -> bool:
    """Poll TCP port until it accepts connections. Returns True if ready."""
    loop = asyncio.get_event_loop()
    elapsed = 0
    interval = 2

    while elapsed < timeout:
        try:
            # Non-blocking socket check
            connected = await loop.run_in_executor(
                None, _try_connect, host, port
            )
            if connected:
                return True
        except Exception:
            pass
        await asyncio.sleep(interval)
        elapsed += interval

    return False


def _try_connect(host: str, port: int) -> bool:
    """Attempt a TCP connection. Returns True on success."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect((host, port))
        return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False
    finally:
        sock.close()


# ---------------------------------------------------------------------------
# Helper: start dev server as background process
# ---------------------------------------------------------------------------

async def _start_dev_server(
    command: str, cwd: str, port: int
) -> asyncio.subprocess.Process:
    """Start dev server as a background subprocess."""
    kwargs: dict[str, Any] = {
        "cwd": cwd,
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.STDOUT,
    }

    if sys.platform == "win32":
        # CREATE_NEW_PROCESS_GROUP for clean tree kill later
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    logger.info(f"Starting dev server: {command} (port {port}, cwd={cwd})")

    proc = await asyncio.create_subprocess_shell(command, **kwargs)
    return proc


# ---------------------------------------------------------------------------
# Helper: kill process tree
# ---------------------------------------------------------------------------

async def _kill_process_tree(proc: asyncio.subprocess.Process) -> None:
    """Kill a process and its entire process tree."""
    if proc is None or proc.returncode is not None:
        return  # Already exited

    pid = proc.pid
    logger.info(f"Killing dev server process tree (PID={pid})")

    try:
        if sys.platform == "win32":
            # taskkill /F /T kills entire tree on Windows
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                timeout=15,
            )
        else:
            # Unix: kill process group (SIGTERM → SIGKILL)
            try:
                pgid = os.getpgid(pid)
                os.killpg(pgid, 15)  # SIGTERM
            except (ProcessLookupError, PermissionError):
                proc.terminate()

            try:
                await asyncio.wait_for(proc.wait(), timeout=10)
            except asyncio.TimeoutError:
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, 9)  # SIGKILL
                except (ProcessLookupError, PermissionError):
                    proc.kill()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    pass
    except Exception as e:
        logger.debug(f"Error killing dev server: {e}")

    # Close stdout pipe
    try:
        if proc.stdout:
            proc.stdout.feed_eof()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helper: run setup command
# ---------------------------------------------------------------------------

async def _run_setup_command(cmd: str, cwd: str) -> tuple[bool, str]:
    """Run a setup command (e.g., flutter create --platforms web .).

    Returns (success, output).
    """
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode("utf-8", errors="replace") if stdout else ""
        return proc.returncode == 0, output
    except asyncio.TimeoutError:
        return False, f"Setup command timed out after 120s: {cmd}"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Helper: drain subprocess stdout (limited)
# ---------------------------------------------------------------------------

async def _drain_server_output(
    proc: asyncio.subprocess.Process, max_bytes: int = 4096
) -> str:
    """Read available output from server process (non-blocking, limited)."""
    if proc.stdout is None:
        return ""
    chunks: list[bytes] = []
    total = 0
    try:
        while total < max_bytes:
            try:
                chunk = await asyncio.wait_for(proc.stdout.read(1024), timeout=0.5)
            except asyncio.TimeoutError:
                break
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
    except Exception:
        pass
    return b"".join(chunks).decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Helper: wait for server ready (stdout-based)
# ---------------------------------------------------------------------------

# Framework-specific ready messages in dev server stdout.
# When one of these patterns is found (case-insensitive), the server is fully
# compiled and ready to serve the app — not just the HTTP port open.
_READY_PATTERNS: dict[str, list[str]] = {
    "flutter": ["is being served at", "running at http"],
    "next": ["ready started server", "ready on http", "compiled client and server"],
    "nuxt": ["listening on", "ready in", "nitro built in"],
    "vite": ["local:   http", "ready in", "dev server running"],
    "react": ["compiled successfully", "you can now view"],
    "angular": ["compiled successfully", "angular live development server"],
    "vue": ["local:   http", "app running at"],
    "expo": ["starting project at", "web is waiting on"],
    "svelte": ["local:   http", "ready in"],
}


async def _wait_for_server_ready(
    proc: asyncio.subprocess.Process,
    framework: str,
    port: int,
    timeout: int = 120,
) -> tuple[bool, list[str]]:
    """Wait for dev server to finish compilation and be fully ready.

    Reads stdout looking for framework-specific "ready" messages.
    Falls back to TCP port polling for unknown frameworks.

    Returns (ready, output_lines) where output_lines contains server output
    captured during the wait.
    """
    # Find patterns for this framework
    patterns: list[str] = []
    for key, pats in _READY_PATTERNS.items():
        if key in framework.lower():
            patterns = pats
            break

    if not patterns:
        # Unknown framework: fall back to port polling
        ready = await _wait_for_port(port, timeout=timeout)
        return ready, []

    output_lines: list[str] = []
    elapsed = 0
    last_heartbeat = 0

    while elapsed < timeout:
        if proc.stdout is None:
            break

        try:
            line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=5)
        except asyncio.TimeoutError:
            elapsed += 5
            # Emit periodic heartbeat so daemon knows we're alive
            if elapsed - last_heartbeat >= 30:
                print(f"[browser] Server compiling... ({elapsed}s/{timeout}s)")
                last_heartbeat = elapsed
            continue

        if not line_bytes:
            # Process ended
            break

        text = line_bytes.decode("utf-8", errors="replace").strip()
        if text:
            output_lines.append(text)

        text_lower = text.lower()
        for pattern in patterns:
            if pattern in text_lower:
                return True, output_lines

    return False, output_lines


# ---------------------------------------------------------------------------
# Helper: auto-inject marionette_flutter for Marionette MCP support
# ---------------------------------------------------------------------------

async def _inject_marionette_flutter(
    project_dir: Path, report_lines: list[str]
) -> bool:
    """Auto-inject marionette_flutter package and MarionetteBinding into a Flutter app.

    This enables the QA agent to use Marionette MCP tools (tap, enter_text,
    scroll_to, etc.) for widget-level interaction during QA validation.

    Only modifies files in the worktree — never touches the main project.
    Requires: dart pub global activate marionette_mcp (one-time install)

    Returns True if injection succeeded (or was already done).
    """
    pubspec = project_dir / "pubspec.yaml"
    if not pubspec.exists():
        return False

    try:
        pubspec_content = pubspec.read_text(encoding="utf-8")
    except OSError:
        return False

    # Step 1: Add marionette_flutter dependency if not already present
    if "marionette_flutter" not in pubspec_content:
        try:
            proc = await asyncio.create_subprocess_shell(
                "flutter pub add marionette_flutter",
                cwd=str(project_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
            output = stdout.decode("utf-8", errors="replace") if stdout else ""

            if proc.returncode != 0:
                report_lines.append(f"- Marionette: flutter pub add failed ({output[:150]})\n")
                return False
        except (asyncio.TimeoutError, Exception) as e:
            report_lines.append(f"- Marionette: dep install error ({str(e)[:100]})\n")
            return False

    # Step 2: Patch main.dart with MarionetteBinding (idempotent)
    main_dart = project_dir / "lib" / "main.dart"
    if not main_dart.exists():
        return False

    try:
        main_content = main_dart.read_text(encoding="utf-8")
    except OSError:
        return False

    if "MarionetteBinding" in main_content:
        return True  # Already patched

    # Add import
    import_line = "import 'package:marionette_flutter/marionette_flutter.dart';\n"
    foundation_import = "import 'package:flutter/foundation.dart';\n"

    new_content = main_content

    # Add imports at top (after existing flutter imports)
    if "marionette_flutter" not in new_content:
        # Find a good insertion point — after the last import
        lines = new_content.split("\n")
        last_import_idx = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("import "):
                last_import_idx = i

        if last_import_idx >= 0:
            # Add our imports after the last existing import
            insert_lines = []
            if "package:flutter/foundation.dart" not in new_content:
                insert_lines.append(foundation_import.rstrip())
            insert_lines.append(import_line.rstrip())
            lines = lines[:last_import_idx + 1] + insert_lines + lines[last_import_idx + 1:]
            new_content = "\n".join(lines)

    # Replace WidgetsFlutterBinding with MarionetteBinding (debug mode only)
    # Pattern: WidgetsFlutterBinding.ensureInitialized();
    if "WidgetsFlutterBinding.ensureInitialized()" in new_content:
        new_content = new_content.replace(
            "WidgetsFlutterBinding.ensureInitialized();",
            "if (kDebugMode) {\n"
            "    MarionetteBinding.ensureInitialized();\n"
            "  } else {\n"
            "    WidgetsFlutterBinding.ensureInitialized();\n"
            "  }",
        )
    elif "runApp(" in new_content and "ensureInitialized" not in new_content:
        # No explicit binding — add MarionetteBinding before runApp
        new_content = new_content.replace(
            "runApp(",
            "if (kDebugMode) {\n"
            "    MarionetteBinding.ensureInitialized();\n"
            "  } else {\n"
            "    WidgetsFlutterBinding.ensureInitialized();\n"
            "  }\n"
            "  runApp(",
        )

    try:
        main_dart.write_text(new_content, encoding="utf-8")
    except OSError as e:
        report_lines.append(f"- Marionette: main.dart patch failed ({e})\n")
        return False

    return True


# ===========================================================================
# BrowserValidator
# ===========================================================================

class BrowserValidator(BaseValidator):
    """Playwright-based UI verification.

    Autonomously starts dev server, launches headless Chromium, navigates,
    takes screenshots, captures a11y tree and console errors.
    Uses accessibility snapshots (not CSS selectors) for robust element
    identification across all renderers including Flutter CanvasKit.
    """

    id = "browser"
    description = "Browser-based UI verification via Playwright"
    capability_trigger = ""  # Checked via is_applicable override
    validation_doc = "mcp_tools/playwright_browser.md"

    def is_applicable(self, capabilities: dict) -> bool:
        """Run for web frontends, Flutter web, Expo web, or Tauri."""
        needs_browser = (
            capabilities.get("is_web_frontend")
            or capabilities.get("is_flutter")
            or capabilities.get("is_expo")
            or capabilities.get("is_tauri")
        )
        return bool(needs_browser and not capabilities.get("is_electron"))

    async def validate(self, ctx: dict) -> ValidatorResult:
        """Run real browser validation.

        Steps:
        1.  Parse project_index.json → dev server config
        2.  Lazy import playwright (graceful skip if not installed)
        3.  Run setup command if needed
        4.  Start dev server (background subprocess)
        5.  Poll port (120s timeout)
        6.  Launch headless Chromium
        7.  Register console event listener
        8.  Navigate to localhost:PORT
        9.  Wait settling time
        10. Take screenshot
        11. Get accessibility snapshot
        12. Analyze console errors
        13. Return ValidatorResult with evidence
        """
        project_dir: Path = ctx["project_dir"]
        spec_dir: Path = ctx["spec_dir"]

        report_lines = ["## Browser Validation\n"]
        screenshots: list[str] = []
        issues: list[dict] = []

        # Step 1: Parse dev server config
        print("[browser] Parsing dev server config...")
        config = _get_dev_server_config(project_dir)
        if not config:
            report_lines.append("- No dev server config found, skipping browser validation\n")
            return ValidatorResult(
                validator_id=self.id,
                passed=True,
                report_section="\n".join(report_lines),
                metadata={"skipped": True, "reason": "no dev server config"},
            )

        # Step 2: Lazy import playwright
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            report_lines.append(
                "- playwright not installed, skipping browser validation\n"
                "  (install with: pip install playwright && playwright install chromium)\n"
            )
            return ValidatorResult(
                validator_id=self.id,
                passed=True,
                report_section="\n".join(report_lines),
                metadata={"skipped": True, "reason": "playwright not installed"},
            )

        command = config["command"]
        port = config["port"]
        cwd = config["cwd"]
        setup_cmd = config.get("setup_cmd", "")
        framework = config.get("framework", "unknown")

        # Flutter: replace '-d chrome' with '-d web-server' so Flutter
        # starts a headless HTTP server instead of opening its own Chrome.
        # Playwright will handle the browser window.
        # Note: '--web-renderer html' no longer exists in Flutter (only canvaskit/skwasm).
        # Instead, we enable semantics via JS after page load to get testable DOM elements.
        is_flutter = "flutter" in framework.lower()
        if is_flutter and "-d chrome" in command:
            command = command.replace("-d chrome", "-d web-server")
            report_lines.append("- Replaced '-d chrome' with '-d web-server' for Playwright control\n")

        # Flutter: auto-inject marionette_flutter for Marionette MCP support.
        # This enables the QA agent to interact with Flutter widgets directly
        # via the Marionette MCP server (tap, scroll, enter_text, etc.)
        # Only injects in worktree — main project code is never touched.
        vm_service_uri: str | None = None
        if is_flutter:
            print("[browser] Injecting marionette_flutter...")
            marionette_ready = await _inject_marionette_flutter(project_dir, report_lines)
            if marionette_ready:
                print("[browser] Marionette injection OK")
                report_lines.append("- Marionette: injected (QA agent can use Marionette MCP tools)\n")
            else:
                print("[browser] Marionette injection skipped/failed")

        # Resolve port conflicts: kill zombie processes or pick a new port
        if _is_port_in_use(port):
            freed = await _kill_port_occupant(port)
            if freed:
                report_lines.append(f"- Port {port}: freed (killed zombie process)\n")
            else:
                # Port couldn't be freed — use a dynamic port
                old_port = port
                port = _find_free_port()
                # Update command with new port
                if f"--web-port={old_port}" in command:
                    command = command.replace(f"--web-port={old_port}", f"--web-port={port}")
                elif f"--port={old_port}" in command:
                    command = command.replace(f"--port={old_port}", f"--port={port}")
                elif f":{old_port}" in command:
                    command = command.replace(f":{old_port}", f":{port}")
                else:
                    # Append port flag
                    command = f"{command} --web-port={port}" if is_flutter else f"{command} --port={port}"
                report_lines.append(f"- Port {old_port} occupied, switched to {port}\n")
                print(f"[browser] Port {old_port} occupied, using {port} instead")

        url = f"http://localhost:{port}"

        report_lines.append(f"- Framework: {framework}\n")
        report_lines.append(f"- Dev command: `{command}`\n")
        report_lines.append(f"- Port: {port}\n")

        dev_server_proc: asyncio.subprocess.Process | None = None
        pw_instance = None
        browser = None

        try:
            # Step 3: Run setup command if needed
            if setup_cmd:
                report_lines.append(f"- Running setup: `{setup_cmd}`\n")
                success, output = await _run_setup_command(setup_cmd, cwd)
                if not success:
                    report_lines.append(f"- Setup command failed (non-blocking): {output[:200]}\n")
                    issues.append({
                        "severity": "minor",
                        "description": f"Setup command failed: {output[:200]}",
                        "file": "",
                        "line": 0,
                    })
                else:
                    report_lines.append("- Setup: OK\n")

            # Step 4: Start dev server
            print(f"[browser] Starting dev server: {command[:60]}...")
            dev_server_proc = await _start_dev_server(command, cwd, port)
            report_lines.append(f"- Dev server started (PID={dev_server_proc.pid})\n")

            # Step 5: Wait for server to be fully ready (compilation done)
            print(f"[browser] Waiting for server ready (port {port}, timeout=120s)...")
            report_lines.append(f"- Waiting for server to compile and start (port {port})...\n")
            server_ready, server_lines = await _wait_for_server_ready(
                dev_server_proc, framework, port, timeout=120
            )

            if not server_ready:
                print("[browser] Server TIMEOUT — not ready after 120s")
                server_output = "\n".join(server_lines[-20:]) if server_lines else ""
                if not server_output:
                    server_output = await _drain_server_output(dev_server_proc)
                report_lines.append(f"- **TIMEOUT**: Server not ready after 120s\n")
                if server_output:
                    report_lines.append(f"- Server output:\n```\n{server_output[:1000]}\n```\n")
                issues.append({
                    "severity": "major",
                    "description": f"Dev server did not start within 120s on port {port}",
                    "file": "",
                    "line": 0,
                })
                return ValidatorResult(
                    validator_id=self.id,
                    passed=True,  # Non-blocking — server issues shouldn't hard-fail QA
                    issues=issues,
                    screenshots=screenshots,
                    report_section="\n".join(report_lines),
                    metadata={"server_timeout": True, "server_output": server_output[:500] if server_output else ""},
                )

            print("[browser] Server ready (compilation complete)")
            report_lines.append(f"- Server ready (compilation complete)\n")

            # Extract VM service URI from server output (for Marionette MCP connection)
            if is_flutter and server_lines:
                for line in server_lines:
                    vm_match = re.search(r"(ws://\S+)", line)
                    if vm_match:
                        vm_service_uri = vm_match.group(1)
                        report_lines.append(f"- VM service URI: `{vm_service_uri}`\n")
                        break

            # Step 6: Launch Chromium (visible by default so user can watch)
            headless = _is_headless()
            launch_opts: dict[str, Any] = {"headless": headless}
            if not headless:
                launch_opts["slow_mo"] = 500  # 500ms between actions — user can follow along

            print(f"[browser] Launching Chromium ({'headless' if headless else 'visible'})...")
            pw_instance = await async_playwright().start()
            browser = await pw_instance.chromium.launch(**launch_opts)
            page = await browser.new_page(viewport={"width": 1280, "height": 720})
            report_lines.append(f"- Browser mode: {'headless' if headless else 'visible (user can watch)'}\n")

            # Step 7: Register console event listener BEFORE navigation
            console_messages: list[dict] = []

            def on_console(msg):
                console_messages.append({
                    "type": msg.type,
                    "text": msg.text,
                })

            page.on("console", on_console)

            # Step 8: Navigate — domcontentloaded first (fast), then wait for full load
            print(f"[browser] Navigating to {url}...")
            report_lines.append(f"- Navigating to {url}\n")
            nav_success = False
            nav_error = ""

            try:
                # Use domcontentloaded (fires quickly, even for slow frameworks)
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                nav_success = True
                report_lines.append("- Navigation: domcontentloaded OK\n")
            except Exception as e1:
                nav_error = str(e1)[:300]
                logger.error(f"Navigation failed: {e1}")

            if not nav_success:
                report_lines.append(f"- **NAVIGATION FAILED**: {nav_error}\n")
                issues.append({
                    "severity": "critical",
                    "description": f"Browser navigation failed: {nav_error}",
                    "file": "",
                    "line": 0,
                })
                return ValidatorResult(
                    validator_id=self.id,
                    passed=False,
                    issues=issues,
                    screenshots=screenshots,
                    report_section="\n".join(report_lines),
                    metadata={"navigation_failed": True, "error": nav_error},
                )

            # Step 9: Wait for app to actually render (framework-agnostic)
            # Flutter CanvasKit: downloads WASM, compiles, renders to canvas (can take 30-60s first time)
            # React/Vue/Angular: hydrates, renders root component
            # Strategy: wait for networkidle (up to 60s), then check for content selectors
            print("[browser] Waiting for app render (networkidle + content selectors)...")
            report_lines.append("- Waiting for app to fully load...\n")
            try:
                await page.wait_for_load_state("networkidle", timeout=60000)
                report_lines.append("- Network idle reached\n")
            except Exception:
                report_lines.append("- Network idle timeout (60s) -- app may use persistent connections\n")

            # Now wait for visible content to appear
            CONTENT_SELECTORS = "canvas, #root, #app, #__next, flt-glass-pane, main, [data-testid]"
            try:
                await page.wait_for_selector(CONTENT_SELECTORS, timeout=15000)
                report_lines.append("- Content element detected\n")
            except Exception:
                report_lines.append("- No standard content selectors found\n")

            # Final settling time for rendering to complete
            await asyncio.sleep(3)

            # Flutter CanvasKit: enable semantics so Playwright can find elements.
            # CanvasKit renders everything to <canvas> — no DOM elements by default.
            # We must activate the semantics tree by clicking the hidden placeholder
            # AND the "Enable accessibility" button, then wait for full tree population.
            # Reference: https://habr.com/en/articles/809137/
            #            https://docs.flutter.dev/ui/accessibility/web-accessibility
            if is_flutter:
                try:
                    # Flutter CanvasKit: enable accessibility/semantics tree.
                    # Flutter shows an "Enable accessibility" overlay when Tab is pressed.
                    # Pressing Tab then Enter activates it, populating the semantics tree.
                    # Ref: https://docs.flutter.dev/ui/accessibility/web-accessibility
                    await page.keyboard.press("Tab")
                    await asyncio.sleep(0.5)
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(2)
                    report_lines.append("- Flutter semantics: activated via Tab+Enter\n")

                    # Re-check ARIA snapshot after semantics enabled
                    try:
                        post_aria = await page.locator("body").aria_snapshot()
                        lines_count = len(post_aria.strip().split("\n")) if post_aria else 0
                        report_lines.append(f"- Post-semantics ARIA: {lines_count} lines\n")
                        if lines_count > 3:
                            report_lines.append(f"```\n{post_aria[:600]}\n```\n")
                    except Exception:
                        pass

                except Exception as e:
                    report_lines.append(f"- Flutter semantics enablement failed: {str(e)[:100]}\n")

            # Step 10: Take screenshot
            print("[browser] Taking screenshots and a11y snapshot...")
            screenshots_dir = spec_dir / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = screenshots_dir / "01-initial-load.png"

            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
                screenshots.append(str(screenshot_path))
                report_lines.append(f"- Screenshot saved: `{screenshot_path.name}`\n")
            except Exception as e:
                logger.warning(f"Screenshot failed: {e}")
                report_lines.append(f"- Screenshot failed: {str(e)[:100]}\n")

            # Step 11: ARIA snapshot (accessibility tree)
            # Note: page.accessibility.snapshot() is deprecated in Playwright >=1.50.
            # Use locator.aria_snapshot() which returns a YAML string.
            a11y_tree: dict | None = None
            aria_yaml: str = ""
            try:
                aria_yaml = await page.locator("body").aria_snapshot()
                if aria_yaml and len(aria_yaml.strip()) > 10:
                    report_lines.append(f"- ARIA snapshot ({len(aria_yaml)} chars):\n```\n{aria_yaml[:800]}\n```\n")
                else:
                    report_lines.append(
                        "- ARIA snapshot: minimal/empty (expected for CanvasKit/canvas renderers)\n"
                    )
            except Exception:
                # Fallback to deprecated API for older Playwright versions
                try:
                    a11y_tree = await page.accessibility.snapshot()  # type: ignore[attr-defined]
                    if a11y_tree:
                        a11y_summary = _summarize_a11y_tree(a11y_tree)
                        report_lines.append(f"- Accessibility tree: {a11y_summary}\n")
                    else:
                        report_lines.append("- Accessibility tree: empty\n")
                except Exception as e2:
                    report_lines.append(f"- Accessibility info unavailable: {str(e2)[:100]}\n")

            # Step 11.5: Interactive UI exploration — click buttons, fill inputs
            print("[browser] Exploring UI (clicking buttons, testing interactions)...")
            interaction_count = await _explore_ui(
                page, a11y_tree, screenshots_dir, screenshots, report_lines, issues
            )
            report_lines.append(f"- UI interactions performed: {interaction_count}\n")

            # Step 12: Analyze console errors
            errors_found = [
                m for m in console_messages if m["type"] in ("error", "warning")
            ]
            if errors_found:
                report_lines.append(f"- Console issues: {len(errors_found)} error/warning messages\n")
                for i, msg in enumerate(errors_found[:10]):
                    report_lines.append(f"  - [{msg['type']}] {msg['text'][:200]}\n")
                    if msg["type"] == "error":
                        issues.append({
                            "severity": "minor",
                            "description": f"Console error: {msg['text'][:200]}",
                            "file": "",
                            "line": 0,
                        })
                if len(errors_found) > 10:
                    report_lines.append(f"  - ... and {len(errors_found) - 10} more\n")
            else:
                report_lines.append("- Console: clean (no errors/warnings)\n")

            # Step 13: Build result
            report_lines.append(f"\n**Browser validation complete.** "
                                f"Screenshots: {len(screenshots)}, "
                                f"Console errors: {len([m for m in errors_found if m['type'] == 'error'])}, "
                                f"Console warnings: {len([m for m in errors_found if m['type'] == 'warning'])}\n")

            # Brief pause so user can see final state (headed mode only)
            if not headless:
                report_lines.append("- Keeping browser open 3s for user review...\n")
                await asyncio.sleep(3)

            print(f"[browser] Complete: {len(screenshots)} screenshots, {len(issues)} issues")
            return ValidatorResult(
                validator_id=self.id,
                passed=True,
                issues=issues,
                screenshots=screenshots,
                report_section="\n".join(report_lines),
                metadata={
                    "url": url,
                    "framework": framework,
                    "headless": headless,
                    "interactions": interaction_count,
                    "a11y_node_count": _count_a11y_nodes(a11y_tree) if a11y_tree else 0,
                    "console_errors": len([m for m in errors_found if m["type"] == "error"]),
                    "console_warnings": len([m for m in errors_found if m["type"] == "warning"]),
                    **({"vm_service_uri": vm_service_uri} if vm_service_uri else {}),
                },
            )

        except Exception as e:
            logger.error(f"Browser validator unexpected error: {e}", exc_info=True)
            return ValidatorResult(
                validator_id=self.id,
                passed=True,  # Non-blocking — unexpected errors shouldn't block QA
                issues=[{
                    "severity": "minor",
                    "description": f"Browser validation error: {str(e)[:200]}",
                    "file": "",
                    "line": 0,
                }],
                screenshots=screenshots,
                report_section=f"## Browser Validation\n\n- ERROR: {str(e)[:300]}\n",
            )

        finally:
            # Always clean up: close browser, stop playwright, kill dev server
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if pw_instance:
                try:
                    await pw_instance.stop()
                except Exception:
                    pass
            if dev_server_proc:
                await _kill_process_tree(dev_server_proc)


# ---------------------------------------------------------------------------
# Interactive UI exploration
# ---------------------------------------------------------------------------

def _sanitize_filename(name: str, max_len: int = 30) -> str:
    """Sanitize a string for use in filenames."""
    safe = re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "-")
    return safe[:max_len] if safe else "unknown"


def _find_interactive_elements(
    tree: dict | None, max_items: int = 10
) -> list[dict]:
    """Extract interactive elements (buttons, links, inputs, textboxes) from a11y tree.

    Returns list of dicts: {role, name, depth} sorted by depth (shallow first).
    """
    if not tree:
        return []

    results: list[dict] = []

    INTERACTIVE_ROLES = {
        "button", "link", "menuitem", "tab", "checkbox",
        "radio", "switch", "textbox", "combobox", "spinbutton",
        "slider", "searchbox",
    }

    def _walk(node: dict, depth: int = 0) -> None:
        role = node.get("role", "")
        name = node.get("name", "")
        if role in INTERACTIVE_ROLES and name:
            results.append({"role": role, "name": name, "depth": depth})
        for child in node.get("children", []):
            _walk(child, depth + 1)

    _walk(tree)

    # Sort by depth (interact with top-level elements first), then limit
    results.sort(key=lambda x: x["depth"])
    return results[:max_items]


async def _find_flutter_semantics_elements(page, max_items: int = 10) -> list[dict]:
    """Find Flutter semantics elements in shadow DOM after semantics enabled.

    Flutter CanvasKit renders to canvas but creates flt-semantics elements
    in shadow DOM when semantics is enabled. These have aria-label, role attrs.
    Reference: https://habr.com/en/articles/809137/
    """
    results: list[dict] = []
    try:
        # Query flt-semantics elements in shadow DOM (including deeply nested)
        elements_data = await page.evaluate("""() => {
            const pane = document.querySelector('flt-glass-pane');
            if (!pane || !pane.shadowRoot) return [];
            const host = pane.shadowRoot.querySelector('flt-semantics-host');
            if (!host) return [];
            // Get ALL flt-semantics elements (they can be deeply nested)
            const elems = host.querySelectorAll('flt-semantics');
            return Array.from(elems).slice(0, 30).map(el => ({
                role: el.getAttribute('role') || '',
                name: el.getAttribute('aria-label') || '',
                tag: el.tagName,
                hasClick: el.style.pointerEvents !== 'none',
            })).filter(e => e.name && e.name !== 'Enable accessibility');
        }""")

        for item in elements_data:
            if item.get("name"):
                results.append({
                    "role": item["role"],
                    "name": item["name"],
                    "depth": 0,
                    "flutter_semantics": True,  # Flag for special handling
                })

    except Exception as e:
        logger.debug(f"Flutter semantics query failed: {e}")

    return results[:max_items]


async def _find_dom_interactive_elements(page, max_items: int = 10) -> list[dict]:
    """Fallback: find interactive elements via DOM when a11y tree is empty.

    Returns list of dicts: {role, name, depth} compatible with _find_interactive_elements output.
    """
    results: list[dict] = []

    # Query for common interactive elements via CSS selectors
    SELECTORS = [
        ("button", "button"),
        ("a[href]", "link"),
        ("input:not([type=hidden])", "textbox"),
        ("[role=button]", "button"),
        ("[role=link]", "link"),
        ("[role=tab]", "tab"),
        ("[role=checkbox]", "checkbox"),
        ("[role=switch]", "switch"),
        ("select", "combobox"),
        ("[onclick]", "button"),
    ]

    for selector, role in SELECTORS:
        try:
            locator = page.locator(selector)
            count = await locator.count()
            for i in range(min(count, 3)):  # Max 3 per selector type
                try:
                    elem = locator.nth(i)
                    # Get element text content for the name
                    name = await elem.text_content() or ""
                    name = name.strip()[:50]
                    if not name:
                        name = await elem.get_attribute("aria-label") or ""
                    if not name:
                        name = await elem.get_attribute("title") or ""
                    if not name:
                        name = await elem.get_attribute("value") or ""
                    if not name:
                        name = f"{role}-{i}"
                    # Check visibility
                    if await elem.is_visible() and "enable accessibility" not in name.lower():
                        results.append({"role": role, "name": name, "depth": 0})
                except Exception:
                    continue
        except Exception:
            continue

        if len(results) >= max_items:
            break

    return results[:max_items]


async def _explore_by_tab_navigation(
    page,
    screenshots_dir: Path,
    screenshots: list[str],
    report_lines: list[str],
    max_interactions: int = 15,
) -> int:
    """Explore UI by Tab-cycling through focusable elements and pressing Enter.

    Works for canvas-based renderers (Flutter CanvasKit, Unity, etc.) where
    DOM elements don't exist. Tab moves focus through the app's semantic tree,
    Enter activates the focused element.

    Also handles page navigation: if URL changes after an interaction,
    takes a screenshot of the new page and continues exploring.
    """
    interaction_count = 0
    ss_index = 2
    prev_url = page.url
    visited_urls: set[str] = {prev_url}

    # Take a reference screenshot to compare against
    try:
        ref_bytes = await page.screenshot()
    except Exception:
        ref_bytes = b""

    for i in range(max_interactions):
        try:
            # Tab to next focusable element
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.3)

            # Press Enter to activate
            await page.keyboard.press("Enter")
            await asyncio.sleep(0.8)

            # Check for navigation (page change)
            current_url = page.url
            if current_url != prev_url:
                report_lines.append(f"- [{ss_index:02d}] Page navigated: {current_url}\n")
                visited_urls.add(current_url)
                prev_url = current_url
                await asyncio.sleep(1)  # Extra settle time for new page

            # Take screenshot
            ss_path = screenshots_dir / f"{ss_index:02d}-tab-{i + 1}.png"
            await page.screenshot(path=str(ss_path), full_page=True)
            screenshots.append(str(ss_path))
            report_lines.append(f"- [{ss_index:02d}] Tab({i + 1}) + Enter -> screenshot\n")
            interaction_count += 1
            ss_index += 1

        except Exception as e:
            err_msg = str(e)[:80]
            if "Target closed" in err_msg:
                report_lines.append(f"- Tab({i + 1}): page closed, stopping\n")
                break
            report_lines.append(f"- Tab({i + 1}): {err_msg}\n")

    # If we visited multiple pages, go back and report
    if len(visited_urls) > 1:
        report_lines.append(f"- Pages visited: {len(visited_urls)}\n")
        try:
            await page.go_back()
            await asyncio.sleep(1)
        except Exception:
            pass

    return interaction_count


async def _explore_ui(
    page,
    a11y_tree: dict | None,
    screenshots_dir: Path,
    screenshots: list[str],
    report_lines: list[str],
    issues: list[dict],
) -> int:
    """Interact with UI elements: click buttons, fill inputs, screenshot each step.

    Returns the number of interactions performed.
    """
    report_lines.append("\n### Interactive UI Exploration\n")

    elements = _find_interactive_elements(a11y_tree)
    if not elements:
        # Fallback 1: find Flutter semantics elements in shadow DOM
        report_lines.append("- No a11y elements, trying Flutter semantics fallback...\n")
        elements = await _find_flutter_semantics_elements(page)

    if not elements:
        # Fallback 2: find interactive elements via DOM selectors
        report_lines.append("- Trying DOM selector fallback...\n")
        elements = await _find_dom_interactive_elements(page)

    if not elements:
        # Final fallback: Tab-based navigation for canvas renderers.
        # Tab cycles through focusable elements, Enter activates them.
        # Works for Flutter CanvasKit, Unity, and any app with keyboard support.
        report_lines.append("- No DOM elements found, using Tab+Enter exploration\n")
        return await _explore_by_tab_navigation(
            page, screenshots_dir, screenshots, report_lines
        )

    report_lines.append(f"- Found {len(elements)} interactive elements\n")
    interaction_count = 0
    ss_index = 2  # Screenshots start at 02 (01 = initial load)

    for elem in elements:
        role = elem["role"]
        name = elem["name"]
        safe_name = _sanitize_filename(name)

        try:
            # Flutter semantics: use JS to click (canvas intercepts normal clicks)
            if elem.get("flutter_semantics"):
                clicked = await page.evaluate(f"""() => {{
                    const pane = document.querySelector('flt-glass-pane');
                    if (!pane || !pane.shadowRoot) return false;
                    const host = pane.shadowRoot.querySelector('flt-semantics-host');
                    if (!host) return false;
                    const el = host.querySelector('flt-semantics[aria-label="{name}"]');
                    if (!el) return false;
                    el.dispatchEvent(new PointerEvent('pointerdown', {{bubbles: true}}));
                    el.dispatchEvent(new PointerEvent('pointerup', {{bubbles: true}}));
                    el.click();
                    return true;
                }}""")
                if not clicked:
                    continue
                action_desc = f"Clicked Flutter '{name}'"
            else:
                # Standard DOM: use Playwright's accessible locator (role + name)
                locator = page.get_by_role(role, name=name)

                # Check element exists and is visible
                count = await locator.count()
                if count == 0:
                    continue

                first = locator.first

                # Different interaction based on role
                if role in ("textbox", "searchbox", "combobox", "spinbutton"):
                    await first.click()
                    await first.fill("test123")
                    action_desc = f"Filled '{name}' with 'test123'"
                elif role == "checkbox" or role == "switch":
                    await first.click()
                    action_desc = f"Toggled {role} '{name}'"
                elif role == "slider":
                    await first.click()
                    action_desc = f"Clicked slider '{name}'"
                else:
                    await first.click()
                    action_desc = f"Clicked {role} '{name}'"

            # Wait for UI to settle after interaction
            await asyncio.sleep(0.8)

            # Screenshot after interaction
            ss_path = screenshots_dir / f"{ss_index:02d}-{role}-{safe_name}.png"
            try:
                await page.screenshot(path=str(ss_path), full_page=True)
                screenshots.append(str(ss_path))
            except Exception:
                pass

            report_lines.append(f"- [{ss_index:02d}] {action_desc} → screenshot saved\n")
            interaction_count += 1
            ss_index += 1

        except Exception as e:
            err_msg = str(e)[:120]
            # Don't spam the report with expected errors
            if "Target closed" in err_msg or "Navigation" in err_msg:
                report_lines.append(f"- {role} '{name}': navigation triggered, stopping exploration\n")
                # Page navigated away — take a screenshot of the new state
                try:
                    await asyncio.sleep(1)
                    ss_path = screenshots_dir / f"{ss_index:02d}-after-navigation.png"
                    await page.screenshot(path=str(ss_path), full_page=True)
                    screenshots.append(str(ss_path))
                    ss_index += 1
                except Exception:
                    pass
                break
            else:
                report_lines.append(f"- {role} '{name}': interaction failed ({err_msg})\n")

        # Cap interactions to avoid running too long
        if interaction_count >= 8:
            report_lines.append(f"- Reached interaction limit (8), stopping\n")
            break

    # If we had successful element-based interactions, also try Tab exploration
    # to cover elements we might have missed (e.g., scroll areas, hidden sections)
    if interaction_count > 0 and interaction_count < 5:
        report_lines.append("- Supplementing with Tab exploration for full coverage...\n")
        tab_count = await _explore_by_tab_navigation(
            page, screenshots_dir, screenshots, report_lines,
            max_interactions=5,
        )
        interaction_count += tab_count

    # Final screenshot after all interactions
    try:
        ss_path = screenshots_dir / f"{ss_index + interaction_count:02d}-final-state.png"
        await page.screenshot(path=str(ss_path), full_page=True)
        screenshots.append(str(ss_path))
        report_lines.append(f"- Final state screenshot\n")
    except Exception:
        pass

    return interaction_count


# ---------------------------------------------------------------------------
# A11y tree helpers
# ---------------------------------------------------------------------------

def _summarize_a11y_tree(tree: dict, max_depth: int = 3) -> str:
    """Produce a one-line summary of the a11y tree."""
    node_count = _count_a11y_nodes(tree)
    roles = _collect_roles(tree, max_depth=max_depth)
    role_summary = ", ".join(f"{r}({c})" for r, c in sorted(roles.items(), key=lambda x: -x[1])[:8])
    return f"{node_count} nodes — top roles: {role_summary}" if role_summary else f"{node_count} nodes"


def _count_a11y_nodes(tree: dict | None) -> int:
    """Count total nodes in the a11y tree."""
    if not tree:
        return 0
    count = 1
    for child in tree.get("children", []):
        count += _count_a11y_nodes(child)
    return count


def _collect_roles(tree: dict, depth: int = 0, max_depth: int = 3) -> dict[str, int]:
    """Collect role counts from the a11y tree."""
    if depth > max_depth:
        return {}
    roles: dict[str, int] = {}
    role = tree.get("role", "")
    if role:
        roles[role] = roles.get(role, 0) + 1
    for child in tree.get("children", []):
        for r, c in _collect_roles(child, depth + 1, max_depth).items():
            roles[r] = roles.get(r, 0) + c
    return roles
