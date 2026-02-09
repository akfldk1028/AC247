"""
MCTS Orchestrator
==================

Main MCTS loop — pure Python orchestration (no direct LLM calls).
Delegates idea generation, improvement, debugging, and lesson extraction
to dedicated LLM agent wrappers.

Algorithm:
    1. INITIALIZE — load/create tree, load spec
    2. EXPAND    — generate initial ideas via idea_generator
    3. SIMULATE  — create child specs, wait for daemon to execute them
    4. EVALUATE  — score completed branches
    5. BACKPROPAGATE — propagate scores up the tree
    6. EXTRACT LESSONS — compare branches, extract insights
    7. SELECT    — UCB1 to pick next node to expand
    8. REPEAT    — until budget exhausted or converged
    9. FINALIZE  — select best branch, return result

Public API: run_mcts_search()
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.file_utils import write_json_atomic

from .budget import BudgetTracker
from .scorer import BranchScore, score_branch
from .tree import MCTSNode, MCTSTree

logger = logging.getLogger(__name__)


# =============================================================================
# Result Type
# =============================================================================


@dataclass
class MCTSResult:
    """Result of an MCTS search run.

    Attributes:
        success: Whether the search completed successfully
        best_node: The highest-scoring node
        best_score: Score of the best node
        best_spec_id: Spec ID of the best branch
        total_iterations: Number of MCTS rounds completed
        total_branches: Number of branches explored
        total_tokens: Total API tokens consumed
        tree: The final MCTS tree
        lessons: All extracted lessons
        summary: Human-readable summary
    """

    success: bool = False
    best_node: MCTSNode | None = None
    best_score: float = 0.0
    best_spec_id: str | None = None
    total_iterations: int = 0
    total_branches: int = 0
    total_tokens: int = 0
    tree: MCTSTree | None = None
    lessons: list[dict[str, Any]] = field(default_factory=list)
    summary: str = ""


# =============================================================================
# Constants
# =============================================================================

POLL_INTERVAL_SECONDS = 30  # How often to check child spec completion
MAX_POLL_WAIT_SECONDS = 1800  # Max wait for a single round (30 min)
MIN_SCORE_TO_ACCEPT = 0.7  # Early termination if score exceeds this
DEFAULT_N_IDEAS = 4  # Ideas to generate per expansion round


# =============================================================================
# Main Entry Point
# =============================================================================


async def run_mcts_search(
    project_dir: Path,
    spec_dir: Path,
    model: str = "sonnet",
    max_iterations: int = 10,
    max_branches: int = 20,
    max_concurrent: int = 3,
    budget_seconds: float = 3600.0,
    convergence_threshold: float = 0.02,
) -> MCTSResult:
    """Run MCTS multi-path search for the given spec.

    This is the main entry point. It manages the full MCTS loop:
    generate ideas → create child specs → wait for completion →
    score → backpropagate → extract lessons → select next → repeat.

    Child specs are created via SpecFactory and executed by the daemon.

    Args:
        project_dir: Project root directory
        spec_dir: Parent spec directory (contains spec.md)
        model: Claude model for LLM agent calls
        max_iterations: Maximum MCTS rounds
        max_branches: Maximum total branches
        max_concurrent: Max concurrent child specs (not used directly — daemon controls this)
        budget_seconds: Total wall-clock time budget
        convergence_threshold: Stop if best score delta < this

    Returns:
        MCTSResult with the best branch and search metadata
    """
    print("[MCTS] ═══════════════════════════════════════════════════")
    print("[MCTS] Starting MCTS Multi-Path Search")
    print(f"[MCTS] Max iterations: {max_iterations}, Max branches: {max_branches}")
    print(f"[MCTS] Budget: {budget_seconds:.0f}s, Convergence: {convergence_threshold}")
    print("[MCTS] ═══════════════════════════════════════════════════")

    # 1. INITIALIZE
    spec_content = _load_spec_content(spec_dir)
    if not spec_content:
        print("[MCTS] ERROR: No spec.md found")
        return MCTSResult(success=False, summary="No spec.md found")

    tree = MCTSTree.load(spec_dir)
    if tree:
        print(f"[MCTS] Resuming from existing tree ({len(tree.nodes)} nodes, "
              f"{tree.total_iterations} iterations)")
    else:
        tree = MCTSTree.create(
            task_summary=spec_content[:200],
            max_iterations=max_iterations,
            budget_seconds=budget_seconds,
            convergence_threshold=convergence_threshold,
        )
        print("[MCTS] Created new search tree")

    budget = BudgetTracker(
        max_wall_seconds=budget_seconds,
        max_iterations=max_iterations,
        max_branches=max_branches,
        start_time=tree.created_at,
        spent_iterations=tree.total_iterations,
        spent_branches=max(len(tree.nodes) - 1, 0),  # Exclude root
    )

    # Load existing lessons
    all_lessons = _load_lessons(spec_dir)

    # 2. MAIN LOOP
    prev_best_score = tree.best_node.score if tree.best_node else 0.0

    while budget.has_budget():
        iteration = budget.spent_iterations + 1
        print(f"\n[MCTS] ─── Round {iteration} / {max_iterations} ───")
        print(f"[MCTS] {budget.budget_summary()}")

        round_start = time.time()

        # Heartbeat for daemon liveness detection
        print(f"[MCTS] Heartbeat: round {iteration} starting")

        # ── EXPAND: Generate new branches ──
        new_nodes = await _expand_round(
            tree, spec_content, all_lessons, project_dir, spec_dir, model, budget,
        )

        if not new_nodes:
            print("[MCTS] No new branches generated, stopping")
            break

        # ── SIMULATE: Wait for daemon to execute child specs ──
        print(f"[MCTS] Waiting for {len(new_nodes)} branches to complete...")
        await _wait_for_completion(new_nodes, tree, spec_dir, project_dir)

        # ── EVALUATE + BACKPROPAGATE ──
        for node in new_nodes:
            if node.status in ("completed", "failed", "bug"):
                child_spec_dir = _resolve_child_spec_dir(node, project_dir)
                if child_spec_dir and child_spec_dir.exists():
                    score_result = await score_branch(child_spec_dir, project_dir)
                    node.metadata["score_breakdown"] = score_result.to_dict()
                    tree.backpropagate(node.id, score_result.total)  # Sets node.score
                    print(f"[MCTS]   {node.id}: score={score_result.total:.2f} "
                          f"(build={score_result.build_passed}, "
                          f"test={score_result.test_pass_rate:.1%}, "
                          f"qa={score_result.qa_approved})")
                else:
                    tree.backpropagate(node.id, 0.0)  # Sets node.score = 0.0
                    print(f"[MCTS]   {node.id}: score=0.00 (spec dir not found)")

        # ── EXTRACT LESSONS ──
        completed = tree.get_completed_nodes()
        if len(completed) >= 2:
            from .lesson_extractor import extract_lessons
            node_dicts = [n.to_dict() for n in completed]
            new_lessons = await extract_lessons(
                node_dicts, spec_content, project_dir, spec_dir, model,
            )
            for lesson in new_lessons:
                lesson_dict = lesson.to_dict()
                all_lessons.append(lesson_dict)
                # Attach to source node
                source_node = tree.get_node(lesson.node_id)
                if source_node:
                    source_node.lessons.append(lesson_dict)

        # ── UPDATE STATE ──
        round_seconds = time.time() - round_start
        budget.record_iteration()
        tree.total_iterations = budget.spent_iterations
        tree.spent_budget_seconds += round_seconds
        tree.save(spec_dir)

        # ── CONVERGENCE CHECK ──
        current_best = tree.best_node.score if tree.best_node else 0.0
        score_delta = abs(current_best - prev_best_score)
        prev_best_score = current_best

        print(f"[MCTS] Best score: {current_best:.2f} (delta={score_delta:.3f})")

        if current_best >= MIN_SCORE_TO_ACCEPT:
            print(f"[MCTS] Score {current_best:.2f} >= {MIN_SCORE_TO_ACCEPT}, accepting")
            break

        if iteration > 1 and score_delta < convergence_threshold:
            print(f"[MCTS] Converged (delta {score_delta:.3f} < {convergence_threshold})")
            break

        # Heartbeat
        print(f"[MCTS] Heartbeat: round {iteration} complete")

    # 3. FINALIZE
    tree.save(spec_dir)
    best = tree.best_node
    result = MCTSResult(
        success=best is not None and (best.score if best else 0) > 0,
        best_node=best,
        best_score=best.score if best else 0.0,
        best_spec_id=best.spec_id if best else None,
        total_iterations=tree.total_iterations,
        total_branches=len(tree.nodes) - 1,
        total_tokens=budget.spent_tokens,
        tree=tree,
        lessons=all_lessons,
        summary=_build_summary(tree, budget),
    )

    print("\n[MCTS] ═══════════════════════════════════════════════════")
    print(f"[MCTS] Search complete: {result.summary}")
    print("[MCTS] ═══════════════════════════════════════════════════")

    return result


# =============================================================================
# Expansion Logic
# =============================================================================


async def _expand_round(
    tree: MCTSTree,
    spec_content: str,
    lessons: list[dict[str, Any]],
    project_dir: Path,
    spec_dir: Path,
    model: str,
    budget: BudgetTracker,
) -> list[MCTSNode]:
    """Expand the tree with new branches for this round.

    Round 1: Generate initial ideas (draft nodes from root)
    Round N: Select via UCB, then improve or debug
    """
    new_nodes: list[MCTSNode] = []

    if tree.total_iterations == 0:
        # ── First round: generate diverse ideas ──
        from .idea_generator import generate_ideas

        n_ideas = min(DEFAULT_N_IDEAS, budget.remaining_branches())
        ideas = await generate_ideas(
            spec_content, project_dir, n_ideas=n_ideas,
            past_lessons=lessons, model=model,
        )

        for idea in ideas:
            summary = idea.get("summary", "Unknown approach")
            node = tree.expand_node(
                parent_id=tree.root_id,
                action="draft",
                idea_summary=summary,
            )
            node.metadata["idea"] = idea
            new_nodes.append(node)

    else:
        # ── Subsequent rounds: UCB selection + improve/debug ──
        remaining = min(3, budget.remaining_branches())

        # Try debugging failed nodes first
        failed_nodes = tree.get_failed_nodes()
        for fnode in failed_nodes[:1]:  # Debug at most 1 failed node per round
            if remaining <= 0:
                break
            from .debugger import analyze_failure

            error_output = fnode.metadata.get("error", "Unknown error")
            debug_plan = await analyze_failure(
                spec_content, fnode.idea_summary, error_output,
                spec_dir, project_dir, model,
            )

            if debug_plan.get("retry_viable", False):
                child = tree.expand_node(
                    parent_id=fnode.id,
                    action="debug",
                    idea_summary=f"Fix: {debug_plan.get('fix_direction', 'retry')[:100]}",
                )
                child.metadata["debug_plan"] = debug_plan
                new_nodes.append(child)
                remaining -= 1

        # Improve best branches
        selected = tree.select_node()
        if selected and selected.is_expandable and remaining > 0:
            from .improver import propose_improvement

            improvement = await propose_improvement(
                spec_content, selected.idea_summary, selected.score,
                lessons, project_dir, model,
            )

            child = tree.expand_node(
                parent_id=selected.id,
                action="improve",
                idea_summary=improvement.get("summary", "Improvement")[:200],
            )
            child.metadata["improvement_plan"] = improvement
            new_nodes.append(child)
            remaining -= 1

    # Create child specs for all new nodes
    if new_nodes:
        await _create_child_specs(new_nodes, tree, project_dir, spec_dir, budget)

    return new_nodes


async def _create_child_specs(
    nodes: list[MCTSNode],
    tree: MCTSTree,
    project_dir: Path,
    spec_dir: Path,
    budget: BudgetTracker,
) -> None:
    """Create child specs for new MCTS nodes via SpecFactory."""
    from agents.tools_pkg.tools.subtask import _calculate_task_depth, MAX_CHILD_DEPTH

    # Depth guard: prevent creating child specs beyond MAX_CHILD_DEPTH
    current_depth = _calculate_task_depth(spec_dir)
    child_depth = current_depth + 1
    if child_depth > MAX_CHILD_DEPTH:
        print(f"[MCTS] Depth limit reached ({child_depth} > {MAX_CHILD_DEPTH}), cannot create child specs")
        for node in nodes:
            node.status = "failed"
            node.metadata["error"] = f"Depth limit exceeded (depth={child_depth}, max={MAX_CHILD_DEPTH})"
        tree.save(spec_dir)
        return

    from services.spec_factory import SpecFactory

    factory = SpecFactory(project_dir)
    parent_spec_id = spec_dir.name

    specs_data: list[dict[str, Any]] = []
    for node in nodes:
        task_desc = _build_child_task_description(node)
        specs_data.append({
            "task": task_desc,
            "priority": 2,  # NORMAL
            "task_type": "impl",
            "complexity": "standard",
            "context": {
                "mcts_node_id": node.id,
                "mcts_action": node.action,
                "mcts_parent_spec": parent_spec_id,
            },
        })

    created_dirs = await factory.create_batch_specs(parent_spec_id, specs_data)

    # Link spec IDs back to nodes
    for node, created_dir in zip(nodes, created_dirs):
        node.spec_id = created_dir.name
        node.status = "running"
        budget.record_branch()
        print(f"[MCTS] Created child spec: {created_dir.name} → {node.id}")

    tree.save(spec_dir)


def _build_child_task_description(node: MCTSNode) -> str:
    """Build task description for a child spec from an MCTS node."""
    parts = [node.idea_summary]

    if node.action == "improve" and "improvement_plan" in node.metadata:
        plan = node.metadata["improvement_plan"]
        if plan.get("changes"):
            parts.append("\n\nRequired changes:")
            for change in plan["changes"]:
                parts.append(f"- {change}")
        if plan.get("rationale"):
            parts.append(f"\nRationale: {plan['rationale']}")
        if plan.get("cited_lessons"):
            parts.append(f"\nBased on lessons: {', '.join(plan['cited_lessons'])}")

    elif node.action == "debug" and "debug_plan" in node.metadata:
        plan = node.metadata["debug_plan"]
        if plan.get("root_cause"):
            parts.append(f"\n\nRoot cause: {plan['root_cause']}")
        if plan.get("fix_direction"):
            parts.append(f"Fix direction: {plan['fix_direction']}")
        if plan.get("changes"):
            parts.append("\nChanges:")
            for change in plan["changes"]:
                parts.append(f"- {change}")

    elif node.action == "draft" and "idea" in node.metadata:
        idea = node.metadata["idea"]
        if idea.get("strategy"):
            parts.append(f"\n\nStrategy: {idea['strategy']}")

    return "\n".join(parts)


# =============================================================================
# Completion Waiting
# =============================================================================


async def _wait_for_completion(
    nodes: list[MCTSNode],
    tree: MCTSTree,
    spec_dir: Path,
    project_dir: Path,
) -> None:
    """Poll child spec status until all nodes are terminal or timeout."""
    start = time.time()
    pending = {n.id for n in nodes if n.status == "running"}

    while pending and (time.time() - start) < MAX_POLL_WAIT_SECONDS:
        await asyncio.sleep(POLL_INTERVAL_SECONDS)

        # Heartbeat
        elapsed = time.time() - start
        print(f"[MCTS] Heartbeat: waiting for {len(pending)} branches "
              f"({elapsed:.0f}s elapsed)")

        for node_id in list(pending):
            node = tree.get_node(node_id)
            if not node or not node.spec_id:
                pending.discard(node_id)
                continue

            child_spec_dir = _resolve_child_spec_dir(node, project_dir)
            if not child_spec_dir or not child_spec_dir.exists():
                continue

            plan_path = child_spec_dir / "implementation_plan.json"
            if not plan_path.exists():
                continue

            try:
                with open(plan_path, encoding="utf-8") as f:
                    plan = json.load(f)
                status = plan.get("status", "")

                if status in ("done", "complete", "human_review"):
                    node.status = "completed"
                    node.cost_seconds = time.time() - start
                    pending.discard(node_id)
                    print(f"[MCTS] Branch {node_id} completed (status={status})")
                elif status in ("error", "failed"):
                    node.status = "failed"
                    node.metadata["error"] = plan.get("lastError", "Unknown error")
                    pending.discard(node_id)
                    print(f"[MCTS] Branch {node_id} failed (status={status})")
            except (json.JSONDecodeError, OSError):
                continue

        tree.save(spec_dir)

    # Mark remaining as failed (timeout)
    for node_id in pending:
        node = tree.get_node(node_id)
        if node:
            node.status = "failed"
            node.metadata["error"] = "Timeout waiting for completion"
            print(f"[MCTS] Branch {node_id} timed out")


def _resolve_child_spec_dir(node: MCTSNode, project_dir: Path) -> Path | None:
    """Resolve the spec directory for a child node."""
    if not node.spec_id:
        return None
    return project_dir / ".auto-claude" / "specs" / node.spec_id


# =============================================================================
# Utilities
# =============================================================================


def _load_spec_content(spec_dir: Path) -> str:
    """Load spec.md content."""
    spec_path = Path(spec_dir) / "spec.md"
    if spec_path.exists():
        try:
            return spec_path.read_text(encoding="utf-8")
        except OSError:
            pass
    return ""


def _load_lessons(spec_dir: Path) -> list[dict[str, Any]]:
    """Load existing lessons from mcts_lessons.json."""
    lessons_path = Path(spec_dir) / "mcts_lessons.json"
    if lessons_path.exists():
        try:
            with open(lessons_path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _build_summary(tree: MCTSTree, budget: BudgetTracker) -> str:
    """Build human-readable search summary."""
    best = tree.best_node
    if best:
        return (
            f"Best: {best.idea_summary[:80]} (score={best.score:.2f}), "
            f"{tree.total_iterations} rounds, "
            f"{len(tree.nodes) - 1} branches, "
            f"{budget.budget_summary()}"
        )
    return f"No viable solution found after {tree.total_iterations} rounds"
