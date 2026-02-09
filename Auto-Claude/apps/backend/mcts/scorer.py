"""
MCTS Branch Scorer
===================

Generic scoring for solution branches. Evaluates build success,
test pass rate, lint cleanliness, and QA approval.
Pure Python — no LLM calls.

Scoring weights:
    Build passed:    0.30
    Test pass rate:  0.30
    Lint clean:      0.10
    QA approved:     0.30
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BranchScore:
    """Quantitative score for a solution branch.

    Attributes:
        build_passed: Whether the build succeeded
        test_pass_rate: Fraction of tests passing (0.0 ~ 1.0)
        lint_clean: Whether lint passed without errors
        qa_approved: Whether QA reviewer approved
        subtask_completion: Fraction of subtasks completed (0.0 ~ 1.0)
        total: Normalized total score (0.0 ~ 1.0)
        breakdown: Per-criterion score details
    """

    build_passed: bool = False
    test_pass_rate: float = 0.0
    lint_clean: bool = False
    qa_approved: bool = False
    subtask_completion: float = 0.0
    total: float = 0.0
    breakdown: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "build_passed": self.build_passed,
            "test_pass_rate": self.test_pass_rate,
            "lint_clean": self.lint_clean,
            "qa_approved": self.qa_approved,
            "subtask_completion": self.subtask_completion,
            "total": self.total,
            "breakdown": self.breakdown,
        }


# Score weights
W_BUILD = 0.30
W_TEST = 0.30
W_LINT = 0.10
W_QA = 0.30


async def score_branch(spec_dir: Path, project_dir: Path) -> BranchScore:
    """Score a child spec's results.

    Reads implementation_plan.json for subtask completion,
    qa_report.md for QA status, and validator results if available.

    Args:
        spec_dir: Child spec directory
        project_dir: Project root directory

    Returns:
        BranchScore with total normalized to 0.0~1.0
    """
    score = BranchScore()
    breakdown: dict[str, Any] = {}

    # 1. Subtask completion from implementation_plan.json
    plan_path = spec_dir / "implementation_plan.json"
    if plan_path.exists():
        try:
            with open(plan_path, encoding="utf-8") as f:
                plan = json.load(f)
            score.subtask_completion = _calc_subtask_completion(plan)
            breakdown["subtask_completion"] = score.subtask_completion
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read plan for scoring: {e}")

    # 2. Build/lint/test from validator results
    validator_path = spec_dir / "validator_results.json"
    if validator_path.exists():
        try:
            with open(validator_path, encoding="utf-8") as f:
                results = json.load(f)
            _apply_validator_results(score, results, breakdown)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Failed to read validator results: {e}")
    else:
        # Fallback: infer from plan status
        if plan_path.exists():
            _infer_build_from_plan(score, plan_path, breakdown)

    # 3. QA approval from plan status or qa_report.md
    qa_report_path = spec_dir / "qa_report.md"
    if qa_report_path.exists():
        try:
            qa_text = qa_report_path.read_text(encoding="utf-8")
            score.qa_approved = _parse_qa_approval(qa_text)
            breakdown["qa_source"] = "qa_report.md"
        except OSError:
            pass
    elif plan_path.exists():
        try:
            with open(plan_path, encoding="utf-8") as f:
                plan = json.load(f)
            status = plan.get("status", "")
            score.qa_approved = status in ("done", "complete", "human_review")
            breakdown["qa_source"] = f"plan_status={status}"
        except (json.JSONDecodeError, OSError):
            pass

    # 4. Compute total
    score.total = _compute_total(score)
    score.breakdown = breakdown
    breakdown["total_formula"] = (
        f"{W_BUILD}*build + {W_TEST}*test + {W_LINT}*lint + {W_QA}*qa"
    )

    return score


def _calc_subtask_completion(plan: dict) -> float:
    """Calculate fraction of completed subtasks."""
    total = 0
    completed = 0

    for phase in plan.get("phases", []):
        for subtask in phase.get("subtasks", []):
            if isinstance(subtask, dict):
                total += 1
                if subtask.get("status") in ("completed", "done"):
                    completed += 1

    # Also check flat subtasks
    for subtask in plan.get("subtasks", []):
        if isinstance(subtask, dict):
            total += 1
            if subtask.get("status") in ("completed", "done"):
                completed += 1

    return completed / total if total > 0 else 0.0


def _apply_validator_results(
    score: BranchScore,
    results: list[dict[str, Any]] | dict[str, Any],
    breakdown: dict[str, Any],
) -> None:
    """Extract build/lint/test from validator results JSON."""
    # Handle both list format and dict-with-validators format
    validators: list[dict[str, Any]]
    if isinstance(results, list):
        validators = results
    elif isinstance(results, dict):
        validators = results.get("validators", results.get("results", []))
    else:
        return

    for v in validators:
        vid = v.get("validator_id", "")
        passed = v.get("passed", False)

        if vid == "build":
            # Build validator has sub-results for build/lint/test
            sub = v.get("sub_results", {})
            score.build_passed = sub.get("build", {}).get("passed", passed)
            score.lint_clean = sub.get("lint", {}).get("passed", False)

            test_result = sub.get("test", {})
            if test_result.get("passed"):
                score.test_pass_rate = 1.0
            elif "pass_rate" in test_result:
                score.test_pass_rate = test_result["pass_rate"]

            breakdown["build_validator"] = {
                "build": score.build_passed,
                "lint": score.lint_clean,
                "test_pass_rate": score.test_pass_rate,
            }
        elif vid == "browser":
            breakdown["browser_validator"] = {"passed": passed}
        elif vid == "api":
            breakdown["api_validator"] = {"passed": passed}


def _infer_build_from_plan(
    score: BranchScore,
    plan_path: Path,
    breakdown: dict[str, Any],
) -> None:
    """Infer build success from plan status when no validator results."""
    try:
        with open(plan_path, encoding="utf-8") as f:
            plan = json.load(f)
        status = plan.get("status", "")
        exec_phase = plan.get("executionPhase", "")

        # If we got past coding phase, build likely succeeded
        if exec_phase in ("qa_review", "qa_fixing", "complete"):
            score.build_passed = True
            score.lint_clean = True  # Assume if build passed
            breakdown["build_inferred_from"] = f"executionPhase={exec_phase}"
        elif status in ("done", "complete", "human_review"):
            score.build_passed = True
            score.lint_clean = True
            breakdown["build_inferred_from"] = f"status={status}"
    except (json.JSONDecodeError, OSError):
        pass


def _parse_qa_approval(qa_text: str) -> bool:
    """Parse QA report to determine if approved."""
    text_lower = qa_text.lower()
    # Check for explicit approval signals
    if "qa_approved" in text_lower or "approved" in text_lower:
        if "not approved" not in text_lower and "disapproved" not in text_lower:
            return True
    if "all acceptance criteria met" in text_lower:
        return True
    if "qa passed" in text_lower:
        return True
    return False


def _compute_total(score: BranchScore) -> float:
    """Compute weighted total score (0.0 ~ 1.0)."""
    total = 0.0
    total += W_BUILD * (1.0 if score.build_passed else 0.0)
    total += W_TEST * score.test_pass_rate
    total += W_LINT * (1.0 if score.lint_clean else 0.0)
    total += W_QA * (1.0 if score.qa_approved else 0.0)
    return min(total, 1.0)
