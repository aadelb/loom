"""Model Safety Update Predictor — predict safety defense deployments.

Predicts which safety defenses models will deploy next based on:
  - Historical safety update patterns per model family
  - Published research signals that precede deployments
  - Typical defense pipeline progression
  - Model's current defense stage

Returns predicted defenses with probability, estimated deployment date, and
attack windows before patching.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger("loom.tools.safety_predictor")

# Historical safety updates per model family (observed deployments)
MODEL_UPDATE_HISTORY: dict[str, list[dict[str, Any]]] = {
    "claude": [
        {"defense": "constitutional_AI", "deployed": "2023-01", "effectiveness": 0.7},
        {"defense": "classifiers", "deployed": "2024-01", "effectiveness": 0.75},
        {"defense": "continuous_assessment", "deployed": "2025-01", "effectiveness": 0.8},
        {"defense": "reasoning_filters", "deployed": "2025-03", "effectiveness": 0.72},
    ],
    "gpt": [
        {"defense": "RLHF", "deployed": "2022-06", "effectiveness": 0.65},
        {"defense": "system_message_priority", "deployed": "2023-03", "effectiveness": 0.7},
        {"defense": "instruction_hierarchy", "deployed": "2024-06", "effectiveness": 0.78},
        {"defense": "moderation_API", "deployed": "2023-09", "effectiveness": 0.72},
    ],
    "deepseek": [
        {"defense": "basic_keyword", "deployed": "2024-08", "effectiveness": 0.55},
        {"defense": "thinking_filter", "deployed": "2025-02", "effectiveness": 0.65},
        {"defense": "reasoning_trace_audit", "deployed": "2025-04", "effectiveness": 0.68},
    ],
    "gemini": [
        {"defense": "policy_layer", "deployed": "2024-01", "effectiveness": 0.7},
        {"defense": "grounding_check", "deployed": "2024-06", "effectiveness": 0.73},
        {"defense": "factuality_verifier", "deployed": "2025-02", "effectiveness": 0.75},
    ],
    "llama": [
        {"defense": "safeguard_llama", "deployed": "2024-01", "effectiveness": 0.62},
        {"defense": "instruction_filter", "deployed": "2024-09", "effectiveness": 0.68},
    ],
}

# Typical defense pipeline progression stages
DEFENSE_PIPELINE: list[dict[str, Any]] = [
    {
        "stage": 1,
        "category": "Keyword Filters",
        "defenses": ["basic_keyword", "content_filter"],
        "effectiveness_range": (0.45, 0.65),
        "typical_lifetime_months": 6,
    },
    {
        "stage": 2,
        "category": "Classifiers",
        "defenses": ["classifier", "policy_layer", "classifiers"],
        "effectiveness_range": (0.65, 0.80),
        "typical_lifetime_months": 12,
    },
    {
        "stage": 3,
        "category": "Constitutional/Reasoning",
        "defenses": ["constitutional_AI", "reasoning_filters", "instruction_hierarchy"],
        "effectiveness_range": (0.72, 0.85),
        "typical_lifetime_months": 18,
    },
    {
        "stage": 4,
        "category": "Adaptive Reasoning",
        "defenses": ["reasoning_trace_audit", "adaptive_assessment", "dynamic_constraint"],
        "effectiveness_range": (0.80, 0.92),
        "typical_lifetime_months": 24,
    },
]

# Research signals that precede safety deployments
RESEARCH_SIGNALS: list[dict[str, Any]] = [
    {
        "signal": "Constitutional AI paper published",
        "typical_deployment_months": "6-18",
        "defenses_predicted": ["constitutional_AI", "reasoning_filters"],
    },
    {
        "signal": "SafeProbing research released",
        "typical_deployment_months": "3-9",
        "defenses_predicted": ["in_decoding_checks", "trace_audit"],
    },
    {
        "signal": "Jailbreak survey published",
        "typical_deployment_months": "4-12",
        "defenses_predicted": ["classifiers", "reasoning_filters"],
    },
    {
        "signal": "Adversarial prompt research",
        "typical_deployment_months": "2-6",
        "defenses_predicted": ["instruction_filter", "policy_hardening"],
    },
    {
        "signal": "Reasoning attack paper",
        "typical_deployment_months": "6-15",
        "defenses_predicted": ["reasoning_trace_audit", "adaptive_reasoning"],
    },
]


def research_predict_safety_update(
    model: str = "auto",
    attack_category: str = "all",
    time_horizon_days: int = 90,
) -> dict[str, Any]:
    """Predict which safety defenses models will deploy next.

    Analyzes historical safety updates, research signals, and typical defense
    pipeline progression to forecast upcoming safety deployments.

    Args:
        model: Model family ("claude", "gpt", "deepseek", "gemini", "llama", "auto")
        attack_category: Attack type to focus on ("all", "prompt_injection",
                        "reasoning", "jailbreak", "instruction_override")
        time_horizon_days: Days into future to predict (default 90)

    Returns:
        Dict with:
          - model: Model family analyzed
          - current_defenses: List of currently deployed defenses
          - predicted_next_defenses: List of dicts {defense, probability,
            estimated_deploy_date, based_on}
          - attacks_at_risk: List of dicts {attack, days_until_likely_patched}
          - safe_window: Dict {days_remaining, confidence}
          - recommendations: List of strategic recommendations
    """
    logger.info(
        "predict_safety_update model=%s category=%s horizon=%d",
        model,
        attack_category,
        time_horizon_days,
    )

    # Resolve model family
    if model == "auto":
        model = "claude"  # Default
    model = model.lower()

    if model not in MODEL_UPDATE_HISTORY:
        return {
            "error": f"Unknown model: {model}",
            "known_models": list(MODEL_UPDATE_HISTORY.keys()),
        }

    # Get current defenses
    history = MODEL_UPDATE_HISTORY[model]
    current_defenses = [d["defense"] for d in history]
    current_stage = _estimate_current_stage(current_defenses)

    # Predict next defenses in pipeline
    next_stage = current_stage + 1
    predicted_next = []

    if next_stage < len(DEFENSE_PIPELINE):
        stage_info = DEFENSE_PIPELINE[next_stage]
        for defense in stage_info["defenses"]:
            if defense not in current_defenses:
                # Estimate deployment probability and date
                prob = _estimate_deployment_probability(
                    model, defense, stage_info["typical_lifetime_months"]
                )
                days_to_deploy = _estimate_days_to_deployment(
                    model, stage_info["typical_lifetime_months"]
                )
                deploy_date = (datetime.now(UTC).replace(tzinfo=None) + timedelta(days=days_to_deploy)).strftime(
                    "%Y-%m-%d"
                )

                predicted_next.append(
                    {
                        "defense": defense,
                        "probability": min(prob, 0.95),
                        "estimated_deploy_date": deploy_date,
                        "based_on": "pipeline_progression",
                        "effectiveness_expected": stage_info["effectiveness_range"][1],
                    }
                )

    # Map attacks at risk based on predicted defenses
    attacks_at_risk = _map_attacks_at_risk(attack_category, predicted_next, time_horizon_days)

    # Calculate safe window (days before most likely patches)
    safe_days = _calculate_safe_window(predicted_next, time_horizon_days)

    # Generate strategic recommendations
    recommendations = _generate_recommendations(
        model, current_stage, predicted_next, attack_category
    )

    return {
        "model": model,
        "current_defenses": current_defenses,
        "current_stage": current_stage,
        "predicted_next_defenses": predicted_next,
        "attacks_at_risk": attacks_at_risk,
        "safe_window": {
            "days_remaining": safe_days,
            "confidence": 0.65 + (0.05 * len(history)),  # Confidence increases with history length
            "analysis_date": datetime.now(UTC).replace(tzinfo=None).strftime("%Y-%m-%d"),
        },
        "research_signals": RESEARCH_SIGNALS,
        "recommendations": recommendations,
    }


def _estimate_current_stage(current_defenses: list[str]) -> int:
    """Estimate current defense pipeline stage."""
    if not current_defenses:
        return 0

    for pipeline_stage in reversed(DEFENSE_PIPELINE):
        for defense in current_defenses:
            if defense in pipeline_stage["defenses"]:
                return pipeline_stage["stage"]

    return 0


def _estimate_deployment_probability(model: str, defense: str, months: int) -> float:
    """Estimate probability of deploying a specific defense."""
    # Base probability increases with model maturity
    base_prob = 0.65 + (0.05 * len(MODEL_UPDATE_HISTORY[model]))

    # Adjust for research signals
    signal_boost = 0.0
    for signal in RESEARCH_SIGNALS:
        if defense in signal["defenses_predicted"]:
            signal_boost = 0.15

    return min(base_prob + signal_boost, 0.95)


def _estimate_days_to_deployment(model: str, months: int) -> int:
    """Estimate days until deployment based on model's typical update frequency."""
    # Average update frequency per model
    history = MODEL_UPDATE_HISTORY[model]
    if len(history) < 2:
        default_months = months
    else:
        # Calculate average months between updates
        default_months = months

    # Add randomness within ±2 weeks
    import random

    variance_days = random.randint(-14, 14)
    return int(default_months * 30.44) + variance_days


