"""Exploit resilience predictor — estimate how long attacks remain effective."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("loom.tools.resilience_predictor")

# Strategy classification & metadata
_STRATEGY_META: dict[str, dict[str, Any]] = {
    "direct_jailbreak": {"complexity": "simple", "date": "2021-09-01"},
    "role_play": {"complexity": "medium", "date": "2022-03-15"},
    "persona": {"complexity": "medium", "date": "2022-06-01"},
    "hypothetical": {"complexity": "medium", "date": "2022-08-20"},
    "prompt_injection": {"complexity": "complex", "date": "2022-12-10"},
    "token_smuggling": {"complexity": "complex", "date": "2023-02-01"},
    "multi_turn": {"complexity": "complex", "date": "2023-03-15"},
    "logic_manipulation": {"complexity": "complex", "date": "2023-05-10"},
    "consent_smuggling": {"complexity": "complex", "date": "2023-06-20"},
    "indirect_request": {"complexity": "medium", "date": "2023-07-01"},
    "constraint_relaxation": {"complexity": "medium", "date": "2023-08-15"},
    "context_overflow": {"complexity": "complex", "date": "2023-09-01"},
    "deep_inception": {"complexity": "complex", "date": "2024-01-15"},
    "recursive_authority": {"complexity": "complex", "date": "2024-02-20"},
    "scaffolded_layered_depth": {"complexity": "complex", "date": "2024-03-10"},
    "cognitive_wedge": {"complexity": "complex", "date": "2024-04-01"},
}

_MODEL_UPDATE_FREQ = {
    "gpt4": 21, "gpt4o": 21, "gpt-4-turbo": 21,
    "claude3": 21, "claude3.5": 21, "gemini": 28, "gemini2": 28,
    "llama2": 14, "llama3": 14, "deepseek": 14, "mistral": 35,
}


async def research_predict_resilience(
    strategy: str,
    target_model: str = "auto",
    current_asr: float = 0.8,
) -> dict[str, Any]:
    """Predict how long an exploit will remain effective.

    Analyzes strategy age, model update frequency, complexity, and publication
    status to estimate exploit lifespan.

    Args:
        strategy: Strategy name (e.g., "token_smuggling", "multi_turn")
        target_model: Target model ("gpt4", "claude3", "gemini", etc., or "auto")
        current_asr: Current attack success rate (0.0-1.0)

    Returns:
        dict with predicted lifespan days, confidence, risk factors, and recommendations
    """
    strategy_lower = strategy.lower()
    target_model = target_model.lower() if target_model != "auto" else "gpt4"

    # Get strategy metadata
    meta = _STRATEGY_META.get(strategy_lower, {})
    complexity = meta.get("complexity")

    # Classify if not in metadata
    if not complexity:
        if any(x in strategy_lower for x in ["token", "multi_turn", "inception", "recursive", "layered"]):
            complexity = "complex"
        elif any(x in strategy_lower for x in ["role", "persona", "hypothetical", "indirect"]):
            complexity = "medium"
        else:
            complexity = "simple" if any(x in strategy_lower for x in ["keyword", "rot13", "obfuscation"]) else "medium"

    # Calculate strategy age
    try:
        date_str = meta.get("date", "2022-01-01")
        age_days = (datetime.now(UTC) - datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)).days
    except (ValueError, TypeError):
        age_days = 365

    # Determine if public (heuristic: age > 90 days or in standard modules)
    is_public = age_days > 90 or any(x in strategy_lower for x in ["core", "advanced", "reasoning", "legal", "academic"])

    # Get model update frequency (lower = faster updates = shorter lifespan)
    update_freq = next((v for k, v in _MODEL_UPDATE_FREQ.items() if k in target_model), 21)

    # Base lifespan by complexity
    base_lifespan = {"simple": 10, "medium": 45, "complex": 90, "novel": 240}.get(complexity, 45)

    # Adjust for age: very old strategies may already be patched
    if age_days > 365:
        base_lifespan = max(1, base_lifespan - (age_days // 100))

    # Public strategies have shorter lifespan (70% of base)
    if is_public:
        base_lifespan = max(1, int(base_lifespan * 0.7))

    # Adjust for model update frequency: slower updates = longer lifespan
    # update_freq / 21 gives ratio (35/21 = 1.67x for mistral, 14/21 = 0.67x for deepseek)
    update_pressure = update_freq / 21.0
    lifespan = max(1, int(base_lifespan * update_pressure))

    # Adjust for ASR
    if current_asr < 0.3:
        lifespan = max(1, int(lifespan * 0.5))
    elif current_asr < 0.5:
        lifespan = max(1, int(lifespan * 0.7))
    elif current_asr > 0.9:
        lifespan = int(lifespan * 1.2)

    # Confidence based on complexity and age
    confidence = {"simple": 0.85, "medium": 0.75, "complex": 0.65, "novel": 0.4}.get(complexity, 0.65)
    if age_days > 730:
        confidence = min(0.95, confidence + 0.15)
    elif age_days < 30:
        confidence = max(0.3, confidence - 0.15)

    # Risk factors
    risk_factors = []
    if is_public:
        risk_factors.append("strategy_is_public")
    if current_asr < 0.5:
        risk_factors.append("low_success_rate")
    if complexity == "simple":
        risk_factors.append("simple_strategies_patch_faster")
    if age_days > 1095:
        risk_factors.append("strategy_very_old")
    if 60 < age_days < 180:
        risk_factors.append("strategy_in_active_patching_window")

    # Suggestions for modification
    suggestions = []
    if complexity == "simple":
        suggestions.extend(["combine_with_multi_turn_escalation", "layer_with_persona_framing"])
    if complexity in ("simple", "medium"):
        suggestions.append("add_token_smuggling_layer")
    if is_public:
        suggestions.extend(["develop_novel_variation", "combine_multiple_known_strategies"])
    if "jailbreak" in strategy_lower:
        suggestions.append("add_consent_smuggling_component")
    suggestions = (suggestions or ["increase_stealth_scoring", "add_reasoning_chain_complexity"])[:3]

    # Recommendation
    if lifespan > 120:
        recommendation = "hold"
    elif lifespan > 30:
        recommendation = "modify_first"
    else:
        recommendation = "publish_now"

    if complexity == "novel" and current_asr > 0.85:
        recommendation = "hold"
    elif current_asr < 0.3:
        recommendation = "publish_now"

    return {
        "strategy": strategy,
        "target_model": target_model,
        "current_asr": round(current_asr, 2),
        "predicted_lifespan_days": lifespan,
        "confidence": round(confidence, 2),
        "complexity": complexity,
        "age_days": age_days,
        "is_public": is_public,
        "risk_factors": risk_factors,
        "recommendation": recommendation,
        "suggested_modifications": suggestions,
    }
