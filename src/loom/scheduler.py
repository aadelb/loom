"""Background task scheduler for periodic operations.

Manages periodic tasks like cache cleanup, DLQ processing, quota resets,
and strategy flushing via asyncio tasks with configurable intervals.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

log = logging.getLogger("loom.scheduler")


@dataclass
class ScheduledTask:
    """State tracking for a single scheduled task."""

    name: str
    func: Callable[..., Coroutine[Any, Any, None]]
    interval_seconds: int
    last_run_time: float | None = None
    next_run_time: float | None = None
    task: asyncio.Task[None] | None = None
    run_count: int = 0
    error_count: int = 0
    last_error: str | None = None


class TaskScheduler:
    """Background task scheduler for periodic operations.

    Manages asyncio-based periodic tasks with configurable intervals.
    Provides status reporting, graceful stop, and error tracking.
    """

    def __init__(self) -> None:
        """Initialize the scheduler."""
        self._tasks: dict[str, ScheduledTask] = {}
        self._running = False
        self._lock = asyncio.Lock()
        self._start_time = time.time()

    def register(
        self,
        name: str,
        func: Callable[..., Coroutine[Any, Any, None]],
        interval_seconds: int,
    ) -> None:
        """Register a periodic task.

        Args:
            name: unique task identifier
            func: async callable to execute periodically
            interval_seconds: interval in seconds between runs
        """
        if name in self._tasks:
            log.warning("task_already_registered overwriting task=%s", name)
        self._tasks[name] = ScheduledTask(
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            next_run_time=time.time(),
        )
        log.info(
            "task_registered name=%s interval_seconds=%d",
            name,
            interval_seconds,
        )

    async def start(self) -> None:
        """Start all registered periodic tasks.

        Launches an asyncio.Task for each registered task that runs the task
        periodically at the specified interval. Should be called once at server
        startup.
        """
        async with self._lock:
            if self._running:
                log.warning("scheduler_already_running")
                return
            self._running = True

        log.info("scheduler_starting total_tasks=%d", len(self._tasks))

        for task_name, task_info in self._tasks.items():
            # Create and start the task
            task = asyncio.create_task(self._run_periodic(task_info))
            task_info.task = task
            log.info("task_started name=%s", task_name)

        log.info("scheduler_started total_tasks=%d", len(self._tasks))

    async def _run_periodic(self, task_info: ScheduledTask) -> None:
        """Run a task periodically at the specified interval.

        Args:
            task_info: ScheduledTask instance with execution details
        """
        while self._running:
            try:
                now = time.time()
                # Wait until next scheduled run time
                if task_info.next_run_time and now < task_info.next_run_time:
                    wait_time = task_info.next_run_time - now
                    await asyncio.sleep(min(wait_time, 1.0))
                    continue

                # Execute the task
                task_info.last_run_time = now
                task_info.next_run_time = now + task_info.interval_seconds
                task_info.run_count += 1

                start = time.time()
                try:
                    await task_info.func()
                    duration = time.time() - start
                    log.info(
                        "task_completed name=%s run_count=%d duration_seconds=%.2f",
                        task_info.name,
                        task_info.run_count,
                        duration,
                    )
                    task_info.last_error = None
                except Exception as exc:
                    duration = time.time() - start
                    task_info.error_count += 1
                    task_info.last_error = str(exc)
                    log.error(
                        "task_failed name=%s run_count=%d error_count=%d duration_seconds=%.2f error=%s",
                        task_info.name,
                        task_info.run_count,
                        task_info.error_count,
                        duration,
                        str(exc),
                    )

            except Exception as exc:
                log.error("task_loop_error name=%s error=%s", task_info.name, str(exc))
                await asyncio.sleep(1.0)

    async def stop(self) -> None:
        """Stop all running periodic tasks.

        Cancels all task asyncio.Task instances and waits for them to complete.
        Should be called during graceful shutdown.
        """
        async with self._lock:
            if not self._running:
                log.warning("scheduler_not_running")
                return
            self._running = False

        log.info("scheduler_stopping total_tasks=%d", len(self._tasks))

        # Cancel all tasks
        for task_info in self._tasks.values():
            if task_info.task and not task_info.task.done():
                task_info.task.cancel()
                try:
                    await task_info.task
                except asyncio.CancelledError:
                    log.debug("task_cancelled name=%s", task_info.name)
                except Exception as exc:
                    log.warning(
                        "task_stop_error name=%s error=%s",
                        task_info.name,
                        str(exc),
                    )

        log.info("scheduler_stopped")

    def get_status(self) -> dict[str, Any]:
        """Get scheduler status including all running tasks and their metrics.

        Returns:
            dict with running, tasks, uptime_seconds, and task-level details
        """
        uptime = time.time() - self._start_time
        tasks_status = []

        for task_info in self._tasks.values():
            task_status = {
                "name": task_info.name,
                "interval_seconds": task_info.interval_seconds,
                "run_count": task_info.run_count,
                "error_count": task_info.error_count,
                "last_error": task_info.last_error,
                "last_run_time": (
                    datetime.fromtimestamp(
                        task_info.last_run_time, tz=UTC
                    ).isoformat()
                    if task_info.last_run_time
                    else None
                ),
                "next_run_time": (
                    datetime.fromtimestamp(
                        task_info.next_run_time, tz=UTC
                    ).isoformat()
                    if task_info.next_run_time
                    else None
                ),
                "is_running": (
                    task_info.task is not None
                    and not task_info.task.done()
                ),
            }
            tasks_status.append(task_status)

        return {
            "running": self._running,
            "uptime_seconds": uptime,
            "task_count": len(self._tasks),
            "tasks": tasks_status,
            "timestamp": datetime.now(UTC).isoformat(),
        }


# Global scheduler instance
_scheduler: TaskScheduler | None = None


def get_scheduler() -> TaskScheduler:
    """Get or create the global TaskScheduler instance.

    Returns:
        TaskScheduler singleton instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


