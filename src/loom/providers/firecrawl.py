"""Firecrawl web intelligence search provider."""

from __future__ import annotations

import logging
import os
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger("loom.providers.firecrawl")


def search_firecrawl(
    query: str,
    n: int = 10,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search the web using Firecrawl.

    Date-range filtering is not supported by Firecrawl. Domain filtering
    is applied client-side after results are returned.

    Args:
        query: search query
        n: max number of results
        include_domains: restrict to these domains (client-side filter)
        exclude_domains: exclude these domains (client-side filter)
        **kwargs: passed through to Firecrawl SDK

    Returns:
        Normalized result dict with ``results`` list and ``query``.
    """
    api_key = os.environ.get("FIRECRAWL_API_KEY", "")
    if not api_key:
        return {"results": [], "query": query, "error": "FIRECRAWL_API_KEY not set"}

    try:
        from firecrawl import FirecrawlApp  # type: ignore[import-untyped]
    except ImportError:
        return {"results": [], "query": query, "error": "firecrawl-py not installed"}

    try:
        app = FirecrawlApp(api_key=api_key)
        response = app.search(query, limit=n)

        if isinstance(response, list):
            raw: list[Any] = response
        elif hasattr(response, "web") and isinstance(response.web, list):
            raw = response.web
        elif hasattr(response, "data") and isinstance(response.data, list):
            raw = response.data
        elif isinstance(response, dict):
            raw = response.get("data", [])
        else:
            raw = []

        results: list[dict[str, Any]] = []
        for r in raw:
            if isinstance(r, dict):
                url = r.get("url", "")
                title = r.get("title", "")
                snippet = (r.get("description", "") or "")[:500]
                score = r.get("score")
            else:
                url = getattr(r, "url", "")
                title = getattr(r, "title", "")
                snippet = (getattr(r, "description", "") or "")[:500]
                score = getattr(r, "score", None)

            if not url:
                continue

            if include_domains or exclude_domains:
                domain = urlparse(url).netloc.lower()
                if include_domains and not any(d in domain for d in include_domains):
                    continue
                if exclude_domains and any(d in domain for d in exclude_domains):
                    continue

            results.append(
                {
                    "url": url,
                    "title": title,
                    "snippet": snippet,
                    "score": score,
                }
            )

        return {"results": results, "query": query}

    except Exception as exc:
        # Don't log full exception to avoid leaking API keys (HIGH #4)
        logger.error("firecrawl_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
