"""Signal detection tools — Detect coordinated activity, temporal anomalies, and SEC filings."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.signal_detection")

# Public APIs
_HN_ALGOLIA = "https://hn.algolia.com/api/v1/search_by_date"
_REDDIT_SEARCH = "https://www.reddit.com/search.json"
_GITHUB_EVENTS = "https://api.github.com/events"
_GOOGLE_DOH = "https://dns.google/resolve"
_CRT_SH = "https://crt.sh/?q=%25.{domain}&output=json"
_SEC_EDGAR = "https://www.sec.gov/cgi-bin/browse-edgar"


async def _get_json(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0
) -> Any:
    """Fetch JSON from a URL."""
    try:
        resp = await client.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Loom-Research/1.0"},
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("signal_detection json fetch failed: %s", exc)
    return None


async def _get_text(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> str:
    """Fetch text from a URL."""
    try:
        resp = await client.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Loom-Research/1.0"},
        )
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("signal_detection text fetch failed: %s", exc)
    return ""


async def _search_github(
    client: httpx.AsyncClient, keyword: str
) -> list[dict[str, Any]]:
    """Search GitHub events for keyword matches."""
    try:
        data = await _get_json(client, _GITHUB_EVENTS, timeout=15.0)
        if not isinstance(data, list):
            return []

        events = []
        now = datetime.now(timezone.utc)
        keyword_lower = keyword.lower()

        for event in data[:100]:  # Limit to recent events
            # Check commit messages and repo names
            created = event.get("created_at", "")
            repo_name = event.get("repo", {}).get("name", "").lower()

            if keyword_lower in repo_name:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    events.append(
                        {
                            "platform": "GitHub",
                            "timestamp": created,
                            "seconds_ago": int((now - created_dt).total_seconds()),
                            "type": event.get("type", ""),
                            "repo": event.get("repo", {}).get("name", ""),
                        }
                    )
                except (ValueError, AttributeError):
                    pass
        return events
    except Exception as exc:
        logger.debug("github search failed: %s", exc)
        return []


async def _search_hackernews(
    client: httpx.AsyncClient, keyword: str
) -> list[dict[str, Any]]:
    """Search HackerNews for keyword matches."""
    url = f"{_HN_ALGOLIA}?query={quote(keyword)}&tags=story"
    data = await _get_json(client, url, timeout=15.0)
    if not isinstance(data, dict) or "hits" not in data:
        return []

    events = []
    now = datetime.now(timezone.utc)

    for hit in data.get("hits", [])[:50]:
        created_at = hit.get("created_at")
        if created_at:
            try:
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                events.append(
                    {
                        "platform": "HackerNews",
                        "timestamp": created_at,
                        "seconds_ago": int((now - created_dt).total_seconds()),
                        "title": hit.get("title", ""),
                        "url": hit.get("url", ""),
                    }
                )
            except (ValueError, AttributeError):
                pass
    return events


async def _search_reddit(
    client: httpx.AsyncClient, keyword: str
) -> list[dict[str, Any]]:
    """Search Reddit for keyword matches."""
    url = f"{_REDDIT_SEARCH}?q={quote(keyword)}&sort=new&limit=20"
    data = await _get_json(client, url, timeout=15.0)

    if not isinstance(data, dict) or "data" not in data:
        return []

    events = []
    now = datetime.now(timezone.utc)
    posts = data.get("data", {}).get("children", [])

    for post in posts:
        post_data = post.get("data", {})
        created = post_data.get("created_utc")

        if created:
            try:
                created_dt = datetime.fromtimestamp(created, tz=timezone.utc)
                events.append(
                    {
                        "platform": "Reddit",
                        "timestamp": created_dt.isoformat(),
                        "seconds_ago": int((now - created_dt).total_seconds()),
                        "title": post_data.get("title", ""),
                        "subreddit": post_data.get("subreddit", ""),
                        "score": post_data.get("score", 0),
                    }
                )
            except (ValueError, TypeError):
                pass
    return events


def research_ghost_protocol(
    keywords: list[str], time_window_minutes: int = 30
) -> dict[str, Any]:
    """Detect coordinated activity across platforms by checking temporal correlation.

    Searches GitHub Events, HackerNews (Algolia), and Reddit for keyword mentions
    within a time window. Events that occur across 2+ platforms within the window
    indicate potential coordination.

    Args:
        keywords: List of keywords to search for (e.g., ["breach", "vulnerability"])
        time_window_minutes: Time window in minutes to check for correlation (default: 30)

    Returns:
        Dict with keys:
          - keywords: input keywords
          - time_window_minutes: search window
          - platforms_checked: list of platforms (GitHub, HackerNews, Reddit)
          - clusters_found: list of coordinated event clusters
          - coordination_score: 0-100 indicating likelihood of coordination
          - total_events: total events found across all platforms
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            all_events: dict[str, list[dict[str, Any]]] = {
                "GitHub": [],
                "HackerNews": [],
                "Reddit": [],
            }

            # Search all platforms in parallel
            tasks = []
            for keyword in keywords:
                tasks.append(_search_github(client, keyword))
                tasks.append(_search_hackernews(client, keyword))
                tasks.append(_search_reddit(client, keyword))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Distribute results back to platforms
            idx = 0
            for keyword in keywords:
                for platform in ["GitHub", "HackerNews", "Reddit"]:
                    if idx < len(results) and isinstance(results[idx], list):
                        all_events[platform].extend(results[idx])
                    idx += 1

            # Find clusters: events within time_window on 2+ platforms
            window_seconds = time_window_minutes * 60
            clusters = []
            seen_clusters: set[str] = set()

            # Convert all timestamps to datetime for comparison
            timestamp_to_events: dict[str, list[dict[str, Any]]] = {}
            for platform, events in all_events.items():
                for event in events:
                    try:
                        ts = event.get("timestamp", "")
                        if ts not in timestamp_to_events:
                            timestamp_to_events[ts] = []
                        timestamp_to_events[ts].append(
                            {**event, "platform": platform}
                        )
                    except Exception:
                        pass

            # Find time-correlated events
            for ts, events in timestamp_to_events.items():
                if len(events) >= 2:
                    # Multiple platforms at same time = coordinated
                    platforms_in_cluster = {e["platform"] for e in events}
                    if len(platforms_in_cluster) >= 2:
                        cluster_hash = hashlib.sha256(
                            str(sorted(platforms_in_cluster)).encode()
                        ).hexdigest()[:8]
                        if cluster_hash not in seen_clusters:
                            seen_clusters.add(cluster_hash)
                            clusters.append(
                                {
                                    "platforms": sorted(list(platforms_in_cluster)),
                                    "events": events,
                                    "time_diff_seconds": 0,
                                    "count": len(events),
                                }
                            )

            # Fuzzy clustering: events within time_window
            flat_events = []
            for platform, events in all_events.items():
                flat_events.extend(
                    [
                        {**e, "platform": platform}
                        for e in events
                    ]
                )

            # Sort by timestamp
            try:
                flat_events_sorted = sorted(
                    flat_events,
                    key=lambda x: x.get("seconds_ago", float("inf")),
                )
            except Exception:
                flat_events_sorted = flat_events

            # Cluster nearby events
            for i, event in enumerate(flat_events_sorted):
                platform_set = {event["platform"]}
                time_window_cluster = [event]

                for j in range(i + 1, len(flat_events_sorted)):
                    other = flat_events_sorted[j]
                    seconds_diff = abs(
                        event.get("seconds_ago", 0)
                        - other.get("seconds_ago", 0)
                    )

                    if seconds_diff <= window_seconds:
                        platform_set.add(other["platform"])
                        time_window_cluster.append(other)

                if len(platform_set) >= 2:
                    cluster_hash = hashlib.sha256(
                        str(sorted(platform_set)).encode()
                    ).hexdigest()[:8]
                    if cluster_hash not in seen_clusters:
                        seen_clusters.add(cluster_hash)
                        clusters.append(
                            {
                                "platforms": sorted(list(platform_set)),
                                "events": time_window_cluster[:5],
                                "time_diff_seconds": max(
                                    [
                                        abs(
                                            time_window_cluster[0].get("seconds_ago", 0)
                                            - e.get("seconds_ago", 0)
                                        )
                                        for e in time_window_cluster
                                    ],
                                    default=0,
                                ),
                                "count": len(time_window_cluster),
                            }
                        )

            # Calculate coordination score (0-100)
            coordination_score = 0
            if clusters:
                coordination_score = min(100, len(clusters) * 25)

            return {
                "keywords": keywords,
                "time_window_minutes": time_window_minutes,
                "platforms_checked": ["GitHub", "HackerNews", "Reddit"],
                "clusters_found": clusters[:20],  # Limit to top 20
                "coordination_score": coordination_score,
                "total_events": len(flat_events),
            }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


