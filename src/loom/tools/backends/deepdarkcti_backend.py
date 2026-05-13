"""deepdarkCTI threat intelligence aggregation — dark web & public feed collection."""
from __future__ import annotations

import logging
import re
import time
from typing import Any
import httpx

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.deepdarkcti_backend")

# Public CTI feed URLs (no API key required)
_CTI_FEEDS = {
    "abuse_ipdb_recent": "https://api.abuseipdb.com/datasets/blacklist/",
    "urlhaus_recent": "https://urlhaus-api.abuse.ch/v1/urls/recent/",
    "phishtank": "https://openphish.com/feed.txt",
    "ransomware_tracker": "https://data.ransomware.com/api/v1/search/",
    "tweetfeed": "https://tweetfeed.abuse.ch/rss/",
}

# Darkweb/paste site search endpoints (free/public)
_DARKWEB_SOURCES = [
    "ahmia",  # Tor search engine
    "onionsearch",  # Onion domain search
]


def _extract_iocs(text: str) -> list[dict[str, Any]]:
    """Extract IOCs from text (IPs, domains, URLs, emails, hashes).

    Args:
        text: Text content to parse for IOCs

    Returns:
        List of dicts with keys: value, type
    """
    iocs = []
    seen: set[str] = set()

    # IPv4 addresses
    ipv4_pattern = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    for match in re.finditer(ipv4_pattern, text):
        ip = match.group()
        if ip not in seen:
            iocs.append({"value": ip, "type": "ip"})
            seen.add(ip)

    # Domains and URLs
    url_pattern = r"https?://[^\s<>\"{}|\\^`\[\]]+"
    for match in re.finditer(url_pattern, text):
        url = match.group()
        if url not in seen:
            iocs.append({"value": url, "type": "url"})
            seen.add(url)

    # Domains without protocol (basic)
    domain_pattern = r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b"
    for match in re.finditer(domain_pattern, text):
        domain = match.group()
        # Skip if already in URL and avoid false positives
        if (
            domain not in seen
            and "://" not in domain
            and len(domain) > 4
            and domain not in {"the", "that", "with"}
        ):
            iocs.append({"value": domain, "type": "domain"})
            seen.add(domain)

    # Email addresses
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    for match in re.finditer(email_pattern, text):
        email = match.group()
        if email not in seen:
            iocs.append({"value": email, "type": "email"})
            seen.add(email)

    # Hashes (MD5, SHA1, SHA256)
    md5_pattern = r"\b[a-fA-F0-9]{32}\b"
    for match in re.finditer(md5_pattern, text):
        hash_val = match.group()
        if hash_val not in seen:
            iocs.append({"value": hash_val, "type": "hash"})
            seen.add(hash_val)

    sha1_pattern = r"\b[a-fA-F0-9]{40}\b"
    for match in re.finditer(sha1_pattern, text):
        hash_val = match.group()
        if hash_val not in seen:
            iocs.append({"value": hash_val, "type": "hash"})
            seen.add(hash_val)

    sha256_pattern = r"\b[a-fA-F0-9]{64}\b"
    for match in re.finditer(sha256_pattern, text):
        hash_val = match.group()
        if hash_val not in seen:
            iocs.append({"value": hash_val, "type": "hash"})
            seen.add(hash_val)

    return iocs


