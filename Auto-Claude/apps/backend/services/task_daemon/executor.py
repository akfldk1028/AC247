"""
Task Daemon Executor - Task Execution Logic
============================================

Handles building and running task commands.

Module maintainability:
- Separated from daemon orchestration
- Easy to add new execution backends
- Claude CLI and run.py support
- Agent Registry for task-type specific agents

Extensibility:
- Add new agents to AGENT_REGISTRY
- Each agent can have custom script, prompt, CLI flags
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from .types import (
    ExecutionMode,
    PLAN_MODE_TASK_TYPES,
)

if TYPE_CHECKING:
    from logging import Logger


# =============================================================================
# AGENT REGISTRY - Task Type별 Agent 설정
# =============================================================================


@dataclass
class AgentConfig:
    """
    Configuration for a specific agent type.

    Allows customizing execution per task type.
    나중에 agent별 다른 명령어 지원할 때 이 클래스 사용.

    Examples:
        # Custom script agent
        AgentConfig(
            script="agents/frontend_agent.py",
            extra_args=["--framework", "react"],
        )

        # Custom prompt agent
        AgentConfig(
            use_claude_cli=True,
            prompt_template="You are a frontend specialist...",
        )

        # Default (uses run.py)
        AgentConfig()
    """

    # Script path (relative to auto_claude_dir)
    # None = use default run.py
    script: str | None = None

    # Extra CLI arguments for the script
    extra_args: list[str] = field(default_factory=list)

    # Force Claude CLI instead of script
    use_claude_cli: bool = False

    # Custom prompt template (for Claude CLI mode)
    # {spec_id}, {task}, {spec_content} placeholders available
    prompt_template: str | None = None

    # Custom system prompt file (relative to prompts/)
    system_prompt: str | None = None

    # Execution mode override (None = auto-detect)
    execution_mode: str | None = None

    # MCP servers for this agent type (future: Claude CLI --mcp flag)
    # e.g., ["puppeteer"] for frontend, ["context7"] for backend
    mcp_servers: list[str] = field(default_factory=list)

    # Pre-execution hook (e.g., setup, validation)
    pre_hook: Callable[[str, Path], bool] | None = None

    # Post-execution hook (e.g., cleanup, reporting)
    post_hook: Callable[[str, Path, int], None] | None = None


# Agent Registry - Task Type별 Agent 매핑
# 새 agent 추가 시 여기에 등록
#
# Key design decision: design/architecture agents use run.py (use_claude_cli=False)
# because run.py → create_client() → auto-claude MCP server → create_batch_child_specs tool.
# Claude CLI mode does NOT have access to auto-claude MCP tools.
AGENT_REGISTRY: dict[str, AgentConfig] = {
    # Plan Mode Agents (설계/분석)
    # use_claude_cli=False → run.py 사용 → MCP tool 접근 가능
    # (create_batch_child_specs 등)
    "design": AgentConfig(
        use_claude_cli=False,  # run.py for MCP tool access
        system_prompt="design_architect.md",
        prompt_template=(
            "You are a Design Architect Agent.\n\n"
            "Task: {task}\n\n"
            "Analyze the project structure and create implementation tasks using "
            "the create_batch_child_specs tool.\n\n"
            "Spec Content:\n{spec_content}"
        ),
    ),
    "architecture": AgentConfig(
        use_claude_cli=False,  # run.py for MCP tool access
        prompt_template=(
            "You are an Architecture Analyst Agent.\n\n"
            "Task: {task}\n\n"
            "Analyze the codebase architecture and provide recommendations.\n\n"
            "Spec Content:\n{spec_content}"
        ),
    ),
    "research": AgentConfig(
        use_claude_cli=True,
        execution_mode=ExecutionMode.PLAN,
        prompt_template=(
            "You are a Research Agent.\n\n"
            "Task: {task}\n\n"
            "Investigate the codebase and gather information.\n\n"
            "Spec Content:\n{spec_content}"
        ),
    ),
    "review": AgentConfig(
        use_claude_cli=True,
        execution_mode=ExecutionMode.PLAN,
        prompt_template=(
            "You are a Code Review Agent.\n\n"
            "Task: {task}\n\n"
            "Review the code and provide feedback.\n\n"
            "Spec Content:\n{spec_content}"
        ),
    ),

    # Implementation Agents (구현)
    # 기본값 = run.py 사용 (Auto-Claude pipeline: planner → coder → QA)
    "impl": AgentConfig(),
    "frontend": AgentConfig(
        mcp_servers=["puppeteer"],  # UI 테스트용
    ),
    "backend": AgentConfig(
        mcp_servers=["context7"],  # API 문서 참조
    ),
    "database": AgentConfig(
        mcp_servers=["context7"],  # DB 라이브러리 문서
    ),
    "api": AgentConfig(),
    "test": AgentConfig(),
    "integration": AgentConfig(),
    "docs": AgentConfig(),

    # Verification & Error-Check Agents
    "verify": AgentConfig(
        use_claude_cli=False,  # run.py for MCP tool access
        system_prompt="verify_agent.md",
        # MCP servers resolved dynamically by models.py AGENT_CONFIGS
        # ("browser" → puppeteer/electron based on project type)
    ),
    "error_check": AgentConfig(
        use_claude_cli=False,  # run.py for MCP tool access
        system_prompt="error_check_agent.md",
    ),

    # Default fallback
    "default": AgentConfig(),
}


def register_agent(task_type: str, config: AgentConfig) -> None:
    """
    Register a custom agent for a task type.

    Example:
        register_agent("frontend", AgentConfig(
            script="agents/frontend_specialist.py",
            extra_args=["--framework", "react", "--typescript"],
        ))
    """
    AGENT_REGISTRY[task_type] = config


def get_agent_config(task_type: str) -> AgentConfig:
    """Get agent config for a task type, falling back to default."""
    return AGENT_REGISTRY.get(task_type, AGENT_REGISTRY["default"])


class TaskExecutor:
    """
    Builds and executes task commands.

    Supports:
    - Auto-Claude run.py (default)
    - Claude CLI with plan mode
    - Claude CLI with headless mode
    """

    def __init__(
        self,
        project_dir: Path,
        specs_dir: Path,
        auto_claude_dir: Path | None,
        *,
        use_claude_cli: bool = False,
        claude_cli_path: str | None = None,
        headless_mode: bool = True,
        logger: Logger | None = None,
    ):
        """
        Initialize executor.

        Args:
            project_dir: Project directory
            specs_dir: Specs directory (.auto-claude/specs/)
            auto_claude_dir: Auto-Claude backend directory
            use_claude_cli: Use Claude CLI instead of run.py
            claude_cli_path: Custom Claude CLI path
            headless_mode: Enable headless mode for non-plan tasks
            logger: Logger instance
        """
        self.project_dir = project_dir
        self.specs_dir = specs_dir
        self.auto_claude_dir = auto_claude_dir
        self.use_claude_cli = use_claude_cli
        self.claude_cli_path = claude_cli_path or self._find_claude_cli()
        self.headless_mode = headless_mode
        self._logger = logger

    def _log(self, level: str, message: str) -> None:
        """Log a message."""
        if self._logger:
            getattr(self._logger, level)(message)

    def _find_claude_cli(self) -> str | None:
        """Find the Claude CLI executable."""
        candidates = ["claude", "claude.exe"]

        for name in candidates:
            path = shutil.which(name)
            if path:
                return path

        # Windows-specific locations
        if sys.platform == "win32":
            home = Path.home()
            win_paths = [
                home / ".local" / "bin" / "claude.exe",
                home / "AppData" / "Local" / "Programs" / "claude" / "claude.exe",
            ]
            for path in win_paths:
                if path.exists():
                    return str(path)

        return None

    def get_execution_mode(self, task_type: str) -> str:
        """
        Determine execution mode based on task type.

        Plan Mode: design, architecture, planning, research, review
        Headless Mode: impl, frontend, backend, database, api, test, etc.
        """
        if task_type in PLAN_MODE_TASK_TYPES:
            return ExecutionMode.PLAN

        if self.headless_mode:
            return ExecutionMode.HEADLESS

        return ExecutionMode.STANDARD

    def build_command(
        self,
        spec_id: str,
        work_dir: Path,
        execution_mode: str,
        task_type: str = "default",
    ) -> tuple[list[str] | None, Path]:
        """
        Build the command to run a task.

        Uses AGENT_REGISTRY to determine how to execute each task type.

        Args:
            spec_id: Spec ID
            work_dir: Working directory
            execution_mode: Execution mode (plan, headless, standard)
            task_type: Task type for agent selection

        Returns:
            Tuple of (command list, working directory for subprocess)
        """
        # Get agent config from registry
        agent_config = get_agent_config(task_type)

        # Override execution mode if agent specifies it
        if agent_config.execution_mode:
            execution_mode = agent_config.execution_mode

        # Run pre-hook if defined
        if agent_config.pre_hook:
            try:
                if not agent_config.pre_hook(spec_id, work_dir):
                    self._log("warning", f"Pre-hook failed for {spec_id}")
                    return None, work_dir
            except Exception as e:
                self._log("error", f"Pre-hook error for {spec_id}: {e}")

        # 1. Agent has custom script → use that script
        if agent_config.script and self.auto_claude_dir:
            cmd = self._build_custom_agent_command(
                spec_id, work_dir, agent_config
            )
            if cmd:
                return cmd, self.auto_claude_dir

        # 2. Agent forces Claude CLI or Plan mode → Claude CLI
        if agent_config.use_claude_cli and self.claude_cli_path:
            cmd = self._build_claude_cli_command(
                spec_id, work_dir, execution_mode, agent_config
            )
            return cmd, work_dir

        # 3. Plan mode → Claude CLI (only for agents not explicitly registered)
        #    Registered agents like "design"/"architecture" chose run.py in their
        #    config (use_claude_cli=False). Only unregistered plan-mode tasks
        #    should fall through to Claude CLI here.
        if execution_mode == ExecutionMode.PLAN and self.claude_cli_path:
            if task_type not in AGENT_REGISTRY:
                cmd = self._build_claude_cli_command(
                    spec_id, work_dir, execution_mode, agent_config
                )
                return cmd, work_dir

        # 4. Explicit Claude CLI mode → Claude CLI
        if self.use_claude_cli and self.claude_cli_path:
            cmd = self._build_claude_cli_command(
                spec_id, work_dir, execution_mode, agent_config
            )
            return cmd, work_dir

        # 5. Default: Use run.py (Auto-Claude pipeline)
        cmd = self._build_run_py_command(spec_id, work_dir, execution_mode)
        return cmd, self.auto_claude_dir

    def _build_custom_agent_command(
        self,
        spec_id: str,
        work_dir: Path,
        agent_config: AgentConfig,
    ) -> list[str] | None:
        """Build command for a custom agent script."""
        if not self.auto_claude_dir or not agent_config.script:
            return None

        script_path = self.auto_claude_dir / agent_config.script
        if not script_path.exists():
            self._log("warning", f"Agent script not found: {script_path}")
            return None

        cmd = [
            self._find_venv_python(),
            "-u",  # unbuffered stdout/stderr (critical for Windows pipe reading)
            str(script_path),
            "--spec", spec_id,
            "--project-dir", str(work_dir),
        ]

        # Add extra args from config
        if agent_config.extra_args:
            cmd.extend(agent_config.extra_args)

        return cmd

    def _find_venv_python(self) -> str:
        """Find the venv Python executable, falling back to sys.executable."""
        if not self.auto_claude_dir:
            return sys.executable

        # Check for venv in auto_claude_dir
        if sys.platform == "win32":
            venv_python = self.auto_claude_dir / ".venv" / "Scripts" / "python.exe"
        else:
            venv_python = self.auto_claude_dir / ".venv" / "bin" / "python"

        if venv_python.exists():
            return str(venv_python)

        return sys.executable

    def _build_run_py_command(
        self,
        spec_id: str,
        work_dir: Path,
        execution_mode: str,
    ) -> list[str] | None:
        """Build command using Auto-Claude's run.py."""
        if not self.auto_claude_dir:
            return None

        run_script = self.auto_claude_dir / "run.py"
        if not run_script.exists():
            return None

        python_path = self._find_venv_python()

        cmd = [
            python_path,
            "-u",  # unbuffered stdout/stderr (critical for Windows pipe reading)
            str(run_script),
            "--spec", spec_id,
            "--project-dir", str(work_dir),
            "--auto-continue",
            "--force",  # bypass approval check for daemon (24/7 unattended)
        ]

        return cmd

    def _build_claude_cli_command(
        self,
        spec_id: str,
        work_dir: Path,
        execution_mode: str,
        agent_config: AgentConfig | None = None,
    ) -> list[str] | None:
        """
        Build command using Claude CLI directly.

        Claude CLI flags:
        - --permission-mode plan: Read-only exploration
        - --dangerously-skip-permissions: Skip all prompts
        - -p "prompt": Headless mode with prompt
        - --output-format stream-json: Streaming JSON output
        """
        if not self.claude_cli_path:
            return None

        spec_dir = self.specs_dir / spec_id
        spec_path = spec_dir / "spec.md"
        requirements_path = spec_dir / "requirements.json"
        plan_path = spec_dir / "implementation_plan.json"

        cmd = [self.claude_cli_path]

        # Add execution mode flags
        if execution_mode == ExecutionMode.PLAN:
            cmd.extend(["--permission-mode", "plan"])
        elif execution_mode == ExecutionMode.HEADLESS:
            cmd.append("--dangerously-skip-permissions")

        # Build prompt: use agent-specific template if available
        if agent_config and agent_config.prompt_template:
            prompt = self._build_agent_prompt(spec_id, spec_dir, agent_config)
        else:
            prompt = self._build_prompt(spec_id, spec_path, requirements_path, plan_path)

        if not prompt:
            return None

        cmd.extend(["-p", prompt])
        cmd.extend(["--output-format", "stream-json"])

        return cmd

    def _build_prompt(
        self,
        spec_id: str,
        spec_path: Path,
        requirements_path: Path,
        plan_path: Path,
    ) -> str | None:
        """Build prompt from spec files."""
        prompt_parts = []

        # Try spec.md
        if spec_path.exists():
            try:
                prompt_parts.append(spec_path.read_text(encoding="utf-8-sig"))
            except Exception:
                pass

        # Try requirements.json
        if requirements_path.exists():
            try:
                requirements = json.loads(requirements_path.read_text(encoding="utf-8-sig"))
                task = requirements.get("task", "")
                if task and task not in str(prompt_parts):
                    prompt_parts.insert(0, f"Task: {task}\n")
            except Exception:
                pass

        # Default prompt if nothing found
        if not prompt_parts:
            prompt_parts.append(f"Implement task: {spec_id}")

        # Add subtask context
        if plan_path.exists():
            try:
                plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
                subtasks = plan.get("subtasks", [])
                if subtasks:
                    prompt_parts.append(f"\n\nSubtasks to complete: {len(subtasks)}")

                task_type = plan.get("taskType", plan.get("task_type", ""))
                if task_type in ("design", "architecture"):
                    prompt_parts.append(
                        "\n\nAs a Design Agent, analyze the project and use "
                        "create_batch_child_specs tool to create implementation tasks."
                    )
            except Exception:
                pass

        return "\n".join(prompt_parts)

    def _build_agent_prompt(
        self,
        spec_id: str,
        spec_dir: Path,
        agent_config: AgentConfig,
    ) -> str | None:
        """Build prompt from AgentConfig's prompt_template.

        Injects {spec_id}, {task}, {spec_content} into the template.
        """
        if not agent_config.prompt_template:
            return None

        # Load spec content
        spec_content = ""
        spec_path = spec_dir / "spec.md"
        if spec_path.exists():
            try:
                spec_content = spec_path.read_text(encoding="utf-8-sig")
            except Exception:
                pass

        # Extract task from requirements.json
        task = spec_id
        req_path = spec_dir / "requirements.json"
        if req_path.exists():
            try:
                reqs = json.loads(req_path.read_text(encoding="utf-8-sig"))
                task = reqs.get("task", spec_id)
            except Exception:
                pass

        # Use manual replacement instead of str.format() because spec_content
        # may contain curly braces from code/JSON which would crash format() (BUG 18)
        result = agent_config.prompt_template
        result = result.replace("{spec_id}", spec_id)
        result = result.replace("{task}", task)
        result = result.replace("{spec_content}", spec_content)
        return result

    def spawn_process(
        self,
        cmd: list[str],
        cwd: Path,
    ) -> subprocess.Popen:
        """
        Spawn a subprocess for task execution.

        Args:
            cmd: Command to run
            cwd: Working directory

        Returns:
            Popen object
        """
        # Force unbuffered output so _read_output() gets lines in real-time
        # and last_update stays current (prevents false stuck detection)
        env = {**os.environ, "PYTHONUNBUFFERED": "1"}

        # Windows: CREATE_NEW_PROCESS_GROUP so taskkill /T can kill the
        # entire process tree (python → run.py → claude, etc.) (BUG 9)
        kwargs: dict = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        # Use encoding="utf-8" explicitly because:
        # - run.py reconfigures stdout to UTF-8 on Windows (lines 46-71)
        # - Without this, Popen uses system default (cp1252 on Windows)
        # - Encoding mismatch can block readline() on multi-byte chars
        return subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            stdin=subprocess.DEVNULL,
            env=env,
            **kwargs,
        )


def find_auto_claude_backend(project_dir: Path) -> Path | None:
    """Find the Auto-Claude backend directory."""
    # Check relative to current file first
    current_file_backend = Path(__file__).parent.parent.parent
    if (current_file_backend / "run.py").exists():
        return current_file_backend.resolve()

    # Check relative to project directory
    candidates = [
        project_dir / "Auto-Claude" / "apps" / "backend",
        project_dir.parent / "Auto-Claude" / "apps" / "backend",
        project_dir.parent.parent / "Auto-Claude" / "apps" / "backend",
    ]

    for candidate in candidates:
        if (candidate / "run.py").exists():
            return candidate.resolve()

    return None
