"""Result aggregation utilities.

Gathers results from multiple sources, filters by quality,
deduplicates, and ranks. Used by multi_search, deep research,
and evidence pipeline tools.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("loom.result_aggregator")


def gather_results(
    results: list[dict[str, Any]],
    *,
    error_key: str = "error",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Separate successful results from errors.

    Returns (successes, errors) tuple.
    """
    successes: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for r in results:
        if error_key in r and r[error_key]:
            errors.append(r)
        else:
            successes.append(r)
    return successes, errors


def deduplicate_by(
    items: list[dict[str, Any]],
    key: str,
    *,
    case_insensitive: bool = True,
    normalize_url: bool = False,
) -> list[dict[str, Any]]:
    """Remove duplicates based on a dict key."""
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        value = str(item.get(key, ""))
        if case_insensitive:
            value = value.lower()
        if normalize_url:
            value = value.rstrip("/").split("?")[0]
        if value and value not in seen:
            seen.add(value)
            unique.append(item)
    return unique


def filter_by_score(
    items: list[dict[str, Any]],
    *,
    score_key: str = "score",
    min_score: float = 0.0,
) -> list[dict[str, Any]]:
    """Filter items by minimum score threshold."""
    return [
        item for item in items
        if float(item.get(score_key, 0.0) or 0.0) >= min_score
    ]


def rank_results(
    items: list[dict[str, Any]],
    *,
    score_key: str = "score",
    limit: int = 0,
    descending: bool = True,
) -> list[dict[str, Any]]:
    """Sort results by score and optionally limit."""
    sorted_items = sorted(
        items,
        key=lambda x: float(x.get(score_key, 0.0) or 0.0),
        reverse=descending,
    )
    if limit > 0:
        return sorted_items[:limit]
    return sorted_items


def merge_results(
    *result_lists: list[dict[str, Any]],
    dedup_key: str = "url",
    score_key: str = "score",
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Merge multiple result lists, deduplicate, and rank.

    Convenience function combining gather + dedup + rank.
    """
    combined: list[dict[str, Any]] = []
    for results in result_lists:
        combined.extend(results)
    deduped = deduplicate_by(combined, dedup_key, normalize_url=True)
    return rank_results(deduped, score_key=score_key, limit=limit)
