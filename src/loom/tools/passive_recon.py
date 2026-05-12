"""Passive infrastructure reconnaissance — map hidden infrastructure without active scanning."""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.passive_recon")


def _validate_domain(domain: str) -> str:
    """Validate domain name to prevent command injection.

    Allows alphanumeric, dots, and hyphens. Returns the validated domain.

    Args:
        domain: domain name to validate

    Returns:
        The validated domain string

    Raises:
        ValueError: if domain contains disallowed characters
    """
    if not domain or len(domain) > 255:
        raise ValueError("domain must be 1-255 characters")

    # Allow alphanumeric, dots, hyphens
    if not re.match(r"^[a-z0-9.-]+$", domain, re.IGNORECASE):
        raise ValueError("domain contains disallowed characters")

    return domain


def _extract_ct_subdomains(json_data: list[dict[str, Any]]) -> list[str]:
    """Extract subdomains from Certificate Transparency JSON response.

    Args:
        json_data: list of cert entries from crt.sh

    Returns:
        List of unique subdomains
    """
    subdomains: set[str] = set()

    for entry in json_data:
        name_value = entry.get("name_value", "")
        for line in name_value.split("\n"):
            line = line.strip().lstrip("*.")
            if line:
                subdomains.add(line)

    return sorted(subdomains)[:50]  # Max 50


def _extract_dns_records(response_json: dict[str, Any]) -> list[str]:
    """Extract DNS records from Google DNS API response.

    Args:
        response_json: JSON response from dns.google

    Returns:
        List of record values
    """
    records: list[str] = []

    if "Answer" in response_json:
        for answer in response_json["Answer"]:
            data = answer.get("data", "")
            if data:
                records.append(data)

    return records


def _parse_email_security(txt_records: list[str]) -> dict[str, Any]:
    """Parse SPF, DKIM, and DMARC from TXT records.

    Args:
        txt_records: list of TXT record values

    Returns:
        Dict with spf, dkim, dmarc bools and dmarc_policy
    """
    spf_found = False
    dmarc_found = False
    dmarc_policy = ""

    txt_str = " ".join(txt_records).lower()

    # Check SPF
    if "v=spf1" in txt_str:
        spf_found = True

    # Check DMARC (simplified)
    if "v=dmarc1" in txt_str:
        dmarc_found = True
        # Extract DMARC policy value
        for record in txt_records:
            record_lower = record.lower()
            if "v=dmarc1" in record_lower:
                dmarc_policy = record
                break

    # DKIM check (TXT records with "v=DKIM1" or mail._domainkey entries)
    dkim_found = "v=dkim1" in txt_str

    return {
        "spf": spf_found,
        "dkim": dkim_found,
        "dmarc": dmarc_found,
        "dmarc_policy": dmarc_policy,
    }


def _detect_tech_stack(
    domain: str, headers: dict[str, Any], html_content: str
) -> dict[str, Any]:
    """Fingerprint tech stack from HTTP headers and HTML.

    Args:
        domain: target domain
        headers: HTTP response headers
        html_content: HTML response body

    Returns:
        Dict with server, powered_by, frameworks, cdn
    """
    tech: dict[str, Any] = {
        "server": "",
        "powered_by": "",
        "frameworks": [],
        "cdn": "",
    }

    # Extract Server header
    if "server" in headers:
        tech["server"] = headers["server"]

    # Extract X-Powered-By
    if "x-powered-by" in headers:
        tech["powered_by"] = headers["x-powered-by"]

    # Extract X-Generator (common in static site generators)
    if "x-generator" in headers:
        tech["powered_by"] = headers["x-generator"]

    # Framework detection from HTML meta tags
    frameworks: set[str] = set()

    # WordPress
    if "wp-content" in html_content or "wp-includes" in html_content:
        frameworks.add("WordPress")

    # Drupal
    if "drupal" in html_content.lower():
        frameworks.add("Drupal")

    # React
    if "react" in html_content.lower() or "_react" in html_content:
        frameworks.add("React")

    # Vue
    if "vue" in html_content.lower():
        frameworks.add("Vue.js")

    # Angular
    if "angular" in html_content.lower() or "ng-app" in html_content:
        frameworks.add("Angular")

    # Next.js
    if "__next" in html_content:
        frameworks.add("Next.js")

    tech["frameworks"] = sorted(frameworks)

    # CDN detection from headers and DNS CNAME
    if "cdn" in headers.get("server", "").lower():
        tech["cdn"] = headers["server"]
    elif "cloudflare" in headers.get("server", "").lower():
        tech["cdn"] = "Cloudflare"

    return tech


