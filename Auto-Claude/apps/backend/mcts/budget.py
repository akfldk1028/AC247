"""
MCTS Budget Tracker
====================

Tracks wall-clock time, iteration count, and branch count budgets.
Pure Python — no LLM calls.

Provides has_budget() check for the orchestrator's convergence loop
and budget_penalty() for UCB score adjustment.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BudgetTracker:
    """Tracks resource consumption against defined budgets.

    Attributes:
        max_wall_seconds: Total wall-clock time budget
        max_iterations: Maximum MCTS rounds
        max_branches: Maximum total branches (nodes)
        cost_penalty_weight: Exponent w for budget penalty in UCB

        spent_seconds: Wall-clock time consumed
        spent_iterations: Iterations completed
        spent_branches: Branches created
        spent_tokens: Total API tokens consumed
        start_time: When tracking started (epoch seconds)
    """

    max_wall_seconds: float = 3600.0
    max_iterations: int = 10
    max_branches: int = 20
    cost_penalty_weight: float = -0.07

    spent_seconds: float = 0.0
    spent_iterations: int = 0
    spent_branches: int = 0
    spent_tokens: int = 0
    start_time: float = field(default_factory=time.time)

    def has_budget(self) -> bool:
        """Check if any budget remains."""
        elapsed = time.time() - self.start_time
        if elapsed >= self.max_wall_seconds:
            return False
        if self.spent_iterations >= self.max_iterations:
            return False
        if self.spent_branches >= self.max_branches:
            return False
        return True

    def remaining_seconds(self) -> float:
        """Wall-clock seconds remaining."""
        elapsed = time.time() - self.start_time
        return max(0.0, self.max_wall_seconds - elapsed)

    def remaining_iterations(self) -> int:
        return max(0, self.max_iterations - self.spent_iterations)

    def remaining_branches(self) -> int:
        return max(0, self.max_branches - self.spent_branches)

    def record_iteration(self) -> None:
        """Record completion of one MCTS iteration."""
        self.spent_iterations += 1

    def record_branch(self, seconds: float = 0.0, tokens: int = 0) -> None:
        """Record creation/completion of one branch."""
        self.spent_branches += 1
        self.spent_seconds += seconds
        self.spent_tokens += tokens

    def compute_penalty(self, allocated: float, actual: float) -> float:
        """Compute budget-aware penalty for UCB.

        penalty = (allocated / actual) ^ w

        Args:
            allocated: Expected time allocation for this branch
            actual: Actual time consumed

        Returns:
            Penalty multiplier (< 1.0 if over budget)
        """
        if actual <= 0:
            return 1.0
        ratio = allocated / actual
        return ratio ** self.cost_penalty_weight

    def budget_summary(self) -> str:
        """Human-readable budget status."""
        elapsed = time.time() - self.start_time
        return (
            f"Time: {elapsed:.0f}s / {self.max_wall_seconds:.0f}s | "
            f"Iterations: {self.spent_iterations} / {self.max_iterations} | "
            f"Branches: {self.spent_branches} / {self.max_branches} | "
            f"Tokens: {self.spent_tokens:,}"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_wall_seconds": self.max_wall_seconds,
            "max_iterations": self.max_iterations,
            "max_branches": self.max_branches,
            "cost_penalty_weight": self.cost_penalty_weight,
            "spent_seconds": self.spent_seconds,
            "spent_iterations": self.spent_iterations,
            "spent_branches": self.spent_branches,
            "spent_tokens": self.spent_tokens,
            "start_time": self.start_time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BudgetTracker:
        return cls(
            max_wall_seconds=data.get("max_wall_seconds", 3600.0),
            max_iterations=data.get("max_iterations", 10),
            max_branches=data.get("max_branches", 20),
            cost_penalty_weight=data.get("cost_penalty_weight", -0.07),
            spent_seconds=data.get("spent_seconds", 0.0),
            spent_iterations=data.get("spent_iterations", 0),
            spent_branches=data.get("spent_branches", 0),
            spent_tokens=data.get("spent_tokens", 0),
            start_time=data.get("start_time", time.time()),
        )
