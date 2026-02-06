#!/usr/bin/env python3
"""
Spec Factory - Programmatic Spec Creation for Large Architecture Projects
=========================================================================

Design Agent가 대형 프로젝트를 분해할 때 사용하는 spec 생성 API.

핵심 기능:
- 프로그래밍 방식으로 child spec 생성
- parent_task 연결
- 의존성 설정 (depends_on)
- 우선순위 설정

Usage:
    from services.spec_factory import SpecFactory

    factory = SpecFactory(project_dir)

    # 단일 child spec 생성
    spec_dir = await factory.create_child_spec(
        parent_spec_id="001-design",
        task_description="Implement user authentication module",
        priority=1,
        depends_on=["002-database-schema"],
    )

    # 여러 child specs 일괄 생성
    specs = await factory.create_batch_specs(
        parent_spec_id="001-design",
        specs=[
            {"task": "Backend API", "priority": 1},
            {"task": "Frontend UI", "priority": 2, "depends_on": ["002-backend"]},
            {"task": "Integration tests", "priority": 3, "depends_on": ["002-backend", "003-frontend"]},
        ]
    )
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.task_daemon import TaskPriority


class SpecFactory:
    """
    Factory for creating specs programmatically.

    Design Agent나 Architecture Agent가 대형 프로젝트를 분해할 때,
    이 factory를 사용해서 child spec들을 자동 생성합니다.
    """

    def __init__(self, project_dir: Path):
        """
        Initialize SpecFactory.

        Args:
            project_dir: Project directory containing .auto-claude/specs/
        """
        self.project_dir = Path(project_dir).resolve()
        self.specs_dir = self.project_dir / ".auto-claude" / "specs"

        # Ensure specs directory exists
        self.specs_dir.mkdir(parents=True, exist_ok=True)

    def _generate_spec_id(self, task_description: str) -> str:
        """Generate a unique spec ID from task description."""
        # Get next sequence number
        existing = list(self.specs_dir.iterdir())
        max_num = 0
        for d in existing:
            if d.is_dir() and d.name[:3].isdigit():
                try:
                    num = int(d.name[:3])
                    max_num = max(max_num, num)
                except ValueError:
                    pass

        next_num = max_num + 1

        # Slugify task description
        slug = task_description.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')[:50]

        return f"{next_num:03d}-{slug}"

    @staticmethod
    def _normalize_list_field(value: Any) -> list[str]:
        """
        Normalize a field that should be a list but might be a JSON-encoded string.

        MCP tools sometimes double-serialize lists, resulting in:
            '["002-foo", "003-bar"]' instead of ["002-foo", "003-bar"]

        Args:
            value: The value to normalize (list, string, or None)

        Returns:
            A proper Python list of strings
        """
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("["):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass
            # Single string value - treat as single-item list
            if value:
                return [value]
            return []
        return []

    async def create_child_spec(
        self,
        parent_spec_id: str,
        task_description: str,
        *,
        priority: int = TaskPriority.NORMAL,
        task_type: str = "impl",
        depends_on: list[str] | None = None,
        complexity: str = "standard",
        files_to_modify: list[str] | None = None,
        acceptance_criteria: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> Path:
        """
        Create a new child spec that will be picked up by the daemon.

        Args:
            parent_spec_id: ID of the parent spec (e.g., "001-design")
            task_description: Description of what this spec should implement
            priority: Task priority (0=CRITICAL, 1=HIGH, 2=NORMAL, 3=LOW)
            task_type: Type of task (design, architecture, impl, test, integration)
            depends_on: List of spec IDs that must complete before this one
            complexity: Complexity level (simple, standard, complex)
            files_to_modify: List of files this spec will likely modify
            acceptance_criteria: List of acceptance criteria
            context: Additional context to pass to the agent

        Returns:
            Path to the created spec directory
        """
        # Normalize depends_on in case it was double-serialized by MCP
        depends_on = self._normalize_list_field(depends_on)

        spec_id = self._generate_spec_id(task_description)
        spec_dir = self.specs_dir / spec_id
        spec_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc).isoformat()

        # Create spec.md
        spec_content = self._generate_spec_md(
            task_description=task_description,
            parent_spec_id=parent_spec_id,
            acceptance_criteria=acceptance_criteria or [],
            files_to_modify=files_to_modify or [],
        )
        (spec_dir / "spec.md").write_text(spec_content, encoding="utf-8")

        # Create requirements.json
        requirements = {
            "task": task_description,
            "parent_spec": parent_spec_id,
            "complexity": complexity,
            "files_to_modify": files_to_modify or [],
            "acceptance_criteria": acceptance_criteria or [],
            "created_at": now,
            "created_by": "spec_factory",
        }
        (spec_dir / "requirements.json").write_text(
            json.dumps(requirements, indent=2),
            encoding="utf-8"
        )

        # Create implementation_plan.json (queued status for daemon)
        plan = {
            "status": "queue",
            "planStatus": "queue",
            "xstateState": "backlog",
            "executionPhase": "backlog",
            "taskType": task_type,
            "priority": priority,
            "parentTask": parent_spec_id,
            "dependsOn": depends_on or [],
            "complexity": complexity,
            "created_at": now,
            "updated_at": now,
            "phases": [],
            "subtasks": [],
        }

        if context:
            plan["context"] = context

        (spec_dir / "implementation_plan.json").write_text(
            json.dumps(plan, indent=2),
            encoding="utf-8"
        )

        # Create context.json
        ctx = {
            "parent_spec": parent_spec_id,
            "task_description": task_description,
            "files_to_modify": files_to_modify or [],
            "created_at": now,
        }
        if context:
            ctx.update(context)

        (spec_dir / "context.json").write_text(
            json.dumps(ctx, indent=2),
            encoding="utf-8"
        )

        return spec_dir

    def _resolve_batch_dependencies(
        self,
        specs: list[dict[str, Any]],
        created_specs: list[Path],
    ) -> None:
        """
        Resolve internal dependency references to actual spec IDs.

        Design agents use internal references like "002-database-schema" in depends_on,
        but the actual spec IDs are "135-database-schema-...". This method builds a
        mapping and updates all child spec implementation_plan.json files.

        Mapping strategies (tried in order):
        1. Batch index: agent uses NNN-slug where NNN maps to batch order
           (e.g., "002" = 1st child if parent is "001", or 2nd in batch)
        2. Slug matching: the slug portion matches the actual spec ID's slug
        3. Pure number: just a number like "1", "2", "3" = batch index (1-based)
        """
        if not created_specs:
            return

        # Build mapping: internal ref patterns → actual spec ID
        ref_to_actual: dict[str, str] = {}

        for i, spec_dir in enumerate(created_specs):
            actual_id = spec_dir.name  # e.g., "135-scientific-calculator-mode-implement..."
            actual_slug = re.sub(r'^\d+-', '', actual_id)  # remove leading number

            # Internal numbering: first child = 002, second = 003, etc.
            internal_num = i + 2  # parent=001, children start at 002
            batch_1based = i + 1  # 1-based batch index

            # Extract slug from original spec_def for matching
            spec_def = specs[i] if i < len(specs) else {}
            task = spec_def.get("task") or spec_def.get("task_description", "")
            task_slug = re.sub(r'[^a-z0-9\s-]', '', task.lower())
            task_slug = re.sub(r'[\s_]+', '-', task_slug)
            task_slug = re.sub(r'-+', '-', task_slug).strip('-')

            # Register all patterns that could refer to this spec
            # NOTE: Only use 3-digit padded for internal_num ("002") and
            # unpadded for batch_1based ("1") to avoid key collisions.
            # e.g., i=0: "002" and "1", i=1: "003" and "2" — no overlap.
            ref_to_actual[f"{internal_num:03d}"] = actual_id           # "002"
            ref_to_actual[f"{batch_1based}"] = actual_id               # "1"
            ref_to_actual[actual_id] = actual_id                       # exact match
            if actual_slug:
                ref_to_actual[actual_slug] = actual_id                 # "scientific-calculator-mode-implement..."
            # Also register NNN-task_slug pattern for agents that use "002-backend-api" style refs
            if task_slug:
                ref_to_actual[f"{internal_num:03d}-{task_slug}"] = actual_id  # "002-backend-api-module"

        # Now resolve each spec's depends_on
        for i, spec_dir in enumerate(created_specs):
            spec_def = specs[i] if i < len(specs) else {}
            # Check both snake_case and camelCase keys (agents may use either)
            original_deps = self._normalize_list_field(
                spec_def.get("depends_on")
                or spec_def.get("dependsOn")
                or spec_def.get("dependencies")
                or []
            )
            if not original_deps:
                continue

            resolved_deps = []
            for dep_ref in original_deps:
                resolved = self._resolve_single_dep(dep_ref, ref_to_actual, created_specs)
                resolved_deps.append(resolved)

            # Update implementation_plan.json with resolved dependencies
            plan_path = spec_dir / "implementation_plan.json"
            if plan_path.exists():
                try:
                    plan = json.loads(plan_path.read_text(encoding="utf-8"))
                    plan["dependsOn"] = resolved_deps
                    plan["updated_at"] = datetime.now(timezone.utc).isoformat()
                    plan_path.write_text(json.dumps(plan, indent=2), encoding="utf-8")
                except (json.JSONDecodeError, OSError):
                    pass

    def _resolve_single_dep(
        self,
        dep_ref: str,
        ref_to_actual: dict[str, str],
        created_specs: list[Path],
    ) -> str:
        """
        Resolve a single dependency reference to an actual spec ID.

        Args:
            dep_ref: The internal reference (e.g., "002-database-schema")
            ref_to_actual: Mapping of reference patterns to actual spec IDs
            created_specs: List of created spec directories

        Returns:
            The resolved actual spec ID, or the original reference if unresolvable
        """
        # 1. Exact match
        if dep_ref in ref_to_actual:
            return ref_to_actual[dep_ref]

        # 2. Extract number prefix and try matching
        num_match = re.match(r'^(\d+)', dep_ref)
        if num_match:
            num_str = num_match.group(1)
            # Try with leading zeros
            padded = num_str.zfill(3)
            if padded in ref_to_actual:
                return ref_to_actual[padded]
            # Try as-is
            if num_str in ref_to_actual:
                return ref_to_actual[num_str]

        # 3. Slug-based fuzzy matching
        dep_slug = re.sub(r'^\d+-', '', dep_ref).lower()  # remove leading number
        if dep_slug:
            best_match = None
            best_score = 0
            for spec_dir in created_specs:
                actual_id = spec_dir.name
                actual_slug = re.sub(r'^\d+-', '', actual_id).lower()

                # Check if dep_slug is a prefix of or contained in actual_slug
                if dep_slug in actual_slug or actual_slug.startswith(dep_slug):
                    # Score by how much of the slug matches
                    score = len(dep_slug) / max(len(actual_slug), 1)
                    if score > best_score:
                        best_score = score
                        best_match = actual_id

            if best_match and best_score > 0.3:
                return best_match

        # 4. No match found - return original (will be unresolvable but won't crash)
        return dep_ref

    async def create_batch_specs(
        self,
        parent_spec_id: str,
        specs: list[dict[str, Any]],
    ) -> list[Path]:
        """
        Create multiple child specs at once with dependency resolution.

        Uses a 2-pass approach:
        1. Pass 1: Create all specs (with empty depends_on)
        2. Pass 2: Resolve internal dependency references to actual spec IDs

        This ensures that agent's internal references like "002-database-schema"
        are correctly mapped to actual spec IDs like "135-database-schema-...".

        Args:
            parent_spec_id: ID of the parent design spec
            specs: List of spec definitions, each with:
                - task: Task description (required)
                - priority: Priority level (optional, default: NORMAL)
                - task_type: Task type (optional, default: impl)
                - depends_on: Dependencies (optional, will be resolved)
                - complexity: Complexity (optional, default: standard)
                - files: Files to modify (optional)
                - criteria: Acceptance criteria (optional)

        Returns:
            List of created spec directory paths
        """
        created_specs = []
        valid_spec_defs = []  # Track only spec_defs that were actually created

        # Pass 1: Create all specs with empty depends_on
        for spec_def in specs:
            task = spec_def.get("task") or spec_def.get("task_description")
            if not task:
                continue

            spec_dir = await self.create_child_spec(
                parent_spec_id=parent_spec_id,
                task_description=task,
                priority=spec_def.get("priority", TaskPriority.NORMAL),
                task_type=spec_def.get("task_type", "impl"),
                depends_on=[],  # Empty initially - resolved in pass 2
                complexity=spec_def.get("complexity", "standard"),
                files_to_modify=spec_def.get("files") or spec_def.get("files_to_modify"),
                acceptance_criteria=spec_def.get("criteria") or spec_def.get("acceptance_criteria"),
                context=spec_def.get("context"),
            )
            created_specs.append(spec_dir)
            valid_spec_defs.append(spec_def)

        # Pass 2: Resolve internal dependency references to actual spec IDs
        # Use valid_spec_defs (not specs) so indices align with created_specs
        self._resolve_batch_dependencies(valid_spec_defs, created_specs)

        return created_specs

    def _generate_spec_md(
        self,
        task_description: str,
        parent_spec_id: str,
        acceptance_criteria: list[str],
        files_to_modify: list[str],
    ) -> str:
        """Generate spec.md content."""
        lines = [
            f"# {task_description}",
            "",
            f"> Parent Spec: `{parent_spec_id}`",
            "",
            "## Overview",
            "",
            task_description,
            "",
        ]

        if acceptance_criteria:
            lines.extend([
                "## Acceptance Criteria",
                "",
            ])
            for criterion in acceptance_criteria:
                lines.append(f"- [ ] {criterion}")
            lines.append("")

        if files_to_modify:
            lines.extend([
                "## Files to Modify",
                "",
            ])
            for f in files_to_modify:
                lines.append(f"- `{f}`")
            lines.append("")

        lines.extend([
            "## Notes",
            "",
            "This spec was auto-generated by SpecFactory from a design task.",
            "",
        ])

        return "\n".join(lines)

    def get_child_specs(self, parent_spec_id: str) -> list[Path]:
        """Get all child specs of a parent spec."""
        children = []

        for spec_dir in self.specs_dir.iterdir():
            if not spec_dir.is_dir():
                continue

            plan_path = spec_dir / "implementation_plan.json"
            if not plan_path.exists():
                continue

            try:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                parent = plan.get("parentTask") or plan.get("parent_task")
                if parent == parent_spec_id:
                    children.append(spec_dir)
            except (json.JSONDecodeError, OSError):
                continue

        return children

    def repair_all_dependencies(self) -> int:
        """
        Repair all broken dependency references across all specs.

        This method:
        1. Groups specs by parentTask
        2. For each group, resolves internal refs to actual sibling spec IDs
        3. Fixes string-encoded arrays (double-serialized JSON)
        4. Updates implementation_plan.json files

        Called by Task Daemon on startup to fix existing broken references.
        Safe to call multiple times - already-correct refs are left unchanged.

        Returns:
            Number of specs that were repaired
        """
        if not self.specs_dir.exists():
            return 0

        # Step 1: Load all specs and group by parent
        specs_by_parent: dict[str, list[Path]] = {}
        all_spec_ids: set[str] = set()

        for spec_dir in sorted(self.specs_dir.iterdir()):
            if not spec_dir.is_dir() or spec_dir.name.startswith("."):
                continue

            plan_path = spec_dir / "implementation_plan.json"
            if not plan_path.exists():
                continue

            all_spec_ids.add(spec_dir.name)

            try:
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                parent = plan.get("parentTask") or plan.get("parent_task") or ""
                if parent:
                    specs_by_parent.setdefault(parent, []).append(spec_dir)
            except (json.JSONDecodeError, OSError):
                continue

        # Step 2: For each parent group, resolve dependencies
        repaired_count = 0

        for parent_id, siblings in specs_by_parent.items():
            # Build reference mapping for this group
            ref_to_actual: dict[str, str] = {}

            for i, spec_dir in enumerate(siblings):
                actual_id = spec_dir.name
                actual_slug = re.sub(r'^\d+-', '', actual_id).lower()

                # Common internal numbering patterns
                internal_num = i + 2  # parent=001, children start at 002
                batch_1based = i + 1

                # NOTE: Only 3-digit padded for internal_num ("002") and
                # unpadded for batch_1based ("1") to avoid key collisions.
                ref_to_actual[f"{internal_num:03d}"] = actual_id
                ref_to_actual[f"{batch_1based}"] = actual_id
                ref_to_actual[actual_id] = actual_id
                if actual_slug:
                    ref_to_actual[actual_slug] = actual_id

                # Also register NNN-slug derived from the spec's task description
                # for matching "002-backend-api" style refs
                req_path = spec_dir / "requirements.json"
                if req_path.exists():
                    try:
                        req = json.loads(req_path.read_text(encoding="utf-8"))
                        task = req.get("task", "")
                        task_slug = re.sub(r'[^a-z0-9\s-]', '', task.lower())
                        task_slug = re.sub(r'[\s_]+', '-', task_slug)
                        task_slug = re.sub(r'-+', '-', task_slug).strip('-')
                        if task_slug:
                            ref_to_actual[f"{internal_num:03d}-{task_slug}"] = actual_id
                    except (json.JSONDecodeError, OSError):
                        pass

            # Now resolve each sibling's dependsOn
            for spec_dir in siblings:
                plan_path = spec_dir / "implementation_plan.json"
                try:
                    plan = json.loads(plan_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue

                raw_deps = plan.get("dependsOn") or plan.get("depends_on") or []

                # Fix string-encoded arrays
                deps = self._normalize_list_field(raw_deps)

                # Check if any dep needs resolution (not already a valid spec ID)
                needs_repair = False
                resolved_deps = []

                for dep in deps:
                    dep = dep.strip()
                    if not dep:
                        continue

                    if dep in all_spec_ids:
                        # Already a valid spec ID
                        resolved_deps.append(dep)
                    else:
                        # Needs resolution
                        resolved = self._resolve_single_dep(
                            dep, ref_to_actual,
                            [s for s in siblings],  # pass as list of Paths
                        )
                        resolved_deps.append(resolved)
                        if resolved != dep:
                            needs_repair = True

                # Also check if format changed (string → array)
                if isinstance(raw_deps, str) and raw_deps != "[]":
                    needs_repair = True

                if needs_repair or (deps != resolved_deps):
                    plan["dependsOn"] = resolved_deps
                    plan["updated_at"] = datetime.now(timezone.utc).isoformat()
                    try:
                        plan_path.write_text(
                            json.dumps(plan, indent=2), encoding="utf-8"
                        )
                        repaired_count += 1
                    except OSError:
                        pass

        return repaired_count

    def get_spec_manifest(self, parent_spec_id: str) -> dict[str, Any]:
        """Get manifest of all child specs for a parent."""
        children = self.get_child_specs(parent_spec_id)

        manifest = {
            "parent_spec_id": parent_spec_id,
            "child_count": len(children),
            "children": [],
        }

        for spec_dir in children:
            plan_path = spec_dir / "implementation_plan.json"
            req_path = spec_dir / "requirements.json"

            child_info = {
                "spec_id": spec_dir.name,
                "spec_dir": str(spec_dir),
            }

            if plan_path.exists():
                try:
                    plan = json.loads(plan_path.read_text(encoding="utf-8"))
                    child_info["status"] = plan.get("status", "unknown")
                    child_info["priority"] = plan.get("priority", 2)
                    child_info["depends_on"] = plan.get("dependsOn") or plan.get("depends_on") or []
                    child_info["task_type"] = plan.get("taskType") or plan.get("task_type", "impl")
                except (json.JSONDecodeError, OSError):
                    pass

            if req_path.exists():
                try:
                    req = json.loads(req_path.read_text(encoding="utf-8"))
                    child_info["task"] = req.get("task", "")
                except (json.JSONDecodeError, OSError):
                    pass

            manifest["children"].append(child_info)

        return manifest


# Convenience function
def create_spec_factory(project_dir: str | Path) -> SpecFactory:
    """Create a SpecFactory instance."""
    return SpecFactory(Path(project_dir))