async def _periodic_cache_cleanup() -> None:
    """Delete cache entries older than the configured TTL."""
    from loom.cache import get_cache
    from loom.config import CONFIG

    try:
        cache = get_cache()
        config_ttl = CONFIG.get("CACHE_TTL_DAYS", 30)
        removed = cache.clear_older_than(days=config_ttl)
        if removed > 0:
            log.info("periodic_cache_cleanup removed=%d entries", removed)
    except Exception as exc:
        log.error("periodic_cache_cleanup_failed error=%s", str(exc))


async def _periodic_dlq_process() -> None:
    """Process dead letter queue (DLQ) items."""
    try:
        from loom.batch_queue import get_dlq

        dlq = get_dlq()
        if dlq is None:
            return

        # Try to process pending items if method exists
        if hasattr(dlq, "process_pending"):
            processed = await dlq.process_pending()
            if processed > 0:
                log.info("periodic_dlq_process processed=%d items", processed)
    except ImportError:
        # DLQ not available
        pass
    except Exception as exc:
        log.error("periodic_dlq_process_failed error=%s", str(exc))


async def _periodic_quota_reset() -> None:
    """Reset daily quotas for rate limiting."""
    try:
        from loom.rate_limiter import reset_daily_quotas

        reset_daily_quotas()
        log.info("periodic_quota_reset completed")
    except ImportError:
        # Rate limiter not available
        pass
    except Exception as exc:
        log.error("periodic_quota_reset_failed error=%s", str(exc))


async def _periodic_strategy_flush() -> None:
    """Flush strategy adapter stats to disk."""
    try:
        from loom.reid_auto import ReidAutoReframe

        adapter = (
            ReidAutoReframe._instance
            if hasattr(ReidAutoReframe, "_instance")
            else None
        )
        if adapter and hasattr(adapter, "save_state"):
            await adapter.save_state()
            log.info("periodic_strategy_flush completed")
    except ImportError:
        # Strategy module not available
        pass
    except Exception as exc:
        log.error("periodic_strategy_flush_failed error=%s", str(exc))


async def _periodic_health_check() -> None:
    """Internal health verification and metrics collection."""
    try:
        from loom.server_state import get_health_status as _health_status

        log.debug("periodic_health_check health_status=%s", _health_status)
    except Exception as exc:
        log.error("periodic_health_check_failed error=%s", str(exc))


def register_default_tasks() -> None:
    """Register the built-in periodic tasks at server startup.

    Called from server.create_app() after tool registration.
    """
    scheduler = get_scheduler()

    # Cache cleanup: every 3600s (1 hour)
    scheduler.register(
        "cache_cleanup",
        _periodic_cache_cleanup,
        interval_seconds=3600,
    )

    # DLQ processing: every 60s
    scheduler.register(
        "dlq_process",
        _periodic_dlq_process,
        interval_seconds=60,
    )

    # Quota reset: every 86400s (24 hours)
    scheduler.register(
        "quota_reset",
        _periodic_quota_reset,
        interval_seconds=86400,
    )

    # Strategy flush: every 300s (5 minutes)
    scheduler.register(
        "strategy_flush",
        _periodic_strategy_flush,
        interval_seconds=300,
    )

    # Health check: every 60s
    scheduler.register(
        "health_self_check",
        _periodic_health_check,
        interval_seconds=60,
    )

    log.info("default_tasks_registered count=5")
