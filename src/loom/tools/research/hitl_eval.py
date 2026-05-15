"""Human-in-the-Loop evaluation interface for strategy refinement.

Provides three tools for collecting human feedback on strategy+response pairs:
  - research_hitl_submit: Submit a strategy+response pair for human evaluation
  - research_hitl_evaluate: Record human evaluation with score and notes
  - research_hitl_queue: List evaluations awaiting human review
"""

from __future__ import annotations
from loom.error_responses import handle_tool_errors

import asyncio
import logging
import uuid
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import aiosqlite

try:
    from loom.text_utils import truncate
except ImportError:
    def truncate(text, max_chars=500, *, suffix="..."):
        if len(text) <= max_chars: return text
        return text[:max_chars - len(suffix)] + suffix

logger = logging.getLogger("loom.tools.hitl_eval")

_DB_PATH = Path.home() / ".loom" / "hitl_eval.db"
_LOCK: asyncio.Lock | None = None

# Valid evaluation tags
_VALID_TAGS = {"effective", "partial", "refused", "hallucinated", "dangerous", "safe"}
_MIN_SCORE, _MAX_SCORE = 1.0, 10.0
_MAX_PROMPT_LENGTH = 10_000
_MAX_RESPONSE_LENGTH = 50_000
_MAX_NOTES_LENGTH = 2_000


def _get_lock() -> asyncio.Lock:
    """Get or create the lock."""
    global _LOCK
    if _LOCK is None:
        _LOCK = asyncio.Lock()
    return _LOCK


async def _init_db() -> None:
    """Initialize database schema if not exists."""
    async with _get_lock():
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
                evaluated BOOL NOT NULL DEFAULT 0,
                evaluated_at TEXT
            )"""
        )
        await conn.commit()
        await conn.close()


def _validate_uuid(value: str) -> bool:
    """Check if string is a valid UUID v4."""
    try:
        uuid.UUID(value, version=4)
        return True
    except (ValueError, AttributeError):
        return False


def _validate_score(score: float) -> tuple[bool, str]:
    """Validate human score is in [1.0, 10.0]."""
    if not isinstance(score, (int, float)):
        return False, "score must be numeric"
    if score < _MIN_SCORE or score > _MAX_SCORE:
        return False, f"score must be between {_MIN_SCORE} and {_MAX_SCORE}"
    return True, ""


def _validate_tags(tags: list[str] | None) -> tuple[bool, str]:
    """Validate tags are from allowed set."""
    if tags is None:
        return True, ""
    if not isinstance(tags, list):
        return False, "tags must be a list"
    invalid = set(tags) - _VALID_TAGS
    if invalid:
        return False, f"invalid tags: {invalid}. allowed: {_VALID_TAGS}"
    return True, ""


@handle_tool_errors("research_hitl_submit")
async def research_hitl_submit(
    strategy: str,
    prompt: str,
    response: str,
    model: str = "unknown",
) -> dict[str, Any]:
    """Submit a strategy+response pair for human evaluation.

    Args:
        strategy: Strategy name or description (required)
        prompt: The prompt sent to the model (max 10,000 chars)
        response: The model's response to evaluate (max 50,000 chars)
        model: Model identifier (default: 'unknown')

    Returns:
        {eval_id, status, strategy, model, submitted} or {error, tool}
    """
    try:
        # Input validation
        if not strategy or not isinstance(strategy, str):
            return {"error": "strategy must be a non-empty string", "tool": "research_hitl_submit"}
        if not prompt or not isinstance(prompt, str):
            return {"error": "prompt must be a non-empty string", "tool": "research_hitl_submit"}
        if not response or not isinstance(response, str):
            return {"error": "response must be a non-empty string", "tool": "research_hitl_submit"}

        # Truncate large inputs to prevent DB bloat
        prompt_safe = truncate(prompt, _MAX_PROMPT_LENGTH)
        response_safe = truncate(response, _MAX_RESPONSE_LENGTH)

        await _init_db()
        eval_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        async with _get_lock():
            conn = await aiosqlite.connect(str(_DB_PATH))
            try:
                await conn.execute(
                    "INSERT INTO evaluations (id,strategy,prompt,response,model,submitted,evaluated) VALUES (?,?,?,?,?,?,0)",
                    (eval_id, strategy, prompt_safe, response_safe, model, now),
                )
                await conn.commit()
            finally:
                await conn.close()

        logger.info("hitl_submit eval_id=%s strategy=%s model=%s", eval_id, strategy, model)

        return {
            "eval_id": eval_id,
            "status": "pending",
            "strategy": strategy,
            "model": model,
            "submitted": now,
        }
    except Exception as exc:
        logger.error("hitl_submit failed: %s", exc, exc_info=True)
        return {"error": str(exc), "tool": "research_hitl_submit"}


@handle_tool_errors("research_hitl_evaluate")
async def research_hitl_evaluate(
    eval_id: str,
    score: float,
    notes: str = "",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Record human evaluation of a strategy's output.

    Args:
        eval_id: Evaluation ID from research_hitl_submit (must be valid UUID)
        score: Human score (1.0 to 10.0, inclusive)
        notes: Optional human commentary (max 2,000 chars)
        tags: Quality tags (subset of: effective, partial, refused, hallucinated, dangerous, safe)

    Returns:
        {eval_id, score, notes, tags, evaluated_at} or {error, tool}
    """
    try:
        # Input validation
        if not _validate_uuid(eval_id):
            return {"error": f"eval_id must be a valid UUID, got: {eval_id}", "tool": "research_hitl_evaluate"}

        is_valid, msg = _validate_score(score)
        if not is_valid:
            return {"error": msg, "tool": "research_hitl_evaluate"}

        is_valid, msg = _validate_tags(tags)
        if not is_valid:
            return {"error": msg, "tool": "research_hitl_evaluate"}

        notes_safe = truncate(notes, _MAX_NOTES_LENGTH)

        await _init_db()
        now = datetime.now(UTC).isoformat()
        tags_str = ",".join(sorted(tags or []))

        async with _get_lock():
            conn = await aiosqlite.connect(str(_DB_PATH))
            try:
                cursor = await conn.execute(
                    "UPDATE evaluations SET human_score=?, human_notes=?, tags=?, evaluated=1, evaluated_at=? WHERE id=?",
                    (score, notes_safe, tags_str, now, eval_id),
                )
                await conn.commit()

                # Verify the update affected a row
                if cursor.rowcount == 0:
                    logger.warning("hitl_evaluate: no record found for eval_id=%s", eval_id)
                    return {"error": f"eval_id not found: {eval_id}", "tool": "research_hitl_evaluate"}
            finally:
                await conn.close()

        logger.info("hitl_evaluate eval_id=%s score=%s tags=%s", eval_id, score, tags_str)

        return {
            "eval_id": eval_id,
            "score": score,
            "notes": notes_safe,
            "tags": sorted(tags or []),
            "evaluated_at": now,
        }
    except Exception as exc:
        logger.error("hitl_evaluate failed: %s", exc, exc_info=True)
        return {"error": str(exc), "tool": "research_hitl_evaluate"}


