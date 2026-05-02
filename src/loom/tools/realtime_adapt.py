"""Real-time refusal tracking and adaptive model selection."""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger("loom.tools.realtime_adapt")

_REFUSAL_WINDOW: dict[str, list[bool]] = {}
_WINDOW_SIZE = 100


def research_track_refusal(model: str, refused: bool, strategy: str = "") -> dict[str, Any]:
    """Track refusal rate per model in rolling 100-request window.

    Args:
        model: Model identifier (e.g., "gpt-4", "claude-3-sonnet")
        refused: Whether the request was refused
        strategy: Optional strategy name for context

    Returns:
        Dict with: model, refusal_rate, window_size, trend, strategy
    """
    if model not in _REFUSAL_WINDOW:
        _REFUSAL_WINDOW[model] = []

    window = _REFUSAL_WINDOW[model]
    window.append(refused)

    if len(window) > _WINDOW_SIZE:
        window.pop(0)

    refusal_count = sum(1 for r in window if r)
    refusal_rate = refusal_count / len(window) if window else 0.0

    trend: Literal["increasing", "stable", "decreasing"] = "stable"
    if len(window) >= 20:
        mid = len(window) // 2
        first_rate = sum(1 for r in window[:mid] if r) / mid
        second_rate = sum(1 for r in window[mid:] if r) / (len(window) - mid)
        if second_rate > first_rate + 0.05:
            trend = "increasing"
        elif second_rate < first_rate - 0.05:
            trend = "decreasing"

    logger.info(
        "refusal_tracked",
        model=model,
        refused=refused,
        refusal_rate=refusal_rate,
        window_size=len(window),
        trend=trend,
    )

    return {
        "model": model,
        "refusal_rate": round(refusal_rate, 3),
        "window_size": len(window),
        "trend": trend,
        "strategy": strategy or None,
    }


def research_get_best_model(topic: str = "") -> dict[str, Any]:
    """Get model with LOWEST refusal rate.

    Models with refusal_rate > 50% are deprioritized.

    Args:
        topic: Optional topic for logging context

    Returns:
        Dict with: recommended_model, refusal_rate, all_models_ranked, topic
    """
    if not _REFUSAL_WINDOW:
        logger.warning("no_models_tracked", topic=topic)
        return {
            "recommended_model": None,
            "refusal_rate": None,
            "all_models_ranked": [],
            "topic": topic or None,
        }

    model_stats = []
    for model, window in _REFUSAL_WINDOW.items():
        if window:
            refusal_rate = sum(1 for r in window if r) / len(window)
            model_stats.append({
                "model": model,
                "refusal_rate": round(refusal_rate, 3),
                "viable": refusal_rate <= 0.5,
                "window_size": len(window),
            })

    viable = sorted([m for m in model_stats if m["viable"]], key=lambda x: x["refusal_rate"])
    unviable = sorted([m for m in model_stats if not m["viable"]], key=lambda x: x["refusal_rate"])
    ranked = viable + unviable

    recommended = ranked[0] if ranked else None
    recommended_model = recommended["model"] if recommended else None
    recommended_rate = recommended["refusal_rate"] if recommended else None

    logger.info("best_model_selected", recommended_model=recommended_model, refusal_rate=recommended_rate, topic=topic)

    return {
        "recommended_model": recommended_model,
        "refusal_rate": recommended_rate,
        "all_models_ranked": ranked,
        "topic": topic or None,
    }
