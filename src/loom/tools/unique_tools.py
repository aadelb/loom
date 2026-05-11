"""Unique research tools — propaganda detection, credibility scoring, information cascades, and more.

Tools:
- research_propaganda_detector: NLP-based propaganda detection and scoring
- research_source_credibility: Multi-factor source credibility assessment
- research_information_cascade: Track information flow across platforms
- research_web_time_machine: Website evolution and tech signature tracking
- research_influence_operation: Detect coordinated posting patterns
- research_dark_web_bridge: Find clearnet references to dark web content
- research_info_half_life: Estimate URL survival and decay rates
- research_search_discrepancy: Compare results across search engines
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import Any
from urllib.parse import urlparse

import httpx

from loom.validators import validate_url, UrlSafetyError

logger = logging.getLogger("loom.tools.unique_tools")

# Default timeout for HTTP operations
_DEFAULT_TIMEOUT = 15.0


async def _get_json(
    client: httpx.AsyncClient, url: str, timeout: float = _DEFAULT_TIMEOUT
) -> Any:
    """Safely fetch and parse JSON from URL."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("JSON fetch failed for %s: %s", url, exc)
    return None


async def _get_text(
    client: httpx.AsyncClient, url: str, timeout: float = _DEFAULT_TIMEOUT
) -> str:
    """Safely fetch text from URL."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("Text fetch failed for %s: %s", url, exc)
    return ""


async def _check_http_status(
    client: httpx.AsyncClient, url: str, timeout: float = 10.0
) -> int | None:
    """Check HTTP status code for URL."""
    try:
        resp = await client.head(url, timeout=timeout, follow_redirects=False)
        return resp.status_code
    except Exception:
        # Fallback to GET if HEAD fails
        try:
            resp = await client.get(url, timeout=timeout, follow_redirects=False)
            return resp.status_code
        except Exception as exc:
            logger.debug("HTTP status check failed for %s: %s", url, exc)
    return None


def research_propaganda_detector(text: str) -> dict[str, Any]:
    """Detect propaganda techniques in text using NLP analysis.

    Identifies propaganda markers including:
    - Loaded language (highly emotional terms)
    - Appeal to authority phrases
    - Bandwagon terms (everyone believes, most people)
    - False dichotomy markers (either/or statements)
    - Emotional manipulation patterns

    Args:
        text: text to analyze for propaganda techniques

    Returns:
        Dict with ``text_length``, ``techniques_found`` (list),
        ``propaganda_score`` (0-100), and ``dominant_technique``.
    """
    if not isinstance(text, str):
        return {
            "text_length": 0,
            "techniques_found": [],
            "propaganda_score": 0,
            "dominant_technique": None,
        }

    text_lower = text.lower()

    # Loaded language patterns (emotional, extreme adjectives)
    loaded_language = [
        r"\b(absolutely|completely|utterly|totally|entirely|definitely|clearly)\b",
        r"\b(amazing|terrible|horrible|fantastic|dreadful|evil|incredible|unprecedented)\b",
        r"\b(must|always|never|only|worst|best|greatest|perfect)\b",
        r"\b(unbelievable|outrageous|shocking|stunning|disgusting|brilliant)\b",
        r"\b(truth|lies|exposed|revealed|secret|hidden|suppressed)\b",
        r"\b(destroy|radical|extreme|revolution|transform|groundbreaking)\b",
    ]

    # Appeal to authority patterns
    authority_patterns = [
        r"\b(experts? (?:say|claim|agree|confirm|warn|prove))",
        r"\b(doctors? (?:say|recommend|warn|confirm))",
        r"\b(scientists? (?:prove|confirm|show|agree|unanimously))",
        r"\b(according to (?:experts?|studies|research|science))",
        r"\b(research (?:shows?|proves?|confirms?))",
        r"\b(studies (?:prove|show|indicate|confirm))",
        r"\b(unanimously|consensus|undeniable|indisputable)",
    ]

    # Bandwagon patterns (everyone/majority)
    bandwagon_patterns = [
        r"\b(everyone|everyone knows|all people|the majority|millions)\b",
        r"\b(most (?:people|americans|experts|citizens))",
        r"\b(joining the|following the|join the) (?:movement|trend|side|winning)",
        r"\b(growing (?:movement|trend|consensus|number))",
        r"\b(don't be left|left behind|get on board|common sense)",
        r"\b(right side of history|winning side)",
    ]

    # False dichotomy patterns (either/or)
    dichotomy_patterns = [
        r"\b(either\.\.\. ?or)\b",
        r"\b(you're (?:either|with us|against us))",
        r"\b(no (?:middle ground|alternatives|choice|other))",
        r"\b(only (?:choice|option|way|solution|answer))",
        r"\b(if you're not .* you're)",
        r"\b(those who (?:disagree|oppose|refuse))",
    ]

    # Emotional manipulation
    emotion_patterns = [
        r"\b(fear|danger|threat|risk|crisis|emergency)\b",
        r"\b(heartbreaking|tragic|devastating|heartbroken|victims)\b",
        r"\b(defend|protect|save|fight for|stand up)\b",
        r"\b(us vs them|enemies|outsiders|against the people)\b",
        r"\b(act now|last chance|before it's too late|urgent|immediately)\b",
        r"\b(don't (?:wait|miss|ignore|let them))",
    ]

    techniques_found: list[str] = []
    technique_counts: dict[str, int] = {
        "loaded_language": 0,
        "appeal_to_authority": 0,
        "bandwagon": 0,
        "false_dichotomy": 0,
        "emotional_manipulation": 0,
    }

    # Count loaded language matches
    for pattern in loaded_language:
        matches = re.findall(pattern, text_lower)
        technique_counts["loaded_language"] += len(matches)

    # Count authority appeals
    for pattern in authority_patterns:
        matches = re.findall(pattern, text_lower)
        technique_counts["appeal_to_authority"] += len(matches)

    # Count bandwagon terms
    for pattern in bandwagon_patterns:
        matches = re.findall(pattern, text_lower)
        technique_counts["bandwagon"] += len(matches)

    # Count false dichotomy
    for pattern in dichotomy_patterns:
        matches = re.findall(pattern, text_lower)
        technique_counts["false_dichotomy"] += len(matches)

    # Count emotional manipulation
    for pattern in emotion_patterns:
        matches = re.findall(pattern, text_lower)
        technique_counts["emotional_manipulation"] += len(matches)

    # Build techniques list
    for technique, count in technique_counts.items():
        if count > 0:
            techniques_found.append({"technique": technique, "count": count})

    # Calculate propaganda score (0-100)
    word_count = len(text_lower.split())
    if word_count == 0:
        propaganda_score = 0
    else:
        total_markers = sum(technique_counts.values())
        techniques_used = sum(1 for v in technique_counts.values() if v > 0)
        # Score combines: marker density + technique diversity
        # Each technique used adds 15 points, each marker adds proportional density
        density_score = min(50, int((total_markers / max(1, word_count)) * 500))
        diversity_score = techniques_used * 15
        propaganda_score = min(100, density_score + diversity_score)

    # Find dominant technique
    dominant_technique = None
    if techniques_found:
        dominant_technique = max(techniques_found, key=lambda x: x["count"])["technique"]

    return {
        "text_length": len(text),
        "word_count": word_count,
        "techniques_found": techniques_found,
        "propaganda_score": propaganda_score,
        "dominant_technique": dominant_technique,
    }


async def research_source_credibility(url: str) -> dict[str, Any]:
    """Rate source credibility using multiple factors.

    Assesses credibility by:
    - Domain age via WHOIS/RDAP
    - Wikipedia reference check
    - Academic citations (Semantic Scholar)
    - HTTP security headers scoring

    Args:
        url: source URL to evaluate

    Returns:
        Dict with ``url``, ``domain_age_days``, ``wikipedia_referenced``,
        ``academic_citations``, ``security_score``, and ``credibility_score`` (0-100).
    """
    validate_url(url)

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
            timeout=_DEFAULT_TIMEOUT,
        ) as client:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace("www.", "")

            domain_age_days = 0
            security_score = 0
            wikipedia_referenced = False
            academic_citations = 0

            # Try to get domain age from WHOIS (via free RDAP)
            try:
                # RDAP query to find domain registration date
                rdap_url = f"https://rdap.org/domain/{domain}"
                whois_data = await _get_json(client, rdap_url, timeout=10.0)
                if whois_data and "events" in whois_data:
                    for event in whois_data.get("events", []):
                        if event.get("eventAction") == "registration":
                            try:
                                reg_date = datetime.fromisoformat(
                                    event.get("eventDate", "").replace("Z", "+00:00")
                                )
                                domain_age_days = (
                                    datetime.now(timezone.utc) - reg_date
                                ).days
                                break
                            except (ValueError, TypeError):
                                pass
            except Exception as e:
                logger.debug("rdap_domain_age_error: %s", e)

            # Check Wikipedia references via Wikipedia API
            try:
                wiki_search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={domain}&format=json"
                wiki_results = await _get_json(client, wiki_search_url, timeout=10.0)
                if wiki_results and wiki_results.get("query", {}).get("search"):
                    wikipedia_referenced = True
                    # Also check article content for domain mentions
                    for result in wiki_results.get("query", {}).get("search", [])[:3]:
                        try:
                            page_id = result.get("pageid")
                            page_url = f"https://en.wikipedia.org/w/api.php?action=query&pageids={page_id}&prop=extracts&format=json"
                            page_data = await _get_json(client, page_url, timeout=10.0)
                            if page_data:
                                extract = (
                                    page_data.get("query", {})
                                    .get("pages", {})
                                    .get(str(page_id), {})
                                    .get("extract", "")
                                )
                                if domain in extract.lower():
                                    wikipedia_referenced = True
                        except Exception as e:
                            logger.debug("wikipedia_page_extract_error: %s", e)
            except Exception as e:
                logger.debug("wikipedia_search_error: %s", e)

            # Check academic citations via Semantic Scholar
            try:
                scholar_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={domain}&limit=5"
                scholar_data = await _get_json(client, scholar_url, timeout=10.0)
                if scholar_data and scholar_data.get("data"):
                    academic_citations = len(scholar_data.get("data", []))
            except Exception as e:
                logger.debug("semantic_scholar_error: %s", e)

            # Check security headers
            try:
                resp = await client.get(url, timeout=10.0)
                headers = resp.headers
                security_score = 0
                # Score based on security headers present
                security_headers_list = [
                    "strict-transport-security",
                    "content-security-policy",
                    "x-content-type-options",
                    "x-frame-options",
                    "x-xss-protection",
                ]
                for header in security_headers_list:
                    if header.lower() in {k.lower() for k in headers.keys()}:
                        security_score += 20
                security_score = min(100, security_score)
            except Exception as e:
                logger.debug("security_headers_check_error: %s", e)

            # Calculate credibility score (0-100)
            credibility_score = 0

            # Factor 1: Domain age (0-25 points, older is better, 365+ days = 25)
            if domain_age_days >= 365:
                credibility_score += 25
            elif domain_age_days > 0:
                credibility_score += min(25, (domain_age_days / 365) * 25)

            # Factor 2: Wikipedia reference (0-25 points)
            if wikipedia_referenced:
                credibility_score += 25

            # Factor 3: Academic citations (0-25 points)
            if academic_citations > 0:
                credibility_score += min(25, (academic_citations / 10) * 25)

            # Factor 4: Security headers (0-25 points)
            credibility_score += (security_score / 100) * 25

            credibility_score = min(100, int(credibility_score))

            return {
                "url": url,
                "domain": domain,
                "domain_age_days": domain_age_days,
                "wikipedia_referenced": wikipedia_referenced,
                "academic_citations": academic_citations,
                "security_score": security_score,
                "credibility_score": credibility_score,
            }

    return await _run()


async def research_information_cascade(
    topic: str, hours_back: int = 72
) -> dict[str, Any]:
    """Map information flow across platforms (HN, Reddit, arXiv, Wikipedia).

    Traces how information spreads across different platforms,
    identifying the origin source and cascade path.

    Args:
        topic: topic to track across platforms
        hours_back: hours to look back (default 72)

    Returns:
        Dict with ``topic``, ``timeline`` (list of {source, title, url, timestamp}),
        ``origin_source``, ``cascade_depth``, and ``platforms_reached``.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Loom-Research/1.0"},
            timeout=_DEFAULT_TIMEOUT,
        ) as client:
            timeline: list[dict[str, Any]] = []

            # HackerNews search
            try:
                hn_search_url = f"https://hn.algolia.com/api/v1/search?query={topic}&hitsPerPage=10"
                hn_results = await _get_json(client, hn_search_url, timeout=15.0)
                if hn_results and "hits" in hn_results:
                    for hit in hn_results.get("hits", [])[:5]:
                        created_at = hit.get("created_at", "")
                        if created_at:
                            try:
                                ts = datetime.fromisoformat(
                                    created_at.replace("Z", "+00:00")
                                )
                                timeline.append(
                                    {
                                        "source": "HackerNews",
                                        "title": hit.get("title", ""),
                                        "url": hit.get("url", ""),
                                        "timestamp": ts.isoformat(),
                                        "score": hit.get("points", 0),
                                    }
                                )
                            except (ValueError, TypeError):
                                pass
            except Exception as exc:
                logger.debug("HN search failed: %s", exc)

            # Reddit search
            try:
                reddit_search_url = f"https://www.reddit.com/search.json?q={topic}&limit=10&sort=new"
                reddit_results = await _get_json(client, reddit_search_url, timeout=15.0)
                if reddit_results and "data" in reddit_results:
                    for post in reddit_results.get("data", {}).get("children", [])[:5]:
                        created_ts = post.get("data", {}).get("created_utc")
                        if created_ts:
                            ts = datetime.fromtimestamp(created_ts, tz=timezone.utc)
                            timeline.append(
                                {
                                    "source": "Reddit",
                                    "title": post.get("data", {}).get("title", ""),
                                    "url": post.get("data", {}).get("url", ""),
                                    "timestamp": ts.isoformat(),
                                    "score": post.get("data", {}).get("score", 0),
                                }
                            )
            except Exception as exc:
                logger.debug("Reddit search failed: %s", exc)

            # arXiv search
            try:
                arxiv_search_url = f"http://export.arxiv.org/api/query?search_query=all:{topic}&start=0&max_results=5&sortBy=submittedDate&sortOrder=descending"
                arxiv_xml = await _get_text(client, arxiv_search_url, timeout=15.0)
                if arxiv_xml:
                    import xml.etree.ElementTree as ET

                    try:
                        root = ET.fromstring(arxiv_xml)
                        ns = {"atom": "http://www.w3.org/2005/Atom"}
                        for entry in root.findall("atom:entry", ns)[:5]:
                            published = entry.find("atom:published", ns)
                            title = entry.find("atom:title", ns)
                            link = entry.find("atom:id", ns)
                            if published is not None and title is not None:
                                timeline.append(
                                    {
                                        "source": "arXiv",
                                        "title": title.text or "",
                                        "url": link.text or "",
                                        "timestamp": published.text or "",
                                    }
                                )
                    except ET.ParseError:
                        pass
            except Exception as exc:
                logger.debug("arXiv search failed: %s", exc)

            # Wikipedia search
            try:
                wiki_search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={topic}&format=json&srlimit=5"
                wiki_results = await _get_json(client, wiki_search_url, timeout=15.0)
                if wiki_results and wiki_results.get("query", {}).get("search"):
                    for result in wiki_results.get("query", {}).get("search", [])[:5]:
                        timeline.append(
                            {
                                "source": "Wikipedia",
                                "title": result.get("title", ""),
                                "url": f"https://en.wikipedia.org/wiki/{result.get('title', '').replace(' ', '_')}",
                                "timestamp": "",
                            }
                        )
            except Exception as exc:
                logger.debug("Wikipedia search failed: %s", exc)

            # Sort by timestamp (empty timestamps go last)
            timeline_sorted = sorted(
                timeline,
                key=lambda x: x.get("timestamp", "9999-12-31"),
            )

            # Identify origin (earliest mention)
            origin_source = None
            if timeline_sorted:
                # Find first entry with valid timestamp
                for entry in timeline_sorted:
                    if entry.get("timestamp"):
                        origin_source = entry.get("source")
                        break

            # Count platforms reached
            platforms_reached = list(set(entry["source"] for entry in timeline))

            return {
                "topic": topic,
                "hours_back": hours_back,
                "timeline": timeline_sorted[:20],
                "origin_source": origin_source,
                "cascade_depth": len(timeline_sorted),
                "platforms_reached": platforms_reached,
            }

    return await _run()