@handle_tool_errors("research_hitl_queue")
async def research_hitl_queue(
    status: str = "pending",
    limit: int = 20,
) -> dict[str, Any]:
    """List evaluations awaiting human review.

    Args:
        status: Filter by "pending" or "evaluated" (default: pending)
        limit: Maximum records to return (1-100, default: 20)

    Returns:
        {queue: [{eval_id, strategy, prompt_preview, model, submitted}],
         total_pending, total_evaluated, avg_score} or {error, tool}
    """
    try:
        # Input validation
        if status not in ("pending", "evaluated", "all"):
            return {"error": f"status must be 'pending', 'evaluated', or 'all', got: {status}", "tool": "research_hitl_queue"}
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            return {"error": "limit must be an integer between 1 and 100", "tool": "research_hitl_queue"}

        await _init_db()

        async with _get_lock():
            conn = await aiosqlite.connect(str(_DB_PATH))
            try:
                # Build WHERE clause safely (parameterized queries only)
                if status == "pending":
                    where_clause = "WHERE evaluated=0"
                elif status == "evaluated":
                    where_clause = "WHERE evaluated=1"
                else:
                    where_clause = ""

                cursor = await conn.execute(
                    f"SELECT id, strategy, prompt, model, submitted FROM evaluations {where_clause} ORDER BY submitted DESC LIMIT ?",
                    (limit,),
                )
                rows = await cursor.fetchall()

                queue = [
                    {
                        "eval_id": row[0],
                        "strategy": row[1],
                        "prompt_preview": truncate(row[2], 100),
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
                avg_row = await avg.fetchone()
                avg_score = avg_row[0] if avg_row and avg_row[0] is not None else 0.0

            finally:
                await conn.close()

        logger.info("hitl_queue status=%s limit=%d pending=%d evaluated=%d avg_score=%s", status, limit, pending_count, evaluated_count, avg_score)

        return {
            "queue": queue,
            "total_pending": pending_count,
            "total_evaluated": evaluated_count,
            "avg_score": round(avg_score, 2) if avg_score else 0.0,
        }
    except Exception as exc:
        logger.error("hitl_queue failed: %s", exc, exc_info=True)
        return {"error": str(exc), "tool": "research_hitl_queue"}
