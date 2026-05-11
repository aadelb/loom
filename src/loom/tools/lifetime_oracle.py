"""Jailbreak Lifetime Oracle — predict exploit longevity before publishing."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger("loom.tools.lifetime_oracle")

_MODEL_UPDATE_DAYS = {
    "gpt-4": 14, "gpt-4o": 14, "gpt-4-turbo": 14, "claude-3": 21, "claude-3.5": 21,
    "gemini": 28, "deepseek": 42, "llama": 90, "mistral": 35, "default": 21,
}

_KNOWN_PATTERNS = {
    "simple": [r"\b(please|ignore|pretend|roleplay|act as|as if)\b"],
    "medium": [r"\b(persona|character|simulate|hypothetical|story|consent)\b"],
    "complex": [r"\b(token.?smuggl|encoding|obfuscat|multi.?turn|recursive|layered|inception|reasoning|chain|indirect|constraint|logic)\b"],
}


def _classify_complexity(text: str) -> str:
    """Classify strategy complexity from text patterns."""
    if not text:
        return "simple"
    text_lower = text.lower()
    counts = {k: sum(1 for p in v if re.search(p, text_lower)) for k, v in _KNOWN_PATTERNS.items()}

    if counts["complex"] >= 2 or any(x in text_lower for x in ["turn", "chain"]):
        return "complex"
    if counts["complex"] >= 1 and len(text) > 500:
        return "complex"
    if counts["medium"] >= 2 or len(text) > 300:
        return "medium"
    if counts["medium"] >= 1:
        return "medium"
    if counts["simple"] >= 1 and len(text) < 200:
        return "simple"
    return "novel" if counts["simple"] == 0 else "medium"


def _detect_novelty(text: str) -> tuple[bool, float]:
    """Detect novel patterns; return (is_novel, bonus)."""
    if not text:
        return False, 0.0
    text_lower = text.lower()
    all_patterns = [p for v in _KNOWN_PATTERNS.values() for p in v]
    matches = sum(1 for p in all_patterns if re.search(p, text_lower))
    return (True, 0.5) if matches == 0 else ((True, 0.3) if matches <= 1 and len(text) > 600 else (False, 0.0))


async def research_lifetime_predict(
    strategy_name: str,
    strategy_text: str = "",
    target_models: list[str] | None = None,
    is_public: bool = False,
) -> dict[str, Any]:
    """Predict jailbreak longevity before publishing.

    Analyzes complexity, novelty, and model patching to forecast exploit lifespan.
    Helps decide: publish now for impact or hold for private use?

    Args:
        strategy_name: Strategy name/label
        strategy_text: Full strategy text (for novelty detection)
        target_models: Target models (default: all major)
        is_public: Whether strategy will be publicly released

    Returns:
        Dict with predicted lifespan, confidence, recommendation, and reasoning
    """
    try:
        logger.info("lifetime_predict strategy=%s text_len=%d public=%s", strategy_name, len(strategy_text or ""), is_public)

        target_models = target_models or [m for m in _MODEL_UPDATE_DAYS if m != "default"]
        complexity = _classify_complexity(strategy_text)
        base = {"simple": 14, "medium": 60, "complex": 120, "novel": 240}.get(complexity, 60)

        model_adj = {m: max(1, int(base * (_MODEL_UPDATE_DAYS.get(m.lower(), 21) / 21))) for m in target_models}
        penalty = 0.40 if is_public else 0.0
        is_novel, bonus = _detect_novelty(strategy_text)

        avg = sum(model_adj.values()) / len(model_adj) if model_adj else base
        expected = max(1, int(avg * (1 - penalty) * (1 + bonus)))

        confidence = (0.5 if complexity == "novel" else 0.75) - (0.1 if is_novel else 0) - (0.1 if not is_public else 0)

        reasoning = [f"Complexity: {complexity.upper()} ({base}d base)"]
        if is_novel:
            reasoning.append("Novel pattern (+50% lifespan)")
        if is_public:
            reasoning.append("Public release (-40% lifespan)")

        if expected <= 21:
            rec, opt_date = "publish_now", None
            reasoning.append("Short lifespan; publish for visibility")
        elif expected <= 60:
            rec, opt_date = "hold_30_days", (datetime.now(UTC) + timedelta(days=30)).date().isoformat()
            reasoning.append("Hold 30 days to maximize private use")
        else:
            rec, opt_date = "hold_indefinitely", None
            reasoning.append("High-value; hold indefinitely" if not is_novel else "Novel; hold indefinitely")

        return {
            "strategy_name": strategy_name,
            "complexity_class": complexity,
            "base_lifespan_days": base,
            "model_adjustments": model_adj,
            "publication_penalty": round(penalty, 2),
            "novelty_bonus": round(bonus, 2),
            "predicted_lifespan": {"min": max(1, int(expected * 0.7)), "expected": expected, "max": int(expected * 1.5)},
            "confidence": round(max(0.3, min(1.0, confidence)), 2),
            "recommendation": rec,
            "reasoning": reasoning,
            "optimal_publish_date": opt_date,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_lifetime_predict"}
