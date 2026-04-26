"""Wikipedia search provider for general knowledge queries."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.wikipedia_search")

_WIKI_API_URL = "https://en.wikipedia.org/w/api.php"

# Module-level client for connection pooling
_wiki_client: httpx.Client | None = None


def _get_wiki_client() -> httpx.Client:
    """Get or create Wikipedia client with connection pooling."""
    global _wiki_client
    if _wiki_client is None:
        _wiki_client = httpx.Client(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
        )
    return _wiki_client


def search_wikipedia(
    query: str,
    n: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search Wikipedia for articles matching a query.

    Args:
        query: search query
        n: max number of results
        **kwargs: ignored (accepted for interface compat)

    Returns:
        Normalized result dict with ``results`` list.
    """
    params: dict[str, Any] = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": min(n, 50),
    }

    try:
        client = _get_wiki_client()
        resp = client.get(_WIKI_API_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        results = [
            {
                "url": f"https://en.wikipedia.org/wiki/{result.get('title', '').replace(' ', '_')}",
                "title": result.get("title", ""),
                "snippet": (result.get("snippet", "") or "")[:500],
            }
            for result in data.get("query", {}).get("search", [])
        ]
        return {"results": results, "query": query}

    except Exception as exc:
        logger.error("wiki_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
