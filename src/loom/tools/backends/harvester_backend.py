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
import time
from typing import Any

from loom.input_validators import validate_domain, validate_email, validate_ip, ValidationError
from loom.error_responses import handle_tool_errors
from loom.subprocess_helpers import run_command

logger = logging.getLogger("loom.tools.harvester_backend")


def _validate_sources(sources: str) -> str:
    """Validate sources parameter for theHarvester.

    Sources can be 'all' or comma-separated list of valid source names.
    Uses allowlist to prevent injection.

    Args:
        sources: sources to validate (e.g., "all" or "google,bing,linkedin")

    Returns:
        The validated sources string

    Raises:
        ValidationError: if sources is invalid
    """
    sources = sources.strip() if isinstance(sources, str) else ""

    if not sources or len(sources) > 255:
        raise ValidationError("sources must be 1-255 characters")

    # Allowlist of valid theHarvester sources
    VALID_SOURCES = {
        "all", "google", "bing", "linkedin", "twitter", "asana",
        "github", "yahoo", "baidu", "shodan", "censys", "dnsdumpster",
        "duckduckgo", "dogpile", "zoomeye", "qwant", "otx", "grep",
        "fullhunt", "security", "hunter", "intelx", "binaryedge"
    }

    if sources.lower() == "all":
        return sources

    # Validate comma-separated sources
    source_list = [s.strip().lower() for s in sources.split(",")]
    for source in source_list:
        if not source or source not in VALID_SOURCES:
            raise ValidationError(
                f"invalid source '{source}'. valid sources: {', '.join(sorted(VALID_SOURCES))}"
            )

    return sources


def _check_harvester_available() -> tuple[bool, str]:
    """Check if theHarvester CLI is available.

    Returns:
        Tuple of (available: bool, message: str)
    """
    try:
        result = run_command(
            ["theHarvester", "-h"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result["success"]:
            return True, "theHarvester CLI found"
        else:
            return False, f"theHarvester help check failed: {result["stderr"]}"
    except FileNotFoundError:
        return False, (
            "theHarvester CLI not found. Install with: pip install theHarvester"
        )
    except subprocess.TimeoutExpired:
        return False, "theHarvester CLI timeout during availability check"
    except Exception as exc:
        return False, f"theHarvester availability check error: {str(exc)}"


def _is_valid_subdomain(subdomain: str) -> bool:
    """Validate subdomain format.

    Args:
        subdomain: subdomain string to validate

    Returns:
        True if subdomain is valid DNS name
    """
    if not subdomain or len(subdomain) > 253:
        return False
    if subdomain.startswith(".") or subdomain.endswith("."):
        return False
    if ".." in subdomain or "." not in subdomain:
        return False

    for label in subdomain.split("."):
        if not label or len(label) > 63:
            return False
        if not re.match(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$", label, re.IGNORECASE):
            return False

    return True


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
        Tuple of (emails, subdomains, ips) — each as sorted deduplicated lists
    """
    emails_set: set[str] = set()
    subdomains_set: set[str] = set()
    ips_set: set[str] = set()

    # Combined output to parse (prefer stdout, fall back to stderr)
    output = stdout if stdout else stderr

    lines = output.split("\n")
    current_section = None

    for line in lines:
        line = line.strip()

        # Detect section headers (case-insensitive)
        if re.search(r"emails?\s*found", line, re.IGNORECASE):
            current_section = "emails"
            continue
        elif re.search(r"hosts?\s*found", line, re.IGNORECASE):
            current_section = "hosts"
            continue
        elif re.search(r"ip", line, re.IGNORECASE) and "found" in line.lower():
            current_section = "ips"
            continue

        # Skip separator lines, empty lines, and log lines
        if line.startswith("===") or line.startswith("---") or not line or line.startswith("["):
            continue

        # Parse based on current section
        if current_section == "emails":
            try:
                validate_email(line)
                emails_set.add(line)
            except ValidationError:
                pass
        elif current_section == "hosts" and _is_valid_subdomain(line):
            subdomains_set.add(line)
        elif current_section == "ips":
            try:
                validate_ip(line)
                ips_set.add(line)
            except ValidationError:
                pass

    # Return sorted lists for deterministic output
    return sorted(list(emails_set)), sorted(list(subdomains_set)), sorted(list(ips_set))


@handle_tool_errors("research_harvest")
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
        limit: maximum number of results per source to return (default 100, range 1-10000)

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
    # Validate domain
    try:
        domain = validate_domain(domain)
    except ValidationError as exc:
        return {"domain": domain, "error": str(exc), "harvester_available": False}

    # Validate sources
    try:
        sources = _validate_sources(sources)
    except ValidationError as exc:
        return {"domain": domain, "error": str(exc), "harvester_available": False}

    # Validate limit (must be 1-10000)
    if not isinstance(limit, int) or limit < 1 or limit > 10000:
        return {
            "domain": domain,
            "error": "limit must be an integer between 1 and 10000",
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
        # Record start time
        start_time = time.time()

        # Build theHarvester command with validated parameters
        cmd = ["theHarvester", "-d", domain, "-b", sources, "-l", str(limit)]

        # Run theHarvester with 120-second timeout
        result = run_command(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout (reduced from 5 for responsiveness)
        )

        # Parse output
        emails, subdomains, ips = _parse_harvester_output(result["stdout"], result["stderr"])

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
        duration_ms = int((time.time() - start_time) * 1000)
        return {
            "domain": domain,
            "error": f"theHarvester lookup timed out after 120 seconds (duration: {duration_ms}ms)",
            "duration_ms": duration_ms,
            "harvester_available": True,
        }
    except subprocess.CalledProcessError as exc:
        logger.error(f"theHarvester returned error: {exc.stderr}")
        return {
            "domain": domain,
            "error": f"theHarvester process error: {exc.stderr[:200]}",
            "harvester_available": True,
        }
    except OSError as exc:
        logger.error(f"OS error executing theHarvester: {exc}")
        return {
            "domain": domain,
            "error": f"OS error: {str(exc)}",
            "harvester_available": False,
        }
    except Exception as exc:
        logger.exception("Unexpected error in research_harvest")
        return {
            "domain": domain,
            "error": f"Unexpected error: {type(exc).__name__}",
            "harvester_available": False,
        }