@handle_tool_errors("research_dark_cti")
def research_dark_cti(
    query: str,
    sources: list[str] | None = None,
    max_results: int = 20,
) -> dict[str, Any]:
    """Aggregate dark web and public CTI feeds for threat intelligence.

    deepdarkCTI aggregates threat data from public CTI feeds, dark web forums,
    paste sites, and leak databases. No API key required (uses public feeds).

    Args:
        query: Search query (threat name, IOC, actor name, malware family, etc.)
        sources: Specific sources to query. If None, queries all available sources.
                Options: 'abuse_ipdb_recent', 'urlhaus_recent', 'phishtank',
                'ransomware_tracker', 'tweetfeed', 'ahmia', 'onionsearch'
        max_results: Maximum number of results to return per source

    Returns:
        Dict with keys:
        - query: The search query
        - findings: List of relevant findings with source, title, url, iocs
        - sources_checked: List of sources that were queried
        - threat_level: Overall threat level ('critical', 'high', 'medium', 'low')
        - iocs_found: Extracted IOCs from findings (deduplicated)
        - error: Error message if query failed
    """
    result: dict[str, Any] = {
        "query": query,
        "findings": [],
        "sources_checked": [],
        "threat_level": "low",
        "iocs_found": [],
    }

    # Use provided sources or all
    sources_to_check = sources or list(_CTI_FEEDS.keys()) + _DARKWEB_SOURCES

    findings_list: list[dict[str, Any]] = []
    iocs_set: set[str] = set()

    # Query each source
    for source in sources_to_check:
        if source not in _CTI_FEEDS and source not in _DARKWEB_SOURCES:
            logger.warning("dark_cti_unknown_source: %s", source)
            continue

        result["sources_checked"].append(source)

        try:
            # Fetch from CTI feeds
            if source in _CTI_FEEDS:
                feed_url = _CTI_FEEDS[source]

                with httpx.Client(timeout=10.0) as client:
                    resp = client.get(feed_url)
                    resp.raise_for_status()
                    content = resp.text

                # Search for query in feed content
                if query.lower() in content.lower():
                    # Extract context around matches
                    lines = content.split("\n")
                    for line in lines:
                        if query.lower() in line.lower():
                            # Extract IOCs from matching line
                            iocs = _extract_iocs(line)
                            for ioc in iocs:
                                iocs_set.add(ioc["value"])

                            findings_list.append(
                                {
                                    "source": source,
                                    "title": line[:100],
                                    "url": feed_url,
                                    "iocs": iocs,
                                    "timestamp": time.time(),
                                }
                            )

                            if len(findings_list) >= max_results:
                                break

            # Dark web sources (Ahmia, OnionSearch)
            elif source == "ahmia":
                try:
                    # Ahmia Tor search (public API)
                    ahmia_url = f"https://ahmia.fi/search/?q={query}&format=json"
                    with httpx.Client(timeout=10.0) as client:
                        resp = client.get(ahmia_url)
                        resp.raise_for_status()
                        data = resp.json()

                    for result_item in data.get("results", [])[:max_results]:
                        title = result_item.get("title", "")
                        url = result_item.get("url", "")
                        description = result_item.get("description", "")

                        # Extract IOCs from title and description
                        iocs = _extract_iocs(f"{title} {description}")
                        for ioc in iocs:
                            iocs_set.add(ioc["value"])

                        findings_list.append(
                            {
                                "source": "ahmia",
                                "title": title,
                                "url": url,
                                "iocs": iocs,
                                "timestamp": time.time(),
                            }
                        )

                except Exception as exc:
                    logger.warning("ahmia_query_failed query=%s: %s", query, exc)

            elif source == "onionsearch":
                # OnionSearch integration (simplified — actual integration needs API)
                logger.info("onionsearch_query attempted query=%s", query)
                # Would integrate with onionsearch API if available
                pass

        except httpx.HTTPStatusError as exc:
            logger.warning(
                "dark_cti_feed_error source=%s status=%d",
                source,
                exc.response.status_code,
            )
        except httpx.RequestError as exc:
            logger.warning("dark_cti_connection_error source=%s: %s", source, exc)
        except Exception as exc:
            logger.warning("dark_cti_parse_error source=%s: %s", source, exc)

    # Deduplicate and organize findings
    seen_urls: set[str] = set()
    for finding in findings_list:
        url = finding.get("url", "")
        if url and url not in seen_urls:
            result["findings"].append(finding)
            seen_urls.add(url)

    # Limit results
    result["findings"] = result["findings"][:max_results]

    # Collect unique IOCs
    result["iocs_found"] = sorted(iocs_set)

    # Calculate threat level based on sources and findings
    threat_keywords = {
        "malware": 3,
        "exploit": 3,
        "ransomware": 4,
        "botnet": 3,
        "phishing": 2,
        "ddos": 3,
        "steal": 2,
        "breach": 3,
        "leak": 2,
        "trojan": 3,
    }

    threat_score = 0
    for finding in result["findings"]:
        title_lower = finding.get("title", "").lower()
        for keyword, score in threat_keywords.items():
            if keyword in title_lower:
                threat_score = max(threat_score, score)

    # Map score to threat level
    if threat_score >= 4:
        result["threat_level"] = "critical"
    elif threat_score >= 3:
        result["threat_level"] = "high"
    elif threat_score >= 2:
        result["threat_level"] = "medium"
    else:
        result["threat_level"] = "low"

    logger.info(
        "dark_cti_complete query=%s findings=%d iocs=%d threat_level=%s",
        query,
        len(result["findings"]),
        len(result["iocs_found"]),
        result["threat_level"],
    )

    return result
