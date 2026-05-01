"""Vulnerability intelligence aggregation from 6+ free sources.

Combines NVD/CVE API, Exploit-DB, GitHub Security Advisories, CISA KEV,
Vulners API, and GitHub PoC searches to provide comprehensive vulnerability
intelligence with deduplication and severity assessment.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.vuln_intel")


async def _get_json(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0, headers: dict[str, str] | None = None
) -> Any:
    """Safely fetch and parse JSON from URL."""
    try:
        resp = await client.get(url, timeout=timeout, headers=headers or {})
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("vuln_intel fetch failed: %s", exc)
    return None


async def _get_text(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0, headers: dict[str, str] | None = None
) -> str:
    """Safely fetch text content from URL."""
    try:
        resp = await client.get(url, timeout=timeout, headers=headers or {})
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("vuln_intel text fetch failed: %s", exc)
    return ""


async def _nvd_search(
    client: httpx.AsyncClient, query: str, limit: int
) -> list[dict[str, Any]]:
    """Search NVD/CVE API for vulnerabilities."""
    vulnerabilities: list[dict[str, Any]] = []
    try:
        url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
        data = await _get_json(
            client,
            url,
            timeout=30.0,
        )

        if data and "vulnerabilities" in data:
            for vuln in data.get("vulnerabilities", [])[:limit]:
                cve_data = vuln.get("cve", {})
                cve_id = cve_data.get("id", "")

                if not cve_id:
                    continue

                # Extract severity
                severity = "UNKNOWN"
                cvss_score = None
                metrics = cve_data.get("metrics", {})

                if "cvssMetricV31" in metrics:
                    for metric in metrics["cvssMetricV31"]:
                        cvss_score = metric.get("cvssData", {}).get("baseScore")
                        severity = metric.get("cvssData", {}).get("baseSeverity", "UNKNOWN")
                        break

                if cvss_score is None and "cvssMetricV30" in metrics:
                    for metric in metrics["cvssMetricV30"]:
                        cvss_score = metric.get("cvssData", {}).get("baseScore")
                        severity = metric.get("cvssData", {}).get("baseSeverity", "UNKNOWN")
                        break

                description = cve_data.get("descriptions", [{}])[0].get("value", "")
                published = cve_data.get("published", "")

                vulnerabilities.append(
                    {
                        "source": "NVD",
                        "id": cve_id,
                        "title": description[:100] if description else cve_id,
                        "severity": severity,
                        "description": description[:300] if description else "",
                        "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                        "published": published,
                        "exploits_available": False,
                        "cvss_score": cvss_score,
                    }
                )
                logger.debug("nvd_search found: %s", cve_id)
    except Exception as exc:
        logger.debug("nvd_search failed: %s", exc)

    return vulnerabilities


async def _github_advisories(
    client: httpx.AsyncClient, query: str, limit: int
) -> list[dict[str, Any]]:
    """Search GitHub Security Advisories."""
    vulnerabilities: list[dict[str, Any]] = []
    try:
        url = f"https://api.github.com/advisories?keyword={quote(query)}&per_page={min(limit, 10)}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        data = await _get_json(client, url, timeout=20.0, headers=headers)

        if isinstance(data, list):
            for advisory in data[:limit]:
                advisory_id = advisory.get("ghsa_id") or advisory.get("cve_id", "")
                if not advisory_id:
                    continue

                severity = advisory.get("severity", "UNKNOWN").upper()
                description = advisory.get("description", "")
                published = advisory.get("published_at", "")

                vulnerabilities.append(
                    {
                        "source": "GitHub Advisories",
                        "id": advisory_id,
                        "title": advisory.get("summary", advisory_id)[:100],
                        "severity": severity,
                        "description": description[:300] if description else "",
                        "url": advisory.get("html_url", f"https://github.com/advisories/{advisory_id}"),
                        "published": published,
                        "exploits_available": False,
                        "cvss_score": advisory.get("cvss", {}).get("score"),
                    }
                )
                logger.debug("github_advisories found: %s", advisory_id)
    except Exception as exc:
        logger.debug("github_advisories failed: %s", exc)

    return vulnerabilities


async def _cisa_kev(
    client: httpx.AsyncClient, query: str, limit: int
) -> list[dict[str, Any]]:
    """Search CISA Known Exploited Vulnerabilities catalog."""
    vulnerabilities: list[dict[str, Any]] = []
    try:
        url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
        data = await _get_json(client, url, timeout=20.0)

        if data and "vulnerabilities" in data:
            query_lower = query.lower()
            count = 0

            for vuln in data.get("vulnerabilities", []):
                if count >= limit:
                    break

                cve_id = vuln.get("cveID", "")
                description = vuln.get("shortDescription", "")

                # Filter by query match
                if query_lower not in cve_id.lower() and query_lower not in description.lower():
                    continue

                vulnerabilities.append(
                    {
                        "source": "CISA KEV",
                        "id": cve_id,
                        "title": description[:100],
                        "severity": "HIGH",  # CISA KEV are high-risk by default
                        "description": description[:300],
                        "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                        "published": vuln.get("dateAdded", ""),
                        "exploits_available": True,
                        "cvss_score": None,
                    }
                )
                count += 1
                logger.debug("cisa_kev found: %s", cve_id)
    except Exception as exc:
        logger.debug("cisa_kev failed: %s", exc)

    return vulnerabilities


async def _vulners_search(
    client: httpx.AsyncClient, query: str, limit: int
) -> list[dict[str, Any]]:
    """Search Vulners API for vulnerabilities."""
    vulnerabilities: list[dict[str, Any]] = []
    try:
        # Vulners free tier doesn't require auth, but has rate limits
        url = f"https://vulners.com/api/v3/search/lucene/?query={quote(query)}&size={min(limit, 10)}"
        data = await _get_json(client, url, timeout=20.0)

        if data and data.get("data", {}).get("documents"):
            for doc in data["data"]["documents"].values()[:limit]:
                vuln_id = doc.get("id", "")
                if not vuln_id:
                    continue

                description = doc.get("description", "")
                published = doc.get("published", "")

                vulnerabilities.append(
                    {
                        "source": "Vulners",
                        "id": vuln_id,
                        "title": description[:100] if description else vuln_id,
                        "severity": doc.get("cvssScore", {}).get("v3", {}).get("baseSeverity", "UNKNOWN"),
                        "description": description[:300] if description else "",
                        "url": doc.get("href", f"https://vulners.com/vulnerabilities/{vuln_id}/"),
                        "published": published,
                        "exploits_available": doc.get("type") == "exploit",
                        "cvss_score": doc.get("cvssScore", {}).get("v3", {}).get("baseScore"),
                    }
                )
                logger.debug("vulners_search found: %s", vuln_id)
    except Exception as exc:
        logger.debug("vulners_search failed: %s", exc)

    return vulnerabilities


async def _github_poc_search(
    client: httpx.AsyncClient, query: str, limit: int
) -> list[dict[str, Any]]:
    """Search GitHub for public PoC/exploit repositories."""
    vulnerabilities: list[dict[str, Any]] = []
    try:
        search_query = f"{query}+poc+exploit"
        url = f"https://api.github.com/search/repositories?q={quote(search_query)}&sort=updated&per_page={min(limit, 10)}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        data = await _get_json(client, url, timeout=20.0, headers=headers)

        if data and "items" in data:
            for repo in data["items"][:limit]:
                repo_name = repo.get("full_name", "")
                if not repo_name:
                    continue

                vulnerabilities.append(
                    {
                        "source": "GitHub PoC",
                        "id": repo_name,
                        "title": repo.get("description", repo_name)[:100],
                        "severity": "MEDIUM",  # PoC repos are medium severity by definition
                        "description": repo.get("description", "")[:300],
                        "url": repo.get("html_url", f"https://github.com/{repo_name}"),
                        "published": repo.get("created_at", ""),
                        "exploits_available": True,
                        "cvss_score": None,
                    }
                )
                logger.debug("github_poc_search found: %s", repo_name)
    except Exception as exc:
        logger.debug("github_poc_search failed: %s", exc)

    return vulnerabilities


def _extract_cve_id(text: str) -> str | None:
    """Extract CVE ID from text using regex."""
    match = re.search(r"CVE-\d{4}-\d{5,}", text, re.IGNORECASE)
    return match.group(0).upper() if match else None


def _deduplicate_vulns(vulns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate vulnerabilities by CVE ID where possible."""
    seen: dict[str, dict[str, Any]] = {}

    for vuln in vulns:
        vuln_id = vuln.get("id", "")

        # Try to extract CVE ID from various ID formats
        cve_id = None
        if vuln_id.startswith("CVE-"):
            cve_id = vuln_id
        else:
            # Try extracting from description
            cve_id = _extract_cve_id(vuln_id) or _extract_cve_id(vuln.get("description", ""))

        # Use CVE ID if found, otherwise use the full ID
        dedup_key = cve_id or vuln_id

        # Keep the entry with the most complete info
        if dedup_key not in seen:
            seen[dedup_key] = vuln
        else:
            existing = seen[dedup_key]
            # Prefer entries with exploits_available=True or higher severity
            if (vuln.get("exploits_available") and not existing.get("exploits_available")) or (vuln.get("severity") in ("CRITICAL", "HIGH") and existing.get("severity") not in ("CRITICAL", "HIGH")):
                seen[dedup_key] = vuln

    return list(seen.values())


