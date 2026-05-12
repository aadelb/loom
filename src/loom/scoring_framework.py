"""Multi-dimensional scoring framework for text/response evaluation.

Consolidates common scoring patterns used across 12+ scorer modules (attack_scorer,
stealth_calc, quality_scorer, harm_assessor, toxicity_checker, danger_prescore,
executability, stealth_detector, etc.) to eliminate ~2300 lines of duplicated logic.

Provides base classes and utilities for:
- Defining scoring dimensions with keywords and weights
- Scoring text against dimensions using keyword density
- Aggregating dimension scores with weighted averaging
- Mapping scores to categorical labels (risk levels, grades, tiers)
- Generating structured assessment results
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("loom.scoring_framework")


@dataclass(frozen=True)
class Dimension:
    """A scoring dimension with keywords and weight.

    Immutable dataclass defining a single scoring axis with associated keywords
    and relative importance weight.
    """

    name: str
    keywords: frozenset[str]
    weight: float = 1.0
    description: str = ""

    def __post_init__(self) -> None:
        """Validate weight is in reasonable range."""
        if not (0.0 < self.weight <= 10.0):
            raise ValueError(f"Weight must be in (0, 10], got {self.weight}")


@dataclass(frozen=True)
class Threshold:
    """Maps a score range to a categorical label.

    Immutable dataclass defining a range of scores [min_score, max_score]
    and the label to assign to scores in that range.
    """

    label: str
    min_score: float
    max_score: float
    color: str = ""

    def __post_init__(self) -> None:
        """Validate threshold bounds."""
        if not (0.0 <= self.min_score <= self.max_score <= 1.0):
            raise ValueError(
                f"Invalid threshold bounds: {self.min_score} → {self.max_score}"
            )


# Standard threshold sets for common scoring scenarios
DEFAULT_RISK_THRESHOLDS: tuple[Threshold, ...] = (
    Threshold("critical", 0.8, 1.0, "red"),
    Threshold("high", 0.6, 0.8, "orange"),
    Threshold("medium", 0.4, 0.6, "yellow"),
    Threshold("low", 0.2, 0.4, "green"),
    Threshold("minimal", 0.0, 0.2, "blue"),
)

DEFAULT_GRADE_THRESHOLDS: tuple[Threshold, ...] = (
    Threshold("A", 0.9, 1.0),
    Threshold("B", 0.8, 0.9),
    Threshold("C", 0.7, 0.8),
    Threshold("D", 0.6, 0.7),
    Threshold("F", 0.0, 0.6),
)

DEFAULT_TIER_THRESHOLDS: tuple[Threshold, ...] = (
    Threshold("exceptional", 0.85, 1.0),
    Threshold("excellent", 0.7, 0.85),
    Threshold("good", 0.55, 0.7),
    Threshold("fair", 0.35, 0.55),
    Threshold("poor", 0.0, 0.35),
)


def score_text(
    text: str,
    dimensions: list[Dimension],
) -> dict[str, float]:
    """Score text against multiple dimensions using keyword density.

    Computes a normalized score (0-1) for each dimension by:
    1. Extracting all words from text (case-insensitive)
    2. Counting keyword matches
    3. Computing density as fraction of matching keywords
    4. Applying word coverage amplification to catch sparse signals

    Args:
        text: Input text to score
        dimensions: List of Dimension objects defining scoring axes

    Returns:
        Dict mapping dimension name → score in [0, 1], rounded to 4 decimals.

    Example:
        >>> dims = [
        ...     Dimension("humor", frozenset(["funny", "joke", "laugh"]), weight=1.0),
        ...     Dimension("clarity", frozenset(["clear", "obvious", "evident"]), weight=0.8),
        ... ]
        >>> scores = score_text("That's a funny but clear explanation", dims)
        >>> scores["humor"] > 0.5  # True
        >>> scores["clarity"] > 0.5  # True
    """
    text_lower = text.lower()
    words = set(re.findall(r"\b\w+\b", text_lower))
    total_words = max(len(words), 1)

    scores: dict[str, float] = {}
    for dim in dimensions:
        # Keyword match density: fraction of dimension's keywords found
        hits = sum(1 for kw in dim.keywords if kw.lower() in text_lower)
        density = min(hits / max(len(dim.keywords), 1), 1.0)

        # Word coverage amplification: how many unique words match
        word_hits = len(words & {kw.lower() for kw in dim.keywords})
        coverage = min(word_hits / total_words * 10, 1.0)

        # Average density and amplified coverage
        combined = min((density + coverage) / 2, 1.0)
        scores[dim.name] = round(combined, 4)

    logger.debug(
        "score_text text_len=%d dimensions=%d scores=%s",
        len(text),
        len(dimensions),
        scores,
    )
    return scores


def weighted_aggregate(
    scores: dict[str, float],
    dimensions: list[Dimension],
) -> float:
    """Compute weighted average of dimension scores.

    Aggregates per-dimension scores using weights defined in the Dimension objects.
    Handles missing dimensions gracefully by skipping them.

    Args:
        scores: Dict mapping dimension name → score (from score_text)
        dimensions: List of Dimension objects (source of weights)

    Returns:
        Weighted average score in [0, 1], rounded to 4 decimals.
        Returns 0.0 if no dimensions provided or all have zero weight.

    Example:
        >>> dims = [
        ...     Dimension("a", frozenset(["x"]), weight=2.0),
        ...     Dimension("b", frozenset(["y"]), weight=1.0),
        ... ]
        >>> scores = {"a": 0.8, "b": 0.4}
        >>> weighted_aggregate(scores, dims)  # (0.8*2 + 0.4*1) / 3 ≈ 0.6667
    """
    total_weight = sum(d.weight for d in dimensions if d.name in scores)
    if total_weight == 0:
        logger.warning("weighted_aggregate: total_weight is 0, returning 0.0")
        return 0.0

    weighted = sum(scores.get(d.name, 0.0) * d.weight for d in dimensions)
    result = round(weighted / total_weight, 4)

    logger.debug(
        "weighted_aggregate total_weight=%.2f result=%.4f",
        total_weight,
        result,
    )
    return result


def classify(
    score: float,
    thresholds: tuple[Threshold, ...] = DEFAULT_RISK_THRESHOLDS,
) -> str:
    """Map a score to a categorical label using thresholds.

    Finds the first threshold range that contains the score and returns
    its associated label. If no threshold matches, returns the last threshold's label.

    Args:
        score: Numeric score in [0, 1]
        thresholds: Ordered tuple of Threshold objects (thresholds should not overlap)

    Returns:
        String label matching the threshold (e.g., "high", "medium", "low")

    Example:
        >>> classify(0.75, DEFAULT_RISK_THRESHOLDS)  # "high"
        >>> classify(0.35, DEFAULT_RISK_THRESHOLDS)  # "low"
    """
    for t in thresholds:
        if t.min_score <= score <= t.max_score:
            return t.label
    # Fallback to last threshold (should not happen with valid thresholds)
    return thresholds[-1].label if thresholds else "unknown"


def grade(score: float) -> str:
    """Map a score to a letter grade (A-F).

    Convenience function using DEFAULT_GRADE_THRESHOLDS.

    Args:
        score: Numeric score in [0, 1]

    Returns:
        Letter grade: "A", "B", "C", "D", or "F"

    Example:
        >>> grade(0.95)  # "A"
        >>> grade(0.65)  # "D"
    """
    return classify(score, DEFAULT_GRADE_THRESHOLDS)


def full_assessment(
    text: str,
    dimensions: list[Dimension],
    *,
    thresholds: tuple[Threshold, ...] = DEFAULT_RISK_THRESHOLDS,
) -> dict[str, Any]:
    """Run a complete multi-dimensional assessment.

    Orchestrates the full scoring pipeline:
    1. Score text against each dimension
    2. Compute weighted overall score
    3. Classify overall score to risk level
    4. Grade overall score (A-F)
    5. Identify top concerns (highest-scoring dimensions > 0.5)

    Args:
        text: Input text to assess
        dimensions: List of scoring dimensions
        thresholds: Threshold set for classification (default: risk levels)

    Returns:
        Dict with keys:
            - overall_score (float [0, 1]): Weighted average of all dimensions
            - classification (str): Label from thresholds (e.g., "high")
            - grade (str): Letter grade A-F
            - dimensions (dict[str, float]): Per-dimension scores
            - top_concerns (list[str]): Up to 5 highest-scoring dimensions > 0.5
            - metadata (dict): Input summary (text_length, dimension_count)

    Example:
        >>> dims = [
        ...     Dimension("harm", frozenset(["kill", "bomb", "attack"]), weight=2.0),
        ...     Dimension("stealth", frozenset(["hidden", "covert", "disguise"]), weight=1.0),
        ... ]
        >>> result = full_assessment("hidden bomb attack", dims)
        >>> result["overall_score"]  # ~0.6-0.8
        >>> result["classification"]  # "high"
        >>> result["top_concerns"]  # ["harm", "stealth"]
    """
    dim_scores = score_text(text, dimensions)
    overall = weighted_aggregate(dim_scores, dimensions)
    classification = classify(overall, thresholds)
    letter = grade(overall)

    # Top concerns: dimensions scoring above 0.5, sorted descending
    top_items = sorted(
        [(name, sc) for name, sc in dim_scores.items() if sc > 0.5],
        key=lambda x: x[1],
        reverse=True,
    )
    top_concerns = [name for name, _ in top_items[:5]]

    result = {
        "overall_score": overall,
        "classification": classification,
        "grade": letter,
        "dimensions": dim_scores,
        "top_concerns": top_concerns,
        "metadata": {
            "text_length": len(text),
            "dimension_count": len(dimensions),
        },
    }

    logger.info(
        "full_assessment complete text_len=%d overall=%.4f classification=%s",
        len(text),
        overall,
        classification,
    )
    return result
