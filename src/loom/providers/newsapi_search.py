"""NewsAPI search provider for news articles (REST API via httpx)."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.newsapi_search")

_NEWSAPI_EVERYTHING_URL = "https://newsapi.org/v2/everything"


def search_newsapi(
    query: str,
    n: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search news articles using NewsAPI.

    Args:
        query: search query
        n: max number of results
        **kwargs: ignored (accepted for interface compat)

    Returns:
        Normalized result dict with ``results`` list and ``query``.
    """
    api_key = os.environ.get("NEWS_API_KEY", "")
    if not api_key:
        return {"results": [], "query": query, "error": "NEWS_API_KEY not set"}

    params: dict[str, Any] = {
        "q": query,
        "pageSize": min(n, 100),  # NewsAPI max is 100
        "sortBy": "relevancy",
        "language": "en",
    }

    headers = {
        "Accept": "application/json",
        "X-Api-Key": api_key,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(_NEWSAPI_EVERYTHING_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        results = [
            {
                "url": article.get("url", ""),
                "title": article.get("title", ""),
                "snippet": (article.get("description", "") or "")[:500],
                "published_date": article.get("publishedAt"),
            }
            for article in data.get("articles", [])
        ]
        return {"results": results, "query": query}

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.warning("newsapi_search_http_error query=%s status=%d", query[:50], code)
        return {"results": [], "query": query, "error": f"HTTP {code}"}

    except Exception as exc:
        # Don't log full exception to avoid leaking API keys (HIGH #4)
        logger.error("newsapi_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
