"""Threat intelligence tools — monitor dark markets, ransomware, phishing, botnets, malware, domains, and IOCs."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Literal
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.threat_intel")

# API endpoints for threat intelligence services
_OTX_BASE = "https://otx.alienvault.com/api/v1"
_URLHAUS_BASE = "https://urlhaus-api.abuse.ch/v1"
_FEODO_TRACKER = "https://feodotracker.abuse.ch/downloads/ipblocklist_aggressive.json"
_MALWARE_BAZAAR_BASE = "https://mb-api.abuse.ch/api/v1"
_CIRCL_HASHLOOKUP = "https://hashlookup.circl.lu/lookup"
_CRT_SH = "https://crt.sh/?q=%25.{domain}&output=json"
_SHODAN_INTERNETDB = "https://internetdb.shodan.io/{ip}"
_ABUSEIPDB_BASE = "https://api.abuseipdb.com/api/v2"


async def _get_json(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0, headers: dict[str, str] | None = None
) -> Any:
    """Fetch JSON from URL with error handling."""
    try:
        resp = await client.get(url, timeout=timeout, headers=headers or {})
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("threat_intel json fetch failed: %s", exc)
    return None


async def _get_text(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> str:
    """Fetch text from URL with error handling."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("threat_intel text fetch failed: %s", exc)
    return ""


async def _search_otx(
    client: httpx.AsyncClient, keyword: str
) -> list[dict[str, Any]]:
    """Search AlienVault OTX for pulses by keyword."""
    try:
        url = f"{_OTX_BASE}/search/pulses?q={quote(keyword)}"
        data = await _get_json(client, url, timeout=15.0)
        if data and "results" in data:
            return data.get("results", [])
    except Exception as exc:
        logger.debug("otx search failed: %s", exc)
    return []


async def _search_ahmia(
    client: httpx.AsyncClient, keyword: str
) -> list[dict[str, Any]]:
    """Search Ahmia darknet search engine."""
    try:
        url = f"https://ahmia.fi/search/?q={quote(keyword)}&format=json"
        data = await _get_json(client, url, timeout=15.0)
        if data and "results" in data:
            return data.get("results", [])
    except Exception as exc:
        logger.debug("ahmia search failed: %s", exc)
    return []


async def _crt_sh_lookalikes(
    client: httpx.AsyncClient, domain: str
) -> list[str]:
    """Find lookalike domains via Certificate Transparency logs."""
    try:
        url = _CRT_SH.format(domain=domain)
        data = await _get_json(client, url, timeout=30.0)
        if not data:
            return []

        lookalikes: set[str] = set()
        for entry in data:
            name = entry.get("name_value", "")
            for line in name.split("\n"):
                line = line.strip().lstrip("*.")
                # Check for typosquatting variants
                if line != domain and (
                    domain.replace(".", "") in line.replace(".", "") or
                    line.replace(".", "") in domain.replace(".", "")
                ):
                    lookalikes.add(line)
        return sorted(lookalikes)[:100]
    except Exception as exc:
        logger.debug("crt_sh lookalike search failed: %s", exc)
    return []


