"""DarkSearch.io search provider — Darkweb search API.

DarkSearch is a free darkweb search engine with a simple REST API.
No API key required for basic search.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.darksearch_search")

_DARKSEARCH_API_URL = "https://darksearch.io/api/search"

# Module-level client for connection pooling
_darksearch_client: httpx.Client | None = None


def _get_darksearch_client() -> httpx.Client:
    """Get or create DarkSearch API client with connection pooling."""
    global _darksearch_client
    if _darksearch_client is None:
        _darksearch_client = httpx.Client(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=20),
        )
    return _darksearch_client


def search_darksearch(
    query: str,
    n: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search the darkweb using DarkSearch.io API.

    DarkSearch is a free darkweb search engine with no API key requirement.
    Results are .onion sites indexed by the service.

    Args:
        query: search query
        n: max number of results (API returns up to n results)
        **kwargs: ignored (accepted for interface compatibility)

    Returns:
        Normalized result dict with ``results`` list and ``query``.
        Each result has: url, title, snippet.
    """
    params = {
        "query": query,
        "page": 1,
    }

    try:
        client = _get_darksearch_client()
        resp = client.get(_DARKSEARCH_API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        # DarkSearch API returns {"data": [...]} structure
        api_results = data.get("data", [])
        results = [
            {
                "url": item.get("link", ""),
                "title": item.get("title", "")[:200],
                "snippet": (item.get("description", "") or "")[:500],
            }
            for item in api_results[:n]
            if item.get("link")  # Only include results with valid URLs
        ]

        return {"results": results, "query": query}

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        # Rate limit errors should be handled gracefully
        if code == 429:
            logger.warning("darksearch_rate_limited query=%s", query[:50])
            return {"results": [], "query": query, "error": "rate_limited"}
        else:
            logger.warning("darksearch_http_error query=%s status=%d", query[:50], code)
            return {"results": [], "query": query, "error": f"HTTP {code}"}

    except Exception as exc:
        # Don't log full exception or details to avoid leaking sensitive information
        logger.error("darksearch_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
