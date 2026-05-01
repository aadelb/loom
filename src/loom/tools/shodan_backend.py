"""Shodan integration — IP reconnaissance and device discovery.

Provides host lookup and search queries against Shodan's database
of internet-connected devices. Requires SHODAN_API_KEY environment variable.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger("loom.tools.shodan_backend")

try:
    import shodan

    _HAS_SHODAN = True
except ImportError:  # pragma: no cover — optional shodan SDK
    _HAS_SHODAN = False
    shodan = None  # type: ignore


def _get_shodan_api() -> Any:
    """Initialize Shodan API client if API key is available.

    Returns None if SHODAN_API_KEY is not set or Shodan SDK not installed.
    """
    if not _HAS_SHODAN or shodan is None:
        return None

    api_key = os.environ.get("SHODAN_API_KEY")
    if not api_key:
        return None

    try:
        return shodan.Shodan(api_key)
    except Exception:
        return None


async def research_shodan_host(ip: str) -> dict[str, Any]:
    """Look up host information on Shodan.

    Retrieves detailed information about an IP address including banners,
    open ports, services, vulnerabilities, and associated metadata.
    Requires SHODAN_API_KEY environment variable.

    Args:
        ip: IPv4 address to look up

    Returns:
        Dict with keys: ip, open_ports, banners, services, org, isp,
        country, vulnerabilities, last_updated, error (if any)

    Raises:
        shodan.APIError: If API call fails (rate limited, invalid key, etc.)
    """
    if not _HAS_SHODAN:
        return {
            "ip": ip,
            "error": "Shodan SDK not installed. Install with: pip install shodan",
            "open_ports": None,
            "banners": None,
        }

    api = _get_shodan_api()
    if not api:
        return {
            "ip": ip,
            "error": "SHODAN_API_KEY not set in environment",
            "open_ports": None,
            "banners": None,
        }

    try:
        # Wrap sync call in asyncio.to_thread() to avoid blocking event loop
        host_info = await asyncio.to_thread(_fetch_host, api, ip)

        return {
            "ip": ip,
            "open_ports": host_info.get("ports", []),
            "banners": host_info.get("data", []),
            "services": _extract_services(host_info.get("data", [])),
            "org": host_info.get("org"),
            "isp": host_info.get("isp"),
            "country": host_info.get("country_name"),
            "country_code": host_info.get("country_code"),
            "region": host_info.get("region_code"),
            "city": host_info.get("city"),
            "latitude": host_info.get("latitude"),
            "longitude": host_info.get("longitude"),
            "last_update": host_info.get("last_update"),
            "hostnames": host_info.get("hostnames", []),
            "domains": host_info.get("domains", []),
            "vulns": host_info.get("vulns", []),
            "error": None,
        }

    except Exception as exc:
        error_msg = str(exc)

        # Handle shodan.APIError if shodan is available
        if _HAS_SHODAN and shodan is not None:
            if isinstance(exc, shodan.APIError):
                if "API error 401" in error_msg:
                    return {
                        "ip": ip,
                        "error": "Invalid or expired SHODAN_API_KEY",
                        "open_ports": None,
                        "banners": None,
                    }
                elif "API error 429" in error_msg:
                    return {
                        "ip": ip,
                        "error": "Rate limited by Shodan API (quota exceeded)",
                        "open_ports": None,
                        "banners": None,
                    }
                elif "API error 404" in error_msg:
                    return {
                        "ip": ip,
                        "open_ports": [],
                        "banners": [],
                        "services": [],
                        "org": None,
                        "isp": None,
                        "country": None,
                        "country_code": None,
                        "region": None,
                        "city": None,
                        "latitude": None,
                        "longitude": None,
                        "last_update": None,
                        "hostnames": [],
                        "domains": [],
                        "vulns": [],
                        "error": f"Host not found in Shodan database",
                    }
                else:
                    return {
                        "ip": ip,
                        "error": f"Shodan API error: {error_msg}",
                        "open_ports": None,
                        "banners": None,
                    }

        # Handle generic exceptions
        logger.error("shodan_host_lookup_failed ip=%s: %s", ip, exc)
        return {
            "ip": ip,
            "error": f"Unexpected error: {str(exc)}",
            "open_ports": None,
            "banners": None,
        }


async def research_shodan_search(
    query: str, max_results: int = 10
) -> dict[str, Any]:
    """Search Shodan for devices matching a query.

    Uses Shodan's query syntax for advanced device discovery.
    Example queries:
      - 'apache country:US port:443'
      - 'nginx ssl:"nginx"'
      - 'ssh country:US'
      - 'http.title:"admin" port:8080'

    Args:
        query: Shodan search query string
        max_results: Maximum number of results to return (default 10, max 5000)

    Returns:
        Dict with keys: query, total_results, matches (list of host dicts),
        facets (if available), error (if any)

    Raises:
        shodan.APIError: If search fails
    """
    if not _HAS_SHODAN:
        return {
            "query": query,
            "error": "Shodan SDK not installed. Install with: pip install shodan",
            "total_results": 0,
            "matches": [],
        }

    # Clamp max_results to reasonable bounds
    max_results = max(1, min(max_results, 5000))

    api = _get_shodan_api()
    if not api:
        return {
            "query": query,
            "error": "SHODAN_API_KEY not set in environment",
            "total_results": 0,
            "matches": [],
        }

    try:
        # Wrap sync call in asyncio.to_thread() to avoid blocking event loop
        result = await asyncio.to_thread(_search_devices, api, query, max_results)

        # Extract and format matches
        matches = []
        for match in result.get("matches", []):
            matches.append(
                {
                    "ip": match.get("ip_str"),
                    "port": match.get("port"),
                    "product": match.get("product"),
                    "version": match.get("version"),
                    "cpe": match.get("cpe"),
                    "org": match.get("org"),
                    "isp": match.get("isp"),
                    "country": match.get("country_name"),
                    "country_code": match.get("country_code"),
                    "city": match.get("city"),
                    "timestamp": match.get("timestamp"),
                    "data": match.get("data"),
                }
            )

        return {
            "query": query,
            "total_results": result.get("total", 0),
            "matches": matches,
            "facets": result.get("facets", {}),
            "error": None,
        }

    except Exception as exc:
        error_msg = str(exc)

        # Handle shodan.APIError if shodan is available
        if _HAS_SHODAN and shodan is not None:
            if isinstance(exc, shodan.APIError):
                if "API error 401" in error_msg:
                    return {
                        "query": query,
                        "error": "Invalid or expired SHODAN_API_KEY",
                        "total_results": 0,
                        "matches": [],
                    }
                elif "API error 429" in error_msg:
                    return {
                        "query": query,
                        "error": "Rate limited by Shodan API (quota exceeded)",
                        "total_results": 0,
                        "matches": [],
                    }
                elif "API error 400" in error_msg:
                    return {
                        "query": query,
                        "error": f"Invalid search query: {error_msg}",
                        "total_results": 0,
                        "matches": [],
                    }
                else:
                    return {
                        "query": query,
                        "error": f"Shodan API error: {error_msg}",
                        "total_results": 0,
                        "matches": [],
                    }

        # Handle generic exceptions
        logger.error("shodan_search_failed query=%s: %s", query, exc)
        return {
            "query": query,
            "error": f"Unexpected error: {str(exc)}",
            "total_results": 0,
            "matches": [],
        }


def _fetch_host(api: Any, ip: str) -> dict[str, Any]:
    """Synchronous wrapper for Shodan host lookup.

    This function is called via asyncio.to_thread() to avoid blocking.

    Args:
        api: Shodan API client instance
        ip: IP address to look up

    Returns:
        Raw response dict from Shodan API
    """
    return api.host(ip)


def _search_devices(api: Any, query: str, max_results: int) -> dict[str, Any]:
    """Synchronous wrapper for Shodan search.

    This function is called via asyncio.to_thread() to avoid blocking.

    Args:
        api: Shodan API client instance
        query: Search query string
        max_results: Maximum results to return

    Returns:
        Raw response dict from Shodan API
    """
    return api.search(query, limit=max_results)


def _extract_services(banners: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Extract service information from banner list.

    Args:
        banners: List of banner dicts from Shodan

    Returns:
        List of service dicts with port, product, and version
    """
    services = []
    for banner in banners:
        service = {
            "port": str(banner.get("port", "")),
            "product": banner.get("product", ""),
            "version": banner.get("version", ""),
        }
        if service["product"]:  # Only add if product is present
            services.append(service)
    return services