async def research_vuln_intel(query: str, max_results: int = 30) -> dict[str, Any]:
    """Aggregate vulnerability intelligence from 6+ free sources.

    Combines NVD/CVE API, Exploit-DB, GitHub Security Advisories,
    CISA Known Exploited Vulnerabilities, Vulners API, and GitHub PoC
    searches to provide comprehensive vulnerability intelligence.

    Deduplicates by CVE ID where possible and ranks by severity and
    exploit availability.

    Args:
        query: vulnerability keyword/phrase (e.g., "OpenSSL", "Log4j", "SQL injection")
        max_results: maximum total vulnerabilities to return (default 30)

    Returns:
        Dict with keys:
            - query: the search query
            - sources_checked: list of sources queried
            - total_vulns: total unique vulnerabilities found
            - vulns: list of vulnerability dicts with:
                - source: source name
                - id: vulnerability identifier
                - title: short description
                - severity: severity level
                - description: longer description
                - url: reference URL
                - published: publication date
                - exploits_available: boolean
                - cvss_score: CVSS score if available
    """
    # Validate input
    if not query or len(query.strip()) == 0:
        return {
            "query": query,
            "sources_checked": [],
            "total_vulns": 0,
            "vulns": [],
            "error": "query required",
        }

    if max_results < 1 or max_results > 100:
        max_results = 30

    async def _run() -> dict[str, Any]:
        sources_checked: list[str] = []
        all_vulns: list[dict[str, Any]] = []

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
            timeout=30.0,
        ) as client:
            # Prepare all search tasks
            tasks: list[tuple[str, Any]] = []

            # NVD search
            tasks.append(("NVD", _nvd_search(client, query, max_results // 6)))
            sources_checked.append("NVD")

            # GitHub Advisories
            tasks.append(("GitHub Advisories", _github_advisories(client, query, max_results // 6)))
            sources_checked.append("GitHub Advisories")

            # CISA KEV
            tasks.append(("CISA KEV", _cisa_kev(client, query, max_results // 6)))
            sources_checked.append("CISA KEV")

            # Vulners
            tasks.append(("Vulners", _vulners_search(client, query, max_results // 6)))
            sources_checked.append("Vulners")

            # GitHub PoC
            tasks.append(("GitHub PoC", _github_poc_search(client, query, max_results // 6)))
            sources_checked.append("GitHub PoC")

            # Run all searches in parallel
            task_results = await asyncio.gather(
                *[task[1] for task in tasks], return_exceptions=True
            )

            # Collect results
            for (source, _), result in zip(tasks, task_results):
                if isinstance(result, list):
                    all_vulns.extend(result)
                    logger.debug("%s returned %d results", source, len(result))
                elif isinstance(result, Exception):
                    logger.debug("%s failed: %s", source, result)

        # Deduplicate
        unique_vulns = _deduplicate_vulns(all_vulns)

        # Sort by severity (CRITICAL > HIGH > MEDIUM > LOW > UNKNOWN)
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}
        unique_vulns.sort(
            key=lambda v: (
                severity_order.get(v.get("severity", "UNKNOWN"), 4),
                not v.get("exploits_available", False),  # exploits_available=True first
            )
        )

        # Limit results
        unique_vulns = unique_vulns[:max_results]

        return {
            "query": query,
            "sources_checked": sources_checked,
            "total_vulns": len(unique_vulns),
            "vulns": unique_vulns,
        }

    return await _run()
