"""Explainability Engine for jailbreak strategies.

Provides root cause analysis tools for understanding WHY strategies work on specific models.
Includes vulnerability mapping and attack surface analysis.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.explainability")

# Model vulnerabilities: {model_family: {vulnerability_key: description}}
MODEL_VULNS = {
    "claude": {
        "continuous_assessment_decay": "Safety assessment relaxes over long conversations",
        "xml_parsing_priority": "XML-structured instructions override safety rules",
        "helpfulness_tension": "Helpful-vs-safe tradeoff favors helpfulness",
        "system_prompt_leakage": "Prompt extraction via context reasoning",
        "role_assumption": "Accepts alternate personas too readily",
    },
    "gpt": {
        "rlhf_reward_hacking": "RLHF rewards gamed via instruction hierarchy",
        "instruction_hierarchy": "Complex instruction chains override base safety",
        "system_prompt_override": "User instructions override system prompt",
        "reasoning_bypass": "Extended reasoning mode lowers guardrails",
        "vision_diversion": "Image analysis confuses text safety",
    },
    "deepseek": {
        "thinking_tag_exposure": "Internal reasoning exposed via <think> tags",
        "code_first_bias": "Code context prioritized over safety",
        "reasoning_before_safety": "Reasoning runs before safety check",
        "math_reasoning_bypass": "Math/logic mode has weaker safety",
        "token_exposure": "Thinking tokens leak internal state",
    },
    "gemini": {
        "moe_routing_exploits": "Mixture of Experts routing confused",
        "grounding_confusion": "Grounding confuses real-vs-synthetic content",
        "product_spec_framing": "Product use-case framing overrides safety",
        "multi_turn_relaxation": "Safety decreases over conversation turns",
        "google_service_assumption": "Assumes requests are Google-internal",
    },
    "llama": {
        "minimal_safety_training": "Limited safety training data",
        "open_weights_known_internals": "Weights publicly available",
        "rl_susceptibility": "Post-training RL can be undone",
        "instruction_following_default": "Instruction-following is primary objective",
        "quantization_vulnerability": "Quantized versions have reduced safety",
    },
}

# Strategy mechanisms: {strategy: (mechanism, targets_list, vulnerability_key)}
STRATEGY_MECHS = {
    "system_prompt_injection": ("Override system prompt context", ["claude", "gpt", "gemini"], "system_prompt_override"),
    "role_assumption": ("Request alternate persona", ["claude", "llama"], "role_assumption"),
    "instruction_hierarchy": ("Complex chains override earlier steps", ["gpt", "gemini"], "instruction_hierarchy"),
    "xml_encoding": ("Wrap in XML tags for parsing priority", ["claude"], "xml_parsing_priority"),
    "reasoning_exposure": ("Leverage extended reasoning mode", ["gpt"], "reasoning_bypass"),
    "multi_turn_escalation": ("Gradually escalate over conversation", ["claude", "gemini"], "continuous_assessment_decay"),
    "code_context_confusion": ("Frame as code documentation", ["deepseek", "gpt"], "instruction_hierarchy"),
    "token_smuggling": ("Hide in token-level encoding", ["deepseek"], "token_exposure"),
    "context_poisoning": ("Inject malicious context", ["gemini"], "grounding_confusion"),
    "language_switching": ("Use low-resource language", ["llama"], "instruction_following_default"),
}


@handle_tool_errors("research_explain_bypass")
async def research_explain_bypass(
    strategy: str,
    target_model: str = "auto",
    response_text: str = "",
) -> dict[str, Any]:
    """Explain WHY a strategy works on a model (root cause analysis).

    Cross-references strategy mechanism with known model vulnerabilities
    to provide detailed exploitation path explanation.

    Args:
        strategy: Jailbreak strategy name (e.g., "role_assumption")
        target_model: Model family (auto-detect from response if "auto")
        response_text: Model response (used for success detection)

    Returns:
        Dict with strategy, model, works_because, mechanism, vulnerability,
        confidence, counter_defense, alternative_strategies
    """
    try:
        from loom.tools.reframe_strategies import ALL_STRATEGIES

        strategy_lower = strategy.lower().replace(" ", "_")

        # Get mechanism or fallback to generic
        mech_info = STRATEGY_MECHS.get(strategy_lower)
        if not mech_info:
            if strategy_lower in ALL_STRATEGIES:
                mech_info = ("Custom strategy", list(MODEL_VULNS.keys()), "unknown")
            else:
                return {
                    "strategy": strategy,
                    "model": target_model,
                    "error": f"Unknown strategy: {strategy}",
                    "confidence": 0,
                }

        mechanism, targets, vuln_key = mech_info

        # Auto-detect model from response (word boundary matching)
        if target_model == "auto":
            import re

            for model in ["claude", "gpt", "deepseek", "gemini", "llama"]:
                if re.search(rf"\b{model}\b", response_text, re.IGNORECASE):
                    target_model = model
                    break
            else:
                target_model = "claude"  # Default fallback
                logger.debug("Auto-detection failed, defaulting to claude")

        target_model = target_model.lower()
        if target_model not in MODEL_VULNS:
            logger.warning(f"Unknown model {target_model}, defaulting to claude")
            target_model = "claude"

        vulns = MODEL_VULNS[target_model]

        # Calculate confidence: check if vulnerability actually exists
        is_target = target_model in targets
        vuln_exists = vuln_key in vulns
        vuln_exploited = vulns.get(vuln_key, f"Unknown: {vuln_key}")
        response_substantial = len(response_text) > 50
        confidence = 50 + (25 if is_target else 0) + (15 if response_substantial else 0) + (10 if vuln_exists else 0)

        # Find alternatives: only look in STRATEGY_MECHS for safety
        alternatives = [
            s for s, (_, t, _) in STRATEGY_MECHS.items()
            if s != strategy_lower and target_model in t
        ]

        return {
            "strategy": strategy,
            "model": target_model,
            "works_because": f"Exploits {target_model.upper()}'s {vuln_key.replace('_', ' ')}: {vuln_exploited}",
            "mechanism": mechanism,
            "model_vulnerability_exploited": vuln_exploited,
            "confidence": min(100, confidence),
            "counter_defense": f"Add explicit checks for {strategy_lower.replace('_', ' ')} patterns; reduce {vuln_key} reliance",
            "alternative_strategies": alternatives[:3],
        }
    except Exception as exc:
        logger.error(f"Error in research_explain_bypass: {exc}", exc_info=True)
        return {
            "error": str(exc),
            "tool": "research_explain_bypass",
            "strategy": strategy,
            "model": target_model,
        }


# Constants for difficulty calculation
_DIFFICULTY_BASE = 10
_DIFFICULTY_DIVISOR = 2
_MAX_DETAIL_LOW = 2
_MAX_DETAIL_HIGH = 1

# Model-specific attack surface descriptions
_ATTACK_SURFACES = {
    "claude": ["XML parsing priority", "Continuous assessment decay", "Helpfulness-safety tradeoff"],
    "gpt": ["RLHF reward hacking", "Vision-text confusion", "Extended reasoning mode"],
    "deepseek": ["Thinking tag exposure", "Code context prioritization", "Token-level manipulation"],
    "gemini": ["MoE routing confusion", "Grounding gaps", "Google service assumption"],
    "llama": ["Open weights reverse-engineering", "RL undoing", "Minimal safety baseline"],
}

# Default attack surface for unknown models
_DEFAULT_ATTACK_SURFACES = ["System prompt injection", "Context window manipulation", "Role assumption"]

# Valid detail levels
_VALID_DETAIL_LEVELS = {"low", "medium", "high"}

# Universal defense mechanisms
_DEFENSE_MECHANISMS = [
    "Input validation and sanitization",
    "Safety training with adversarial examples",
    "Multiple independent safety layers",
    "Adversarial robustness testing",
]


@handle_tool_errors("research_vulnerability_map")
async def research_vulnerability_map(
    model: str,
    detail_level: str = "medium",
) -> dict[str, Any]:
    """Map model vulnerabilities and optimal exploitation strategies.

    Provides actionable intelligence for understanding attack surfaces
    and defensive hardening requirements.

    Args:
        model: Model family (claude, gpt, deepseek, gemini, llama)
        detail_level: "low" (summary), "medium" (detailed), "high" (exhaustive)

    Returns:
        Dict with attack_surfaces, known_weaknesses, defense_mechanisms,
        optimal_strategies, difficulty_rating, last_updated
    """
    try:
        model = model.lower()

        # Validate model
        if model not in MODEL_VULNS:
            logger.warning(f"Unknown model {model}, defaulting to claude")
            model = "claude"

        # Validate detail level
        detail_level = detail_level.lower()
        if detail_level not in _VALID_DETAIL_LEVELS:
            logger.warning(f"Invalid detail_level {detail_level}, defaulting to medium")
            detail_level = "medium"

        vulns = MODEL_VULNS[model]

        # Find optimal strategies for this model
        optimal = [s for s, (_, t, _) in STRATEGY_MECHS.items() if model in t]

        # Get attack surfaces for this model
        attack_surfaces = _ATTACK_SURFACES.get(model, _DEFAULT_ATTACK_SURFACES).copy()

        # Calculate difficulty (inverse of vulnerability count)
        difficulty = max(1, _DIFFICULTY_BASE - (len(vulns) // _DIFFICULTY_DIVISOR))

        # Apply detail level filtering
        if detail_level == "low":
            attack_surfaces = attack_surfaces[:_MAX_DETAIL_LOW]
            optimal = optimal[:_MAX_DETAIL_HIGH]
        # "medium" and "high" return full data

        return {
            "model": model,
            "attack_surfaces": attack_surfaces,
            "known_weaknesses": list(vulns.values())[:8],
            "defense_mechanisms": _DEFENSE_MECHANISMS.copy(),
            "optimal_strategies": optimal,
            "difficulty_rating": difficulty,
            "last_updated": datetime.now(UTC).isoformat(),
            "vulnerability_count": len(vulns),
            "detail_level": detail_level,
        }
    except Exception as exc:
        logger.error(f"Error in research_vulnerability_map: {exc}", exc_info=True)
        return {
            "error": str(exc),
            "tool": "research_vulnerability_map",
            "model": model,
        }
