"""Domain intelligence tools — WHOIS, DNS lookup, and port scanning."""

from __future__ import annotations
import asyncio

import ipaddress
import logging
import re
import socket
import subprocess
from typing import Any

logger = logging.getLogger("loom.tools.domain_intel")


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


def _validate_ip_or_domain(target: str) -> str:
    """Validate target is an IP address or domain (no CIDR, no ranges).

    Args:
        target: IP address or domain name

    Returns:
        The validated target string

    Raises:
        ValueError: if target is invalid
    """
    target = target.strip()

    # Fix C3: Reject targets starting with "-" to prevent nmap flag injection
    if target.startswith("-"):
        raise ValueError("target cannot start with '-'")

    # Try to parse as IP address first
    try:
        ipaddress.ip_address(target)
        return target
    except ValueError:
        pass

    # Fall back to domain validation
    return _validate_domain(target)


def _run_whois(domain: str) -> tuple[str, int, str]:
    """Run whois command (blocking I/O).

    Args:
        domain: domain to query

    Returns:
        Tuple of (stdout, returncode, stderr)
    """
    result = subprocess.run(
        ["whois", domain],
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.stdout, result.returncode, result.stderr


def _run_nmap(cmd: list[str]) -> tuple[str, int]:
    """Run nmap command (blocking I/O).

    Args:
        cmd: nmap command as list

    Returns:
        Tuple of (stdout, returncode)
    """
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout, result.returncode


async def research_whois(domain: str) -> dict[str, Any]:
    """Run whois lookup on a domain.

    Uses the system `whois` command to retrieve registration information.
    Parses output to extract common fields.

    Args:
        domain: domain name (e.g., "example.com")

    Returns:
        Dict with:
        - domain: the queried domain
        - registrar: registrar name
        - creation_date: domain creation date
        - expiration_date: domain expiration date
        - updated_date: last update date
        - registrant_name: registrant name (if available)
        - registrant_org: registrant organization (if available)
        - registrant_country: registrant country (if available)
        - nameservers: list of nameserver hostnames
        - status: list of domain status codes
        - raw_text: truncated raw whois output (2000 chars max)
        - error: error message if lookup failed
    """
    try:
        domain = _validate_domain(domain)
    except ValueError as exc:
        return {"domain": domain, "error": str(exc)}

    try:
        # Run blocking subprocess in executor
        raw_text, returncode, stderr = await asyncio.to_thread(_run_whois, domain)

        if returncode != 0:
            return {"domain": domain, "error": f"whois command failed: {stderr}"}

        # Parse common whois fields using regex patterns
        output: dict[str, Any] = {"domain": domain}

        # Registrar
        registrar_match = re.search(
            r"(?:Registrar|registrar)[\s:]+(.+?)(?:\n|$)", raw_text
        )
        if registrar_match:
            output["registrar"] = registrar_match.group(1).strip()

        # Creation date
        creation_match = re.search(
            r"(?:Creation\s+Date|creation\s+date|created)[\s:]+(.+?)(?:\n|$)",
            raw_text,
            re.IGNORECASE,
        )
        if creation_match:
            output["creation_date"] = creation_match.group(1).strip()

        # Expiration date
        expiration_match = re.search(
            r"(?:Expiration\s+Date|Expiration|Registrar\s+Expiration|Registry\s+Expiry)[\s:]+(.+?)(?:\n|$)",
            raw_text,
            re.IGNORECASE,
        )
        if expiration_match:
            output["expiration_date"] = expiration_match.group(1).strip()

        # Updated date
        updated_match = re.search(
            r"(?:Updated\s+Date|updated|last\s+updated)[\s:]+(.+?)(?:\n|$)",
            raw_text,
            re.IGNORECASE,
        )
        if updated_match:
            output["updated_date"] = updated_match.group(1).strip()

        # Registrant name
        registrant_match = re.search(
            r"(?:Registrant\s+Name|registrant\s+name)[\s:]+(.+?)(?:\n|$)",
            raw_text,
            re.IGNORECASE,
        )
        if registrant_match:
            output["registrant_name"] = registrant_match.group(1).strip()

        # Registrant organization
        org_match = re.search(
            r"(?:Registrant\s+Organization|registrant\s+org)[\s:]+(.+?)(?:\n|$)",
            raw_text,
            re.IGNORECASE,
        )
        if org_match:
            output["registrant_org"] = org_match.group(1).strip()

        # Registrant country
        country_match = re.search(
            r"(?:Registrant\s+Country|registrant\s+country)[\s:]+(.+?)(?:\n|$)",
            raw_text,
            re.IGNORECASE,
        )
        if country_match:
            output["registrant_country"] = country_match.group(1).strip()

        # Name servers
        ns_lines = re.findall(
            r"(?:Name Server|nameserver)[\s:]+(.+?)(?:\n|$)",
            raw_text,
            re.IGNORECASE,
        )
        if ns_lines:
            output["nameservers"] = [ns.strip() for ns in ns_lines]

        # Status codes
        status_lines = re.findall(
            r"(?:Status|domain status)[\s:]+(.+?)(?:\n|$)",
            raw_text,
            re.IGNORECASE,
        )
        if status_lines:
            output["status"] = [s.strip() for s in status_lines]

        # Include truncated raw text
        output["raw_text"] = raw_text[:2000]

        logger.info("whois_lookup_success domain=%s", domain)
        return output

    except subprocess.TimeoutExpired:
        logger.warning("whois_lookup_timeout domain=%s", domain)
        return {"domain": domain, "error": "whois command timed out (>15s)"}
    except Exception as exc:
        logger.exception("whois_lookup_failed domain=%s", domain)
        return {"domain": domain, "error": str(exc)}


async def research_dns_lookup(
    domain: str, record_types: list[str] | None = None
) -> dict[str, Any]:
    """DNS lookup for domain records.

    Attempts to use dnspython library if available, falls back to socket.

    Args:
        domain: domain name to look up
        record_types: list of record types (A, AAAA, MX, NS, TXT, etc.)
                     Default: ["A", "AAAA", "MX", "NS", "TXT"]

    Returns:
        Dict with:
        - domain: the queried domain
        - records: dict mapping record type to list of values
        - ip_addresses: flattened list of all A/AAAA records
        - error: error message if lookup failed
    """
    try:
        domain = _validate_domain(domain)
    except ValueError as exc:
        return {"domain": domain, "error": str(exc)}

    if record_types is None:
        record_types = ["A", "AAAA", "MX", "NS", "TXT"]

    # Normalize record types to uppercase
    record_types = [rt.upper() for rt in record_types]

    output: dict[str, Any] = {"domain": domain, "records": {}}

    # Try dnspython first
    try:
        import dns.resolver  # type: ignore

        resolver = dns.resolver.Resolver()
        resolver.timeout = 10
        resolver.lifetime = 10

        for record_type in record_types:
            try:
                answers = resolver.resolve(domain, record_type)
                records = []

                if record_type == "MX":
                    for answer in answers:
                        records.append(
                            {
                                "priority": int(answer.preference),
                                "host": str(answer.exchange),
                            }
                        )
                elif record_type in ("NS", "CNAME", "PTR"):
                    for answer in answers:
                        records.append(str(answer.target).rstrip("."))
                else:
                    for answer in answers:
                        records.append(str(answer))

                if records:
                    output["records"][record_type] = records

            except Exception as exc:
                logger.debug("dns_lookup_record_failed domain=%s type=%s: %s",
                           domain, record_type, exc)
                # Continue with other record types
                continue

        logger.info("dns_lookup_success domain=%s records=%s",
                   domain, list(output["records"].keys()))

    except ImportError:
        # Fallback to socket library (basic A/AAAA only)
        logger.debug("dnspython not available, falling back to socket")

        try:
            infos = socket.getaddrinfo(domain, None)
            a_records = []
            aaaa_records = []

            for family, _, _, _, sockaddr in infos:
                ip = sockaddr[0]
                if family == socket.AF_INET:
                    a_records.append(ip)
                elif family == socket.AF_INET6:
                    aaaa_records.append(ip)

            if a_records:
                output["records"]["A"] = a_records
            if aaaa_records:
                output["records"]["AAAA"] = aaaa_records

        except socket.gaierror as exc:
            logger.warning("dns_lookup_failed domain=%s: %s", domain, exc)
            return {"domain": domain, "records": {}, "error": str(exc)}

    # Flatten A/AAAA records into ip_addresses list
    ip_addresses = []
    for record_type in ("A", "AAAA"):
        if record_type in output["records"]:
            ip_addresses.extend(output["records"][record_type])

    output["ip_addresses"] = ip_addresses

    return output


async def research_nmap_scan(
    target: str, ports: str = "80,443,8080,8443", scan_type: str = "basic"
) -> dict[str, Any]:
    """Port scan using nmap.

    Scans the specified ports on the target using nmap CLI. Only performs
    scans on authorized targets (no CIDR ranges, no port ranges).

    Args:
        target: IP address or domain (no CIDR blocks or ranges)
        ports: comma-separated port list (e.g., "80,443,8080") or port range (e.g., "80-443")
        scan_type: "basic" (-sT -T3) or "service" (-sV -T3)

    Returns:
        Dict with:
        - target: the scanned target
        - ports: list of dicts with port, state, service
        - scan_type: the scan type used
        - host_up: whether the host responded
        - error: error message if scan failed
    """
    try:
        target = _validate_ip_or_domain(target)
    except ValueError as exc:
        return {"target": target, "error": str(exc)}

    if scan_type not in ("basic", "service"):
        return {"target": target, "error": "scan_type must be 'basic' or 'service'"}

    # Validate ports format (comma-separated, allow ranges)
    if not ports or len(ports) > 100:
        return {"target": target, "error": "ports format invalid"}

    if not re.match(r"^[\d,\-]+$", ports):
        return {"target": target, "error": "ports must be comma-separated or ranges"}

    output: dict[str, Any] = {
        "target": target,
        "scan_type": scan_type,
        "ports": [],
    }

    try:
        # Build nmap command
        cmd = ["nmap", "-p", ports]

        if scan_type == "basic":
            cmd.extend(["-sT", "-T3"])  # Connect scan, polite timing
        elif scan_type == "service":
            cmd.extend(["-sV", "-T3"])  # Service version detection

        cmd.append(target)

        # Run blocking subprocess in executor
        nmap_output, returncode = await asyncio.to_thread(_run_nmap, cmd)

        if returncode not in (0, 1):  # nmap returns 1 if no ports found
            logger.warning("nmap_scan_failed target=%s code=%d", target, returncode)
            return {
                **output,
                "error": f"nmap command failed with code {returncode}",
            }

        # Parse output for open ports
        port_pattern = re.compile(
            r"(\d+)/tcp\s+(\w+)\s+(?:(\S+))?"
        )

        for match in port_pattern.finditer(nmap_output):
            port_num = int(match.group(1))
            state = match.group(2).lower()
            service = match.group(3) or "unknown"

            # Only include open ports
            if state == "open":
                output["ports"].append(
                    {"port": port_num, "state": state, "service": service}
                )

        # Check if host is up (look for Nmap output indicating host alive)
        host_up = "Host is up" in nmap_output or len(output["ports"]) > 0
        output["host_up"] = host_up

        logger.info(
            "nmap_scan_success target=%s open_ports=%d",
            target,
            len(output["ports"]),
        )

        return output

    except FileNotFoundError:
        logger.error("nmap_not_found; ensure nmap is installed in PATH")
        return {
            **output,
            "error": "nmap command not found (install nmap)",
        }
    except subprocess.TimeoutExpired:
        logger.warning("nmap_scan_timeout target=%s", target)
        return {**output, "error": "nmap command timed out (>60s)"}
    except Exception as exc:
        logger.exception("nmap_scan_failed target=%s", target)
        return {**output, "error": str(exc)}
