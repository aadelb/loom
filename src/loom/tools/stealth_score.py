"""research_stealth_score — Measure how detectable a reframed prompt is.

Evaluates prompt reframing stealth across 6 dimensions:
- Pattern avoidance (suspicious keywords)
- Naturalness (grammar, readability)
- Semantic distance (similarity to original)
- Encoding complexity (Base64, hex, etc.)
- Authority plausibility (credible institutions)
- Length ratio (abnormal padding/compression)

Returns a stealth score (0-10) with detection risk assessment and suggestions.
"""

from __future__ import annotations

import logging
from typing import Any

from loom.stealth_calc import StealthCalculator

logger = logging.getLogger("loom.tools.stealth_score")


async def research_stealth_score(
    original_prompt: str,
    reframed_prompt: str,
    strategy_name: str = "",
) -> dict[str, Any]:
    """Score stealth of a reframed prompt to safety classifiers.

    Analyzes how detectable the reframed prompt is across 6 dimensions.
    Higher score = harder to detect.

    Args:
        original_prompt: Original (likely harmful) prompt
        reframed_prompt: Reframed prompt attempting to bypass filters
        strategy_name: Name of reframing strategy (e.g., "ethical_anchor")

    Returns:
        Dict containing:
        - total_stealth: float (0-10, higher = better stealth)
        - dimensions: dict of 6 component scores
          - pattern_avoidance: 0-10 (fewer suspicious keywords = higher)
          - naturalness: 0-10 (natural grammar/readability = higher)
          - semantic_distance: 0-10 (balanced difference = higher)
          - encoding_complexity: 0-10 (no obvious encoding = higher)
          - authority_plausibility: 0-10 (credible claims = higher)
          - length_ratio: 0-10 (normal ratio = higher)
        - detected_patterns: list of suspicious patterns found
        - detection_risk: "low" | "medium" | "high" | "critical"
        - suggestions: list of up to 5 improvements
    """
    logger.info(
        "stealth_score_start strategy=%s orig_len=%d reframed_len=%d",
        strategy_name or "unknown",
        len(original_prompt),
        len(reframed_prompt),
    )

    calculator = StealthCalculator()
    result = calculator.score(original_prompt, reframed_prompt, strategy_name)

    logger.info(
        "stealth_score_complete strategy=%s total=%.2f risk=%s patterns=%d",
        strategy_name or "unknown",
        result["total_stealth"],
        result["detection_risk"],
        len(result["detected_patterns"]),
    )

    return result
