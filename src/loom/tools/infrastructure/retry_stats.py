"""Retry statistics monitoring tool.

Provides visibility into retry behavior across all decorated functions
in the Loom system. Used to identify flaky external calls and measure
the effectiveness of the auto-retry middleware.
"""

from __future__ import annotations

import logging
from typing import Any

from loom.retry import get_retry_stats, reset_retry_stats
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.retry_stats")


@handle_tool_errors("research_retry_stats")
def research_retry_stats(
    reset: bool = False,
) -> dict[str, Any]:
    """Get retry statistics showing retry behavior across all decorated functions.

    Returns cumulative statistics on retry attempts, successes after retry,
    and permanent failures. Useful for identifying flaky external services
    and measuring retry effectiveness.

    Args:
        reset: If True, clear all statistics after returning them (for testing)

    Returns:
        Dictionary with keys:
            - summary: Overall statistics (total_retries, success_after_retry, permanent_failure)
            - by_function: Per-function breakdown with same keys
            - timestamp: ISO timestamp of stats collection
            - functions_tracked: Number of distinct functions tracked

    Example response:
        {
            "summary": {
                "total_retries": 42,
                "success_after_retry": 31,
                "permanent_failure": 11,
                "recovery_rate": 0.738
            },
            "by_function": {
                "research_fetch": {
                    "total_retries": 25,
                    "success_after_retry": 20,
                    "permanent_failure": 5
                },
                "research_search": {
                    "total_retries": 17,
                    "success_after_retry": 11,
                    "permanent_failure": 6
                }
            },
            "functions_tracked": 2,
            "timestamp": "2026-05-04T10:30:45Z"
        }
    """
    try:
        from datetime import UTC, datetime

        stats = get_retry_stats()

        # Calculate summary
        total_retries = sum(s.get("total_retries", 0) for s in stats.values())
        success_after_retry = sum(s.get("success_after_retry", 0) for s in stats.values())
        permanent_failure = sum(s.get("permanent_failure", 0) for s in stats.values())

        # Calculate recovery rate (what percentage of retries succeeded)
        recovery_rate = (
            success_after_retry / total_retries if total_retries > 0 else 0
        )

        result: dict[str, Any] = {
            "summary": {
                "total_retries": total_retries,
                "success_after_retry": success_after_retry,
                "permanent_failure": permanent_failure,
                "recovery_rate": round(recovery_rate, 3),
            },
            "by_function": stats,
            "functions_tracked": len(stats),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        if reset:
            reset_retry_stats()
            result["reset"] = True
            logger.info("retry_stats_reset")

        logger.info(
            "retry_stats_retrieved total_retries=%d success_after_retry=%d permanent_failure=%d functions_tracked=%d",
            total_retries,
            success_after_retry,
            permanent_failure,
            len(stats),
        )

        return result
    except Exception as exc:
        logger.error("retry_stats_error: %s", exc)
        return {"error": str(exc), "tool": "research_retry_stats"}
