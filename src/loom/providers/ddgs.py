"""DuckDuckGo search provider (free, no API key)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("loom.providers.ddgs")


def search_ddgs(
    query: str,
    n: int = 10,
    region: str = "wt-wt",
    time_range: str | None = None,
    search_type: str = "text",
    **kwargs: Any,
) -> dict[str, Any]:
    """Search the web using DuckDuckGo (free, no API key).

    Args:
        query: search query
        n: max number of results
        region: DuckDuckGo region code (wt-wt = worldwide)
        time_range: recency filter (d=day, w=week, m=month, y=year)
        search_type: "text" for web, "news" for news results
        **kwargs: passed through to DDGS

    Returns:
        Normalized result dict with ``results`` list and ``query``.
    """
    try:
        from ddgs import DDGS  # type: ignore[import-untyped]
    except ImportError:
        return {"results": [], "query": query, "error": "ddgs not installed (pip install ddgs)"}

    try:
        ddgs = DDGS()
        search_kwargs: dict[str, Any] = {
            "keywords": query,
            "max_results": min(n, 30),
            "region": region,
        }
        if time_range:
            search_kwargs["timelimit"] = time_range

        if search_type == "news":
            raw = list(ddgs.news(**search_kwargs))
            results = [
                {
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "snippet": (r.get("body", "") or "")[:500],
                    "published_date": r.get("date"),
                    "source": r.get("source"),
                }
                for r in raw
            ]
        else:
            raw = list(ddgs.text(**search_kwargs))
            results = [
                {
                    "url": r.get("href", ""),
                    "title": r.get("title", ""),
                    "snippet": (r.get("body", "") or "")[:500],
                }
                for r in raw
            ]

        return {"results": results, "query": query}

    except Exception as exc:
        logger.exception("ddgs_search_failed query=%s", query[:50])
        return {"results": [], "query": query, "error": str(exc)}
