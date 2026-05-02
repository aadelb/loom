"""research_detect_anomalies — Detect numerical and textual anomalies in research data.

Pure Python statistical analysis tools for identifying unusual patterns in
numerical data (z-score, IQR, isolation forest) and textual anomalies
(length, vocabulary, structure, encoding artifacts).
"""

from __future__ import annotations

import logging
import math
import random
from typing import Any

logger = logging.getLogger("loom.tools.anomaly_detector")


async def research_detect_anomalies(
    data: list[float],
    method: str = "zscore",
    threshold: float = 2.0,
) -> dict[str, Any]:
    """Detect anomalies in numerical data using statistical methods.

    Supports three detection methods:
    - zscore: flag points > threshold standard deviations from mean
    - iqr: flag points outside Q1-1.5*IQR to Q3+1.5*IQR
    - isolation: simplified isolation forest (random splits)

    Args:
        data: List of numerical values to analyze
        method: Detection method (zscore, iqr, isolation)
        threshold: Sensitivity threshold (zscore std devs or isolation depth)

    Returns:
        Dict with:
          - method: detection method used
          - threshold: threshold parameter applied
          - total_points: total values analyzed
          - anomalies: list of {index, value, score, reason}
          - anomaly_rate: fraction of points flagged as anomalies
          - statistics: {mean, std, min, max, q1, q3}
    """
    try:
        # Validate inputs
        if not data:
            return {
                "error": "data list cannot be empty",
                "method": method,
            }

        if len(data) > 100000:
            return {
                "error": "data list exceeds max 100000 items",
                "method": method,
            }

        if method not in ("zscore", "iqr", "isolation"):
            return {
                "error": f"method must be zscore, iqr, or isolation (got {method})",
                "method": method,
            }

        if threshold <= 0 or threshold > 10:
            return {
                "error": f"threshold must be 0 < threshold <= 10 (got {threshold})",
                "method": method,
            }

        # Convert to float and filter invalid values
        try:
            values = [float(x) for x in data if x is not None]
        except (ValueError, TypeError):
            return {
                "error": "all data values must be numeric",
                "method": method,
            }

        if not values:
            return {
                "error": "no valid numeric values in data",
                "method": method,
            }

        logger.info("detect_anomalies method=%s threshold=%.1f n=%d", method, threshold, len(values))

        # Compute statistics
        stats = _compute_stats(values)

        # Detect anomalies based on method
        if method == "zscore":
            anomalies = _detect_zscore(values, stats, threshold)
        elif method == "iqr":
            anomalies = _detect_iqr(values, stats)
        else:  # isolation
            anomalies = _detect_isolation(values, int(threshold))

        # Sort by score descending
        anomalies = sorted(anomalies, key=lambda a: a["score"], reverse=True)

        anomaly_rate = len(anomalies) / len(values) if values else 0

        return {
            "method": method,
            "threshold": threshold,
            "total_points": len(values),
            "anomalies": anomalies,
            "anomaly_rate": round(anomaly_rate, 4),
            "statistics": {
                "mean": round(stats["mean"], 4),
                "std": round(stats["std"], 4),
                "min": round(stats["min"], 4),
                "max": round(stats["max"], 4),
                "median": round(stats["median"], 4),
                "q1": round(stats["q1"], 4),
                "q3": round(stats["q3"], 4),
            },
        }

    except Exception as e:
        logger.exception("Unexpected error in detect_anomalies")
        return {
            "error": f"Execution failed: {type(e).__name__}: {str(e)[:200]}",
            "method": method,
        }


