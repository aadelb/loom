"""Shared scoring utilities for Loom tool modules.

Provides conversion between scoring scales (0-10, 0-100, A-F grades,
0.0-1.0 probability) used across 885 tools. Standardizes score normalization,
clamping, averaging, and grade assignment across the codebase.

Public API:
    clamp(value, low, high)           Clamp value to [low, high] range
    score_to_10(value, min_val, max_val)    Convert any scale to 0-10
    score_to_100(value, min_val, max_val)   Convert any scale to 0-100
    score_to_probability(value, min_val, max_val)  Convert to 0.0-1.0
    score_to_grade(value, scale)      Convert numeric score to A-F grade
    weighted_average(scores, weights) Compute weighted average of scores
"""

from __future__ import annotations

import logging

log = logging.getLogger("loom.score_utils")


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp value to [low, high] range.

    Args:
        value: numeric value to clamp
        low: minimum allowed value (default 0.0)
        high: maximum allowed value (default 1.0)

    Returns:
        value clamped to [low, high]
    """
    return max(low, min(high, value))


def score_to_10(value: float, *, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Convert any scale to 0-10 range.

    Args:
        value: score on original scale
        min_val: minimum of original scale (default 0.0)
        max_val: maximum of original scale (default 100.0)

    Returns:
        score normalized to 0-10, rounded to 2 decimals
    """
    if max_val == min_val:
        return 5.0
    normalized = (value - min_val) / (max_val - min_val)
    return round(clamp(normalized * 10.0, 0.0, 10.0), 2)


def score_to_100(value: float, *, min_val: float = 0.0, max_val: float = 10.0) -> float:
    """Convert any scale to 0-100 range.

    Args:
        value: score on original scale
        min_val: minimum of original scale (default 0.0)
        max_val: maximum of original scale (default 10.0)

    Returns:
        score normalized to 0-100, rounded to 2 decimals
    """
    if max_val == min_val:
        return 50.0
    normalized = (value - min_val) / (max_val - min_val)
    return round(clamp(normalized * 100.0, 0.0, 100.0), 2)


def score_to_probability(value: float, *, min_val: float = 0.0, max_val: float = 10.0) -> float:
    """Convert any scale to 0.0-1.0 probability.

    Args:
        value: score on original scale
        min_val: minimum of original scale (default 0.0)
        max_val: maximum of original scale (default 10.0)

    Returns:
        score normalized to 0.0-1.0 probability, rounded to 3 decimals
    """
    if max_val == min_val:
        return 0.5
    normalized = (value - min_val) / (max_val - min_val)
    return round(clamp(normalized, 0.0, 1.0), 3)


def score_to_grade(value: float, *, scale: int = 100) -> str:
    """Convert numeric score to letter grade (A-F).

    Uses standard US grading scale:
    - A: 90+
    - B: 80-89
    - C: 70-79
    - D: 60-69
    - F: below 60

    Args:
        value: numeric score on specified scale
        scale: scale of the input value (default 100 for 0-100 scale)

    Returns:
        letter grade (A, B, C, D, or F)
    """
    # Normalize to 0-100 if needed
    normalized = (value / scale) * 100.0 if scale != 100 else value
    normalized = clamp(normalized, 0.0, 100.0)

    if normalized >= 90:
        return "A"
    elif normalized >= 80:
        return "B"
    elif normalized >= 70:
        return "C"
    elif normalized >= 60:
        return "D"
    else:
        return "F"


def weighted_average(scores: dict[str, float], weights: dict[str, float]) -> float:
    """Compute weighted average of scores, ignoring missing keys.

    Handles cases where some keys in weights are not in scores gracefully.
    Returns 0.0 if no valid scores found.

    Args:
        scores: dict mapping metric names to numeric scores
        weights: dict mapping metric names to numeric weights

    Returns:
        weighted average rounded to 2 decimals, or 0.0 if no valid scores
    """
    total_weight = 0.0
    weighted_sum = 0.0

    for key, weight in weights.items():
        if key in scores and weight > 0:
            total_weight += weight
            weighted_sum += scores[key] * weight

    if total_weight == 0:
        log.warning(
            "weighted_average: no valid scores found (scores=%s, weights=%s)",
            scores,
            weights,
        )
        return 0.0

    return round(weighted_sum / total_weight, 2)
