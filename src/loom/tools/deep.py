"""One-shot deep research: search → fetch → markdown.

Combines research_search (offloaded to executor) with research_markdown
(native async) for in-depth research results.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from loom.validators import EXTERNAL_TIMEOUT_SECS

logger = logging.getLogger("loom.deep")


async def research_deep(
    query: str,
    depth: int = 2,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    language: str | None = None,
    provider_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """One-shot deep research: discover + fetch + extract markdown.

    research_search is sync (HTTP clients block); offload to thread executor
    so it doesn't block the event loop. research_markdown is native async
    and awaited directly.

    Args:
        query: search query string
        depth: number of pages to fetch (multiplied internally for result count)
        include_domains: only search within these domains
        exclude_domains: exclude these domains
        start_date: ISO yyyy-mm-dd start date
        end_date: ISO yyyy-mm-dd end date
        language: language hint
        provider_config: provider-specific kwargs

    Returns:
        Dict with keys:
            - query: the search query
            - provider: which provider was used
            - hit_count: number of search hits retrieved
            - pages: list of dicts with title, url, markdown
            - error: error message if search failed (key absent on success)
    """
    # Import here to avoid circular imports and ensure lazy loading
    from loom.tools.search import research_search

    loop = asyncio.get_running_loop()

    try:
        # Offload sync search to executor so HTTP doesn't block event loop
        search = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: research_search(
                    query,
                    n=depth * 5,
                    include_domains=include_domains,
                    exclude_domains=exclude_domains,
                    start_date=start_date,
                    end_date=end_date,
                    language=language,
                    provider_config=provider_config,
                ),
            ),
            timeout=EXTERNAL_TIMEOUT_SECS,
        )
    except TimeoutError:
        logger.warning("deep_search_timeout query=%s", query)
        return {
            "query": query,
            "provider": None,
            "hit_count": 0,
            "pages": [],
            "error": "search timeout",
        }
    except Exception as exc:
        logger.exception("deep_search_failed query=%s", query)
        return {
            "query": query,
            "provider": None,
            "hit_count": 0,
            "pages": [],
            "error": str(exc),
        }

    hits = search.get("results", [])[: depth * 3]
    pages: list[dict[str, Any]] = []

    # Lazily import here to avoid circular dependency
    from loom.tools.markdown import research_markdown

    for h in hits:
        url = h.get("url")
        if not url:
            continue

        try:
            md = await research_markdown(url)
            pages.append(
                {
                    "title": h.get("title"),
                    "url": url,
                    "markdown": md.get("markdown", ""),
                }
            )
        except Exception as exc:
            logger.warning("deep_fetch_fail url=%s error=%s", url, exc)

    return {
        "query": query,
        "provider": search.get("provider"),
        "hit_count": len(hits),
        "pages": pages,
    }
