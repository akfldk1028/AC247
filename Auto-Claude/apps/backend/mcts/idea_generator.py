"""
MCTS Idea Generator
====================

LLM agent wrapper that generates N diverse solution approaches for a task.
Calls mcts_idea_generator agent via create_simple_client.

Input:  spec.md content + past lessons + Graphiti similar tasks
Output: List of idea dicts [{summary, strategy, pros, cons}, ...]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def generate_ideas(
    spec_content: str,
    project_dir: Path,
    n_ideas: int = 5,
    past_lessons: list[dict[str, Any]] | None = None,
    similar_tasks: list[dict[str, Any]] | None = None,
    model: str = "sonnet",
) -> list[dict[str, Any]]:
    """Generate N diverse solution ideas for the given spec.

    Args:
        spec_content: Full spec.md text
        project_dir: Project root for cwd
        n_ideas: Number of ideas to generate
        past_lessons: Previously extracted MCTS lessons
        model: Claude model to use

    Returns:
        List of idea dicts with keys:
            - summary (str): One-line idea summary
            - strategy (str): Implementation approach
            - pros (list[str]): Expected advantages
            - cons (list[str]): Expected disadvantages
            - estimated_complexity (str): "simple" | "standard" | "complex"
    """
    from core.simple_client import create_simple_client

    prompt = _build_prompt(spec_content, n_ideas, past_lessons, similar_tasks)

    client = create_simple_client(
        agent_type="mcts_idea_generator",
        model=model,
        cwd=project_dir,
        max_turns=3,
    )

    print(f"[MCTS] Generating {n_ideas} solution ideas...")

    try:
        async with client:
            from . import query_llm
            result = await query_llm(client, prompt)
        return _parse_ideas(result, n_ideas)
    except Exception as e:
        logger.error(f"Idea generation failed: {e}")
        print(f"[MCTS] Idea generation error: {e}")
        return []


def _build_prompt(
    spec_content: str,
    n_ideas: int,
    past_lessons: list[dict[str, Any]] | None,
    similar_tasks: list[dict[str, Any]] | None,
) -> str:
    parts = [
        f"Generate exactly {n_ideas} diverse solution approaches for the following task.",
        "",
        "## Task Specification",
        spec_content,
    ]

    if past_lessons:
        parts.append("")
        parts.append("## Lessons from Previous Attempts")
        for lesson in past_lessons:
            lid = lesson.get("id", "?")
            title = lesson.get("title", "")
            summary = lesson.get("summary", "")
            parts.append(f"- [{lid}] {title}: {summary}")

    if similar_tasks:
        parts.append("")
        parts.append("## Similar Past Tasks")
        for task in similar_tasks[:5]:
            parts.append(f"- {task.get('summary', str(task))}")

    parts.append("")
    parts.append(f"Output EXACTLY {n_ideas} ideas as a JSON array.")
    parts.append("Each idea must have: summary, strategy, pros, cons, estimated_complexity.")
    parts.append('Use ```json ... ``` code fence.')

    return "\n".join(parts)


def _parse_ideas(response: str, n_ideas: int) -> list[dict[str, Any]]:
    """Parse LLM response into structured idea list."""
    text = _extract_json_block(response)

    try:
        ideas = json.loads(text)
        if isinstance(ideas, list):
            return ideas[:n_ideas]
        if isinstance(ideas, dict) and "ideas" in ideas:
            return ideas["ideas"][:n_ideas]
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse ideas JSON")

    return []


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
        pass  # Malformed code fence — no closing backticks
    return text
