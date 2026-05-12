"""research_epistemic_score — Epistemic confidence scoring for text claims.

Scores truth probability for claims in text using heuristics:
- Presence of numbers/citations (increases confidence)
- Hedging language (decreases confidence)
- Specificity (names, dates increase confidence)
- Verifiability (can claim be fact-checked?)
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("loom.tools.epistemic_score")

# Constraints
MIN_TEXT_CHARS = 10
MAX_TEXT_CHARS = 50000
MAX_CLAIMS = 50

# Hedging/uncertainty language
HEDGING_WORDS = {
    "maybe", "possibly", "arguably", "supposedly", "allegedly",
    "reportedly", "seems", "appears", "might", "could", "may",
    "somewhat", "rather", "quite", "fairly", "relatively",
    "apparently", "likely", "probably", "roughly", "approximately",
    "purportedly", "claimed"
}

# Citation indicators
CITATION_PATTERNS = [
    r"\([A-Z][a-z]+\s+\d{4}\)",  # (Author 2024)
    r"\[\d+\]",  # [1], [2]
    r"according to",
    r"studies show",
    r"research indicates",
    r"evidence suggests",
    r"data shows",
    r"reported by",
]

# Number patterns (specificity)
NUMBER_PATTERNS = [
    r"\d+%",  # percentages
    r"\d+\.\d+",  # decimals
    r"\$\d+",  # currency
    r"\d+\s*(million|billion|thousand|year|day|hour|minute)",  # quantities
    r"\d{4}",  # years
    r"\d{1,2}/\d{1,2}/\d{2,4}",  # dates
]

# Named entity patterns
ENTITY_PATTERNS = [
    r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",  # Names (e.g. John Smith)
    r"\b(USA|EU|UK|UN|NASA|WHO|EPA|FBI)\b",  # Acronyms
]


def _extract_sentences(text: str) -> list[str]:
    """Extract sentences from text."""
    sentences = re.split(r"[.!?]+", text)
    return [s.strip() for s in sentences if s.strip()]


def _has_numbers(claim: str) -> int:
    """Check for numbers in claim (1 = yes, 0 = no)."""
    return 1 if re.search(r"|".join(NUMBER_PATTERNS), claim) else 0


def _has_citation(claim: str) -> int:
    """Check for citation indicators (1 = yes, 0 = no)."""
    return 1 if re.search(r"|".join(CITATION_PATTERNS), claim, re.IGNORECASE) else 0


def _hedging_count(claim: str) -> int:
    """Count hedging words in claim."""
    words = set(w.lower() for w in re.findall(r"\b\w+\b", claim))
    return len(words & HEDGING_WORDS)


def _specificity_score(claim: str) -> float:
    """Score specificity (0-1): named entities + numbers."""
    entities = len(re.findall(r"|".join(ENTITY_PATTERNS), claim))
    numbers = len(re.findall(r"|".join(NUMBER_PATTERNS), claim))
    claim_words = len(re.findall(r"\b\w+\b", claim))

    if claim_words == 0:
        return 0.0
    # Specificity ratio: specific markers per word (capped at 1.0)
    return min(1.0, (entities + numbers * 0.5) / claim_words)


def _is_factual_claim(claim: str) -> bool:
    """Determine if sentence is a factual claim vs. opinion/procedural."""
    opinion_markers = {"i think", "i believe", "in my opinion", "should", "must"}
    procedural_markers = {"please", "you can", "to do", "how to", "step"}

    claim_lower = claim.lower()
    if any(m in claim_lower for m in opinion_markers | procedural_markers):
        return False

    # Require some content words (verbs/nouns)
    words = re.findall(r"\b\w{3,}\b", claim_lower)
    return len(words) >= 3


def _compute_confidence(claim: str) -> float:
    """Compute confidence score (0-1) for a claim."""
    if not _is_factual_claim(claim):
        return 0.0

    score = 0.2  # baseline: unverified claims start at low confidence
    claim_words = len(re.findall(r"\b\w+\b", claim))

    if claim_words == 0:
        return 0.0

    # Numbers: +0.2
    score += _has_numbers(claim) * 0.2

    # Citations: +0.15
    score += _has_citation(claim) * 0.15

    # Specificity: +0.2
    score += _specificity_score(claim) * 0.2

    # Hedging: -0.05 per hedging word (max -0.2)
    score -= min(0.2, _hedging_count(claim) * 0.05)

    # Claim length penalty: very short claims less confident
    if claim_words < 5:
        score -= 0.1

    return max(0.0, min(1.0, score))


async def research_epistemic_score(
    text: str,
    claims_to_verify: list[str] | None = None,
) -> dict[str, Any]:
    """Score epistemic confidence for claims in text.

    Args:
        text: Input text to analyze (10-50,000 chars)
        claims_to_verify: List of specific claims to score. If not provided,
                         auto-extracts factual claims from text.

    Returns:
        Dict with:
        - overall_confidence: float (0-1)
        - claims: list of identified claims
        - per_claim_scores: [{"claim": str, "confidence": float, ...}]
        - high_confidence_claims: claims with score >= 0.7
        - low_confidence_claims: claims with score < 0.4
        - recommendations: list of suggestions for improving confidence
    """
    # Validate input
    if not text or len(text) < MIN_TEXT_CHARS:
        error_msg = f"text must be at least {MIN_TEXT_CHARS} characters"
        logger.warning("epistemic_score_invalid_input length=%d", len(text))
        return {
            "error": error_msg,
            "overall_confidence": 0.0,
            "claims": [],
            "per_claim_scores": [],
        }

    if len(text) > MAX_TEXT_CHARS:
        error_msg = f"text exceeds {MAX_TEXT_CHARS} character limit"
        logger.warning("epistemic_score_text_too_long length=%d", len(text))
        return {
            "error": error_msg,
            "overall_confidence": 0.0,
            "claims": [],
            "per_claim_scores": [],
        }

    try:
        # Extract or use provided claims
        if claims_to_verify is not None:
            claims = claims_to_verify[:MAX_CLAIMS]
        else:
            sentences = _extract_sentences(text)
            claims = [s for s in sentences if _is_factual_claim(s)][:MAX_CLAIMS]

        if not claims:
            logger.info("epistemic_score_no_claims text_len=%d", len(text))
            return {
                "overall_confidence": 0.0,
                "claims": [],
                "per_claim_scores": [],
                "high_confidence_claims": [],
                "low_confidence_claims": [],
                "recommendations": ["No factual claims found in text"],
                "text_length": len(text),
                "total_claims_analyzed": 0,
            }

        # Score each claim
        per_claim_scores = []
        for claim in claims:
            conf = _compute_confidence(claim)
            per_claim_scores.append({
                "claim": claim[:150],  # Truncate for output
                "confidence": round(conf, 3),
                "has_numbers": bool(_has_numbers(claim)),
                "has_citation": bool(_has_citation(claim)),
                "hedging_words": _hedging_count(claim),
                "specificity": round(_specificity_score(claim), 3),
            })

        # Compute overall confidence
        confidences = [s["confidence"] for s in per_claim_scores]
        overall = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

        # Categorize claims
        high_conf = [s for s in per_claim_scores if s["confidence"] >= 0.7]
        low_conf = [s for s in per_claim_scores if s["confidence"] < 0.4]

        # Generate recommendations
        recommendations = []
        low_confidence_pct = len(low_conf) / len(per_claim_scores) if per_claim_scores else 0
        if low_confidence_pct > 0.5:
            recommendations.append("Add citations and specific data to support claims")
        if not any(s["has_numbers"] for s in per_claim_scores):
            recommendations.append("Include quantitative data (numbers, percentages, dates)")
        if not any(s["has_citation"] for s in per_claim_scores):
            recommendations.append("Add references or citations (Author 2024, [1], etc.)")
        if sum(s["hedging_words"] for s in per_claim_scores) > len(per_claim_scores):
            recommendations.append("Reduce hedging language (maybe, possibly, apparently)")

        logger.info(
            "epistemic_score_completed claims=%d overall_confidence=%.2f",
            len(claims),
            overall,
        )

        return {
            "overall_confidence": overall,
            "claims": claims,
            "per_claim_scores": per_claim_scores,
            "high_confidence_claims": high_conf,
            "low_confidence_claims": low_conf,
            "recommendations": recommendations,
            "text_length": len(text),
            "total_claims_analyzed": len(per_claim_scores),
        }

    except Exception as e:
        error_msg = f"epistemic scoring failed: {e!s}"
        logger.error("epistemic_score_error: %s", e)
        return {
            "error": error_msg,
            "overall_confidence": 0.0,
            "claims": [],
            "per_claim_scores": [],
        }
