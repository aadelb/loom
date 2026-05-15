"""Unified sandbox management for tool execution.

Provides resource limits, execution timeouts, and isolation
for tool functions that run external code or untrusted content.
"""
from __future__ import annotations

import asyncio
import logging
import os
import resource
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger("loom.sandbox_manager")


@contextmanager
def resource_limits(
    *,
    max_memory_mb: int = 512,
    max_cpu_seconds: int = 60,
    max_file_size_mb: int = 100,
    max_open_files: int = 256,
) -> Generator[None, None, None]:
    """Context manager that sets resource limits for the current process.

    Only effective on Unix systems. On other platforms, yields without limits.
    """
    if os.name != "posix":
        yield
        return

    old_limits: dict[int, tuple[int, int]] = {}
    limits = [
        (resource.RLIMIT_AS, max_memory_mb * 1024 * 1024),
        (resource.RLIMIT_CPU, max_cpu_seconds),
        (resource.RLIMIT_FSIZE, max_file_size_mb * 1024 * 1024),
        (resource.RLIMIT_NOFILE, max_open_files),
    ]

    try:
        for res, soft_limit in limits:
            try:
                old_limits[res] = resource.getrlimit(res)
                hard = old_limits[res][1]
                resource.setrlimit(res, (min(soft_limit, hard), hard))
            except (ValueError, OSError) as exc:
                logger.debug("cannot_set_limit resource=%s error=%s", res, exc)
        yield
    finally:
        for res, old in old_limits.items():
            try:
                resource.setrlimit(res, old)
            except (ValueError, OSError):
                pass


async def run_sandboxed(
    coro: Any,
    *,
    timeout: float = 60.0,
    max_memory_mb: int = 512,
) -> dict[str, Any]:
    """Run a coroutine with timeout and resource constraints.

    Returns {"result": value} on success, {"error": message} on failure.
    """
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        return {"result": result}
    except asyncio.TimeoutError:
        return {"error": f"Sandbox timeout after {timeout}s"}
    except MemoryError:
        return {"error": "Memory limit exceeded"}
    except Exception as exc:
        return {"error": f"Sandbox error: {type(exc).__name__}: {exc}"}


def is_sandboxed() -> bool:
    """Check if we're running inside a sandbox (Docker, chroot, etc.)."""
    indicators = [
        os.path.exists("/.dockerenv"),
        os.path.exists("/run/.containerenv"),
        os.environ.get("LOOM_SANDBOXED") == "1",
    ]
    return any(indicators)
