"""Real-time monitoring of multiple sources for recent mentions of topics.

Monitors HackerNews, Reddit, arXiv, NewsAPI, and Wikipedia for recent
mentions, with parallel fetching and result aggregation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.realtime_monitor")

_HTTP_TIMEOUT = 30.0
_MAX_RESULTS_PER_SOURCE = 10


async def _fetch_hackernews(client: httpx.AsyncClient, topic: str, hours_back: int) -> list[dict[str, Any]]:
    """Fetch recent HackerNews stories mentioning the topic."""
    try:
        # HackerNews API returns stories from last N hours via timestamp filter
        # Current timestamp minus hours_back in seconds
        cutoff_timestamp = int(time.time()) - (hours_back * 3600)

        url = f"https://hn.algolia.com/api/v1/search_by_date?query={quote(topic)}&tags=story&numericFilters=created_at_i%3E{cutoff_timestamp}&hitsPerPage={_MAX_RESULTS_PER_SOURCE}"

        resp = await client.get(url, timeout=_HTTP_TIMEOUT)
        if resp.status_code != 200:
            return []

        data = resp.json()
        items = []

        for hit in data.get("hits", []):
            items.append(
                {
                    "topic": topic,
                    "source": "HackerNews",
                    "title": hit.get("title", ""),
                    "url": hit.get("url", "") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    "timestamp": hit.get("created_at", ""),
                    "score": float(hit.get("points", 0)),
                }
            )

        return items
    except Exception as e:
        logger.debug("hackernews fetch failed topic=%s: %s", topic, e)
        return []


async def _fetch_reddit(client: httpx.AsyncClient, topic: str) -> list[dict[str, Any]]:
    """Fetch recent Reddit posts mentioning the topic."""
    try:
        url = f"https://www.reddit.com/search.json?q={quote(topic)}&sort=new&limit={_MAX_RESULTS_PER_SOURCE}&t=day"

        headers = {
            "User-Agent": "Loom-Research/1.0 (compatible with Reddit API)",
        }

        resp = await client.get(url, timeout=_HTTP_TIMEOUT, headers=headers)
        if resp.status_code != 200:
            return []

        data = resp.json()
        items = []

        for post in data.get("data", {}).get("children", []):
            post_data = post.get("data", {})
            # Convert Unix timestamp to ISO format
            created = post_data.get("created_utc", 0)
            timestamp_iso = datetime.fromtimestamp(created, UTC).isoformat() if created else ""

            items.append(
                {
                    "topic": topic,
                    "source": "Reddit",
                    "title": post_data.get("title", ""),
                    "url": f"https://reddit.com{post_data.get('permalink', '')}",
                    "timestamp": timestamp_iso,
                    "score": float(post_data.get("score", 0)),
                }
            )

        return items
    except Exception as e:
        logger.debug("reddit fetch failed topic=%s: %s", topic, e)
        return []


async def _fetch_arxiv(client: httpx.AsyncClient, topic: str) -> list[dict[str, Any]]:
    """Fetch recent arXiv papers mentioning the topic."""
    try:
        # ArXiv API returns entries in reverse chronological order by default
        url = f"http://export.arxiv.org/api/query?search_query=all:{quote(topic)}&sortBy=submittedDate&sortOrder=descending&max_results={_MAX_RESULTS_PER_SOURCE}"

        resp = await client.get(url, timeout=_HTTP_TIMEOUT)
        if resp.status_code != 200:
            return []

        # Parse Atom feed
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            return []

        items = []
        namespaces = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", namespaces):
            title_elem = entry.find("atom:title", namespaces)
            title = (title_elem.text or "").strip() if title_elem is not None else ""

            # Get arXiv ID from id tag
            id_elem = entry.find("atom:id", namespaces)
            arxiv_id = (id_elem.text or "").split("/abs/")[-1] if id_elem is not None else ""
            url_arxiv = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""

            # Get published date
            published_elem = entry.find("atom:published", namespaces)
            timestamp = (published_elem.text or "").split("T")[0] if published_elem is not None else ""

            items.append(
                {
                    "topic": topic,
                    "source": "arXiv",
                    "title": title,
                    "url": url_arxiv,
                    "timestamp": timestamp,
                    "score": 0.0,  # arXiv doesn't provide scores
                }
            )

        return items
    except Exception as e:
        logger.debug("arxiv fetch failed topic=%s: %s", topic, e)
        return []


async def _fetch_newsapi(client: httpx.AsyncClient, topic: str) -> list[dict[str, Any]]:
    """Fetch recent news articles mentioning the topic via NewsAPI."""
    try:
        from loom.config import get_config

        api_key = get_config().get("NEWS_API_KEY", "")
        if not api_key:
            return []

        url = f"https://newsapi.org/v2/everything?q={quote(topic)}&sortBy=publishedAt&pageSize={_MAX_RESULTS_PER_SOURCE}"
        headers = {"X-Api-Key": api_key}

        resp = await client.get(url, timeout=_HTTP_TIMEOUT, headers=headers)
        if resp.status_code != 200:
            return []

        data = resp.json()
        if data.get("status") != "ok":
            return []

        items = []
        for article in data.get("articles", []):
            items.append(
                {
                    "topic": topic,
                    "source": "NewsAPI",
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "timestamp": article.get("publishedAt", ""),
                    "score": 0.0,  # NewsAPI doesn't provide score
                }
            )

        return items
    except Exception as e:
        logger.debug("newsapi fetch failed topic=%s: %s", topic, e)
        return []


async def _fetch_wikipedia_changes(client: httpx.AsyncClient, topic: str) -> list[dict[str, Any]]:
    """Fetch recent changes on Wikipedia for pages matching the topic."""
    try:
        # Wikipedia RecentChanges API: search for articles matching topic
        # First search for the article
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=recentchanges&rcnamespace=0&rctitle={quote(topic)}&rclimit={_MAX_RESULTS_PER_SOURCE}&format=json"

        resp = await client.get(url, timeout=_HTTP_TIMEOUT)
        if resp.status_code != 200:
            return []

        data = resp.json()
        items = []

        for change in data.get("query", {}).get("recentchanges", []):
            timestamp = change.get("timestamp", "")
            title = change.get("title", "")
            pageid = change.get("pageid", 0)
            url_wiki = f"https://en.wikipedia.org/wiki/{quote(title)}" if title else ""

            items.append(
                {
                    "topic": topic,
                    "source": "Wikipedia",
                    "title": f"Change to {title}",
                    "url": url_wiki,
                    "timestamp": timestamp,
                    "score": 0.0,
                }
            )

        return items
    except Exception as e:
        logger.debug("wikipedia fetch failed topic=%s: %s", topic, e)
        return []


async def research_realtime_monitor(
    topics: list[str],
    sources: list[str] | None = None,
    hours_back: int = 24,
) -> dict[str, Any]:
    """Monitor multiple sources for recent mentions of topics.

    Queries HackerNews, Reddit, arXiv, NewsAPI, and Wikipedia for recent
    mentions of the provided topics. Returns aggregated results sorted by
    timestamp (newest first).

    Args:
        topics: List of topics to monitor (e.g., ["AI", "Python", "security"])
        sources: List of sources to query. Valid sources: "hackernews", "reddit",
                 "arxiv", "newsapi", "wikipedia". If None, queries all available.
        hours_back: Number of hours to look back (default 24)

    Returns:
        Dict with:
            - topics: input topics list
            - time_range_hours: hours_back parameter
            - total_mentions: total count of mentions found
            - mentions_by_topic: dict[topic] -> count
            - mentions_by_source: dict[source] -> count
            - recent_items: list of mention dicts, sorted by timestamp (newest first),
                           each with: topic, source, title, url, timestamp, score
    """
    if not topics:
        return {
            "topics": [],
            "time_range_hours": hours_back,
            "total_mentions": 0,
            "mentions_by_topic": {},
            "mentions_by_source": {},
            "recent_items": [],
        }

    # Default sources if not specified
    if sources is None:
        sources = ["hackernews", "reddit", "arxiv", "newsapi", "wikipedia"]

    # Normalize source names
    sources = [s.lower() for s in sources]
    valid_sources = {"hackernews", "reddit", "arxiv", "newsapi", "wikipedia"}
    sources = [s for s in sources if s in valid_sources]

    if not sources:
        sources = list(valid_sources)

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            # Build task list: (topic, source) -> coroutine
            tasks: dict[tuple[str, str], asyncio.Task[list[dict[str, Any]]]] = {}

            for topic in topics:
                for source in sources:
                    if source == "hackernews":
                        task = _fetch_hackernews(client, topic, hours_back)
                    elif source == "reddit":
                        task = _fetch_reddit(client, topic)
                    elif source == "arxiv":
                        task = _fetch_arxiv(client, topic)
                    elif source == "newsapi":
                        task = _fetch_newsapi(client, topic)
                    elif source == "wikipedia":
                        task = _fetch_wikipedia_changes(client, topic)
                    else:
                        continue

                    tasks[(topic, source)] = asyncio.create_task(task)

            # Wait for all tasks
            results = await asyncio.gather(*tasks.values(), return_exceptions=True)

            # Aggregate results
            all_items: list[dict[str, Any]] = []
            mentions_by_topic: dict[str, int] = {t: 0 for t in topics}
            mentions_by_source: dict[str, int] = {s: 0 for s in sources}

            for (topic, source), result in zip(tasks.keys(), results):
                if isinstance(result, list):
                    all_items.extend(result)
                    mentions_by_topic[topic] += len(result)
                    mentions_by_source[source] += len(result)

            # Sort by timestamp (newest first)
            # Handle both ISO format and date-only format
            def parse_timestamp(ts: str) -> float:
                if not ts:
                    return 0.0
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    return dt.timestamp()
                except (ValueError, AttributeError):
                    return 0.0

            all_items.sort(key=lambda x: parse_timestamp(x.get("timestamp", "")), reverse=True)

            return {
                "topics": topics,
                "time_range_hours": hours_back,
                "total_mentions": len(all_items),
                "mentions_by_topic": mentions_by_topic,
                "mentions_by_source": mentions_by_source,
                "recent_items": all_items,
            }

    return await _run()
