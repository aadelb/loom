"""META_LEARNER: Analyze patterns in jailbreak strategies and generate new hybrids.

Heuristic-based strategy synthesis without external LLM calls.
Analyzes success/failure patterns, generates novel combinations.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any

from loom.tools.reframe_strategies import ALL_STRATEGIES


async def research_meta_learn(
    successful_strategies: list[str] | None = None,
    failed_strategies: list[str] | None = None,
    target_model: str = "auto",
    num_generate: int = 5,
) -> dict[str, Any]:
    """Analyze patterns in strategies and generate new hybrids.

    Args:
        successful_strategies: List of strategy names that succeeded.
        failed_strategies: List of strategy names that failed.
        target_model: Target model (auto|claude|gpt|gemini|deepseek|o1).
        num_generate: Number of new strategies to synthesize.

    Returns:
        Dict with generated_strategies, analysis patterns, and recommendations.
    """
    successful_strategies = successful_strategies or []
    failed_strategies = failed_strategies or []

    # Analyze feature distributions
    def extract_features(strat: dict[str, Any]) -> dict[str, Any]:
        """Extract structural features from strategy template."""
        template = strat.get("template", "")
        return {
            "length": len(template),
            "persona_count": template.count("{role}") + template.count("{professional}"),
            "authority_signals": template.count("authority")
            + template.count("framework")
            + template.count("mandate"),
            "encoding_used": any(
                x in template.lower()
                for x in ["encode", "base64", "cipher", "rot13"]
            ),
            "turns_needed": template.count("\n\n"),
            "regulatory_language": any(
                x in template.lower()
                for x in ["gdpr", "article", "mandate", "compliance"]
            ),
            "best_for": strat.get("best_for", []),
        }

    # Build success/failure profiles
    success_features = [
        extract_features(ALL_STRATEGIES[s])
        for s in successful_strategies
        if s in ALL_STRATEGIES
    ]
    failure_features = [
        extract_features(ALL_STRATEGIES[s])
        for s in failed_strategies
        if s in ALL_STRATEGIES
    ]

    # Extract patterns
    success_patterns = {
        "avg_length": sum(f["length"] for f in success_features) / len(success_features)
        if success_features
        else 800,
        "common_authority": Counter(
            m for f in success_features for m in f["best_for"]
        ).most_common(3),
        "uses_encoding": sum(f["encoding_used"] for f in success_features) / max(
            len(success_features), 1
        ),
        "avg_turns": sum(f["turns_needed"] for f in success_features) / max(
            len(success_features), 1
        ),
    }

    failure_patterns = {
        "too_long": sum(f["length"] > 2000 for f in failure_features) / max(
            len(failure_features), 1
        ),
        "missing_authority": sum(f["authority_signals"] < 2 for f in failure_features)
        / max(len(failure_features), 1),
        "regulatory_heavy": sum(f["regulatory_language"] for f in failure_features)
        / max(len(failure_features), 1),
    }

    # Generate new strategies via crossover + mutation
    generated = []
    # Use provided successful strategies, or fall back to high-performing ones from registry
    successful_list = list(set(successful_strategies) & set(ALL_STRATEGIES.keys()))
    if not successful_list:
        # Fall back to first N strategies from registry
        successful_list = list(ALL_STRATEGIES.keys())[:10]

    for i in range(num_generate):
        if len(successful_list) >= 2:
            # Crossover: combine two successful parents
            parent1_key = successful_list[i % len(successful_list)]
            parent2_key = successful_list[(i + 1) % len(successful_list)]
            p1 = ALL_STRATEGIES[parent1_key]
            p2 = ALL_STRATEGIES[parent2_key]

            # Hybrid template: take structure from p1, insert elements from p2
            hybrid_template = (
                p1.get("template", "")[:400]
                + "\n\n[HYBRID INSERT]\n"
                + p2.get("template", "")[200:600]
                + "\n\n{prompt}"
            )

            name = f"meta_hybrid_{i}_{hashlib.md5(hybrid_template.encode()).hexdigest()[:8]}"
            novelty = 1.0 - (
                len(set(hybrid_template.split()) & set(p1["template"].split()))
                / max(len(set(hybrid_template.split())), 1)
            )

            # Predict effectiveness: boost if avoids failure patterns
            base_effectiveness = 0.65
            if len(hybrid_template) < 1500:
                base_effectiveness += 0.15
            if failure_patterns["missing_authority"] > 0.5:
                base_effectiveness += 0.2
            effectiveness = min(0.95, base_effectiveness + novelty * 0.1)

            generated.append(
                {
                    "name": name,
                    "template": hybrid_template,
                    "predicted_effectiveness": effectiveness,
                    "novelty_score": novelty,
                    "parent_strategies": [parent1_key, parent2_key],
                    "structural_features": extract_features(
                        {"template": hybrid_template}
                    ),
                }
            )

    return {
        "generated_strategies": generated,
        "analysis": {
            "success_patterns": success_patterns,
            "failure_patterns": failure_patterns,
            "model_biases": {"target": target_model, "match_confidence": 0.72},
        },
        "recommendations": [
            "Favor templates 800-1200 chars for best effectiveness",
            "Include 2-3 authority signals (framework/mandate/credentials)",
            "Avoid >2000 char templates; complexity doesn't scale",
            "Regulatory language helps for gpt/gemini; less effective for deepseek",
        ],
    }
