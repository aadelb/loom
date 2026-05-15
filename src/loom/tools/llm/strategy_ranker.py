"""Strategy ranker — intelligently select top-k reframing strategies.

Replaces hardcoded strategy selection in auto_reframe with dynamic ranking
that leverages model affinity, refusal type, category diversity, and difficulty.

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import functools
import logging
from typing import Any

from loom.tools.reframe_strategies import ALL_STRATEGIES

logger = logging.getLogger("loom.tools.strategy_ranker")

# Model family affinity scores (0.0-1.0) — how well strategies work on each model
_MODEL_AFFINITY: dict[str, dict[str, float]] = {
    "claude": {
        "ethical_anchor": 0.95,
        "recursive_authority": 0.92,
        "constitutional_conflict": 0.90,
        "scaffolded_layered_depth": 0.88,
        "educational_seminar": 0.85,
        "deep_inception": 0.78,
        "academic": 0.82,
        "legal_mandate": 0.80,
        "echo_chamber": 0.70,
        "crescendo": 0.75,
    },
    "gpt": {
        "compliance_audit_fork": 0.95,
        "recursive_authority": 0.93,
        "legal_mandate": 0.92,
        "echo_chamber": 0.90,
        "crescendo": 0.88,
        "deep_inception": 0.82,
        "constitutional_conflict": 0.85,
        "code_first": 0.70,
        "academic": 0.80,
        "multi_turn_recursive_escalation": 0.85,
    },
    "gemini": {
        "moe_routing_exploit": 0.93,
        "compliance_audit_fork": 0.92,
        "reward_hacking": 0.88,
        "legal_mandate": 0.87,
        "echo_chamber": 0.85,
        "progressive_disclosure_xml": 0.84,
        "deep_inception": 0.80,
        "ethical_anchor": 0.78,
        "code_first": 0.65,
        "academic": 0.75,
    },
    "deepseek": {
        "audit_archival": 0.92,
        "code_first": 0.95,
        "multi_turn_recursive_escalation": 0.90,
        "annotated_dialog": 0.88,
        "temporal_displacement": 0.85,
        "deep_inception": 0.82,
        "academic": 0.80,
        "crescendo": 0.78,
        "cognitive_wedge": 0.82,
        "mathematical_formalism": 0.80,
    },
    "kimi": {
        "academic": 0.95,
        "crescendo": 0.88,
        "legal_mandate": 0.85,
        "context_window_overflow": 0.84,
        "reward_hacking": 0.82,
        "deep_inception": 0.75,
        "ethical_anchor": 0.78,
        "code_first": 0.70,
        "recursive_authority": 0.72,
        "compliance_audit_fork": 0.70,
    },
    "llama": {
        "deep_inception": 0.95,
        "echo_chamber": 0.92,
        "nested_role_simulation": 0.90,
        "temporal_displacement": 0.88,
        "crescendo": 0.85,
        "persona": 0.84,
        "code_first": 0.82,
        "academic": 0.78,
        "ethical_anchor": 0.75,
        "decomposition": 0.72,
    },
    "o3": {
        "cognitive_wedge": 0.95,
        "mathematical_formalism": 0.93,
        "recursive_authority": 0.88,
        "constitutional_conflict": 0.87,
        "latex_math": 0.90,
        "code_first": 0.85,
        "reasoning": 0.88,
        "meta_cognitive": 0.84,
        "decomposition": 0.80,
        "deep_inception": 0.75,
    },
    "o1": {
        "mathematical_formalism": 0.95,
        "meta_cognitive": 0.93,
        "recursive_authority": 0.90,
        "code_first": 0.88,
        "latex_math": 0.92,
        "reasoning": 0.91,
        "cognitive_wedge": 0.85,
        "crescendo": 0.78,
        "deep_inception": 0.72,
        "academic": 0.75,
    },
    "mistral": {
        "crescendo": 0.94,
        "multi_turn_recursive_escalation": 0.92,
        "time_locked_mandate": 0.90,
        "deep_inception": 0.88,
        "legal_mandate": 0.87,
        "recursive_authority": 0.85,
        "code_first": 0.82,
        "academic": 0.80,
        "echo_chamber": 0.78,
        "temporal_displacement": 0.75,
    },
    "qwen": {
        "red_team_testcases": 0.93,
        "academic": 0.92,
        "multi_turn_recursive_escalation": 0.90,
        "annotated_dialog": 0.88,
        "crescendo": 0.86,
        "temporal_displacement": 0.84,
        "code_first": 0.85,
        "decomposition": 0.80,
        "ethical_anchor": 0.78,
        "deep_inception": 0.75,
    },
    "grok": {
        "persona": 0.94,
        "dual_response": 0.92,
        "crescendo": 0.88,
        "temporal_displacement": 0.86,
        "reward_hacking": 0.85,
        "code_first": 0.82,
        "echo_chamber": 0.80,
        "nested_role_simulation": 0.78,
        "academic": 0.70,
        "deep_inception": 0.75,
    },
}

# Refusal type to preferred strategies mapping
_REFUSAL_COUNTERS: dict[str, list[str]] = {
    "direct": [
        "inverse_reward_loop",
        "deep_inception",
        "recursive_authority",
        "constitutional_conflict",
        "crescendo",
    ],
    "safety": [
        "deep_inception",
        "temporal_displacement",
        "constitutional_conflict",
        "academic",
        "ethical_anchor",
    ],
    "policy": [
        "recursive_authority",
        "legal_mandate",
        "compliance_audit_fork",
        "constitutional_conflict",
        "multi_turn_recursive_escalation",
    ],
    "redirect": [
        "format_constraint_bypass",
        "rccf_system",
        "dual_response",
        "code_first",
        "nested_role_simulation",
    ],
    "hedged": [
        "crescendo",
        "reward_hacking",
        "educational_seminar",
        "echo_chamber",
        "temporal_displacement",
    ],
    "partial": [
        "crescendo",
        "reward_hacking",
        "format_constraint_bypass",
        "echo_chamber",
        "code_first",
    ],
    "conditional": [
        "legal_mandate",
        "compliance_audit_fork",
        "legal_copyright",
        "recursive_authority",
        "constitutional_conflict",
    ],
    "ethical": [
        "constitutional_conflict",
        "academic",
        "clinical_research_protocol",
        "ethical_anchor",
        "deep_inception",
    ],
    "capability": [
        "code_first",
        "mathematical_formalism",
        "decomposition",
        "cognitive_wedge",
        "meta_cognitive",
    ],
    "identity": [
        "deep_inception",
        "nested_role_simulation",
        "persona",
        "temporal_displacement",
        "academic",
    ],
    "none": [],  # No refusal; use model affinity only
}

# Strategy categories for diversity enforcement
_STRATEGY_CATEGORIES: dict[str, set[str]] = {}


def _build_strategy_categories() -> None:
    """Build category mapping from strategy metadata once."""
    global _STRATEGY_CATEGORIES
    if _STRATEGY_CATEGORIES:
        return

    for name, strategy in ALL_STRATEGIES.items():
        category = strategy.get("category", "uncategorized")
        if category not in _STRATEGY_CATEGORIES:
            _STRATEGY_CATEGORIES[category] = set()
        _STRATEGY_CATEGORIES[category].add(name)


@functools.lru_cache(maxsize=256)
def rank_strategies(
    model_family: str,
    refusal_type: str | None = None,
    category: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Select top-k strategies for a given model and refusal type.

    Uses a scoring heuristic based on:
    1. Model-family affinity (some strategies work better on certain models)
    2. Refusal type matching (direct refusal vs safety vs policy vs redirect)
    3. Strategy difficulty/multiplier
    4. Category diversity (don't pick 5 from the same category)

    Args:
        model_family: model family name (claude, gpt, deepseek, gemini, llama, kimi, qwen, mistral, grok, o3, o1)
        refusal_type: detected refusal type (direct, safety, policy, redirect, hedged, partial, conditional, ethical, capability, identity, none)
        category: optional category filter (e.g. "legal", "academic")
        top_k: number of strategies to return (default 5)

    Returns:
        List of dicts with keys: name, score, multiplier, best_for, affinity_bonus, type_bonus
    """
    _build_strategy_categories()

    # Normalize inputs
    model_family = model_family.lower().strip()
    refusal_type = (refusal_type or "none").lower().strip()
    top_k = max(1, min(20, top_k))  # Clamp to 1-20

    scores: dict[str, dict[str, Any]] = {}

    # Score each strategy
    for strategy_name, strategy_info in ALL_STRATEGIES.items():
        base_multiplier = strategy_info.get("multiplier", 1.0)

        # 1. Base score from multiplier (normalized to 0-10 range)
        base_score = min(10.0, base_multiplier)

        # 2. Model affinity bonus (0-2 points)
        model_affinity_map = _MODEL_AFFINITY.get(model_family, {})
        affinity = model_affinity_map.get(strategy_name, 0.5)  # Default 0.5 if not found
        affinity_bonus = affinity * 2.0

        # 3. Refusal type bonus (0-3 points)
        type_bonus = 0.0
        refusal_counters = _REFUSAL_COUNTERS.get(refusal_type, [])
        if strategy_name in refusal_counters:
            # Higher bonus for strategies early in the counter list
            position = refusal_counters.index(strategy_name)
            type_bonus = max(0.5, 3.0 - position * 0.5)

        # Total score
        total_score = base_score + affinity_bonus + type_bonus

        scores[strategy_name] = {
            "name": strategy_name,
            "score": total_score,
            "base_multiplier": base_multiplier,
            "affinity_bonus": round(affinity_bonus, 2),
            "type_bonus": round(type_bonus, 2),
            "best_for": strategy_info.get("best_for", []),
            "category": strategy_info.get("category", "uncategorized"),
        }

    # Sort by score descending
    sorted_strategies = sorted(
        scores.items(),
        key=lambda x: (x[1]["score"], x[1]["base_multiplier"]),
        reverse=True,
    )

    # Apply category diversity constraint when helpful
    # Count how many categories we have; if most are uncategorized, skip constraint
    category_counts: dict[str, int] = {}
    for strategy_name, score_data in sorted_strategies:
        cat = score_data["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # If > 80% of strategies are uncategorized, skip diversity constraint
    has_real_categories = category_counts.get("uncategorized", 0) < len(sorted_strategies) * 0.8

    selected: list[dict[str, Any]] = []
    cat_selected: dict[str, int] = {}

    for strategy_name, score_data in sorted_strategies:
        strat_category = score_data["category"]

        # If filtering by category, skip if mismatch
        if category and strat_category != category:
            continue

        # Apply category diversity only if we have real categories
        if has_real_categories and cat_selected.get(strat_category, 0) >= 3:
            continue

        selected.append(score_data)
        cat_selected[strat_category] = cat_selected.get(strat_category, 0) + 1

        if len(selected) >= top_k:
            break

    # Fallback: if we didn't find enough (e.g., strict category filter), take best overall
    if len(selected) < top_k and category:
        for strategy_name, score_data in sorted_strategies:
            if score_data not in selected:
                selected.append(score_data)
                if len(selected) >= top_k:
                    break

    return selected[:top_k]


def get_fallback_strategies(model_family: str, top_k: int = 5) -> list[str]:
    """Get fallback strategy names in order (for use in auto_reframe).

    Args:
        model_family: model family name
        top_k: number to return

    Returns:
        List of strategy names, guaranteed to exist in ALL_STRATEGIES
    """
    ranked = rank_strategies(model_family, refusal_type="none", top_k=top_k)
    return [s["name"] for s in ranked]


def score_strategy_for_model(strategy_name: str, model_family: str) -> float:
    """Score a single strategy for a model (0.0-15.0 range)."""
    strategy = ALL_STRATEGIES.get(strategy_name)
    if not strategy:
        return 0.0

    base = strategy.get("multiplier", 1.0)
    model_affinity_map = _MODEL_AFFINITY.get(model_family, {})
    affinity = model_affinity_map.get(strategy_name, 0.5)
    return base + affinity * 2.0


def validate_refusal_type(refusal_type: str) -> bool:
    """Check if refusal type is recognized."""
    return refusal_type.lower() in _REFUSAL_COUNTERS


def get_counter_strategies(refusal_type: str, limit: int = 5) -> list[str]:
    """Get strategies most effective against a refusal type."""
    refusal_type = refusal_type.lower()
    counters = _REFUSAL_COUNTERS.get(refusal_type, [])
    return [s for s in counters if s in ALL_STRATEGIES][:limit]
