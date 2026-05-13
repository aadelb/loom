"""research_deception_detect — Linguistic deception and fraud detection."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from loom.error_responses import handle_tool_errors

try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None  # type: ignore[assignment,misc]

logger = logging.getLogger("loom.tools.deception_detect")

# Hedging language indicators
HEDGING_WORDS = {
    "maybe",
    "perhaps",
    "possibly",
    "might",
    "could",
    "seem",
    "appear",
    "suggest",
    "think",
    "believe",
    "feel",
    "sort",
    "kind",
    "rather",
    "quite",
    "somewhat",
    "arguably",
    "apparently",
    "allegedly",
    "reportedly",
}

# Distancing language patterns
DISTANCING_PATTERNS = [
    r"\bone\s+would\b",
    r"\bpeople\s+say\b",
    r"\bit\s+is\s+said\b",
    r"\bone\s+can\b",
    r"\bthey\s+say\b",
    r"\bsources\s+indicate\b",
]

# Superlative words
SUPERLATIVES = {
    "best",
    "worst",
    "greatest",
    "most",
    "least",
    "amazing",
    "incredible",
    "unbelievable",
    "fantastic",
    "terrible",
    "excellent",
    "perfect",
    "horrible",
    "brilliant",
    "awful",
    "outstanding",
    "exceptional",
    "phenomenal",
    "astonishing",
    "devastating",
}

# Certainty markers (high confidence words)
CERTAINTY_MARKERS = {
    "definitely",
    "certainly",
    "absolutely",
    "undoubtedly",
    "clearly",
    "obviously",
    "undeniably",
    "invariably",
    "always",
    "never",
    "must",
    "will",
    "fact",
    "truth",
    "proven",
}

# First person pronouns
FIRST_PERSON_PRONOUNS = {"i", "me", "my", "mine", "myself"}


def _tokenize_words(text: str) -> list[str]:
    """Split text into words using basic regex."""
    words = re.findall(r"\b\w+\b", text.lower())
    return words


def _tokenize_sentences(text: str) -> list[str]:
    """Split text into sentences using basic regex."""
    sentences = re.split(r"[.!?]+", text)
    return [s.strip() for s in sentences if s.strip()]


def _count_pattern_matches(text: str, patterns: list[str]) -> int:
    """Count total matches across multiple regex patterns."""
    count = 0
    text_lower = text.lower()
    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        count += len(matches)
    return count


def _extract_deception_indicators(text: str) -> dict[str, Any]:
    """Extract linguistic deception indicators from text."""
    if not text or len(text) < 100:
        return {
            "hedging_count": 0,
            "hedging_ratio": 0.0,
            "distancing_count": 0,
            "superlative_count": 0,
            "first_person_ratio": 0.0,
            "avg_sentence_length": 0.0,
            "certainty_marker_count": 0,
        }

    words = _tokenize_words(text)
    sentences = _tokenize_sentences(text)

    if not words:
        return {
            "hedging_count": 0,
            "hedging_ratio": 0.0,
            "distancing_count": 0,
            "superlative_count": 0,
            "first_person_ratio": 0.0,
            "avg_sentence_length": 0.0,
            "certainty_marker_count": 0,
        }

    word_count = len(words)
    sentence_count = len(sentences) if sentences else 1

    # Count hedging words
    hedging_count = sum(1 for w in words if w in HEDGING_WORDS)
    hedging_ratio = hedging_count / word_count if word_count > 0 else 0.0

    # Count distancing language
    distancing_count = _count_pattern_matches(text, DISTANCING_PATTERNS)

    # Count superlatives
    superlative_count = sum(1 for w in words if w in SUPERLATIVES)

    # Count first person pronouns
    first_person_count = sum(1 for w in words if w in FIRST_PERSON_PRONOUNS)
    first_person_ratio = first_person_count / word_count if word_count > 0 else 0.0

    # Average sentence length
    avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0.0

    # Count certainty markers
    certainty_marker_count = sum(1 for w in words if w in CERTAINTY_MARKERS)

    return {
        "hedging_count": hedging_count,
        "hedging_ratio": round(hedging_ratio, 4),
        "distancing_count": distancing_count,
        "superlative_count": superlative_count,
        "first_person_ratio": round(first_person_ratio, 4),
        "avg_sentence_length": round(avg_sentence_length, 2),
        "certainty_marker_count": certainty_marker_count,
    }


def _identify_red_flags(indicators: dict[str, Any]) -> list[str]:
    """Identify specific red flags based on indicators."""
    red_flags: list[str] = []

    # High hedging with high certainty = suspicious
    if indicators["hedging_ratio"] > 0.05 and indicators["certainty_marker_count"] > 5:
        red_flags.append("high_hedging_with_certainty_markers")

    # High superlative usage
    if indicators["superlative_count"] > 10:
        red_flags.append("excessive_superlatives")

    # Low first person pronouns (deceptive speakers often avoid personal responsibility)
    if indicators["first_person_ratio"] < 0.01 and indicators.get("avg_sentence_length", 0) > 10:
        red_flags.append("avoidance_of_personal_pronouns")

    # High distancing language
    if indicators["distancing_count"] > 3:
        red_flags.append("excessive_distancing_language")

    # Very short sentences (often used to hide complexity)
    if indicators.get("avg_sentence_length", 20) < 8:
        red_flags.append("unusually_short_sentences")

    # High hedging ratio
    if indicators["hedging_ratio"] > 0.08:
        red_flags.append("excessive_hedging_language")

    return red_flags


def _calculate_deception_score(indicators: dict[str, Any], red_flags: list[str]) -> float:
    """Calculate deception likelihood score (0.0-1.0)."""
    score = 0.0

    # Hedging ratio contribution (0.0-0.3)
    hedging_contrib = min(indicators["hedging_ratio"] * 3, 0.3)
    score += hedging_contrib

    # Superlative overuse (0.0-0.2)
    superlative_contrib = min(indicators["superlative_count"] / 30, 0.2)
    score += superlative_contrib

    # First person avoidance (0.0-0.25)
    if indicators["first_person_ratio"] < 0.01:
        first_person_contrib = 0.25
    else:
        first_person_contrib = max(0.0, (1.0 - indicators["first_person_ratio"] * 100) * 0.0025)
    score += min(first_person_contrib, 0.25)

    # Distancing language (0.0-0.15)
    distancing_contrib = min(indicators["distancing_count"] / 20, 0.15)
    score += distancing_contrib

    # Red flags bonus (0.0-0.1)
    red_flag_contrib = min(len(red_flags) * 0.05, 0.1)
    score += red_flag_contrib

    return min(score, 1.0)


async def _try_llm_assessment(text: str) -> str | None:
    """Attempt to get LLM-based deception assessment if available."""
    try:
        from loom.tools.llm.llm import research_llm_classify

        result = await research_llm_classify(
            text=text,
            categories=["truthful", "deceptive", "uncertain"],
        )

        if isinstance(result, dict) and "classification" in result:
            classification = result["classification"]
            explanation = result.get("explanation", "")
            return f"LLM classification: {classification}. {explanation}"

    except ImportError:
        logger.debug("LLM tools not available, skipping LLM assessment")
    except Exception as e:
        logger.debug("LLM assessment failed: %s", e)

    return None


@handle_tool_errors("research_deception_detect")
async def research_deception_detect(text: str) -> dict[str, Any]:
    """Detect deceptive or fraudulent content using linguistic cues.

    Analyzes text for deception indicators including hedging language,
    distancing patterns, superlative overuse, and other linguistic markers.
    Optionally enhances analysis with LLM classification if available.

    Args:
        text: Text to analyze for deception (minimum 100 characters)

    Returns:
        Dict with deception score, verdict, indicators, red flags, and optional LLM assessment
    """
    try:
        if not text or len(text) < 100:
            logger.warning("deception_detect: text too short (min 100 chars)")
            return {
                "error": "Text must be at least 100 characters",
                "deception_score": 0.0,
                "verdict": "insufficient_data",
                "word_count": len(_tokenize_words(text)) if text else 0,
            }

        # Extract indicators
        indicators = _extract_deception_indicators(text)
        words = _tokenize_words(text)

        # Identify red flags
        red_flags = _identify_red_flags(indicators)

        # Calculate deception score
        deception_score = _calculate_deception_score(indicators, red_flags)

        # Determine verdict
        if deception_score < 0.3:
            verdict = "likely_truthful"
        elif deception_score < 0.7:
            verdict = "uncertain"
        else:
            verdict = "likely_deceptive"

        # Try to get LLM assessment
        llm_assessment = await _try_llm_assessment(text)

        result: dict[str, Any] = {
            "deception_score": round(deception_score, 3),
            "verdict": verdict,
            "indicators": indicators,
            "red_flags": red_flags,
            "word_count": len(words),
        }

        if llm_assessment:
            result["llm_assessment"] = llm_assessment

        return result
    except Exception as exc:
        return {"error": str(exc), "tool": "research_deception_detect"}


def tool_deception_detect(text: str) -> list[TextContent]:
    """MCP wrapper for research_deception_detect."""
    result_dict = {
        "error": "deception_detect requires async context. Use research_deception_detect directly."
    }
    return [TextContent(type="text", text=json.dumps(result_dict, indent=2))]
