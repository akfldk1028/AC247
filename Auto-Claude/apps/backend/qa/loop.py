"""
QA Validation Loop Orchestration
=================================

Main QA loop that coordinates reviewer and fixer sessions until
approval or max iterations.
"""

import os
import time as time_module
from pathlib import Path

from core.client import create_client
from core.task_event import TaskEventEmitter
from debug import debug, debug_error, debug_section, debug_success, debug_warning
from linear_updater import (
    LinearTaskState,
    is_linear_enabled,
    linear_qa_approved,
    linear_qa_max_iterations,
    linear_qa_rejected,
    linear_qa_started,
)
from phase_config import get_phase_model, get_phase_thinking_budget
from phase_event import ExecutionPhase, emit_phase
from progress import count_subtasks, is_build_complete
from security.constants import PROJECT_DIR_ENV_VAR
from task_logger import (
    LogPhase,
    get_task_logger,
)

from .criteria import (
    get_qa_iteration_count,
    get_qa_signoff_status,
    is_qa_approved,
)
from .fixer import run_qa_fixer_session
from .report import (
    create_manual_test_plan,
    escalate_to_human,
    get_iteration_history,
    get_recurring_issue_summary,
    has_recurring_issues,
    is_no_test_project,
    record_iteration,
)
from .reviewer import review_with_results, run_qa_agent_session

# Lazy imports for Graphiti memory (avoid startup cost when disabled)
_is_graphiti_enabled = None
_get_graphiti_memory = None

# Lazy import for project index refresh
_analyze_project = None

# Lazy import for worktree sync
_sync_spec_to_source = None


def _sync_to_source(spec_dir: Path, source_spec_dir: Path | None) -> None:
    """Sync spec files from worktree to main project (no-op if not in worktree)."""
    if not source_spec_dir:
        return
    global _sync_spec_to_source
    if _sync_spec_to_source is None:
        from agents.utils import sync_spec_to_source as _ss
        _sync_spec_to_source = _ss
    try:
        _sync_spec_to_source(spec_dir, source_spec_dir)
    except Exception as e:
        debug_warning("qa_loop", f"Failed to sync spec to source: {e}")

# Configuration
MAX_QA_ITERATIONS = 50
MAX_CONSECUTIVE_ERRORS = 3  # Stop after 3 consecutive errors without progress


async def _save_qa_outcome(
    spec_dir: Path,
    project_dir: Path,
    success: bool,
    qa_iteration: int,
    issues: list[dict] | None = None,
) -> None:
    """Save QA outcome to Graphiti for cross-task learning (non-blocking)."""
    try:
        global _is_graphiti_enabled, _get_graphiti_memory
        if _is_graphiti_enabled is None:
            from graphiti_config import is_graphiti_enabled
            _is_graphiti_enabled = is_graphiti_enabled
        if not _is_graphiti_enabled():
            return

        if _get_graphiti_memory is None:
            from memory.graphiti_helpers import get_graphiti_memory
            _get_graphiti_memory = get_graphiti_memory

        memory = await _get_graphiti_memory(spec_dir, project_dir)
        if not memory:
            return
        try:
            spec_desc = ""
            spec_file = spec_dir / "spec.md"
            if spec_file.exists():
                spec_desc = spec_file.read_text(encoding="utf-8")[:500]
            if success:
                outcome = f"QA approved after {qa_iteration} iteration(s)"
            else:
                issue_titles = [i.get("title", "") for i in (issues or [])[:5]]
                outcome = f"QA failed after {qa_iteration} iterations: {', '.join(issue_titles)}"
            await memory.save_task_outcome(
                task_id=spec_dir.name,
                success=success,
                outcome=outcome,
                metadata={"spec_description": spec_desc, "iterations": qa_iteration},
            )
        finally:
            await memory.close()
    except Exception as e:
        debug_warning("qa_loop", f"Failed to save QA outcome to Graphiti: {e}")


# =============================================================================
# QA VALIDATION LOOP
# =============================================================================


