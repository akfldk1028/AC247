"""
Subtask Management Tools
========================

Tools for managing subtask status in implementation_plan.json.
Also includes tools for creating child specs (for large architecture projects).
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import os

from core.file_utils import write_json_atomic
from spec.validate_pkg.auto_fix import auto_fix_plan

logger = logging.getLogger(__name__)

# Maximum child spec nesting depth.
# depth 0 = root design task, depth 1 = child, depth 2 = grandchild.
# Default 2 (allows grandchildren). Override via AUTO_CLAUDE_MAX_CHILD_DEPTH env var.
MAX_CHILD_DEPTH = int(os.environ.get("AUTO_CLAUDE_MAX_CHILD_DEPTH", "2"))

# Task types that are NOT allowed beyond depth 1 (prevent recursive design explosion)
DESIGN_ONLY_TYPES = {"design", "architecture", "mcts"}


def _calculate_task_depth(spec_dir: Path) -> int:
    """Calculate nesting depth by walking up the parentTask chain.

    Returns:
        0 = root task (no parent)
        1 = child of root
        2 = grandchild
        ...
    """
    depth = 0
    current_dir = spec_dir
    specs_parent = spec_dir.parent  # .auto-claude/specs/

    for _ in range(10):  # safety limit
        plan_file = current_dir / "implementation_plan.json"
        if not plan_file.exists():
            break
        try:
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)
            parent_id = plan.get("parentTask", plan.get("parent_task"))
            if not parent_id:
                break
            depth += 1
            current_dir = specs_parent / parent_id
        except (json.JSONDecodeError, OSError):
            break

    return depth


def _get_original_project_dir(project_dir: Path) -> Path:
    """
    Get the original project directory from a worktree path.

    Worktrees are located at:
    - .auto-claude/worktrees/tasks/{spec-name}/
    - .worktrees/{spec-name}/ (legacy)

    This function extracts the original project path so child specs
    are created in the main project, not inside the worktree.

    Args:
        project_dir: Current working directory (may be a worktree)

    Returns:
        Original project directory path
    """
    resolved = project_dir.resolve()
    path_str = str(resolved).replace("\\", "/")

    # Check for worktree markers
    worktree_markers = [
        "/.auto-claude/worktrees/tasks/",
        "/.auto-claude/github/pr/worktrees/",
        "/.worktrees/",
    ]

    for marker in worktree_markers:
        if marker in path_str:
            # Extract the original project path (everything before the marker)
            original_path = path_str.split(marker)[0]
            return Path(original_path)

    # Not a worktree, return as-is
    return project_dir

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None


def _update_subtask_in_plan(
    plan: dict[str, Any],
    subtask_id: str,
    status: str,
    notes: str,
) -> bool:
    """
    Update a subtask in the plan.

    Args:
        plan: The implementation plan dict
        subtask_id: ID of the subtask to update
        status: New status (pending, in_progress, completed, failed)
        notes: Optional notes to add

    Returns:
        True if subtask was found and updated, False otherwise
    """
    subtask_found = False
    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            if subtask.get("id") == subtask_id:
                subtask["status"] = status
                if notes:
                    subtask["notes"] = notes
                subtask["updated_at"] = datetime.now(timezone.utc).isoformat()
                subtask_found = True
                break
        if subtask_found:
            break

    if subtask_found:
        plan["last_updated"] = datetime.now(timezone.utc).isoformat()

    return subtask_found


def create_subtask_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create subtask management tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of subtask tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    tools = []

    # -------------------------------------------------------------------------
    # Tool: update_subtask_status
    # -------------------------------------------------------------------------
    @tool(
        "update_subtask_status",
        "Update the status of a subtask in implementation_plan.json. Use this when completing or starting a subtask.",
        {"subtask_id": str, "status": str, "notes": str},
    )
    async def update_subtask_status(args: dict[str, Any]) -> dict[str, Any]:
        """Update subtask status in the implementation plan."""
        subtask_id = args["subtask_id"]
        status = args["status"]
        notes = args.get("notes", "")

        valid_statuses = ["pending", "in_progress", "completed", "failed"]
        if status not in valid_statuses:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Invalid status '{status}'. Must be one of: {valid_statuses}",
                    }
                ]
            }

        plan_file = spec_dir / "implementation_plan.json"
        if not plan_file.exists():
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: implementation_plan.json not found",
                    }
                ]
            }

        try:
            with open(plan_file, encoding="utf-8") as f:
                plan = json.load(f)

            subtask_found = _update_subtask_in_plan(plan, subtask_id, status, notes)

            if not subtask_found:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Subtask '{subtask_id}' not found in implementation plan",
                        }
                    ]
                }

            # Use atomic write to prevent file corruption
            write_json_atomic(plan_file, plan, indent=2)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully updated subtask '{subtask_id}' to status '{status}'",
                    }
                ]
            }

        except json.JSONDecodeError as e:
            # Attempt to auto-fix the plan and retry
            if auto_fix_plan(spec_dir):
                # Retry after fix
                try:
                    with open(plan_file, encoding="utf-8") as f:
                        plan = json.load(f)

                    subtask_found = _update_subtask_in_plan(
                        plan, subtask_id, status, notes
                    )

                    if subtask_found:
                        write_json_atomic(plan_file, plan, indent=2)
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Successfully updated subtask '{subtask_id}' to status '{status}' (after auto-fix)",
                                }
                            ]
                        }
                    else:
                        return {
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"Error: Subtask '{subtask_id}' not found in implementation plan (after auto-fix)",
                                }
                            ]
                        }
                except Exception as retry_err:
                    logging.warning(
                        f"Subtask update retry failed after auto-fix: {retry_err}"
                    )
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Subtask update failed after auto-fix: {retry_err}",
                            }
                        ]
                    }

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Invalid JSON in implementation_plan.json: {e}",
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error updating subtask status: {e}"}
                ]
            }

    tools.append(update_subtask_status)

    # -------------------------------------------------------------------------
    # Tool: create_child_spec
    # -------------------------------------------------------------------------
    @tool(
        "create_child_spec",
        """Create a new implementation spec (child task) that will be executed by the daemon.

