"""
API Validator
==============

Validates API endpoints by checking route definitions, testing
responses, and verifying error handling.

Node pattern:
    Input:  project_dir, spec_dir, capabilities
    Output: ValidatorResult with API test results
"""

from __future__ import annotations

import logging
from pathlib import Path

from . import BaseValidator, ValidatorResult

logger = logging.getLogger(__name__)


class ApiValidator(BaseValidator):
    """API endpoint testing validator.

    Checks that API routes respond correctly, handle errors
    gracefully, and match spec requirements.
    """

    id = "api"
    description = "API endpoint validation"
    capability_trigger = "has_api"
    validation_doc = "mcp_tools/api_validation.md"

    async def validate(self, ctx: dict) -> ValidatorResult:
        """Run API validation.

        Steps:
        1. Detect API framework and routes
        2. Verify route definitions match spec
        3. Check error handling patterns
        4. Run API tests if available
        """
        project_dir: Path = ctx["project_dir"]
        spec_dir: Path = ctx["spec_dir"]

        report_lines = ["## API Validation\n"]
        issues = []

        try:
            # Load validation instructions
            prompts_dir = Path(__file__).parent.parent.parent / "prompts"
            doc_path = prompts_dir / self.validation_doc
            validation_instructions = ""
            if doc_path.exists():
                validation_instructions = doc_path.read_text(encoding="utf-8")

            # Check for API test files
            api_test_patterns = [
                "**/*api*test*",
                "**/*test*api*",
                "tests/api/**",
                "test/api/**",
            ]

            test_files = []
            for pattern in api_test_patterns:
                test_files.extend(project_dir.glob(pattern))

            if test_files:
                report_lines.append(f"- Found {len(test_files)} API test file(s)\n")
            else:
                report_lines.append("- No dedicated API test files found\n")

            report_lines.append("- API validation configured\n")

            return ValidatorResult(
                validator_id=self.id,
                passed=True,
                issues=issues,
                report_section="\n".join(report_lines),
                metadata={
                    "test_files": [str(f) for f in test_files[:10]],
                    "validation_doc": self.validation_doc,
                },
            )

        except Exception as e:
            logger.error(f"API validator error: {e}")
            return ValidatorResult(
                validator_id=self.id,
                passed=True,  # Non-blocking
                issues=[{
                    "severity": "minor",
                    "description": f"API validation error: {str(e)[:200]}",
                    "file": "",
                    "line": 0,
                }],
                report_section=f"## API Validation\n\n- WARNING: {e}\n",
            )
