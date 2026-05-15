"""Standardized tool response helpers.

Provides consistent success/error response envelopes for all MCP tools.
Every tool should use these helpers instead of manually constructing
response dicts, ensuring uniform structure for clients.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger("loom.error_responses")

F = TypeVar("F", bound=Callable[..., Any])


def success_response(
    data: dict[str, Any],
    *,
    tool: str = "",
    source: str = "",
    cached: bool = False,
    elapsed_ms: int = 0,
) -> dict[str, Any]:
    """Build a standardized success response envelope.

    Args:
        data: the actual response payload (dict)
        tool: optional tool name identifier
        source: optional source identifier (e.g., "cached", "api", "database")
        cached: whether the result came from cache
        elapsed_ms: milliseconds elapsed during operation

    Returns:
        Dict with success response structure (original data + metadata)
    """
    result = dict(data)  # Don't mutate the original
    if tool:
        result["tool"] = tool
    if source:
        result["source"] = source
    if cached:
        result["cached"] = cached
    if elapsed_ms:
        result["elapsed_ms"] = elapsed_ms
    return result


def error_response(
    error: str | Exception,
    *,
    tool: str = "",
    error_type: str = "",
    **extra: Any,
) -> dict[str, Any]:
    """Build a standardized error response envelope.

    Args:
        error: error message (str) or exception instance
        tool: optional tool name identifier
        error_type: optional error type (defaults to exception class name)
        **extra: additional fields to include in response

    Returns:
        Dict with error response structure (error + metadata)
    """
    _REDACT_PATTERNS = ("://", "api_key=", "token=", "password=", "secret=", "bearer ", "authorization:")
    if isinstance(error, Exception):
        raw = str(error)
        for pattern in _REDACT_PATTERNS:
            if pattern in raw.lower():
                raw = type(error).__name__
                break
        msg = raw
    else:
        msg = str(error)
        for pattern in _REDACT_PATTERNS:
            if pattern in msg.lower():
                msg = "Internal error (details redacted)"
                break
    result: dict[str, Any] = {"error": msg}
    if tool:
        result["tool"] = tool
    if error_type:
        result["error_type"] = error_type
    elif isinstance(error, Exception):
        result["error_type"] = type(error).__name__
    result.update(extra)
    return result


def handle_tool_errors(tool_name: str) -> Callable[[F], F]:
    """Decorator that catches exceptions and returns error_response.

    Works for both sync and async functions. Automatically measures elapsed time
    and logs errors with full context.

    Args:
        tool_name: name of the tool (used for logging and error response)

    Returns:
        Decorator function

    Usage:
        @handle_tool_errors("research_foo")
        async def research_foo(query: str) -> dict[str, Any]:
            return {"results": [...]}

        @handle_tool_errors("research_bar")
        def research_bar(query: str) -> dict[str, Any]:
            return {"results": [...]}
    """

    def decorator(func: F) -> F:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                t0 = time.monotonic()
                try:
                    result = await func(*args, **kwargs)
                    if isinstance(result, dict):
                        if "elapsed_ms" not in result:
                            result["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
                        if "error" in result:
                            result.setdefault("tool", tool_name)
                            result.setdefault("error_type", "ValidationError")
                    return result
                except Exception as exc:
                    elapsed = int((time.monotonic() - t0) * 1000)
                    logger.error("%s failed: %s", tool_name, exc, exc_info=True)
                    return error_response(exc, tool=tool_name, elapsed_ms=elapsed)

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                t0 = time.monotonic()
                try:
                    result = func(*args, **kwargs)
                    if isinstance(result, dict):
                        if "elapsed_ms" not in result:
                            result["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
                        if "error" in result:
                            result.setdefault("tool", tool_name)
                            result.setdefault("error_type", "ValidationError")
                    return result
                except Exception as exc:
                    elapsed = int((time.monotonic() - t0) * 1000)
                    logger.error("%s failed: %s", tool_name, exc, exc_info=True)
                    return error_response(exc, tool=tool_name, elapsed_ms=elapsed)

            return sync_wrapper  # type: ignore[return-value]

    return decorator
