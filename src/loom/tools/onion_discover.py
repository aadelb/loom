"""research_onion_discover — Discover .onion hidden services using multiple methods."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.onion_discover")


async def _fetch_ahmia(
    client: httpx.AsyncClient, query: str, timeout: float = 20.0
) -> list[dict[str, Any]]:
    """Fetch .onion URLs from Ahmia API via HTML parsing."""
    urls = []
    try:
        search_url = f"https://ahmia.fi/search/?q={quote(query)}"
        resp = await client.get(search_url, timeout=timeout)
        if resp.status_code == 200:
            # Parse HTML for .onion links
            onion_pattern = r"(https?://[a-z0-9]+\.onion[^\s<>\"']*)"
            matches = re.findall(onion_pattern, resp.text, re.IGNORECASE)
            for match in matches:
                urls.append(
                    {
                        "url": match,
                        "source": "ahmia",
                        "title": f"Result from {query}",
                        "snippet": "",
                    }
                )
    except Exception as exc:
        logger.debug("ahmia fetch failed: %s", exc)
    return urls


async def _fetch_darksearch(
    client: httpx.AsyncClient, query: str, timeout: float = 20.0
) -> list[dict[str, Any]]:
    """Fetch .onion URLs from DarkSearch API (JSON)."""
    urls = []
    try:
        api_url = f"https://darksearch.io/api/search?query={quote(query)}&page=1"
        resp = await client.get(api_url, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "data" in data:
                for result in data["data"]:
                    if isinstance(result, dict):
                        result_url = result.get("url", "")
                        if ".onion" in result_url:
                            urls.append(
                                {
                                    "url": result_url,
                                    "source": "darksearch",
                                    "title": result.get("title", ""),
                                    "snippet": result.get("description", ""),
                                }
                            )
    except Exception as exc:
        logger.debug("darksearch fetch failed: %s", exc)
    return urls


async def _fetch_intelx(
    client: httpx.AsyncClient, query: str, timeout: float = 20.0
) -> list[dict[str, Any]]:
    """Fetch .onion URLs from IntelX public search (limited free tier)."""
    urls = []
    try:
        search_url = "https://2.intelx.io/phonebook/search"
        payload = {
            "term": query,
            "maxresults": 20,
            "media": 0,
            "sort": 0,
            "type": -1,
        }
        resp = await client.post(search_url, json=payload, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                results = data.get("selectors", [])
                for item in results:
                    if isinstance(item, dict):
                        selector = item.get("selector", "")
                        if ".onion" in selector:
                            urls.append(
                                {
                                    "url": selector,
                                    "source": "intelx",
                                    "title": f"IntelX result: {selector}",
                                    "snippet": "",
                                }
                            )
    except Exception as exc:
        logger.debug("intelx fetch failed: %s", exc)
    return urls


async def _fetch_ct_onion_certs(
    client: httpx.AsyncClient, timeout: float = 30.0
) -> list[dict[str, Any]]:
    """Fetch .onion certificates from Certificate Transparency (crt.sh)."""
    urls = []
    try:
        ct_url = "https://crt.sh/?q=%25.onion&output=json"
        resp = await client.get(ct_url, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                seen = set()
                for entry in data:
                    if isinstance(entry, dict):
                        name_value = entry.get("name_value", "")
                        for line in name_value.split("\n"):
                            line = line.strip().lstrip("*.")
                            if line.endswith(".onion") and line not in seen:
                                seen.add(line)
                                urls.append(
                                    {
                                        "url": f"https://{line}",
                                        "source": "certificate_transparency",
                                        "title": f"CT cert: {line}",
                                        "snippet": "",
                                    }
                                )
    except Exception as exc:
        logger.debug("certificate transparency fetch failed: %s", exc)
    return urls


async def _fetch_reddit_onions(
    client: httpx.AsyncClient, query: str, timeout: float = 20.0
) -> list[dict[str, Any]]:
    """Fetch .onion URLs from Reddit darknet subreddits."""
    urls = []
    try:
        reddit_url = f"https://www.reddit.com/r/onions/search.json?q={quote(query)}&limit=10"
        headers = {"User-Agent": "Loom-Research/1.0"}
        resp = await client.get(reddit_url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict) and "data" in data:
                posts = data["data"].get("children", [])
                for post in posts:
                    if isinstance(post, dict):
                        post_data = post.get("data", {})
                        title = post_data.get("title", "")
                        selftext = post_data.get("selftext", "")
                        content = f"{title} {selftext}"

                        # Find .onion URLs in title and content
                        onion_pattern = (
                            r"(https?://[a-z0-9]+\.onion[^\s<>\"']*)"
                        )
                        matches = re.findall(onion_pattern, content, re.IGNORECASE)
                        for match in matches:
                            urls.append(
                                {
                                    "url": match,
                                    "source": "reddit_onions",
                                    "title": title[:100],
                                    "snippet": selftext[:200],
                                }
                            )
    except Exception as exc:
        logger.debug("reddit onions fetch failed: %s", exc)
    return urls


async def research_onion_discover(
    query: str, max_results: int = 50
) -> dict[str, Any]:
    """Discover .onion hidden services related to a query using 5+ methods.

    Uses Ahmia API, DarkSearch API, IntelX public search, Certificate
    Transparency (crt.sh), and Reddit darknet subreddits to find .onion URLs.

    Args:
        query: search query to find related .onion services
        max_results: max results to return (1-100)

    Returns:
        Dict with keys:
            - query: the search query
            - sources_checked: list of sources queried
            - onion_urls_found: list of dicts with url, source, title, snippet
            - total_unique: count of unique .onion URLs found
    """

    async def _run() -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": "Loom-Research/1.0"},
            ) as client:
                # Run all 5 methods in parallel with return_exceptions=True
                # to ensure partial results even if individual sources fail
                ahmia_task = _fetch_ahmia(client, query)
                darksearch_task = _fetch_darksearch(client, query)
                intelx_task = _fetch_intelx(client, query)
                ct_task = _fetch_ct_onion_certs(client)
                reddit_task = _fetch_reddit_onions(client, query)

                all_results = await asyncio.gather(
                    ahmia_task,
                    darksearch_task,
                    intelx_task,
                    ct_task,
                    reddit_task,
                    return_exceptions=True,
                )

                # Filter out exceptions and extract results safely
                ahmia_urls = (
                    all_results[0] if isinstance(all_results[0], list) else []
                )
                darksearch_urls = (
                    all_results[1] if isinstance(all_results[1], list) else []
                )
                intelx_urls = (
                    all_results[2] if isinstance(all_results[2], list) else []
                )
                ct_urls = (
                    all_results[3] if isinstance(all_results[3], list) else []
                )
                reddit_urls = (
                    all_results[4] if isinstance(all_results[4], list) else []
                )

                # Log any exceptions that occurred
                for idx, result in enumerate(all_results):
                    if isinstance(result, Exception):
                        source_names = [
                            "ahmia",
                            "darksearch",
                            "intelx",
                            "certificate_transparency",
                            "reddit_onions",
                        ]
                        logger.warning(
                            "Exception in %s: %s",
                            source_names[idx],
                            str(result),
                        )

                # Combine and deduplicate by URL
                combined = (
                    ahmia_urls
                    + darksearch_urls
                    + intelx_urls
                    + ct_urls
                    + reddit_urls
                )
                seen_urls: dict[str, dict[str, Any]] = {}
                for item in combined:
                    url = item.get("url", "").lower()
                    if url and ".onion" in url:
                        if url not in seen_urls:
                            seen_urls[url] = item

                # Sort by source diversity and title presence
                sorted_urls = sorted(
                    seen_urls.values(),
                    key=lambda x: (
                        -len(x.get("title", "")),
                        x.get("source", ""),
                    ),
                )

                # Limit to max_results
                final_urls = sorted_urls[: max(1, min(max_results, 100))]

                logger.info(
                    "onion_discover query=%s found=%d unique_sources=%d",
                    query[:50],
                    len(final_urls),
                    len(set(u.get("source") for u in final_urls)),
                )

                return {
                    "query": query,
                    "sources_checked": [
                        "ahmia",
                        "darksearch",
                        "intelx",
                        "certificate_transparency",
                        "reddit_onions",
                    ],
                    "onion_urls_found": final_urls,
                    "total_unique": len(final_urls),
                }
        except Exception as exc:
            logger.error(
                "onion_discover failed with exception: %s", str(exc)
            )
            # Return graceful fallback response
            return {
                "query": query,
                "sources_checked": [
                    "ahmia",
                    "darksearch",
                    "intelx",
                    "certificate_transparency",
                    "reddit_onions",
                ],
                "onion_urls_found": [],
                "total_unique": 0,
            }

    return await _run()