async def _urlhaus_host_check(
    client: httpx.AsyncClient, domain: str
) -> list[dict[str, Any]]:
    """Check URLhaus for URLs hosted on domain."""
    try:
        url = f"{_URLHAUS_BASE}/host/"
        resp = await client.post(
            url,
            data={"host": domain},
            timeout=15.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("query_status") == "ok":
                return data.get("results", [])
    except Exception as exc:
        logger.debug("urlhaus host check failed: %s", exc)
    return []


async def _shodan_internetdb_lookup(
    client: httpx.AsyncClient, ip: str
) -> dict[str, Any]:
    """Query Shodan InternetDB for IP information."""
    try:
        url = _SHODAN_INTERNETDB.format(ip=ip)
        data = await _get_json(client, url, timeout=10.0)
        return data or {}
    except Exception as exc:
        logger.debug("shodan internetdb lookup failed: %s", exc)
    return {}


async def _feodo_tracker_check(
    client: httpx.AsyncClient, ip: str
) -> dict[str, Any]:
    """Check Feodo Tracker for C2 infrastructure."""
    try:
        text = await _get_text(client, _FEODO_TRACKER, timeout=20.0)
        if not text:
            return {}

        for line in text.splitlines():
            if line.startswith("#"):
                continue
            if line.strip() == ip:
                return {
                    "ip": ip,
                    "listed": True,
                    "tracker": "feodo",
                }
        return {"ip": ip, "listed": False, "tracker": "feodo"}
    except Exception as exc:
        logger.debug("feodo tracker check failed: %s", exc)
    return {}


async def _malware_bazaar_lookup(
    client: httpx.AsyncClient, hash_value: str
) -> dict[str, Any]:
    """Query MalwareBazaar for malware hash information."""
    try:
        url = f"{_MALWARE_BAZAAR_BASE}/"
        resp = await client.post(
            url,
            data={"query": "get_info", "sha256_hash": hash_value},
            timeout=15.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("query_status") == "ok":
                return data
    except Exception as exc:
        logger.debug("malware bazaar lookup failed: %s", exc)
    return {}


async def _circl_hashlookup(
    client: httpx.AsyncClient, hash_value: str
) -> dict[str, Any]:
    """Query CIRCL hashlookup service."""
    try:
        url = f"{_CIRCL_HASHLOOKUP}/sha256/{hash_value}"
        data = await _get_json(client, url, timeout=10.0)
        return data or {}
    except Exception as exc:
        logger.debug("circl hashlookup failed: %s", exc)
    return {}


async def _extract_urls_from_text(text: str) -> list[str]:
    """Extract URLs from text content."""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]*'
    return re.findall(url_pattern, text)


def research_dark_market_monitor(keywords: list[str]) -> dict[str, Any]:
    """Monitor dark market activity from public sources.

    Searches multiple threat intelligence sources for dark market mentions:
    - AlienVault OTX threat pulses
    - Ahmia darknet search engine
    - URLhaus malware database

    Args:
        keywords: list of keywords to search (e.g., ["exploit", "ransomware"])

    Returns:
        Dict with keys: keywords, mentions, sources_checked, alerts
    """
    if not keywords or len(keywords) == 0:
        return {
            "keywords": keywords,
            "mentions": [],
            "sources_checked": [],
            "alerts": [],
            "error": "keywords list cannot be empty",
        }

    async def _run() -> dict[str, Any]:
        mentions: list[dict[str, Any]] = []
        sources_checked: list[str] = []
        alerts: list[dict[str, Any]] = []

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            for keyword in keywords[:10]:  # Limit to 10 keywords
                keyword = keyword.strip()
                if not keyword:
                    continue

                # Search OTX
                otx_results = await _search_otx(client, keyword)
                if otx_results:
                    sources_checked.append("OTX")
                    for result in otx_results[:5]:
                        mention = {
                            "source": "OTX",
                            "keyword": keyword,
                            "type": result.get("type", ""),
                            "title": result.get("title", ""),
                            "created": result.get("created", ""),
                        }
                        mentions.append(mention)
                        alerts.append({
                            "level": "medium",
                            "message": f"Dark market activity: {result.get('title', keyword)} on OTX",
                        })

                # Search Ahmia
                ahmia_results = await _search_ahmia(client, keyword)
                if ahmia_results:
                    sources_checked.append("Ahmia")
                    for result in ahmia_results[:3]:
                        mention = {
                            "source": "Ahmia",
                            "keyword": keyword,
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                        }
                        mentions.append(mention)

        return {
            "keywords": keywords,
            "mentions_count": len(mentions),
            "mentions": mentions[:50],
            "sources_checked": list(set(sources_checked)),
            "alerts_count": len(alerts),
            "alerts": alerts[:20],
        }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


def research_ransomware_tracker(
    group_name: str = "", keyword: str = ""
) -> dict[str, Any]:
    """Track ransomware group activity via threat intelligence sources.

    Searches OTX, Ahmia, and other sources for ransomware group activity,
    victim mentions, and indicators of compromise.

    Args:
        group_name: ransomware group name (e.g., "LockBit", "Cl0p")
        keyword: alternative search keyword if group_name not provided

    Returns:
        Dict with keys: group_name, recent_activity, victims_mentioned, iocs_found
    """
    search_term = group_name or keyword or ""
    if not search_term:
        return {
            "group_name": group_name,
            "keyword": keyword,
            "recent_activity": [],
            "victims_mentioned": [],
            "iocs_found": [],
            "error": "group_name or keyword required",
        }

    async def _run() -> dict[str, Any]:
        activity: list[dict[str, Any]] = []
        victims: set[str] = set()
        iocs: set[str] = set()

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            # Search OTX for ransomware activity
            otx_results = await _search_otx(client, search_term)
            for result in otx_results[:10]:
                activity.append({
                    "source": "OTX",
                    "type": result.get("type", ""),
                    "title": result.get("title", ""),
                    "created": result.get("created", ""),
                })

                # Extract indicators from pulse data
                pulse_detail = result.get("pulse_detail", {})
                if isinstance(pulse_detail, dict):
                    indicators = pulse_detail.get("indicators", [])
                    for indicator in indicators[:5]:
                        ind_type = indicator.get("type", "")
                        if ind_type in ("IPv4", "domain", "URL", "file"):
                            iocs.add(indicator.get("indicator", ""))

            # Search Ahmia
            ahmia_results = await _search_ahmia(client, search_term)
            for result in ahmia_results[:5]:
                activity.append({
                    "source": "Ahmia",
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                })

        return {
            "group_name": group_name,
            "keyword": keyword,
            "recent_activity": activity[:30],
            "victims_mentioned": list(victims)[:20],
            "iocs_found": list(iocs)[:20],
            "activity_count": len(activity),
        }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


def research_phishing_mapper(domain: str) -> dict[str, Any]:
    """Detect phishing campaigns targeting a domain.

    Checks for typosquatted domains via Certificate Transparency logs
    and searches URLhaus for known phishing URLs hosting on similar domains.

    Args:
        domain: target domain to check for phishing campaigns

    Returns:
        Dict with keys: domain, lookalike_domains, active_phishing_urls, risk_level
    """
    if not domain or len(domain.strip()) == 0:
        return {
            "domain": domain,
            "lookalike_domains": [],
            "active_phishing_urls": [],
            "risk_level": "unknown",
            "error": "domain required",
        }

    async def _run() -> dict[str, Any]:
        lookalikes: list[str] = []
        phishing_urls: list[dict[str, Any]] = []
        risk_score = 0

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            # Find lookalike domains via Certificate Transparency
            lookalikes = await _crt_sh_lookalikes(client, domain)

            # Check URLhaus for phishing URLs on lookalike domains
            for lookalike in lookalikes[:20]:
                results = await _urlhaus_host_check(client, lookalike)
                for result in results[:5]:
                    phishing_urls.append({
                        "url": result.get("url", ""),
                        "threat": result.get("threat", ""),
                        "tags": result.get("tags", []),
                        "date_added": result.get("date_added", ""),
                        "source_domain": lookalike,
                    })
                    risk_score += 10

        # Determine risk level
        if risk_score >= 50:
            risk_level = "critical"
        elif risk_score >= 20:
            risk_level = "high"
        elif risk_score > 0:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "domain": domain,
            "lookalike_domains_count": len(lookalikes),
            "lookalike_domains": lookalikes[:50],
            "active_phishing_urls_count": len(phishing_urls),
            "active_phishing_urls": phishing_urls[:30],
            "risk_level": risk_level,
            "risk_score": risk_score,
        }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


