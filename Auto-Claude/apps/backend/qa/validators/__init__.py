"""
QA Validators (n8n-Pattern Architecture)
==========================================

Independent validator modules that each check one aspect of quality.
Each validator is an n8n node: clear inputs (context dict), clear outputs
(ValidatorResult), self-contained logic.

Validators are selected based on project capabilities (detected from
project_index.json). They run independently — build validator first,
then runtime validators in parallel.

Usage:
    from qa.validator_orchestrator import run_validators
    from qa.validators import ValidatorResult

    results = await run_validators(project_dir, spec_dir, capabilities)
    for r in results:
        print(f"{r.validator_id}: {'PASS' if r.passed else 'FAIL'}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidatorResult:
    """Output of a single validator — the n8n wire between nodes.

    Attributes:
        validator_id: Which validator produced this result
        passed: Whether validation passed
        issues: List of issue dicts [{severity, description, file, line}, ...]
        screenshots: File paths to captured screenshots
        report_section: Markdown section for qa_report.md
        metadata: Additional validator-specific data
    """

    validator_id: str
    passed: bool = True
    issues: list[dict] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    report_section: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to serializable dict."""
        return {
            "validator_id": self.validator_id,
            "passed": self.passed,
            "issues": self.issues,
            "screenshots": self.screenshots,
            "report_section": self.report_section,
            "metadata": self.metadata,
        }


class BaseValidator:
    """Base class for all validators.

    Subclasses implement validate() which receives a context dict
    and returns a ValidatorResult.

    Attributes:
        id: Unique validator identifier
        description: Human-readable description
        capability_trigger: Capability key that activates this validator
        validation_doc: Prompt file name in prompts/mcp_tools/
    """

    id: str = ""
    description: str = ""
    capability_trigger: str = ""
    validation_doc: str = ""

    async def validate(self, ctx: dict) -> ValidatorResult:
        """Run validation and return structured result.

        Args:
            ctx: Context dict with:
                - project_dir (Path): Project root
                - spec_dir (Path): Spec directory
                - capabilities (dict): From detect_project_capabilities()
                - model (str): Claude model name
                - verbose (bool): Verbose output

        Returns:
            ValidatorResult with pass/fail and issues
        """
        raise NotImplementedError(f"{self.__class__.__name__}.validate() not implemented")

    def is_applicable(self, capabilities: dict) -> bool:
        """Check if this validator should run for the given project capabilities."""
        if not self.capability_trigger:
            return True  # Always applicable if no trigger
        return bool(capabilities.get(self.capability_trigger, False))
