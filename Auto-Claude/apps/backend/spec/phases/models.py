"""
Phase Models and Constants
===========================

Data structures and constants for phase execution.
"""

import asyncio
from dataclasses import dataclass


@dataclass
class PhaseResult:
    """Result of a phase execution."""

    phase: str
    success: bool
    output_files: list[str]
    errors: list[str]
    retries: int


# Maximum retry attempts for phase execution
MAX_RETRIES = 3

# Exponential backoff base (seconds). Delays: 2, 4 seconds for attempts 0, 1.
RETRY_BACKOFF_BASE = 2

# Keywords that indicate a retryable API/network error (OpenClaw pattern: graceful degradation)
_RETRYABLE_KEYWORDS = (
    "rate_limit", "rate limit", "429", "overloaded",
    "capacity", "timeout", "timed out", "connection",
    "temporarily unavailable", "503", "502",
)


def is_retryable_error(error_text: str) -> bool:
    """Check if an error message indicates a retryable condition.

    Detects rate limits, timeouts, overload, and transient network errors.
    """
    if not error_text:
        return False
    lower = error_text.lower()
    return any(kw in lower for kw in _RETRYABLE_KEYWORDS)


async def retry_backoff(attempt: int, error_text: str, ui_module) -> None:
    """Apply exponential backoff if the error appears retryable.

    Call this at the end of a retry loop body, after a failed attempt.
    Only sleeps if the error is retryable AND there are retries remaining.

    Delegates to core.retry.calculate_backoff() for enhanced jitter support.

    Args:
        attempt: Current attempt index (0-based)
        error_text: The error output from the failed attempt
        ui_module: UI module or object with print_status(msg, level)
    """
    if attempt >= MAX_RETRIES - 1:
        return  # Last attempt, no point sleeping
    if not is_retryable_error(error_text):
        return  # Not a transient error, retry immediately

    from core.retry import RetryConfig, calculate_backoff

    config = RetryConfig(base_delay=RETRY_BACKOFF_BASE, max_retries=MAX_RETRIES)
    backoff = calculate_backoff(attempt, config)
    ui_module.print_status(
        f"Transient error detected, waiting {backoff:.1f}s before retry...", "info"
    )
    await asyncio.sleep(backoff)
