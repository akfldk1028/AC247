"""
MCTS Improver
==============

LLM agent wrapper that proposes targeted improvements to an existing solution.
Uses lessons from previous branches to suggest specific refinements.

Input:  Existing code summary + score + lessons
Output: Improvement plan dict {summary, changes, expected_score_delta}
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def propose_improvement(
    spec_content: str,
    node_summary: str,
    node_score: float,
    lessons: list[dict[str, Any]],
    project_dir: Path,
    model: str = "sonnet",
) -> dict[str, Any]:
    """Propose improvements for an existing solution branch.

    Args:
        spec_content: Original spec.md text
        node_summary: Summary of the branch being improved
        node_score: Current score of the branch (0.0~1.0)
        lessons: Extracted lessons from MCTS tree
        project_dir: Project root for cwd
        model: Claude model

    Returns:
        Improvement plan dict:
            - summary (str): One-line improvement summary
            - changes (list[str]): Specific changes to make
            - rationale (str): Why these changes will help
            - cited_lessons (list[str]): Lesson IDs referenced
            - expected_score_delta (float): Expected score improvement
    """
    from core.simple_client import create_simple_client

    prompt = _build_prompt(spec_content, node_summary, node_score, lessons)

    client = create_simple_client(
        agent_type="mcts_improver",
        model=model,
        cwd=project_dir,
        max_turns=3,
    )

    print(f"[MCTS] Proposing improvement for branch (score={node_score:.2f})...")

    try:
        async with client:
            from . import query_llm
            result = await query_llm(client, prompt)
        return _parse_improvement(result)
    except Exception as e:
        logger.error(f"Improvement proposal failed: {e}")
        return {
            "summary": f"Improve from score {node_score:.2f}",
            "changes": [],
            "rationale": f"Error: {e}",
            "cited_lessons": [],
            "expected_score_delta": 0.0,
        }


def _build_prompt(
    spec_content: str,
    node_summary: str,
    node_score: float,
    lessons: list[dict[str, Any]],
) -> str:
    parts = [
        "Propose targeted improvements for an existing solution branch.",
        "",
        "## Original Task",
        spec_content,
        "",
        "## Current Branch",
        f"- Summary: {node_summary}",
        f"- Score: {node_score:.2f} / 1.00",
        "",
    ]

    if lessons:
        parts.append("## Lessons Learned")
        for lesson in lessons:
            lid = lesson.get("id", "?")
            title = lesson.get("title", "")
            takeaway = lesson.get("key_takeaway", "")
            parts.append(f"- [{lid}] {title}: {takeaway}")
        parts.append("")
        parts.append("IMPORTANT: Cite relevant lessons by ID (e.g., 'Based on lesson_node_xxxx').")

    parts.append("")
    parts.append("Output a JSON object with: summary, changes, rationale, cited_lessons, expected_score_delta.")
    parts.append('Use ```json ... ``` code fence.')

    return "\n".join(parts)


def _parse_improvement(response: str) -> dict[str, Any]:
    """Parse improvement plan from LLM response."""
    text = _extract_json_block(response)

    try:
        plan = json.loads(text)
        if isinstance(plan, dict):
            return plan
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "summary": "Improvement plan (parse failed)",
        "changes": [],
        "rationale": response[:500],
        "cited_lessons": [],
        "expected_score_delta": 0.0,
    }


def _extract_json_block(text: str) -> str:
    """Extract JSON from a code fence, handling malformed fences gracefully."""
    try:
        if "```json" in text:
            start = text.index("```json") + 7
            end = text.index("```", start)
            return text[start:end].strip()
        if "```" in text:
            start = text.index("```") + 3
            end = text.index("```", start)
            return text[start:end].strip()
    except ValueError:
        pass
    return text
