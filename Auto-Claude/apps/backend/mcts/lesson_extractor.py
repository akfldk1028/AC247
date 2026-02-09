"""
MCTS Lesson Extractor
======================

LLM agent wrapper that compares completed branches and extracts
structured lessons. Saves lessons to both the MCTS tree and Graphiti.

Input:  Completed branch diffs + scores
Output: List of Lesson dicts
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Lesson:
    """Structured lesson extracted from branch comparison.

    Attributes:
        id: Lesson identifier (e.g., "lesson_node_xxxxx")
        node_id: Source node ID
        title: Short lesson title
        summary: Detailed summary
        findings: Empirical findings
        key_takeaway: Core lesson
        detection_signals: Signals to detect similar situations
    """

    id: str
    node_id: str
    title: str = ""
    summary: str = ""
    findings: list[str] = field(default_factory=list)
    key_takeaway: str = ""
    detection_signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "title": self.title,
            "summary": self.summary,
            "findings": self.findings,
            "key_takeaway": self.key_takeaway,
            "detection_signals": self.detection_signals,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Lesson:
        return cls(
            id=data.get("id", ""),
            node_id=data.get("node_id", ""),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            findings=list(data.get("findings", [])),
            key_takeaway=data.get("key_takeaway", ""),
            detection_signals=list(data.get("detection_signals", [])),
        )


async def extract_lessons(
    completed_nodes: list[dict[str, Any]],
    spec_content: str,
    project_dir: Path,
    spec_dir: Path,
    model: str = "sonnet",
) -> list[Lesson]:
    """Compare completed branches and extract structured lessons.

    Args:
        completed_nodes: List of node dicts with id, idea_summary, score, status
        spec_content: Original spec.md text
        project_dir: Project root for cwd
        spec_dir: Parent spec directory for lesson storage
        model: Claude model

    Returns:
        List of Lesson objects
    """
    if len(completed_nodes) < 2:
        logger.info("Need at least 2 completed nodes for lesson extraction")
        return []

    from core.simple_client import create_simple_client

    prompt = _build_prompt(completed_nodes, spec_content)

    client = create_simple_client(
        agent_type="mcts_lesson_extractor",
        model=model,
        cwd=project_dir,
        max_turns=3,
    )

    print(f"[MCTS] Extracting lessons from {len(completed_nodes)} branches...")

    try:
        async with client:
            from . import query_llm
            result = await query_llm(client, prompt)
        lessons = _parse_lessons(result, completed_nodes)

        # Save lessons to spec_dir
        _save_lessons(lessons, spec_dir)

        return lessons
    except Exception as e:
        logger.error(f"Lesson extraction failed: {e}")
        print(f"[MCTS] Lesson extraction error: {e}")
        return []


def _build_prompt(
    completed_nodes: list[dict[str, Any]],
    spec_content: str,
) -> str:
    # Sort by score descending for comparison
    sorted_nodes = sorted(completed_nodes, key=lambda n: n.get("score", 0), reverse=True)

    parts = [
        "Compare the following solution branches and extract structured lessons.",
        "",
        "## Task",
        spec_content[:2000],  # Truncate long specs
        "",
        "## Completed Branches (sorted by score)",
    ]

    for node in sorted_nodes:
        status_emoji = "OK" if node.get("status") == "completed" else "FAIL"
        parts.append(
            f"- [{status_emoji}] {node.get('id', '?')} "
            f"(score={node.get('score', -1):.2f}, action={node.get('action', '?')}): "
            f"{node.get('idea_summary', 'no summary')}"
        )

    parts.append("")
    parts.append("## Instructions")
    parts.append("For each lesson:")
    parts.append("1. Compare what worked (high score) vs what didn't (low score)")
    parts.append("2. Extract specific, actionable findings")
    parts.append("3. Include detection_signals for recognizing similar situations")
    parts.append("")
    parts.append("Output a JSON array of lesson objects.")
    parts.append("Each lesson: {id, node_id, title, summary, findings, key_takeaway, detection_signals}.")
    parts.append("Use node IDs from the branches above. Use `lesson_<node_id>` for lesson IDs.")
    parts.append('Use ```json ... ``` code fence.')

    return "\n".join(parts)


def _parse_lessons(
    response: str,
    completed_nodes: list[dict[str, Any]],
) -> list[Lesson]:
    """Parse lessons from LLM response."""
    text = _extract_json_block(response)

    try:
        raw = json.loads(text)
        lessons_data = raw if isinstance(raw, list) else raw.get("lessons", [])
        return [Lesson.from_dict(ld) for ld in lessons_data if isinstance(ld, dict)]
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse lessons JSON")
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
        pass
    return text


def _save_lessons(lessons: list[Lesson], spec_dir: Path) -> None:
    """Persist lessons to spec_dir/mcts_lessons.json."""
    from core.file_utils import write_json_atomic

    filepath = spec_dir / "mcts_lessons.json"

    # Merge with existing lessons
    existing: list[dict[str, Any]] = []
    if filepath.exists():
        try:
            with open(filepath, encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    existing_ids = {l.get("id") for l in existing}
    for lesson in lessons:
        if lesson.id not in existing_ids:
            existing.append(lesson.to_dict())

    write_json_atomic(filepath, existing)
    print(f"[MCTS] Saved {len(lessons)} lessons to mcts_lessons.json")
