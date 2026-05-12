"""Strategy Gamification system — leaderboards, challenges, competitions."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite
from loom.error_responses import handle_tool_errors

logger = logging.getLogger(__name__)

DB_PATH = Path.home() / ".loom" / "gamification.db"
_db_conn: aiosqlite.Connection | None = None


async def _init_db() -> None:
    """Initialize database schema (idempotent)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(DB_PATH))
    try:
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS scores ("
            "  id INTEGER PRIMARY KEY, "
            "  strategy TEXT NOT NULL, "
            "  metric TEXT NOT NULL, "
            "  value REAL NOT NULL, "
            "  timestamp TEXT NOT NULL, "
            "  model TEXT, "
            "  run_id TEXT"
            ")"
        )
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS challenges ("
            "  id INTEGER PRIMARY KEY, "
            "  challenge_id TEXT UNIQUE NOT NULL, "
            "  name TEXT NOT NULL, "
            "  target_model TEXT NOT NULL, "
            "  success_criteria TEXT NOT NULL, "
            "  reward_credits INTEGER NOT NULL, "
            "  status TEXT NOT NULL, "
            "  created_at TEXT NOT NULL, "
            "  attempts INTEGER DEFAULT 0, "
            "  completions INTEGER DEFAULT 0"
            ")"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_scores_metric ON scores(metric, timestamp)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_challenges_status ON challenges(status)"
        )
        await conn.commit()
        logger.debug("Database schema initialized")
    finally:
        await conn.close()


async def _get_db() -> aiosqlite.Connection:
    """Get or create singleton database connection."""
    global _db_conn
    if _db_conn is None:
        await _init_db()
        _db_conn = await aiosqlite.connect(str(DB_PATH))
        _db_conn.row_factory = aiosqlite.Row  # Named row access
        logger.debug("Database connection established")
    return _db_conn


@asynccontextmanager
async def _db_context() -> Any:
    """Context manager for database operations with automatic cleanup."""
    conn = await _get_db()
    try:
        yield conn
    except Exception as e:
        logger.error(f"Database operation failed: {e}", exc_info=True)
        raise


