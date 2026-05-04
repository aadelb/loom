"""CPU-bound task executor using ProcessPoolExecutor.

Provides async-friendly wrapper for CPU-intensive operations that would
otherwise block the async event loop. Includes graceful shutdown and
health monitoring.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from concurrent.futures import ProcessPoolExecutor
from functools import wraps
from typing import Any, Callable, TypeVar

logger = logging.getLogger("loom.cpu_executor")

# Module-level ProcessPoolExecutor instance (singleton)
_executor: ProcessPoolExecutor | None = None
_executor_lock = asyncio.Lock()

# Track active tasks for shutdown
_active_tasks: set[asyncio.Task[Any]] = set()


def _get_max_workers() -> int:
    """Get max worker count from env or use sensible default.

    Args:
        LOOM_CPU_WORKERS: Number of worker processes (default: 4)

    Returns:
        Number of worker processes to use
    """
    try:
        max_workers = int(os.environ.get("LOOM_CPU_WORKERS", "4"))
        # Clamp to reasonable range (1-16)
        return max(1, min(16, max_workers))
    except ValueError:
        logger.warning("LOOM_CPU_WORKERS not an integer, using default 4")
        return 4


async def _get_executor() -> ProcessPoolExecutor:
    """Get or create the global ProcessPoolExecutor (thread-safe).

    Creates the executor lazily on first access with lock to prevent race
    conditions. Max workers is configurable via LOOM_CPU_WORKERS env var.

    Returns:
        The module-level ProcessPoolExecutor instance
    """
    global _executor

    if _executor is not None:
        return _executor

    async with _executor_lock:
        # Double-check after acquiring lock
        if _executor is not None:
            return _executor

        max_workers = _get_max_workers()
        _executor = ProcessPoolExecutor(
            max_workers=max_workers,
            initializer=None,  # No initializer for now; can be extended
        )
        logger.info("cpu_executor_created max_workers=%d", max_workers)
        return _executor


def is_cpu_bound(func: Callable[..., Any]) -> bool:
    """Check if a function is marked as CPU-bound.

    Args:
        func: Function to check

    Returns:
        True if function has _cpu_bound attribute set to True
    """
    return getattr(func, "_cpu_bound", False) is True


def cpu_bound(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to mark a sync function as CPU-bound.

    Sets _cpu_bound = True on the wrapper so that _wrap_tool can detect
    and route to the process pool instead of thread pool.

    Args:
        func: Synchronous function to wrap

    Returns:
        Wrapper with _cpu_bound = True attribute set
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await run_cpu_bound(func, *args, **kwargs)

    # Mark the wrapper as CPU-bound
    wrapper._cpu_bound = True  # type: ignore
    return wrapper


async def run_cpu_bound(
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute a CPU-bound function in the process pool.

    Submits a sync function to the process pool and returns an awaitable
    that completes when the function finishes. Handles exceptions and
    timeouts gracefully.

    Args:
        func: Synchronous function to execute
        *args: Positional arguments to pass to func
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result of func(*args, **kwargs)

    Raises:
        Exception: Re-raised from the worker process
        asyncio.TimeoutError: If execution takes too long
    """
    loop = asyncio.get_event_loop()
    executor = await _get_executor()

    try:
        result = await loop.run_in_executor(executor, func, *args)
        return result
    except Exception as exc:
        logger.error(
            "cpu_bound_execution_failed func=%s error=%s",
            getattr(func, "__name__", str(func)),
            str(exc)[:200],
        )
        raise


async def get_pool_status() -> dict[str, Any]:
    """Get health status of the CPU executor pool.

    Returns:
        Dict with:
        - pool_initialized: bool indicating if executor has been created
        - max_workers: Configured number of worker processes
        - active_tasks: Current number of tasks running in process pool
        - pending_tasks: Tasks waiting in queue (estimate)
        - status: "healthy", "busy", or "idle"
    """
    executor = None
    try:
        executor = await asyncio.wait_for(_get_executor(), timeout=1.0)
    except asyncio.TimeoutError:
        logger.warning("cpu_executor timeout during status check")
        return {
            "pool_initialized": False,
            "status": "unhealthy",
            "error": "executor_init_timeout",
        }

    max_workers = _get_max_workers()
    active_count = len(_active_tasks)

    # Estimate based on active tasks
    if active_count == 0:
        pool_status = "idle"
    elif active_count < max_workers // 2:
        pool_status = "healthy"
    elif active_count < max_workers:
        pool_status = "busy"
    else:
        pool_status = "saturated"

    return {
        "pool_initialized": executor is not None,
        "max_workers": max_workers,
        "active_tasks": active_count,
        "pending_tasks": max(0, active_count - max_workers),
        "status": pool_status,
        "configuration": {
            "LOOM_CPU_WORKERS": os.environ.get("LOOM_CPU_WORKERS", "4"),
        },
    }


async def shutdown_executor() -> dict[str, Any]:
    """Gracefully shut down the CPU executor pool.

    Waits for all pending tasks to complete, then shuts down the
    process pool. Called automatically on SIGTERM/SIGINT.

    Returns:
        Dict with shutdown results:
        - tasks_waited: Number of tasks waited for completion
        - status: "success" or "error"
        - message: Human-readable status message
    """
    global _executor

    if _executor is None:
        return {
            "status": "success",
            "message": "executor not initialized",
            "tasks_waited": 0,
        }

    try:
        # Wait for active tasks
        if _active_tasks:
            logger.info("shutdown_executor waiting for %d active tasks", len(_active_tasks))
            await asyncio.gather(*_active_tasks, return_exceptions=True)

        # Shutdown executor
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _executor.shutdown, True)
        _executor = None
        logger.info("shutdown_executor complete")

        return {
            "status": "success",
            "message": "executor shut down successfully",
            "tasks_waited": len(_active_tasks),
        }

    except Exception as exc:
        logger.error("shutdown_executor failed: %s", exc)
        return {
            "status": "error",
            "message": str(exc),
            "tasks_waited": len(_active_tasks),
        }


def _handle_shutdown_signal(signum: int, frame: Any) -> None:
    """Signal handler for SIGTERM/SIGINT to gracefully shutdown.

    Args:
        signum: Signal number (SIGTERM=15, SIGINT=2)
        frame: Current stack frame
    """
    logger.info("received_shutdown_signal signum=%d", signum)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(shutdown_executor())
    except RuntimeError:
        # Event loop not running, create new one
        asyncio.run(shutdown_executor())


# Register signal handlers for graceful shutdown
signal.signal(signal.SIGTERM, _handle_shutdown_signal)
signal.signal(signal.SIGINT, _handle_shutdown_signal)


__all__ = [
    "cpu_bound",
    "is_cpu_bound",
    "run_cpu_bound",
    "get_pool_status",
    "shutdown_executor",
]
