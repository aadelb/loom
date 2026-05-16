"""URLhaus malware database lookup tools — check URLs and search threats."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from loom.validators import validate_url

from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_json, fetch_text, fetch_bytes
logger = logging.getLogger("loom.tools.urlhaus_lookup")

_URLHAUS_BASE = "https://urlhaus-api.abuse.ch/v1"

_SUSPICIOUS_TLDS = {".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".buzz", ".work", ".click", ".link", ".info", ".biz", ".pw", ".cc", ".ws"}
_SUSPICIOUS_PATTERNS = ["malware", "phish", "exploit", "hack", "crack", "warez", "torrent", "botnet", "c2", "payload", "dropper", "loader", "stealer"]


def _heuristic_url_check(url: str) -> dict[str, Any]:
    """Fallback heuristic URL risk assessment when URLhaus API is unavailable."""
    import re
    from urllib.parse import urlparse

    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    path = parsed.path.lower()
    risk_factors = []

    ip_pattern = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    if ip_pattern.match(hostname):
        risk_factors.append("ip_based_url")

    for tld in _SUSPICIOUS_TLDS:
        if hostname.endswith(tld):
            risk_factors.append(f"suspicious_tld:{tld}")
            break

    for pattern in _SUSPICIOUS_PATTERNS:
        if pattern in path or pattern in hostname:
            risk_factors.append(f"suspicious_keyword:{pattern}")

    if len(path) > 100:
        risk_factors.append("long_path")
    if parsed.port and parsed.port not in (80, 443, 8080, 8443):
        risk_factors.append(f"unusual_port:{parsed.port}")

    threat_level = "low" if len(risk_factors) == 0 else "medium" if len(risk_factors) <= 2 else "high"

    return {
        "url": url,
        "threat": threat_level if risk_factors else None,
        "status": "heuristic_analysis",
        "tags": risk_factors,
        "date_added": None,
        "threat_type": f"heuristic_{threat_level}" if risk_factors else None,
        "method": "local_heuristic (URLhaus API unavailable)",
        "risk_factors": risk_factors,
        "risk_score": min(len(risk_factors) * 25, 100),
    }


def _heuristic_search(query: str, search_type: str) -> dict[str, Any]:
    """Fallback heuristic search when URLhaus API is unavailable."""
    return {
        "query": query,
        "type": search_type,
        "results": [],
        "total": 0,
        "method": "heuristic_fallback (URLhaus API unavailable)",
        "note": f"URLhaus API returned 401. Query '{query}' cannot be checked against live database. Use VirusTotal or OTX as alternatives.",
        "alternatives": [
            "https://www.virustotal.com/gui/search/" + query,
            "https://otx.alienvault.com/indicator/search/" + query,
        ],
    }


@handle_tool_errors("research_urlhaus_check")

async def research_urlhaus_check(url: str) -> dict[str, Any]:
    """Check if URL is listed in URLhaus malware database (free).

    Queries URLhaus to check if a URL is known to host malware,
    phishing content, or other threats.

    Args:
        url: URL to check (must be valid HTTP/HTTPS URL)

    Returns:
        Dict with keys: url, threat, status, tags, date_added, threat_type
    """
    validate_url(url)
    if not url or not (url.startswith("http://") or url.startswith("https://")):
        return {
            "url": url,
            "error": "Invalid URL (must start with http:// or https://)",
            "threat": None,
            "status": None,
            "tags": [],
            "date_added": None,
            "threat_type": None,
        }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"{_URLHAUS_BASE}/url/",
                data={"url": url},
            )
            if resp.status_code in (401, 403, 429):
                return _heuristic_url_check(url)
            resp.raise_for_status()
            data = resp.json()

        if data.get("query_status") == "ok":
            result_data = data.get("result", [])

            if not result_data:
                return {
                    "url": url,
                    "threat": None,
                    "status": "not_listed",
                    "tags": [],
                    "date_added": None,
                    "threat_type": None,
                }

            first_result = result_data[0] if isinstance(result_data, list) else result_data
            return {
                "url": url,
                "threat": first_result.get("threat"),
                "status": "listed",
                "tags": first_result.get("tags", []),
                "date_added": first_result.get("date_added"),
                "threat_type": first_result.get("threat"),
            }
        elif data.get("query_status") == "no_results":
            return {
                "url": url,
                "threat": None,
                "status": "not_listed",
                "tags": [],
                "date_added": None,
                "threat_type": None,
            }
        else:
            return _heuristic_url_check(url)

    except Exception as exc:
        logger.warning("urlhaus_check_failed url=%s: %s — using heuristic fallback", url, exc)
        return _heuristic_url_check(url)

@handle_tool_errors("research_urlhaus_search")

async def research_urlhaus_search(
    query: str,
    search_type: str = "tag",
) -> dict[str, Any]:
    """Search URLhaus by tag, signature, or payload hash (free).

    Query URLhaus threat database by specific search criteria.

    Args:
        query: search term (tag name, signature, or payload hash)
        search_type: search type - "tag", "signature", or "hash"

    Returns:
        Dict with keys: query, type, results (list), total
    """
    if not query or len(query.strip()) == 0:
        return {
            "query": query,
            "type": search_type,
            "results": [],
            "total": 0,
            "error": "query required",
        }

    # Validate search_type
    if search_type not in ("tag", "signature", "hash"):
        search_type = "tag"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if search_type == "tag":
                endpoint = f"{_URLHAUS_BASE}/tag/"
                resp = await client.post(endpoint, data={"tag": query})
            elif search_type == "hash":
                endpoint = f"{_URLHAUS_BASE}/payload/"
                resp = await client.post(endpoint, data={"sha256_hash": query})
            else:  # signature
                endpoint = f"{_URLHAUS_BASE}/signature/"
                resp = await client.post(endpoint, data={"signature": query})

            if resp.status_code in (401, 403, 429):
                return _heuristic_search(query, search_type)
            resp.raise_for_status()
            data = resp.json()

        if data.get("query_status") == "no_results":
            return {"query": query, "type": search_type, "results": [], "total": 0}

        if data.get("query_status") != "ok":
            return _heuristic_search(query, search_type)

        result_data = data.get("result", [])
        if not result_data:
            return {"query": query, "type": search_type, "results": [], "total": 0}

        if not isinstance(result_data, list):
            result_data = [result_data]

        results = []
        for item in result_data[:50]:
            results.append({
                "url": item.get("url"),
                "status": item.get("url_status"),
                "threat": item.get("threat"),
                "tags": item.get("tags", []),
                "date_added": item.get("date_added"),
            })

        return {"query": query, "type": search_type, "results": results, "total": len(results)}

    except Exception as exc:
        logger.warning("urlhaus_search_failed query=%s: %s — using fallback", query, exc)
        return _heuristic_search(query, search_type)
