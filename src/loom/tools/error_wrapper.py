"""Universal error wrapper decorator to prevent uncaught exceptions from crashing MCP.

Provides safe_tool_call decorator that catches ALL exceptions and returns
structured error responses. Includes error tracking and diagnostic tools.

SECURITY: Error messages and tracebacks are sanitized before external exposure.
Stack traces and internal paths are logged server-side only.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import re
import traceback
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Callable, TypeVar

log = logging.getLogger("loom.error_wrapper")

# Module-level error statistics tracker (protected by lock for thread-safety)
_error_stats: dict[str, dict[str, Any]] = {}
_error_stats_lock = Lock()

T = TypeVar("T")


def safe_tool_call(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to safely wrap tool functions and prevent exception propagation.

    Catches ALL exceptions from the wrapped function and returns a structured
    error response instead of crashing. Tracks error statistics per tool.

    Works with both sync and async functions, preserving original signature.

    SECURITY: External error responses are sanitized and do NOT include stack traces.
    Stack traces with internal paths are logged server-side only via _track_error.

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
                # Return sanitized response (no traceback, no internal paths)
                return _build_error_response(tool_name, e, internal_logs=False)

        return async_wrapper
    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                _track_error(tool_name, e)
                # Return sanitized response (no traceback, no internal paths)
                return _build_error_response(tool_name, e, internal_logs=False)

        return sync_wrapper


def _track_error(tool_name: str, error: Exception) -> None:
    """Track error occurrence in module-level stats dict (thread-safe).

    SECURITY: Full stack traces and error messages are logged server-side only.
    Do NOT expose these via diagnostic endpoints.

    Args:
        tool_name: Name of the tool that encountered the error
        error: The exception that was raised
    """
    timestamp = datetime.now(UTC).isoformat()

    with _error_stats_lock:
        if tool_name not in _error_stats:
            _error_stats[tool_name] = {
                "count": 0,
                "last_error_type": None,
                "last_timestamp": None,
                "error_types": {},
            }

        stats = _error_stats[tool_name]
        stats["count"] += 1
        # Store only error type, not full message (security)
        stats["last_error_type"] = type(error).__name__
        stats["last_timestamp"] = timestamp

        error_type = type(error).__name__
        if error_type not in stats["error_types"]:
            stats["error_types"][error_type] = 0
        stats["error_types"][error_type] += 1

    # Log with full traceback SERVER-SIDE ONLY
    # This is safe because log output stays within server boundaries
    log.error(
        f"Tool error in {tool_name}: {error_type}",
        extra={
            "tool_name": tool_name,
            "error_type": error_type,
            "error_message": str(error),
        },
        exc_info=True,
    )


def _sanitize_error_message(error_message: str) -> str:
    """Sanitize error message to remove internal paths and sensitive data.

    Removes:
    - File paths (e.g., /home/user/projects/...)
    - Home directory references
    - Potential API keys or credentials

    Args:
        error_message: Raw error message string

    Returns:
        Sanitized error message safe for external exposure
    """
    # Remove home directory paths
    sanitized = re.sub(r"/home/\w+", "~", error_message)
    sanitized = re.sub(r"/Users/\w+", "~", sanitized)
    sanitized = re.sub(r"C:\\Users\\\w+", "~", sanitized)

    # Remove absolute paths (simplified; maintains relative paths)
    sanitized = re.sub(r"/[a-z0-9/_-]*(?:projects|src|lib|etc)/", "/[path]/", sanitized)

    return sanitized


def _build_error_response(tool_name: str, error: Exception, internal_logs: bool = True) -> dict[str, Any]:
    """Build structured error response from exception.

    SECURITY: Stack traces are NEVER included in external responses.
    When internal_logs=False (external caller), error message is sanitized.
    When internal_logs=True (internal use), full details are preserved.

    Args:
        tool_name: Name of the tool that encountered the error
        error: The exception that was raised
        internal_logs: If False, sanitize the response for external exposure

    Returns:
        Dict with error, error_type, tool, and timestamp (no traceback for external)
    """
    error_type = type(error).__name__
    error_msg = str(error)

    if not internal_logs:
        # External response: sanitized, no stack trace
        error_msg = _sanitize_error_message(error_msg)

    response: dict[str, Any] = {
        "error": error_msg,
        "error_type": error_type,
        "tool": tool_name,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    # ONLY include traceback for internal logs (when internal_logs=True)
    if internal_logs:
        response["traceback"] = traceback.format_exc()

    return response


async def research_error_stats() -> dict[str, Any]:
    """Get error statistics from all wrapped tools.

    Returns error tracking data showing error counts, types, and last occurrence
    for each tool that has encountered errors. Only error types are exposed,
    not full error messages (which may contain sensitive data).

    SECURITY: Error messages are NOT included in the response to prevent
    information disclosure. Only error type names and counts are returned.

    Returns:
        Dict with per-tool error statistics including count, error_types, and timestamps
    """
    try:
        with _error_stats_lock:
            if not _error_stats:
                return {
                    "status": "ok",
                    "message": "No errors recorded",
                    "total_errors": 0,
                    "total_tools_with_errors": 0,
                    "error_data": {},
                }

            total_count = sum(stats["count"] for stats in _error_stats.values())

            # Build response with sanitized data (no full error messages)
            sanitized_error_data = {}
            for tool_name, stats in _error_stats.items():
                sanitized_error_data[tool_name] = {
                    "count": stats["count"],
                    "last_error_type": stats["last_error_type"],
                    "last_timestamp": stats["last_timestamp"],
                    "error_types": stats["error_types"],
                }

            return {
                "status": "ok",
                "timestamp": datetime.now(UTC).isoformat(),
                "total_errors": total_count,
                "total_tools_with_errors": len(_error_stats),
                "error_data": sanitized_error_data,
            }
    except Exception as exc:
        # Sanitize exception message before returning
        return {
            "status": "error",
            "error": _sanitize_error_message(str(exc)),
            "error_type": type(exc).__name__,
            "tool": "research_error_stats",
        }


async def research_error_clear() -> dict[str, Any]:
    """Clear error history and reset tracking (thread-safe).

    Clears all accumulated error statistics, useful for resetting after
    troubleshooting or redeployment.

    Returns:
        Dict with cleared status and count of previously recorded errors
    """
    try:
        with _error_stats_lock:
            previous_count = sum(stats["count"] for stats in _error_stats.values())
            _error_stats.clear()

        log.info(f"Error statistics cleared: {previous_count} errors removed")

        return {
            "status": "ok",
            "cleared": True,
            "previous_error_count": previous_count,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": _sanitize_error_message(str(exc)),
            "error_type": type(exc).__name__,
            "tool": "research_error_clear",
        }
