"""Research progress tracker for long-running investigations.

Provides tools for creating, updating, and monitoring investigation progress
with ETA estimation and status dashboard.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

log = logging.getLogger("loom.progress_tracker")


def _get_investigations_path() -> Path:
    """Get path to investigations storage file."""
    base_dir = Path.home() / ".loom"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / "investigations.json"


def _load_investigations() -> dict[str, Any]:
    """Load all investigations from storage."""
    path = _get_investigations_path()
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.error(f"Failed to load investigations: {e}")
        return {}


def _save_investigations(data: dict[str, Any]) -> None:
    """Save investigations to storage with atomic writes."""
    path = _get_investigations_path()
    tmp_path = path.parent / f".{uuid.uuid4()}.tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, path)
    except OSError as e:
        log.error(f"Failed to save investigations: {e}")
        if tmp_path.exists():
            tmp_path.unlink()


async def research_progress_create(
    investigation: str,
    total_steps: int = 10,
    description: str = "",
) -> dict[str, Any]:
    """Create a new investigation progress tracker.

    Args:
        investigation: Name of the investigation (e.g., "Threat Intel - Campaign X")
        total_steps: Total steps expected (default: 10)
        description: Optional detailed description

    Returns:
        dict with investigation_id, name, total_steps, progress_pct, created_at
    """
    if not investigation or not investigation.strip():
        return {"error": "Investigation name is required"}
    if total_steps < 1 or total_steps > 10000:
        return {"error": "total_steps must be between 1 and 10000"}

    inv_id = str(uuid.uuid4())[:8]
    now = datetime.now(UTC).isoformat()

    data = _load_investigations()
    data[inv_id] = {
        "id": inv_id,
        "name": investigation.strip(),
        "description": description.strip(),
        "total_steps": total_steps,
        "current_step": 0,
        "progress_pct": 0,
        "notes": [],
        "created_at": now,
        "last_updated": now,
        "completed_at": None,
    }
    _save_investigations(data)

    return {
        "investigation_id": inv_id,
        "name": investigation.strip(),
        "total_steps": total_steps,
        "progress_pct": 0,
        "created_at": now,
    }


async def research_progress_update(
    investigation_id: str,
    step: int,
    note: str = "",
) -> dict[str, Any]:
    """Update progress on an investigation.

    Args:
        investigation_id: ID of investigation to update
        step: Current step number (0-indexed, but displayed as 1-indexed)
        note: Optional progress note

    Returns:
        dict with investigation_id, step, total_steps, progress_pct, eta_hours
    """
    data = _load_investigations()
    if investigation_id not in data:
        return {"error": f"Investigation {investigation_id} not found"}

    inv = data[investigation_id]
    total = inv["total_steps"]

    if step < 0 or step > total:
        return {"error": f"step must be between 0 and {total}"}

    inv["current_step"] = step
    inv["progress_pct"] = int((step / total * 100)) if total > 0 else 0
    inv["last_updated"] = datetime.now(UTC).isoformat()

    if note:
        inv["notes"].append({
            "step": step,
            "text": note.strip(),
            "timestamp": inv["last_updated"],
        })

    if step >= total:
        inv["completed_at"] = inv["last_updated"]

    _save_investigations(data)

    created = datetime.fromisoformat(inv["created_at"])
    now = datetime.now(UTC)
    elapsed = (now - created).total_seconds() / 3600
    if step > 0:
        rate = elapsed / step
        eta_hours = int(rate * (total - step))
    else:
        eta_hours = 0

    return {
        "investigation_id": investigation_id,
        "name": inv["name"],
        "step": step,
        "total_steps": total,
        "progress_pct": inv["progress_pct"],
        "note": note,
        "estimated_completion_hours": eta_hours,
        "last_updated": inv["last_updated"],
    }


async def research_progress_dashboard() -> dict[str, Any]:
    """Show all active and completed investigations.

    Returns:
        dict with active (list), completed (count), total (count)
    """
    data = _load_investigations()

    active = []
    completed_count = 0

    for inv_id, inv in data.items():
        is_done = inv.get("completed_at") is not None
        if is_done:
            completed_count += 1
        else:
            created = datetime.fromisoformat(inv["created_at"])
            last_updated = datetime.fromisoformat(inv["last_updated"])
            now = datetime.now(UTC)
            elapsed_hours = (now - created).total_seconds() / 3600

            step = inv["current_step"]
            total = inv["total_steps"]
            if step > 0:
                rate = elapsed_hours / step
                eta_hours = int(rate * (total - step))
            else:
                eta_hours = 0

            active.append({
                "id": inv_id,
                "name": inv["name"],
                "progress_pct": inv["progress_pct"],
                "step": step,
                "total_steps": total,
                "last_updated": last_updated.isoformat(),
                "eta_hours": eta_hours,
                "notes_count": len(inv["notes"]),
            })

    return {
        "active": active,
        "completed": completed_count,
        "total": len(data),
    }
