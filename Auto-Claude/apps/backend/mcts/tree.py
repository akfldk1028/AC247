"""
MCTS Tree Data Structures
===========================

Core data structures for Monte Carlo Tree Search: MCTSNode and MCTSTree.
Pure Python — no LLM calls. All other MCTS modules depend on this.

Node lifecycle: pending → running → completed | failed | bug
Tree persistence: spec_dir/mcts_tree.json via write_json_atomic().
Resume support: load from JSON and continue from where we left off.
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.file_utils import write_json_atomic


# =============================================================================
# MCTSNode
# =============================================================================


@dataclass
class MCTSNode:
    """One node in the MCTS tree. Represents a single solution attempt.

    Attributes:
        id: Unique node identifier (e.g., "node_00001")
        parent_id: Parent node ID (None for root)
        spec_id: Child spec ID created for this node (e.g., "003-idea-caching")
        action: How this node was created ("root" | "draft" | "debug" | "improve")
        idea_summary: One-line summary of the approach
        score: Evaluation score (-1.0 = unevaluated, 0.0~1.0 = evaluated)
        visit_count: Number of times this node was visited (for UCB)
        status: Node lifecycle status
        cost_seconds: Wall-clock time spent
        cost_tokens: API tokens consumed
        children: List of child node IDs
        lessons: Extracted lessons from this branch
        metadata: Free-form metadata
    """

    id: str
    parent_id: str | None = None
    spec_id: str | None = None
    action: str = "root"  # root | draft | debug | improve
    idea_summary: str = ""
    score: float = -1.0  # -1.0 = unevaluated
    visit_count: int = 0
    status: str = "pending"  # pending | running | completed | failed | bug
    cost_seconds: float = 0.0
    cost_tokens: int = 0
    children: list[str] = field(default_factory=list)
    lessons: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_evaluated(self) -> bool:
        return self.score >= 0.0

    @property
    def is_terminal(self) -> bool:
        return self.status in ("completed", "failed", "bug")

    @property
    def is_expandable(self) -> bool:
        return self.status == "completed" and self.is_evaluated

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "parent_id": self.parent_id,
            "spec_id": self.spec_id,
            "action": self.action,
            "idea_summary": self.idea_summary,
            "score": self.score,
            "visit_count": self.visit_count,
            "status": self.status,
            "cost_seconds": self.cost_seconds,
            "cost_tokens": self.cost_tokens,
            "children": list(self.children),
            "lessons": list(self.lessons),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCTSNode:
        return cls(
            id=data["id"],
            parent_id=data.get("parent_id"),
            spec_id=data.get("spec_id"),
            action=data.get("action", "root"),
            idea_summary=data.get("idea_summary", ""),
            score=data.get("score", -1.0),
            visit_count=data.get("visit_count", 0),
            status=data.get("status", "pending"),
            cost_seconds=data.get("cost_seconds", 0.0),
            cost_tokens=data.get("cost_tokens", 0),
            children=list(data.get("children", [])),
            lessons=list(data.get("lessons", [])),
            metadata=dict(data.get("metadata", {})),
        )


def _generate_node_id() -> str:
    """Generate a unique node ID."""
    short_uuid = uuid.uuid4().hex[:8]
    return f"node_{short_uuid}"


# =============================================================================
# MCTSTree
# =============================================================================


@dataclass
class MCTSTree:
    """Full MCTS tree with UCB selection, backpropagation, and persistence.

    Attributes:
        root_id: ID of the root node
        nodes: All nodes indexed by ID
        best_node_id: Current best scoring node
        total_budget_seconds: Total wall-clock budget
        spent_budget_seconds: Budget consumed so far
        total_iterations: Iterations completed
        max_iterations: Maximum iterations allowed
        convergence_threshold: Score delta below which we stop
        exploration_constant: UCB exploration constant C
        cost_penalty_weight: Budget penalty exponent w
        created_at: Tree creation timestamp
    """

    root_id: str
    nodes: dict[str, MCTSNode] = field(default_factory=dict)
    best_node_id: str | None = None
    total_budget_seconds: float = 3600.0
    spent_budget_seconds: float = 0.0
    total_iterations: int = 0
    max_iterations: int = 10
    convergence_threshold: float = 0.02
    exploration_constant: float = 1.414  # sqrt(2)
    cost_penalty_weight: float = -0.07
    created_at: float = field(default_factory=time.time)

    @property
    def root(self) -> MCTSNode:
        return self.nodes[self.root_id]

    @property
    def best_node(self) -> MCTSNode | None:
        if self.best_node_id and self.best_node_id in self.nodes:
            return self.nodes[self.best_node_id]
        return None

    # ── Node Management ──

    def add_node(self, node: MCTSNode) -> None:
        """Add a node to the tree."""
        self.nodes[node.id] = node
        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            if node.id not in parent.children:
                parent.children.append(node.id)

    def get_node(self, node_id: str) -> MCTSNode | None:
        return self.nodes.get(node_id)

    def get_children(self, node_id: str) -> list[MCTSNode]:
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[cid] for cid in node.children if cid in self.nodes]

    # ── UCB Selection ──

    def select_node(self) -> MCTSNode:
        """Select the best node to expand using UCB1 formula.

        UCB(v) = Q(v)/N(v) + C * sqrt(ln(N_parent) / N(v)) * budget_penalty(v)

        Returns the leaf node with highest UCB score. If no expandable
        leaves exist, returns the root.
        """
        best_ucb = float("-inf")
        best_node = self.root

        for node in self.nodes.values():
            if not node.is_expandable:
                continue

            ucb = self._compute_ucb(node)
            if ucb > best_ucb:
                best_ucb = ucb
                best_node = node

        return best_node

    def _compute_ucb(self, node: MCTSNode) -> float:
        """Compute UCB1 score for a node.

        node.score is the actual branch score (not cumulative), so
        exploitation = score directly (no division by visit_count).
        """
        if node.visit_count == 0:
            return float("inf")  # Unvisited → highest priority

        # Exploitation: node.score is already the evaluated score (0.0~1.0)
        exploitation = node.score

        # Exploration: UCB exploration term
        parent = self.nodes.get(node.parent_id) if node.parent_id else None
        parent_visits = parent.visit_count if parent else self.total_iterations
        parent_visits = max(parent_visits, 1)

        exploration = self.exploration_constant * math.sqrt(
            math.log(parent_visits) / node.visit_count
        )

        # Budget penalty: penalize nodes that took too long
        penalty = self._compute_budget_penalty(node)

        return exploitation + exploration * penalty

    def _compute_budget_penalty(self, node: MCTSNode) -> float:
        """Compute budget-aware penalty for a node.

        penalty = (allocated / actual) ^ w, where w = -0.07
        Nodes that used more time than allocated get penalized.
        """
        if node.cost_seconds <= 0:
            return 1.0

        # Allocate budget equally across max branches
        total_branches = max(len(self.nodes) - 1, 1)  # Exclude root
        allocated = self.total_budget_seconds / total_branches
        actual = node.cost_seconds

        if actual <= 0:
            return 1.0

        ratio = allocated / actual
        return ratio ** self.cost_penalty_weight

    # ── Tree Operations ──

    def expand_node(
        self,
        parent_id: str,
        action: str,
        idea_summary: str,
        spec_id: str | None = None,
    ) -> MCTSNode:
        """Create a new child node under the given parent.

        Args:
            parent_id: Parent node to expand from
            action: "draft" | "debug" | "improve"
            idea_summary: One-line idea description
            spec_id: Child spec ID (filled after spec creation)

        Returns:
            The newly created child node
        """
        node = MCTSNode(
            id=_generate_node_id(),
            parent_id=parent_id,
            action=action,
            idea_summary=idea_summary,
            spec_id=spec_id,
        )
        self.add_node(node)
        return node

    def backpropagate(self, node_id: str, score: float) -> None:
        """Propagate visit_count from a leaf node up to the root.

        Only increments visit_count on ancestors — does NOT overwrite
        their score. Each node's score is set exactly once by the scorer.
        Also updates best_node_id if this leaf has a higher score.
        """
        # Set the leaf's score directly (scorer already computed it)
        leaf = self.nodes.get(node_id)
        if leaf:
            leaf.score = score
            leaf.visit_count += 1

        # Walk up ancestors: increment visit_count only
        current_id = leaf.parent_id if leaf else None
        while current_id and current_id in self.nodes:
            node = self.nodes[current_id]
            node.visit_count += 1
            current_id = node.parent_id

        # Update best node (compare actual branch scores, not averages)
        if leaf and leaf.is_evaluated:
            if self.best_node_id is None:
                self.best_node_id = node_id
            else:
                current_best = self.nodes.get(self.best_node_id)
                if current_best is None or score > current_best.score:
                    self.best_node_id = node_id

    def get_best_path(self) -> list[MCTSNode]:
        """Get the path from root to the best scoring node."""
        if not self.best_node_id or self.best_node_id not in self.nodes:
            return [self.root]

        path: list[MCTSNode] = []
        current_id: str | None = self.best_node_id
        while current_id and current_id in self.nodes:
            path.append(self.nodes[current_id])
            current_id = self.nodes[current_id].parent_id

        path.reverse()
        return path

    def get_completed_nodes(self) -> list[MCTSNode]:
        """Get all completed (evaluated) non-root nodes."""
        return [
            n for n in self.nodes.values()
            if n.id != self.root_id and n.is_terminal and n.is_evaluated
        ]

    def get_pending_nodes(self) -> list[MCTSNode]:
        """Get all nodes that are pending or running."""
        return [
            n for n in self.nodes.values()
            if n.status in ("pending", "running")
        ]

    def get_failed_nodes(self) -> list[MCTSNode]:
        """Get all failed nodes that haven't been debugged."""
        return [
            n for n in self.nodes.values()
            if n.status in ("failed", "bug") and not any(
                self.nodes.get(cid) and self.nodes[cid].action == "debug"
                for cid in n.children
            )
        ]

    # ── Serialization ──

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_id": self.root_id,
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "best_node_id": self.best_node_id,
            "total_budget_seconds": self.total_budget_seconds,
            "spent_budget_seconds": self.spent_budget_seconds,
            "total_iterations": self.total_iterations,
            "max_iterations": self.max_iterations,
            "convergence_threshold": self.convergence_threshold,
            "exploration_constant": self.exploration_constant,
            "cost_penalty_weight": self.cost_penalty_weight,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MCTSTree:
        nodes = {
            nid: MCTSNode.from_dict(ndata)
            for nid, ndata in data.get("nodes", {}).items()
        }
        return cls(
            root_id=data["root_id"],
            nodes=nodes,
            best_node_id=data.get("best_node_id"),
            total_budget_seconds=data.get("total_budget_seconds", 3600.0),
            spent_budget_seconds=data.get("spent_budget_seconds", 0.0),
            total_iterations=data.get("total_iterations", 0),
            max_iterations=data.get("max_iterations", 10),
            convergence_threshold=data.get("convergence_threshold", 0.02),
            exploration_constant=data.get("exploration_constant", 1.414),
            cost_penalty_weight=data.get("cost_penalty_weight", -0.07),
            created_at=data.get("created_at", time.time()),
        )

    # ── Persistence ──

    def save(self, spec_dir: Path) -> None:
        """Persist tree to spec_dir/mcts_tree.json atomically."""
        filepath = Path(spec_dir) / "mcts_tree.json"
        write_json_atomic(filepath, self.to_dict())

    @classmethod
    def load(cls, spec_dir: Path) -> MCTSTree | None:
        """Load tree from spec_dir/mcts_tree.json. Returns None if not found."""
        import json

        filepath = Path(spec_dir) / "mcts_tree.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, OSError):
            return None

    # ── Factory ──

    @classmethod
    def create(
        cls,
        task_summary: str,
        max_iterations: int = 10,
        budget_seconds: float = 3600.0,
        convergence_threshold: float = 0.02,
    ) -> MCTSTree:
        """Create a new MCTS tree with a root node.

        Args:
            task_summary: One-line summary of the task being searched
            max_iterations: Maximum MCTS iterations
            budget_seconds: Total wall-clock budget in seconds
            convergence_threshold: Score delta below which we stop

        Returns:
            A new MCTSTree with a root node
        """
        root = MCTSNode(
            id=_generate_node_id(),
            action="root",
            idea_summary=task_summary,
            status="completed",  # Root is always "completed"
            score=0.0,
        )
        tree = cls(
            root_id=root.id,
            nodes={root.id: root},
            max_iterations=max_iterations,
            total_budget_seconds=budget_seconds,
            convergence_threshold=convergence_threshold,
        )
        return tree
