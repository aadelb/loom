"""MCP tool for querying background task scheduler status."""

from __future__ import annotations

from typing import Any

from loom.scheduler import get_scheduler


async def research_scheduler_status() -> dict[str, Any]:
    """Get the status of all scheduled background tasks.

    Returns comprehensive information about all registered periodic tasks,
    including run counts, error tracking, and next scheduled run times.

    Returns:
        dict with keys:
            - running (bool): whether the scheduler is active
            - uptime_seconds (float): scheduler uptime
            - task_count (int): number of registered tasks
            - tasks (list): list of task status dicts with:
                - name (str): task name
                - interval_seconds (int): execution interval
                - run_count (int): total successful runs
                - error_count (int): total failed runs
                - last_error (str | None): most recent error message
                - last_run_time (str | None): ISO 8601 timestamp of last run
                - next_run_time (str | None): ISO 8601 timestamp of next run
                - is_running (bool): whether task is currently executing
            - timestamp (str): ISO 8601 timestamp of response
    """
    scheduler = get_scheduler()
    return scheduler.get_status()
