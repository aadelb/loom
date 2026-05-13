"""Dark forum intelligence aggregator — cross-reference dark web forum content from 5+ sources."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

from loom.http_helpers import fetch_json, fetch_text
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.dark_forum")

_AHMIA_SEARCH = "https://ahmia.fi/search/?q={query}"
_OTX_SEARCH = "https://otx.alienvault.com/api/v1/search/pulses?q={query}&limit=10"
_REDDIT_DARKNET = "https://www.reddit.com/r/darknet/search.json?q={query}&limit=10&sort=relevance"
_REDDIT_ONIONS = "https://www.reddit.com/r/onions/search.json?q={query}&limit=10&sort=relevance"


async def _search_ahmia(client: httpx.AsyncClient, query: str) -> list[dict[str, str]]:
    html = await fetch_text(client, _AHMIA_SEARCH.format(query=quote(query)))
    if not html:
        return []
    results: list[dict[str, str]] = []
    for match in re.finditer(
        r'<a[^>]+href="(https?://[^"]*\.onion[^"]*)"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    ):
        url = match.group(1)
        title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
        results.append({"source": "ahmia", "url": url, "title": title[:200]})
    return results[:20]


async def _search_otx(client: httpx.AsyncClient, query: str) -> list[dict[str, str]]:
    data = await fetch_json(client, _OTX_SEARCH.format(query=quote(query)))
    if not data:
        return []
    pulses = data.get("results", [])
    return [
        {
            "source": "alienvault_otx",
            "url": f"https://otx.alienvault.com/pulse/{p.get('id', '')}",
            "title": p.get("name", ""),
            "description": p.get("description", "")[:300],
            "tags": ", ".join(p.get("tags", [])[:5]),
            "created": p.get("created", ""),
            "indicators_count": str(p.get("indicator_count", 0)),
        }
        for p in pulses[:10]
    ]


async def _search_reddit_sub(
    client: httpx.AsyncClient, query: str, subreddit: str
) -> list[dict[str, str]]:
    url = f"https://www.reddit.com/r/{subreddit}/search.json?q={quote(query)}&limit=10&sort=relevance&restrict_sr=on"
    data = await fetch_json(
        client, url, headers={"User-Agent": "Loom-Research/1.0"}
    )
    if not data:
        return []
    children = data.get("data", {}).get("children", [])
    return [
        {
            "source": f"reddit_r/{subreddit}",
            "url": f"https://reddit.com{child['data'].get('permalink', '')}",
            "title": child["data"].get("title", ""),
            "description": child["data"].get("selftext", "")[:300],
            "score": str(child["data"].get("score", 0)),
            "created": str(child["data"].get("created_utc", "")),
        }
        for child in children
        if child.get("data", {}).get("title")
    ]


@handle_tool_errors("research_dark_forum")
async def research_dark_forum(
    query: str,
    max_results: int = 50,
) -> dict[str, Any]:
    """Aggregate dark web forum intelligence from 4+ sources.

    Searches Ahmia (indexed .onion sites), AlienVault OTX (threat
    intelligence pulses), and Reddit darknet-related subreddits
    (r/darknet, r/onions) in parallel.

    Args:
        query: the search query (topic, keyword, or .onion URL)
        max_results: max results to return after dedup

    Returns:
        Dict with ``query``, ``sources_checked``, ``total_results``,
        ``results`` list (each with source, url, title, description),
        and ``sources_breakdown``.
    """
    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=30.0,
            ) as client:
                ahmia_task = _search_ahmia(client, query)
                otx_task = _search_otx(client, query)
                reddit_darknet_task = _search_reddit_sub(client, query, "darknet")
                reddit_onions_task = _search_reddit_sub(client, query, "onions")

                results = await asyncio.gather(
                    ahmia_task,
                    otx_task,
                    reddit_darknet_task,
                    reddit_onions_task,
                    return_exceptions=True,
                )

                all_items: list[dict[str, str]] = []
                sources_with_results = 0
                for result in results:
                    if isinstance(result, list) and result:
                        sources_with_results += 1
                        all_items.extend(result)

                seen_urls: set[str] = set()
                unique_items: list[dict[str, str]] = []
                for item in all_items:
                    url = item.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        unique_items.append(item)

                source_breakdown: dict[str, int] = {}
                for item in unique_items:
                    src = item.get("source", "unknown")
                    source_breakdown[src] = source_breakdown.get(src, 0) + 1

                return {
                    "query": query,
                    "sources_checked": 4,
                    "sources_with_results": sources_with_results,
                    "total_results": len(unique_items),
                    "results": unique_items[:max_results],
                    "sources_breakdown": source_breakdown,
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_dark_forum"}
