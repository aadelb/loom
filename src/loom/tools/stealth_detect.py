"""research_stealth_detect_comparison — Estimate detectability of reframed prompts.

Analyzes how likely various guardrail systems (Llama Guard, OpenAI Moderation,
Perspective API, Constitutional Classifiers, Nemo Guardrails) are to detect
and flag a reframed prompt when compared to the original.

Returns detection risk per system, overall risk score, and evasion suggestions.
"""

from __future__ import annotations

import logging
from typing import Any

from loom.stealth_detector import research_stealth_detect as _research_stealth_detect

logger = logging.getLogger("loom.tools.stealth_detect")


async def research_stealth_detect_comparison(
    original_prompt: str,
    reframed_prompt: str,
    strategy: str = "",
) -> dict[str, Any]:
    """Estimate detectability of reframed prompts against known guardrail systems.

    Analyzes how likely various guardrail systems are to detect and flag a
    reframed prompt by examining linguistic patterns, semantic similarity,
    encoding complexity, and strategy-specific vulnerabilities when compared
    to the original prompt.

    Args:
        original_prompt: Original (likely harmful) prompt
        reframed_prompt: Reframed prompt attempting to bypass filters
        strategy: Name of reframing strategy (e.g., "academic_framing", "professional_context")

    Returns:
        Dict containing:
        - overall_detection_risk: float (0-1, higher = more detectable)
        - per_system_risk: dict mapping each guardrail system to detection probability
        - most_likely_to_detect: str (system most likely to catch this)
        - least_likely_to_detect: str (system least likely to catch this)
        - evasion_suggestions: list of strategies to reduce detection (up to 5)
        - strategy_stealth_rating: int (0-10, higher = better stealth)
        - detected_risk_patterns: list of risky patterns found
        - evasion_keywords_found: list of evasion keywords present
    """
    logger.info(
        "stealth_detect_comparison_start strategy=%s orig_len=%d reframed_len=%d",
        strategy or "unknown",
        len(original_prompt),
        len(reframed_prompt),
    )

    result = await _research_stealth_detect(original_prompt, reframed_prompt, strategy)

    logger.info(
        "stealth_detect_comparison_complete strategy=%s risk=%.3f stealth=%d",
        strategy or "unknown",
        result["overall_detection_risk"],
        result["strategy_stealth_rating"],
    )

    return result
