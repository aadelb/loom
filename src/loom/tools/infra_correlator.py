"""Infrastructure fingerprint correlator — link hidden services via shared signals."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

from loom.http_helpers import fetch_json, fetch_text

logger = logging.getLogger("loom.tools.infra_correlator")

_CRT_SH = "https://crt.sh/?q={query}&output=json"
_SHODAN_INTERNETDB = "https://internetdb.shodan.io/{ip}"




async def _get_bytes(client: httpx.AsyncClient, url: str) -> bytes:
    try:
        resp = await client.get(url, timeout=15.0, follow_redirects=True)
        if resp.status_code == 200:
            return resp.content[:100_000]
    except Exception as exc:
        logger.debug("infra_correlator bytes fetch failed: %s", exc)
    return b""


async def _get_headers(client: httpx.AsyncClient, url: str) -> dict[str, str]:
    try:
        resp = await client.head(url, timeout=15.0, follow_redirects=True)
        return dict(resp.headers)
    except Exception as exc:
        logger.debug("infra_correlator headers fetch failed: %s", exc)
    return {}


def _mmh3_hash(data: bytes) -> int:
    try:
        import mmh3

        return mmh3.hash(data)
    except ImportError:
        return int(hashlib.md5(data).hexdigest()[:8], 16)


async def _get_favicon_hash(client: httpx.AsyncClient, domain: str) -> int:
    favicon_data = await _get_bytes(client, f"https://{domain}/favicon.ico")
    if not favicon_data:
        html_text = b""
        try:
            resp = await client.get(
                f"https://{domain}", timeout=15.0, follow_redirects=True
            )
            if resp.status_code == 200:
                html_text = resp.content[:50000]
        except Exception:
            pass
        icon_match = re.search(
            rb'<link[^>]+rel\s*=\s*["\'](?:shortcut )?icon["\'][^>]+href\s*=\s*["\']([^"\']+)["\']',
            html_text,
            re.IGNORECASE,
        )
        if icon_match:
            icon_url = icon_match.group(1).decode("utf-8", errors="replace")
            if not icon_url.startswith("http"):
                icon_url = f"https://{domain}/{icon_url.lstrip('/')}"
            favicon_data = await _get_bytes(client, icon_url)
    if favicon_data:
        return _mmh3_hash(favicon_data)
    return 0


async def _extract_analytics_ids(client: httpx.AsyncClient, domain: str) -> list[dict[str, str]]:
    ids: list[dict[str, str]] = []
    try:
        resp = await client.get(
            f"https://{domain}", timeout=20.0, follow_redirects=True
        )
        if resp.status_code != 200:
            return ids
        text = resp.text
    except Exception:
        return ids

    ga_patterns = [
        (r"UA-\d{6,9}-\d{1,3}", "google_analytics_ua"),
        (r"G-[A-Z0-9]{10,12}", "google_analytics_4"),
        (r"GTM-[A-Z0-9]{6,8}", "google_tag_manager"),
        (r"AW-\d{9,12}", "google_ads"),
        (r"pub-\d{10,20}", "google_adsense"),
    ]
    for pattern, id_type in ga_patterns:
        for match in re.finditer(pattern, text):
            ids.append({"type": id_type, "id": match.group(0)})

    fb_match = re.search(r'fbq\s*\(\s*["\']init["\']\s*,\s*["\'](\d{10,20})["\']', text)
    if fb_match:
        ids.append({"type": "facebook_pixel", "id": fb_match.group(1)})

    return ids


async def _get_cert_sans(client: httpx.AsyncClient, domain: str) -> list[str]:
    data = await fetch_json(client, _CRT_SH.format(query=quote(f"%.{domain}")))
    if not data:
        return []
    sans: set[str] = set()
    for entry in data[:50]:
        name = entry.get("name_value", "")
        for line in name.split("\n"):
            line = line.strip().lstrip("*.")
            if line and line != domain:
                sans.add(line)
    return sorted(sans)


async def _get_http_fingerprint(client: httpx.AsyncClient, domain: str) -> dict[str, str]:
    headers = await _get_headers(client, f"https://{domain}")
    return {
        "server": headers.get("server", ""),
        "x-powered-by": headers.get("x-powered-by", ""),
        "x-generator": headers.get("x-generator", ""),
        "via": headers.get("via", ""),
        "x-cdn": headers.get("x-cdn", ""),
    }


_DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)*\.[a-z]{2,}$")


async def research_infra_correlator(
    domain: str,
    check_favicon: bool = True,
    check_analytics: bool = True,
    check_certs: bool = True,
    check_http: bool = True,
) -> dict[str, Any]:
    """Correlate infrastructure fingerprints to link related or hidden services.

    Combines favicon hash (MMH3), analytics/tracking IDs (GA, GTM, FB Pixel),
    Certificate Transparency SAN entries, and HTTP header fingerprints
    to identify domains operated by the same entity.

    Args:
        domain: target domain to fingerprint
        check_favicon: compute and compare favicon MMH3 hash
        check_analytics: extract Google Analytics, GTM, FB Pixel IDs
        check_certs: query CT logs for shared certificate SANs
        check_http: collect HTTP header fingerprints

    Returns:
        Dict with ``domain``, ``favicon_hash``, ``analytics_ids``,
        ``cert_sans``, ``http_fingerprint``, and ``correlation_signals``.
    """
    try:
        domain = domain.strip().lower()
        if not domain or not _DOMAIN_RE.match(domain) or len(domain) > 253:
            return {"error": "Invalid domain format", "domain": domain}

        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=30.0,
            ) as client:
                tasks: dict[str, Any] = {}
                if check_favicon:
                    tasks["favicon"] = _get_favicon_hash(client, domain)
                if check_analytics:
                    tasks["analytics"] = _extract_analytics_ids(client, domain)
                if check_certs:
                    tasks["certs"] = _get_cert_sans(client, domain)
                if check_http:
                    tasks["http"] = _get_http_fingerprint(client, domain)

                results = {}
                if tasks:
                    gathered = await asyncio.gather(
                        *tasks.values(), return_exceptions=True
                    )
                    for key, val in zip(tasks.keys(), gathered, strict=False):
                        if not isinstance(val, Exception):
                            results[key] = val

                favicon_hash = results.get("favicon", 0)
                analytics_ids = results.get("analytics", [])
                cert_sans = results.get("certs", [])
                http_fp = results.get("http", {})

                correlation_signals: list[dict[str, str]] = []
                if favicon_hash:
                    correlation_signals.append(
                        {
                            "type": "favicon_hash",
                            "value": str(favicon_hash),
                            "description": f"Search Shodan for http.favicon.hash:{favicon_hash}",
                        }
                    )
                for aid in analytics_ids:
                    correlation_signals.append(
                        {
                            "type": f"analytics_{aid['type']}",
                            "value": aid["id"],
                            "description": f"Search PublicWWW for {aid['id']} to find related domains",
                        }
                    )

                return {
                    "domain": domain,
                    "favicon_hash": favicon_hash,
                    "analytics_ids": analytics_ids,
                    "cert_sans": cert_sans[:100],
                    "cert_sans_count": len(cert_sans),
                    "http_fingerprint": http_fp,
                    "correlation_signals": correlation_signals,
                    "total_signals": len(correlation_signals),
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_infra_correlator"}
