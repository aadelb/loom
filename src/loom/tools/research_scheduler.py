"""Research Scheduler — create and manage recurring/scheduled research tasks."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from loom.config import get_config
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.scheduler")


def _get_schedules_file() -> Path:
    """Get path to schedules.json file."""
    base = Path(get_config().get("HOME", "~")).expanduser() / ".loom"
    base.mkdir(parents=True, exist_ok=True)
    return base / "schedules.json"


def _load_schedules() -> dict[str, Any]:
    """Load all schedules from disk. Create empty file if missing."""
    path = _get_schedules_file()
    if not path.exists():
        path.write_text(json.dumps({"schedules": []}, indent=2))
        return {"schedules": []}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        logger.error("schedules_load_failed: %s", e)
        return {"schedules": []}


def _save_schedules(data: dict[str, Any]) -> None:
    """Save schedules to disk atomically."""
    path = _get_schedules_file()
    tmp_path = path.with_suffix(".tmp")
    try:
        tmp_path.write_text(json.dumps(data, indent=2))
        tmp_path.replace(path)
    except OSError as e:
        logger.error("schedules_save_failed: %s", e)
        if tmp_path.exists():
            tmp_path.unlink()


@handle_tool_errors("research_schedule_create")
def research_schedule_create(
    name: str,
    tool_name: str,
    params: dict,
    interval_hours: int = 24,
    enabled: bool = True,
) -> dict[str, Any]:
    """Create a scheduled research task.

    Args:
        name: Human-readable schedule name
        tool_name: Name of research tool to call (e.g., "research_fetch")
        params: Tool parameters as dict
        interval_hours: Interval between runs in hours (default: 24)
        enabled: Whether schedule is active (default: True)

    Returns:
        Dict with: schedule_id, name, tool, interval_hours, next_run_at, enabled
    """
    try:
        now = datetime.now(UTC)
        schedule_id = str(uuid.uuid4())[:8]

        schedules = _load_schedules()
        new_schedule = {
            "id": schedule_id,
            "name": name,
            "tool": tool_name,
            "params": params,
            "interval_hours": interval_hours,
            "enabled": enabled,
            "created_at": now.isoformat(),
            "last_run": None,
            "next_run_at": (now + timedelta(seconds=10)).isoformat(),
            "runs_count": 0,
        }

        schedules["schedules"].append(new_schedule)
        _save_schedules(schedules)

        return {
            "schedule_id": schedule_id,
            "name": name,
            "tool": tool_name,
            "interval_hours": interval_hours,
            "next_run_at": new_schedule["next_run_at"],
            "enabled": enabled,
        }
    except Exception as exc:
        logger.error("schedule_create_error: %s", exc)
        return {"error": str(exc), "tool": "research_schedule_create"}


@handle_tool_errors("research_schedule_list")
def research_schedule_list() -> dict[str, Any]:
    """List all scheduled tasks with metadata.

    Returns:
        Dict with: schedules (list), total, active_count
    """
    try:
        schedules = _load_schedules()
        schedule_list = schedules.get("schedules", [])

        active_count = sum(1 for s in schedule_list if s.get("enabled", False))

        return {
            "schedules": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "tool": s["tool"],
                    "interval_hours": s["interval_hours"],
                    "last_run": s.get("last_run"),
                    "next_run": s.get("next_run_at"),
                    "enabled": s.get("enabled", False),
                    "runs_count": s.get("runs_count", 0),
                }
                for s in schedule_list
            ],
            "total": len(schedule_list),
            "active_count": active_count,
        }
    except Exception as exc:
        logger.error("schedule_list_error: %s", exc)
        return {"error": str(exc), "tool": "research_schedule_list"}


@handle_tool_errors("research_schedule_check")
def research_schedule_check() -> dict[str, Any]:
    """Check which scheduled tasks are due for execution.

    Returns:
        Dict with: due_now (list of due schedules), next_due_in_minutes
    """
    try:
        now = datetime.now(UTC)
        now_ts = now.timestamp()
        schedules = _load_schedules()
        schedule_list = schedules.get("schedules", [])

        due_now = []
        next_due_ts = None

        for schedule in schedule_list:
            if not schedule.get("enabled", False):
                continue

            next_run_str = schedule.get("next_run_at")
            if not next_run_str:
                continue

            try:
                next_run = datetime.fromisoformat(next_run_str.replace("Z", "+00:00"))
                next_run_ts = next_run.timestamp()

                if next_run_ts <= now_ts:
                    overdue_minutes = round((now_ts - next_run_ts) / 60)
                    due_now.append(
                        {
                            "id": schedule["id"],
                            "name": schedule["name"],
                            "tool": schedule["tool"],
                            "params": schedule.get("params", {}),
                            "overdue_minutes": overdue_minutes,
                        }
                    )
                else:
                    if next_due_ts is None or next_run_ts < next_due_ts:
                        next_due_ts = next_run_ts
            except (ValueError, AttributeError) as e:
                logger.warning("schedule_parse_failed id=%s: %s", schedule["id"], e)

        next_due_minutes = None
        if next_due_ts is not None:
            next_due_minutes = max(0, round((next_due_ts - now_ts) / 60))

        return {
            "due_now": due_now,
            "due_count": len(due_now),
            "next_due_in_minutes": next_due_minutes,
        }
    except Exception as exc:
        logger.error("schedule_check_error: %s", exc)
        return {"error": str(exc), "tool": "research_schedule_check"}
