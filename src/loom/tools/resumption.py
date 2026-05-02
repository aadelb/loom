"""Stateful Resumption Engine — checkpoint-based task recovery via SQLite."""

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
        """CREATE TABLE IF NOT EXISTS checkpoints (
            task_id TEXT PRIMARY KEY, state TEXT NOT NULL, progress REAL DEFAULT 0.0,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"""
    )
    await conn.commit()
    return conn


async def research_checkpoint_save(
    task_id: str, state: dict[str, Any], progress_pct: float = 0.0
) -> dict[str, Any]:
    """Save research progress to SQLite checkpoint. Atomically upserts task state."""
    if not task_id or not isinstance(task_id, str):
        raise ValueError("task_id must be a non-empty string")
    if not isinstance(state, dict):
        raise ValueError("state must be a dictionary")
    if not 0.0 <= progress_pct <= 100.0:
        raise ValueError("progress_pct must be between 0.0 and 100.0")

    now = datetime.now(UTC).isoformat()
    state_json = json.dumps(state, default=str)
    state_bytes = len(state_json.encode("utf-8"))

    conn = await _get_db()
    try:
        cursor = await conn.execute(
            """INSERT INTO checkpoints (task_id, state, progress, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(task_id) DO UPDATE SET
                state=excluded.state, progress=excluded.progress, updated_at=excluded.updated_at""",
            (task_id, state_json, progress_pct, now, now),
        )
        await conn.commit()
        logger.info("checkpoint_saved", task_id=task_id, progress=progress_pct, size=state_bytes)
        return {
            "task_id": task_id,
            "progress_pct": progress_pct,
            "checkpoint_size_bytes": state_bytes,
            "action": "inserted" if cursor.rowcount == 1 else "updated",
        }
    finally:
        await conn.close()


async def research_checkpoint_resume(task_id: str) -> dict[str, Any]:
    """Retrieve saved checkpoint for task resumption."""
    if not task_id or not isinstance(task_id, str):
        raise ValueError("task_id must be a non-empty string")

    conn = await _get_db()
    try:
        cursor = await conn.execute(
            "SELECT state, progress, updated_at FROM checkpoints WHERE task_id = ?",
            (task_id,),
        )
        row = await cursor.fetchone()

        if not row:
            logger.info("checkpoint_not_found", task_id=task_id)
            return {
                "task_id": task_id,
                "state": None,
                "progress_pct": None,
                "last_updated": None,
                "age_seconds": None,
            }

        state = json.loads(row[0])
        updated_at = datetime.fromisoformat(row[2])
        age_seconds = (datetime.now(UTC) - updated_at).total_seconds()

        logger.info("checkpoint_resumed", task_id=task_id, progress=row[1])
        return {
            "task_id": task_id,
            "state": state,
            "progress_pct": row[1],
            "last_updated": updated_at.isoformat(),
            "age_seconds": round(age_seconds, 1),
        }
    finally:
        await conn.close()


async def research_checkpoint_list(status: str = "all") -> dict[str, Any]:
    """List all checkpoints with filtering. Deletes checkpoints older than 7 days."""
    if status not in ("all", "incomplete", "stale"):
        raise ValueError('status must be "all", "incomplete", or "stale"')

    conn = await _get_db()
    try:
        cutoff = datetime.now(UTC) - timedelta(days=7)
        cursor = await conn.execute(
            "DELETE FROM checkpoints WHERE updated_at < ?", (cutoff.isoformat(),)
        )
        deleted_old = cursor.rowcount
        await conn.commit()

        cursor = await conn.execute(
            "SELECT task_id, progress, updated_at FROM checkpoints"
        )
        rows = await cursor.fetchall()

        now = datetime.now(UTC)
        checkpoints, incomplete_count = [], 0

        for task_id, progress, updated_at_str in rows:
            updated_at = datetime.fromisoformat(updated_at_str)
            age_seconds = (now - updated_at).total_seconds()

            if status == "incomplete" and progress >= 100.0:
                continue
            if status == "stale" and age_seconds < 86400:
                continue

            if progress < 100.0:
                incomplete_count += 1
            checkpoints.append({
                "task_id": task_id,
                "progress": progress,
                "age_seconds": round(age_seconds, 1),
            })

        logger.info("checkpoint_list", status=status, total=len(checkpoints))
        return {
            "checkpoints": checkpoints,
            "total": len(checkpoints),
            "incomplete_count": incomplete_count,
            "deleted_old_count": deleted_old,
        }
    finally:
        await conn.close()