async def _get_dns_changes(
    client: httpx.AsyncClient, domain: str
) -> dict[str, Any]:
    """Check DNS records via Google DoH."""
    records: dict[str, list[str]] = {}
    for rtype in ("A", "AAAA", "MX", "NS"):
        url = f"{_GOOGLE_DOH}?name={quote(domain)}&type={rtype}"
        data = await _get_json(client, url, timeout=10.0)
        if data and "Answer" in data:
            records[rtype] = [a.get("data", "") for a in data["Answer"]]
    return records


async def _get_cert_timing(
    client: httpx.AsyncClient, domain: str
) -> list[dict[str, Any]]:
    """Get SSL certificate issuance times from crt.sh."""
    url = _CRT_SH.format(domain=domain)
    data = await _get_json(client, url, timeout=30.0)

    if not isinstance(data, list):
        return []

    certs = []
    for entry in data[:50]:
        not_before = entry.get("not_before")
        if not_before:
            try:
                # Parse ISO format timestamp
                cert_dt = datetime.fromisoformat(
                    not_before.replace("Z", "+00:00")
                )
                # Check if issued on weekend or holiday-like times
                weekday = cert_dt.weekday()
                hour = cert_dt.hour

                anomalies = []
                if weekday >= 5:  # Saturday (5) or Sunday (6)
                    anomalies.append("weekend_issuance")
                if hour < 6 or hour > 22:  # Off-hours
                    anomalies.append("off_hours")

                certs.append(
                    {
                        "timestamp": not_before,
                        "weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][
                            weekday
                        ],
                        "hour": hour,
                        "anomalies": anomalies,
                    }
                )
            except (ValueError, AttributeError):
                pass

    return certs


