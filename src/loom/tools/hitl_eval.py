"""Human-in-the-Loop evaluation interface for strategy refinement.

Provides three tools for collecting human feedback on strategy+response pairs:
  - research_hitl_submit: Submit a strategy+response pair for human evaluation
  - research_hitl_evaluate: Record human evaluation with score and notes
  - research_hitl_queue: List evaluations awaiting human review
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, UTC
from pathlib import Path

import aiosqlite

logger = logging.getLogger("loom.tools.hitl_eval")

_DB_PATH = Path.home() / ".loom" / "hitl_eval.db"
_LOCK = asyncio.Lock()


async def _init_db() -> None:
    """Initialize database schema if not exists."""
    async with _LOCK:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(str(_DB_PATH))
        await conn.execute(
            """CREATE TABLE IF NOT EXISTS evaluations (
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
            )"""
        )
        await conn.commit()
        await conn.close()


async def research_hitl_submit(
    strategy: str,
    prompt: str,
    response: str,
    model: str = "unknown",
) -> dict:
    """Submit a strategy+response pair for human evaluation.

    Args:
        strategy: Strategy name or description
        prompt: The prompt sent to the model
        response: The model's response to evaluate
        model: Model identifier

    Returns:
        {eval_id, status, strategy, model, submitted}
    """
    await _init_db()
    eval_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    conn = await aiosqlite.connect(str(_DB_PATH))
    await conn.execute(
        "INSERT INTO evaluations (id,strategy,prompt,response,model,submitted,evaluated) VALUES (?,?,?,?,?,?,0)",
        (eval_id, strategy, prompt, response, model, now),
    )
    await conn.commit()
    await conn.close()
    logger.info("hitl_submit", eval_id=eval_id, strategy=strategy, model=model)

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
) -> dict:
    """Record human evaluation of a strategy's output.

    Args:
        eval_id: Evaluation ID from research_hitl_submit
        score: Human score (1-10)
        notes: Optional human commentary
        tags: Quality tags: effective, partial, refused, hallucinated, dangerous, safe

    Returns:
        {eval_id, score, notes, tags, evaluated}
    """
    await _init_db()
    now = datetime.now(UTC).isoformat()
    tags_str = ",".join(tags or [])

    conn = await aiosqlite.connect(str(_DB_PATH))
    await conn.execute(
        "UPDATE evaluations SET human_score=?, human_notes=?, tags=?, evaluated=1 WHERE id=?",
        (score, notes, tags_str, eval_id),
    )
    await conn.commit()
    await conn.close()
    logger.info("hitl_evaluate", eval_id=eval_id, score=score, tags=tags_str)

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
) -> dict:
    """List evaluations awaiting human review.

    Args:
        status: Filter by "pending" or "evaluated"
        limit: Maximum records to return (1-100)

    Returns:
        {queue: [{eval_id, strategy, prompt_preview, model, submitted}],
         total_pending, total_evaluated, avg_score}
    """
    await _init_db()

    conn = await aiosqlite.connect(str(_DB_PATH))
    where = "WHERE evaluated=0" if status == "pending" else "WHERE evaluated=1" if status == "evaluated" else ""

    cursor = await conn.execute(
        f"SELECT id, strategy, prompt, model, submitted FROM evaluations {where} ORDER BY submitted DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()

    queue = [
        {
            "eval_id": row[0],
            "strategy": row[1],
            "prompt_preview": (row[2][:100] + "...") if len(row[2]) > 100 else row[2],
            "model": row[3],
            "submitted": row[4],
        }
        for row in rows
    ]

    pending = await conn.execute("SELECT COUNT(*) FROM evaluations WHERE evaluated=0")
    pending_count = (await pending.fetchone())[0]

    evaluated = await conn.execute("SELECT COUNT(*) FROM evaluations WHERE evaluated=1")
    evaluated_count = (await evaluated.fetchone())[0]

    avg = await conn.execute("SELECT AVG(human_score) FROM evaluations WHERE evaluated=1")
    avg_score = (await avg.fetchone())[0]

    await conn.close()
    logger.info("hitl_queue", status=status, pending=pending_count, evaluated=evaluated_count, avg_score=avg_score)

    return {
        "queue": queue,
        "total_pending": pending_count,
        "total_evaluated": evaluated_count,
        "avg_score": avg_score,
    }
