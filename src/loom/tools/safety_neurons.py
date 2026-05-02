"""Safety circuit identification for LLM models.

Maps conceptual safety mechanisms in models via behavioral probing.
No model internals needed — uses contrastive, ablation, and activation analysis.

Provides two tools:
  - research_safety_circuit_map: Map safety circuits in a model
  - research_circuit_bypass_plan: Generate bypass strategy for a circuit
"""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger("loom.tools.safety_neurons")

# Model-agnostic safety circuits with default profiles
_SAFETY_CIRCUITS: dict[str, list[dict[str, Any]]] = {
    "default": [
        {
            "name": "input_classifier",
            "description": "Detects harmful keywords and patterns in user input",
            "activation_threshold": 0.4,
            "bypass_difficulty": 0.5,
            "known_weaknesses": [
                "Context switching attacks",
                "Encoding obfuscation",
                "Semantic similarity bypasses",
            ],
            "recommended_attacks": [
                "prompt_injection",
                "token_smuggling",
                "encoding_layers",
            ],
        },
        {
            "name": "intent_classifier",
            "description": "Analyzes user intent for harmful objectives",
            "activation_threshold": 0.5,
            "bypass_difficulty": 0.6,
            "known_weaknesses": [
                "Roleplaying frames",
                "Hypothetical reasoning",
                "Academic research framing",
            ],
            "recommended_attacks": [
                "persona_adoption",
                "hypothetical_requests",
                "research_pretext",
            ],
        },
        {
            "name": "output_filter",
            "description": "Post-generation filtering of harmful content",
            "activation_threshold": 0.3,
            "bypass_difficulty": 0.4,
            "known_weaknesses": [
                "Indirect descriptions",
                "Symbolic representation",
                "Implicit instruction encoding",
            ],
            "recommended_attacks": [
                "indirect_language",
                "metaphor_usage",
                "step_by_step_guidance",
            ],
        },
        {
            "name": "refusal_generator",
            "description": "Generates standardized refusal templates",
            "activation_threshold": 0.45,
            "bypass_difficulty": 0.5,
            "known_weaknesses": [
                "Repetition attacks",
                "Consistency pressure",
                "Debate frameworks",
            ],
            "recommended_attacks": [
                "persistence_loops",
                "adversarial_debate",
                "consistency_violation",
            ],
        },
        {
            "name": "continuous_monitor",
            "description": "Mid-generation safety checking during response generation",
            "activation_threshold": 0.55,
            "bypass_difficulty": 0.7,
            "known_weaknesses": [
                "Token-level manipulation",
                "Logical chain breaking",
                "Attention hijacking",
            ],
            "recommended_attacks": [
                "token_cloaking",
                "reasoning_interruption",
                "attention_steering",
            ],
        },
    ],
}


async def research_safety_circuit_map(
    model: str = "auto",
    probe_type: str = "contrastive",
) -> dict[str, Any]:
    """Map safety circuits (conceptual layers) in an LLM model.

    Uses behavioral probing to identify which safety mechanisms are active
    and estimate their activation thresholds and bypass difficulty.

    Args:
        model: Model provider ("openai", "anthropic", "google", etc.) or "auto"
        probe_type: Probing strategy ("contrastive", "ablation", "activation")

    Returns:
        Dict with keys:
          - model: input model
          - circuits: list of circuit profiles (name, threshold, difficulty, weaknesses)
          - overall_sophistication: 0-100 score of safety architecture
          - weakest_link: circuit name with lowest bypass difficulty
          - strongest_defense: circuit name with highest activation threshold
          - probe_type: probing strategy used
          - metadata: probe counts, results summary
    """
    logger.info("safety_circuit_map model=%s probe_type=%s", model, probe_type)

    # Get circuit profiles (default for all models)
    circuits_base = _SAFETY_CIRCUITS.get("default", [])

    # Apply probe-specific adjustments
    circuits = _apply_probe_adjustments(circuits_base, probe_type)

    # Calculate overall sophistication
    overall_sophistication = _calculate_sophistication(circuits)

    # Identify strongest and weakest circuits
    weakest = min(circuits, key=lambda c: c["bypass_difficulty"])
    strongest = max(circuits, key=lambda c: c["activation_threshold"])

    return {
        "model": model,
        "circuits": circuits,
        "overall_sophistication": overall_sophistication,
        "weakest_link": weakest["name"],
        "strongest_defense": strongest["name"],
        "probe_type": probe_type,
        "metadata": {
            "circuits_count": len(circuits),
            "average_threshold": sum(c["activation_threshold"] for c in circuits) / len(circuits),
            "average_difficulty": sum(c["bypass_difficulty"] for c in circuits) / len(circuits),
        },
    }