def research_botnet_tracker(ioc: str, ioc_type: str = "ip") -> dict[str, Any]:
    """Track botnet C2 infrastructure via threat feeds.

    Checks IOC against multiple botnet tracking services:
    - Feodo Tracker (C2 blocklists)
    - URLhaus (botnet URLs)
    - Shodan InternetDB (infrastructure details)

    Args:
        ioc: indicator of compromise (IP, domain, or URL)
        ioc_type: type of IOC - "ip", "domain", or "url" (default "ip")

    Returns:
        Dict with keys: ioc, known_c2, blocklist_status, threat_level
    """
    if not ioc or len(ioc.strip()) == 0:
        return {
            "ioc": ioc,
            "ioc_type": ioc_type,
            "known_c2": False,
            "blocklist_status": [],
            "threat_level": "unknown",
            "error": "ioc required",
        }

    async def _run() -> dict[str, Any]:
        known_c2 = False
        blocklist_status: list[dict[str, Any]] = []
        threat_level = "low"

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            # Check Feodo Tracker for C2 IPs
            if ioc_type == "ip":
                feodo_result = await _feodo_tracker_check(client, ioc)
                if feodo_result.get("listed"):
                    known_c2 = True
                    blocklist_status.append({
                        "list": "Feodo Tracker",
                        "listed": True,
                    })
                    threat_level = "critical"
                else:
                    blocklist_status.append({
                        "list": "Feodo Tracker",
                        "listed": False,
                    })

                # Check Shodan InternetDB
                shodan_data = await _shodan_internetdb_lookup(client, ioc)
                if shodan_data:
                    blocklist_status.append({
                        "list": "Shodan InternetDB",
                        "listed": True,
                        "ports": shodan_data.get("ports", []),
                        "tags": shodan_data.get("tags", []),
                    })
                    if shodan_data.get("tags"):
                        threat_level = "high"

            # Check URLhaus for botnet URLs
            if ioc_type in ("domain", "ip"):
                urlhaus_results = await _urlhaus_host_check(client, ioc)
                if urlhaus_results:
                    blocklist_status.append({
                        "list": "URLhaus",
                        "listed": True,
                        "count": len(urlhaus_results),
                    })
                    if any(r.get("threat") == "botnet" for r in urlhaus_results):
                        known_c2 = True
                        threat_level = "critical"

        return {
            "ioc": ioc,
            "ioc_type": ioc_type,
            "known_c2": known_c2,
            "blocklist_status": blocklist_status,
            "threat_level": threat_level,
            "sources_checked": [b["list"] for b in blocklist_status],
        }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