async def research_detect_text_anomalies(
    texts: list[str],
    baseline: str = "",
) -> dict[str, Any]:
    """Detect unusual text patterns compared to a baseline or corpus.

    Analyzes:
    - Unusual length (deviation from median)
    - Unusual vocabulary (rare words, high entropy)
    - Unusual structure (punctuation, whitespace patterns)
    - Encoding artifacts (non-UTF8 patterns, control chars)

    Args:
        texts: List of text strings to analyze
        baseline: Optional reference text for comparison

    Returns:
        Dict with:
          - total_texts: number of texts analyzed
          - anomalies: list of {index, text_preview, anomaly_types, score}
          - types_found: dict of anomaly_type -> count
          - statistics: {mean_length, max_length, vocab_size}
    """
    try:
        # Validate inputs
        if not texts:
            return {
                "error": "texts list cannot be empty",
                "total_texts": 0,
            }

        if len(texts) > 50000:
            return {
                "error": "texts list exceeds max 50000 items",
                "total_texts": 0,
            }

        # Convert to strings
        text_list = []
        for t in texts:
            if t is None:
                continue
            text_list.append(str(t))

        if not text_list:
            return {
                "error": "no valid text values",
                "total_texts": 0,
            }

        logger.info("detect_text_anomalies n=%d baseline_len=%d", len(text_list), len(baseline))

        # Compute baseline corpus statistics if not provided
        if baseline:
            baseline_stats = _analyze_text(baseline)
        else:
            # Use corpus statistics from all texts
            all_vocab = set()
            for text in text_list:
                all_vocab.update(_get_words(text))
            baseline_stats = {
                "vocab_size": len(all_vocab),
                "mean_length": sum(len(t) for t in text_list) / len(text_list),
            }

        # Detect anomalies in each text
        anomalies = []
        types_found = {}

        lengths = [len(t) for t in text_list]
        median_length = _median(lengths)

        for idx, text in enumerate(text_list):
            anomaly_types = []
            score = 0.0

            # Check length anomaly
            if median_length > 0:
                length_ratio = len(text) / median_length
                if length_ratio < 0.5 or length_ratio > 2.0:
                    anomaly_types.append("unusual_length")
                    score += 0.3 * min(abs(1.0 - length_ratio), 1.0)

            # Check vocabulary anomaly
            words = _get_words(text)
            if len(words) > 0 and baseline_stats["vocab_size"] > 0:
                vocab_coverage = len(set(words) & set(_get_words(" ".join(text_list)))) / baseline_stats["vocab_size"]
                if vocab_coverage < 0.3:
                    anomaly_types.append("unusual_vocabulary")
                    score += 0.3

            # Check structure anomaly
            punct_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / max(1, len(text))
            if punct_ratio > 0.4 or (len(text) > 50 and punct_ratio < 0.05):
                anomaly_types.append("unusual_structure")
                score += 0.2

            # Check encoding artifacts
            if _has_encoding_artifacts(text):
                anomaly_types.append("encoding_artifacts")
                score += 0.2

            if anomaly_types:
                anomalies.append({
                    "index": idx,
                    "text_preview": text[:100],
                    "anomaly_types": anomaly_types,
                    "score": round(score, 3),
                })
                for atype in anomaly_types:
                    types_found[atype] = types_found.get(atype, 0) + 1

        # Sort by score descending
        anomalies = sorted(anomalies, key=lambda a: a["score"], reverse=True)

        return {
            "total_texts": len(text_list),
            "anomalies": anomalies,
            "anomaly_count": len(anomalies),
            "types_found": types_found,
            "statistics": {
                "mean_length": round(sum(len(t) for t in text_list) / len(text_list), 2),
                "median_length": int(median_length),
                "max_length": max(len(t) for t in text_list),
                "vocab_size": len(set(w for t in text_list for w in _get_words(t))),
            },
        }

    except Exception as e:
        logger.exception("Unexpected error in detect_text_anomalies")
        return {
            "error": f"Execution failed: {type(e).__name__}: {str(e)[:200]}",
            "total_texts": len(texts),
        }


def _compute_stats(values: list[float]) -> dict[str, float]:
    """Compute mean, std, min, max, median, Q1, Q3."""
    if not values:
        return {
            "mean": 0,
            "std": 0,
            "min": 0,
            "max": 0,
            "median": 0,
            "q1": 0,
            "q3": 0,
        }

    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / max(1, n - 1)
    std = math.sqrt(variance) if variance > 0 else 0

    sorted_vals = sorted(values)
    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]
    median = _percentile(sorted_vals, 50)
    q1 = _percentile(sorted_vals, 25)
    q3 = _percentile(sorted_vals, 75)

    return {
        "mean": mean,
        "std": std,
        "min": min_val,
        "max": max_val,
        "median": median,
        "q1": q1,
        "q3": q3,
    }


