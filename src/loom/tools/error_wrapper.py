"""Universal error wrapper decorator to prevent uncaught exceptions from crashing MCP.

Provides safe_tool_call decorator that catches ALL exceptions and returns
structured error responses. Includes error tracking and diagnostic tools.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import traceback
from datetime import UTC, datetime
from typing import Any, Callable, TypeVar

log = logging.getLogger("loom.error_wrapper")

# Module-level error statistics tracker
_error_stats: dict[str, dict[str, Any]] = {}

T = TypeVar("T")


def safe_tool_call(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to safely wrap tool functions and prevent exception propagation.

    Catches ALL exceptions from the wrapped function and returns a structured
    error response instead of crashing. Tracks error statistics per tool.

    Works with both sync and async functions, preserving original signature.

    Args:
        func: The tool function to wrap (sync or async)

    Returns:
        Wrapped function that catches exceptions and returns error dicts
    """
    tool_name = func.__name__
    is_async = inspect.iscoroutinefunction(func)

    if is_async:

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                _track_error(tool_name, e)
                return _build_error_response(tool_name, e)

        return async_wrapper
    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _track_error(tool_name, e)
                return _build_error_response(tool_name, e)

        return sync_wrapper


def _track_error(tool_name: str, error: Exception) -> None:
    """Track error occurrence in module-level stats dict.

    Args:
        tool_name: Name of the tool that encountered the error
        error: The exception that was raised
    """
    timestamp = datetime.now(UTC).isoformat()

    if tool_name not in _error_stats:
        _error_stats[tool_name] = {
            "count": 0,
            "last_error": None,
            "last_timestamp": None,
            "error_types": {},
        }

    stats = _error_stats[tool_name]
    stats["count"] += 1
    stats["last_error"] = str(error)
    stats["last_timestamp"] = timestamp

    error_type = type(error).__name__
    if error_type not in stats["error_types"]:
        stats["error_types"][error_type] = 0
    stats["error_types"][error_type] += 1

    # Log with full traceback
    log.error(
        f"Tool error in {tool_name}: {error_type}",
        extra={
            "tool_name": tool_name,
            "error_type": error_type,
            "error_message": str(error),
        },
        exc_info=True,
    )


def _build_error_response(tool_name: str, error: Exception) -> dict[str, Any]:
    """Build structured error response from exception.

    Args:
        tool_name: Name of the tool that encountered the error
        error: The exception that was raised

    Returns:
        Dict with error, error_type, tool, timestamp, and traceback
    """
    return {
        "error": str(error),
        "error_type": type(error).__name__,
        "tool": tool_name,
        "timestamp": datetime.now(UTC).isoformat(),
        "traceback": traceback.format_exc(),
    }


async def research_error_stats() -> dict[str, Any]:
    """Get error statistics from all wrapped tools.

    Returns error tracking data showing error counts, types, and last occurrence
    for each tool that has encountered errors.

    Returns:
        Dict with per-tool error statistics including count, error_types, and timestamps
    """
    try:
        if not _error_stats:
            return {
                "status": "ok",
                "message": "No errors recorded",
                "total_errors": 0,
                "total_tools_with_errors": 0,
                "error_data": {},
            }

        total_count = sum(stats["count"] for stats in _error_stats.values())

        return {
            "status": "ok",
            "timestamp": datetime.now(UTC).isoformat(),
            "total_errors": total_count,
            "total_tools_with_errors": len(_error_stats),
            "error_data": dict(_error_stats),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_error_stats"}


async def research_error_clear() -> dict[str, Any]:
    """Clear error history and reset tracking.

    Clears all accumulated error statistics, useful for resetting after
    troubleshooting or redeployment.

    Returns:
        Dict with cleared status and count of previously recorded errors
    """
    try:
        global _error_stats
        previous_count = sum(stats["count"] for stats in _error_stats.values())
        _error_stats = {}

        log.info(f"Error statistics cleared: {previous_count} errors removed")

        return {
            "status": "ok",
            "cleared": True,
            "previous_error_count": previous_count,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_error_clear"}