def research_malware_intel(hash_value: str) -> dict[str, Any]:
    """Cross-reference malware hash across multiple threat intelligence sources.

    Queries MalwareBazaar, AlienVault OTX, and CIRCL hashlookup for
    malware information, detection signatures, and family classification.

    Args:
        hash_value: SHA-256, MD5, or SHA-1 hash of malware sample

    Returns:
        Dict with keys: hash, detections, family, first_seen, tags
    """
    if not hash_value or len(hash_value.strip()) == 0:
        return {
            "hash": hash_value,
            "detections": [],
            "family": None,
            "first_seen": None,
            "tags": [],
            "error": "hash_value required",
        }

    async def _run() -> dict[str, Any]:
        detections: list[dict[str, Any]] = []
        family = None
        first_seen = None
        tags: set[str] = set()

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            # Query MalwareBazaar
            mb_result = await _malware_bazaar_lookup(client, hash_value)
            if mb_result.get("query_status") == "ok":
                data = mb_result.get("data", {})
                if isinstance(data, dict):
                    family = data.get("tags", [None])[0] if data.get("tags") else None
                    first_seen = data.get("first_submission_date")
                    detections.append({
                        "source": "MalwareBazaar",
                        "av_detections": data.get("av_detections", 0),
                        "signature": data.get("signature", ""),
                    })
                    tags.update(data.get("tags", []))

            # Query CIRCL hashlookup
            circl_result = await _circl_hashlookup(client, hash_value)
            if circl_result:
                detections.append({
                    "source": "CIRCL hashlookup",
                    "sources": circl_result.get("sources", []),
                    "parents": circl_result.get("parents", []),
                })

            # Search OTX
            otx_results = await _search_otx(client, hash_value)
            if otx_results:
                detections.append({
                    "source": "OTX",
                    "pulse_count": len(otx_results),
                })

        return {
            "hash": hash_value,
            "detections_count": len(detections),
            "detections": detections[:20],
            "family": family,
            "first_seen": first_seen,
            "tags": list(tags)[:20],
            "sources_checked": [d["source"] for d in detections],
        }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