Use this when you are a Design Agent breaking down a large project into parallel modules.
Each child spec will be picked up by the Task Daemon and executed independently.

Example:
    create_child_spec({
        "task_description": "Implement user authentication API",
        "priority": 1,
        "task_type": "impl",
        "depends_on": ["002-database-schema"],
        "files_to_modify": ["src/auth/api.py", "src/auth/models.py"]
    })
""",
        {
            "task_description": str,
            "priority": int,
            "task_type": str,
            "depends_on": list,
            "files_to_modify": list,
            "acceptance_criteria": list,
        },
    )
    async def create_child_spec(args: dict[str, Any]) -> dict[str, Any]:
        """Create a new child spec for parallel execution."""
        task_description = args.get("task_description")
        if not task_description:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: task_description is required",
                    }
                ]
            }

        # Depth guard: limit nesting to MAX_CHILD_DEPTH (default 2)
        current_depth = _calculate_task_depth(spec_dir)
        child_depth = current_depth + 1
        task_type = args.get("task_type", "impl")

        if child_depth > MAX_CHILD_DEPTH:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Error: Cannot create child spec from '{spec_dir.name}' "
                            f"(depth {current_depth}). Max nesting depth is {MAX_CHILD_DEPTH}. "
                            "Flatten your task decomposition instead of nesting deeper."
                        ),
                    }
                ]
            }

        # Block design/architecture types beyond depth 1 (prevent recursive explosion)
        if child_depth >= 2 and task_type in DESIGN_ONLY_TYPES:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Error: Cannot create '{task_type}' child spec at depth {child_depth}. "
                            "Design/architecture/mcts tasks can only be created at depth 0-1. "
                            "Use 'impl', 'frontend', 'backend', etc. for deeper nesting."
                        ),
                    }
                ]
            }

        priority = args.get("priority", 2)
        depends_on = args.get("depends_on") or args.get("dependsOn") or args.get("dependencies") or []
        files_to_modify = args.get("files_to_modify") or []
        acceptance_criteria = args.get("acceptance_criteria") or []

        # Get parent spec ID from current spec directory
        parent_spec_id = spec_dir.name

        try:
            # Import SpecFactory
            from services.spec_factory import SpecFactory

            # Use original project dir (not worktree) so specs are created in main project
            original_project_dir = _get_original_project_dir(project_dir)
            factory = SpecFactory(original_project_dir)

            # Create the child spec (await since we're in async function)
            child_spec_dir = await factory.create_child_spec(
                parent_spec_id=parent_spec_id,
                task_description=task_description,
                priority=priority,
                task_type=task_type,
                depends_on=depends_on,
                files_to_modify=files_to_modify,
                acceptance_criteria=acceptance_criteria,
            )

            child_spec_id = child_spec_dir.name

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully created child spec '{child_spec_id}'.\n\n"
                        f"- Task: {task_description}\n"
                        f"- Priority: {priority}\n"
                        f"- Type: {task_type}\n"
                        f"- Depends on: {depends_on or 'None'}\n"
                        f"- Parent: {parent_spec_id}\n\n"
                        f"The spec will be picked up by the Task Daemon automatically.",
                    }
                ]
            }

        except Exception as e:
            logging.error(f"Failed to create child spec: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error creating child spec: {e}",
                    }
                ]
            }

    tools.append(create_child_spec)

    # -------------------------------------------------------------------------
    # Tool: create_batch_child_specs
    # -------------------------------------------------------------------------
    @tool(
        "create_batch_child_specs",
        """Create multiple child specs at once for parallel execution.

