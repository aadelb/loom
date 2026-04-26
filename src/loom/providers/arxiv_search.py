"""arXiv academic paper search provider (free, no API key)."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("loom.providers.arxiv_search")


def search_arxiv(
    query: str,
    n: int = 10,
    sort_by: str = "relevance",
    **kwargs: Any,
) -> dict[str, Any]:
    """Search arXiv for academic papers (free, no API key, 3 req/sec).

    Args:
        query: search query
        n: max number of results
        sort_by: "relevance", "lastUpdatedDate", or "submittedDate"
        **kwargs: passed through to arxiv.Search

    Returns:
        Normalized result dict with ``results`` list and ``query``.
    """
    try:
        import arxiv  # type: ignore[import-untyped]
    except ImportError:
        return {"results": [], "query": query, "error": "arxiv not installed (pip install arxiv)"}

    try:
        sort_map = {
            "relevance": arxiv.SortCriterion.Relevance,
            "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
            "submittedDate": arxiv.SortCriterion.SubmittedDate,
        }
        sort_criterion = sort_map.get(sort_by, arxiv.SortCriterion.Relevance)

        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=n,
            sort_by=sort_criterion,
        )

        results: list[dict[str, Any]] = []
        for paper in client.results(search):
            authors = [a.name for a in paper.authors[:5]]
            categories = list(paper.categories)[:5]

            results.append(
                {
                    "url": paper.entry_id,
                    "title": paper.title,
                    "snippet": (paper.summary or "")[:500],
                    "published_date": paper.published.isoformat() if paper.published else None,
                    "authors": authors,
                    "categories": categories,
                    "pdf_url": paper.pdf_url,
                }
            )

        return {"results": results, "query": query}

    except Exception as exc:
        # Don't log full exception to avoid leaking data (HIGH #9)
        logger.error("arxiv_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
