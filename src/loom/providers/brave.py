"""Brave Search provider (REST API via httpx, no Python SDK)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.brave")

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


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
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(_BRAVE_SEARCH_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        results = [
            {
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "snippet": (item.get("description", "") or "")[:500],
                "published_date": item.get("page_age"),
            }
            for item in data.get("web", {}).get("results", [])
        ]
        return {"results": results, "query": query}

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.warning("brave_search_http_error query=%s status=%d", query[:50], code)
        return {"results": [], "query": query, "error": f"HTTP {code}"}

    except Exception as exc:
        logger.exception("brave_search_failed query=%s", query[:50])
        return {"results": [], "query": query, "error": str(exc)}
