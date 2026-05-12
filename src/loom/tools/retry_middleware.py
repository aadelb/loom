"""Retry middleware for automatic retries on transient failures."""

from __future__ import annotations

import asyncio
import inspect
import importlib
import logging
import time
from typing import Any

logger = logging.getLogger("loom.tools.retry_middleware")

# Module-level counters for retry statistics
_stats = {
    "total_calls": 0,
    "total_retries": 0,
    "successes_after_retry": 0,
    "final_failures": 0,
    "tools_retry_count": {},  # tool_name -> count
}

# Default error types to retry on
DEFAULT_RETRY_ERRORS = ["TimeoutError", "ConnectionError", "RateLimitError"]


async def research_retry_execute(
    tool_name: str,
    params: dict[str, Any],
    max_retries: int = 3,
    backoff_base: float = 1.0,
    retry_on: list[str] | None = None,
) -> dict[str, Any]:
    """Execute a tool call with automatic retries on transient failures.

    Attempts to call a tool with exponential backoff on failures matching
    the retry_on error types. Returns detailed result with attempt counts.

    Args:
        tool_name: Name of the tool to execute (e.g., "research_fetch")
        params: Dictionary of parameters to pass to the tool
        max_retries: Maximum number of retry attempts (default 3)
        backoff_base: Base for exponential backoff in seconds (default 1.0)
        retry_on: List of error type names to retry on. Defaults to
            ["TimeoutError", "ConnectionError", "RateLimitError"]

    Returns:
        Dict with keys:
            - success: bool, whether the call succeeded
            - result: dict, the tool's result (None on error)
            - attempts: int, total attempts made
            - retries_used: int, number of retries performed
            - total_time_ms: float, total time spent (ms)
            - errors: list[dict], [{attempt, error_type, message}, ...]
    """
    _stats["total_calls"] += 1

    if retry_on is None:
        retry_on = DEFAULT_RETRY_ERRORS

    start_time = time.time()
    errors: list[dict[str, Any]] = []
    result = None
    attempt = 0

    # Try to import and call the tool
    for attempt in range(max_retries + 1):
        try:
            # Dynamically import the tool module
            # Try full tool name first, then fall back to prefix extraction
            try:
                module = importlib.import_module(f"loom.tools.{tool_name}")
                func = getattr(module, tool_name)
            except (ImportError, AttributeError):
                # Fallback: extract module name from tool name (last underscore)
                module_name = "loom.tools." + tool_name.rsplit("_", 1)[0]
                module = importlib.import_module(module_name)
                func = getattr(module, tool_name)

            # Call the tool with params
            if inspect.iscoroutinefunction(func):
                result = await func(**params)
            else:
                result = func(**params)

            # Success
            if attempt > 0:
                _stats["successes_after_retry"] += 1
            return {
                "success": True,
                "result": result,
                "attempts": attempt + 1,
                "retries_used": attempt,
                "total_time_ms": round((time.time() - start_time) * 1000, 2),
                "errors": errors,
            }

        except Exception as e:
            error_type = type(e).__name__

            # Check if this error type should be retried
            should_retry = error_type in retry_on and attempt < max_retries

            errors.append(
                {"attempt": attempt + 1, "error_type": error_type, "message": str(e)}
            )

            if not should_retry:
                # Last attempt or non-retryable error
                _stats["total_retries"] += attempt
                _stats["final_failures"] += 1
                _stats["tools_retry_count"][tool_name] = (
                    _stats["tools_retry_count"].get(tool_name, 0) + 1
                )

                return {
                    "success": False,
                    "result": None,
                    "attempts": attempt + 1,
                    "retries_used": attempt,
                    "total_time_ms": round((time.time() - start_time) * 1000, 2),
                    "errors": errors,
                }

            # Wait before retry with exponential backoff
            wait_time = backoff_base * (2 ** (attempt - 1))
            _stats["total_retries"] += 1
            logger.info(
                f"Retry attempt {attempt + 1} for {tool_name} after {error_type}, "
                f"waiting {wait_time}s"
            )
            await asyncio.sleep(wait_time)

    # Should never reach here
    _stats["final_failures"] += 1
    return {
        "success": False,
        "result": None,
        "attempts": attempt + 1,
        "retries_used": attempt,
        "total_time_ms": round((time.time() - start_time) * 1000, 2),
        "errors": errors,
    }


async def research_retry_middleware_stats() -> dict[str, Any]:
    """Return retry statistics across all tool invocations.

    Returns:
        Dict with keys:
            - total_calls: int, total tool calls made
            - total_retries: int, total retries performed
            - retry_rate_pct: float, percentage of calls that needed retries
            - success_after_retry_pct: float, % of retries that succeeded
            - final_failure_rate_pct: float, % of calls that failed after retries
            - top_retried_tools: list[dict], [{tool_name, retry_count}, ...]
    """
    total_calls = _stats["total_calls"]
    total_retries = _stats["total_retries"]
    successes = _stats["successes_after_retry"]
    failures = _stats["final_failures"]

    retry_rate = (total_retries / total_calls * 100) if total_calls > 0 else 0.0
    success_rate = (successes / total_retries * 100) if total_retries > 0 else 0.0
    failure_rate = (failures / total_calls * 100) if total_calls > 0 else 0.0

    # Get top 5 retried tools
    top_tools = sorted(
        _stats["tools_retry_count"].items(),
        key=lambda x: x[1],
        reverse=True,
    )[:5]

    return {
        "total_calls": total_calls,
        "total_retries": total_retries,
        "retry_rate_pct": round(retry_rate, 2),
        "success_after_retry_pct": round(success_rate, 2),
        "final_failure_rate_pct": round(failure_rate, 2),
        "top_retried_tools": [
            {"tool_name": name, "retry_count": count} for name, count in top_tools
        ],
    }
