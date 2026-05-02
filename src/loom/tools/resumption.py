"""Stateful Resumption Engine — SQLite checkpoint recovery for long-running tasks."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("loom.tools.resumption")
_DB_PATH = Path.home() / ".loom" / "checkpoints.db"


async def _get_db() -> aiosqlite.Connection:
    """Get or create checkpoints database."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(_DB_PATH))
    conn.row_factory = aiosqlite.Row
    await conn.execute(
        "CREATE TABLE IF NOT EXISTS checkpoints("
        "task_id TEXT PRIMARY KEY,state TEXT,progress REAL DEFAULT 0,"
        "created_at TEXT,updated_at TEXT)"
    )
    await conn.commit()
    return conn


async def research_checkpoint_save(
    task_id: str, state: dict[str, Any], progress_pct: float = 0.0
) -> dict[str, Any]:
    """Save checkpoint. Atomically upserts task state."""
    if not task_id or not isinstance(task_id, str):
        raise ValueError("task_id required")
    if not isinstance(state, dict):
        raise ValueError("state must be dict")
    if not 0 <= progress_pct <= 100:
        raise ValueError("progress_pct 0-100")

    now = datetime.now(UTC).isoformat()
    sj = json.dumps(state, default=str)
    conn = await _get_db()
    try:
        c = await conn.execute(
            "INSERT INTO checkpoints VALUES(?,?,?,?,?)ON CONFLICT(task_id)"
            "DO UPDATE SET state=excluded.state,progress=excluded.progress,"
            "updated_at=excluded.updated_at",
            (task_id, sj, progress_pct, now, now),
        )
        await conn.commit()
        return {
            "task_id": task_id,
            "progress_pct": progress_pct,
            "checkpoint_size_bytes": len(sj.encode()),
            "action": "inserted" if c.rowcount == 1 else "updated",
        }
    finally:
        await conn.close()


async def research_checkpoint_resume(task_id: str) -> dict[str, Any]:
    """Retrieve checkpoint."""
    if not task_id or not isinstance(task_id, str):
        raise ValueError("task_id required")

    conn = await _get_db()
    try:
        c = await conn.execute(
            "SELECT state,progress,updated_at FROM checkpoints WHERE task_id=?",
            (task_id,),
        )
        r = await c.fetchone()
        if not r:
            return {
                "task_id": task_id,
                "state": None,
                "progress_pct": None,
                "last_updated": None,
                "age_seconds": None,
            }
        u = datetime.fromisoformat(r[2])
        a = (datetime.now(UTC) - u).total_seconds()
        return {
            "task_id": task_id,
            "state": json.loads(r[0]),
            "progress_pct": r[1],
            "last_updated": u.isoformat(),
            "age_seconds": round(a, 1),
        }
    finally:
        await conn.close()


async def research_checkpoint_list(status: str = "all") -> dict[str, Any]:
    """List checkpoints with filtering. Removes entries >7 days old."""
    if status not in ("all", "incomplete", "stale"):
        raise ValueError("invalid status")

    conn = await _get_db()
    try:
        c = await conn.execute(
            "DELETE FROM checkpoints WHERE updated_at<?",
            ((datetime.now(UTC) - timedelta(days=7)).isoformat(),),
        )
        d = c.rowcount
        await conn.commit()

        c = await conn.execute("SELECT task_id,progress,updated_at FROM checkpoints")
        r = await c.fetchall()

        n = datetime.now(UTC)
        cp, ic = [], 0
        for tid, p, ts in r:
            u = datetime.fromisoformat(ts)
            ag = (n - u).total_seconds()
            if status == "incomplete" and p >= 100:
                continue
            if status == "stale" and ag < 86400:
                continue
            if p < 100:
                ic += 1
            cp.append({"task_id": tid, "progress": p, "age_seconds": round(ag, 1)})
        return {"checkpoints": cp, "total": len(cp), "incomplete_count": ic, "deleted_old_count": d}
    finally:
        await conn.close()