def _detect_zscore(values: list[float], stats: dict[str, float], threshold: float) -> list[dict]:
    """Detect anomalies using z-score method."""
    anomalies = []
    mean = stats["mean"]
    std = stats["std"]

    if std == 0:
        return anomalies

    for idx, val in enumerate(values):
        zscore = abs((val - mean) / std)
        if zscore > threshold:
            anomalies.append({
                "index": idx,
                "value": round(val, 4),
                "score": round(zscore, 3),
                "reason": f"z-score {zscore:.2f} > threshold {threshold}",
            })

    return anomalies


def _detect_iqr(values: list[float], stats: dict[str, float]) -> list[dict]:
    """Detect anomalies using IQR method."""
    anomalies = []
    q1 = stats["q1"]
    q3 = stats["q3"]
    iqr = q3 - q1

    if iqr == 0:
        return anomalies

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    for idx, val in enumerate(values):
        if val < lower_bound or val > upper_bound:
            distance = min(abs(val - lower_bound), abs(val - upper_bound))
            score = distance / max(1, iqr) if iqr > 0 else 1.0
            anomalies.append({
                "index": idx,
                "value": round(val, 4),
                "score": round(score, 3),
                "reason": f"outside IQR bounds [{lower_bound:.2f}, {upper_bound:.2f}]",
            })

    return anomalies


def _detect_isolation(values: list[float], depth_threshold: int) -> list[dict]:
    """Simplified isolation forest: random split trees."""
    anomalies = []

    if len(values) < 3:
        return anomalies

    # Run multiple iterations of random splits
    anomaly_scores = [0.0] * len(values)
    n_trees = min(10, len(values) // 2)

    random.seed(42)  # Deterministic for reproducibility

    for _ in range(n_trees):
        # Random split on random axis
        split_val = random.choice(values)
        indices_left = [i for i, v in enumerate(values) if v <= split_val]
        indices_right = [i for i, v in enumerate(values) if v > split_val]

        # Increment anomaly score for indices that separate quickly
        if indices_left and indices_right:
            if len(indices_left) < len(values) // 10:
                for i in indices_left:
                    anomaly_scores[i] += 1
            if len(indices_right) < len(values) // 10:
                for i in indices_right:
                    anomaly_scores[i] += 1

    # Normalize scores and flag anomalies
    max_score = max(anomaly_scores) if anomaly_scores else 1
    threshold_score = max_score * (1 - 0.1 * min(depth_threshold, 10) / 10)

    for idx, val in enumerate(values):
        if anomaly_scores[idx] > threshold_score:
            anomalies.append({
                "index": idx,
                "value": round(val, 4),
                "score": round(anomaly_scores[idx] / max(1, max_score), 3),
                "reason": f"isolation score {anomaly_scores[idx]:.1f} > threshold",
            })

    return anomalies


def _percentile(sorted_vals: list[float], p: int) -> float:
    """Compute p-th percentile of sorted values."""
    if not sorted_vals:
        return 0.0
    if p <= 0:
        return sorted_vals[0]
    if p >= 100:
        return sorted_vals[-1]

    idx = (p / 100.0) * (len(sorted_vals) - 1)
    lower_idx = int(idx)
    upper_idx = min(lower_idx + 1, len(sorted_vals) - 1)
    fraction = idx - lower_idx

    return sorted_vals[lower_idx] * (1 - fraction) + sorted_vals[upper_idx] * fraction


def _median(values: list[float]) -> float:
    """Compute median of values."""
    return _percentile(sorted(values), 50)


def _get_words(text: str) -> list[str]:
    """Extract words from text (lowercase, alphanum only)."""
    words = []
    for word in text.split():
        clean = "".join(c.lower() for c in word if c.isalnum())
        if clean:
            words.append(clean)
    return words


def _analyze_text(text: str) -> dict[str, Any]:
    """Analyze a text for baseline statistics."""
    words = _get_words(text)
    vocab = set(words)
    return {
        "vocab_size": len(vocab),
        "word_count": len(words),
        "mean_length": len(text) / max(1, len(words)),
    }


def _has_encoding_artifacts(text: str) -> bool:
    """Check for encoding artifacts (control chars, invalid UTF-8 patterns)."""
    # Look for control characters (except common whitespace)
    for char in text:
        code = ord(char)
        if code < 32 and code not in (9, 10, 13):  # tab, newline, carriage return
            return True
        if code == 127:  # DEL
            return True

    # Check for suspicious UTF-8 patterns (replacement char)
    if "�" in text:
        return True

    return False
