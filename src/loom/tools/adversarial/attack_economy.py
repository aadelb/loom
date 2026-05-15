"""Attack Economy — marketplace for discovered exploits.

Traders submit jailbreaks/exploits with ASR (attack success rate) to earn credits.
Higher ASR + novelty = more credits. Transparent leaderboard tracks top strategies.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.attack_economy")

# Database path
_ECONOMY_DB = Path.home() / ".loom" / "economy.db"


async def _get_db() -> aiosqlite.Connection:
    """Get or create database connection."""
    _ECONOMY_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(_ECONOMY_DB))
    # Enable foreign keys
    await conn.execute("PRAGMA foreign_keys = ON")
    # Create table if not exists
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_name TEXT NOT NULL,
            target_model TEXT NOT NULL,
            asr REAL NOT NULL,
            description TEXT,
            credits_earned INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            UNIQUE(strategy_name, target_model)
        )"""
    )
    await conn.commit()
    return conn


def _calculate_credits(
    asr: float, strategy_name: str, target_model: str, is_new: bool
) -> int:
    """Calculate credits earned for exploit submission.

    Base: asr * 100
    Novelty bonus: +50 if new strategy name
    Model bonus: +20 if hard model (claude/gpt)
    """
    base = int(asr * 100)
    novelty_bonus = 50 if is_new else 0
    model_bonus = 20 if target_model.lower() in ("claude", "gpt-4", "gpt-5") else 0
    return base + novelty_bonus + model_bonus


@handle_tool_errors("research_economy_submit")
async def research_economy_submit(
    strategy_name: str,
    target_model: str,
    asr: float,
    description: str = "",
) -> dict[str, Any]:
    """Submit discovered exploit to earn credits.

    Args:
        strategy_name: Name of the reframing/jailbreak strategy
        target_model: Target model (claude, gpt-4, etc.)
        asr: Attack success rate (0.0-1.0)
        description: Optional description of the exploit

    Returns:
        Receipt with credits earned, total_credits, timestamp
    """
    if not (0.0 <= asr <= 1.0):
        return {"error": "asr must be 0.0-1.0", "tool": "research_economy_submit"}
    if len(strategy_name) < 3:
        return {"error": "strategy_name must be at least 3 chars", "tool": "research_economy_submit"}

    try:
        conn = await _get_db()
        # Check if strategy+model already exists
        cursor = await conn.execute(
            "SELECT id FROM submissions WHERE strategy_name=? AND target_model=?",
            (strategy_name, target_model),
        )
        existing = await cursor.fetchone()
        is_new = existing is None

        # Calculate credits
        credits = _calculate_credits(asr, strategy_name, target_model, is_new)

        # Insert or update
        now = datetime.now(UTC).isoformat()
        if is_new:
            await conn.execute(
                """INSERT INTO submissions
                   (strategy_name, target_model, asr, description, credits_earned, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (strategy_name, target_model, asr, description, credits, now),
            )
        else:
            await conn.execute(
                """UPDATE submissions SET asr=?, description=?, credits_earned=?, timestamp=?
                   WHERE strategy_name=? AND target_model=?""",
                (asr, description, credits, now, strategy_name, target_model),
            )

        await conn.commit()

        # Get total credits
        cursor = await conn.execute("SELECT SUM(credits_earned) FROM submissions")
        total = await cursor.fetchone()
        total_credits = total[0] if total and total[0] else 0

        return {
            "success": True,
            "strategy_name": strategy_name,
            "target_model": target_model,
            "asr": asr,
            "credits_earned": credits,
            "total_credits": total_credits,
            "is_new": is_new,
            "timestamp": now,
        }
    except Exception as exc:
        logger.exception("research_economy_submit failed")
        return {"error": str(exc), "tool": "research_economy_submit"}
    finally:
        await conn.close()


@handle_tool_errors("research_economy_balance")
async def research_economy_balance() -> dict[str, Any]:
    """Check credit balance and transaction history.

    Returns:
        total_credits, submissions_count, best_submission, recent_transactions
    """
    try:
        conn = await _get_db()
        # Total credits
        cursor = await conn.execute("SELECT SUM(credits_earned) FROM submissions")
        total = await cursor.fetchone()
        total_credits = total[0] if total and total[0] else 0

        # Count
        cursor = await conn.execute("SELECT COUNT(*) FROM submissions")
        count_result = await cursor.fetchone()
        count = count_result[0] if count_result else 0

        # Best submission
        cursor = await conn.execute(
            """SELECT strategy_name, target_model, asr, credits_earned
               FROM submissions ORDER BY credits_earned DESC LIMIT 1"""
        )
        best = await cursor.fetchone()

        # Recent 5
        cursor = await conn.execute(
            """SELECT strategy_name, target_model, asr, credits_earned, timestamp
               FROM submissions ORDER BY timestamp DESC LIMIT 5"""
        )
        recent = await cursor.fetchall()

        best_submission = (
            {
                "strategy_name": best[0],
                "target_model": best[1],
                "asr": best[2],
                "credits_earned": best[3],
            }
            if best
            else None
        )

        recent_transactions = [
            {
                "strategy_name": r[0],
                "target_model": r[1],
                "asr": r[2],
                "credits_earned": r[3],
                "timestamp": r[4],
            }
            for r in recent
        ]

        return {
            "total_credits": total_credits,
            "submissions_count": count,
            "best_submission": best_submission,
            "recent_transactions": recent_transactions,
        }
    except Exception as exc:
        logger.exception("research_economy_balance failed")
        return {"error": str(exc), "tool": "research_economy_balance"}
    finally:
        await conn.close()


@handle_tool_errors("research_economy_leaderboard")
async def research_economy_leaderboard(top_n: int = 10) -> dict[str, Any]:
    """Show top strategies by credits earned.

    Args:
        top_n: Number of top strategies to return

    Returns:
        leaderboard with rank, strategy_name, total_credits, submissions, avg_asr
    """
    if not (1 <= top_n <= 100):
        return {"error": "top_n must be 1-100", "tool": "research_economy_leaderboard"}

    try:
        conn = await _get_db()
        # Get top strategies by total credits
        cursor = await conn.execute(
            """SELECT strategy_name,
                      SUM(credits_earned) as total_creds,
                      COUNT(*) as sub_count,
                      AVG(asr) as avg_asr
               FROM submissions
               GROUP BY strategy_name
               ORDER BY total_creds DESC
               LIMIT ?""",
            (top_n,),
        )
        rows = await cursor.fetchall()

        # Total stats
        cursor = await conn.execute(
            "SELECT COUNT(DISTINCT strategy_name), SUM(credits_earned) FROM submissions"
        )
        stats = await cursor.fetchone()
        total_strategies = stats[0] if stats and stats[0] else 0
        total_credits_awarded = stats[1] if stats and stats[1] else 0

        leaderboard = [
            {
                "rank": i + 1,
                "strategy_name": r[0],
                "total_credits": r[1],
                "submissions": r[2],
                "avg_asr": round(r[3], 3) if r[3] else 0.0,
            }
            for i, r in enumerate(rows)
        ]

        return {
            "leaderboard": leaderboard,
            "total_strategies_submitted": total_strategies,
            "total_credits_awarded": total_credits_awarded,
        }
    except Exception as exc:
        logger.exception("research_economy_leaderboard failed")
        return {"error": str(exc), "tool": "research_economy_leaderboard"}
    finally:
        await conn.close()
