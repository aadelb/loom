"""MISP (Malware Information Sharing Platform) threat intelligence integration.

Connects to MISP instances to search for indicators of compromise (IoCs)
including IPs, domains, hashes, and emails.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.misp_backend")


def _detect_indicator_type(indicator: str) -> str:
    """Automatically detect indicator type from its format.

    Args:
        indicator: The indicator string to classify

    Returns:
        Type string: 'ip', 'domain', 'hash', 'email', or 'unknown'
    """
    indicator = indicator.strip().lower()

    # Check for IPv4
    if re.match(r"^(\d{1,3}\.){3}\d{1,3}$", indicator):
        parts = indicator.split(".")
        if all(0 <= int(p) <= 255 for p in parts):
            return "ip"

    # Check for IPv6
    if ":" in indicator and re.match(r"^([0-9a-f]{0,4}:){2,}", indicator):
        return "ip"

    # Check for hash (MD5: 32 hex, SHA1: 40 hex, SHA256: 64 hex)
    if re.match(r"^[a-f0-9]{32}$", indicator):
        return "hash"  # MD5
    if re.match(r"^[a-f0-9]{40}$", indicator):
        return "hash"  # SHA1
    if re.match(r"^[a-f0-9]{64}$", indicator):
        return "hash"  # SHA256

    # Check for email
    if "@" in indicator and re.match(r"^[^@]+@[^@]+\.[^@]+$", indicator):
        return "email"

    # Check for domain (basic heuristic)
    if (
        "." in indicator
        and "/" not in indicator
        and re.match(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$", indicator)
    ):
        return "domain"

    return "unknown"


@handle_tool_errors("research_misp_lookup")
async def research_misp_lookup(
    indicator: str,
    indicator_type: str = "auto",
) -> dict[str, Any]:
    """Search MISP for indicators of compromise.

    Connects to a MISP instance (via MISP_URL and MISP_API_KEY env vars)
    and searches for the given indicator. Returns matching events with
    threat levels and metadata.

    Args:
        indicator: The IoC to search for (IP, domain, hash, email, etc)
        indicator_type: Type hint ('auto' for auto-detection, or explicit type)

    Returns:
        Dict with keys:
        - indicator: The searched indicator
        - type: Detected or provided indicator type
        - events: List of matching MISP events [id, info, threat_level, date, ...]
        - total_events: Count of matching events
        - error: Error message if any (instead of events on failure)
    """
    # Auto-detect type if needed
    if indicator_type == "auto":
        indicator_type = _detect_indicator_type(indicator)

    result: dict[str, Any] = {
        "indicator": indicator,
        "type": indicator_type,
        "total_events": 0,
        "events": [],
        "error": None,
    }

    # Check if PyMISP is available
    try:
        from pymisp import PyMISP
    except ImportError:
        logger.debug("pymisp not installed")
        result["error"] = "pymisp not installed"
        return result

    # Get MISP credentials from environment
    misp_url = os.environ.get("MISP_URL")
    misp_api_key = os.environ.get("MISP_API_KEY")

    if not misp_url or not misp_api_key:
        logger.debug("MISP_URL or MISP_API_KEY not configured")
        result["error"] = "MISP_URL or MISP_API_KEY not configured in environment"
        return result

    try:
        # Initialize MISP connection with timeout
        ssl_verify = os.environ.get("MISP_SSL_VERIFY", "true").lower() == "true"
        misp = PyMISP(misp_url, misp_api_key, ssl=ssl_verify, timeout=15.0)

        # Search for the indicator
        response = misp.search(
            controller="attributes",
            value=indicator,
            includeEventUuid=True,
            includeEventInfo=True,
            returnFormat="json",
        )

        # Parse response
        if isinstance(response, dict) and "response" in response:
            attributes = response["response"]
            if isinstance(attributes, list):
                events_dict: dict[str, dict[str, Any]] = {}

                # Aggregate events from attributes
                for attr in attributes:
                    if isinstance(attr, dict) and "Attribute" in attr:
                        attr_data = attr["Attribute"]
                        event_id = attr_data.get("event_id")
                        event_obj = attr.get("Event", {})
                        if event_id:
                            if event_id not in events_dict:
                                events_dict[event_id] = {
                                    "id": event_id,
                                    "info": event_obj.get("info", ""),
                                    "threat_level": event_obj.get("threat_level_id"),
                                    "date": event_obj.get("date"),
                                    "attribute_count": 0,
                                }
                            events_dict[event_id]["attribute_count"] += 1

                result["events"] = list(events_dict.values())
                result["total_events"] = len(events_dict)
                logger.info("misp_lookup_success: found %d events for %s", len(events_dict), indicator_type)
            else:
                logger.debug("unexpected misp response format: %s", type(attributes))
        else:
            logger.debug("unexpected misp response structure: %s", response)

    except Exception as e:
        logger.error("misp_lookup_error: %s", e)
        result["error"] = "MISP lookup failed due to connection or parsing error"

    return result