Use this when you have analyzed a large project and want to create multiple
implementation tasks in one go.

Example:
    create_batch_child_specs({
        "specs": [
            {
                "task": "Backend API module",
                "priority": 1,
                "task_type": "impl"
            },
            {
                "task": "Database schema",
                "priority": 1,
                "task_type": "impl"
            },
            {
                "task": "Frontend UI components",
                "priority": 2,
                "depends_on": ["002-backend-api"]
            },
            {
                "task": "Integration tests",
                "priority": 3,
                "depends_on": ["002-backend-api", "004-frontend-ui"]
            }
        ]
    })
""",
        {"specs": list},
    )
    async def create_batch_child_specs(args: dict[str, Any]) -> dict[str, Any]:
        """Create multiple child specs for parallel execution."""
        specs_list = args.get("specs") or []
        if not specs_list:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: specs list is required and cannot be empty",
                    }
                ]
            }

        parent_spec_id = spec_dir.name

        # Idempotency guard: prevent duplicate calls in same session
        # If parent is already marked "complete" with childSpecs, reject
        parent_plan_file = spec_dir / "implementation_plan.json"
        if parent_plan_file.exists():
            try:
                with open(parent_plan_file, encoding="utf-8") as f:
                    parent_plan = json.load(f)
                if parent_plan.get("status") == "complete" or parent_plan.get("childSpecs"):
                    existing = parent_plan.get("childSpecs", [])
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    f"Child specs already created for '{parent_spec_id}' "
                                    f"({len(existing)} specs). Cannot create duplicates. "
                                    "Task is already decomposed."
                                ),
                            }
                        ]
                    }
            except (json.JSONDecodeError, OSError):
                pass

        # Depth guard: limit nesting to MAX_CHILD_DEPTH (default 2)
        current_depth = _calculate_task_depth(spec_dir)
        child_depth = current_depth + 1

        if child_depth > MAX_CHILD_DEPTH:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Error: Cannot create child specs from '{parent_spec_id}' "
                            f"(depth {current_depth}). Max nesting depth is {MAX_CHILD_DEPTH}. "
                            "Flatten your task decomposition instead of nesting deeper."
                        ),
                    }
                ]
            }

        # Block design/architecture types beyond depth 1
        has_design_type = any(
            s.get("task_type", "impl") in DESIGN_ONLY_TYPES for s in specs_list
        )
        if child_depth >= 2 and has_design_type:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Error: Cannot create 'design'/'architecture'/'mcts' child specs at depth {child_depth}. "
                            "Design/architecture/mcts tasks can only be created at depth 0-1. "
                            "Use 'impl', 'frontend', 'backend', etc. for deeper nesting."
                        ),
                    }
                ]
            }

        try:
            from services.spec_factory import SpecFactory

            # Use original project dir (not worktree) so specs are created in main project
            original_project_dir = _get_original_project_dir(project_dir)
            factory = SpecFactory(original_project_dir)

            # Create all specs (await since we're in async function)
            created_specs = await factory.create_batch_specs(
                parent_spec_id=parent_spec_id,
                specs=specs_list,
            )

            # Build result message
            result_lines = [
                f"Successfully created {len(created_specs)} child specs:",
                "",
            ]

            child_spec_names = []
            for i, spec_dir_path in enumerate(created_specs):
                spec_def = specs_list[i] if i < len(specs_list) else {}
                task = spec_def.get("task") or spec_def.get("task_description", "Unknown")
                result_lines.append(f"  {i+1}. {spec_dir_path.name}")
                result_lines.append(f"     Task: {task}")
                child_spec_names.append(spec_dir_path.name)

            result_lines.extend([
                "",
                f"Parent spec: {parent_spec_id}",
                "All specs will be picked up by the Task Daemon automatically.",
            ])

            # Update parent spec status to "complete" so it doesn't run again
            # This prevents the infinite loop where is_first_run() keeps returning True
            parent_plan_file = spec_dir / "implementation_plan.json"
            print(f"[BATCH_SPECS] Updating parent: {parent_plan_file}", flush=True)
            if parent_plan_file.exists():
                try:
                    with open(parent_plan_file, encoding="utf-8") as f:
                        parent_plan = json.load(f)

                    parent_plan["status"] = "complete"
                    parent_plan["planStatus"] = "complete"
                    parent_plan["executionPhase"] = "complete"
                    parent_plan["childSpecs"] = child_spec_names
                    parent_plan["completedAt"] = datetime.now(timezone.utc).isoformat()

                    # Direct write with retry (more reliable than atomic on Windows)
                    for attempt in range(3):
                        try:
                            with open(parent_plan_file, "w", encoding="utf-8") as wf:
                                json.dump(parent_plan, wf, indent=2)
                            print(f"[BATCH_SPECS] Parent updated to 'complete' (attempt {attempt+1})", flush=True)
                            break
                        except PermissionError:
                            print(f"[BATCH_SPECS] PermissionError on attempt {attempt+1}, retrying...", flush=True)
                            import time
                            time.sleep(0.5)
                    else:
                        # All retries failed, try write_json_atomic as last resort
                        write_json_atomic(parent_plan_file, parent_plan, indent=2)
                        print(f"[BATCH_SPECS] Parent updated via atomic write", flush=True)

                    result_lines.append("")
                    result_lines.append("Parent spec status updated to 'complete'.")
                except Exception as plan_err:
                    print(f"[BATCH_SPECS] FAILED: {plan_err}", flush=True)
                    logging.warning(f"Failed to update parent spec status: {plan_err}")
                    result_lines.append("")
                    result_lines.append(f"Warning: Could not update parent status: {plan_err}")
            else:
                print(f"[BATCH_SPECS] Parent file NOT FOUND: {parent_plan_file}", flush=True)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": "\n".join(result_lines),
                    }
                ]
            }

        except Exception as e:
            logging.error(f"Failed to create batch specs: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error creating batch specs: {e}",
                    }
                ]
            }

    tools.append(create_batch_child_specs)

    return tools