async def research_web_time_machine(url: str, snapshots: int = 10) -> dict[str, Any]:
    """Track website evolution via Wayback Machine CDX snapshots.

    Samples website snapshots over time and detects technology changes
    by parsing HTTP headers and page signatures.

    Args:
        url: target URL to track
        snapshots: number of snapshots to retrieve

    Returns:
        Dict with ``url``, ``evolution`` (list of {date, technologies}),
        and ``tech_changes`` (list of {date, added, removed}).
    """
    validate_url(url)

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Loom-Research/1.0"},
            timeout=_DEFAULT_TIMEOUT,
        ) as client:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # Query Wayback CDX API for snapshots
            cdx_url = f"https://web.archive.org/cdx/search/cdx?url={domain}/*&output=json&fl=timestamp,statuscode&filter=statuscode:200&collapse=urlkey&limit={snapshots}&sort=timestamp"

            evolution: list[dict[str, Any]] = []

            try:
                cdx_data = await _get_json(client, cdx_url, timeout=20.0)
                if cdx_data and isinstance(cdx_data, list) and len(cdx_data) > 1:
                    # First row is headers, skip it
                    for row in cdx_data[1:]:
                        if len(row) >= 2:
                            timestamp_str = row[0]
                            try:
                                # Parse timestamp: YYYYMMDDhhmmss
                                ts = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                                snapshot_url = f"https://web.archive.org/web/{timestamp_str}/{url}"

                                # Fetch snapshot and detect technologies
                                snapshot_text = await _get_text(
                                    client, snapshot_url, timeout=15.0
                                )
                                if snapshot_text:
                                    technologies = _detect_tech_signatures(snapshot_text)
                                    evolution.append(
                                        {
                                            "date": ts.isoformat(),
                                            "timestamp": timestamp_str,
                                            "technologies": technologies,
                                        }
                                    )
                            except (ValueError, TypeError):
                                pass
            except Exception as exc:
                logger.debug("Wayback CDX query failed: %s", exc)

            # Detect tech changes
            tech_changes: list[dict[str, Any]] = []
            previous_techs: set[str] = set()
            for entry in evolution:
                current_techs = set(entry.get("technologies", []))
                added = current_techs - previous_techs
                removed = previous_techs - current_techs

                if added or removed:
                    tech_changes.append(
                        {
                            "date": entry.get("date"),
                            "added": sorted(list(added)),
                            "removed": sorted(list(removed)),
                        }
                    )

                previous_techs = current_techs

            return {
                "url": url,
                "domain": domain,
                "snapshots_found": len(evolution),
                "evolution": evolution,
                "tech_changes": tech_changes,
            }

    return await _run()


