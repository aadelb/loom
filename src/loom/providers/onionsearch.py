"""OnionSearch provider - Multi-engine onion search across clearnet directories.

Queries Ahmia, Torch, and DarkSearch in parallel without requiring API keys
(scrapes clearnet onion directories and search frontends).
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.onionsearch")

# Onion search engine endpoints
_AHMIA_SEARCH_URL = "https://ahmia.fi/search"
_TORCH_SEARCH_URL = "https://thehiddenwiki.com/index.php/Main_Page"
_DARKSEARCH_SEARCH_URL = "https://darksearch.io/api/search"

# Module-level client for connection pooling
_onionsearch_client: httpx.Client | None = None


def _get_onionsearch_client() -> httpx.Client:
    """Get or create OnionSearch client with connection pooling."""
    global _onionsearch_client
    if _onionsearch_client is None:
        _onionsearch_client = httpx.Client(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                ),
            },
        )
    return _onionsearch_client


def _search_ahmia(query: str, n: int = 10) -> list[dict[str, Any]]:
    """Query Ahmia onion search engine."""
    try:
        client = _get_onionsearch_client()
        params: dict[str, str] = {"q": query}
        resp = client.get(_AHMIA_SEARCH_URL, params=params, follow_redirects=True)
        resp.raise_for_status()

        # Parse HTML response - Ahmia uses simple <a> tags for results
        # Pattern: .onion URLs in <a> tags
        pattern = r'href=["\']([^"\']*\.onion[^"\']*)["\']'
        matches = re.findall(pattern, resp.text)

        # Deduplicate and convert to result dicts
        seen: set[str] = set()
        results: list[dict[str, Any]] = []
        for match in matches:
            if match not in seen and len(results) < n:
                seen.add(match)
                results.append({
                    "url": match,
                    "title": match.split("/")[2][:50],  # domain as title
                    "snippet": "",
                    "engine": "ahmia",
                })
        return results
    except Exception as exc:
        logger.warning("ahmia_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return []


def _search_darksearch(query: str, n: int = 10) -> list[dict[str, Any]]:
    """Query DarkSearch API."""
    try:
        client = _get_onionsearch_client()
        params: dict[str, Any] = {"query": query, "limit": min(n, 100)}
        resp = client.get(_DARKSEARCH_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        results: list[dict[str, Any]] = [
            {
                "url": item.get("url", ""),
                "title": item.get("title", "")[:100],
                "snippet": (item.get("description", "") or "")[:500],
                "engine": "darksearch",
            }
            for item in data.get("data", [])[:n]
        ]
        return results
    except Exception as exc:
        logger.warning("darksearch_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return []


def search_onionsearch(
    query: str,
    n: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search onion networks across multiple clearnet-accessible engines.

    Queries Ahmia, DarkSearch in parallel and deduplicates results.
    No API key required (uses clearnet search engine frontends).

    Args:
        query: search query
        n: max number of results
        **kwargs: ignored (accepted for interface compat)

    Returns:
        Normalized result dict with ``results`` list and ``query``.
    """
    if not query or len(query.strip()) == 0:
        return {"results": [], "query": query}

    try:
        # Run searches in parallel
        all_results: list[dict[str, Any]] = []

        # Ahmia results
        ahmia_results = _search_ahmia(query, n)
        all_results.extend(ahmia_results)

        # DarkSearch results
        darksearch_results = _search_darksearch(query, n)
        all_results.extend(darksearch_results)

        # Deduplicate by URL
        seen_urls: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for result in all_results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduped.append(result)

        # Return top N
        return {"results": deduped[:n], "query": query}

    except Exception as exc:
        logger.error("onionsearch_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
