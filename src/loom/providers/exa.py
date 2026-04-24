"""Exa semantic search provider."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("loom.providers.exa")


def search_exa(
    query: str,
    n: int = 10,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search the web using Exa semantic search.

    Args:
        query: search query
        n: max number of results
        include_domains: restrict to these domains
        exclude_domains: exclude these domains
        start_date: ISO yyyy-mm-dd start date
        end_date: ISO yyyy-mm-dd end date
        **kwargs: passed through to Exa SDK

    Returns:
        Normalized result dict with ``results`` list and ``query``.
    """
    api_key = os.environ.get("EXA_API_KEY", "")
    if not api_key:
        return {"results": [], "query": query, "error": "EXA_API_KEY not set"}

    try:
        from exa_py import Exa  # type: ignore[import-untyped]
    except ImportError:
        return {"results": [], "query": query, "error": "exa-py not installed"}

    try:
        client = Exa(api_key=api_key)
        search_kwargs: dict[str, Any] = {
            "query": query,
            "num_results": n,
            "type": "auto",
        }
        if include_domains:
            search_kwargs["include_domains"] = include_domains
        if exclude_domains:
            search_kwargs["exclude_domains"] = exclude_domains
        if start_date:
            search_kwargs["start_published_date"] = start_date
        if end_date:
            search_kwargs["end_published_date"] = end_date
        search_kwargs.update(kwargs)

        response = client.search_and_contents(**search_kwargs)

        results = [
            {
                "url": getattr(r, "url", ""),
                "title": getattr(r, "title", ""),
                "snippet": (getattr(r, "text", "") or "")[:500],
                "score": getattr(r, "score", None),
                "published_date": getattr(r, "published_date", None),
            }
            for r in response.results
        ]
        return {"results": results, "query": query}

    except Exception as exc:
        logger.exception("exa_search_failed query=%s", query[:50])
        return {"results": [], "query": query, "error": str(exc)}


def find_similar_exa(
    url: str,
    n: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    """Find pages semantically similar to a given URL (Exa).

    Args:
        url: reference URL to find similar pages for
        n: max number of results
        **kwargs: passed through to Exa SDK

    Returns:
        Normalized result dict with ``results`` list.
    """
    api_key = os.environ.get("EXA_API_KEY", "")
    if not api_key:
        return {"results": [], "url": url, "error": "EXA_API_KEY not set"}

    try:
        from exa_py import Exa  # type: ignore[import-untyped]
    except ImportError:
        return {"results": [], "url": url, "error": "exa-py not installed"}

    try:
        client = Exa(api_key=api_key)
        response = client.find_similar_and_contents(url=url, num_results=n, **kwargs)

        results = [
            {
                "url": getattr(r, "url", ""),
                "title": getattr(r, "title", ""),
                "snippet": (getattr(r, "text", "") or "")[:500],
                "score": getattr(r, "score", None),
            }
            for r in response.results
        ]
        return {"results": results, "url": url}

    except Exception as exc:
        logger.exception("exa_find_similar_failed url=%s", url)
        return {"results": [], "url": url, "error": str(exc)}
