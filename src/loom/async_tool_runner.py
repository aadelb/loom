"""Async tool invocation with timeout and error handling.

Provides a unified way to call tool functions (sync or async) from within
other tools, with timeout protection and consistent error handling.
"""
from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import time
from typing import Any, Callable

logger = logging.getLogger("loom.async_tool_runner")


async def invoke(
    func: Callable[..., Any],
    *args: Any,
    timeout: float = 120.0,
    **kwargs: Any,
) -> dict[str, Any]:
    """Invoke a tool function (sync or async) with timeout.

    Returns dict result as-is, or wraps non-dict result in {"result": value}.
    On timeout or exception, returns {"error": message}.
    """
    t0 = time.monotonic()
    try:
        if inspect.iscoroutinefunction(func):
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
        else:
            loop = asyncio.get_running_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, functools.partial(func, *args, **kwargs)),
                timeout=timeout,
            )
        elapsed = int((time.monotonic() - t0) * 1000)
        if isinstance(result, dict):
            if "elapsed_ms" not in result:
                result["elapsed_ms"] = elapsed
            return result
        return {"result": result, "elapsed_ms": elapsed}
    except asyncio.TimeoutError:
        elapsed = int((time.monotonic() - t0) * 1000)
        logger.warning("tool_timeout func=%s timeout=%.1fs", func.__name__, timeout)
        return {"error": f"Timeout after {timeout}s", "elapsed_ms": elapsed}
    except Exception as exc:
        elapsed = int((time.monotonic() - t0) * 1000)
        logger.error("tool_error func=%s error=%s", func.__name__, exc)
        return {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "elapsed_ms": elapsed,
        }


async def invoke_many(
    calls: list[tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]],
    *,
    timeout: float = 120.0,
    max_concurrency: int = 5,
) -> list[dict[str, Any]]:
    """Invoke multiple tool functions concurrently with bounded parallelism.

    Args:
        calls: List of (func, args, kwargs) tuples
        timeout: Per-call timeout in seconds
        max_concurrency: Max concurrent invocations (default 5)

    Returns:
        List of results in same order as input calls
    """
    semaphore = asyncio.Semaphore(max_concurrency)

    async def _run(func: Callable, args: tuple, kwargs: dict) -> dict[str, Any]:
        async with semaphore:
            return await invoke(func, *args, timeout=timeout, **kwargs)

    tasks = [_run(func, args, kwargs) for func, args, kwargs in calls]
    return await asyncio.gather(*tasks)