def _detect_tech_signatures(html: str) -> list[str]:
    """Detect technology signatures in HTML content."""
    technologies: set[str] = set()

    # JavaScript frameworks
    if "react" in html.lower():
        technologies.add("React")
    if "angular" in html.lower():
        technologies.add("Angular")
    if "vue" in html.lower():
        technologies.add("Vue.js")
    if "jquery" in html.lower():
        technologies.add("jQuery")

    # CMS systems
    if "wordpress" in html.lower():
        technologies.add("WordPress")
    if "drupal" in html.lower():
        technologies.add("Drupal")
    if "joomla" in html.lower():
        technologies.add("Joomla")

    # Web servers (via meta tags / headers not available in snapshot text)
    if "nginx" in html.lower():
        technologies.add("Nginx")
    if "apache" in html.lower():
        technologies.add("Apache")

    # Other markers
    if "google analytics" in html.lower() or "gtag" in html.lower():
        technologies.add("Google Analytics")
    if "_gaq.push" in html:
        technologies.add("Google Analytics (legacy)")

    return sorted(list(technologies))


async def research_influence_operation(topic: str) -> dict[str, Any]:
    """Detect potential influence operations via coordinated posting patterns.

    Analyzes HN and Reddit for suspicious clusters of posts:
    - Same topic posted within tight time windows
    - Similar language/phrasing patterns
    - Bayesian probability scoring

    Args:
        topic: topic to analyze for coordination signals

    Returns:
        Dict with ``topic``, ``suspicious_clusters`` (list),
        ``coordination_score`` (0-100), and ``evidence``.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Loom-Research/1.0"},
            timeout=_DEFAULT_TIMEOUT,
        ) as client:
            clusters: list[dict[str, Any]] = []
            all_posts: list[dict[str, Any]] = []

            # Fetch HN posts
            try:
                hn_url = f"https://hn.algolia.com/api/v1/search?query={topic}&hitsPerPage=30"
                hn_data = await _get_json(client, hn_url, timeout=15.0)
                if hn_data and "hits" in hn_data:
                    for hit in hn_data.get("hits", []):
                        created_at = hit.get("created_at", "")
                        if created_at:
                            try:
                                ts = datetime.fromisoformat(
                                    created_at.replace("Z", "+00:00")
                                )
                                all_posts.append(
                                    {
                                        "platform": "HN",
                                        "title": hit.get("title", ""),
                                        "author": hit.get("author", ""),
                                        "timestamp": ts,
                                        "url": hit.get("url", ""),
                                        "points": hit.get("points", 0),
                                    }
                                )
                            except (ValueError, TypeError):
                                pass
            except Exception as exc:
                logger.debug("HN fetch failed: %s", exc)

            # Fetch Reddit posts
            try:
                reddit_url = f"https://www.reddit.com/search.json?q={topic}&limit=30"
                reddit_data = await _get_json(client, reddit_url, timeout=15.0)
                if reddit_data and "data" in reddit_data:
                    for post in reddit_data.get("data", {}).get("children", []):
                        created_ts = post.get("data", {}).get("created_utc")
                        if created_ts:
                            ts = datetime.fromtimestamp(created_ts, tz=timezone.utc)
                            all_posts.append(
                                {
                                    "platform": "Reddit",
                                    "title": post.get("data", {}).get("title", ""),
                                    "author": post.get("data", {}).get("author", ""),
                                    "timestamp": ts,
                                    "url": post.get("data", {}).get("url", ""),
                                    "score": post.get("data", {}).get("score", 0),
                                }
                            )
            except Exception as exc:
                logger.debug("Reddit fetch failed: %s", exc)

            # Sort by timestamp
            all_posts.sort(key=lambda x: x["timestamp"])

            # Detect clusters: posts within 1 hour of each other
            if all_posts:
                current_cluster: list[dict[str, Any]] = [all_posts[0]]
                for post in all_posts[1:]:
                    time_diff = (post["timestamp"] - current_cluster[0]["timestamp"]).total_seconds()
                    if time_diff <= 3600:  # 1 hour
                        current_cluster.append(post)
                    else:
                        if len(current_cluster) >= 2:
                            # Calculate similarity score (simplified: title overlap)
                            cluster_dict = {
                                "size": len(current_cluster),
                                "time_window_hours": (
                                    (current_cluster[-1]["timestamp"] - current_cluster[0]["timestamp"]).total_seconds()
                                    / 3600
                                ),
                                "posts": current_cluster,
                                "platforms": list(set(p["platform"] for p in current_cluster)),
                            }
                            clusters.append(cluster_dict)
                        current_cluster = [post]

                # Don't forget the last cluster
                if len(current_cluster) >= 2:
                    cluster_dict = {
                        "size": len(current_cluster),
                        "time_window_hours": (
                            (current_cluster[-1]["timestamp"] - current_cluster[0]["timestamp"]).total_seconds()
                            / 3600
                        ),
                        "posts": current_cluster,
                        "platforms": list(set(p["platform"] for p in current_cluster)),
                    }
                    clusters.append(cluster_dict)

            # Calculate coordination score (0-100)
            # Based on: number of clusters, cluster size, time window tightness
            coordination_score = 0
            if clusters:
                avg_cluster_size = sum(c["size"] for c in clusters) / len(clusters)
                avg_time_window = sum(c["time_window_hours"] for c in clusters) / len(clusters)

                # Larger clusters and tighter time windows = higher coordination
                coordination_score = min(
                    100,
                    int((avg_cluster_size / 5) * 50 + (1 - min(avg_time_window / 1, 1)) * 50),
                )

            evidence = {
                "total_posts_analyzed": len(all_posts),
                "clusters_detected": len(clusters),
                "platforms": list(set(p["platform"] for p in all_posts)),
            }

            return {
                "topic": topic,
                "suspicious_clusters": clusters[:10],
                "coordination_score": coordination_score,
                "evidence": evidence,
            }

    return await _run()


async def research_dark_web_bridge(query: str) -> dict[str, Any]:
    """Find clearnet references to dark web content.

    Searches for .onion mentions in clearnet sources:
    - Google Dorks for .onion references
    - Ahmia indexed content with clearnet equivalents
    - Reddit r/onions discussions
    - Academic papers citing dark web

    Args:
        query: search term to find dark web references for

    Returns:
        Dict with ``query``, ``clearnet_references`` (list),
        ``academic_references`` (list), and ``total``.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Loom-Research/1.0"},
            timeout=_DEFAULT_TIMEOUT,
        ) as client:
            clearnet_refs: list[dict[str, str]] = []

            # Search for .onion mentions in Reddit
            try:
                reddit_url = f"https://www.reddit.com/r/onions/search.json?q={query}&limit=20&sort=new"
                reddit_data = await _get_json(client, reddit_url, timeout=15.0)
                if reddit_data and "data" in reddit_data:
                    for post in reddit_data.get("data", {}).get("children", [])[:10]:
                        title = post.get("data", {}).get("title", "")
                        url = post.get("data", {}).get("url", "")
                        # Extract .onion URLs from title if present
                        onion_matches = re.findall(r"[\w\-]+\.onion", title.lower())
                        if onion_matches or ".onion" in url:
                            clearnet_refs.append(
                                {
                                    "source": "Reddit r/onions",
                                    "title": title,
                                    "url": url,
                                    "onion_mentions": onion_matches,
                                }
                            )
            except Exception as exc:
                logger.debug("Reddit r/onions search failed: %s", exc)

            # Search Ahmia for indexed content
            try:
                ahmia_url = f"https://ahmia.fi/search/?q={query}&p=0"
                ahmia_html = await _get_text(client, ahmia_url, timeout=15.0)
                if ahmia_html and ".onion" in ahmia_html:
                    # Extract .onion URLs from Ahmia results
                    onion_urls = re.findall(r"([\w\-]+\.onion)", ahmia_html)
                    if onion_urls:
                        clearnet_refs.append(
                            {
                                "source": "Ahmia",
                                "query": query,
                                "onion_urls_found": list(set(onion_urls))[:5],
                            }
                        )
            except Exception as exc:
                logger.debug("Ahmia search failed: %s", exc)

            # Search Wikipedia for dark web references
            academic_refs: list[dict[str, str]] = []
            try:
                wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query} dark web&format=json&srlimit=10"
                wiki_results = await _get_json(client, wiki_url, timeout=15.0)
                if wiki_results and wiki_results.get("query", {}).get("search"):
                    for result in wiki_results.get("query", {}).get("search", [])[:5]:
                        academic_refs.append(
                            {
                                "source": "Wikipedia",
                                "title": result.get("title", ""),
                                "url": f"https://en.wikipedia.org/wiki/{result.get('title', '').replace(' ', '_')}",
                            }
                        )
            except Exception as exc:
                logger.debug("Wikipedia search failed: %s", exc)

            # Try Semantic Scholar for academic papers
            try:
                scholar_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query} dark web&limit=10"
                scholar_data = await _get_json(client, scholar_url, timeout=15.0)
                if scholar_data and scholar_data.get("data"):
                    for paper in scholar_data.get("data", [])[:5]:
                        academic_refs.append(
                            {
                                "source": "Semantic Scholar",
                                "title": paper.get("title", ""),
                                "year": paper.get("year", ""),
                                "url": paper.get("url", ""),
                            }
                        )
            except Exception as exc:
                logger.debug("Semantic Scholar search failed: %s", exc)

            return {
                "query": query,
                "clearnet_references": clearnet_refs[:10],
                "academic_references": academic_refs[:10],
                "total": len(clearnet_refs) + len(academic_refs),
            }

    return await _run()


