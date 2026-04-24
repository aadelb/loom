"""Tavily agent-native search provider."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("loom.providers.tavily")


def search_tavily(
    query: str,
    n: int = 10,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search the web using Tavily.

    Args:
        query: search query
        n: max number of results
        include_domains: restrict to these domains
        exclude_domains: exclude these domains
        start_date: not used (accepted for interface compat)
        end_date: not used (accepted for interface compat)
        **kwargs: passed through to Tavily SDK

    Returns:
        Normalized result dict with ``results`` list and ``query``.
    """
    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        return {"results": [], "query": query, "error": "TAVILY_API_KEY not set"}

    try:
        from tavily import TavilyClient  # type: ignore[import-untyped]
    except ImportError:
        return {"results": [], "query": query, "error": "tavily-python not installed"}

    try:
        client = TavilyClient(api_key=api_key)
        search_kwargs: dict[str, Any] = {"query": query, "max_results": n}
        if include_domains:
            search_kwargs["include_domains"] = include_domains
        if exclude_domains:
            search_kwargs["exclude_domains"] = exclude_domains
        if kwargs.get("search_depth"):
            search_kwargs["search_depth"] = kwargs.pop("search_depth")
        if kwargs.get("include_answer"):
            search_kwargs["include_answer"] = kwargs.pop("include_answer")
        if kwargs.get("topic"):
            search_kwargs["topic"] = kwargs.pop("topic")
        search_kwargs.update(kwargs)

        response = client.search(**search_kwargs)

        results = [
            {
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "snippet": (r.get("content", "") or "")[:500],
                "score": r.get("score"),
                "published_date": r.get("published_date"),
            }
            for r in response.get("results", [])
        ]

        output: dict[str, Any] = {"results": results, "query": query}
        if response.get("answer"):
            output["answer"] = response["answer"]
        return output

    except Exception as exc:
        logger.exception("tavily_search_failed query=%s", query[:50])
        return {"results": [], "query": query, "error": str(exc)}
