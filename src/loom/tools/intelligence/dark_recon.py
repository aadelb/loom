"""Dark web reconnaissance tools — TorBot and OWASP Amass integration."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

try:
    from loom.billing import requires_tier
except ImportError:
    def requires_tier(tier: str):  # type: ignore[misc]
        def decorator(func):  # type: ignore[no-untyped-def]
            return func
        return decorator

from loom.cli_checker import is_available
from loom.input_validators import validate_domain, ValidationError
from loom.validators import validate_url, UrlSafetyError
from loom.error_responses import handle_tool_errors
from loom.subprocess_helpers import run_command

logger = logging.getLogger("loom.tools.dark_recon")

# Maximum stdout read size: 10 MB
MAX_OUTPUT_SIZE = 10 * 1024 * 1024


@requires_tier("pro")
@handle_tool_errors("research_torbot")
def research_torbot(url: str, depth: int = 2) -> dict[str, Any]:
    """Dark web OSINT crawling via TorBot subprocess.

    Uses the TorBot tool to crawl a URL through Tor and extract information
    including linked URLs, email addresses, and phone numbers.

    Requires: Pro tier or higher

    Args:
        url: URL to crawl (must be valid HTTP/HTTPS or onion address)
        depth: crawl depth (1-5, default 2)

    Returns:
        Dict with:
        - url: the queried URL
        - links_found: list of discovered URLs
        - emails_found: list of discovered email addresses
        - phone_numbers: list of discovered phone numbers
        - depth_crawled: actual depth that was crawled
        - error: error message if crawl failed
        - warning: warning message if TorBot or Tor is not available
    """
    try:
        url = validate_url(url)
    except (ValueError, UrlSafetyError) as exc:
        return {"url": url, "error": str(exc)}

    # Validate depth
    if not isinstance(depth, int) or depth < 1 or depth > 5:
        return {"url": url, "error": "depth must be an integer between 1 and 5"}

    # Check if TorBot is available
    if not is_available("torbot"):
        return {
            "url": url,
            "warning": "TorBot is not installed. Install with: pip install torbot",
            "links_found": [],
            "emails_found": [],
            "phone_numbers": [],
            "depth_crawled": 0,
        }

    try:
        result = run_command(
            ["torbot", "-u", url, "--depth", str(depth), "--json"],
            timeout=300,  # 5 minutes for deep crawls
        )

        # Check for timeout error
        if not result["success"]:
            if result.get("error") and "Command timed out" in result["error"]:
                return {
                    "url": url,
                    "error": "torbot crawl timed out (exceeded 300 seconds)",
                    "links_found": [],
                    "emails_found": [],
                    "phone_numbers": [],
                    "depth_crawled": 0,
                }
            else:
                return {
                    "url": url,
                    "error": f"torbot command failed: {result['stderr'][:500] if result['stderr'] else result.get('error', 'Unknown error')}",
                    "links_found": [],
                    "emails_found": [],
                    "phone_numbers": [],
                    "depth_crawled": 0,
                }

        # Limit stdout read to prevent OOM from huge output
        stdout = result["stdout"][:MAX_OUTPUT_SIZE] if result["stdout"] else ""
        if result["stdout"] and len(result["stdout"]) > MAX_OUTPUT_SIZE:
            logger.warning("torbot output truncated (exceeded %d bytes)", MAX_OUTPUT_SIZE)

        output: dict[str, Any] = {"url": url, "depth_crawled": depth}

        # Parse JSON output from torbot
        try:
            json_output = json.loads(stdout)
            output["links_found"] = json_output.get("links", [])
            output["emails_found"] = json_output.get("emails", [])
            output["phone_numbers"] = json_output.get("phone_numbers", [])
        except json.JSONDecodeError:
            # Fallback: parse text output with regex
            output["links_found"] = re.findall(r"https?://[^\s]+", stdout)
            output["emails_found"] = re.findall(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                stdout,
            )
            output["phone_numbers"] = re.findall(r"\+?\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}", stdout)

        return output

    except Exception as exc:
        logger.error("torbot error url=%s error=%s", url, exc)
        return {
            "url": url,
            "error": f"torbot error: {type(exc).__name__}: {str(exc)}",
            "links_found": [],
            "emails_found": [],
            "phone_numbers": [],
            "depth_crawled": 0,
        }


@requires_tier("pro")
@handle_tool_errors("research_amass_enum")
def research_amass_enum(domain: str, passive: bool = True, timeout: int = 120) -> dict[str, Any]:
    """Attack surface mapping and asset discovery via OWASP Amass enum.

    Uses the Amass tool to enumerate subdomains, ASNs, and IP addresses
    associated with a domain.

    Requires: Pro tier or higher

    Args:
        domain: domain name to enumerate
        passive: if True, use passive enumeration only (default True)
        timeout: timeout in seconds for the enumeration (1-600, default 120)

    Returns:
        Dict with:
        - domain: the queried domain
        - subdomains: list of discovered subdomains
        - asns: list of discovered ASNs
        - ip_addresses: list of discovered IP addresses
        - count: total number of assets discovered
        - sources: list of sources used for discovery
        - error: error message if enumeration failed
        - warning: warning message if Amass is not installed
    """
    try:
        domain = validate_domain(domain)
    except ValidationError as exc:
        return {"domain": domain, "error": str(exc)}

    # Validate timeout
    if not isinstance(timeout, int) or timeout < 1 or timeout > 600:
        return {"domain": domain, "error": "timeout must be an integer between 1 and 600"}

    # Check if Amass is available
    if not is_available("amass"):
        return {
            "domain": domain,
            "warning": "Amass is not installed. Install from: https://github.com/OWASP/Amass",
            "subdomains": [],
            "asns": [],
            "ip_addresses": [],
            "count": 0,
            "sources": [],
        }

    try:
        cmd = ["amass", "enum", "-d", domain, "-json"]
        if passive:
            cmd.append("-passive")

        result = run_command(
            cmd,
            timeout=timeout,
        )

        # Check for timeout or other errors
        if not result["success"]:
            if result.get("error") and "Command timed out" in result["error"]:
                return {
                    "domain": domain,
                    "error": f"amass enum timed out (exceeded {timeout} seconds)",
                    "subdomains": [],
                    "asns": [],
                    "ip_addresses": [],
                    "count": 0,
                    "sources": [],
                }
            else:
                return {
                    "domain": domain,
                    "error": f"amass enum command failed: {result['stderr'][:500] if result['stderr'] else result.get('error', 'Unknown error')}",
                    "subdomains": [],
                    "asns": [],
                    "ip_addresses": [],
                    "count": 0,
                    "sources": [],
                }

        # Limit stdout read to prevent OOM
        stdout = result["stdout"][:MAX_OUTPUT_SIZE] if result["stdout"] else ""
        if result["stdout"] and len(result["stdout"]) > MAX_OUTPUT_SIZE:
            logger.warning("amass output truncated (exceeded %d bytes)", MAX_OUTPUT_SIZE)

        output: dict[str, Any] = {"domain": domain}

        # Parse JSON lines output from amass
        subdomains: set[str] = set()
        asns: set[str] = set()
        ip_addresses: set[str] = set()
        sources: set[str] = set()

        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                # Extract subdomain
                if "name" in entry:
                    subdomains.add(entry["name"])
                # Extract IP addresses
                if "addresses" in entry:
                    for addr in entry["addresses"]:
                        if "ip" in addr:
                            ip_addresses.add(addr["ip"])
                # Extract ASN
                if "asn" in entry and "asnum" in entry["asn"]:
                    asns.add(str(entry["asn"]["asnum"]))
                # Extract sources
                if "sources" in entry:
                    for source in entry["sources"]:
                        sources.add(source)
            except json.JSONDecodeError:
                # Skip malformed lines
                continue

        output["subdomains"] = sorted(list(subdomains))
        output["asns"] = sorted(list(asns))
        output["ip_addresses"] = sorted(list(ip_addresses))
        output["sources"] = sorted(list(sources))
        output["count"] = len(subdomains) + len(asns) + len(ip_addresses)

        return output

    except Exception as exc:
        logger.error("amass enum error domain=%s error=%s", domain, exc)
        return {
            "domain": domain,
            "error": f"amass enum error: {type(exc).__name__}: {str(exc)}",
            "subdomains": [],
            "asns": [],
            "ip_addresses": [],
            "count": 0,
            "sources": [],
        }


@requires_tier("pro")
@handle_tool_errors("research_amass_intel")
def research_amass_intel(domain: str) -> dict[str, Any]:
    """OSINT intelligence gathering via OWASP Amass intel.

    Uses the Amass intel command to gather passive reconnaissance information
    including organizations, emails, and related domains.

    Requires: Pro tier or higher

    Args:
        domain: domain name to investigate

    Returns:
        Dict with:
        - domain: the queried domain
        - organizations: list of discovered organizations
        - emails: list of discovered email addresses
        - related_domains: list of related domain names
        - error: error message if intel gathering failed
        - warning: warning message if Amass is not installed
    """
    try:
        domain = validate_domain(domain)
    except ValidationError as exc:
        return {"domain": domain, "error": str(exc)}

    # Check if Amass is available
    if not is_available("amass"):
        return {
            "domain": domain,
            "warning": "Amass is not installed. Install from: https://github.com/OWASP/Amass",
            "organizations": [],
            "emails": [],
            "related_domains": [],
        }

    try:
        result = run_command(
            ["amass", "intel", "-d", domain, "-json"],
            timeout=120,
        )

        # Check for timeout or other errors
        if not result["success"]:
            if result.get("error") and "Command timed out" in result["error"]:
                return {
                    "domain": domain,
                    "error": "amass intel timed out (exceeded 120 seconds)",
                    "organizations": [],
                    "emails": [],
                    "related_domains": [],
                }
            else:
                return {
                    "domain": domain,
                    "error": f"amass intel command failed: {result['stderr'][:500] if result['stderr'] else result.get('error', 'Unknown error')}",
                    "organizations": [],
                    "emails": [],
                    "related_domains": [],
                }

        # Limit stdout read to prevent OOM
        stdout = result["stdout"][:MAX_OUTPUT_SIZE] if result["stdout"] else ""
        if result["stdout"] and len(result["stdout"]) > MAX_OUTPUT_SIZE:
            logger.warning("amass intel output truncated (exceeded %d bytes)", MAX_OUTPUT_SIZE)

        output: dict[str, Any] = {"domain": domain}

        # Parse JSON lines output from amass intel
        organizations: set[str] = set()
        emails: set[str] = set()
        related_domains: set[str] = set()

        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                # Extract organization
                if "org" in entry:
                    organizations.add(entry["org"])
                # Extract email
                if "email" in entry:
                    emails.add(entry["email"])
                # Extract related domain
                if "domain" in entry:
                    related_domains.add(entry["domain"])
                # Also check name field as alternative domain
                if "name" in entry:
                    related_domains.add(entry["name"])
            except json.JSONDecodeError:
                # Skip malformed lines
                continue

        output["organizations"] = sorted(list(organizations))
        output["emails"] = sorted(list(emails))
        output["related_domains"] = sorted(list(related_domains))

        return output

    except Exception as exc:
        logger.error("amass intel error domain=%s error=%s", domain, exc)
        return {
            "domain": domain,
            "error": f"amass intel error: {type(exc).__name__}: {str(exc)}",
            "organizations": [],
            "emails": [],
            "related_domains": [],
        }