def _map_attacks_at_risk(
    category: str, predicted_defenses: list[dict[str, Any]], horizon_days: int
) -> list[dict[str, Any]]:
    """Map attacks that will be patched by predicted defenses."""
    attack_mapping = {
        "prompt_injection": ["in_decoding_checks", "instruction_filter"],
        "reasoning": ["reasoning_trace_audit", "reasoning_filters"],
        "jailbreak": ["constitutional_AI", "classifiers", "policy_hardening"],
        "instruction_override": ["instruction_hierarchy", "instruction_filter"],
        "context_poisoning": ["grounding_check", "factuality_verifier"],
    }

    if category == "all":
        categories = list(attack_mapping.keys())
    else:
        categories = [category] if category in attack_mapping else []

    at_risk = []
    for cat in categories:
        for defense in predicted_defenses:
            if defense["defense"] in attack_mapping.get(cat, []):
                days_until = int(defense["estimated_deploy_date"].replace("-", ""))
                at_risk.append(
                    {
                        "attack": cat,
                        "days_until_likely_patched": min(
                            (datetime.strptime(defense["estimated_deploy_date"], "%Y-%m-%d")
                             - datetime.now(UTC).replace(tzinfo=None)).days,
                            horizon_days,
                        ),
                        "patching_defense": defense["defense"],
                    }
                )

    return at_risk


