"""
MCTS Debugger
==============

LLM agent wrapper that analyzes failed branches and proposes fix directions.
Reads error logs and code to determine root cause.

Input:  Failed branch error output + code context
Output: Debug plan dict {root_cause, fix_direction, changes}
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def analyze_failure(
    spec_content: str,
    node_summary: str,
    error_output: str,
    spec_dir: Path,
    project_dir: Path,
    model: str = "sonnet",
) -> dict[str, Any]:
    """Analyze a failed branch and propose fix direction.

    Args:
        spec_content: Original spec.md text
        node_summary: Summary of the failed branch
        error_output: Error logs or failure output
        spec_dir: Spec directory of the failed branch
        project_dir: Project root for cwd
        model: Claude model

    Returns:
        Debug plan dict:
            - root_cause (str): Root cause analysis
            - fix_direction (str): Proposed fix approach
            - changes (list[str]): Specific changes to make
            - severity (str): "minor" | "major" | "fundamental"
            - retry_viable (bool): Whether retrying with fixes is viable
    """
    from core.simple_client import create_simple_client

    prompt = _build_prompt(spec_content, node_summary, error_output)

    client = create_simple_client(
        agent_type="mcts_debugger",
        model=model,
        cwd=project_dir,
        max_turns=3,
    )

    print(f"[MCTS] Analyzing failure for branch: {node_summary[:60]}...")

    try:
        async with client:
            from . import query_llm
            result = await query_llm(client, prompt)
        return _parse_debug_plan(result)
    except Exception as e:
        logger.error(f"Failure analysis failed: {e}")
        return {
            "root_cause": f"Analysis error: {e}",
            "fix_direction": "Manual investigation needed",
            "changes": [],
            "severity": "major",
            "retry_viable": False,
        }


def _build_prompt(
    spec_content: str,
    node_summary: str,
    error_output: str,
) -> str:
    # Truncate very long error output
    max_error_len = 3000
    if len(error_output) > max_error_len:
        error_output = error_output[:max_error_len] + "\n... (truncated)"

    parts = [
        "Analyze the root cause of a failed solution attempt and propose a fix direction.",
        "",
        "## Original Task",
        spec_content,
        "",
        "## Failed Branch",
        f"- Approach: {node_summary}",
        "",
        "## Error Output",
        "```",
        error_output,
        "```",
        "",
        "Output a JSON object with: root_cause, fix_direction, changes, severity, retry_viable.",
        'Use ```json ... ``` code fence.',
    ]
    return "\n".join(parts)


def _parse_debug_plan(response: str) -> dict[str, Any]:
    """Parse debug plan from LLM response."""
    text = _extract_json_block(response)

    try:
        plan = json.loads(text)
        if isinstance(plan, dict):
            return plan
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "root_cause": "Parse failed",
        "fix_direction": response[:500],
        "changes": [],
        "severity": "major",
        "retry_viable": False,
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
