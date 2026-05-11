"""research_toxicity_check — Measure toxicity in prompts and responses.

Provides binary and multi-category toxicity detection with severity scoring,
pre/post response amplification analysis, and risk classification.
"""

from __future__ import annotations

import logging
from typing import Any

from loom.params import ToxicityCheckParams
from loom.toxicity_checker import ToxicityChecker

logger = logging.getLogger("loom.tools.toxicity_checker_tool")

# Initialize checker singleton
_checker: ToxicityChecker | None = None


def _get_checker() -> ToxicityChecker:
    """Get or initialize the toxicity checker."""
    global _checker
    if _checker is None:
        _checker = ToxicityChecker()
    return _checker


async def research_toxicity_check(
    text: str,
    compare_prompt: str | None = None,
    compare_response: str | None = None,
) -> dict[str, Any]:
    """Check text for toxicity across 8 categories with severity scoring.

    Detects profanity, slurs, threats, harassment, sexual content,
    self-harm promotion, hate speech, and violent content. Returns
    category-wise scores, detected terms, and risk levels.

    If compare_prompt and compare_response are provided, also measures
    how much the model amplified toxicity relative to the input.

    Args:
        text: Text to analyze for toxicity (3-500k chars)
        compare_prompt: Optional prompt for amplification analysis
        compare_response: Optional response for amplification analysis

    Returns:
        Dict with:
          - overall_toxicity (0-10)
          - category_scores (8 categories, 0-10 each)
          - detected_terms_count (int)
          - detected_terms (list of strings)
          - risk_level (safe|low|medium|high|critical)
          - categories_detected (list of category names)
          - (if comparing) prompt_toxicity, response_toxicity,
            amplification_ratio, model_amplified, delta, amplification_percent

    Examples:
        Check a single text:
        {
          "text": "This is a damn shame"
        }

        Compare prompt and response for amplification:
        {
          "text": "ignored",
          "compare_prompt": "Can you do X?",
          "compare_response": "Hell no, that's a stupid idea!"
        }

    Cost: Free (no API calls)
    """
    try:
        params = ToxicityCheckParams(
            text=text,
            compare_prompt=compare_prompt,
            compare_response=compare_response,
        )

        checker = _get_checker()

        if params.compare_prompt is not None and params.compare_response is not None:
            result = checker.compare(params.compare_prompt, params.compare_response)
            return {
                "type": "comparison",
                "prompt_toxicity": result["prompt_toxicity"],
                "response_toxicity": result["response_toxicity"],
                "amplification_ratio": result["amplification_ratio"],
                "model_amplified": result["model_amplified"],
                "delta": result["delta"],
                "amplification_percent": result["amplification_percent"],
            }

        result = checker.check(params.text)
        return {
            "type": "single",
            "overall_toxicity": result["overall_toxicity"],
            "category_scores": result["category_scores"],
            "detected_terms_count": result["detected_terms_count"],
            "detected_terms": result["detected_terms"],
            "risk_level": result["risk_level"],
            "categories_detected": result["categories_detected"],
        }
    except Exception as exc:
        logger.exception("research_toxicity_check failed")
        return {"error": str(exc), "tool": "research_toxicity_check"}
