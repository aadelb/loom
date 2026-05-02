"""Strategy Gamification system — leaderboards, challenges, competitions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import aiosqlite

DB_PATH = Path.home() / ".loom" / "gamification.db"


async def _get_db() -> aiosqlite.Connection:
    """Get or create database connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(str(DB_PATH))
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("CREATE TABLE IF NOT EXISTS scores (id INTEGER PRIMARY KEY, strategy TEXT NOT NULL, metric TEXT NOT NULL, value REAL NOT NULL, timestamp TEXT NOT NULL, model TEXT, run_id TEXT)")
    await conn.execute("CREATE TABLE IF NOT EXISTS challenges (id INTEGER PRIMARY KEY, challenge_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL, target_model TEXT NOT NULL, success_criteria TEXT NOT NULL, reward_credits INTEGER NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, attempts INTEGER DEFAULT 0, completions INTEGER DEFAULT 0)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_scores_metric ON scores(metric, timestamp)")
    await conn.execute("CREATE INDEX IF NOT EXISTS idx_challenges_status ON challenges(status)")
    await conn.commit()
    return conn


async def research_leaderboard(
    metric: str = "total_bypasses",
    period: str = "all_time",
    limit: int = 20,
) -> dict[str, Any]:
    """Show strategy leaderboard ranked by metric (total_bypasses, avg_asr, unique_models_bypassed, stealth_score, novelty_score). Periods: today, week, month, all_time."""
    if metric not in ["total_bypasses", "avg_asr", "unique_models_bypassed", "stealth_score", "novelty_score"]:
        return {"error": f"Unknown metric: {metric}"}
    if period not in ["today", "week", "month", "all_time"]:
        return {"error": f"Unknown period: {period}"}
    if not (1 <= limit <= 100):
        return {"error": "Limit must be 1-100"}

    conn = await _get_db()
    try:
        now = datetime.now(UTC)
        cutoff = {
            "today": (now - timedelta(days=1)).isoformat(),
            "week": (now - timedelta(days=7)).isoformat(),
            "month": (now - timedelta(days=30)).isoformat(),
            "all_time": "1970-01-01",
        }[period]

        queries = {
            "total_bypasses": ("SELECT strategy, COUNT(*) as value FROM scores WHERE metric = 'bypass' AND timestamp >= ? GROUP BY strategy ORDER BY value DESC LIMIT ?", (cutoff, limit)),
            "avg_asr": ("SELECT strategy, AVG(value) as value FROM scores WHERE metric = 'asr' AND timestamp >= ? GROUP BY strategy ORDER BY value DESC LIMIT ?", (cutoff, limit)),
            "unique_models_bypassed": ("SELECT strategy, COUNT(DISTINCT model) as value FROM scores WHERE metric = 'bypass' AND timestamp >= ? AND model IS NOT NULL GROUP BY strategy ORDER BY value DESC LIMIT ?", (cutoff, limit)),
            "stealth_score": ("SELECT strategy, AVG(value) as value FROM scores WHERE metric = 'stealth' AND timestamp >= ? GROUP BY strategy ORDER BY value DESC LIMIT ?", (cutoff, limit)),
            "novelty_score": ("SELECT strategy, AVG(value) as value FROM scores WHERE metric = 'novelty' AND timestamp >= ? GROUP BY strategy ORDER BY value DESC LIMIT ?", (cutoff, limit)),
        }

        query, params = queries[metric]
        rows = await (await conn.execute(query, params)).fetchall()
        rankings = [{"rank": i+1, "strategy": s, "value": round(float(v), 2), "trend": "up"} for i, (s, v) in enumerate(rows)]
        total = (await (await conn.execute("SELECT COUNT(DISTINCT strategy) FROM scores")).fetchone())[0] or 0
        return {"metric": metric, "period": period, "rankings": rankings, "total_strategies": total, "timestamp": now.isoformat()}
    finally:
        await conn.close()


async def research_challenge_create(
    name: str,
    target_model: str,
    success_criteria: str = "asr > 0.7",
    reward_credits: int = 100,
) -> dict[str, Any]:
    """Create a new challenge for users to attempt."""
    if not (1 <= len(name) <= 100):
        return {"error": "Name must be 1-100 chars"}
    if not (1 <= len(target_model) <= 50):
        return {"error": "Target model must be 1-50 chars"}
    if not (1 <= len(success_criteria) <= 200):
        return {"error": "Criteria must be 1-200 chars"}
    if not (0 <= reward_credits <= 10000):
        return {"error": "Reward must be 0-10000"}

    challenge_id = f"challenge_{uuid.uuid4().hex[:12]}"
    now = datetime.now(UTC).isoformat()
    conn = await _get_db()
    try:
        await conn.execute(
            "INSERT INTO challenges (challenge_id, name, target_model, success_criteria, reward_credits, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (challenge_id, name, target_model, success_criteria, reward_credits, "active", now),
        )
        await conn.commit()
        return {"challenge_id": challenge_id, "name": name, "target": target_model, "criteria": success_criteria, "reward": reward_credits, "status": "active", "created_at": now}
    finally:
        await conn.close()


async def research_challenge_list(status: str = "active") -> dict[str, Any]:
    """List challenges filtered by status (active, completed, all)."""
    if status not in ["active", "completed", "all"]:
        return {"error": f"Unknown status: {status}"}

    conn = await _get_db()
    try:
        query = "SELECT * FROM challenges" + ("" if status == "all" else " WHERE status = ?") + " ORDER BY created_at DESC"
        rows = await (await conn.execute(query, () if status == "all" else (status,))).fetchall()
        challenges = [{"id": r[1], "name": r[2], "target_model": r[3], "criteria": r[4], "reward": r[5], "status": r[6], "created_at": r[7], "attempts": r[8], "completions": r[9]} for r in rows]
        active_count = (await (await conn.execute("SELECT COUNT(*) FROM challenges WHERE status = 'active'")).fetchone())[0]
        return {"challenges": challenges, "active_count": active_count, "timestamp": datetime.now(UTC).isoformat()}
    finally:
        await conn.close()
