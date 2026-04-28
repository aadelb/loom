"""Passive infrastructure reconnaissance — map hidden infrastructure without active scanning."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.passive_recon")

_CRT_SH = "https://crt.sh/?q=%25.{domain}&output=json"
_HACKERTARGET_REVERSE_IP = "https://api.hackertarget.com/reverseiplookup/?q={ip}"
_SHODAN_INTERNETDB = "https://internetdb.shodan.io/{ip}"


async def _get_json(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0
) -> Any:
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("passive_recon fetch failed: %s", exc)
    return None


async def _get_text(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> str:
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("passive_recon text fetch failed: %s", exc)
    return ""


async def _resolve_dns(
    client: httpx.AsyncClient, domain: str
) -> dict[str, list[str]]:
    records: dict[str, list[str]] = {}
    for rtype in ("A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA"):
        url = f"https://dns.google/resolve?name={quote(domain)}&type={rtype}"
        data = await _get_json(client, url, timeout=10.0)
        if data and "Answer" in data:
            records[rtype] = [a.get("data", "") for a in data["Answer"]]
    return records


async def _ct_subdomains(client: httpx.AsyncClient, domain: str) -> list[str]:
    data = await _get_json(client, _CRT_SH.format(domain=domain), timeout=30.0)
    if not data:
        return []
    subdomains: set[str] = set()
    for entry in data:
        name = entry.get("name_value", "")
        for line in name.split("\n"):
            line = line.strip().lstrip("*.")
            if line.endswith(f".{domain}") or line == domain:
                subdomains.add(line)
    return sorted(subdomains)


async def _reverse_ip(client: httpx.AsyncClient, ip: str) -> list[str]:
    text = await _get_text(client, _HACKERTARGET_REVERSE_IP.format(ip=ip))
    if not text or "error" in text.lower():
        return []
    return [line.strip() for line in text.splitlines() if line.strip()]


async def _shodan_internetdb(client: httpx.AsyncClient, ip: str) -> dict[str, Any]:
    data = await _get_json(client, _SHODAN_INTERNETDB.format(ip=ip))
    return data or {}


def _parse_spf(txt_records: list[str]) -> list[str]:
    includes: list[str] = []
    for record in txt_records:
        if "v=spf1" in record:
            for part in record.split():
                if part.startswith("include:"):
                    includes.append(part.replace("include:", ""))
                elif part.startswith("a:") or part.startswith("mx:"):
                    includes.append(part)
    return includes


def _parse_dmarc(txt_records: list[str]) -> str:
    for record in txt_records:
        if "v=DMARC1" in record:
            return record
    return ""


def _detect_cdn(cname_records: list[str], a_records: list[str]) -> str:
    all_records = " ".join(cname_records + a_records).lower()
    if "cloudflare" in all_records:
        return "Cloudflare"
    if "fastly" in all_records:
        return "Fastly"
    if "akamai" in all_records or "edgekey" in all_records:
        return "Akamai"
    if "cloudfront" in all_records:
        return "CloudFront"
    if "azureedge" in all_records:
        return "Azure CDN"
    return ""


def _detect_email_providers(mx_records: list[str]) -> list[str]:
    providers: list[str] = []
    mx_str = " ".join(mx_records).lower()
    if "google" in mx_str or "gmail" in mx_str:
        providers.append("Google Workspace")
    if "outlook" in mx_str or "microsoft" in mx_str:
        providers.append("Microsoft 365")
    if "protonmail" in mx_str:
        providers.append("ProtonMail")
    if "zoho" in mx_str:
        providers.append("Zoho")
    if "mimecast" in mx_str:
        providers.append("Mimecast")
    return providers


def research_passive_recon(
    domain: str,
    include_shodan: bool = True,
    include_reverse_ip: bool = True,
) -> dict[str, Any]:
    """Map a domain's hidden infrastructure using only passive techniques.

    Combines Certificate Transparency logs (crt.sh), DNS enumeration
    (all record types), reverse IP lookup (HackerTarget), Shodan
    InternetDB (free, no API key), SPF/DMARC parsing, CDN detection,
    and email provider identification.

    Args:
        domain: target domain (e.g. "example.com")
        include_shodan: query Shodan InternetDB for open ports/vulns
        include_reverse_ip: query reverse IP for shared hosting neighbors

    Returns:
        Dict with ``subdomains``, ``dns_records``, ``spf_includes``,
        ``dmarc_policy``, ``cdn``, ``email_providers``, ``shared_hosting``,
        ``shodan`` (ports, vulns, tags), and ``ip_address``.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            subdomains_task = _ct_subdomains(client, domain)
            dns_task = _resolve_dns(client, domain)

            subdomains, dns_records = await asyncio.gather(
                subdomains_task, dns_task
            )

            a_records = dns_records.get("A", [])
            ip_address = a_records[0] if a_records else ""

            txt_records = dns_records.get("TXT", [])
            cname_records = dns_records.get("CNAME", [])
            mx_records = dns_records.get("MX", [])

            shodan_data: dict[str, Any] = {}
            shared_hosting: list[str] = []

            if ip_address:
                tasks = []
                if include_shodan:
                    tasks.append(_shodan_internetdb(client, ip_address))
                if include_reverse_ip:
                    tasks.append(_reverse_ip(client, ip_address))

                results = await asyncio.gather(*tasks, return_exceptions=True)
                idx = 0
                if include_shodan and idx < len(results):
                    if isinstance(results[idx], dict):
                        shodan_data = results[idx]
                    idx += 1
                if include_reverse_ip and idx < len(results):
                    if isinstance(results[idx], list):
                        shared_hosting = results[idx]

            dmarc_text = ""
            dmarc_domain = f"_dmarc.{domain}"
            dmarc_dns = await _resolve_dns(client, dmarc_domain)
            dmarc_txt = dmarc_dns.get("TXT", [])
            dmarc_text = _parse_dmarc(dmarc_txt)

            return {
                "domain": domain,
                "ip_address": ip_address,
                "subdomains_count": len(subdomains),
                "subdomains": subdomains[:200],
                "dns_records": dns_records,
                "spf_includes": _parse_spf(txt_records),
                "dmarc_policy": dmarc_text,
                "cdn_detected": _detect_cdn(cname_records, a_records),
                "email_providers": _detect_email_providers(mx_records),
                "shared_hosting_neighbors": shared_hosting[:50],
                "shodan": {
                    "ports": shodan_data.get("ports", []),
                    "vulns": shodan_data.get("vulns", []),
                    "hostnames": shodan_data.get("hostnames", []),
                    "tags": shodan_data.get("tags", []),
                    "cpes": shodan_data.get("cpes", []),
                },
            }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