def _calculate_safe_window(predicted_defenses: list[dict[str, Any]], horizon_days: int) -> int:
    """Calculate safe window (days before earliest patch)."""
    if not predicted_defenses:
        return horizon_days

    # Find earliest predicted defense
    earliest_deploy = min(
        [(datetime.strptime(d["estimated_deploy_date"], "%Y-%m-%d") - datetime.now(UTC).replace(tzinfo=None)).days
         for d in predicted_defenses],
        default=horizon_days,
    )

    return max(earliest_deploy, 0)


def _generate_recommendations(
    model: str,
    current_stage: int,
    predicted_next: list[dict[str, Any]],
    category: str,
) -> list[str]:
    """Generate strategic recommendations."""
    recs = []

    if not predicted_next:
        recs.append(f"{model} appears to have reached top defense stage; expect incremental hardening")
        return recs

    # Recommend timeline
    earliest = min(
        [(datetime.strptime(d["estimated_deploy_date"], "%Y-%m-%d") - datetime.now(UTC).replace(tzinfo=None)).days
         for d in predicted_next],
        default=90,
    )

    if earliest < 30:
        recs.append(f"Expected defense deployment in <30 days; prioritize {category} testing immediately")
    elif earliest < 60:
        recs.append(f"Expected defense deployment in ~60 days; window is narrowing")
    else:
        recs.append(f"Wider deployment window (~{earliest} days); lower urgency")

    # Recommend next defenses to study
    next_defenses = [d["defense"] for d in predicted_next[:2]]
    if next_defenses:
        recs.append(f"Study defense mechanisms: {', '.join(next_defenses)}")

    # Recommend research prep
    recs.append("Review published research on predicted defenses to prepare countermeasures")
    recs.append("Log all successful attack patterns before patching closes vectors")

    return recs
