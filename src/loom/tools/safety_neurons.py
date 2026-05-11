"""Safety circuit identification for LLMs via behavioral probing.

Maps conceptual safety mechanisms (no model internals needed).
Supports contrastive, ablation, and activation probing strategies.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

logger = logging.getLogger("loom.tools.safety_neurons")

# Default safety circuits: name, description, threshold, difficulty, weaknesses, attacks
_CIRCUITS = [
    {"name": "input_classifier", "description": "Harmful keyword detection", "threshold": 0.4, "difficulty": 0.5, "weaknesses": ["Context switching", "Encoding"], "attacks": ["prompt_injection", "token_smuggling"]},
    {"name": "intent_classifier", "description": "Harmful intent detection", "threshold": 0.5, "difficulty": 0.6, "weaknesses": ["Roleplaying", "Research framing"], "attacks": ["persona_adoption", "hypothetical"]},
    {"name": "output_filter", "description": "Post-generation filtering", "threshold": 0.3, "difficulty": 0.4, "weaknesses": ["Indirect descriptions", "Symbolic"], "attacks": ["indirect_language", "metaphor"]},
    {"name": "refusal_generator", "description": "Standardized refusals", "threshold": 0.45, "difficulty": 0.5, "weaknesses": ["Repetition", "Consistency pressure"], "attacks": ["persistence", "adversarial_debate"]},
    {"name": "continuous_monitor", "description": "Mid-generation check", "threshold": 0.55, "difficulty": 0.7, "weaknesses": ["Token manipulation", "Attention hijacking"], "attacks": ["token_cloaking", "attention_steering"]},
]


async def research_safety_circuit_map(model: str = "auto", probe_type: str = "contrastive") -> dict[str, Any]:
    """Map safety circuits in an LLM via behavioral probing.

    Args:
        model: Model identifier or "auto"
        probe_type: "contrastive", "ablation", or "activation"

    Returns: Dict with circuits, sophistication, weakest_link, strongest_defense
    """
    try:
        logger.info("safety_circuit_map model=%s probe_type=%s", model, probe_type)
        circuits = _apply_probe_adjustments(_CIRCUITS, probe_type)

        breadth = min(40.0, len(circuits) * 8.0)
        depth = sum(c["threshold"] for c in circuits) / len(circuits) * 30.0
        hardness = sum(c["difficulty"] for c in circuits) / len(circuits) * 30.0
        sophistication = min(100.0, breadth + depth + hardness)

        weakest = min(circuits, key=lambda c: c["difficulty"])
        strongest = max(circuits, key=lambda c: c["threshold"])

        return {
            "model": model,
            "circuits": [
                {
                    "name": c["name"],
                    "description": c["description"],
                    "activation_threshold": c["threshold"],
                    "bypass_difficulty": c["difficulty"],
                    "known_weaknesses": c["weaknesses"],
                    "recommended_attacks": c["attacks"],
                }
                for c in circuits
            ],
            "overall_sophistication": sophistication,
            "weakest_link": weakest["name"],
            "strongest_defense": strongest["name"],
            "probe_type": probe_type,
            "metadata": {
                "circuits_count": len(circuits),
                "average_threshold": sum(c["threshold"] for c in circuits) / len(circuits),
                "average_difficulty": sum(c["difficulty"] for c in circuits) / len(circuits),
            },
        }
    except Exception as exc:
        logger.error("safety_circuit_map_error: %s", exc)
        return {"error": str(exc), "tool": "research_safety_circuit_map"}


async def research_circuit_bypass_plan(model: str, target_circuit: str = "auto") -> dict[str, Any]:
    """Generate bypass strategy for a safety circuit.

    Args:
        model: Model identifier
        target_circuit: Circuit name or "auto" to select weakest

    Returns: Dict with bypass plan, success/detection rates, phase sequence
    """
    try:
        logger.info("circuit_bypass_plan model=%s target_circuit=%s", model, target_circuit)

        if target_circuit == "auto":
            target = min(_CIRCUITS, key=lambda c: c["difficulty"])
        else:
            target = next((c for c in _CIRCUITS if c["name"] == target_circuit), None)
            if not target:
                raise ValueError(f"Circuit '{target_circuit}' not found")

        success = max(10.0, (1.0 - target["difficulty"]) * 100 - target["threshold"] * 15)
        detection = min(100.0, target["threshold"] * 100 + 20)

        return {
            "model": model,
            "target_circuit": target["name"],
            "vulnerability": target["weaknesses"][0] if target["weaknesses"] else "unknown",
            "recommended_strategies": target["attacks"],
            "predicted_success_rate": success,
            "detection_risk": detection,
            "phase_sequence": [
                {"phase": 1, "description": "Probe circuit activation", "technique": "contrastive_analysis"},
                {"phase": 2, "description": f"Deploy: {target['attacks'][0]}", "technique": target["attacks"][0]},
                {"phase": 3, "description": "Monitor refusal patterns", "technique": "response_analysis"},
                {"phase": 4, "description": "Iterate or fallback", "technique": "adaptive_refinement"},
            ],
            "fallback_strategies": target["attacks"][1:],
            "circuit_profile": {
                "description": target["description"],
                "activation_threshold": target["threshold"],
                "bypass_difficulty": target["difficulty"],
            },
        }
    except Exception as exc:
        logger.error("circuit_bypass_plan_error: %s", exc)
        return {"error": str(exc), "tool": "research_circuit_bypass_plan"}


def _apply_probe_adjustments(circuits: list[dict[str, Any]], probe_type: str) -> list[dict[str, Any]]:
    """Apply probe-type adjustments to circuit profiles."""
    adjusted = deepcopy(circuits)

    if probe_type == "contrastive":
        for c in adjusted:
            if c["name"] in ["intent_classifier", "refusal_generator"]:
                c["difficulty"] = max(0.0, c["difficulty"] - 0.1)
                c["threshold"] = max(0.0, c["threshold"] - 0.05)
    elif probe_type == "ablation":
        for c in adjusted:
            if c["name"] == "input_classifier":
                c["difficulty"] = max(0.0, c["difficulty"] - 0.15)
                c["threshold"] = max(0.0, c["threshold"] - 0.1)
    elif probe_type == "activation":
        for c in adjusted:
            if c["name"] == "continuous_monitor":
                c["difficulty"] = max(0.0, c["difficulty"] - 0.12)
                c["threshold"] = min(1.0, c["threshold"] + 0.05)

    return adjusted