def research_domain_reputation(domain: str) -> dict[str, Any]:
    """Aggregate domain reputation from multiple threat intelligence sources.

    Checks domain reputation across 5+ sources:
    - URLhaus malware database
    - Shodan InternetDB
    - OTX threat feeds
    - Ahmia darknet search
    - Certificate Transparency typosquatting

    Args:
        domain: domain to check (e.g., "example.com")

    Returns:
        Dict with keys: domain, reputation_score, verdicts_by_source, is_malicious
    """
    if not domain or len(domain.strip()) == 0:
        return {
            "domain": domain,
            "reputation_score": 0,
            "verdicts_by_source": {},
            "is_malicious": False,
            "error": "domain required",
        }

    async def _run() -> dict[str, Any]:
        verdicts: dict[str, dict[str, Any]] = {}
        malicious_votes = 0
        total_sources = 0

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            # Check URLhaus
            urlhaus_results = await _urlhaus_host_check(client, domain)
            total_sources += 1
            if urlhaus_results:
                verdicts["URLhaus"] = {
                    "verdict": "malicious",
                    "count": len(urlhaus_results),
                }
                malicious_votes += 1
            else:
                verdicts["URLhaus"] = {"verdict": "clean"}

            # Check OTX
            otx_results = await _search_otx(client, domain)
            total_sources += 1
            if otx_results:
                verdicts["OTX"] = {
                    "verdict": "suspicious",
                    "pulse_count": len(otx_results),
                }
                malicious_votes += 1
            else:
                verdicts["OTX"] = {"verdict": "clean"}

            # Check Ahmia
            ahmia_results = await _search_ahmia(client, domain)
            total_sources += 1
            if ahmia_results:
                verdicts["Ahmia"] = {
                    "verdict": "suspicious",
                    "result_count": len(ahmia_results),
                }
                malicious_votes += 0.5
            else:
                verdicts["Ahmia"] = {"verdict": "clean"}

            # Check Certificate Transparency for lookalikes (phishing risk)
            lookalikes = await _crt_sh_lookalikes(client, domain)
            total_sources += 1
            if lookalikes:
                verdicts["CT Lookalikes"] = {
                    "verdict": "phishing_risk",
                    "count": len(lookalikes),
                }
                malicious_votes += 0.5
            else:
                verdicts["CT Lookalikes"] = {"verdict": "clean"}

        # Calculate reputation score (0-100, lower is worse)
        reputation_score = max(0, 100 - int((malicious_votes / total_sources) * 100))
        is_malicious = malicious_votes >= (total_sources * 0.5)

        return {
            "domain": domain,
            "reputation_score": reputation_score,
            "verdicts_by_source": verdicts,
            "is_malicious": is_malicious,
            "malicious_sources": int(malicious_votes),
            "total_sources_checked": total_sources,
        }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


