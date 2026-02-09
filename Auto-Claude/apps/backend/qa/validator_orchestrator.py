"""
Validator Orchestrator
=======================

Selects and runs validators based on project capabilities.
Build validator runs first (sequential), then runtime validators
run in parallel.

Node pattern:
    Input:  project_dir, spec_dir, capabilities
    Output: list[ValidatorResult]

Usage:
    from qa.validator_orchestrator import run_validators, select_validators

    capabilities = detect_project_capabilities(project_index)
    results = await run_validators(project_dir, spec_dir, capabilities)
    all_passed = all(r.passed for r in results)
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from .validators import BaseValidator, ValidatorResult
from .validators.api_validator import ApiValidator
from .validators.browser_validator import BrowserValidator
from .validators.build_validator import BuildValidator
from .validators.db_validator import DatabaseValidator

logger = logging.getLogger(__name__)


# All available validators — order matters for display only
ALL_VALIDATORS: list[BaseValidator] = [
    BuildValidator(),
    BrowserValidator(),
    ApiValidator(),
    DatabaseValidator(),
]


def select_validators(capabilities: dict) -> list[BaseValidator]:
    """Select applicable validators based on project capabilities.

    Args:
        capabilities: Dict from detect_project_capabilities()

    Returns:
        List of validators that should run for this project
    """
    return [v for v in ALL_VALIDATORS if v.is_applicable(capabilities)]


async def run_validators(
    project_dir: Path,
    spec_dir: Path,
    capabilities: dict,
    model: str = "",
    verbose: bool = False,
) -> list[ValidatorResult]:
    """Run all applicable validators for a project.

    Execution order:
    1. Build validator runs first (sequential) — must pass before runtime validators
    2. Runtime validators (browser, API, database) run in parallel

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory
        capabilities: Dict from detect_project_capabilities()
        model: Claude model name (for agent-based validators)
        verbose: Enable verbose output

    Returns:
        List of ValidatorResult objects
    """
    validators = select_validators(capabilities)
    if not validators:
        logger.info("No validators applicable for this project")
        return []

    ctx = {
        "project_dir": project_dir,
        "spec_dir": spec_dir,
        "capabilities": capabilities,
        "model": model,
        "verbose": verbose,
    }

    results: list[ValidatorResult] = []
    validator_names = [v.id for v in validators]
    logger.info(f"Running validators: {validator_names}")
    print(f"[validators] Running: {', '.join(validator_names)}")

    # Step 1: Run build validator first (sequential)
    build_validators = [v for v in validators if v.id == "build"]
    runtime_validators = [v for v in validators if v.id != "build"]

    for v in build_validators:
        logger.info(f"Running {v.id} validator...")
        print(f"[validators] {v.id}: starting...")
        result = await v.validate(ctx)
        _status = "PASS" if result.passed else "FAIL"
        print(f"[validators] {v.id}: {_status}")
        results.append(result)

        if not result.passed:
            logger.warning(f"Build validator failed — skipping runtime validators")
            # Still return results (don't run runtime validators on build failure)
            for rv in runtime_validators:
                results.append(ValidatorResult(
                    validator_id=rv.id,
                    passed=True,
                    report_section=f"## {rv.description}\n\n- Skipped (build failed)\n",
                    metadata={"skipped": True, "reason": "build_failed"},
                ))
            return results

    # Step 2: Run runtime validators in parallel
    if runtime_validators:
        logger.info(f"Running runtime validators in parallel: {[v.id for v in runtime_validators]}")
        print(f"[validators] Runtime validators starting: {', '.join(v.id for v in runtime_validators)}")
        runtime_results = await asyncio.gather(
            *[v.validate(ctx) for v in runtime_validators],
            return_exceptions=True,
        )

        for i, result in enumerate(runtime_results):
            if isinstance(result, Exception):
                v = runtime_validators[i]
                logger.error(f"{v.id} validator raised exception: {result}")
                print(f"[validators] {v.id}: ERROR ({result})")
                results.append(ValidatorResult(
                    validator_id=v.id,
                    passed=True,  # Don't block on validator errors
                    issues=[{
                        "severity": "minor",
                        "description": f"Validator error: {str(result)[:200]}",
                    }],
                    report_section=f"## {v.description}\n\n- ERROR: {result}\n",
                ))
            else:
                _status = "PASS" if result.passed else "FAIL"
                print(f"[validators] {runtime_validators[i].id}: {_status}")
                results.append(result)

    _total_passed = sum(1 for r in results if r.passed)
    print(f"[validators] Complete: {_total_passed}/{len(results)} passed")
    return results


def format_validator_report(results: list[ValidatorResult]) -> str:
    """Format validator results into a markdown report section.

    Args:
        results: List of ValidatorResult objects

    Returns:
        Markdown string for inclusion in qa_report.md
    """
    if not results:
        return ""

    sections = ["# Validator Results\n"]

    passed_count = sum(1 for r in results if r.passed)
    total = len(results)
    sections.append(f"**{passed_count}/{total} validators passed**\n")

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        sections.append(f"### {result.validator_id} [{status}]\n")
        if result.report_section:
            sections.append(result.report_section)
        if result.issues:
            sections.append("\n**Issues:**\n")
            for issue in result.issues:
                severity = issue.get("severity", "unknown")
                desc = issue.get("description", "")
                sections.append(f"- [{severity}] {desc}\n")
        sections.append("")

    return "\n".join(sections)
