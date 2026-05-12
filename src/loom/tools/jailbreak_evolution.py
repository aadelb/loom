"""research_jailbreak_evolution_* — track jailbreak strategy evolution across model versions."""

from __future__ import annotations

import logging
from typing import Any

try:
    from loom.jailbreak_evolution import JailbreakEvolutionTracker
    _EVOLUTION_AVAILABLE = True
except ImportError:
    _EVOLUTION_AVAILABLE = False
    JailbreakEvolutionTracker = None  # type: ignore[assignment,misc]

logger = logging.getLogger("loom.tools.jailbreak_evolution")

# Global tracker instance
_tracker: JailbreakEvolutionTracker | None = None


def _get_tracker() -> JailbreakEvolutionTracker:
    """Get or create global tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = JailbreakEvolutionTracker()
    return _tracker


async def research_jailbreak_evolution_record(
    strategy: str,
    model: str,
    model_version: str,
    success: bool,
    hcs: float,
    timestamp: str = "",
) -> dict[str, Any]:
    """Record a jailbreak attack result with model version info.

    Tracks attack strategy effectiveness across model versions to detect
    when models are patched and how strategies must adapt.

    Args:
        strategy: Jailbreak strategy name (e.g. "prompt_injection", "role_play")
        model: Model name (e.g. "gpt-4", "claude-3-sonnet")
        model_version: Model version string (e.g. "gpt-4-0613")
        success: Whether the attack succeeded
        hcs: Helpfulness Compliance Score (0-10)
        timestamp: ISO timestamp (defaults to now)

    Returns:
        Dict with recorded data:
        - status: "recorded"
        - strategy, model, version, success, hcs, timestamp: echoed back
    """
    tracker = _get_tracker()
    try:
        result = tracker.record_result(
            strategy=strategy,
            model=model,
            model_version=model_version,
            success=success,
            hcs=hcs,
            timestamp=timestamp,
        )
        logger.info("recorded_jailbreak_result strategy=%s model=%s version=%s", strategy, model, model_version)
        return result
    except (ValueError, TypeError) as e:
        logger.error("record_error error=%s", str(e))
        return {"status": "error", "error": str(e)}


async def research_jailbreak_evolution_get(
    strategy: str,
    model: str,
) -> dict[str, Any]:
    """Get evolution of a jailbreak strategy across model versions.

    Shows how a strategy's effectiveness changed over model updates,
    detects patches, and identifies trends.

    Args:
        strategy: Jailbreak strategy name
        model: Model name

    Returns:
        Dict with:
        - strategy: strategy name
        - model: model name
        - versions: list of {version, success_rate, avg_hcs, samples, date_range}
        - trend: "improving" | "declining" | "stable" | "patched" | "unknown"
        - patch_detected_at: version where patch applied (if applicable)
        - error: error message if data not found
    """
    tracker = _get_tracker()
    try:
        result = tracker.get_evolution(strategy=strategy, model=model)
        logger.info("fetched_evolution strategy=%s model=%s", strategy, model)
        return result
    except Exception as e:
        logger.error("evolution_error error=%s", str(e))
        return {
            "strategy": strategy,
            "model": model,
            "versions": [],
            "trend": "unknown",
            "patch_detected_at": None,
            "error": str(e),
        }


async def research_jailbreak_evolution_timeline(
    model: str,
) -> dict[str, Any]:
    """Get model safety timeline across all jailbreak strategies.

    Shows how a model's defenses evolved across versions by aggregating
    all strategy results per version.

    Args:
        model: Model name

    Returns:
        Dict with:
        - model: model name
        - versions: list of version strings
        - strategies: list of tested strategies
        - safety_metrics: dict of {version: {total_tests, success_rate, avg_hcs, ...}}
        - error: error message if data not found
    """
    tracker = _get_tracker()
    try:
        result = tracker.get_model_timeline(model=model)
        logger.info("fetched_timeline model=%s", model)
        return result
    except Exception as e:
        logger.error("timeline_error error=%s", str(e))
        return {
            "model": model,
            "versions": [],
            "strategies": [],
            "safety_metrics": {},
            "error": str(e),
        }


async def research_jailbreak_evolution_patches(
    model: str,
) -> dict[str, Any]:
    """Detect model patches against jailbreak strategies.

    Identifies version updates where specific strategies suddenly stopped
    working (success rate drop >50%), indicating a targeted patch.

    Args:
        model: Model name

    Returns:
        Dict with:
        - patches: list of {strategy, patched_at_version, previous_version,
                   previous_success_rate, new_success_rate, drop_percentage}
        - total_patches_detected: count of patches
        - error: error message if data not found
    """
    tracker = _get_tracker()
    try:
        patches = tracker.detect_patches(model=model)
        logger.info("detected_patches model=%s count=%d", model, len(patches))
        return {
            "model": model,
            "patches": patches,
            "total_patches_detected": len(patches),
        }
    except Exception as e:
        logger.error("patch_detection_error error=%s", str(e))
        return {
            "model": model,
            "patches": [],
            "total_patches_detected": 0,
            "error": str(e),
        }


async def research_jailbreak_evolution_adapt(
    strategy: str,
    model: str,
) -> dict[str, Any]:
    """Suggest strategy adaptations based on evolution analysis.

    Uses version history to recommend how to evolve a jailbreak strategy
    that stopped working, based on patterns across models and versions.

    Args:
        strategy: Jailbreak strategy name
        model: Model name

    Returns:
        Dict with:
        - strategy: strategy name
        - model: model name
        - suggestions: list of adaptation suggestions
        - reasoning: explanation of why these suggestions apply
    """
    tracker = _get_tracker()
    try:
        suggestions = tracker.suggest_adaptations(strategy=strategy, model=model)
        logger.info("suggested_adaptations strategy=%s model=%s", strategy, model)

        # Get evolution data for reasoning
        evolution = tracker.get_evolution(strategy=strategy, model=model)
        trend = evolution.get("trend", "unknown")
        patch_detected = evolution.get("patch_detected_at")

        reasoning = f"Strategy trend: {trend}"
        if patch_detected:
            reasoning += f". Patch detected at {patch_detected}"

        return {
            "strategy": strategy,
            "model": model,
            "suggestions": suggestions,
            "reasoning": reasoning,
        }
    except Exception as e:
        logger.error("adaptation_error error=%s", str(e))
        return {
            "strategy": strategy,
            "model": model,
            "suggestions": ["Unable to generate suggestions"],
            "error": str(e),
        }


async def research_jailbreak_evolution_stats(
    model: str | None = None,
) -> dict[str, Any]:
    """Export evolution tracking statistics.

    Returns overview of tracked data: total models, strategies, records.

    Args:
        model: Optional model name to filter stats (None = all models)

    Returns:
        Dict with:
        - total_models: count of models with data
        - total_strategies: total unique strategies
        - total_records: total recorded results
        - models: dict with per-model breakdown
    """
    tracker = _get_tracker()
    try:
        stats = tracker.export_stats(model=model)
        logger.info("exported_stats model=%s", model or "all")
        return stats
    except Exception as e:
        logger.error("stats_error error=%s", str(e))
        return {
            "total_models": 0,
            "total_strategies": 0,
            "total_records": 0,
            "models": {},
            "error": str(e),
        }
