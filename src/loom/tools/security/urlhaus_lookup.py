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
            resp.raise_for_status()
            data = resp.json()

        if data.get("query_status") == "ok":
            result_data = data.get("result", [])

            if not result_data:
                # URL not found in URLhaus
                return {
                    "url": url,
                    "threat": None,
                    "status": "not_listed",
                    "tags": [],
                    "date_added": None,
                    "threat_type": None,
                }

            # URL is listed
            first_result = result_data[0] if isinstance(result_data, list) else result_data
            return {
                "url": url,
                "threat": first_result.get("threat"),
                "status": "listed",
                "tags": first_result.get("tags", []),
                "date_added": first_result.get("date_added"),
                "threat_type": first_result.get("threat"),
            }
        else:
            # Query failed
            return {
                "url": url,
                "error": data.get("query_status", "unknown error"),
                "threat": None,
                "status": None,
                "tags": [],
                "date_added": None,
                "threat_type": None,
            }

    except Exception as exc:
        logger.warning("urlhaus_check_failed url=%s: %s", url, exc)
        return {
            "url": url,
            "error": str(exc),
            "threat": None,
            "status": None,
            "tags": [],
            "date_added": None,
            "threat_type": None,
        }

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

            resp.raise_for_status()
            data = resp.json()

        if data.get("query_status") != "ok":
            return {
                "query": query,
                "type": search_type,
                "results": [],
                "total": 0,
                "error": data.get("query_status", "search failed"),
            }

        result_data = data.get("result", [])

        if not result_data:
            return {
                "query": query,
                "type": search_type,
                "results": [],
                "total": 0,
            }

        # Normalize result list
        if not isinstance(result_data, list):
            result_data = [result_data]

        results = []
        for item in result_data[:50]:  # Cap at 50 results
            results.append(
                {
                    "url": item.get("url"),
                    "status": item.get("url_status"),
                    "threat": item.get("threat"),
                    "tags": item.get("tags", []),
                    "date_added": item.get("date_added"),
                }
            )

        return {
            "query": query,
            "type": search_type,
            "results": results,
            "total": len(results),
        }

    except Exception as exc:
        logger.warning("urlhaus_search_failed query=%s type=%s: %s", query, search_type, exc)
        return {
            "query": query,
            "type": search_type,
            "results": [],
            "total": 0,
            "error": str(exc),
        }
