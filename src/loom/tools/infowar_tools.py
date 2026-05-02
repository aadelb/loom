"""Information warfare research tools — narrative tracking, bot detection, censorship analysis, social recovery, and robots.txt archaeology."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.parse import quote, urlparse

import httpx

logger = logging.getLogger("loom.tools.infowar_tools")

_HN_ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
_REDDIT_API = "https://www.reddit.com"
_ARXIV_API = "https://export.arxiv.org/api/query"
_LUMEN_DATABASE = "https://lumendatabase.org/notices/search.json"
_WAYBACK_CDX = "https://web.archive.org/cdx/search/cdx"
_GOOGLE_CACHE = "https://webcache.googleusercontent.com/search"

# DNS over HTTPS (DoH) endpoints
_GOOGLE_DOH = "https://dns.google/resolve"
_CLOUDFLARE_DOH = "https://cloudflare-dns.com/dns-query"
_QUAD9_DOH = "https://dns.quad9.net/dns-query"


async def _fetch_json(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0, **kwargs: Any
) -> Any:
    """Fetch JSON with error handling."""
    try:
        resp = await client.get(url, timeout=timeout, **kwargs)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("infowar_tools fetch failed url=%s: %s", url[:80], exc)
    return None


async def _fetch_text(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0, **kwargs: Any
) -> str:
    """Fetch text with error handling."""
    try:
        resp = await client.get(url, timeout=timeout, **kwargs)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("infowar_tools text fetch failed url=%s: %s", url[:80], exc)
    return ""


async def _hn_search(
    client: httpx.AsyncClient, query: str, hours_back: int
) -> list[dict[str, Any]]:
    """Search Hacker News via Algolia API."""
    try:
        # Search for posts in the last N hours
        search_query = f"{query} created_at > now-{hours_back}h"
        params = {
            "query": search_query,
            "tags": "story",
            "numericFilters": f"created_at>{int((asyncio.get_event_loop().time() - hours_back * 3600))}",
        }
        data = await _fetch_json(client, _HN_ALGOLIA_SEARCH, timeout=15.0, params=params)
        if data and "hits" in data:
            return [
                {
                    "platform": "hn",
                    "title": hit.get("title", ""),
                    "url": hit.get("url", ""),
                    "author": hit.get("author", ""),
                    "timestamp": hit.get("created_at", ""),
                    "score": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                }
                for hit in data["hits"][:20]
            ]
    except Exception as exc:
        logger.debug("hn_search failed: %s", exc)
    return []


async def _reddit_search(
    client: httpx.AsyncClient, query: str, hours_back: int
) -> list[dict[str, Any]]:
    """Search Reddit via Pushshift API or Reddit API."""
    try:
        # Try Pushshift-style endpoint (check if available)
        url = f"https://api.pushshift.io/reddit/search/submission"
        params = {
            "q": query,
            "after": f"{int((asyncio.get_event_loop().time() - hours_back * 3600))}",
            "sort": "desc",
            "size": 20,
        }
        data = await _fetch_json(client, url, timeout=15.0, params=params)
        if data and "data" in data:
            return [
                {
                    "platform": "reddit",
                    "title": post.get("title", ""),
                    "url": post.get("full_link", ""),
                    "author": post.get("author", ""),
                    "timestamp": post.get("created_utc", ""),
                    "score": post.get("score", 0),
                    "comments": post.get("num_comments", 0),
                    "subreddit": post.get("subreddit", ""),
                }
                for post in data["data"][:20]
            ]
    except Exception as exc:
        logger.debug("reddit_search failed: %s", exc)
    return []


async def _arxiv_search(
    client: httpx.AsyncClient, query: str, hours_back: int
) -> list[dict[str, Any]]:
    """Search arXiv for recent papers."""
    try:
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": 20,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        text = await _fetch_text(client, _ARXIV_API, timeout=15.0, params=params)
        if not text:
            return []

        # Simple XML parsing for arXiv
        results = []
        entries = text.split("<entry>")[1:]
        for entry in entries:
            try:
                title_start = entry.find("<title>") + 7
                title_end = entry.find("</title>")
                title = entry[title_start:title_end].strip() if title_end > title_start else ""

                author_start = entry.find("<author>")
                author_end = entry.find("</author>")
                author = ""
                if author_end > author_start:
                    name_start = entry.find("<name>", author_start) + 6
                    name_end = entry.find("</name>", author_start)
                    author = entry[name_start:name_end].strip() if name_end > name_start else ""

                published_start = entry.find("<published>") + 11
                published_end = entry.find("</published>")
                published = entry[published_start:published_end].strip() if published_end > published_start else ""

                id_start = entry.find("<id>") + 4
                id_end = entry.find("</id>")
                arxiv_id = entry[id_start:id_end].strip() if id_end > id_start else ""

                if title and arxiv_id:
                    results.append(
                        {
                            "platform": "arxiv",
                            "title": title,
                            "url": f"https://arxiv.org/abs/{arxiv_id.split('/abs/')[-1]}",
                            "author": author,
                            "timestamp": published,
                        }
                    )
            except Exception as e:
                logger.debug("arxiv_entry_parse_error: %s", e)
                continue
        return results[:20]
    except Exception as exc:
        logger.debug("arxiv_search failed: %s", exc)
    return []


async def research_narrative_tracker(topic: str, hours_back: int = 72) -> dict[str, Any]:
    """Track narrative propagation across platforms.

    Searches HN Algolia, Reddit, arXiv, and constructs timeline showing
    when the topic emerged, velocity of posts, and cross-platform reach.

    Args:
        topic: narrative topic to track (e.g., "AI safety", "XYZ vulnerability")
        hours_back: how many hours back to search (default 72)

    Returns:
        Dict with ``topic``, ``timeline`` list with (timestamp, platform, count),
        ``velocity`` (posts/hour), ``reach`` (unique platforms), ``total_posts``,
        and ``platforms`` dict keyed by platform name.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0 (academic research)"},
        ) as client:
            tasks = [
                _hn_search(client, topic, hours_back),
                _reddit_search(client, topic, hours_back),
                _arxiv_search(client, topic, hours_back),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            hn_posts = results[0] if isinstance(results[0], list) else []
            reddit_posts = results[1] if isinstance(results[1], list) else []
            arxiv_posts = results[2] if isinstance(results[2], list) else []

            all_posts = hn_posts + reddit_posts + arxiv_posts

            # Build timeline
            timeline_map: dict[str, dict[str, int]] = {}
            for post in all_posts:
                ts = post.get("timestamp", "")
                if ts:
                    # Round to hour
                    hour = ts[:13] if len(ts) >= 13 else ts[:10]
                    platform = post.get("platform", "unknown")
                    if hour not in timeline_map:
                        timeline_map[hour] = {}
                    if platform not in timeline_map[hour]:
                        timeline_map[hour][platform] = 0
                    timeline_map[hour][platform] += 1

            timeline = [
                {"timestamp": ts, "counts": counts}
                for ts, counts in sorted(timeline_map.items())
            ]

            # Calculate velocity
            velocity = len(all_posts) / max(hours_back, 1)

            # Reach
            reach = len(set(p.get("platform", "") for p in all_posts))

            return {
                "topic": topic,
                "hours_back": hours_back,
                "total_posts": len(all_posts),
                "velocity_posts_per_hour": round(velocity, 2),
                "reach_platforms": reach,
                "timeline": timeline[:100],
                "platforms": {
                    "hn": len(hn_posts),
                    "reddit": len(reddit_posts),
                    "arxiv": len(arxiv_posts),
                },
                "top_posts": sorted(all_posts, key=lambda p: p.get("score", 0), reverse=True)[:10],
            }

    return await _run()


async def _analyze_posting_times(
    posts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Detect coordinated posting patterns."""
    timestamps = []
    authors = set()
    for post in posts:
        ts = post.get("timestamp", "")
        author = post.get("author", "")
        if ts and author:
            timestamps.append((ts, author))
            authors.add(author)

    # Simple clustering: find timestamps within 5 minutes of each other
    suspicious_clusters: list[list[dict[str, Any]]] = []
    if timestamps:
        timestamps.sort()
        current_cluster: list[dict[str, Any]] = []
        cluster_start_time = timestamps[0][0] if timestamps else ""

        for ts, author in timestamps:
            # Simple time diff check (5 min window)
            if cluster_start_time and ts:
                try:
                    # Parse ISO format times
                    import datetime

                    t1 = datetime.datetime.fromisoformat(cluster_start_time.replace("Z", "+00:00"))
                    t2 = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    diff = (t2 - t1).total_seconds()
                    if diff <= 300:  # 5 minutes
                        current_cluster.append({"timestamp": ts, "author": author})
                    else:
                        if len(current_cluster) >= 3:
                            suspicious_clusters.append(current_cluster)
                        current_cluster = [{"timestamp": ts, "author": author}]
                        cluster_start_time = ts
                except Exception as e:
                    logger.debug("timestamp_parse_error: %s", e)

        if len(current_cluster) >= 3:
            suspicious_clusters.append(current_cluster)

    # Word overlap analysis
    all_words: dict[str, int] = {}
    for post in posts:
        content = (post.get("title", "") + " " + post.get("url", "")).lower().split()
        for word in content:
            if len(word) > 3:  # Filter out common short words
                all_words[word] = all_words.get(word, 0) + 1

    # Find common words across posts (> 30% overlap)
    overlap_threshold = len(posts) * 0.3
    common_words = {w: c for w, c in all_words.items() if c > overlap_threshold}

    coordination_score = min(len(suspicious_clusters) * 10 + len(common_words) * 5, 100)

    return {
        "suspicious_clusters": len(suspicious_clusters),
        "cluster_details": [
            {
                "size": len(cluster),
                "authors": len(set(c["author"] for c in cluster)),
                "time_window_minutes": 5,
            }
            for cluster in suspicious_clusters[:10]
        ],
        "content_similarity_common_words": len(common_words),
        "coordination_score": coordination_score,
    }


async def research_bot_detector(subreddit: str = "", hn_query: str = "") -> dict[str, Any]:
    """Detect coordinated bot/spam behavior on social platforms.

    Analyzes posting patterns (timestamps within 5 min), content similarity
    (word overlap >30%), and author clustering to detect coordination.

    Args:
        subreddit: subreddit to analyze (e.g., "programming")
        hn_query: HN query to analyze (e.g., "AI safety")

    Returns:
        Dict with ``accounts_analyzed``, ``suspicious_clusters``,
        ``coordination_score`` (0-100), and ``cluster_details``.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            posts: list[dict[str, Any]] = []
            accounts_analyzed = 0

            if subreddit:
                reddit_posts = await _reddit_search(client, subreddit, 24)
                posts.extend(reddit_posts)
                accounts_analyzed += len(set(p.get("author", "") for p in reddit_posts))

            if hn_query:
                hn_posts = await _hn_search(client, hn_query, 24)
                posts.extend(hn_posts)
                accounts_analyzed += len(set(p.get("author", "") for p in hn_posts))

            if not posts:
                return {
                    "accounts_analyzed": 0,
                    "posts_analyzed": 0,
                    "suspicious_clusters": 0,
                    "coordination_score": 0,
                    "cluster_details": [],
                }

            analysis = await _analyze_posting_times(posts)

            return {
                "accounts_analyzed": accounts_analyzed,
                "posts_analyzed": len(posts),
                "subreddit": subreddit,
                "hn_query": hn_query,
                "suspicious_clusters": analysis["suspicious_clusters"],
                "coordination_score": analysis["coordination_score"],
                "content_similarity_words": analysis["content_similarity_common_words"],
                "cluster_details": analysis["cluster_details"],
            }

    return await _run()


async def _dns_lookup_doh(
    client: httpx.AsyncClient, domain: str, doh_endpoint: str
) -> dict[str, Any]:
    """Lookup DNS via DoH endpoint."""
    try:
        if "google" in doh_endpoint:
            url = doh_endpoint
            params = {"name": domain, "type": "A"}
            data = await _fetch_json(client, url, timeout=10.0, params=params)
            if data and "Answer" in data:
                return {
                    "provider": "google",
                    "answers": [a.get("data", "") for a in data["Answer"]],
                    "status": "resolved",
                }
        elif "cloudflare" in doh_endpoint:
            url = doh_endpoint
            params = {"name": domain, "type": "A"}
            headers = {"accept": "application/dns-json"}
            data = await _fetch_json(
                client, url, timeout=10.0, params=params, headers=headers
            )
            if data and "Answer" in data:
                return {
                    "provider": "cloudflare",
                    "answers": [a.get("data", "") for a in data["Answer"]],
                    "status": "resolved",
                }
        elif "quad9" in doh_endpoint:
            url = doh_endpoint
            params = {"name": domain, "type": "A"}
            headers = {"accept": "application/dns-json"}
            data = await _fetch_json(
                client, url, timeout=10.0, params=params, headers=headers
            )
            if data and "Answer" in data:
                return {
                    "provider": "quad9",
                    "answers": [a.get("data", "") for a in data["Answer"]],
                    "status": "resolved",
                }
    except Exception as exc:
        logger.debug("dns_lookup_doh failed for %s: %s", domain, exc)

    return {"provider": doh_endpoint.split("/")[2], "status": "failed"}


async def _lumen_database_check(
    client: httpx.AsyncClient, domain: str
) -> list[dict[str, Any]]:
    """Check Lumen Database for takedown notices."""
    try:
        params = {"term": domain}
        data = await _fetch_json(client, _LUMEN_DATABASE, timeout=15.0, params=params)
        if data and "notices" in data:
            return [
                {
                    "notice_id": notice.get("id", ""),
                    "title": notice.get("title", ""),
                    "sender": notice.get("sender", ""),
                    "date_sent": notice.get("date_sent", ""),
                    "reason": notice.get("action_taken", ""),
                }
                for notice in data["notices"][:10]
            ]
    except Exception as exc:
        logger.debug("lumen_database_check failed: %s", exc)
    return []


async def research_censorship_detector(url: str) -> dict[str, Any]:
    """Detect DNS censorship and takedown notices.

    Queries DNS over HTTPS (Google, Cloudflare, Quad9) to detect
    inconsistent resolution (sign of censorship). Checks Lumen Database
    for DMCA/legal takedown notices.

    Args:
        url: URL to analyze for censorship (e.g., "example.com")

    Returns:
        Dict with ``url``, ``dns_consistent`` (bool), ``blocked_providers`` list,
        ``takedown_notices`` count, and ``notices`` list.
    """

    async def _run() -> dict[str, Any]:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split("/")[0]

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            # DNS lookups in parallel
            dns_tasks = [
                _dns_lookup_doh(client, domain, _GOOGLE_DOH),
                _dns_lookup_doh(client, domain, _CLOUDFLARE_DOH),
                _dns_lookup_doh(client, domain, _QUAD9_DOH),
            ]
            dns_results = await asyncio.gather(*dns_tasks, return_exceptions=True)

            # Lumen Database check
            notices = await _lumen_database_check(client, domain)

            # Analyze DNS consistency
            resolved_ips: dict[str, set[str]] = {}
            for result in dns_results:
                if isinstance(result, dict) and result.get("status") == "resolved":
                    provider = result.get("provider", "unknown")
                    answers = result.get("answers", [])
                    resolved_ips[provider] = set(answers)

            # Check consistency
            dns_consistent = True
            blocked_providers = []
            if resolved_ips:
                first_ips = next(iter(resolved_ips.values()))
                for provider, ips in resolved_ips.items():
                    if ips != first_ips:
                        dns_consistent = False
                        if not ips or "NXDOMAIN" in str(ips):
                            blocked_providers.append(provider)

            return {
                "url": url,
                "domain": domain,
                "dns_consistent": dns_consistent,
                "dns_providers_checked": 3,
                "blocked_providers": blocked_providers,
                "dns_results": {
                    provider: list(ips) for provider, ips in resolved_ips.items()
                },
                "takedown_notices_found": len(notices),
                "notices": notices,
            }

    return await _run()


async def _wayback_search_social(
    client: httpx.AsyncClient, url: str, platform: str
) -> list[dict[str, Any]]:
    """Search Wayback Machine for social media URLs."""
    try:
        cdx_url = _WAYBACK_CDX
        params = {
            "url": url,
            "output": "json",
            "fl": "timestamp,original,statuscode",
            "filter": "statuscode:200",
            "limit": 50,
        }
        data = await _fetch_json(client, cdx_url, timeout=30.0, params=params)
        if data and len(data) > 1:
            snapshots = []
            for row in data[1:]:
                try:
                    snapshots.append(
                        {
                            "timestamp": row[0] if len(row) > 0 else "",
                            "url": row[1] if len(row) > 1 else "",
                            "archive_url": f"https://web.archive.org/web/{row[0]}/{url}"
                            if len(row) > 0
                            else "",
                            "status": row[2] if len(row) > 2 else "",
                        }
                    )
                except Exception as e:
                    logger.debug("wayback_snapshot_parse_error: %s", e)
            return snapshots
    except Exception as exc:
        logger.debug("wayback_search_social failed: %s", exc)
    return []


async def research_deleted_social(url: str) -> dict[str, Any]:
    """Recover deleted social media content from archives.

    Searches Wayback Machine CDX for deleted tweets, Reddit posts, or YouTube videos.
    Returns snapshots with timestamps and recovery links.

    Args:
        url: URL to deleted social content (e.g., twitter.com/user/status/123)

    Returns:
        Dict with ``url``, ``platform`` (detected), ``snapshots_found``,
        and ``recovered_content_preview`` (list of snapshots).
    """

    async def _run() -> dict[str, Any]:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Detect platform
        platform = "unknown"
        if "twitter.com" in domain or "x.com" in domain:
            platform = "twitter"
        elif "reddit.com" in domain:
            platform = "reddit"
        elif "youtube.com" in domain or "youtu.be" in domain:
            platform = "youtube"
        elif "tiktok.com" in domain:
            platform = "tiktok"
        elif "instagram.com" in domain:
            platform = "instagram"
        elif "facebook.com" in domain:
            platform = "facebook"

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            wayback_snapshots = await _wayback_search_social(client, url, platform)

            # Try Google Cache as fallback
            google_cache_url = f"{_GOOGLE_CACHE}?q=cache:{quote(url, safe='')}"
            google_status = 0
            try:
                resp = await client.head(google_cache_url, timeout=15.0)
                google_status = resp.status_code
            except Exception as e:
                logger.debug("google_cache_check_error: %s", e)

            snapshots_found = len(wayback_snapshots)
            if google_status == 200:
                snapshots_found += 1

            return {
                "url": url,
                "platform": platform,
                "snapshots_found": snapshots_found,
                "wayback_snapshots": len(wayback_snapshots),
                "google_cache_available": google_status == 200,
                "recovered_content_preview": wayback_snapshots[:20],
            }

    return await _run()


async def _robots_txt_cdx(
    client: httpx.AsyncClient, domain: str, snapshots: int
) -> list[dict[str, Any]]:
    """Fetch historical robots.txt versions from Wayback Machine."""
    try:
        robots_url = f"{domain}/robots.txt"
        cdx_url = _WAYBACK_CDX
        params = {
            "url": robots_url,
            "output": "json",
            "fl": "timestamp,original,statuscode",
            "filter": "statuscode:200",
            "limit": snapshots,
        }
        data = await _fetch_json(client, cdx_url, timeout=30.0, params=params)
        if data and len(data) > 1:
            versions = []
            for row in data[1:]:
                try:
                    ts = row[0] if len(row) > 0 else ""
                    archive_url = f"https://web.archive.org/web/{ts}/{robots_url}" if ts else ""
                    versions.append(
                        {
                            "timestamp": ts,
                            "archive_url": archive_url,
                            "status": row[2] if len(row) > 2 else "",
                        }
                    )
                except Exception as e:
                    logger.debug("robots_version_parse_error: %s", e)
            return versions
    except Exception as exc:
        logger.debug("robots_txt_cdx failed: %s", exc)
    return []


async def _robots_txt_content(
    client: httpx.AsyncClient, archive_url: str
) -> str:
    """Fetch actual robots.txt content from archive."""
    try:
        return await _fetch_text(client, archive_url, timeout=15.0)
    except Exception as e:
        logger.debug("robots_txt_fetch_error: %s", e)
        return ""


def _diff_robots_rules(
    old_content: str, new_content: str
) -> tuple[list[str], list[str]]:
    """Diff robots.txt versions."""
    old_rules = set(line.strip() for line in old_content.split("\n") if line.strip())
    new_rules = set(line.strip() for line in new_content.split("\n") if line.strip())

    added = sorted(new_rules - old_rules)
    removed = sorted(old_rules - new_rules)

    return added, removed


async def research_robots_archaeology(domain: str, snapshots: int = 10) -> dict[str, Any]:
    """Analyze historical robots.txt changes to find hidden paths.

    Fetches historical robots.txt versions from Wayback Machine CDX,
    diffs consecutive versions to track Disallow/Allow rule changes,
    and identifies paths that were hidden then revealed.

    Args:
        domain: domain to analyze (e.g., "example.com")
        snapshots: number of historical versions to fetch (default 10)

    Returns:
        Dict with ``domain``, ``versions_found``, and ``changes`` list with
        {date, added_rules, removed_rules, hidden_paths_timeline}.
    """

    async def _run() -> dict[str, Any]:
        if not domain.startswith("http"):
            domain_url = f"https://{domain}"
        else:
            domain_url = domain

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            versions = await _robots_txt_cdx(client, domain_url, snapshots)

            if not versions:
                return {
                    "domain": domain,
                    "versions_found": 0,
                    "changes": [],
                    "hidden_paths_timeline": [],
                }

            # Fetch content for each version
            content_tasks = [
                _robots_txt_content(client, v["archive_url"]) for v in versions
            ]
            contents = await asyncio.gather(*content_tasks, return_exceptions=True)

            # Build timeline of changes
            changes = []
            hidden_paths_timeline: dict[str, list[str]] = {}

            prev_content = ""
            for i, version in enumerate(versions):
                current_content = (
                    contents[i] if i < len(contents) and isinstance(contents[i], str) else ""
                )
                if current_content:
                    if prev_content:
                        added, removed = _diff_robots_rules(prev_content, current_content)
                    else:
                        added = current_content.split("\n")
                        removed = []

                    # Track hidden paths (Disallow rules that appear)
                    disallow_rules = [
                        line.split(":")[-1].strip()
                        for line in current_content.split("\n")
                        if line.lower().startswith("disallow:")
                    ]

                    ts = version.get("timestamp", "")
                    changes.append(
                        {
                            "date": ts,
                            "archive_url": version.get("archive_url", ""),
                            "added_rules": added,
                            "removed_rules": removed,
                            "disallow_count": len(disallow_rules),
                        }
                    )
                    if ts:
                        hidden_paths_timeline[ts] = disallow_rules

                    prev_content = current_content

            # Identify paths that appeared then disappeared
            all_hidden_paths: dict[str, list[str]] = {}
            for ts, paths in hidden_paths_timeline.items():
                for path in paths:
                    if path:
                        if path not in all_hidden_paths:
                            all_hidden_paths[path] = []
                        all_hidden_paths[path].append(ts)

            return {
                "domain": domain,
                "versions_found": len(versions),
                "snapshots_analyzed": len(
                    [c for c in contents if isinstance(c, str) and c]
                ),
                "changes": changes[:50],
                "hidden_paths_timeline": all_hidden_paths,
            }

    return await _run()
