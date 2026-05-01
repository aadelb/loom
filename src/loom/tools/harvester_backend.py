"""theHarvester OSINT backend — email and subdomain discovery from public sources.

theHarvester is an open-source tool that gathers email addresses, subdomains,
IP addresses, and other data from public sources like search engines, DNS,
and threat intelligence feeds. This module provides a wrapper around the
theHarvester CLI with subprocess execution and output parsing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
import tempfile
import uuid
from typing import Any

logger = logging.getLogger("loom.tools.harvester_backend")


def _validate_domain(domain: str) -> str:
    """Validate domain name for theHarvester lookup.

    Args:
        domain: domain to validate

    Returns:
        The validated domain string

    Raises:
        ValueError: if domain is invalid
    """
    domain = domain.strip() if isinstance(domain, str) else ""

    if not domain or len(domain) > 255:
        raise ValueError("domain must be 1-255 characters")

    # Basic domain validation (alphanumeric, dots, hyphens)
    if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", domain, re.IGNORECASE):
        raise ValueError("domain format is invalid")

    return domain


def _validate_sources(sources: str) -> str:
    """Validate sources parameter for theHarvester.

    Args:
        sources: comma-separated list of sources or "all"

    Returns:
        The validated sources string

    Raises:
        ValueError: if sources is invalid
    """
    sources = sources.strip() if isinstance(sources, str) else ""

    if not sources:
        raise ValueError("sources must not be empty")

    if len(sources) > 1000:
        raise ValueError("sources string is too long")

    # Allow comma-separated alphanumeric with underscores or "all"
    if sources.lower() == "all":
        return "all"

    # Validate comma-separated list
    parts = sources.split(",")
    for part in parts:
        part = part.strip()
        if not re.match(r"^[a-z0-9_-]+$", part, re.IGNORECASE):
            raise ValueError(f"invalid source name: {part}")

    return sources


def _validate_limit(limit: int) -> int:
    """Validate limit parameter.

    Args:
        limit: maximum number of results

    Returns:
        The validated limit value

    Raises:
        ValueError: if limit is invalid
    """
    if not isinstance(limit, int):
        raise ValueError("limit must be an integer")

    if limit < 1 or limit > 10000:
        raise ValueError("limit must be between 1 and 10000")

    return limit


def _check_harvester_available() -> tuple[bool, str]:
    """Check if theHarvester CLI is available.

    Returns:
        Tuple of (available: bool, message: str)
    """
    try:
        result = subprocess.run(
            ["theHarvester", "-h"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 or "usage" in result.stdout.lower():
            return True, "theHarvester CLI found"
        else:
            return False, f"theHarvester check failed: {result.stderr}"
    except FileNotFoundError:
        return False, (
            "theHarvester CLI not found. Install with: pip install theHarvester"
        )
    except subprocess.TimeoutExpired:
        return False, "theHarvester CLI timeout during version check"
    except Exception as exc:
        return False, f"theHarvester availability check error: {str(exc)}"


async def research_harvest(
    domain: str, sources: str = "all", limit: int = 500
) -> dict[str, Any]:
    """Discover emails, subdomains, and IPs for a domain using theHarvester.

    Searches public sources (search engines, DNS, threat intelligence feeds)
    for information about a given domain including email addresses, subdomains,
    and IP addresses.

    Args:
        domain: domain to search for (e.g., "example.com")
        sources: comma-separated list of sources or "all" (default: "all")
                 Common sources: google, bing, duckduckgo, baidu, dnsdumpster, etc.
        limit: maximum number of results per category (default: 500)

    Returns:
        Dict with:
        - domain: the searched domain
        - emails: list of discovered email addresses
        - subdomains: list of discovered subdomains
        - ips: list of discovered IP addresses
        - hosts: list of discovered hosts with IP addresses
        - sources_used: list of sources that were searched
        - total_emails: count of unique emails found
        - total_subdomains: count of unique subdomains found
        - harvester_available: bool indicating if theHarvester CLI is available
        - error: error message if lookup failed (optional)
    """
    try:
        domain = _validate_domain(domain)
        sources = _validate_sources(sources)
        limit = _validate_limit(limit)
    except ValueError as exc:
        return {
            "domain": domain,
            "error": str(exc),
            "harvester_available": False,
        }

    # Check if harvester is available
    available, msg = _check_harvester_available()
    if not available:
        return {
            "domain": domain,
            "error": msg,
            "harvester_available": False,
        }

    try:
        # Create temp file for output (use uuid to avoid conflicts)
        output_base = f"/tmp/harvest_{uuid.uuid4().hex}"

        # Build theHarvester command
        cmd = [
            "theHarvester",
            "-d",
            domain,
            "-b",
            sources,
            "-l",
            str(limit),
            "-f",
            f"{output_base}.json",
        ]

        # Run theHarvester asynchronously
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # theHarvester can be slow
        )

        # Parse the JSON output
        output: dict[str, Any] = {
            "domain": domain,
            "harvester_available": True,
        }

        try:
            # Try to read the JSON output file
            json_file = f"{output_base}.json"
            with open(json_file, "r") as f:
                harvest_data = json.load(f)

            # Extract data from theHarvester JSON output
            output["emails"] = list(
                set(harvest_data.get("emails", []))
            )  # Deduplicate
            output["subdomains"] = list(
                set(harvest_data.get("subdomains", []))
            )
            output["ips"] = list(set(harvest_data.get("ips", [])))
            output["hosts"] = harvest_data.get("hosts", [])
            output["sources_used"] = harvest_data.get("sources_used", [])
            output["total_emails"] = len(output["emails"])
            output["total_subdomains"] = len(output["subdomains"])

        except (json.JSONDecodeError, IOError, FileNotFoundError) as exc:
            # Fallback: return empty results with warning
            output["emails"] = []
            output["subdomains"] = []
            output["ips"] = []
            output["hosts"] = []
            output["sources_used"] = []
            output["total_emails"] = 0
            output["total_subdomains"] = 0
            output["warning"] = f"Could not parse theHarvester output: {str(exc)}"

        return output

    except subprocess.TimeoutExpired:
        return {
            "domain": domain,
            "error": "theHarvester lookup timed out after 300 seconds",
            "harvester_available": True,
        }
    except Exception as exc:
        logger.exception("theHarvester lookup failed")
        return {
            "domain": domain,
            "error": f"theHarvester lookup error: {str(exc)}",
            "harvester_available": True,
        }
