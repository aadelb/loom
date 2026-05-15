"""research_dead_content — Dead Content Resurrection Engine for deleted web pages."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote
import httpx

from loom.validators import validate_url
from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_json

logger = logging.getLogger("loom.tools.dead_content")

# Archive sources to check (free, no auth required)
_ARCHIVE_SOURCES = [
    "wayback",
    "archive_today",
    "common_crawl",
    "memento",
    "google_cache",
    "cached_search",
]


@handle_tool_errors("research_dead_content")
async def research_dead_content(
    url: str,
    include_snapshots: bool = True,
    max_sources: int = 12,
) -> dict[str, Any]:
    """Query multiple archive/cache sources for deleted web content.

    Checks Wayback Machine, Archive.today, Common Crawl, Memento TimeTravel,
    Google Cache, and cached search snippets. Returns snapshot metadata
    (timestamps, previews, archive URLs) for each found archive.

    Args:
        url: target URL to check
        include_snapshots: include snapshot details (default True)
        max_sources: max sources to check (1-12, default 12)

    Returns:
        Dict with: url, found_in (sources), snapshots (list), is_deleted,
        total_sources_checked, checked_at timestamp.
    """
    # Validate URL
    try:
        url = validate_url(url)
    except Exception as exc:
        return {
            "url": url,
            "error": f"Invalid URL: {exc}",
            "found_in": [],
            "snapshots": [],
            "is_deleted": False,
            "total_sources_checked": 0,
        }

    # Clamp max_sources
    max_sources = max(1, min(max_sources, len(_ARCHIVE_SOURCES)))

    # Results accumulator
    found_in: list[str] = []
    snapshots: list[dict[str, Any]] = []
    sources_checked = 0

    # Use shared httpx client
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        # 1. Wayback Machine CDX API
        if sources_checked < max_sources:
            sources_checked += 1
            try:
                data = await fetch_json(client,
                    "https://web.archive.org/cdx/search/cdx",
                    params={"url": url, "output": "json", "limit": 10},
                )
                if data and len(data) > 1:
                    found_in.append("wayback_machine")
                    # data[0] is header row, rest are snapshots
                    for row in data[1:6]:  # Cap at 5 snapshots
                            if include_snapshots and len(row) >= 4:
                                snapshots.append(
                                    {
                                        "source": "wayback_machine",
                                        "timestamp": row[1],
                                        "status": row[4],
                                        "archive_url": f"https://web.archive.org/web/{row[1]}/{url}",
                                    }
                                )
            except Exception as e:
                logger.debug("wayback_check_failed url=%s error=%s", url, str(e))

        # 2. Archive.today (archive.ph)
        if sources_checked < max_sources:
            sources_checked += 1
            try:
                resp = await client.head(f"https://archive.ph/newest/{quote(url)}")
                if resp.status_code == 200:
                    found_in.append("archive_today")
                    if include_snapshots:
                        snapshots.append(
                            {
                                "source": "archive_today",
                                "archive_url": str(resp.url),
                            }
                        )
            except Exception as e:
                logger.debug("archive_today_check_failed url=%s error=%s", url, str(e))

        # 3. Common Crawl Index
        if sources_checked < max_sources:
            sources_checked += 1
            try:
                data = await fetch_json(client,
                    "https://index.commoncrawl.org/CC-MAIN-2024-10-index",
                    params={"url": url, "output": "json"},
                )
                if data and isinstance(data, list) and len(data) > 0:
                        found_in.append("common_crawl")
                        if include_snapshots and len(data) > 0:
                            entry = data[0]
                            snapshots.append(
                                {
                                    "source": "common_crawl",
                                    "timestamp": entry.get("timestamp", ""),
                                    "archive_url": f"https://commoncrawl.org/data/{entry.get('filename', '')}",
                                }
                            )
            except Exception as e:
                logger.debug("common_crawl_check_failed url=%s error=%s", url, str(e))

        # 4. Memento TimeTravel
        if sources_checked < max_sources:
            sources_checked += 1
            try:
                data = await fetch_json(client,
                    f"https://timetravel.mementoweb.org/timemap/json/{url}"
                )
                if data and "mementos" in data and data["mementos"].get("list"):
                        found_in.append("memento_timetravel")
                        if include_snapshots:
                            for mem in data["mementos"]["list"][:3]:
                                snapshots.append(
                                    {
                                        "source": "memento_timetravel",
                                        "timestamp": mem.get("datetime", ""),
                                        "archive_url": mem.get("uri", ""),
                                    }
                                )
            except Exception as e:
                logger.debug("memento_check_failed url=%s error=%s", url, str(e))

        # 5. Google Cache (HEAD check only)
        if sources_checked < max_sources:
            sources_checked += 1
            try:
                resp = await client.head(
                    "https://webcache.googleusercontent.com/search",
                    params={"q": f"cache:{url}"},
                )
                if resp.status_code == 200:
                    found_in.append("google_cache")
            except Exception as e:
                logger.debug("google_cache_check_failed url=%s error=%s", url, str(e))

        # 6. Cached search snippet (basic check)
        if sources_checked < max_sources:
            sources_checked += 1
            try:
                resp = await client.head(f"https://web.archive.org/web/2024/{url}")
                if resp.status_code == 200:
                    found_in.append("wayback_2024_snapshot")
            except Exception as e:
                logger.debug("cached_search_check_failed url=%s error=%s", url, str(e))

    return {
        "url": url,
        "found_in": found_in,
        "snapshots": snapshots,
        "has_archive_copies": len(found_in) > 0,
        "total_sources_checked": sources_checked,
        "checked_at": datetime.now(UTC).isoformat(),
    }