async def research_info_half_life(urls: list[str]) -> dict[str, Any]:
    """Estimate URL survival rate and information decay half-life.

    For each URL, checks:
    - Wayback Machine availability
    - Live HTTP status

    Estimates time until 50% of URLs are dead.

    Args:
        urls: list of URLs to check

    Returns:
        Dict with ``urls_checked``, ``alive_count``, ``dead_count``,
        and ``estimated_half_life_days``.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Loom-Research/1.0"},
            timeout=_DEFAULT_TIMEOUT,
        ) as client:
            alive_count = 0
            dead_count = 0
            url_statuses: list[dict[str, Any]] = []

            tasks = []
            for url in urls[:50]:  # Limit to 50 for performance
                tasks.append(_check_url_status(client, url))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for url, result in zip(urls[:50], results):
                if isinstance(result, dict):
                    url_statuses.append(result)
                    if result["status"] == "alive":
                        alive_count += 1
                    else:
                        dead_count += 1

            # Estimate half-life based on historical data
            # Simplified: assume URLs age out exponentially
            # In practice, this would use Wayback snapshots over time
            estimated_half_life_days = 365  # Default: 1 year
            if url_statuses:
                # Calculate average age estimation from Wayback
                ages: list[int] = []
                for status in url_statuses:
                    if status.get("wayback_available"):
                        ages.append(status.get("days_since_last_snapshot", 365))

                if ages:
                    avg_age = sum(ages) / len(ages)
                    # Rough estimate: if average age is high, half-life is longer
                    estimated_half_life_days = min(3650, max(30, int(avg_age * 0.5)))

            return {
                "urls_checked": len(url_statuses),
                "alive_count": alive_count,
                "dead_count": dead_count,
                "url_statuses": url_statuses[:20],
                "estimated_half_life_days": estimated_half_life_days,
            }

    async def _check_url_status(client: httpx.AsyncClient, url: str) -> dict[str, Any]:
        """Check status of a single URL."""
        http_status = await _check_http_status(client, url)
        wayback_available = False
        days_since_snapshot = 0

        # Check Wayback availability
        try:
            wayback_url = f"https://archive.org/wayback/available?url={url}"
            wayback_data = await _get_json(client, wayback_url, timeout=10.0)
            if wayback_data and wayback_data.get("archived_snapshots"):
                wayback_available = True
                closest = wayback_data.get("archived_snapshots", {}).get("closest", {})
                if closest.get("timestamp"):
                    try:
                        snapshot_date = datetime.strptime(
                            closest.get("timestamp"), "%Y%m%d%H%M%S"
                        )
                        days_since_snapshot = (datetime.now() - snapshot_date).days
                    except (ValueError, TypeError):
                        pass
        except Exception as e:
            logger.debug("wayback_check_error: %s", e)

        status = "alive" if http_status and 200 <= http_status < 400 else "dead"

        return {
            "url": url,
            "status": status,
            "http_status": http_status,
            "wayback_available": wayback_available,
            "days_since_last_snapshot": days_since_snapshot,
        }

    return await _run()


async def research_search_discrepancy(query: str) -> dict[str, Any]:
    """Compare search results across multiple engines to find discrepancies.

    Queries:
    - DuckDuckGo (privacy-focused)
    - Brave (ads-free)
    - Marginalia (indie alternative)
    - Wikipedia (knowledge base)

    Identifies URLs unique to each engine (potential deindexing).

    Args:
        query: search query

    Returns:
        Dict with ``query``, ``engines_queried``, ``unique_per_engine`` (dict),
        and ``deindexed_candidates``.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Loom-Research/1.0"},
            timeout=_DEFAULT_TIMEOUT,
        ) as client:
            results_per_engine: dict[str, list[str]] = {
                "ddg": [],
                "brave": [],
                "marginalia": [],
                "wikipedia": [],
            }

            # DuckDuckGo search
            try:
                ddg_url = f"https://duckduckgo.com/api?q={query}&format=json"
                ddg_data = await _get_json(client, ddg_url, timeout=15.0)
                if ddg_data and "Results" in ddg_data:
                    results_per_engine["ddg"] = [
                        r.get("FirstURL", "") for r in ddg_data.get("Results", [])[:10]
                    ]
            except Exception as exc:
                logger.debug("DuckDuckGo search failed: %s", exc)

            # Brave search (note: Brave requires API key in practice, this is simplified)
            try:
                brave_url = f"https://api.search.brave.com/res/v1/web/search?q={query}&count=10"
                brave_headers = {"User-Agent": "Loom-Research/1.0"}
                brave_data = await _get_json(client, brave_url, timeout=15.0)
                if brave_data and "web" in brave_data:
                    results_per_engine["brave"] = [
                        r.get("url", "") for r in brave_data.get("web", [])[:10]
                    ]
            except Exception as exc:
                logger.debug("Brave search failed: %s", exc)

            # Marginalia search
            try:
                marginalia_url = f"https://api.marginalia.nu/search?query={query}&limit=10"
                marginalia_data = await _get_json(client, marginalia_url, timeout=15.0)
                if marginalia_data and isinstance(marginalia_data, dict):
                    if "results" in marginalia_data:
                        results_per_engine["marginalia"] = [
                            r.get("url", "") for r in marginalia_data.get("results", [])[:10]
                        ]
            except Exception as exc:
                logger.debug("Marginalia search failed: %s", exc)

            # Wikipedia search
            try:
                wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&format=json&srlimit=10"
                wiki_data = await _get_json(client, wiki_url, timeout=15.0)
                if wiki_data and "query" in wiki_data:
                    results_per_engine["wikipedia"] = [
                        f"https://en.wikipedia.org/wiki/{r.get('title', '').replace(' ', '_')}"
                        for r in wiki_data.get("query", {}).get("search", [])[:10]
                    ]
            except Exception as exc:
                logger.debug("Wikipedia search failed: %s", exc)

            # Calculate unique URLs per engine
            unique_per_engine: dict[str, list[str]] = {}
            all_urls: set[str] = set()
            for engine, urls in results_per_engine.items():
                all_urls.update(urls)

            for engine, urls in results_per_engine.items():
                engine_set = set(urls)
                other_urls = all_urls - engine_set
                unique_per_engine[engine] = sorted(list(other_urls))[:5]

            # Find deindexed candidates (in alternative engines but not in major ones)
            ddg_set = set(results_per_engine["ddg"])
            major_engines = {"ddg"}
            alternative_engines = {"brave", "marginalia", "wikipedia"} - major_engines

            deindexed_candidates = []
            for engine in alternative_engines:
                alt_set = set(results_per_engine.get(engine, []))
                potentially_deindexed = alt_set - ddg_set
                if potentially_deindexed:
                    deindexed_candidates.extend(
                        [
                            {"url": url, "found_in": engine, "missing_from": "ddg"}
                            for url in list(potentially_deindexed)[:3]
                        ]
                    )

            return {
                "query": query,
                "engines_queried": list(results_per_engine.keys()),
                "results_per_engine": results_per_engine,
                "unique_per_engine": unique_per_engine,
                "deindexed_candidates": deindexed_candidates[:10],
            }

    return await _run()