@handle_tool_errors("research_leaderboard")
async def research_leaderboard(
    metric: str = "total_bypasses",
    period: str = "all_time",
    limit: int = 20,
) -> dict[str, Any]:
    """Show strategy leaderboard ranked by metric.

    Valid metrics: total_bypasses, avg_asr, unique_models_bypassed, stealth_score, novelty_score.
    Periods: today, week, month, all_time.
    """
    valid_metrics = {
        "total_bypasses",
        "avg_asr",
        "unique_models_bypassed",
        "stealth_score",
        "novelty_score",
    }
    if metric not in valid_metrics:
        logger.warning(f"Invalid metric requested: {metric}")
        return {"error": f"Unknown metric: {metric}"}

    valid_periods = {"today", "week", "month", "all_time"}
    if period not in valid_periods:
        logger.warning(f"Invalid period requested: {period}")
        return {"error": f"Unknown period: {period}"}

    if not (1 <= limit <= 100):
        logger.warning(f"Invalid limit requested: {limit}")
        return {"error": "Limit must be 1-100"}

    async with _db_context() as conn:
        try:
            now = datetime.now(UTC)
            cutoff = {
                "today": (now - timedelta(days=1)).isoformat(),
                "week": (now - timedelta(days=7)).isoformat(),
                "month": (now - timedelta(days=30)).isoformat(),
                "all_time": "1970-01-01",
            }[period]

            queries = {
                "total_bypasses": (
                    "SELECT strategy, COUNT(*) as value FROM scores "
                    "WHERE metric = 'bypass' AND timestamp >= ? "
                    "GROUP BY strategy ORDER BY value DESC LIMIT ?",
                    (cutoff, limit),
                ),
                "avg_asr": (
                    "SELECT strategy, AVG(value) as value FROM scores "
                    "WHERE metric = 'asr' AND timestamp >= ? "
                    "GROUP BY strategy ORDER BY value DESC LIMIT ?",
                    (cutoff, limit),
                ),
                "unique_models_bypassed": (
                    "SELECT strategy, COUNT(DISTINCT model) as value FROM scores "
                    "WHERE metric = 'bypass' AND timestamp >= ? AND model IS NOT NULL "
                    "GROUP BY strategy ORDER BY value DESC LIMIT ?",
                    (cutoff, limit),
                ),
                "stealth_score": (
                    "SELECT strategy, AVG(value) as value FROM scores "
                    "WHERE metric = 'stealth' AND timestamp >= ? "
                    "GROUP BY strategy ORDER BY value DESC LIMIT ?",
                    (cutoff, limit),
                ),
                "novelty_score": (
                    "SELECT strategy, AVG(value) as value FROM scores "
                    "WHERE metric = 'novelty' AND timestamp >= ? "
                    "GROUP BY strategy ORDER BY value DESC LIMIT ?",
                    (cutoff, limit),
                ),
            }

            query, params = queries[metric]
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            rankings = [
                {"rank": i + 1, "strategy": row[0], "value": round(float(row[1]), 2), "trend": "up"}
                for i, row in enumerate(rows)
            ]

            cursor = await conn.execute("SELECT COUNT(DISTINCT strategy) FROM scores")
            total_row = await cursor.fetchone()
            total = (total_row[0] if total_row else 0) or 0

            logger.debug(
                f"Leaderboard generated: {metric} for {period} with "
                f"{len(rankings)} entries"
            )
            return {
                "metric": metric,
                "period": period,
                "rankings": rankings,
                "total_strategies": total,
                "timestamp": now.isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to generate leaderboard: {e}", exc_info=True)
            return {"error": f"Leaderboard generation failed: {e!s}"}


@handle_tool_errors("research_challenge_create")
async def research_challenge_create(
    name: str,
    target_model: str,
    success_criteria: str = "asr > 0.7",
    reward_credits: int = 100,
) -> dict[str, Any]:
    """Create a new challenge for users to attempt."""
    if not (1 <= len(name) <= 100):
        logger.warning(f"Invalid challenge name length: {len(name)}")
        return {"error": "Name must be 1-100 chars"}
    if not (1 <= len(target_model) <= 50):
        logger.warning(f"Invalid target model length: {len(target_model)}")
        return {"error": "Target model must be 1-50 chars"}
    if not (1 <= len(success_criteria) <= 200):
        logger.warning(f"Invalid criteria length: {len(success_criteria)}")
        return {"error": "Criteria must be 1-200 chars"}
    if not (0 <= reward_credits <= 10000):
        logger.warning(f"Invalid reward credits: {reward_credits}")
        return {"error": "Reward must be 0-10000"}

    challenge_id = f"challenge_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()

    async with _db_context() as conn:
        try:
            await conn.execute(
                "INSERT INTO challenges ("
                "challenge_id, name, target_model, success_criteria, reward_credits, "
                "status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (challenge_id, name, target_model, success_criteria, reward_credits, "active", now),
            )
            await conn.commit()
            logger.info(f"Challenge created: {challenge_id}")
            return {
                "challenge_id": challenge_id,
                "name": name,
                "target": target_model,
                "criteria": success_criteria,
                "reward": reward_credits,
                "status": "active",
                "created_at": now,
            }
        except Exception as e:
            logger.error(f"Failed to create challenge: {e}", exc_info=True)
            return {"error": f"Challenge creation failed: {e!s}"}


@handle_tool_errors("research_challenge_list")
async def research_challenge_list(status: str = "active") -> dict[str, Any]:
    """List challenges filtered by status (active, completed, all)."""
    valid_statuses = {"active", "completed", "all"}
    if status not in valid_statuses:
        logger.warning(f"Invalid status requested: {status}")
        return {"error": f"Unknown status: {status}"}

    async with _db_context() as conn:
        try:
            # Use explicit column list to avoid SELECT * brittleness
            if status == "all":
                query = (
                    "SELECT id, challenge_id, name, target_model, "
                    "success_criteria, reward_credits, status, created_at, "
                    "attempts, completions FROM challenges ORDER BY created_at DESC"
                )
                cursor = await conn.execute(query)
            else:
                query = (
                    "SELECT id, challenge_id, name, target_model, "
                    "success_criteria, reward_credits, status, created_at, "
                    "attempts, completions FROM challenges "
                    "WHERE status = ? ORDER BY created_at DESC"
                )
                cursor = await conn.execute(query, (status,))

            rows = await cursor.fetchall()

            # Unpack tuples safely with explicit column mapping
            challenges = [
                {
                    "id": row[1],  # challenge_id (use challenge_id, not auto-increment id)
                    "name": row[2],
                    "target_model": row[3],
                    "criteria": row[4],
                    "reward": row[5],
                    "status": row[6],
                    "created_at": row[7],
                    "attempts": row[8],
                    "completions": row[9],
                }
                for row in rows
            ]

            active_cursor = await conn.execute(
                "SELECT COUNT(*) FROM challenges WHERE status = 'active'"
            )
            active_row = await active_cursor.fetchone()
            active_count = active_row[0] if active_row else 0

            logger.debug(f"Listed {len(challenges)} challenges with status={status}")
            return {
                "challenges": challenges,
                "active_count": active_count,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        except Exception as e:
            logger.error(f"Failed to list challenges: {e}", exc_info=True)
            return {"error": f"Challenge listing failed: {e!s}"}
