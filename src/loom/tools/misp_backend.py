"""research_misp_lookup — Threat intelligence lookup via MISP API.

Provides indicator enrichment and threat correlation using MISP
(Malware Information Sharing Platform) instances.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

try:
    from pymisp import PyMISP

    _HAS_PYMISP = True
except ImportError:
    _HAS_PYMISP = False

logger = logging.getLogger("loom.tools.misp_backend")

# Constraints
INDICATOR_TYPE_MAP = {
    "auto": "auto",
    "domain": "domain",
    "url": "url",
    "ip": "ip-dst",
    "ip-src": "ip-src",
    "ip-dst": "ip-dst",
    "email": "email-src",
    "hash": "md5",
    "md5": "md5",
    "sha1": "sha1",
    "sha256": "sha256",
    "filename": "filename",
    "user-account": "user-account",
    "x509": "x509-fingerprint-sha1",
}

MAX_INDICATOR_LEN = 500
VALID_THREAT_LEVELS = ["low", "medium", "high", "critical"]


def _auto_detect_indicator_type(indicator: str) -> str:
    """Auto-detect indicator type from format.

    Args:
        indicator: Raw indicator string

    Returns:
        MISP indicator type
    """
    indicator = indicator.strip().lower()

    # Check for IP addresses (IPv4 and IPv6)
    ipv4_pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    ipv6_pattern = r"^(?:[0-9a-f]{0,4}:)+[0-9a-f]{0,4}$"

    if re.match(ipv4_pattern, indicator) or re.match(ipv6_pattern, indicator):
        return "ip-dst"

    # Check for MD5, SHA1, SHA256 hashes
    if re.match(r"^[a-f0-9]{32}$", indicator):
        return "md5"
    if re.match(r"^[a-f0-9]{40}$", indicator):
        return "sha1"
    if re.match(r"^[a-f0-9]{64}$", indicator):
        return "sha256"

    # Check for email
    if re.match(r"^[^@]+@[^@]+\.[^@]+$", indicator):
        return "email-src"

    # Check for URL
    if indicator.startswith(("http://", "https://", "ftp://")):
        return "url"

    # Check for domain (basic heuristic)
    if "." in indicator and not indicator.startswith(("http://", "https://", "ftp://")):
        return "domain"

    # Default to URL or domain-like
    return "domain"


async def research_misp_lookup(
    indicator: str,
    indicator_type: str = "auto",
    misp_url: str | None = None,
    include_related: bool = True,
) -> dict[str, Any]:
    """Search for indicator in MISP instance.

    Looks up malware hashes, IPs, domains, and other indicators
    against a MISP instance and returns threat intelligence.

    Args:
        indicator: Indicator to search (IP, domain, hash, URL, email, etc.)
        indicator_type: Type of indicator: 'auto', 'domain', 'url', 'ip',
                       'ip-src', 'ip-dst', 'email', 'hash', 'md5', 'sha1',
                       'sha256', 'filename', 'user-account', 'x509'
                       (default: 'auto')
        misp_url: MISP instance URL (default: MISP_URL env var)
        include_related: Include related indicators in results (default: True)

    Returns:
        Dict with keys:
        - indicator: Input indicator
        - type: Resolved indicator type
        - events: List of MISP events with {id, name, threat_level, date}
        - attributes: List of matching attributes with {type, value, comment}
        - threat_level: Overall threat level (low/medium/high/critical)
        - count: Total number of events found
        - error: Error message if operation failed (optional)
    """
    # Input validation
    if not indicator or not isinstance(indicator, str):
        return {
            "indicator": indicator,
            "error": "indicator must be a non-empty string",
            "type": "unknown",
            "events": [],
            "attributes": [],
            "threat_level": "unknown",
            "count": 0,
        }

    indicator = indicator.strip()
    if len(indicator) > MAX_INDICATOR_LEN:
        return {
            "indicator": indicator[:MAX_INDICATOR_LEN],
            "error": f"indicator length max {MAX_INDICATOR_LEN} chars",
            "type": "unknown",
            "events": [],
            "attributes": [],
            "threat_level": "unknown",
            "count": 0,
        }

    # Resolve indicator type
    if indicator_type not in INDICATOR_TYPE_MAP:
        indicator_type = "auto"

    resolved_type = INDICATOR_TYPE_MAP.get(indicator_type, "auto")

    if resolved_type == "auto":
        resolved_type = _auto_detect_indicator_type(indicator)

    # Get MISP URL
    if not misp_url:
        misp_url = os.environ.get("MISP_URL", "")

    if not misp_url:
        return {
            "indicator": indicator,
            "error": "MISP_URL not configured. Set MISP_URL environment variable.",
            "type": resolved_type,
            "events": [],
            "attributes": [],
            "threat_level": "unknown",
            "count": 0,
        }

    # Ensure URL format
    misp_url = str(misp_url).strip()
    if not misp_url.startswith(("http://", "https://")):
        misp_url = f"https://{misp_url}"

    # Check if PyMISP is installed
    if not _HAS_PYMISP:
        return {
            "indicator": indicator,
            "error": "pymisp library not installed. Install with: pip install pymisp",
            "type": resolved_type,
            "events": [],
            "attributes": [],
            "threat_level": "unknown",
            "count": 0,
            "library_installed": False,
        }

    try:
        # Run in executor to avoid blocking event loop
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            _run_misp_lookup,
            indicator,
            resolved_type,
            misp_url,
            include_related,
        )
        return result

    except Exception as e:
        logger.error("misp_lookup_failed indicator=%s: %s", indicator[:30], e)
        return {
            "indicator": indicator,
            "error": f"MISP lookup error: {str(e)}",
            "type": resolved_type,
            "events": [],
            "attributes": [],
            "threat_level": "unknown",
            "count": 0,
        }


def _run_misp_lookup(
    indicator: str,
    resolved_type: str,
    misp_url: str,
    include_related: bool,
) -> dict[str, Any]:
    """Run MISP lookup in executor thread.

    Args:
        indicator: Indicator to search
        resolved_type: Resolved indicator type
        misp_url: MISP instance URL
        include_related: Include related indicators

    Returns:
        Lookup result dict
    """
    try:
        logger.info(
            "misp_lookup_start indicator=%s type=%s misp_url=%s",
            indicator[:30],
            resolved_type,
            misp_url,
        )

        # Get API key
        misp_api_key = os.environ.get("MISP_API_KEY", "")
        if not misp_api_key:
            return {
                "indicator": indicator,
                "error": "MISP_API_KEY not configured. Set MISP_API_KEY environment variable.",
                "type": resolved_type,
                "events": [],
                "attributes": [],
                "threat_level": "unknown",
                "count": 0,
            }

        # Initialize MISP client
        misp = PyMISP(misp_url, misp_api_key, ssl=True)

        # Search for indicator
        results = misp.search(
            controller="attributes",
            type_attribute=resolved_type,
            value=indicator,
            include_context=True,
        )

        # Parse results
        events = []
        attributes = []
        threat_levels = []

        if isinstance(results, dict):
            # Handle response format
            response_data = results.get("response", results.get("Attribute", []))

            if isinstance(response_data, list):
                for item in response_data:
                    if isinstance(item, dict):
                        # Extract attribute
                        attr_data = item.get("Attribute", item)
                        if isinstance(attr_data, dict):
                            attributes.append({
                                "type": attr_data.get("type", ""),
                                "value": attr_data.get("value", ""),
                                "comment": attr_data.get("comment", ""),
                                "timestamp": attr_data.get("timestamp"),
                            })

                            # Extract associated event
                            if "Event" in attr_data:
                                event = attr_data["Event"]
                                if isinstance(event, dict):
                                    event_dict = {
                                        "id": event.get("id", ""),
                                        "name": event.get("name", event.get("info", "")),
                                        "threat_level": event.get("threat_level_id", ""),
                                        "date": event.get("date", ""),
                                    }
                                    if event_dict not in events:
                                        events.append(event_dict)

                                    # Collect threat levels
                                    level_id = event.get("threat_level_id")
                                    if level_id:
                                        threat_levels.append(level_id)

        # Determine overall threat level
        threat_level = "unknown"
        if threat_levels:
            # Simple heuristic: if any critical, result is critical
            if "4" in threat_levels:  # 4 = critical
                threat_level = "critical"
            elif "3" in threat_levels:  # 3 = high
                threat_level = "high"
            elif "2" in threat_levels:  # 2 = medium
                threat_level = "medium"
            else:
                threat_level = "low"

        logger.info(
            "misp_lookup_complete indicator=%s type=%s events=%d attributes=%d threat=%s",
            indicator[:30],
            resolved_type,
            len(events),
            len(attributes),
            threat_level,
        )

        return {
            "indicator": indicator,
            "type": resolved_type,
            "events": events,
            "attributes": attributes,
            "threat_level": threat_level,
            "count": len(events),
            "library_installed": True,
        }

    except Exception as e:
        logger.error("misp_lookup_internal_error indicator=%s: %s", indicator[:30], e)
        return {
            "indicator": indicator,
            "error": f"MISP lookup error: {str(e)}",
            "type": resolved_type,
            "events": [],
            "attributes": [],
            "threat_level": "unknown",
            "count": 0,
        }
