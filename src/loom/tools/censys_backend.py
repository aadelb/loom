"""Censys backend — host lookup and search for infrastructure reconnaissance.

Censys is an attack surface management platform that provides searchable data
on certificates, hosts, and services. This module provides wrappers around the
Censys Python SDK for host lookups and host searches with detailed service,
TLS, and location information.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

from loom.input_validators import ValidationError, validate_ip
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.censys_backend")

try:
    from censys.search import CensysHosts
    CENSYS_AVAILABLE = True
except ImportError:
    CENSYS_AVAILABLE = False


def _validate_query(query: str) -> str:
    """Validate Censys query string.

    Args:
        query: Censys query (e.g., "services.service_name: HTTP")

    Returns:
        The validated query

    Raises:
        ValueError: if query is invalid
    """
    query = query.strip() if isinstance(query, str) else ""

    if not query or len(query) > 1000:
        raise ValueError("query must be 1-1000 characters")

    # Allow alphanumeric, spaces, colons, dots, hyphens, quotes, parentheses, AND/OR
    if not re.match(r"^[a-zA-Z0-9\s:._\-\"'()&|]+$", query):
        raise ValueError("query contains disallowed characters")

    return query


def _validate_max_results(max_results: int) -> int:
    """Validate max_results parameter.

    Args:
        max_results: maximum number of results to return

    Returns:
        The validated max_results

    Raises:
        ValueError: if max_results is invalid
    """
    if not isinstance(max_results, int) or max_results < 1 or max_results > 1000:
        raise ValueError("max_results must be an integer between 1 and 1000")

    return max_results


def _check_censys_available() -> tuple[bool, str]:
    """Check if Censys API credentials are available.

    Returns:
        Tuple of (available: bool, message: str)
    """
    api_id = os.environ.get("CENSYS_API_ID")
    api_secret = os.environ.get("CENSYS_API_SECRET")

    if not api_id or not api_secret:
        return False, (
            "Censys API credentials not found. "
            "Set CENSYS_API_ID and CENSYS_API_SECRET environment variables. "
            "Get credentials at https://censys.io"
        )

    if not CENSYS_AVAILABLE:
        return False, (
            "Censys Python SDK not installed. "
            "Install with: pip install censys"
        )

    return True, "Censys API available"


@handle_tool_errors("research_censys_host")
async def research_censys_host(ip: str) -> dict[str, Any]:
    """Look up host on Censys — TLS certs, services, protocols.

    Queries Censys for detailed information on a specific IP address,
    including hosted services, TLS certificates, location, and protocols.

    Args:
        ip: IPv4 or IPv6 address to look up

    Returns:
        Dict with:
        - ip: the queried IP address
        - services: list of detected services with ports and protocols
        - tls_certs: list of TLS certificates (subject, issuer, validity)
        - location: geolocation data (country, latitude, longitude)
        - protocols: list of detected protocols
        - autonomous_system: AS number and organization
        - censys_available: bool indicating if API is available
        - error: error message if lookup failed (optional)
    """
    try:
        ip = validate_ip(ip)
    except ValidationError as exc:
        return {
            "ip": ip,
            "error": str(exc),
            "censys_available": False,
        }

    # Check if Censys is available
    available, msg = _check_censys_available()
    if not available:
        return {
            "ip": ip,
            "error": msg,
            "censys_available": False,
        }

    try:
        api_id = os.environ.get("CENSYS_API_ID", "")
        api_secret = os.environ.get("CENSYS_API_SECRET", "")

        # Create Censys client and run lookup in thread
        def _lookup() -> dict[str, Any]:
            try:
                client = CensysHosts(api_id=api_id, api_secret=api_secret)
                host_data = client.view(ip)
                return host_data if isinstance(host_data, dict) else {}
            except Exception as e:
                logger.debug("censys_lookup_error ip=%s: %s", ip, e)
                return {}

        host_data = await asyncio.to_thread(_lookup)
        if not host_data:
            return {
                "ip": ip,
                "error": "Censys lookup returned empty response",
                "censys_available": True,
            }

        # Extract and structure relevant data
        result: dict[str, Any] = {
            "ip": ip,
            "censys_available": True,
            "services": [],
            "tls_certs": [],
            "location": None,
            "protocols": [],
            "autonomous_system": None,
        }

        # Extract services
        if "services" in host_data:
            for service in host_data.get("services", []):
                service_info = {
                    "port": service.get("port"),
                    "protocol": service.get("service_name"),
                    "banner": service.get("banner", "").strip()[:200],  # Truncate to 200 chars
                }
                result["services"].append(service_info)

        # Extract TLS certificates
        if "tls" in host_data:
            tls_info = host_data.get("tls", {})
            certificates = tls_info.get("certificates", [])
            for cert in certificates:
                cert_info = {
                    "subject": cert.get("subject", {}).get("common_name"),
                    "issuer": cert.get("issuer", {}).get("common_name"),
                    "valid_from": cert.get("validity", {}).get("not_before"),
                    "valid_until": cert.get("validity", {}).get("not_after"),
                    "fingerprint": cert.get("fingerprint", "")[:64],  # SHA-256 is 64 hex chars
                }
                result["tls_certs"].append(cert_info)

        # Extract location
        if "location" in host_data:
            location = host_data.get("location", {})
            result["location"] = {
                "country": location.get("country"),
                "latitude": location.get("latitude"),
                "longitude": location.get("longitude"),
            }

        # Extract protocols
        if "protocols" in host_data:
            result["protocols"] = host_data.get("protocols", [])

        # Extract autonomous system
        if "autonomous_system" in host_data:
            asn = host_data.get("autonomous_system", {})
            result["autonomous_system"] = {
                "asn": asn.get("asn"),
                "name": asn.get("name"),
            }

        return result

    except Exception as exc:
        logger.warning("censys_host_lookup_failed ip=%s: %s", ip, exc)
        return {
            "ip": ip,
            "error": str(exc),
            "censys_available": True,
        }


@handle_tool_errors("research_censys_search")
async def research_censys_search(
    query: str,
    max_results: int = 10,
) -> dict[str, Any]:
    """Search Censys for hosts matching criteria.

    Censys query syntax examples:
    - 'services.service_name: HTTP AND location.country: US'
    - 'services.http.status_code: 200'
    - 'tls.certificates.parsed.subject.common_name: *.google.com'

    Args:
        query: Censys query string using their query language
        max_results: maximum number of results to return (1-1000, default 10)

    Returns:
        Dict with:
        - query: the executed query
        - max_results: the limit on results
        - results: list of matching hosts with IP, services, and score
        - total_results: approximate total matches in Censys
        - censys_available: bool indicating if API is available
        - error: error message if search failed (optional)
    """
    try:
        query = _validate_query(query)
        max_results = _validate_max_results(max_results)
    except ValueError as exc:
        return {
            "query": query,
            "error": str(exc),
            "censys_available": False,
        }

    # Check if Censys is available
    available, msg = _check_censys_available()
    if not available:
        return {
            "query": query,
            "error": msg,
            "censys_available": False,
        }

    try:
        api_id = os.environ.get("CENSYS_API_ID", "")
        api_secret = os.environ.get("CENSYS_API_SECRET", "")

        # Create Censys client and run search in thread
        def _search() -> dict[str, Any]:
            try:
                client = CensysHosts(api_id=api_id, api_secret=api_secret)
                results = []
                total = 0

                # Iterate through pages, respecting max_results limit
                for page, host in enumerate(client.search(query)):
                    if len(results) >= max_results:
                        break

                    if isinstance(host, dict):
                        results.append(host)

                # Get total estimate from query metadata
                # Note: Censys API may not expose total directly via iterator
                # This is a fallback; actual total may differ
                total = len(results)

                return {"results": results, "total": total}
            except Exception as e:
                logger.debug("censys_search_error query=%s: %s", query, e)
                return {"results": [], "total": 0}

        search_data = await asyncio.to_thread(_search)
        if not isinstance(search_data, dict):
            return {
                "query": query,
                "error": "Censys search returned invalid response",
                "censys_available": True,
            }

        result: dict[str, Any] = {
            "query": query,
            "max_results": max_results,
            "censys_available": True,
            "results": [],
            "total_results": search_data.get("total", 0),
        }

        # Structure results
        for host in search_data.get("results", []):
            host_entry = {
                "ip": host.get("ip"),
                "services": [],
                "last_updated": host.get("last_updated"),
                "score": host.get("score"),
            }

            # Extract services from this host
            if "services" in host:
                for service in host.get("services", []):
                    service_info = {
                        "port": service.get("port"),
                        "protocol": service.get("service_name"),
                    }
                    host_entry["services"].append(service_info)

            result["results"].append(host_entry)

        return result

    except Exception as exc:
        logger.warning("censys_search_failed query=%s: %s", query, exc)
        return {
            "query": query,
            "error": str(exc),
            "censys_available": True,
        }
