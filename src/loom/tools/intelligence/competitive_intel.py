"""Competitive intelligence tool — fuse weak signals for market positioning analysis.

Provides:
- research_competitive_intel: Multi-source competitive analysis combining SEC filings,
  USPTO patents, GitHub activity, Certificate Transparency, and DNS signals.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

from loom.http_helpers import fetch_json, fetch_text
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.competitive_intel")

# Semaphore to limit concurrent DNS/HTTP requests
from loom.providers.semaphore_registry import get_semaphore
_request_semaphore = get_semaphore("competitive_intel", max_concurrent=5)


async def _get_json_semaphore(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0
) -> Any:
    """Safely fetch JSON from URL with semaphore."""
    async with _request_semaphore:
        return await fetch_json(client, url, timeout=timeout)


async def _get_text_semaphore(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> str:
    """Safely fetch text from URL with semaphore."""
    async with _request_semaphore:
        return await fetch_text(client, url, timeout=timeout)


async def _fetch_sec_filings(
    client: httpx.AsyncClient, company: str
) -> dict[str, Any]:
    """Fetch SEC EDGAR filings for company.

    Args:
        client: httpx async client
        company: Company name to search

    Returns:
        Dict with filing count and recent filings list
    """
    try:
        # Build date range: past 2 years
        end_date = datetime.now(UTC).strftime("%Y-%m-%d")
        start_date = (datetime.now(UTC) - timedelta(days=730)).strftime("%Y-%m-%d")

        url = (
            f"https://efts.sec.gov/LATEST/search-index"
            f"?q={quote(company)}"
            f"&dateRange=custom"
            f"&startdt={start_date}"
            f"&enddt={end_date}"
            f"&forms=10-K,10-Q"
        )

        text = await _get_text_semaphore(client, url, timeout=30.0)
        if not text:
            return {"count": 0, "recent": []}

        # Extract filing links and dates from HTML
        # Look for 10-K and 10-Q form references
        filings: list[dict[str, str]] = []

        # Simple regex patterns for 10-K and 10-Q forms
        filing_pattern = r"(10-[KQ])\s*\|?\s*(\d{4}-\d{2}-\d{2})"
        matches = re.finditer(filing_pattern, text)

        for match in matches:
            form_type = match.group(1)
            filed_date = match.group(2)
            filings.append({"form": form_type, "date": filed_date})

        # Remove duplicates and sort by date
        filings_dedup = {(f["form"], f["date"]): f for f in filings}.values()
        filings_sorted = sorted(filings_dedup, key=lambda x: x["date"], reverse=True)

        return {
            "count": len(filings_sorted),
            "recent": list(filings_sorted[:5]),
        }

    except Exception as exc:
        logger.warning("sec_filings_error company=%s error=%s", company, exc)
        return {"count": 0, "recent": []}


async def _fetch_patents(
    client: httpx.AsyncClient, company: str
) -> dict[str, Any]:
    """Fetch USPTO patents for company.

    Args:
        client: httpx async client
        company: Company name to search

    Returns:
        Dict with patent count and recent patent titles
    """
    try:
        # USPTO IBD API endpoint
        url = (
            f"https://developer.uspto.gov/ibd-api/v1/application/publications"
            f"?searchText={quote(company)}"
            f"&start=0"
            f"&rows=20"
        )

        data = await _get_json_semaphore(client, url, timeout=25.0)
        if not data or "response" not in data:
            return {"count": 0, "recent_titles": []}

        response = data.get("response", {})
        patents = response.get("docs", [])

        patent_titles: list[str] = []
        for patent in patents[:10]:
            title = patent.get("publicationTitle", "") or patent.get("title", "")
            if title:
                patent_titles.append(title)

        return {
            "count": response.get("numFound", 0),
            "recent_titles": patent_titles,
        }

    except Exception as exc:
        logger.warning("patents_error company=%s error=%s", company, exc)
        return {"count": 0, "recent_titles": []}


async def _fetch_github_activity(
    client: httpx.AsyncClient, github_org: str
) -> dict[str, Any]:
    """Fetch GitHub org activity metrics.

    Args:
        client: httpx async client
        github_org: GitHub organization name

    Returns:
        Dict with repos, stars, languages used
    """
    try:
        url = f"https://api.github.com/orgs/{quote(github_org)}/repos?sort=updated&per_page=50"

        data = await _get_json_semaphore(client, url, timeout=20.0)
        if not data or not isinstance(data, list):
            return {
                "repo_count": 0,
                "total_stars": 0,
                "languages": [],
                "recent_repos": [],
            }

        # Collect metrics
        languages: dict[str, int] = {}
        total_stars = 0
        recent_repos: list[dict[str, Any]] = []

        for repo in data[:20]:
            total_stars += repo.get("stargazers_count", 0)

            # Track language
            lang = repo.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

            # Track recent repos with activity
            recent_repos.append({
                "name": repo.get("name", ""),
                "stars": repo.get("stargazers_count", 0),
                "language": lang or "Unknown",
                "updated": repo.get("updated_at", "")[:10],
            })

        # Sort languages by frequency
        top_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)
        top_langs_list = [lang for lang, _ in top_langs[:5]]

        return {
            "repo_count": len(data),
            "total_stars": total_stars,
            "languages": top_langs_list,
            "recent_repos": recent_repos[:5],
        }

    except Exception as exc:
        logger.warning("github_activity_error org=%s error=%s", github_org, exc)
        return {
            "repo_count": 0,
            "total_stars": 0,
            "languages": [],
            "recent_repos": [],
        }


async def _fetch_certificate_transparency(
    client: httpx.AsyncClient, domain: str
) -> dict[str, Any]:
    """Fetch new subdomains from Certificate Transparency logs.

    Args:
        client: httpx async client
        domain: Domain to search

    Returns:
        Dict with new subdomains found
    """
    try:
        url = f"https://crt.sh/?q=%25.{quote(domain)}&output=json"

        data = await _get_json_semaphore(client, url, timeout=25.0)
        if not data or not isinstance(data, list):
            return {"total_found": 0, "recent_subdomains": []}

        # Extract unique subdomains
        subdomains: set[str] = set()
        for entry in data:
            name_value = entry.get("name_value", "")
            for line in name_value.split("\n"):
                line = line.strip().lstrip("*.")
                if line and (line.endswith(f".{domain}") or line == domain):
                    subdomains.add(line)

        # Try to identify newer subdomains by checking entry timestamps
        recent_subs: list[str] = []
        for entry in data[-20:]:  # Check most recent CT log entries
            name_value = entry.get("name_value", "")
            for line in name_value.split("\n"):
                line = line.strip().lstrip("*.")
                if (
                    line
                    and (line.endswith(f".{domain}") or line == domain)
                    and line not in recent_subs
                ):
                    recent_subs.append(line)

        return {
            "total_found": len(subdomains),
            "recent_subdomains": recent_subs[:20],
        }

    except Exception as exc:
        logger.warning("ct_subdomains_error domain=%s error=%s", domain, exc)
        return {"total_found": 0, "recent_subdomains": []}


async def _fetch_dns_records(
    client: httpx.AsyncClient, domain: str
) -> dict[str, Any]:
    """Fetch DNS records to identify technologies.

    Args:
        client: httpx async client
        domain: Domain to query

    Returns:
        Dict with DNS records and detected technologies
    """
    try:
        # Query Google DNS API for multiple record types
        record_types = ["A", "AAAA", "MX", "TXT", "CNAME", "NS"]
        records: dict[str, list[str]] = {}

        for rtype in record_types:
            url = f"https://dns.google/resolve?name={quote(domain)}&type={rtype}"
            data = await _get_json_semaphore(client, url, timeout=10.0)

            if data and "Answer" in data:
                records[rtype] = [
                    a.get("data", "") for a in data.get("Answer", [])
                ]

        # Detect technology stack from DNS
        detected_techs: list[str] = []

        # Check MX records for email providers
        mx_records = records.get("MX", [])
        mx_str = " ".join(mx_records).lower()
        if "google" in mx_str or "gmail" in mx_str:
            detected_techs.append("Google Workspace")
        if "microsoft" in mx_str or "outlook" in mx_str:
            detected_techs.append("Microsoft 365")

        # Check CNAME for CDN/infrastructure
        cname_records = records.get("CNAME", [])
        cname_str = " ".join(cname_records).lower()
        if "cloudflare" in cname_str:
            detected_techs.append("Cloudflare")
        if "fastly" in cname_str:
            detected_techs.append("Fastly")
        if "akamai" in cname_str:
            detected_techs.append("Akamai")
        if "cloudfront" in cname_str:
            detected_techs.append("CloudFront")

        return {
            "records": records,
            "detected_technologies": detected_techs,
        }

    except Exception as exc:
        logger.warning("dns_records_error domain=%s error=%s", domain, exc)
        return {"records": {}, "detected_technologies": []}


def _synthesize_signals(
    sec_data: dict[str, Any],
    patent_data: dict[str, Any],
    github_data: dict[str, Any],
    ct_data: dict[str, Any],
    dns_data: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    """Synthesize weak signals into assessment.

    Args:
        sec_data: SEC filings data
        patent_data: Patent data
        github_data: GitHub activity data
        ct_data: Certificate Transparency data
        dns_data: DNS records and tech data

    Returns:
        Tuple of (signals list, overall_assessment string)
    """
    signals: list[dict[str, Any]] = []

    # SEC filing activity signal
    if sec_data.get("count", 0) > 0:
        signals.append({
            "source": "SEC EDGAR",
            "signal_type": "Financial Transparency",
            "description": f"Found {sec_data['count']} recent 10-K/10-Q filings",
            "confidence": 0.85,
        })

    # Patent filing activity signal
    if patent_data.get("count", 0) > 0:
        signals.append({
            "source": "USPTO Patents",
            "signal_type": "Innovation Activity",
            "description": f"Found {patent_data['count']} recent patent filings",
            "confidence": 0.80,
        })

    # GitHub activity signal
    if github_data.get("repo_count", 0) > 0:
        stars = github_data.get("total_stars", 0)
        signal_desc = f"Active GitHub org with {github_data['repo_count']} repos"
        if stars > 0:
            signal_desc += f", {stars} total stars"
        signals.append({
            "source": "GitHub",
            "signal_type": "Engineering Velocity",
            "description": signal_desc,
            "confidence": 0.90,
        })

    # New subdomains signal
    if ct_data.get("total_found", 0) > 10:
        signals.append({
            "source": "Certificate Transparency",
            "signal_type": "Product/Service Expansion",
            "description": f"Detected {ct_data['total_found']} subdomains indicating multiple services",
            "confidence": 0.75,
        })

    # Technology stack signal
    detected_techs = dns_data.get("detected_technologies", [])
    if detected_techs:
        signals.append({
            "source": "DNS & Infrastructure",
            "signal_type": "Tech Stack",
            "description": f"Using: {', '.join(detected_techs)}",
            "confidence": 0.70,
        })

    # Generate overall assessment
    assessment_parts: list[str] = []

    filing_activity = "Strong" if sec_data.get("count", 0) >= 2 else "Limited"
    assessment_parts.append(f"Financial reporting: {filing_activity}")

    patent_velocity = "Active" if patent_data.get("count", 0) > 5 else "Moderate"
    assessment_parts.append(f"Patent velocity: {patent_velocity}")

    repo_health = "Mature" if github_data.get("repo_count", 0) > 10 else "Growing"
    assessment_parts.append(f"Open-source presence: {repo_health}")

    service_diversity = (
        "Diverse" if ct_data.get("total_found", 0) > 15 else "Focused"
    )
    assessment_parts.append(f"Service portfolio: {service_diversity}")

    overall_assessment = (
        f"Competitive signals indicate: {', '.join(assessment_parts)}. "
        f"Organization demonstrates {'strong' if len(signals) >= 4 else 'moderate'} "
        f"market activity across filings, R&D, engineering, and infrastructure."
    )

    return signals, overall_assessment


@handle_tool_errors("research_competitive_intel")
async def research_competitive_intel(
    company: str,
    domain: str | None = None,
    github_org: str | None = None,
) -> dict[str, Any]:
    """Analyze company competitive positioning via weak signal fusion.

    Combines data from:
    1. SEC EDGAR filings (10-K, 10-Q)
    2. USPTO patents (recent filings)
    3. GitHub activity (repos, stars, languages)
    4. Certificate Transparency logs (subdomain enumeration)
    5. DNS records (technology stack detection)

    Args:
        company: Company name to analyze (e.g., "OpenAI", "Anthropic")
        domain: Optional domain (e.g., "openai.com"). If None, inferred from company.
        github_org: Optional GitHub organization. If None, inferred from company.

    Returns:
        Dict with keys:
        - company: company name
        - domain: domain used
        - github_org: GitHub org searched
        - signals: list of dicts with source, signal_type, description, confidence
        - sec_filings: dict with count and recent filings list
        - patents: dict with count and recent_titles list
        - github_activity: dict with repo_count, total_stars, languages, recent_repos
        - new_subdomains: dict with total_found and recent_subdomains list
        - dns_records: dict with records and detected_technologies
        - overall_assessment: synthesized assessment string
    """

    async def _run() -> dict[str, Any]:
        # Validate inputs
        company_clean = (company or "").strip()
        if not company_clean or len(company_clean) > 256:
            return {
                "company": company_clean,
                "error": "company must be 1-256 characters",
            }

        domain_clean = (domain or "").strip() if domain else None
        github_org_clean = (github_org or "").strip() if github_org else None

        # Infer domain from company name if not provided
        if not domain_clean:
            # Simple inference: lowercase and replace spaces with hyphens
            inferred = company_clean.lower().replace(" ", "-").replace("&", "and")
            # Remove special chars except hyphens
            inferred = re.sub(r"[^a-z0-9\-]", "", inferred)
            domain_clean = f"{inferred}.com"

        # Infer GitHub org from company if not provided
        if not github_org_clean:
            inferred_org = company_clean.lower().replace(" ", "-").replace("&", "and")
            inferred_org = re.sub(r"[^a-z0-9\-]", "", inferred_org)
            github_org_clean = inferred_org

        logger.info(
            "competitive_intel start company=%s domain=%s github_org=%s",
            company_clean,
            domain_clean,
            github_org_clean,
        )

        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            # Fetch all signals in parallel with overall timeout
            sec_task = _fetch_sec_filings(client, company_clean)
            patent_task = _fetch_patents(client, company_clean)
            github_task = _fetch_github_activity(client, github_org_clean)
            ct_task = _fetch_certificate_transparency(client, domain_clean)
            dns_task = _fetch_dns_records(client, domain_clean)

            try:
                sec_data, patent_data, github_data, ct_data, dns_data = (
                    await asyncio.wait_for(
                        asyncio.gather(
                            sec_task,
                            patent_task,
                            github_task,
                            ct_task,
                            dns_task,
                            return_exceptions=True,
                        ),
                        timeout=60.0,
                    )
                )
            except TimeoutError:
                logger.warning(
                    "competitive_intel timeout after 60s company=%s",
                    company_clean,
                )
                sec_data = {"count": 0, "recent": []}
                patent_data = {"count": 0, "recent_titles": []}
                github_data = {
                    "repo_count": 0,
                    "total_stars": 0,
                    "languages": [],
                    "recent_repos": [],
                }
                ct_data = {"total_found": 0, "recent_subdomains": []}
                dns_data = {"records": {}, "detected_technologies": []}
            else:
                if isinstance(sec_data, BaseException):
                    sec_data = {"count": 0, "recent": []}
                if isinstance(patent_data, BaseException):
                    patent_data = {"count": 0, "recent_titles": []}
                if isinstance(github_data, BaseException):
                    github_data = {"repo_count": 0, "total_stars": 0, "languages": [], "recent_repos": []}
                if isinstance(ct_data, BaseException):
                    ct_data = {"total_found": 0, "recent_subdomains": []}
                if isinstance(dns_data, BaseException):
                    dns_data = {"records": {}, "detected_technologies": []}

        # Synthesize signals
        signals, overall_assessment = _synthesize_signals(
            sec_data, patent_data, github_data, ct_data, dns_data
        )

        result = {
            "company": company_clean,
            "domain": domain_clean,
            "github_org": github_org_clean,
            "signals": signals,
            "sec_filings": sec_data,
            "patents": patent_data,
            "github_activity": github_data,
            "new_subdomains": ct_data,
            "dns_records": dns_data,
            "overall_assessment": overall_assessment,
        }

        logger.info(
            "competitive_intel complete company=%s signals=%d",
            company_clean,
            len(signals),
        )

        return result

    return await _run()
