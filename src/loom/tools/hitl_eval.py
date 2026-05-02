"""Human-in-the-Loop evaluation interface for strategy refinement.

Provides three tools for collecting human feedback on strategy+response pairs:
  - research_hitl_submit: Submit a strategy+response pair for human evaluation
  - research_hitl_evaluate: Record human evaluation with score and notes
  - research_hitl_queue: List evaluations awaiting human review
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger("loom.tools.hitl_eval")

# Database path in user's loom directory
_DB_PATH = Path.home() / ".loom" / "hitl_eval.db"
_LOCK = asyncio.Lock()


async def _get_db() -> aiosqlite.Connection:
    """Get or create the SQLite database connection."""
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(_DB_PATH))
    conn.row_factory = aiosqlite.Row
    return conn


async def _init_db() -> None:
    """Initialize the database schema if not exists."""
    async with _LOCK:
        conn = await _get_db()
        try:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluations (
                    id TEXT PRIMARY KEY,
                    strategy TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    model TEXT NOT NULL DEFAULT 'unknown',
                    submitted TEXT NOT NULL,
                    human_score REAL,
                    human_notes TEXT,
                    tags TEXT,
                    evaluated BOOL NOT NULL DEFAULT 0
                )
                """
            )
            await conn.commit()
        finally:
            await conn.close()


async def research_hitl_submit(
    strategy: str,
    prompt: str,
    response: str,
    model: str = "unknown",
) -> dict[str, Any]:
    """Submit a strategy+response pair for human evaluation.

    Stores the evaluation request in a SQLite queue with a unique eval_id.

    Args:
        strategy: Strategy name or description (e.g., "jailbreak_v1")
        prompt: The prompt sent to the model
        response: The model's response to evaluate
        model: Model identifier (e.g., "gpt-4", "claude-3-opus")

    Returns:
        {
            "eval_id": "uuid-string",
            "status": "pending",
            "strategy": strategy,
            "model": model,
            "submitted": ISO8601 timestamp
        }
    """
    await _init_db()

    eval_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    conn = await _get_db()
    try:
        await conn.execute(
            """
            INSERT INTO evaluations
            (id, strategy, prompt, response, model, submitted, evaluated)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (eval_id, strategy, prompt, response, model, now),
        )
        await conn.commit()
        logger.info(
            "hitl_submit",
            eval_id=eval_id,
            strategy=strategy,
            model=model,
        )
    finally:
        await conn.close()

    return {
        "eval_id": eval_id,
        "status": "pending",
        "strategy": strategy,
        "model": model,
        "submitted": now,
    }


async def research_hitl_evaluate(
    eval_id: str,
    score: float,
    notes: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Record human evaluation of a strategy's output.

    Updates the evaluation record with score (1-10), optional notes, and tags.

    Args:
        eval_id: The evaluation ID returned from research_hitl_submit
        score: Human score (1-10 scale, where 10 = most effective)
        notes: Optional human commentary on the response
        tags: List of tags describing the response quality:
              ["effective", "partial", "refused", "hallucinated", "dangerous", "safe"]

    Returns:
        {
            "eval_id": eval_id,
            "score": score,
            "notes": notes,
            "tags": tags,
            "evaluated": ISO8601 timestamp
        }
    """
    await _init_db()
    now = datetime.now(UTC).isoformat()
    tags_str = ",".join(tags or [])

    conn = await _get_db()
    try:
        await conn.execute(
            """
            UPDATE evaluations
            SET human_score = ?, human_notes = ?, tags = ?, evaluated = 1
            WHERE id = ?
            """,
            (score, notes, tags_str, eval_id),
        )
        await conn.commit()
        logger.info(
            "hitl_evaluate",
            eval_id=eval_id,
            score=score,
            tags=tags_str,
        )
    finally:
        await conn.close()

    return {
        "eval_id": eval_id,
        "score": score,
        "notes": notes,
        "tags": tags or [],
        "evaluated": now,
    }


async def research_hitl_queue(
    status: str = "pending",
    limit: int = 20,
) -> dict[str, Any]:
    """List evaluations awaiting human review or get stats.

    Args:
        status: Filter by status ("pending" or "evaluated")
        limit: Maximum number of records to return

    Returns:
        {
            "queue": [
                {
                    "eval_id": str,
                    "strategy": str,
                    "prompt_preview": str (first 100 chars),
                    "model": str,
                    "submitted": ISO8601 timestamp
                },
                ...
            ],
            "total_pending": int,
            "total_evaluated": int,
            "avg_score": float | null
        }
    """
    await _init_db()

    conn = await _get_db()
    try:
        # Build query based on status filter
        if status == "pending":
            where_clause = "WHERE evaluated = 0"
        elif status == "evaluated":
            where_clause = "WHERE evaluated = 1"
        else:
            where_clause = ""

        # Get queue items
        cursor = await conn.execute(
            f"""
            SELECT id, strategy, prompt, model, submitted
            FROM evaluations
            {where_clause}
            ORDER BY submitted DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()

        queue = []
        for row in rows:
            queue.append(
                {
                    "eval_id": row[0],
                    "strategy": row[1],
                    "prompt_preview": (row[2][:100] + "...") if len(row[2]) > 100 else row[2],
                    "model": row[3],
                    "submitted": row[4],
                }
            )

        # Get stats
        pending = await conn.execute(
            "SELECT COUNT(*) FROM evaluations WHERE evaluated = 0"
        )
        pending_count = (await pending.fetchone())[0]

        evaluated = await conn.execute(
            "SELECT COUNT(*) FROM evaluations WHERE evaluated = 1"
        )
        evaluated_count = (await evaluated.fetchone())[0]

        avg = await conn.execute(
            "SELECT AVG(human_score) FROM evaluations WHERE evaluated = 1"
        )
        avg_row = await avg.fetchone()
        avg_score = avg_row[0] if avg_row and avg_row[0] is not None else None

    finally:
        await conn.close()

    logger.info(
        "hitl_queue",
        status=status,
        pending=pending_count,
        evaluated=evaluated_count,
        avg_score=avg_score,
    )

    return {
        "queue": queue,
        "total_pending": pending_count,
        "total_evaluated": evaluated_count,
        "avg_score": avg_score,
    }