async def run_qa_validation_loop(
    project_dir: Path,
    spec_dir: Path,
    model: str,
    verbose: bool = False,
    source_spec_dir: Path | None = None,
) -> bool:
    """
    Run the full QA validation loop.

    This is the self-validating loop:
    1. QA Agent reviews
    2. If rejected → Fixer Agent fixes
    3. QA Agent re-reviews
    4. Loop until approved or max iterations

    Enhanced with:
    - Iteration tracking with detailed history
    - Recurring issue detection (3+ occurrences → human escalation)
    - No-test project handling

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory
        model: Claude model to use
        verbose: Whether to show detailed output
        source_spec_dir: Original spec directory in main project (for worktree sync).
                         When running in isolated workspace, events and plan updates
                         are written to the worktree spec dir. This parameter enables
                         syncing back to the main project so the daemon/UI can see
                         QA progress in real-time.

    Returns:
        True if QA approved, False otherwise
    """
    # Set environment variable for security hooks to find the correct project directory
    # This is needed because os.getcwd() may return the wrong directory in worktree mode
    os.environ[PROJECT_DIR_ENV_VAR] = str(project_dir.resolve())
    task_event_emitter = TaskEventEmitter.from_spec_dir(spec_dir)

    debug_section("qa_loop", "QA Validation Loop")
    debug(
        "qa_loop",
        "Starting QA validation loop",
        project_dir=str(project_dir),
        spec_dir=str(spec_dir),
        model=model,
        max_iterations=MAX_QA_ITERATIONS,
    )

    print("\n" + "=" * 70)
    print("  QA VALIDATION LOOP")
    print("  Self-validating quality assurance")
    print("=" * 70)

    # Initialize task logger for the validation phase
    task_logger = get_task_logger(spec_dir)

    # Verify build is complete
    if not is_build_complete(spec_dir):
        debug_warning("qa_loop", "Build is not complete, cannot run QA")
        print("\n❌ Build is not complete. Cannot run QA validation.")
        completed, total = count_subtasks(spec_dir)
        debug("qa_loop", "Build progress", completed=completed, total=total)
        print(f"   Progress: {completed}/{total} subtasks completed")
        return False

    # Emit phase event at start of QA validation (before any early returns)
    emit_phase(ExecutionPhase.QA_REVIEW, "Starting QA validation")
    task_event_emitter.emit(
        "QA_STARTED",
        {"iteration": 1, "maxIterations": MAX_QA_ITERATIONS},
    )

    # Sync to main project so daemon/UI can see QA has started
    _sync_to_source(spec_dir, source_spec_dir)

    # Refresh project_index.json before QA starts — the coder may have created
    # new directories (e.g. web/ for Flutter) that change project capabilities
    try:
        from prompts_pkg.project_context import should_refresh_project_index

        if should_refresh_project_index(project_dir):
            debug("qa_loop", "Refreshing project_index.json (dependency files changed)")
            global _analyze_project
            if _analyze_project is None:
                from analysis.analyzers import analyze_project as _ap
                _analyze_project = _ap
            index_file = project_dir / ".auto-claude" / "project_index.json"
            _analyze_project(project_dir, index_file)
            debug_success("qa_loop", "project_index.json refreshed")
    except Exception as e:
        debug_warning("qa_loop", f"Failed to refresh project index: {e}")

    # Check if there's pending human feedback that needs to be processed
    fix_request_file = spec_dir / "QA_FIX_REQUEST.md"
    has_human_feedback = fix_request_file.exists()

    # Check if already approved - but if there's human feedback, we need to process it first
    if is_qa_approved(spec_dir) and not has_human_feedback:
        debug_success("qa_loop", "Build already approved by QA")
        print("\n✅ Build already approved by QA.")
        task_event_emitter.emit(
            "QA_PASSED",
            {"iteration": 0, "testsRun": {}},
        )
        return True

    # If there's human feedback, we need to run the fixer first before re-validating
    if has_human_feedback:
        debug(
            "qa_loop",
            "Human feedback detected - will run fixer first",
            fix_request_file=str(fix_request_file),
        )
        emit_phase(ExecutionPhase.QA_FIXING, "Processing human feedback")
        task_event_emitter.emit(
            "QA_FIXING_STARTED",
            {"iteration": 0},
        )
        print("\n📝 Human feedback detected. Running QA Fixer first...")

        # Get model and thinking budget for fixer (uses QA phase config)
        qa_model = get_phase_model(spec_dir, "qa", model)
        fixer_thinking_budget = get_phase_thinking_budget(spec_dir, "qa")

        fix_client = create_client(
            project_dir,
            spec_dir,
            qa_model,
            agent_type="qa_fixer",
            max_thinking_tokens=fixer_thinking_budget,
        )

        async with fix_client:
            fix_status, fix_response = await run_qa_fixer_session(
                fix_client,
                spec_dir,
                0,
                False,  # iteration 0 for human feedback
            )

        if fix_status == "error":
            debug_error("qa_loop", f"Fixer error: {fix_response[:200]}")
            print(f"\n❌ Fixer encountered error: {fix_response}")
            return False

        debug_success("qa_loop", "Human feedback fixes applied")
        task_event_emitter.emit(
            "QA_FIXING_COMPLETE",
            {"iteration": 0},
        )
        print("\n✅ Fixes applied based on human feedback. Running QA validation...")

        # Remove the fix request file after processing
        try:
            fix_request_file.unlink()
            debug("qa_loop", "Removed processed QA_FIX_REQUEST.md")
        except OSError:
            pass  # Ignore if file removal fails

    # Check for no-test projects
    if is_no_test_project(spec_dir, project_dir):
        print("\n⚠️  No test framework detected in project.")
        print("Creating manual test plan...")
        manual_plan = create_manual_test_plan(spec_dir, spec_dir.name)
        print(f"📝 Manual test plan created: {manual_plan}")
        print("\nNote: Automated testing will be limited for this project.")

    # Start validation phase in task logger
    if task_logger:
        task_logger.start_phase(LogPhase.VALIDATION, "Starting QA validation...")

    # Check Linear integration status
    linear_task = None
    if is_linear_enabled():
        linear_task = LinearTaskState.load(spec_dir)
        if linear_task and linear_task.task_id:
            print(f"Linear task: {linear_task.task_id}")
            # Update Linear to "In Review" when QA starts
            await linear_qa_started(spec_dir)
            print("Linear task moved to 'In Review'")

    # Run automated validators before the QA review loop (first iteration only).
    # Results are injected into the first reviewer session as structured evidence.
    validator_results = None
    try:
        from prompts_pkg.project_context import detect_project_capabilities
        import json as _json

        _idx_file = project_dir / ".auto-claude" / "project_index.json"
        if _idx_file.exists():
            _idx = _json.loads(_idx_file.read_text(encoding="utf-8"))
            _caps = detect_project_capabilities(_idx)
            if _caps:
                from .validator_orchestrator import run_validators
                debug("qa_loop", "Running automated validators before QA review", capabilities=list(_caps.keys()))
                print(f"[qa] Running automated validators (capabilities: {', '.join(k for k, v in _caps.items() if v)})")
                validator_results = await run_validators(project_dir, spec_dir, _caps)
                _passed = sum(1 for r in validator_results if r.passed)
                print(f"[qa] Validators done: {_passed}/{len(validator_results)} passed")
                debug_success("qa_loop", f"Validators complete: {_passed}/{len(validator_results)} passed")
                # Sync screenshots/validator artifacts to main spec dir immediately
                # (browser_validator saves to worktree spec_dir which is deleted after merge)
                _sync_to_source(spec_dir, source_spec_dir)
    except Exception as e:
        debug_warning("qa_loop", f"Validator pre-run failed (non-blocking): {e}")
        validator_results = None

    qa_iteration = get_qa_iteration_count(spec_dir)
    consecutive_errors = 0
    last_error_context = None  # Track error for self-correction feedback
    max_iterations_emitted = False
    first_loop_iteration = True  # For validator injection on first pass

    while qa_iteration < MAX_QA_ITERATIONS:
        qa_iteration += 1
        iteration_start = time_module.time()

        debug_section("qa_loop", f"QA Iteration {qa_iteration}")
        debug(
            "qa_loop",
            f"Starting iteration {qa_iteration}/{MAX_QA_ITERATIONS}",
            iteration=qa_iteration,
            max_iterations=MAX_QA_ITERATIONS,
        )

        print(f"\n--- QA Iteration {qa_iteration}/{MAX_QA_ITERATIONS} ---")
        emit_phase(
            ExecutionPhase.QA_REVIEW, f"Running QA review iteration {qa_iteration}"
        )

        # Run QA reviewer with phase-specific model and thinking budget
        qa_model = get_phase_model(spec_dir, "qa", model)
        qa_thinking_budget = get_phase_thinking_budget(spec_dir, "qa")
        debug(
            "qa_loop",
            "Creating client for QA reviewer session...",
            model=qa_model,
            thinking_budget=qa_thinking_budget,
        )
        client = create_client(
            project_dir,
            spec_dir,
            qa_model,
            agent_type="qa_reviewer",
            max_thinking_tokens=qa_thinking_budget,
        )

        async with client:
            debug("qa_loop", "Running QA reviewer agent session...")
            # First iteration with validator results → use review_with_results()
            if validator_results is not None and first_loop_iteration:
                debug("qa_loop", "Using review_with_results() with pre-computed validator evidence")
                status, response = await review_with_results(
                    client,
                    project_dir,
                    spec_dir,
                    validator_results,
                    qa_iteration,
                    MAX_QA_ITERATIONS,
                    verbose,
                )
                # Clear so subsequent iterations use standard path
                validator_results = None
            else:
                status, response = await run_qa_agent_session(
                    client,
                    project_dir,  # Pass project_dir for capability-based tool injection
                    spec_dir,
                    qa_iteration,
                    MAX_QA_ITERATIONS,
                    verbose,
                    previous_error=last_error_context,  # Pass error context for self-correction
                )
            first_loop_iteration = False

        iteration_duration = time_module.time() - iteration_start
        debug(
            "qa_loop",
            "QA reviewer session completed",
            status=status,
            duration_seconds=f"{iteration_duration:.1f}",
            response_length=len(response),
        )

        # Sync after every reviewer session so daemon/UI sees real-time QA progress
        _sync_to_source(spec_dir, source_spec_dir)

        if status == "approved":
            emit_phase(ExecutionPhase.COMPLETE, "QA validation passed")
            # Reset error tracking on success
            consecutive_errors = 0
            last_error_context = None

            # Record successful iteration
            debug_success(
                "qa_loop",
                "QA APPROVED",
                iteration=qa_iteration,
                duration=f"{iteration_duration:.1f}s",
            )
            record_iteration(spec_dir, qa_iteration, "approved", [], iteration_duration)
            qa_status = get_qa_signoff_status(spec_dir) or {}
            task_event_emitter.emit(
                "QA_PASSED",
                {
                    "iteration": qa_iteration,
                    "testsRun": qa_status.get("tests_passed", {}),
                },
            )

            print("\n" + "=" * 70)
            print("  ✅ QA APPROVED")
            print("=" * 70)
            print("\nAll acceptance criteria verified.")
            print("The implementation is production-ready.")
            print("\nNext steps:")
            print("  1. Review the auto-claude/* branch")
            print("  2. Create a PR and merge to main")

            # End validation phase successfully
            if task_logger:
                task_logger.end_phase(
                    LogPhase.VALIDATION,
                    success=True,
                    message="QA validation passed - all criteria met",
                )

            # Update Linear: QA approved, awaiting human review
            if linear_task and linear_task.task_id:
                await linear_qa_approved(spec_dir)
                print("\nLinear: Task marked as QA approved, awaiting human review")

            # Save approved outcome to Graphiti for cross-task learning
            await _save_qa_outcome(spec_dir, project_dir, True, qa_iteration)

            # Sync approved state to main project
            _sync_to_source(spec_dir, source_spec_dir)
            return True

        elif status == "rejected":
            # Reset error tracking on valid response (rejected is a valid response)
            consecutive_errors = 0
            last_error_context = None

            debug_warning(
                "qa_loop",
                "QA REJECTED",
                iteration=qa_iteration,
                duration=f"{iteration_duration:.1f}s",
            )
            print(f"\n❌ QA found issues. Iteration {qa_iteration}/{MAX_QA_ITERATIONS}")

            # Get issues from QA report
            qa_status = get_qa_signoff_status(spec_dir)
            current_issues = qa_status.get("issues_found", []) if qa_status else []
            debug(
                "qa_loop",
                "Issues found by QA",
                issue_count=len(current_issues),
                issues=current_issues[:3] if current_issues else [],  # Show first 3
            )
            task_event_emitter.emit(
                "QA_FAILED",
                {
                    "iteration": qa_iteration,
                    "issueCount": len(current_issues),
                    "issues": [
                        issue.get("title", "")
                        for issue in (current_issues[:5] if current_issues else [])
                    ],
                },
            )

            # Check for recurring issues BEFORE recording current iteration
            # This prevents the current issues from matching themselves in history
            history = get_iteration_history(spec_dir)
            has_recurring, recurring_issues = has_recurring_issues(
                current_issues, history
            )

            # Record rejected iteration AFTER checking for recurring issues
            record_iteration(
                spec_dir, qa_iteration, "rejected", current_issues, iteration_duration
            )

            if has_recurring:
                from .report import RECURRING_ISSUE_THRESHOLD

                debug_error(
                    "qa_loop",
                    "Recurring issues detected - escalating to human",
                    recurring_count=len(recurring_issues),
                    threshold=RECURRING_ISSUE_THRESHOLD,
                )
                print(
                    f"\n⚠️  Recurring issues detected ({len(recurring_issues)} issue(s) appeared {RECURRING_ISSUE_THRESHOLD}+ times)"
                )
                print("Escalating to human review due to recurring issues...")

                # Create escalation file
                await escalate_to_human(spec_dir, recurring_issues, qa_iteration)

                # End validation phase
                if task_logger:
                    task_logger.end_phase(
                        LogPhase.VALIDATION,
                        success=False,
                        message=f"QA escalated to human after {qa_iteration} iterations due to recurring issues",
                    )

                # Update Linear
                if linear_task and linear_task.task_id:
                    await linear_qa_max_iterations(spec_dir, qa_iteration)
                    print(
                        "\nLinear: Task marked as needing human intervention (recurring issues)"
                    )
                task_event_emitter.emit(
                    "QA_MAX_ITERATIONS",
                    {"iteration": qa_iteration, "maxIterations": MAX_QA_ITERATIONS},
                )
                max_iterations_emitted = True

                # Save failed outcome to Graphiti for cross-task learning
                await _save_qa_outcome(spec_dir, project_dir, False, qa_iteration, current_issues)

                # Sync escalation state to main project
                _sync_to_source(spec_dir, source_spec_dir)
                return False

            # Record rejection in Linear
            if linear_task and linear_task.task_id:
                issues_count = len(current_issues)
                await linear_qa_rejected(spec_dir, issues_count, qa_iteration)

            if qa_iteration >= MAX_QA_ITERATIONS:
                print("\n⚠️  Maximum QA iterations reached.")
                print("Escalating to human review.")
                if not max_iterations_emitted:
                    task_event_emitter.emit(
                        "QA_MAX_ITERATIONS",
                        {
                            "iteration": qa_iteration,
                            "maxIterations": MAX_QA_ITERATIONS,
                        },
                    )
                    max_iterations_emitted = True
                break

            # Run fixer with phase-specific thinking budget
            fixer_thinking_budget = get_phase_thinking_budget(spec_dir, "qa")
            debug(
                "qa_loop",
                "Starting QA fixer session...",
                model=qa_model,
                thinking_budget=fixer_thinking_budget,
            )
            emit_phase(ExecutionPhase.QA_FIXING, "Fixing QA issues")
            task_event_emitter.emit(
                "QA_FIXING_STARTED",
                {"iteration": qa_iteration},
            )
            print("\nRunning QA Fixer Agent...")

            fix_client = create_client(
                project_dir,
                spec_dir,
                qa_model,
                agent_type="qa_fixer",
                max_thinking_tokens=fixer_thinking_budget,
            )

            async with fix_client:
                fix_status, fix_response = await run_qa_fixer_session(
                    fix_client, spec_dir, qa_iteration, verbose
                )

            debug(
                "qa_loop",
                "QA fixer session completed",
                fix_status=fix_status,
                response_length=len(fix_response),
            )

            if fix_status == "error":
                debug_error("qa_loop", f"Fixer error: {fix_response[:200]}")
                print(f"\n❌ Fixer encountered error: {fix_response}")
                record_iteration(
                    spec_dir,
                    qa_iteration,
                    "error",
                    [{"title": "Fixer error", "description": fix_response}],
                )
                break

            debug_success("qa_loop", "Fixes applied, re-running QA validation")
            task_event_emitter.emit(
                "QA_FIXING_COMPLETE",
                {"iteration": qa_iteration},
            )
            # Sync after fixer so daemon/UI sees the fix progress
            _sync_to_source(spec_dir, source_spec_dir)
            print("\n✅ Fixes applied. Re-running QA validation...")

        elif status == "error":
            consecutive_errors += 1
            debug_error(
                "qa_loop",
                f"QA session error: {response[:200]}",
                consecutive_errors=consecutive_errors,
                max_consecutive=MAX_CONSECUTIVE_ERRORS,
            )
            print(f"\n❌ QA error: {response}")
            print(
                f"   Consecutive errors: {consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}"
            )
            record_iteration(
                spec_dir,
                qa_iteration,
                "error",
                [{"title": "QA error", "description": response}],
            )

            # Build error context for self-correction in next iteration
            last_error_context = {
                "error_type": "missing_implementation_plan_update",
                "error_message": response,
                "consecutive_errors": consecutive_errors,
                "expected_action": "You MUST update implementation_plan.json with a qa_signoff object containing 'status': 'approved' or 'status': 'rejected'",
                "file_path": str(spec_dir / "implementation_plan.json"),
            }

            # Check if we've hit max consecutive errors
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                debug_error(
                    "qa_loop",
                    f"Max consecutive errors ({MAX_CONSECUTIVE_ERRORS}) reached - escalating to human",
                )
                print(
                    f"\n⚠️  {MAX_CONSECUTIVE_ERRORS} consecutive errors without progress."
                )
                print(
                    "The QA agent is unable to properly update implementation_plan.json."
                )
                print("Escalating to human review.")
                task_event_emitter.emit(
                    "QA_AGENT_ERROR",
                    {
                        "iteration": qa_iteration,
                        "consecutiveErrors": consecutive_errors,
                    },
                )

                # End validation phase as failed
                if task_logger:
                    task_logger.end_phase(
                        LogPhase.VALIDATION,
                        success=False,
                        message=f"QA agent failed {MAX_CONSECUTIVE_ERRORS} consecutive times - unable to update implementation_plan.json",
                    )
                _sync_to_source(spec_dir, source_spec_dir)
                return False

            print("Retrying with error feedback...")

    # Max iterations reached without approval
    emit_phase(ExecutionPhase.FAILED, "QA validation incomplete")
    if not max_iterations_emitted:
        task_event_emitter.emit(
            "QA_MAX_ITERATIONS",
            {"iteration": qa_iteration, "maxIterations": MAX_QA_ITERATIONS},
        )
    debug_error(
        "qa_loop",
        "QA VALIDATION INCOMPLETE - max iterations reached",
        iterations=qa_iteration,
        max_iterations=MAX_QA_ITERATIONS,
    )
    print("\n" + "=" * 70)
    print("  ⚠️  QA VALIDATION INCOMPLETE")
    print("=" * 70)
    print(f"\nReached maximum iterations ({MAX_QA_ITERATIONS}) without approval.")
    print("\nRemaining issues require human review:")

    # Show iteration summary
    history = get_iteration_history(spec_dir)
    summary = get_recurring_issue_summary(history)
    debug(
        "qa_loop",
        "QA loop final summary",
        total_iterations=len(history),
        total_issues=summary.get("total_issues", 0),
        unique_issues=summary.get("unique_issues", 0),
    )
    if summary["total_issues"] > 0:
        print("\n📊 Iteration Summary:")
        print(f"   Total iterations: {len(history)}")
        print(f"   Total issues found: {summary['total_issues']}")
        print(f"   Unique issues: {summary['unique_issues']}")
        if summary.get("most_common"):
            print("   Most common issues:")
            for issue in summary["most_common"][:3]:
                print(f"     - {issue['title']} ({issue['occurrences']} occurrences)")

    # End validation phase as failed
    if task_logger:
        task_logger.end_phase(
            LogPhase.VALIDATION,
            success=False,
            message=f"QA validation incomplete after {qa_iteration} iterations",
        )

    # Show the fix request file if it exists
    fix_request_file = spec_dir / "QA_FIX_REQUEST.md"
    if fix_request_file.exists():
        print(f"\nSee: {fix_request_file}")

    qa_report_file = spec_dir / "qa_report.md"
    if qa_report_file.exists():
        print(f"See: {qa_report_file}")

    # Update Linear: max iterations reached, needs human intervention
    if linear_task and linear_task.task_id:
        await linear_qa_max_iterations(spec_dir, qa_iteration)
        print("\nLinear: Task marked as needing human intervention")

    # Save failed outcome to Graphiti for cross-task learning
    await _save_qa_outcome(spec_dir, project_dir, False, qa_iteration)

    # Final sync so main project has the latest QA state
    _sync_to_source(spec_dir, source_spec_dir)

    print("\nManual intervention required.")
    return False
