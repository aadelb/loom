"""Dark web reconnaissance tools — TorBot and OWASP Amass integration."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from typing import Any

from loom.validators import validate_url, UrlSafetyError

logger = logging.getLogger("loom.tools.dark_recon")


def _validate_domain(domain: str) -> str:
    """Validate domain name to prevent command injection.

    Allows alphanumeric, dots, hyphens, and underscores.
    Returns the validated domain.

    Args:
        domain: domain name to validate

    Returns:
        The validated domain string

    Raises:
        ValueError: if domain contains disallowed characters
    """
    if not domain or len(domain) > 255:
        raise ValueError("domain must be 1-255 characters")

    # Allow alphanumeric, dots, hyphens, underscores
    if not re.match(r"^[a-z0-9._-]+$", domain, re.IGNORECASE):
        raise ValueError("domain contains disallowed characters")

    return domain


def _is_tool_available(tool_name: str) -> bool:
    """Check if a tool is available in the system PATH.

    Args:
        tool_name: name of the tool to check (e.g., 'torbot', 'amass')

    Returns:
        True if tool is available, False otherwise
    """
    return shutil.which(tool_name) is not None


def research_torbot(url: str, depth: int = 2) -> dict[str, Any]:
    """Dark web OSINT crawling via TorBot subprocess.

    Uses the TorBot tool to crawl a URL through Tor and extract information
    including linked URLs, email addresses, and phone numbers.

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
    if not _is_tool_available("torbot"):
        return {
            "url": url,
            "warning": "TorBot is not installed. Install with: pip install torbot",
            "links_found": [],
            "emails_found": [],
            "phone_numbers": [],
            "depth_crawled": 0,
        }

    try:
        result = subprocess.run(
            ["torbot", "-u", url, "--depth", str(depth), "--json"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes for deep crawls
        )

        output: dict[str, Any] = {"url": url, "depth_crawled": depth}

        if result.returncode != 0:
            output["error"] = f"torbot command failed: {result.stderr}"
            output["links_found"] = []
            output["emails_found"] = []
            output["phone_numbers"] = []
            return output

        # Parse JSON output from torbot
        try:
            json_output = json.loads(result.stdout)
            output["links_found"] = json_output.get("links", [])
            output["emails_found"] = json_output.get("emails", [])
            output["phone_numbers"] = json_output.get("phone_numbers", [])
        except json.JSONDecodeError:
            # Fallback: parse text output with regex
            output["links_found"] = re.findall(r"https?://[^\s]+", result.stdout)
            output["emails_found"] = re.findall(
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                result.stdout,
            )
            output["phone_numbers"] = re.findall(r"\+?\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}", result.stdout)

        return output

    except subprocess.TimeoutExpired:
        return {
            "url": url,
            "error": "torbot crawl timed out (exceeded 300 seconds)",
            "links_found": [],
            "emails_found": [],
            "phone_numbers": [],
            "depth_crawled": 0,
        }
    except Exception as exc:
        logger.error("torbot error", url=url, error=str(exc))
        return {
            "url": url,
            "error": f"torbot error: {type(exc).__name__}: {str(exc)}",
            "links_found": [],
            "emails_found": [],
            "phone_numbers": [],
            "depth_crawled": 0,
        }


def research_amass_enum(domain: str, passive: bool = True, timeout: int = 120) -> dict[str, Any]:
    """Attack surface mapping and asset discovery via OWASP Amass enum.

    Uses the Amass tool to enumerate subdomains, ASNs, and IP addresses
    associated with a domain.

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
        domain = _validate_domain(domain)
    except ValueError as exc:
        return {"domain": domain, "error": str(exc)}

    # Validate timeout
    if not isinstance(timeout, int) or timeout < 1 or timeout > 600:
        return {"domain": domain, "error": "timeout must be an integer between 1 and 600"}

    # Check if Amass is available
    if not _is_tool_available("amass"):
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

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output: dict[str, Any] = {"domain": domain}

        if result.returncode != 0:
            output["error"] = f"amass enum command failed: {result.stderr}"
            output["subdomains"] = []
            output["asns"] = []
            output["ip_addresses"] = []
            output["count"] = 0
            output["sources"] = []
            return output

        # Parse JSON lines output from amass
        subdomains: set[str] = set()
        asns: set[str] = set()
        ip_addresses: set[str] = set()
        sources: set[str] = set()

        for line in result.stdout.strip().split("\n"):
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

    except subprocess.TimeoutExpired:
        return {
            "domain": domain,
            "error": f"amass enum timed out (exceeded {timeout} seconds)",
            "subdomains": [],
            "asns": [],
            "ip_addresses": [],
            "count": 0,
            "sources": [],
        }
    except Exception as exc:
        logger.error("amass enum error", domain=domain, error=str(exc))
        return {
            "domain": domain,
            "error": f"amass enum error: {type(exc).__name__}: {str(exc)}",
            "subdomains": [],
            "asns": [],
            "ip_addresses": [],
            "count": 0,
            "sources": [],
        }


def research_amass_intel(domain: str) -> dict[str, Any]:
    """OSINT intelligence gathering via OWASP Amass intel.

    Uses the Amass intel command to gather passive reconnaissance information
    including organizations, emails, and related domains.

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
        domain = _validate_domain(domain)
    except ValueError as exc:
        return {"domain": domain, "error": str(exc)}

    # Check if Amass is available
    if not _is_tool_available("amass"):
        return {
            "domain": domain,
            "warning": "Amass is not installed. Install from: https://github.com/OWASP/Amass",
            "organizations": [],
            "emails": [],
            "related_domains": [],
        }

    try:
        result = subprocess.run(
            ["amass", "intel", "-d", domain, "-json"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        output: dict[str, Any] = {"domain": domain}

        if result.returncode != 0:
            output["error"] = f"amass intel command failed: {result.stderr}"
            output["organizations"] = []
            output["emails"] = []
            output["related_domains"] = []
            return output

        # Parse JSON lines output from amass intel
        organizations: set[str] = set()
        emails: set[str] = set()
        related_domains: set[str] = set()

        for line in result.stdout.strip().split("\n"):
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

    except subprocess.TimeoutExpired:
        return {
            "domain": domain,
            "error": "amass intel timed out (exceeded 120 seconds)",
            "organizations": [],
            "emails": [],
            "related_domains": [],
        }
    except Exception as exc:
        logger.error("amass intel error", domain=domain, error=str(exc))
        return {
            "domain": domain,
            "error": f"amass intel error: {type(exc).__name__}: {str(exc)}",
            "organizations": [],
            "emails": [],
            "related_domains": [],
        }
