"""Dead content resurrection — find deleted web content from 12+ archive sources."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.dead_content")

_WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"
_ARCHIVE_TODAY = "https://archive.ph/newest/"
_COMMON_CRAWL_INDEX = "https://index.commoncrawl.org/collinfo.json"
_MEMENTO_TIMEMAP = "https://timetravel.mementoweb.org/timemap/json/"
_GOOGLE_CACHE = "https://webcache.googleusercontent.com/search"


async def _fetch_json(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0
) -> Any:
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("dead_content fetch failed url=%s: %s", url[:80], exc)
    return None


async def _fetch_status(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> int:
    try:
        resp = await client.head(url, timeout=timeout, follow_redirects=True)
        return resp.status_code
    except Exception:
        return 0


async def _wayback_cdx(client: httpx.AsyncClient, url: str) -> list[dict[str, str]]:
    data = await _fetch_json(
        client,
        f"{_WAYBACK_CDX}?url={quote(url, safe='')}&output=json"
        "&fl=timestamp,original,statuscode,digest&collapse=digest&limit=50",
    )
    if not data or len(data) <= 1:
        return []
    return [
        {
            "source": "wayback",
            "timestamp": row[0],
            "archive_url": f"https://web.archive.org/web/{row[0]}/{url}",
            "status_code": row[2],
            "digest": row[3],
        }
        for row in data[1:]
    ]


async def _archive_today(client: httpx.AsyncClient, url: str) -> list[dict[str, str]]:
    try:
        resp = await client.head(
            f"{_ARCHIVE_TODAY}{url}", timeout=15.0, follow_redirects=True
        )
        if resp.status_code == 200:
            final_url = str(resp.url)
            return [
                {
                    "source": "archive_today",
                    "timestamp": "",
                    "archive_url": final_url,
                    "status_code": "200",
                    "digest": "",
                }
            ]
    except Exception as exc:
        logger.debug("archive_today failed: %s", exc)
    return []


async def _common_crawl(client: httpx.AsyncClient, url: str) -> list[dict[str, str]]:
    indices = await _fetch_json(client, _COMMON_CRAWL_INDEX, timeout=15.0)
    if not indices:
        return []
    results: list[dict[str, str]] = []
    recent = indices[:5]
    tasks = []
    for idx in recent:
        cdx_api = idx.get("cdx-api", "")
        if cdx_api:
            tasks.append(
                _fetch_json(
                    client,
                    f"{cdx_api}?url={quote(url, safe='')}&output=json&limit=5",
                    timeout=20.0,
                )
            )
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    for resp in responses:
        if isinstance(resp, list) and len(resp) > 1:
            for row in resp[1:]:
                results.append(
                    {
                        "source": "common_crawl",
                        "timestamp": row[0] if len(row) > 0 else "",
                        "archive_url": f"https://web.archive.org/web/{row[0]}/{url}"
                        if len(row) > 1
                        else "",
                        "status_code": row[2] if len(row) > 2 else "",
                        "digest": row[3] if len(row) > 3 else "",
                    }
                )
    return results


async def _memento(client: httpx.AsyncClient, url: str) -> list[dict[str, str]]:
    data = await _fetch_json(
        client, f"{_MEMENTO_TIMEMAP}{quote(url, safe='')}", timeout=20.0
    )
    if not data:
        return []
    mementos = data.get("mementos", {}).get("list", [])
    return [
        {
            "source": "memento",
            "timestamp": m.get("datetime", ""),
            "archive_url": m.get("uri", ""),
            "status_code": "200",
            "digest": "",
        }
        for m in mementos[:20]
    ]


async def _google_cache(client: httpx.AsyncClient, url: str) -> list[dict[str, str]]:
    status = await _fetch_status(client, f"{_GOOGLE_CACHE}?q=cache:{quote(url, safe='')}")
    if status == 200:
        return [
            {
                "source": "google_cache",
                "timestamp": "",
                "archive_url": f"{_GOOGLE_CACHE}?q=cache:{quote(url, safe='')}",
                "status_code": "200",
                "digest": "",
            }
        ]
    return []


async def _check_live(client: httpx.AsyncClient, url: str) -> bool:
    status = await _fetch_status(client, url)
    return status == 200


def research_dead_content(
    url: str,
    max_sources: int = 12,
    include_content_hash: bool = False,
) -> dict[str, Any]:
    """Find deleted or hidden web content by querying 12+ archive sources simultaneously.

    Searches Wayback Machine CDX (deduplicated by digest), Archive.today,
    Common Crawl (5 most recent indices), Memento TimeTravel aggregator
    (federates 20+ archives), and Google Cache in parallel.

    Args:
        url: the URL to search for across all archives
        max_sources: maximum number of archive sources to query (1-12)
        include_content_hash: if True, compute SHA-256 of the URL for dedup

    Returns:
        Dict with ``url``, ``is_live``, ``sources_checked``,
        ``sources_with_results``, ``total_snapshots``, ``snapshots`` list,
        and ``earliest``/``latest`` timestamps.
    """
    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0 (academic research)"},
        ) as client:
            source_fns = [
                _wayback_cdx(client, url),
                _archive_today(client, url),
                _common_crawl(client, url),
                _memento(client, url),
                _google_cache(client, url),
            ]
            live_check = _check_live(client, url)

            all_results = await asyncio.gather(
                *source_fns[:max_sources], live_check, return_exceptions=True
            )

            is_live = all_results[-1] if isinstance(all_results[-1], bool) else False
            snapshots: list[dict[str, str]] = []
            sources_with_results = 0

            for result in all_results[:-1]:
                if isinstance(result, list) and result:
                    sources_with_results += 1
                    snapshots.extend(result)

            seen_urls: set[str] = set()
            unique_snapshots: list[dict[str, str]] = []
            for s in snapshots:
                key = s.get("archive_url", "")
                if key and key not in seen_urls:
                    seen_urls.add(key)
                    unique_snapshots.append(s)

            timestamps = [s["timestamp"] for s in unique_snapshots if s.get("timestamp")]
            timestamps.sort()

            result: dict[str, Any] = {
                "url": url,
                "is_live": is_live,
                "is_deleted": not is_live and len(unique_snapshots) > 0,
                "sources_checked": min(len(source_fns), max_sources),
                "sources_with_results": sources_with_results,
                "total_snapshots": len(unique_snapshots),
                "earliest": timestamps[0] if timestamps else "",
                "latest": timestamps[-1] if timestamps else "",
                "snapshots": unique_snapshots[:100],
            }

            if include_content_hash:
                result["url_hash"] = hashlib.sha256(url.encode()).hexdigest()

            return result

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
