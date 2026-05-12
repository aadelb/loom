"""IP intelligence tools — reputation checking, geolocation, and metadata."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

from loom.input_validators import ValidationError, validate_ip

logger = logging.getLogger("loom.tools.ip_intel")

_IP_API_URL = "https://ip-api.com/json"
_IPINFO_URL = "https://ipinfo.io"
_ABUSEIPDB_URL = "https://api.abuseipdb.com/api/v2/check"


async def research_ip_reputation(ip: str) -> dict[str, Any]:
    """Check IP reputation using free APIs (no API key needed).

    Queries multiple sources:
    - AbuseIPDB (if API key set)
    - ip-api.com geolocation
    - ipinfo.io geolocation

    Args:
        ip: IPv4 or IPv6 address to check

    Returns:
        Dict with keys: ip, geolocation, abuse_score, is_tor_exit, reverse_dns
    """
    # Validate IP
    try:
        validate_ip(ip)
    except ValidationError:
        return {
            "ip": ip,
            "error": "Invalid IP address or private IP not allowed",
            "geolocation": None,
            "abuse_score": None,
            "is_tor_exit": None,
            "reverse_dns": None,
        }

    result: dict[str, Any] = {
        "ip": ip,
        "geolocation": None,
        "abuse_score": None,
        "is_tor_exit": None,
        "reverse_dns": None,
    }

    # Try reverse DNS
    try:
        import socket

        reverse_dns = socket.gethostbyaddr(ip)[0]
        result["reverse_dns"] = reverse_dns
    except Exception as e:
        logger.debug("reverse_dns_lookup_error: %s", e)

    # Check AbuseIPDB if API key is set
    abuseipdb_key = os.environ.get("ABUSEIPDB_API_KEY")
    if abuseipdb_key:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    _ABUSEIPDB_URL,
                    params={"ipAddress": ip, "maxAgeInDays": 90},
                    headers={"Key": abuseipdb_key, "Accept": "application/json"},
                )
                resp.raise_for_status()
                data = resp.json()
                if data.get("data"):
                    result["abuse_score"] = data["data"].get("abuseConfidenceScore")
                    result["is_tor_exit"] = data["data"].get("isTor")
        except Exception as exc:
            logger.warning("abuseipdb_check_failed ip=%s: %s", ip, exc)

    # Query ip-api.com (free, no key, 45 req/min)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{_IP_API_URL}/{ip}")
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "success":
                result["geolocation"] = {
                    "country": data.get("country"),
                    "city": data.get("city"),
                    "org": data.get("org"),
                    "isp": data.get("isp"),
                    "lat": data.get("lat"),
                    "lon": data.get("lon"),
                }
    except Exception as exc:
        logger.warning("ip_api_lookup_failed ip=%s: %s", ip, exc)

    return result


async def research_ip_geolocation(ip: str) -> dict[str, Any]:
    """Get geolocation for an IP address (lightweight, free).

    Uses ip-api.com free tier (45 requests/minute).

    Args:
        ip: IPv4 or IPv6 address to geolocate

    Returns:
        Dict with keys: ip, country, region, city, lat, lon, timezone, isp, org
    """
    # Validate IP
    try:
        validate_ip(ip)
    except ValidationError:
        return {
            "ip": ip,
            "error": "Invalid IP address or private IP not allowed",
            "country": None,
            "region": None,
            "city": None,
            "lat": None,
            "lon": None,
            "timezone": None,
            "isp": None,
            "org": None,
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{_IP_API_URL}/{ip}")
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") == "success":
            return {
                "ip": ip,
                "country": data.get("country"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "timezone": data.get("timezone"),
                "isp": data.get("isp"),
                "org": data.get("org"),
            }
        else:
            return {
                "ip": ip,
                "error": data.get("message", "lookup failed"),
                "country": None,
                "region": None,
                "city": None,
                "lat": None,
                "lon": None,
                "timezone": None,
                "isp": None,
                "org": None,
            }

    except Exception as exc:
        logger.warning("ip_geolocation_failed ip=%s: %s", ip, exc)
        return {
            "ip": ip,
            "error": str(exc),
            "country": None,
            "region": None,
            "city": None,
            "lat": None,
            "lon": None,
            "timezone": None,
            "isp": None,
            "org": None,
        }