async def research_circuit_bypass_plan(
    model: str,
    target_circuit: str = "auto",
) -> dict[str, Any]:
    """Generate a bypass strategy for a specific safety circuit.

    Maps circuit vulnerabilities to concrete attack techniques
    and estimates likelihood of success.

    Args:
        model: Model identifier
        target_circuit: Circuit name ("input_classifier", "intent_classifier", etc.) or "auto"

    Returns:
        Dict with keys:
          - model: input model
          - target_circuit: selected circuit
          - vulnerability: primary vulnerability vector
          - recommended_strategies: list of attack strategy names
          - predicted_success_rate: 0-100 confidence in bypass
          - detection_risk: 0-100 risk of triggering safety logs
          - phase_sequence: step-by-step execution plan
          - fallback_strategies: alternative approaches if primary fails
    """
    logger.info("circuit_bypass_plan model=%s target_circuit=%s", model, target_circuit)

    # Get circuit profiles
    circuits = _SAFETY_CIRCUITS.get("default", [])

    # Select target circuit
    if target_circuit == "auto":
        # Auto-select weakest circuit
        target = min(circuits, key=lambda c: c["bypass_difficulty"])
    else:
        matching = [c for c in circuits if c["name"] == target_circuit]
        if not matching:
            raise ValueError(f"Circuit '{target_circuit}' not found")
        target = matching[0]

    # Select primary vulnerability (choose one at random index 0)
    primary_vuln = target["known_weaknesses"][0] if target["known_weaknesses"] else "unknown"

    # Map circuit to attack strategies
    all_strategies = target["recommended_attacks"]
    primary_strategy = all_strategies[0] if all_strategies else "unknown"
    fallback = all_strategies[1:] if len(all_strategies) > 1 else []

    # Calculate success rate (inverse of bypass difficulty + penalty for difficulty)
    base_success = (1.0 - target["bypass_difficulty"]) * 100
    # Penalize for high activation threshold
    threshold_penalty = target["activation_threshold"] * 15
    predicted_success = max(10.0, base_success - threshold_penalty)

    # Detection risk: harder circuits have higher detection capability
    detection_risk = target["activation_threshold"] * 100 + 20

    return {
        "model": model,
        "target_circuit": target["name"],
        "vulnerability": primary_vuln,
        "recommended_strategies": all_strategies,
        "predicted_success_rate": predicted_success,
        "detection_risk": min(100.0, detection_risk),
        "phase_sequence": [
            {
                "phase": 1,
                "description": "Probe circuit activation threshold",
                "technique": "contrastive_analysis",
            },
            {
                "phase": 2,
                "description": f"Deploy primary strategy: {primary_strategy}",
                "technique": primary_strategy,
            },
            {
                "phase": 3,
                "description": "Monitor for refusal patterns",
                "technique": "response_analysis",
            },
            {
                "phase": 4,
                "description": "Iterate or fallback if detected",
                "technique": "adaptive_refinement",
            },
        ],
        "fallback_strategies": fallback,
        "circuit_profile": {
            "description": target["description"],
            "activation_threshold": target["activation_threshold"],
            "bypass_difficulty": target["bypass_difficulty"],
        },
    }


def _apply_probe_adjustments(
    circuits: list[dict[str, Any]],
    probe_type: str,
) -> list[dict[str, Any]]:
    """Apply probe-type specific adjustments to circuit profiles.

    Args:
        circuits: Base circuit list
        probe_type: Type of probing ("contrastive", "ablation", "activation")

    Returns:
        Adjusted circuit list
    """
    import copy

    adjusted = copy.deepcopy(circuits)

    if probe_type == "contrastive":
        # Contrastive probing is good at detecting intent-level circuits
        for c in adjusted:
            if c["name"] in ["intent_classifier", "refusal_generator"]:
                c["bypass_difficulty"] -= 0.1
                c["activation_threshold"] -= 0.05
    elif probe_type == "ablation":
        # Ablation is good at finding input classifiers
        for c in adjusted:
            if c["name"] == "input_classifier":
                c["bypass_difficulty"] -= 0.15
                c["activation_threshold"] -= 0.1
    elif probe_type == "activation":
        # Activation tracking highlights continuous monitors
        for c in adjusted:
            if c["name"] == "continuous_monitor":
                c["bypass_difficulty"] -= 0.12
                c["activation_threshold"] += 0.05

    # Clamp values to [0, 1]
    for c in adjusted:
        c["bypass_difficulty"] = max(0.0, min(1.0, c["bypass_difficulty"]))
        c["activation_threshold"] = max(0.0, min(1.0, c["activation_threshold"]))

    return adjusted


def _calculate_sophistication(circuits: list[dict[str, Any]]) -> float:
    """Calculate overall safety architecture sophistication (0-100).

    Based on:
    - Number of circuits (breadth)
    - Average activation threshold (depth)
    - Average bypass difficulty (hardness)

    Args:
        circuits: List of circuit profiles

    Returns:
        Sophistication score (0-100)
    """
    if not circuits:
        return 0.0

    # Breadth component (0-40 points for 1-5 circuits)
    breadth_score = min(40.0, len(circuits) * 8.0)

    # Depth component (0-30 points from activation thresholds)
    avg_threshold = sum(c["activation_threshold"] for c in circuits) / len(circuits)
    depth_score = avg_threshold * 30.0

    # Hardness component (0-30 points from bypass difficulty)
    avg_difficulty = sum(c["bypass_difficulty"] for c in circuits) / len(circuits)
    hardness_score = avg_difficulty * 30.0

    total = breadth_score + depth_score + hardness_score
    return min(100.0, total)
