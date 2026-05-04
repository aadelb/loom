"""theHarvester email/subdomain OSINT backend — gather email addresses and subdomains.

theHarvester is a powerful open-source tool for email and subdomain reconnaissance.
This module provides a wrapper around the theHarvester CLI with subprocess execution
and output parsing. It searches multiple sources (Google, Bing, LinkedIn, etc.) to
identify email addresses, subdomains, IP addresses, and other information related
to a target domain.

Uses theHarvester as a subprocess since it's not easily pip-installable as a library.
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from typing import Any

logger = logging.getLogger("loom.tools.harvester_backend")


def _validate_domain(domain: str) -> str:
    """Validate domain for theHarvester lookup.

    theHarvester accepts domains that are valid DNS names.
    We validate but keep restrictions permissive to allow international domains.

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

    # Allow alphanumeric, hyphen, period
    # Disallow only command-injection chars and spaces
    if not re.match(r"^[a-z0-9.\-]+$", domain, re.IGNORECASE):
        raise ValueError("domain contains disallowed characters")

    return domain


def _validate_sources(sources: str) -> str:
    """Validate sources parameter for theHarvester.

    Sources can be 'all' or comma-separated list like 'google,bing,linkedin'.

    Args:
        sources: sources to validate

    Returns:
        The validated sources string

    Raises:
        ValueError: if sources is invalid
    """
    sources = sources.strip() if isinstance(sources, str) else ""

    if not sources or len(sources) > 255:
        raise ValueError("sources must be 1-255 characters")

    # Allow alphanumeric, comma, and hyphen
    if not re.match(r"^[a-z0-9,\-]+$", sources, re.IGNORECASE):
        raise ValueError("sources contains disallowed characters")

    return sources


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
        if result.returncode == 0:
            return True, "theHarvester CLI found"
        else:
            return False, f"theHarvester help check failed: {result.stderr}"
    except FileNotFoundError:
        return False, (
            "theHarvester CLI not found. Install with: pip install theHarvester"
        )
    except subprocess.TimeoutExpired:
        return False, "theHarvester CLI timeout during availability check"
    except Exception as exc:
        return False, f"theHarvester availability check error: {str(exc)}"


def _parse_harvester_output(stdout: str, stderr: str) -> tuple[list[str], list[str], list[str]]:
    """Parse theHarvester stdout/stderr for emails, subdomains, and IPs.

    theHarvester outputs results in plain text format with clear section headers.
    Example output sections:
      Emails found:
      ============
      user@example.com

      Hosts found:
      ============
      subdomain.example.com

      IPs found:
      =========
      192.168.1.1

    Args:
        stdout: stdout from theHarvester subprocess
        stderr: stderr from theHarvester subprocess

    Returns:
        Tuple of (emails, subdomains, ips)
    """
    emails: list[str] = []
    subdomains: list[str] = []
    ips: list[str] = []

    # Combined output to parse
    output = stdout + "\n" + stderr

    lines = output.split("\n")
    current_section = None

    for i, line in enumerate(lines):
        line = line.strip()

        # Detect section headers
        if "Emails found" in line or "Emails found:" in line:
            current_section = "emails"
            continue
        elif "Hosts found" in line or "Hosts found:" in line:
            current_section = "hosts"
            continue
        elif "IPs found" in line or "IPs found:" in line:
            current_section = "ips"
            continue
        elif line.startswith("===") or line.startswith("---"):
            # Skip separator lines
            continue
        elif not line or line.startswith("["):
            # Skip empty lines and log lines
            current_section = None
            continue

        # Parse based on current section
        if current_section == "emails":
            # Match email pattern: user@domain.ext
            if re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", line):
                if line not in emails:
                    emails.append(line)

        elif current_section == "hosts":
            # Match domain/subdomain pattern
            if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", line):
                if line not in subdomains:
                    subdomains.append(line)

        elif current_section == "ips":
            # Match IP pattern (IPv4 or IPv6)
            if re.match(
                r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|[a-fA-F0-9:]+)$", line
            ):
                if line not in ips:
                    ips.append(line)

    return emails, subdomains, ips


def research_harvest(
    domain: str, sources: str = "all", limit: int = 100
) -> dict[str, Any]:
    """Search for emails and subdomains using theHarvester.

    Searches the specified domain across multiple sources (Google, Bing, LinkedIn,
    etc.) to identify email addresses, subdomains, IP addresses, and other
    reconnaissance information.

    Args:
        domain: target domain to harvest (e.g., "example.com")
        sources: comma-separated list of sources or "all" for all sources
                 (e.g., "google,bing,linkedin" or "all")
        limit: maximum number of results per source to return (default 100)

    Returns:
        Dict with:
        - domain: the target domain
        - emails: list of email addresses found
        - subdomains: list of subdomains found
        - ips: list of IP addresses found
        - sources_used: the sources parameter used
        - duration_ms: execution time in milliseconds
        - harvester_available: bool indicating if theHarvester CLI is available
        - error: error message if lookup failed (optional)
    """
    try:
        domain = _validate_domain(domain)
    except ValueError as exc:
        return {"domain": domain, "error": str(exc), "harvester_available": False}

    try:
        sources = _validate_sources(sources)
    except ValueError as exc:
        return {"domain": domain, "error": str(exc), "harvester_available": False}

    # Check if harvester is available
    available, msg = _check_harvester_available()
    if not available:
        return {
            "domain": domain,
            "error": msg,
            "harvester_available": False,
        }

    try:
        # Record start time
        start_time = time.time()

        # Build theHarvester command
        cmd = ["theHarvester", "-d", domain, "-b", sources, "-l", str(limit)]

        # Run theHarvester
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for large harvests
        )

        # Parse output
        emails, subdomains, ips = _parse_harvester_output(result.stdout, result.stderr)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        output: dict[str, Any] = {
            "domain": domain,
            "emails": emails,
            "subdomains": subdomains,
            "ips": ips,
            "sources_used": sources,
            "duration_ms": duration_ms,
            "harvester_available": True,
        }

        return output

    except subprocess.TimeoutExpired:
        return {
            "domain": domain,
            "error": "theHarvester lookup timed out after 300 seconds",
            "harvester_available": True,
        }
    except Exception as exc:
        return {
            "domain": domain,
            "error": f"theHarvester lookup error: {str(exc)}",
            "harvester_available": True,
        }
