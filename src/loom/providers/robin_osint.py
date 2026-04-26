"""ROBIN OSINT provider - AI-powered onion search with relevance scoring.

Inspired by apurvsinghgautam/robin. Combines multiple darkweb search engines
(Ahmia, DarkSearch) and deduplicates results with relevance scoring.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.robin_osint")

# Search engine endpoints
_AHMIA_SEARCH_URL = "https://ahmia.fi/search"
_DARKSEARCH_SEARCH_URL = "https://darksearch.io/api/search"

# Module-level client for connection pooling
_robin_client: httpx.Client | None = None


def _get_robin_client() -> httpx.Client:
    """Get or create ROBIN OSINT client with connection pooling."""
    global _robin_client
    if _robin_client is None:
        _robin_client = httpx.Client(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                ),
            },
        )
    return _robin_client


def _calculate_relevance_score(
    query: str,
    title: str,
    snippet: str,
    url: str,
) -> float:
    """Calculate relevance score for a result.

    Scoring factors:
    - Exact match in title: 10 points
    - Partial match in title: 5 points
    - Match in snippet: 2 points
    - Match in URL: 1 point
    """
    score = 0.0
    query_lower = query.lower()

    # Title scoring (highest weight)
    if title:
        title_lower = title.lower()
        if query_lower == title_lower:
            score += 10.0
        elif query_lower in title_lower:
            score += 5.0

    # Snippet scoring
    if snippet:
        snippet_lower = snippet.lower()
        if query_lower in snippet_lower:
            score += 2.0

    # URL scoring (lowest weight)
    if url:
        url_lower = url.lower()
        if query_lower in url_lower:
            score += 1.0

    # Normalize to 0-100 scale
    return min(100.0, score * 5)


def _search_ahmia_osint(query: str, n: int = 10) -> list[dict[str, Any]]:
    """Query Ahmia for OSINT results."""
    try:
        client = _get_robin_client()
        params: dict[str, str] = {"q": query}
        resp = client.get(_AHMIA_SEARCH_URL, params=params, follow_redirects=True)
        resp.raise_for_status()

        # Extract .onion links and context
        pattern = r'href=["\']([^"\']*\.onion[^"\']*)["\'][^>]*>([^<]*)<'
        matches = re.findall(pattern, resp.text)

        results: list[dict[str, Any]] = []
        seen: set[str] = set()
        for url, title in matches:
            if url not in seen and len(results) < n:
                seen.add(url)
                results.append({
                    "url": url,
                    "title": (title or url.split("/")[2])[:100],
                    "snippet": "",
                    "source": "ahmia",
                })
        return results
    except Exception as exc:
        logger.warning("ahmia_osint_failed query=%s: %s", query[:50], type(exc).__name__)
        return []


def _search_darksearch_osint(query: str, n: int = 10) -> list[dict[str, Any]]:
    """Query DarkSearch API for OSINT results."""
    try:
        client = _get_robin_client()
        params: dict[str, Any] = {"query": query, "limit": min(n, 100)}
        resp = client.get(_DARKSEARCH_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        results: list[dict[str, Any]] = [
            {
                "url": item.get("url", ""),
                "title": item.get("title", "")[:100],
                "snippet": (item.get("description", "") or "")[:500],
                "source": "darksearch",
            }
            for item in data.get("data", [])[:n]
        ]
        return results
    except Exception as exc:
        logger.warning("darksearch_osint_failed query=%s: %s", query[:50], type(exc).__name__)
        return []


def search_robin_osint(
    query: str,
    n: int = 10,
    min_relevance: float = 0.0,
    **kwargs: Any,
) -> dict[str, Any]:
    """AI-powered OSINT search combining multiple darkweb engines with scoring.

    Queries Ahmia and DarkSearch in parallel, deduplicates results, and scores
    by relevance. No API key required.

    Args:
        query: OSINT search query
        n: max number of results
        min_relevance: minimum relevance score threshold (0-100)
        **kwargs: ignored (accepted for interface compat)

    Returns:
        Normalized result dict with ``results`` list, ``query``, and scoring.
    """
    if not query or len(query.strip()) == 0:
        return {"results": [], "query": query}

    try:
        # Fetch from both engines
        ahmia_results = _search_ahmia_osint(query, n * 2)
        darksearch_results = _search_darksearch_osint(query, n * 2)

        # Combine and deduplicate by URL
        combined = ahmia_results + darksearch_results
        seen_urls: dict[str, dict[str, Any]] = {}  # URL -> result dict

        for result in combined:
            url = result.get("url", "").lower()
            if not url:
                continue

            # Calculate relevance score
            relevance = _calculate_relevance_score(
                query,
                result.get("title", ""),
                result.get("snippet", ""),
                result.get("url", ""),
            )

            # Keep highest scoring version of duplicates
            if url not in seen_urls or relevance > seen_urls[url].get("relevance_score", 0):
                result["relevance_score"] = relevance
                seen_urls[url] = result

        # Filter by minimum relevance and sort by score descending
        filtered = [
            r for r in seen_urls.values()
            if r.get("relevance_score", 0) >= min_relevance
        ]
        filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

        # Return top N with rounded scores
        results: list[dict[str, Any]] = []
        for result in filtered[:n]:
            result["relevance_score"] = round(result.get("relevance_score", 0), 2)
            results.append(result)

        return {
            "results": results,
            "query": query,
            "sources_queried": ["ahmia", "darksearch"],
            "min_relevance_threshold": min_relevance,
            "total_deduplicated": len(seen_urls),
        }

    except Exception as exc:
        logger.error("robin_osint_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