async def research_passive_recon(
    domain: str,
    check_ct_logs: bool = True,
    check_dns: bool = True,
    check_reverse_ip: bool = True,
    check_tech_stack: bool = True,
) -> dict[str, Any]:
    """Map domain's hidden infrastructure using only passive techniques.

    Queries Certificate Transparency logs, DNS records, reverse IP lookup,
    and tech stack fingerprinting without active scanning.

    Args:
        domain: target domain (e.g., "example.com")
        check_ct_logs: query Certificate Transparency for subdomains
        check_dns: query DNS records (A, AAAA, MX, NS, TXT, SOA)
        check_reverse_ip: query reverse IP for shared hosting neighbors
        check_tech_stack: fetch homepage and fingerprint tech stack

    Returns:
        Dict with subdomains, dns_records, reverse_ip_domains, tech_stack,
        email_security, and total_findings
    """
    try:
        domain = _validate_domain(domain)
    except ValueError as exc:
        return {"domain": domain, "error": str(exc)}

    output: dict[str, Any] = {
        "domain": domain,
        "subdomains": [],
        "dns_records": {},
        "reverse_ip_domains": [],
        "tech_stack": {
            "server": "",
            "powered_by": "",
            "frameworks": [],
            "cdn": "",
        },
        "email_security": {
            "spf": False,
            "dkim": False,
            "dmarc": False,
            "dmarc_policy": "",
        },
        "total_findings": 0,
    }

    finding_count = 0

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # CT Logs
            if check_ct_logs:
                try:
                    ct_url = f"https://crt.sh/?q=%25.{quote(domain)}&output=json"
                    resp = await client.get(ct_url, timeout=15.0)
                    if resp.status_code == 200:
                        ct_data = resp.json()
                        if isinstance(ct_data, list):
                            subdomains = _extract_ct_subdomains(ct_data)
                            output["subdomains"] = subdomains
                            finding_count += len(subdomains)
                except Exception as exc:
                    logger.debug("ct_logs_failed domain=%s: %s", domain, exc)

            # DNS Records
            if check_dns:
                dns_records: dict[str, list[str]] = {}
                for rtype in ("A", "AAAA", "MX", "NS", "TXT", "SOA"):
                    try:
                        dns_url = (
                            f"https://dns.google/resolve?"
                            f"name={quote(domain)}&type={rtype}"
                        )
                        resp = await client.get(dns_url, timeout=10.0)
                        if resp.status_code == 200:
                            dns_json = resp.json()
                            records = _extract_dns_records(dns_json)
                            if records:
                                dns_records[rtype] = records
                                finding_count += len(records)
                    except Exception as exc:
                        logger.debug(
                            "dns_lookup_failed domain=%s type=%s: %s",
                            domain, rtype, exc
                        )

                output["dns_records"] = dns_records

                # Parse email security
                txt_records = dns_records.get("TXT", [])
                if txt_records:
                    email_sec = _parse_email_security(txt_records)
                    output["email_security"] = email_sec

            # Reverse IP Lookup
            if check_reverse_ip:
                # Get first A record to use for reverse IP
                a_records = output["dns_records"].get("A", [])
                if a_records:
                    ip = a_records[0]
                    try:
                        rev_url = (
                            f"https://api.hackertarget.com/reverseiplookup/?q={ip}"
                        )
                        resp = await client.get(rev_url, timeout=10.0)
                        if resp.status_code == 200:
                            text = resp.text
                            if text and "error" not in text.lower():
                                reverse_domains = [
                                    line.strip()
                                    for line in text.splitlines()
                                    if line.strip()
                                ]
                                output["reverse_ip_domains"] = reverse_domains[:50]
                                finding_count += len(reverse_domains)
                    except Exception as exc:
                        logger.debug(
                            "reverse_ip_failed domain=%s ip=%s: %s",
                            domain, ip, exc
                        )

            # Tech Stack Fingerprinting
            if check_tech_stack:
                try:
                    # Try HTTP first, then HTTPS
                    for scheme in ("https", "http"):
                        try:
                            homepage_url = f"{scheme}://{domain}"
                            resp = await client.get(
                                homepage_url, timeout=10.0, follow_redirects=True
                            )
                            if resp.status_code == 200:
                                headers_dict = dict(resp.headers)
                                # Normalize header keys to lowercase
                                headers_lower = {
                                    k.lower(): v
                                    for k, v in headers_dict.items()
                                }
                                html = resp.text[:10000]  # First 10KB
                                tech = _detect_tech_stack(
                                    domain, headers_lower, html
                                )
                                output["tech_stack"] = tech
                                finding_count += sum(
                                    1 for v in tech.values()
                                    if v and (
                                        isinstance(v, str) or
                                        (isinstance(v, list) and v)
                                    )
                                )
                                break
                        except (httpx.ConnectError, httpx.TimeoutException):
                            continue
                except Exception as exc:
                    logger.debug(
                        "tech_stack_detection_failed domain=%s: %s",
                        domain, exc
                    )

        output["total_findings"] = finding_count
        logger.info(
            "passive_recon_success domain=%s findings=%d",
            domain, finding_count
        )
        return output

    except Exception as exc:
        logger.exception("passive_recon_failed domain=%s", domain)
        return {
            **output,
            "error": str(exc),
        }
