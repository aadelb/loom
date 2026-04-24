"""HackerNews + Reddit sentiment search (free, no API key)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.hn_reddit")

_HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


def search_hackernews(
    query: str,
    n: int = 10,
    sort_by: str = "relevance",
    **kwargs: Any,
) -> dict[str, Any]:
    """Search HackerNews via Algolia API (free, no API key).

    Args:
        query: search query
        n: max results
        sort_by: "relevance" or "date"

    Returns:
        Normalized result dict.
    """
    endpoint = _HN_ALGOLIA_URL if sort_by == "relevance" else f"{_HN_ALGOLIA_URL}_by_date"

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(endpoint, params={"query": query, "hitsPerPage": min(n, 30)})
            resp.raise_for_status()
            data = resp.json()

        results = [
            {
                "url": hit.get("url")
                or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "title": hit.get("title", ""),
                "snippet": (hit.get("story_text", "") or hit.get("comment_text", "") or "")[:500],
                "points": hit.get("points"),
                "num_comments": hit.get("num_comments"),
                "author": hit.get("author"),
                "created_at": hit.get("created_at"),
            }
            for hit in data.get("hits", [])
        ]
        return {"results": results, "query": query, "source": "hackernews"}

    except Exception as exc:
        logger.exception("hn_search_failed query=%s", query[:50])
        return {"results": [], "query": query, "source": "hackernews", "error": str(exc)}


def search_reddit(
    query: str,
    n: int = 10,
    subreddit: str | None = None,
    sort: str = "relevance",
    time_filter: str = "all",
    **kwargs: Any,
) -> dict[str, Any]:
    """Search Reddit via public JSON API (free, no API key).

    Args:
        query: search query
        n: max results
        subreddit: restrict to specific subreddit
        sort: "relevance", "hot", "top", "new"
        time_filter: "hour", "day", "week", "month", "year", "all"

    Returns:
        Normalized result dict.
    """
    if subreddit:
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
    else:
        url = "https://www.reddit.com/search.json"

    try:
        with httpx.Client(
            timeout=15.0,
            headers={"User-Agent": "Loom/0.1 (research MCP server)"},
        ) as client:
            resp = client.get(
                url,
                params={
                    "q": query,
                    "limit": min(n, 25),
                    "sort": sort,
                    "t": time_filter,
                    "restrict_sr": "on" if subreddit else "off",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        posts = data.get("data", {}).get("children", [])
        results = [
            {
                "url": f"https://www.reddit.com{post['data'].get('permalink', '')}",
                "title": post["data"].get("title", ""),
                "snippet": (post["data"].get("selftext", "") or "")[:500],
                "score": post["data"].get("score"),
                "num_comments": post["data"].get("num_comments"),
                "subreddit": post["data"].get("subreddit"),
                "author": post["data"].get("author"),
                "created_utc": post["data"].get("created_utc"),
            }
            for post in posts
            if post.get("data")
        ]
        return {"results": results, "query": query, "source": "reddit"}

    except Exception as exc:
        logger.exception("reddit_search_failed query=%s", query[:50])
        return {"results": [], "query": query, "source": "reddit", "error": str(exc)}
