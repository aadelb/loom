"""Brave Search provider (REST API via httpx, no Python SDK)."""

from __future__ import annotations

import logging
import os
from typing import Any

import atexit
import threading

import httpx

logger = logging.getLogger("loom.providers.brave")

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

_brave_client: httpx.Client | None = None
_brave_lock = threading.Lock()


def _get_brave_client() -> httpx.Client:
    """Get or create Brave Search client with connection pooling."""
    global _brave_client
    if _brave_client is None:
        with _brave_lock:
            if _brave_client is None:
                _brave_client = httpx.Client(
                    timeout=30.0,
                    limits=httpx.Limits(max_keepalive_connections=10, max_connections=50),
                )
    return _brave_client


def _close_brave_client() -> None:
    global _brave_client
    if _brave_client is not None:
        _brave_client.close()
        _brave_client = None


atexit.register(_close_brave_client)


def search_brave(
    query: str,
    n: int = 10,
    country: str | None = None,
    freshness: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search the web using Brave Search REST API.

    Brave's free tier supports up to 20 results per request and does not
    support server-side domain filtering.

    Args:
        query: search query
        n: max number of results (capped at 20 for free tier)
        country: two-letter country code
        freshness: recency filter (e.g. ``pd`` = past day, ``pw`` = past week)
        **kwargs: ignored (accepted for interface compat)

    Returns:
        Normalized result dict with ``results`` list and ``query``.
    """
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        return {"results": [], "query": query, "error": "BRAVE_API_KEY not set"}

    params: dict[str, Any] = {"q": query, "count": min(n, 20)}
    if country:
        params["country"] = country
    if freshness:
        params["freshness"] = freshness

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
    }

    try:
        client = _get_brave_client()
        resp = client.get(_BRAVE_SEARCH_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        raw_results = data.get("web", {}).get("results", [])
        total = max(len(raw_results), 1)
        results = [
            {
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "snippet": (item.get("description", "") or "")[:500],
                "published_date": item.get("page_age"),
                "score": 1.0 - (idx / total),
            }
            for idx, item in enumerate(raw_results)
        ]
        return {"results": results, "query": query}

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.warning("brave_search_http_error query=%s status=%d", query[:50], code)
        return {"results": [], "query": query, "error": f"HTTP {code}"}

    except Exception as exc:
        # Don't log full exception to avoid leaking API keys (HIGH #4)
        logger.error("brave_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