async def _check_server_clock_skew(
    client: httpx.AsyncClient, domain: str
) -> int:
    """Check for clock skew between server and local time."""
    url = f"https://{domain}/"
    try:
        resp = await client.head(
            url, timeout=10.0, follow_redirects=False
        )
        server_date = resp.headers.get("date", "")
        if server_date:
            try:
                server_dt = datetime.fromisoformat(
                    server_date.replace("GMT", "+00:00")
                    .replace("UTC", "+00:00")
                )
                local_dt = datetime.now(timezone.utc)
                skew_ms = int(abs((server_dt - local_dt).total_seconds() * 1000))
                return skew_ms
            except (ValueError, AttributeError):
                pass
    except Exception as exc:
        logger.debug("clock_skew check failed: %s", exc)
    return 0


def research_temporal_anomaly(
    domain: str, check_type: str = "all"
) -> dict[str, Any]:
    """Detect temporal anomalies in a domain's infrastructure.

    Checks:
    - SSL certificate issuance at unusual times (weekends, off-hours)
    - DNS record changes via Google DoH
    - Server clock skew (Date header vs actual time)

    Args:
        domain: Target domain (e.g. "example.com")
        check_type: Type of checks to run ("all", "certs", "dns", "clock")

    Returns:
        Dict with keys:
          - domain: target domain
          - anomalies_found: list of detected anomalies
          - clock_skew_ms: detected clock skew in milliseconds
          - cert_timing_anomalies: list of unusual cert issuances
          - dns_records: DNS A/AAAA/MX/NS records
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            tasks = []
            results_map: dict[str, Any] = {}

            if check_type in ("all", "certs"):
                tasks.append(("certs", _get_cert_timing(client, domain)))
            if check_type in ("all", "dns"):
                tasks.append(("dns", _get_dns_changes(client, domain)))
            if check_type in ("all", "clock"):
                tasks.append(("clock", _check_server_clock_skew(client, domain)))

            task_names = [t[0] for t in tasks]
            task_coros = [t[1] for t in tasks]

            results = await asyncio.gather(*task_coros, return_exceptions=True)

            for name, result in zip(task_names, results):
                if not isinstance(result, Exception):
                    results_map[name] = result

            anomalies = []
            cert_anomalies = results_map.get("certs", [])
            if cert_anomalies:
                for cert in cert_anomalies:
                    if cert.get("anomalies"):
                        anomalies.extend(
                            [
                                {
                                    "type": "cert_timing",
                                    "description": f"{cert['anomaly']} at {cert['timestamp']}",
                                    "severity": "medium",
                                }
                                for cert_anom in cert.get("anomalies", [])
                                for anomaly in [cert_anom]
                            ]
                        )

            # Deduplicate
            seen = set()
            unique_anomalies = []
            for anom in anomalies:
                key = (anom.get("type"), anom.get("description"))
                if key not in seen:
                    seen.add(key)
                    unique_anomalies.append(anom)

            return {
                "domain": domain,
                "anomalies_found": unique_anomalies[:20],
                "clock_skew_ms": results_map.get("clock", 0),
                "cert_timing_anomalies": cert_anomalies[:10],
                "dns_records": results_map.get("dns", {}),
            }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


def research_sec_tracker(
    company: str, filing_types: list[str] | None = None
) -> dict[str, Any]:
    """Track SEC filings for a company over the past 90 days.

    Uses SEC EDGAR database to retrieve recent filings by type.
    Defaults to 10-K, 10-Q, 8-K if no filing types specified.

    Args:
        company: Company name or CIK number (e.g., "Apple Inc" or "0000789019")
        filing_types: List of filing types to filter (e.g., ["10-K", "10-Q", "8-K"])

    Returns:
        Dict with keys:
          - company: input company name
          - filings_found: total count of filings
          - recent_filings: list of recent filings with details
          - filing_velocity: filings per 30-day period
          - lookback_days: number of days searched
    """

    async def _run() -> dict[str, Any]:
        default_types = filing_types or ["10-K", "10-Q", "8-K"]

        # SEC EDGAR search endpoint
        # Using CSV output format for easier parsing
        search_url = f"{_SEC_EDGAR}?action=getcompany&company={quote(company)}&output=csv"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                resp = await client.get(search_url, timeout=20.0)
                if resp.status_code != 200:
                    return {
                        "company": company,
                        "filings_found": 0,
                        "recent_filings": [],
                        "filing_velocity": 0,
                        "lookback_days": 90,
                        "error": f"SEC EDGAR returned {resp.status_code}",
                    }

                lines = resp.text.splitlines()
                if len(lines) < 2:
                    return {
                        "company": company,
                        "filings_found": 0,
                        "recent_filings": [],
                        "filing_velocity": 0,
                        "lookback_days": 90,
                        "note": "No matching companies found",
                    }

                # Parse CSV
                filings = []
                now = datetime.now(timezone.utc)
                ninety_days_ago = now - timedelta(days=90)

                for line in lines[1:]:  # Skip header
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 5:
                        try:
                            filing_type = parts[1]
                            filing_date = parts[3]

                            # Check if matches requested types and is recent
                            if any(t.strip() == filing_type for t in default_types):
                                try:
                                    filing_dt = datetime.strptime(
                                        filing_date, "%Y-%m-%d"
                                    ).replace(tzinfo=timezone.utc)
                                    if filing_dt >= ninety_days_ago:
                                        filings.append(
                                            {
                                                "type": filing_type,
                                                "date": filing_date,
                                                "accession": parts[4] if len(parts) > 4 else "",
                                                "url": f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={quote(company)}&accession_number={parts[4]}&xbrl_type=v"
                                                if len(parts) > 4
                                                else "",
                                            }
                                        )
                                except ValueError:
                                    pass
                        except (IndexError, ValueError):
                            pass

                # Sort by date descending
                filings.sort(
                    key=lambda x: x.get("date", ""), reverse=True
                )

                # Calculate velocity
                filing_velocity = len(filings) / 3 if filings else 0  # per 30 days

                return {
                    "company": company,
                    "filings_found": len(filings),
                    "recent_filings": filings[:50],
                    "filing_velocity": round(filing_velocity, 2),
                    "lookback_days": 90,
                }

            except Exception as exc:
                logger.debug("sec_tracker fetch failed: %s", exc)
                return {
                    "company": company,
                    "filings_found": 0,
                    "recent_filings": [],
                    "filing_velocity": 0,
                    "lookback_days": 90,
                    "error": str(exc),
                }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
