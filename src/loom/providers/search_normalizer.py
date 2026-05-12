"""Search result normalization.

Converts search results from 21 different providers into a uniform format.
Each provider returns slightly different structures — this module
ensures all results have consistent fields for downstream tools.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    """Normalized search result from any provider."""

    title: str = ""
    url: str = ""
    snippet: str = ""
    score: float = 0.0
    provider: str = ""
    published_date: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict, omitting empty fields."""
        d: dict[str, Any] = {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
        }
        if self.score:
            d["score"] = self.score
        if self.provider:
            d["provider"] = self.provider
        if self.published_date:
            d["published_date"] = self.published_date
        if self.metadata:
            d["metadata"] = self.metadata
        return d


def normalize_results(
    raw_results: list[dict[str, Any]],
    provider: str,
) -> list[SearchResult]:
    """Normalize raw results from any provider into SearchResult list.

    Args:
        raw_results: List of result dicts from provider API
        provider: Provider name (exa, tavily, brave, ddgs, etc.)

    Returns:
        List of normalized SearchResult objects.
    """
    normalized: list[SearchResult] = []
    for item in raw_results:
        normalized.append(_normalize_one(item, provider))
    return normalized


def _normalize_one(item: dict[str, Any], provider: str) -> SearchResult:
    """Normalize a single result dict based on provider format.

    Handles field name variations across providers:
    - title: "title", "name", "headline"
    - url: "url", "link", "href"
    - snippet: "snippet", "description", "text", "content"
    - score: "score", "relevance_score"
    - date: "published_date", "date", "publishedAt"
    """
    title = (
        item.get("title")
        or item.get("name")
        or item.get("headline")
        or ""
    )
    url = (
        item.get("url")
        or item.get("link")
        or item.get("href")
        or ""
    )
    snippet = (
        item.get("snippet")
        or item.get("description")
        or item.get("text")
        or (item.get("content", "")[:300] if item.get("content") else "")
        or ""
    )
    score = float(
        item.get("score") or item.get("relevance_score") or 0.0
    )
    published = (
        item.get("published_date")
        or item.get("date")
        or item.get("publishedAt")
        or ""
    )

    # Store non-standard fields in metadata
    standard_keys = {
        "title", "name", "headline",
        "url", "link", "href",
        "snippet", "description", "text", "content",
        "score", "relevance_score",
        "published_date", "date", "publishedAt"
    }
    metadata = {k: v for k, v in item.items() if k not in standard_keys}

    return SearchResult(
        title=str(title).strip(),
        url=str(url).strip(),
        snippet=str(snippet).strip(),
        score=score,
        provider=provider,
        published_date=str(published),
        metadata=metadata,
    )


def deduplicate(
    results: list[SearchResult],
    *,
    by: str = "url",
) -> list[SearchResult]:
    """Remove duplicate results by URL or title.

    Args:
        results: List of SearchResult objects
        by: Field to deduplicate by ("url" or "title")

    Returns:
        List with duplicates removed.
    """
    seen: set[str] = set()
    unique: list[SearchResult] = []
    for r in results:
        key = getattr(r, by, r.url).lower().rstrip("/")
        if key and key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def sort_by_score(
    results: list[SearchResult],
    *,
    descending: bool = True,
) -> list[SearchResult]:
    """Sort results by relevance score.

    Args:
        results: List of SearchResult objects
        descending: If True, highest scores first

    Returns:
        Sorted list.
    """
    return sorted(results, key=lambda r: r.score, reverse=descending)
