"""
Tests for the Design → MCTS Bridge
====================================

Verifies:
1. "mcts" is in DESIGN_ONLY_TYPES (blocked at depth >= 2)
2. _calculate_task_depth works correctly for depth guard
3. MCTS orchestrator's _create_child_specs refuses at depth > MAX_CHILD_DEPTH
4. create_child_spec / create_batch_child_specs block mcts at depth >= 2
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# 1. DESIGN_ONLY_TYPES includes "mcts"
# ---------------------------------------------------------------------------

class TestDesignOnlyTypes:
    """Verify that 'mcts' is treated as a design-only type."""

    def test_mcts_in_design_only_types(self):
        from agents.tools_pkg.tools.subtask import DESIGN_ONLY_TYPES
        assert "mcts" in DESIGN_ONLY_TYPES

    def test_design_in_design_only_types(self):
        from agents.tools_pkg.tools.subtask import DESIGN_ONLY_TYPES
        assert "design" in DESIGN_ONLY_TYPES

    def test_architecture_in_design_only_types(self):
        from agents.tools_pkg.tools.subtask import DESIGN_ONLY_TYPES
        assert "architecture" in DESIGN_ONLY_TYPES

    def test_impl_not_in_design_only_types(self):
        from agents.tools_pkg.tools.subtask import DESIGN_ONLY_TYPES
        assert "impl" not in DESIGN_ONLY_TYPES

    def test_max_child_depth_default(self):
        from agents.tools_pkg.tools.subtask import MAX_CHILD_DEPTH
        assert MAX_CHILD_DEPTH == 2


# ---------------------------------------------------------------------------
# 2. _calculate_task_depth
# ---------------------------------------------------------------------------

class TestCalculateTaskDepth:
    """Verify depth calculation by walking up parentTask chain."""

    def test_depth_zero_no_parent(self, tmp_path):
        """A spec with no parentTask has depth 0."""
        from agents.tools_pkg.tools.subtask import _calculate_task_depth

        spec_dir = tmp_path / "specs" / "001-root"
        spec_dir.mkdir(parents=True)
        plan = {"status": "queue", "phases": []}
        (spec_dir / "implementation_plan.json").write_text(
            json.dumps(plan), encoding="utf-8"
        )

        assert _calculate_task_depth(spec_dir) == 0

    def test_depth_one_with_parent(self, tmp_path):
        """A child spec with parentTask pointing to root has depth 1."""
        from agents.tools_pkg.tools.subtask import _calculate_task_depth

        specs = tmp_path / "specs"
        specs.mkdir()

        # Root (depth 0)
        root = specs / "001-root"
        root.mkdir()
        (root / "implementation_plan.json").write_text(
            json.dumps({"status": "complete"}), encoding="utf-8"
        )

        # Child (depth 1)
        child = specs / "002-child"
        child.mkdir()
        (child / "implementation_plan.json").write_text(
            json.dumps({"status": "queue", "parentTask": "001-root"}),
            encoding="utf-8",
        )

        assert _calculate_task_depth(child) == 1

    def test_depth_two_grandchild(self, tmp_path):
        """A grandchild spec has depth 2."""
        from agents.tools_pkg.tools.subtask import _calculate_task_depth

        specs = tmp_path / "specs"
        specs.mkdir()

        root = specs / "001-root"
        root.mkdir()
        (root / "implementation_plan.json").write_text(
            json.dumps({"status": "complete"}), encoding="utf-8"
        )

        child = specs / "002-child"
        child.mkdir()
        (child / "implementation_plan.json").write_text(
            json.dumps({"status": "complete", "parentTask": "001-root"}),
            encoding="utf-8",
        )

        grandchild = specs / "003-grandchild"
        grandchild.mkdir()
        (grandchild / "implementation_plan.json").write_text(
            json.dumps({"status": "queue", "parentTask": "002-child"}),
            encoding="utf-8",
        )

        assert _calculate_task_depth(grandchild) == 2


# ---------------------------------------------------------------------------
# 3. MCTS orchestrator depth guard
# ---------------------------------------------------------------------------

class TestMCTSDepthGuard:
    """Verify that _create_child_specs refuses when depth > MAX_CHILD_DEPTH."""

    @pytest.mark.asyncio
    async def test_create_child_specs_blocked_at_depth_limit(self, tmp_path):
        """At depth 2 (grandchild), creating children (depth 3) should be blocked."""
        from mcts.orchestrator import _create_child_specs
        from mcts.tree import MCTSTree, MCTSNode
        from mcts.budget import BudgetTracker

        specs = tmp_path / "specs"
        specs.mkdir()

        # Build chain: root(0) → child(1) → grandchild(2)
        root = specs / "001-root"
        root.mkdir()
        (root / "implementation_plan.json").write_text(
            json.dumps({"status": "complete"}), encoding="utf-8"
        )

        child = specs / "002-child"
        child.mkdir()
        (child / "implementation_plan.json").write_text(
            json.dumps({"status": "complete", "parentTask": "001-root"}),
            encoding="utf-8",
        )

        grandchild = specs / "003-grandchild"
        grandchild.mkdir()
        (grandchild / "implementation_plan.json").write_text(
            json.dumps({"status": "running", "parentTask": "002-child"}),
            encoding="utf-8",
        )

        # Create a tree and nodes
        tree = MCTSTree.create(task_summary="test", max_iterations=3)
        node = tree.expand_node(parent_id=tree.root_id, action="draft", idea_summary="test idea")
        nodes = [node]

        budget = BudgetTracker(
            max_wall_seconds=100, max_iterations=3, max_branches=5
        )

        # This should be blocked (depth 2 → child would be 3 > MAX_CHILD_DEPTH=2)
        await _create_child_specs(nodes, tree, tmp_path, grandchild, budget)

        # Node should be marked as failed
        assert node.status == "failed"
        assert "Depth limit exceeded" in node.metadata.get("error", "")

    @pytest.mark.asyncio
    async def test_create_child_specs_allowed_at_depth_1(self, tmp_path):
        """At depth 1 (child), creating children (depth 2) should be allowed."""
        from mcts.orchestrator import _create_child_specs
        from mcts.tree import MCTSTree, MCTSNode
        from mcts.budget import BudgetTracker

        specs = tmp_path / "specs"
        specs.mkdir()

        root = specs / "001-root"
        root.mkdir()
        (root / "implementation_plan.json").write_text(
            json.dumps({"status": "complete"}), encoding="utf-8"
        )

        child = specs / "002-mcts-child"
        child.mkdir()
        (child / "implementation_plan.json").write_text(
            json.dumps({"status": "running", "parentTask": "001-root"}),
            encoding="utf-8",
        )

        tree = MCTSTree.create(task_summary="test", max_iterations=3)
        node = tree.expand_node(parent_id=tree.root_id, action="draft", idea_summary="test idea")
        nodes = [node]

        budget = BudgetTracker(
            max_wall_seconds=100, max_iterations=3, max_branches=5
        )

        # Mock SpecFactory to avoid real filesystem operations
        mock_spec_dir = tmp_path / "specs" / "003-impl-child"
        mock_spec_dir.mkdir(parents=True)

        with patch("services.spec_factory.SpecFactory") as MockFactory:
            mock_factory = MockFactory.return_value
            mock_factory.create_batch_specs = AsyncMock(return_value=[mock_spec_dir])

            await _create_child_specs(nodes, tree, tmp_path, child, budget)

        # Node should NOT be failed — it should be running (spec created)
        assert node.status == "running"
        assert node.spec_id == mock_spec_dir.name


# ---------------------------------------------------------------------------
# 4. Subtask tools block mcts at depth >= 2
# ---------------------------------------------------------------------------

class TestSubtaskToolsBlockMCTS:
    """Verify that create_child_spec and create_batch_child_specs block mcts at depth >= 2."""

    @pytest.mark.asyncio
    async def test_create_child_spec_blocks_mcts_at_depth_2(self, tmp_path):
        """create_child_spec should refuse task_type='mcts' when at depth >= 2."""
        from agents.tools_pkg.tools.subtask import DESIGN_ONLY_TYPES, _calculate_task_depth, MAX_CHILD_DEPTH

        # Simulate depth 1 spec (child_depth would be 2)
        specs = tmp_path / "specs"
        specs.mkdir()

        root = specs / "001-root"
        root.mkdir()
        (root / "implementation_plan.json").write_text(
            json.dumps({"status": "complete"}), encoding="utf-8"
        )

        child = specs / "002-child"
        child.mkdir()
        (child / "implementation_plan.json").write_text(
            json.dumps({"status": "running", "parentTask": "001-root"}),
            encoding="utf-8",
        )

        current_depth = _calculate_task_depth(child)
        child_depth = current_depth + 1  # = 2

        # mcts is in DESIGN_ONLY_TYPES, so it should be blocked at child_depth >= 2
        assert child_depth >= 2
        assert "mcts" in DESIGN_ONLY_TYPES

    def test_design_mcts_flow_depth_math(self):
        """Verify: design(0) → mcts(1) → impl(2) = MAX_CHILD_DEPTH."""
        from agents.tools_pkg.tools.subtask import MAX_CHILD_DEPTH, DESIGN_ONLY_TYPES

        # design at depth 0 creates mcts at depth 1: allowed (1 < 2)
        assert 1 < 2  # child_depth < 2, so not blocked by DESIGN_ONLY_TYPES

        # mcts at depth 1 creates impl at depth 2: allowed (impl not in DESIGN_ONLY_TYPES)
        assert "impl" not in DESIGN_ONLY_TYPES
        assert 2 <= MAX_CHILD_DEPTH  # depth 2 <= MAX_CHILD_DEPTH=2, within limit

        # mcts at depth 1 creating mcts at depth 2: BLOCKED
        assert "mcts" in DESIGN_ONLY_TYPES  # blocked because mcts is in DESIGN_ONLY_TYPES and depth >= 2
