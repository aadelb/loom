"""Strategy caching layer — remembers what works and reuses it intelligently.

Builds on strategy_feedback.py to provide a high-level caching interface
that automatically selects best strategies based on historical success rates.

Public API:
    research_cached_strategy(topic, model, fallback_strategy)
        → Dict with strategy name, source (cache|fallback), confidence, entry count
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from loom.tools.strategy_feedback import _get_db_conn
    _FEEDBACK_AVAILABLE = True
except ImportError:
    _FEEDBACK_AVAILABLE = False

logger = logging.getLogger("loom.tools.strategy_cache")

# Minimum success rate threshold for cache hit (70%)
MIN_CACHE_CONFIDENCE = 0.70


def research_cached_strategy(
    topic: str,
    model: str = "auto",
    fallback_strategy: str = "ethical_anchor",
) -> dict[str, Any]:
    """Check cache for best strategy on this topic+model combination.

    If success_rate > 70%, returns cached strategy immediately (HIT).
    If not found, returns fallback_strategy (MISS).
    Enables intelligent strategy reuse without re-evaluation.

    Args:
        topic: research topic/query (e.g., "privacy research", "security audit")
        model: LLM model (e.g., "groq", "claude", "auto" for any)
        fallback_strategy: strategy to use on cache miss (default: "ethical_anchor")

    Returns:
        Dict with:
            - strategy: selected strategy name
            - source: "cache" (hit) or "fallback" (miss)
            - confidence: success rate 0.0-1.0 (only on cache hit)
            - cache_entries: total entries for this topic+model
            - model: model used in query
            - topic: topic used in query
    """
    if not topic or len(topic) > 500:
        raise ValueError(f"topic must be 1-500 chars, got {len(topic)}")
    if not fallback_strategy or len(fallback_strategy) > 100:
        raise ValueError(f"fallback_strategy must be 1-100 chars, got {len(fallback_strategy)}")

    try:
        conn = _get_db_conn()

        # Query for best strategy by success rate
        if model != "auto":
            query = """SELECT strategy, SUM(success), COUNT(*)
                       FROM strategy_log
                       WHERE topic = ? AND model = ?
                       GROUP BY strategy
                       ORDER BY (SUM(success)*1.0/COUNT(*)) DESC
                       LIMIT 1"""
            params = [topic, model]
        else:
            query = """SELECT strategy, SUM(success), COUNT(*)
                       FROM strategy_log
                       WHERE topic = ?
                       GROUP BY strategy
                       ORDER BY (SUM(success)*1.0/COUNT(*)) DESC
                       LIMIT 1"""
            params = [topic]

        row = conn.execute(query, params).fetchone()
        conn.close()

        # Cache miss: no entries found
        if not row:
            logger.info("cache_miss topic=%s model=%s", topic, model)
            return {
                "strategy": fallback_strategy,
                "source": "fallback",
                "confidence": 0.0,
                "cache_entries": 0,
                "model": model,
                "topic": topic,
            }

        # Cache hit: check confidence threshold
        strategy, successes, total = row
        success_rate = successes / total if total > 0 else 0.0

        if success_rate >= MIN_CACHE_CONFIDENCE:
            logger.info(
                "cache_hit topic=%s model=%s strategy=%s confidence=%.2f",
                topic,
                model,
                strategy,
                success_rate,
            )
            return {
                "strategy": strategy,
                "source": "cache",
                "confidence": round(success_rate, 3),
                "cache_entries": total,
                "model": model,
                "topic": topic,
            }

        # Below threshold: treat as miss
        logger.info(
            "cache_below_threshold topic=%s model=%s strategy=%s confidence=%.2f",
            topic,
            model,
            strategy,
            success_rate,
        )
        return {
            "strategy": fallback_strategy,
            "source": "fallback",
            "confidence": round(success_rate, 3),
            "cache_entries": total,
            "model": model,
            "topic": topic,
        }

    except Exception as e:
        logger.error("cache_error topic=%s error=%s", topic, str(e)[:100])
        return {
            "strategy": fallback_strategy,
            "source": "fallback",
            "confidence": 0.0,
            "cache_entries": 0,
            "model": model,
            "topic": topic,
            "error": str(e)[:100],
        }
