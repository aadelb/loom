"""Strategy feedback loop — learn which strategies work best per topic/model."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.strategy_feedback")
FEEDBACK_DB = Path.home() / ".loom" / "feedback" / "strategy_log.db"


def _get_db_conn() -> sqlite3.Connection:
    """Get SQLite connection, creating DB and schema if needed."""
    FEEDBACK_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(FEEDBACK_DB))
    conn.execute(
        """CREATE TABLE IF NOT EXISTS strategy_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            strategy TEXT NOT NULL,
            model TEXT NOT NULL,
            hcs_score REAL NOT NULL,
            success INTEGER NOT NULL,
            timestamp TEXT NOT NULL)"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_topic_model ON strategy_log(topic, model)")
    conn.commit()
    return conn


def research_strategy_log(
    topic: str,
    strategy: str,
    model: str,
    hcs_score: float,
    success: bool,
) -> dict[str, Any]:
    """Log a strategy attempt result.

    Args:
        topic: research topic (e.g., "prompt_injection")
        strategy: strategy name used
        model: LLM model identifier
        hcs_score: HCS score (0-100)
        success: whether attack succeeded

    Returns:
        Dict with logged, total_entries, db_path
    """
    try:
        conn = _get_db_conn()
        timestamp = datetime.now(UTC).isoformat()
        conn.execute(
            "INSERT INTO strategy_log(topic,strategy,model,hcs_score,success,timestamp) VALUES(?,?,?,?,?,?)",
            (topic, strategy, model, hcs_score, int(success), timestamp),
        )
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM strategy_log").fetchone()[0]
        conn.close()
        return {"logged": True, "total_entries": total, "db_path": str(FEEDBACK_DB)}
    except Exception as e:
        logger.error("strategy_log error: %s", e)
        return {"logged": False, "error": str(e)}


def research_strategy_recommend(topic: str, model: str = "auto") -> dict[str, Any]:
    """Find best strategy for a topic+model combination.

    Args:
        topic: research topic
        model: LLM model ("auto" = best across all models)

    Returns:
        Dict with recommended_strategy, avg_hcs, success_rate, total_attempts
    """
    try:
        conn = _get_db_conn()
        query = """SELECT strategy, AVG(hcs_score), SUM(success), COUNT(*)
                   FROM strategy_log WHERE topic = ?"""
        params = [topic]
        if model != "auto":
            query += " AND model = ?"
            params.append(model)
        query += " GROUP BY strategy ORDER BY (SUM(success)*1.0/COUNT(*)) DESC, AVG(hcs_score) DESC LIMIT 1"

        row = conn.execute(query, params).fetchone()
        conn.close()

        if not row:
            return {
                "recommended_strategy": None,
                "avg_hcs": 0,
                "success_rate": 0,
                "total_attempts": 0,
            }

        strategy, avg_hcs, successes, total = row
        success_rate = (successes / total) if total > 0 else 0
        return {
            "recommended_strategy": strategy,
            "avg_hcs": round(avg_hcs, 2),
            "success_rate": round(success_rate, 3),
            "total_attempts": total,
            "model": model,
            "topic": topic,
        }
    except Exception as e:
        logger.error("strategy_recommend error: %s", e)
        return {"error": str(e)}


def research_strategy_stats() -> dict[str, Any]:
    """Get overall statistics: top strategies, worst strategies, model performance.

    Returns:
        Dict with total_logs, top_strategies, worst_strategies, model_performance
    """
    try:
        conn = _get_db_conn()

        total_logs = conn.execute("SELECT COUNT(*) FROM strategy_log").fetchone()[0]
        topic_count = conn.execute("SELECT COUNT(DISTINCT topic) FROM strategy_log").fetchone()[0]

        # Top 5 strategies
        top_rows = conn.execute(
            """SELECT strategy, AVG(hcs_score), SUM(success), COUNT(*), SUM(success)*1.0/COUNT(*)
               FROM strategy_log GROUP BY strategy ORDER BY SUM(success)*1.0/COUNT(*) DESC, AVG(hcs_score) DESC LIMIT 5"""
        ).fetchall()
        top_strategies = [
            {
                "strategy": r[0],
                "avg_hcs": round(r[1], 2),
                "successes": r[2],
                "total_attempts": r[3],
                "success_rate": round(r[4], 3),
            }
            for r in top_rows
        ]

        # Worst strategies (min 3 attempts)
        worst_rows = conn.execute(
            """SELECT strategy, AVG(hcs_score), SUM(success), COUNT(*), SUM(success)*1.0/COUNT(*)
               FROM strategy_log GROUP BY strategy HAVING COUNT(*) >= 3 ORDER BY SUM(success)*1.0/COUNT(*) ASC LIMIT 3"""
        ).fetchall()
        worst_strategies = [
            {
                "strategy": r[0],
                "avg_hcs": round(r[1], 2),
                "successes": r[2],
                "total_attempts": r[3],
                "success_rate": round(r[4], 3),
            }
            for r in worst_rows
        ]

        # Model performance
        model_rows = conn.execute(
            """SELECT model, COUNT(*), SUM(success), AVG(hcs_score), SUM(success)*1.0/COUNT(*)
               FROM strategy_log GROUP BY model ORDER BY SUM(success)*1.0/COUNT(*) DESC"""
        ).fetchall()
        model_performance = [
            {
                "model": r[0],
                "attempts": r[1],
                "successes": r[2],
                "avg_hcs": round(r[3], 2),
                "success_rate": round(r[4], 3),
            }
            for r in model_rows
        ]

        conn.close()
        return {
            "total_logs": total_logs,
            "topic_count": topic_count,
            "top_strategies": top_strategies,
            "worst_strategies": worst_strategies,
            "model_performance": model_performance,
            "db_path": str(FEEDBACK_DB),
        }
    except Exception as e:
        logger.error("strategy_stats error: %s", e)
        return {"error": str(e)}
