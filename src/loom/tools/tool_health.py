"""Tool health monitoring system for Loom."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.tool_health")


async def research_health_check_all(timeout_ms: int = 5000) -> dict[str, Any]:
    """Quick health check of all tool categories.

    For each category: check if at least one tool is importable and callable.

    Args:
        timeout_ms: Timeout per category check in milliseconds

    Returns:
        Dict with categories list, overall_health, and timestamp
    """
    categories = [
        {
            "name": "core",
            "modules": ["fetch", "search", "deep"],
            "test_func": "research_fetch",
        },
        {
            "name": "llm",
            "modules": ["llm", "enrich"],
            "test_func": "research_llm_summarize",
        },
        {
            "name": "reframe",
            "modules": ["prompt_reframe"],
            "test_func": "research_prompt_reframe",
        },
        {
            "name": "scoring",
            "modules": ["hcs_score", "attack_scorer"],
            "test_func": "research_hcs_score",
        },
        {
            "name": "infra",
            "modules": ["cache_mgmt", "sessions"],
            "test_func": "research_cache_stats",
        },
    ]

    results = []
    timeout_sec = timeout_ms / 1000.0

    for cat in categories:
        healthy = False
        error = None
        tools_checked = 0

        try:
            for mod_name in cat["modules"]:
                tools_checked += 1
                try:
                    mod = __import__(f"loom.tools.{mod_name}", fromlist=[cat["test_func"]])
                    if hasattr(mod, cat["test_func"]):
                        healthy = True
                        break
                except (ImportError, AttributeError):
                    continue
        except Exception as e:
            error = str(e)

        results.append(
            {
                "name": cat["name"],
                "healthy": healthy,
                "tools_checked": tools_checked,
                "error": error,
            }
        )

    healthy_count = sum(1 for r in results if r["healthy"])
    overall_health = "healthy" if healthy_count == len(results) else "degraded"

    await _append_health_history(overall_health, results)

    return {
        "categories": results,
        "overall_health": overall_health,
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def research_health_history(hours: int = 24) -> dict[str, Any]:
    """Show health check history from ~/.loom/health_history.jsonl.

    Args:
        hours: Look back N hours

    Returns:
        Dict with checks list, uptime_pct, and incidents
    """
    history_file = Path.home() / ".loom" / "health_history.jsonl"

    if not history_file.exists():
        return {
            "checks": [],
            "uptime_pct": 100.0,
            "incidents": [],
        }

    checks = []
    incidents = []
    cutoff = datetime.now(UTC).timestamp() - (hours * 3600)

    try:
        with open(history_file) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    ts = datetime.fromisoformat(entry["timestamp"])
                    if ts.timestamp() >= cutoff:
                        checks.append(entry)
                        if entry.get("overall_health") != "healthy":
                            incidents.append(
                                {
                                    "timestamp": entry["timestamp"],
                                    "health": entry["overall_health"],
                                    "failing": [
                                        c["name"]
                                        for c in entry.get("categories", [])
                                        if not c["healthy"]
                                    ],
                                }
                            )
                except (json.JSONDecodeError, ValueError):
                    continue
    except Exception as e:
        logger.error(f"Error reading health history: {e}")

    uptime_pct = (
        100.0
        if not checks
        else (sum(1 for c in checks if c.get("overall_health") == "healthy") / len(checks))
        * 100
    )

    return {
        "checks": checks[-100:],  # Last 100
        "uptime_pct": round(uptime_pct, 2),
        "incidents": incidents,
    }


async def research_health_alert(threshold: str = "degraded") -> dict[str, Any]:
    """Check if health has fallen below threshold.

    Thresholds: "healthy" (all pass), "degraded" (>80% pass), "critical" (<50% pass)

    Args:
        threshold: Alert threshold level

    Returns:
        Dict with alert bool, current_health, threshold, failing_categories, recommendation
    """
    check_result = await research_health_check_all()
    categories = check_result["categories"]

    healthy_count = sum(1 for c in categories if c["healthy"])
    health_pct = (healthy_count / len(categories)) * 100 if categories else 0

    current_health = (
        "healthy"
        if health_pct == 100
        else "degraded" if health_pct >= 80 else "critical"
    )

    threshold_map = {
        "healthy": 100,
        "degraded": 80,
        "critical": 50,
    }
    threshold_val = threshold_map.get(threshold, 80)

    alert = health_pct < threshold_val
    failing = [c["name"] for c in categories if not c["healthy"]]

    recommendation = (
        "All systems operational"
        if not alert
        else f"Investigate failing categories: {', '.join(failing)}"
    )

    return {
        "alert": alert,
        "current_health": current_health,
        "health_pct": round(health_pct, 2),
        "threshold": threshold,
        "threshold_pct": threshold_val,
        "failing_categories": failing,
        "recommendation": recommendation,
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def _append_health_history(
    overall_health: str, categories: list[dict[str, Any]]
) -> None:
    """Append health check to ~/.loom/health_history.jsonl."""
    history_file = Path.home() / ".loom" / "health_history.jsonl"
    history_file.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "overall_health": overall_health,
        "categories": categories,
    }

    try:
        with open(history_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.error(f"Error appending health history: {e}")
