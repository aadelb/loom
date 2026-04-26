"""Darkweb CTI provider - Threat intelligence source finder.

Inspired by fastfire/deepdarkCTI. Searches a curated list of known dark web
CTI (Cyber Threat Intelligence) sources for relevant threat intelligence.
No external dependencies or API keys required.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("loom.providers.darkweb_cti")

# Curated list of known dark web CTI sources
# Real-world integration would fetch from a maintained list
# This is a representative sample
_CTI_SOURCES = [
    {
        "name": "Exploit.in",
        "url": "http://exploitinnn.onion",
        "category": "marketplace",
        "description": "Exploits and vulnerabilities marketplace",
    },
    {
        "name": "Dream Market",
        "url": "http://dreammarket.onion",
        "category": "marketplace",
        "description": "Dark web marketplace (goods and services)",
    },
    {
        "name": "White House Market",
        "url": "http://whitehousen.onion",
        "category": "marketplace",
        "description": "Dark web marketplace (anonymity focused)",
    },
    {
        "name": "Breach Database",
        "url": "http://breachdb.onion",
        "category": "database",
        "description": "Aggregated data breach records",
    },
    {
        "name": "Leaked Source",
        "url": "http://leakedsource.onion",
        "category": "database",
        "description": "Hacked credentials and leaked data",
    },
    {
        "name": "Under the Wire",
        "url": "http://underthewire.onion",
        "category": "forum",
        "description": "Hacker discussion forum",
    },
    {
        "name": "Nulled",
        "url": "http://nulledhq.onion",
        "category": "forum",
        "description": "Cybercrime tools and vulnerabilities",
    },
    {
        "name": "Darknet Markets Forum",
        "url": "http://dnmforum.onion",
        "category": "forum",
        "description": "Dark net marketplace discussion",
    },
    {
        "name": "Antidetect Browser Marketplace",
        "url": "http://antidetect.onion",
        "category": "tools",
        "description": "Fraudster tools and anti-detection software",
    },
    {
        "name": "C2 Server List",
        "url": "http://c2servers.onion",
        "category": "infrastructure",
        "description": "Active command and control server tracking",
    },
    {
        "name": "Botnet Database",
        "url": "http://botnetdb.onion",
        "category": "infrastructure",
        "description": "Compromised machine information and botnet tracking",
    },
    {
        "name": "Ransomware News",
        "url": "http://ransomwarenews.onion",
        "category": "threat_tracking",
        "description": "Ransomware group announcements and leaked files",
    },
    {
        "name": "APT Activity Log",
        "url": "http://aptlog.onion",
        "category": "threat_tracking",
        "description": "Advanced persistent threat activity tracking",
    },
    {
        "name": "Carding Shop",
        "url": "http://cardingshop.onion",
        "category": "fraud",
        "description": "Stolen credit card and payment information",
    },
    {
        "name": "Dump Database",
        "url": "http://dumpdb.onion",
        "category": "database",
        "description": "Aggregated database dumps and pastes",
    },
    {
        "name": "Vulnerability Exchange",
        "url": "http://vulnexch.onion",
        "category": "vulns",
        "description": "Zero-day and N-day vulnerability trading",
    },
    {
        "name": "Exploit Pack Repository",
        "url": "http://exploitrepo.onion",
        "category": "tools",
        "description": "Curated exploit code repository",
    },
    {
        "name": "Stolen Data Auctions",
        "url": "http://dataauction.onion",
        "category": "database",
        "description": "Auction platform for stolen corporate data",
    },
    {
        "name": "Hacking Tutorial Hub",
        "url": "http://hacktutorials.onion",
        "category": "education",
        "description": "Hacking techniques and exploitation tutorials",
    },
    {
        "name": "Threat Intel Aggregator",
        "url": "http://threatagg.onion",
        "category": "intelligence",
        "description": "Real-time threat intelligence aggregation",
    },
]


def search_darkweb_cti(
    query: str,
    n: int = 10,
    category: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Search dark web CTI (Cyber Threat Intelligence) sources.

    Searches a curated list of known CTI sources without requiring external API
    keys or connections. Matches query against source names and descriptions.

    Args:
        query: search term (vulnerability, threat type, marketplace name, etc.)
        n: max number of results
        category: optional filter by category (marketplace, forum, tools, etc.)
        **kwargs: ignored (accepted for interface compat)

    Returns:
        Normalized result dict with ``results`` list and ``query``.
    """
    if not query or len(query.strip()) == 0:
        return {"results": [], "query": query}

    try:
        query_lower = query.lower()
        results = []

        for source in _CTI_SOURCES:
            # Skip if category filter doesn't match
            if category and source.get("category", "").lower() != category.lower():
                continue

            # Match query against name, URL, or description
            name = source.get("name", "").lower()
            description = source.get("description", "").lower()
            url = source.get("url", "").lower()

            if (
                query_lower in name
                or query_lower in description
                or query_lower in url
            ):
                results.append({
                    "name": source.get("name", ""),
                    "url": source.get("url", ""),
                    "category": source.get("category", ""),
                    "description": source.get("description", ""),
                    "match_fields": [
                        "name" if query_lower in name else None,
                        "description" if query_lower in description else None,
                        "url" if query_lower in url else None,
                    ],
                })

        # Sort by relevance (exact name match first)
        def relevance_score(r: dict[str, Any]) -> int:
            # Exact name match = 3 points
            if query_lower == r.get("name", "").lower():
                return 3
            # Partial name match = 2 points
            if query_lower in r.get("name", "").lower():
                return 2
            # Description match = 1 point
            return 1

        results.sort(key=lambda x: relevance_score(x), reverse=True)

        return {
            "results": results[:n],
            "query": query,
            "sources_count": len(_CTI_SOURCES),
            "category_filter": category,
        }

    except Exception as exc:
        logger.error("darkweb_cti_search_failed query=%s: %s", query[:50], type(exc).__name__)
        return {"results": [], "query": query, "error": "search failed"}
