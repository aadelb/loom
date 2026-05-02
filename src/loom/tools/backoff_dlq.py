"""Dead Letter Queue (DLQ) with exponential backoff for failed tool calls."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("loom.tools.backoff_dlq")

DLQ_DB_PATH = Path.home() / ".loom" / "dlq.db"
BASE_DELAY_SECONDS = 60
MAX_DELAY_SECONDS = 3600
MAX_RETRY_COUNT = 5
_dlq_lock = asyncio.Lock()


async def _ensure_dlq_table() -> None:
    """Ensure DLQ SQLite table exists."""
    DLQ_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(DLQ_DB_PATH)) as db:
        await db.execute(
            """CREATE TABLE IF NOT EXISTS dead_letters (
                id TEXT PRIMARY KEY, tool_name TEXT NOT NULL, params TEXT NOT NULL,
                error TEXT NOT NULL, retry_count INTEGER DEFAULT 0, created TEXT NOT NULL,
                next_retry TEXT NOT NULL, status TEXT DEFAULT 'pending')"""
        )
        await db.commit()


def _calculate_next_retry(retry_count: int) -> str:
    """Calculate next retry time with exponential backoff."""
    delay = min(BASE_DELAY_SECONDS * (2 ** retry_count), MAX_DELAY_SECONDS)
    return (datetime.now(UTC) + timedelta(seconds=delay)).isoformat()


async def research_dlq_push(
    tool_name: str, params: dict[str, Any], error: str, retry_count: int = 0
) -> dict[str, Any]:
    """Push failed tool call to Dead Letter Queue."""
    await _ensure_dlq_table()
    item_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    next_retry = _calculate_next_retry(retry_count)
    status = "exhausted" if retry_count >= MAX_RETRY_COUNT else "pending"

    async with _dlq_lock:
        async with aiosqlite.connect(str(DLQ_DB_PATH)) as db:
            await db.execute(
                "INSERT INTO dead_letters VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (item_id, tool_name, json.dumps(params), error, retry_count, now, next_retry, status),
            )
            await db.commit()
    logger.info("dlq_push", item_id=item_id, tool_name=tool_name, retry_count=retry_count)
    return {"id": item_id, "tool_name": tool_name, "retry_count": retry_count, "next_retry_at": next_retry}


async def research_dlq_list(status: str = "pending") -> dict[str, Any]:
    """List items in the Dead Letter Queue."""
    await _ensure_dlq_table()
    query = "SELECT id, tool_name, error, retry_count, created, next_retry FROM dead_letters"
    params_list = []
    if status != "all":
        query += " WHERE status = ?"
        params_list.append(status)
    query += " ORDER BY created DESC"

    async with _dlq_lock:
        async with aiosqlite.connect(str(DLQ_DB_PATH)) as db:
            db.row_factory = aiosqlite.Row
            rows = await (await db.execute(query, params_list)).fetchall()

    return {"items": [dict(r) for r in rows], "total": len(rows)}


async def research_dlq_retry(item_id: str = "") -> dict[str, Any]:
    """Retry DLQ items by ID or all pending items past next_retry time."""
    await _ensure_dlq_table()
    retried_count = exhausted_count = 0

    async with _dlq_lock:
        async with aiosqlite.connect(str(DLQ_DB_PATH)) as db:
            if item_id:
                row = await (await db.execute(
                    "SELECT retry_count, status FROM dead_letters WHERE id = ?", (item_id,)
                )).fetchone()
                if not row:
                    return {"retried": 0, "exhausted": 0, "remaining": 0}
                new_retry_count = row[0] + 1
                new_status = "exhausted" if new_retry_count >= MAX_RETRY_COUNT else "retrying"
                await db.execute(
                    "UPDATE dead_letters SET retry_count = ?, status = ?, next_retry = ? WHERE id = ?",
                    (new_retry_count, new_status, _calculate_next_retry(new_retry_count), item_id),
                )
                retried_count, exhausted_count = (1, 0) if new_status == "retrying" else (0, 1)
            else:
                now = datetime.now(UTC).isoformat()
                rows = await (await db.execute(
                    "SELECT id, retry_count FROM dead_letters WHERE status = 'pending' AND next_retry <= ?",
                    (now,),
                )).fetchall()
                for row_id, retry_count in rows:
                    new_retry_count = retry_count + 1
                    new_status = "exhausted" if new_retry_count >= MAX_RETRY_COUNT else "retrying"
                    await db.execute(
                        "UPDATE dead_letters SET retry_count = ?, status = ?, next_retry = ? WHERE id = ?",
                        (new_retry_count, new_status, _calculate_next_retry(new_retry_count), row_id),
                    )
                    exhausted_count += (new_status == "exhausted")
                    retried_count += (new_status == "retrying")
            await db.commit()
            remaining = (await (await db.execute(
                "SELECT COUNT(*) FROM dead_letters WHERE status IN ('pending', 'retrying')"
            )).fetchone())[0]

    return {"retried": retried_count, "exhausted": exhausted_count, "remaining": remaining}
