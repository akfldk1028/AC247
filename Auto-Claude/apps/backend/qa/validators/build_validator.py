"""
Build Validator
================

Validates the build by running static analysis, compilation checks,
and test suites. This validator always runs first (before runtime validators).

Node pattern:
    Input:  project_dir, spec_dir, capabilities
    Output: ValidatorResult with compile/test results
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from . import BaseValidator, ValidatorResult

logger = logging.getLogger(__name__)


def _get_build_commands(project_dir: Path) -> dict | None:
    """Read lint/build/test commands from project_index.json.

    framework_analyzer.py stores detected commands in project_index.json
    under each service's entry. This function reads them back.

    Returns:
        Dict with optional keys: lint, build, test — or None if not found.
    """
    index_file = project_dir / ".auto-claude" / "project_index.json"
    if not index_file.exists():
        return None

    try:
        data = json.loads(index_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to read project_index.json: {e}")
        return None

    commands: dict[str, str] = {}
    # Handle both dict and list formats (same as browser_validator, project_context)
    services = data.get("services", {})
    if isinstance(services, dict):
        service_list = list(services.values())
    elif isinstance(services, list):
        service_list = services
    else:
        service_list = []

    for svc in service_list:
        if not isinstance(svc, dict):
            continue
        if svc.get("lint_command"):
            commands.setdefault("lint", svc["lint_command"])
        if svc.get("build_command"):
            commands.setdefault("build", svc["build_command"])
        if svc.get("test_command"):
            commands.setdefault("test", svc["test_command"])

    return commands or None


class BuildValidator(BaseValidator):
    """Static analysis, compilation, and test validation.

    Always runs — not gated by capability trigger. This is the
    foundational validator that must pass before runtime validators.
    """

    id = "build"
    description = "Static analysis, compilation, and test validation"
    capability_trigger = ""  # Always runs
    validation_doc = ""  # No separate doc — uses framework-specific build commands

    async def validate(self, ctx: dict) -> ValidatorResult:
        """Run build validation.

        Steps:
        1. Detect build system from project_index.json
        2. Run lint/analyze command if available
        3. Run build/compile command
        4. Run test command if available
        5. Collect results into ValidatorResult
        """
        project_dir: Path = ctx["project_dir"]
        spec_dir: Path = ctx["spec_dir"]
        capabilities: dict = ctx.get("capabilities", {})

        issues = []
        report_lines = ["## Build Validation\n"]

        try:
            # Get build commands from project_index.json
            # (framework_analyzer.py stores lint/build/test commands there)
            commands = _get_build_commands(project_dir)

            if not commands:
                report_lines.append("- No build system detected, skipping build validation\n")
                return ValidatorResult(
                    validator_id=self.id,
                    passed=True,
                    report_section="\n".join(report_lines),
                    metadata={"skipped": True, "reason": "no build system detected"},
                )

            # Run available commands.
            # "lint" and "test" are blocking (determine passed/failed).
            # "build" (production build) is non-blocking — it's informational only.
            # The browser validator starts its own dev server, so a production
            # build failure should NOT prevent runtime validation.
            results = {}
            blocking_types = ("lint", "test")
            for cmd_type in ("lint", "build", "test"):
                cmd = commands.get(cmd_type)
                if cmd:
                    print(f"[build] Running {cmd_type}: {cmd[:60]}...")
                    success, output = await self._run_command(cmd, project_dir)
                    results[cmd_type] = {"success": success, "output": output[:500]}
                    if success:
                        report_lines.append(f"- {cmd_type}: PASSED\n")
                        print(f"[build] {cmd_type}: PASSED")
                    else:
                        is_blocking = cmd_type in blocking_types
                        severity = "major" if is_blocking else "minor"
                        report_lines.append(f"- {cmd_type}: FAILED{'' if is_blocking else ' (non-blocking)'}\n")
                        print(f"[build] {cmd_type}: FAILED{'' if is_blocking else ' (non-blocking)'}")
                        issues.append({
                            "severity": severity,
                            "description": f"{cmd_type} command failed: {output[:200]}",
                            "file": "",
                            "line": 0,
                        })

            # Only lint and test failures block; build failures are informational
            passed = all(
                r["success"] for cmd_type, r in results.items()
                if cmd_type in blocking_types
            ) if any(cmd_type in blocking_types for cmd_type in results) else True
            return ValidatorResult(
                validator_id=self.id,
                passed=passed,
                issues=issues,
                report_section="\n".join(report_lines),
                metadata={"commands_run": results},
            )

        except Exception as e:
            logger.error(f"Build validator error: {e}")
            return ValidatorResult(
                validator_id=self.id,
                passed=False,
                issues=[{
                    "severity": "critical",
                    "description": f"Build validator error: {str(e)[:200]}",
                    "file": "",
                    "line": 0,
                }],
                report_section=f"## Build Validation\n\n- ERROR: {e}\n",
            )

    async def _run_command(self, cmd: str, cwd: Path) -> tuple[bool, str]:
        """Run a shell command and return (success, output)."""
        import asyncio

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
            output = stdout.decode("utf-8", errors="replace") if stdout else ""
            return proc.returncode == 0, output
        except asyncio.TimeoutError:
            return False, f"Command timed out after 300s: {cmd}"
        except Exception as e:
            return False, str(e)
