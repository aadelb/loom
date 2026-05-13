"""research_darkweb_early_warning — Monitor dark web for threat indicators."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.darkweb_early_warning")


async def _ahmia_search(
    client: httpx.AsyncClient, keyword: str
) -> list[dict[str, Any]]:
    """Search Ahmia for keyword mentions."""
    url = f"https://ahmia.fi/search/?q={quote(keyword)}&format=json"
    try:
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for result in data.get("results", [])[:5]:
                results.append(
                    {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "description": result.get("description", ""),
                    }
                )
            return results
    except Exception as exc:
        logger.debug("ahmia search failed: %s", exc)
    return []


async def _otx_search(client: httpx.AsyncClient, keyword: str) -> list[dict[str, Any]]:
    """Search AlienVault OTX for pulses."""
    url = f"https://otx.alienvault.com/api/v1/search/pulses?q={quote(keyword)}&limit=5"
    try:
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for pulse in data.get("results", [])[:5]:
                results.append(
                    {
                        "name": pulse.get("name", ""),
                        "description": pulse.get("description", ""),
                        "modified": pulse.get("modified", ""),
                    }
                )
            return results
    except Exception as exc:
        logger.debug("otx search failed: %s", exc)
    return []


async def _reddit_darknet_search(
    client: httpx.AsyncClient, keyword: str
) -> list[dict[str, Any]]:
    """Search Reddit r/darknet for recent posts."""
    url = (
        f"https://www.reddit.com/r/darknet/search.json?q={quote(keyword)}"
        f"&sort=new&limit=10"
    )
    try:
        resp = await client.get(
            url,
            headers={"User-Agent": "Loom-Research/1.0"},
            timeout=15.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for post in data.get("data", {}).get("children", [])[:5]:
                post_data = post.get("data", {})
                results.append(
                    {
                        "title": post_data.get("title", ""),
                        "url": post_data.get("url", ""),
                        "created_utc": post_data.get("created_utc", 0),
                    }
                )
            return results
    except Exception as exc:
        logger.debug("reddit darknet search failed: %s", exc)
    return []


async def _hackernews_search(
    client: httpx.AsyncClient, keyword: str
) -> list[dict[str, Any]]:
    """Search HackerNews via Algolia for stories."""
    url = (
        f"https://hn.algolia.com/api/v1/search_by_date?query={quote(keyword)}"
        f"&tags=story&hitsPerPage=5"
    )
    try:
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for hit in data.get("hits", [])[:5]:
                results.append(
                    {
                        "title": hit.get("title", ""),
                        "url": hit.get("url", ""),
                        "created_at": hit.get("created_at", ""),
                    }
                )
            return results
    except Exception as exc:
        logger.debug("hackernews search failed: %s", exc)
    return []


def _estimate_severity(keyword: str, mentions: int) -> str:
    """Estimate severity based on keyword and mention count.

    Args:
        keyword: Search keyword
        mentions: Number of mentions found

    Returns:
        Severity level: "critical", "high", "medium", "low"
    """
    # Critical keywords
    critical_keywords = [
        "exploit",
        "zero-day",
        "ransomware",
        "malware",
        "botnet",
        "stolen",
        "breach",
    ]

    keyword_lower = keyword.lower()
    for critical in critical_keywords:
        if critical in keyword_lower:
            if mentions >= 10:
                return "critical"
            elif mentions >= 5:
                return "high"

    # Mention count based severity
    if mentions >= 20:
        return "high"
    elif mentions >= 10:
        return "medium"
    elif mentions >= 5:
        return "medium"
    return "low"


@handle_tool_errors("research_darkweb_early_warning")
async def research_darkweb_early_warning(
    keywords: list[str], hours_back: int = 72
) -> dict[str, Any]:
    """Monitor dark web sources for early warning signals.

    Searches Ahmia, AlienVault OTX, Reddit r/darknet, and HackerNews
    for recent mentions of specified keywords. Returns aggregated alerts
    with severity assessment.

    Args:
        keywords: List of keywords to monitor (1-10)
        hours_back: Hours of historical data to consider (default 72)

    Returns:
        Dict with keywords, alerts (list of {keyword, source, title, url,
        severity, timestamp}), alert_count, and highest_severity
    """
    try:
        if not keywords:
            return {
                "error": "At least one keyword required",
                "keywords": [],
                "alerts": [],
                "alert_count": 0,
                "highest_severity": None,
            }

        if len(keywords) > 10:
            keywords = keywords[:10]

        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=30.0,
            ) as client:
                alerts: list[dict[str, Any]] = []
                severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
                highest_severity_val = 0
                highest_severity = None

                for keyword in keywords:
                    # Run all searches in parallel
                    ahmia_results, otx_results, reddit_results, hn_results = (
                        await asyncio.gather(
                            _ahmia_search(client, keyword),
                            _otx_search(client, keyword),
                            _reddit_darknet_search(client, keyword),
                            _hackernews_search(client, keyword),
                        )
                    )

                    # Process Ahmia results
                    for result in ahmia_results:
                        severity = _estimate_severity(keyword, 1)
                        alerts.append(
                            {
                                "keyword": keyword,
                                "source": "ahmia",
                                "title": result.get("title", ""),
                                "url": result.get("url", ""),
                                "severity": severity,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                        )
                        if severity_map.get(severity, 0) > highest_severity_val:
                            highest_severity_val = severity_map.get(severity, 0)
                            highest_severity = severity

                    # Process OTX results
                    for result in otx_results:
                        severity = _estimate_severity(keyword, 1)
                        alerts.append(
                            {
                                "keyword": keyword,
                                "source": "alienvault_otx",
                                "title": result.get("name", ""),
                                "url": "",
                                "severity": severity,
                                "timestamp": result.get("modified", ""),
                            }
                        )
                        if severity_map.get(severity, 0) > highest_severity_val:
                            highest_severity_val = severity_map.get(severity, 0)
                            highest_severity = severity

                    # Process Reddit results
                    for result in reddit_results:
                        created_ts = result.get("created_utc", 0)
                        created_dt = datetime.fromtimestamp(created_ts, timezone.utc).isoformat()
                        severity = _estimate_severity(keyword, 1)
                        alerts.append(
                            {
                                "keyword": keyword,
                                "source": "reddit_darknet",
                                "title": result.get("title", ""),
                                "url": result.get("url", ""),
                                "severity": severity,
                                "timestamp": created_dt,
                            }
                        )
                        if severity_map.get(severity, 0) > highest_severity_val:
                            highest_severity_val = severity_map.get(severity, 0)
                            highest_severity = severity

                    # Process HackerNews results
                    for result in hn_results:
                        severity = _estimate_severity(keyword, 1)
                        alerts.append(
                            {
                                "keyword": keyword,
                                "source": "hackernews",
                                "title": result.get("title", ""),
                                "url": result.get("url", ""),
                                "severity": severity,
                                "timestamp": result.get("created_at", ""),
                            }
                        )
                        if severity_map.get(severity, 0) > highest_severity_val:
                            highest_severity_val = severity_map.get(severity, 0)
                            highest_severity = severity

                # Compute per-keyword mention counts for severity
                keyword_mentions: dict[str, int] = {}
                for alert in alerts:
                    kw = alert["keyword"]
                    keyword_mentions[kw] = keyword_mentions.get(kw, 0) + 1

                # Re-score severity with actual mention counts
                highest_severity_val = 0
                highest_severity = None
                for alert in alerts:
                    severity = _estimate_severity(alert["keyword"], keyword_mentions.get(alert["keyword"], 1))
                    alert["severity"] = severity
                    if severity_map.get(severity, 0) > highest_severity_val:
                        highest_severity_val = severity_map.get(severity, 0)
                        highest_severity = severity

                return {
                    "keywords": keywords,
                    "alerts": alerts,
                    "alert_count": len(alerts),
                    "highest_severity": highest_severity,
                    "keyword_mention_counts": keyword_mentions,
                    "search_hours_back": hours_back,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_darkweb_early_warning"}
