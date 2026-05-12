"""CVE database lookup tools — query NVD (National Vulnerability Database)."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.cve_lookup")

_NVD_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _validate_cve_id(cve_id: str) -> bool:
    """Validate CVE ID format: CVE-YYYY-NNNN+ (4+ digits)."""
    return bool(re.match(r"^CVE-\d{4}-\d{4,}$", cve_id.upper()))


@handle_tool_errors("research_cve_lookup")
async def research_cve_lookup(query: str, limit: int = 10) -> dict[str, Any]:
    """Search CVE database using NVD API (free, rate limited).

    Queries the National Vulnerability Database by keyword.

    Args:
        query: keyword or phrase to search (e.g., "OpenSSL", "SQL injection")
        limit: max number of results to return (1-100, default 10)

    Returns:
        Dict with keys: query, total_results, cves (list of CVE details)
    """
    if not query or len(query.strip()) == 0:
        return {"query": query, "total_results": 0, "cves": [], "error": "query required"}

    limit = max(1, min(limit, 100))

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                _NVD_API_BASE,
                params={
                    "keywordSearch": query,
                    "resultsPerPage": limit,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        cves = []
        total_results = data.get("totalResults", 0)

        for vuln in data.get("vulnerabilities", []):
            cve_data = vuln.get("cve", {})
            cve_id = cve_data.get("id")
            description = cve_data.get("descriptions", [{}])[0].get("value", "")

            # Extract CVSS score (prefer v3.1, fallback to v2)
            cvss_score = None
            severity = "UNKNOWN"
            metrics = cve_data.get("metrics", {})

            # Try CVSS v3.1
            if "cvssMetricV31" in metrics:
                for metric in metrics["cvssMetricV31"]:
                    cvss_score = metric.get("cvssData", {}).get("baseScore")
                    severity = metric.get("cvssData", {}).get("baseSeverity", "UNKNOWN")
                    break

            # Fallback to CVSS v3.0
            if cvss_score is None and "cvssMetricV30" in metrics:
                for metric in metrics["cvssMetricV30"]:
                    cvss_score = metric.get("cvssData", {}).get("baseScore")
                    severity = metric.get("cvssData", {}).get("baseSeverity", "UNKNOWN")
                    break

            # Fallback to CVSS v2
            if cvss_score is None and "cvssMetricV2" in metrics:
                for metric in metrics["cvssMetricV2"]:
                    cvss_score = metric.get("cvssData", {}).get("baseScore")
                    break

            # Extract published and modified dates
            published_date = cve_data.get("published")
            last_modified = cve_data.get("lastModified")

            # Extract references
            references = []
            for ref in cve_data.get("references", []):
                url = ref.get("url")
                if url:
                    references.append(url)

            cves.append(
                {
                    "id": cve_id,
                    "description": description[:500] if description else "",  # Cap at 500 chars
                    "cvss": cvss_score,
                    "severity": severity,
                    "published": published_date,
                    "last_modified": last_modified,
                    "references": references[:5],  # Cap at 5 references
                }
            )

        return {"query": query, "total_results": total_results, "cves": cves}

    except httpx.TimeoutException:
        logger.warning("cve_lookup_timeout query=%s", query)
        return {
            "query": query,
            "total_results": 0,
            "cves": [],
            "error": "Request timed out (NVD API rate limited)",
        }
    except Exception as exc:
        logger.warning("cve_lookup_failed query=%s: %s", query, exc)
        return {"query": query, "total_results": 0, "cves": [], "error": str(exc)}


@handle_tool_errors("research_cve_detail")
async def research_cve_detail(cve_id: str) -> dict[str, Any]:
    """Get detailed information for a specific CVE.

    Queries NVD by exact CVE ID. Validate format: CVE-YYYY-NNNN+.

    Args:
        cve_id: CVE identifier (e.g., "CVE-2021-44228")

    Returns:
        Dict with detailed CVE info: id, description, cvss, severity, dates,
        references, affected_products, weaknesses
    """
    if not _validate_cve_id(cve_id):
        return {
            "cve_id": cve_id,
            "error": "Invalid CVE ID format (expected CVE-YYYY-NNNN+)",
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                _NVD_API_BASE,
                params={"cveId": cve_id.upper()},
            )
            resp.raise_for_status()
            data = resp.json()

        if not data.get("vulnerabilities"):
            return {"cve_id": cve_id, "error": "CVE not found"}

        vuln = data["vulnerabilities"][0]
        cve_data = vuln.get("cve", {})

        # Extract CVSS score
        cvss_score = None
        severity = "UNKNOWN"
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

        if cvss_score is None and "cvssMetricV2" in metrics:
            for metric in metrics["cvssMetricV2"]:
                cvss_score = metric.get("cvssData", {}).get("baseScore")
                break

        # Extract description
        description = cve_data.get("descriptions", [{}])[0].get("value", "")

        # Extract references
        references = []
        for ref in cve_data.get("references", []):
            url = ref.get("url")
            if url:
                references.append(url)

        # Extract affected products (CPE entries)
        affected_products = []
        for config in cve_data.get("configurations", []):
            for node in config.get("nodes", []):
                for cpe_match in node.get("cpeMatch", []):
                    cpe = cpe_match.get("criteria")
                    if cpe:
                        affected_products.append(cpe)

        # Extract weaknesses
        weaknesses = []
        for weakness in cve_data.get("weaknesses", []):
            for description in weakness.get("description", []):
                cwe_id = description.get("value")
                if cwe_id:
                    weaknesses.append(cwe_id)

        return {
            "cve_id": cve_data.get("id"),
            "description": description,
            "cvss": cvss_score,
            "severity": severity,
            "published": cve_data.get("published"),
            "last_modified": cve_data.get("lastModified"),
            "references": references,
            "affected_products": affected_products[:10],  # Cap at 10
            "weaknesses": weaknesses[:5],  # Cap at 5
        }

    except httpx.TimeoutException:
        logger.warning("cve_detail_timeout cve_id=%s", cve_id)
        return {
            "cve_id": cve_id,
            "error": "Request timed out (NVD API rate limited)",
        }
    except Exception as exc:
        logger.warning("cve_detail_failed cve_id=%s: %s", cve_id, exc)
        return {"cve_id": cve_id, "error": str(exc)}