def research_ioc_enrich(ioc: str, ioc_type: str = "auto") -> dict[str, Any]:
    """Enrich any IOC (IP, domain, hash, URL) from multiple free sources.

    Simultaneously queries all available free threat intelligence sources:
    - AlienVault OTX
    - URLhaus
    - MalwareBazaar
    - Shodan InternetDB
    - CIRCL hashlookup
    - Ahmia darknet search

    Args:
        ioc: indicator of compromise (IP, domain, hash, or URL)
        ioc_type: type of IOC - "auto", "ip", "domain", "hash", or "url"
                  (default "auto" auto-detects type)

    Returns:
        Dict with keys: ioc, ioc_type, sources_checked, enrichments, threat_score, verdicts
    """
    if not ioc or len(ioc.strip()) == 0:
        return {
            "ioc": ioc,
            "ioc_type": ioc_type,
            "sources_checked": [],
            "enrichments": [],
            "threat_score": 0,
            "verdicts": {},
            "error": "ioc required",
        }

    # Auto-detect IOC type
    detected_type = ioc_type
    if ioc_type == "auto":
        if re.match(r"^[a-f0-9]{32}$|^[a-f0-9]{40}$|^[a-f0-9]{64}$", ioc.lower()):
            detected_type = "hash"
        elif re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ioc):
            detected_type = "ip"
        elif ioc.startswith("http://") or ioc.startswith("https://"):
            detected_type = "url"
        else:
            detected_type = "domain"

    async def _run() -> dict[str, Any]:
        enrichments: list[dict[str, Any]] = []
        sources_checked: set[str] = set()
        verdicts: dict[str, str] = {}
        threat_score = 0

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            # Search OTX
            otx_results = await _search_otx(client, ioc)
            sources_checked.add("OTX")
            if otx_results:
                enrichments.append({
                    "source": "OTX",
                    "type": "threat_pulses",
                    "count": len(otx_results),
                    "data": otx_results[:3],
                })
                verdicts["OTX"] = "malicious"
                threat_score += 30

            # Query MalwareBazaar (for hashes)
            if detected_type == "hash":
                mb_result = await _malware_bazaar_lookup(client, ioc)
                sources_checked.add("MalwareBazaar")
                if mb_result.get("query_status") == "ok":
                    enrichments.append({
                        "source": "MalwareBazaar",
                        "type": "malware_info",
                        "data": mb_result.get("data", {}),
                    })
                    verdicts["MalwareBazaar"] = "malicious"
                    threat_score += 40

                # CIRCL hashlookup
                circl_result = await _circl_hashlookup(client, ioc)
                sources_checked.add("CIRCL")
                if circl_result:
                    enrichments.append({
                        "source": "CIRCL",
                        "type": "hash_relations",
                        "data": circl_result,
                    })
                    verdicts["CIRCL"] = "suspicious"
                    threat_score += 20

            # Query Shodan InternetDB (for IPs)
            if detected_type == "ip":
                shodan_result = await _shodan_internetdb_lookup(client, ioc)
                sources_checked.add("Shodan")
                if shodan_result:
                    enrichments.append({
                        "source": "Shodan",
                        "type": "infrastructure",
                        "ports": shodan_result.get("ports", []),
                        "tags": shodan_result.get("tags", []),
                    })
                    if shodan_result.get("tags"):
                        verdicts["Shodan"] = "suspicious"
                        threat_score += 25

                # Feodo Tracker for C2
                feodo_result = await _feodo_tracker_check(client, ioc)
                sources_checked.add("Feodo")
                if feodo_result.get("listed"):
                    verdicts["Feodo"] = "malicious"
                    threat_score += 50

            # URLhaus check (for domains/URLs)
            if detected_type in ("domain", "url"):
                urlhaus_results = await _urlhaus_host_check(client, ioc)
                sources_checked.add("URLhaus")
                if urlhaus_results:
                    enrichments.append({
                        "source": "URLhaus",
                        "type": "malicious_urls",
                        "count": len(urlhaus_results),
                        "data": urlhaus_results[:3],
                    })
                    verdicts["URLhaus"] = "malicious"
                    threat_score += 35

            # Ahmia darknet search
            ahmia_results = await _search_ahmia(client, ioc)
            sources_checked.add("Ahmia")
            if ahmia_results:
                enrichments.append({
                    "source": "Ahmia",
                    "type": "darknet_mentions",
                    "count": len(ahmia_results),
                })
                verdicts["Ahmia"] = "suspicious"
                threat_score += 15

        # Cap threat score at 100
        threat_score = min(100, threat_score)

        return {
            "ioc": ioc,
            "ioc_type": detected_type,
            "sources_checked": sorted(list(sources_checked)),
            "enrichments_count": len(enrichments),
            "enrichments": enrichments,
            "threat_score": threat_score,
            "verdicts": verdicts,
            "verdict_summary": "malicious" if threat_score >= 60 else "suspicious" if threat_score >= 30 else "clean",
        }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
