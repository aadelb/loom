"""LinkedIn OSINT intelligence — public profile discovery and company research."""

from __future__ import annotations
from loom.error_responses import handle_tool_errors

import logging
import re
from typing import Any

import httpx
from loom.http_helpers import fetch_text

logger = logging.getLogger("loom.tools.linkedin_osint")

_HTTP_TIMEOUT = 15.0
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _validate_person_name(person: str) -> bool:
    """Validate person name for LinkedIn search.

    Args:
        person: Person name to validate

    Returns:
        True if valid, False otherwise.
    """
    if not person or len(person) < 1 or len(person) > 255:
        return False
    # Allow letters, spaces, hyphens, apostrophes
    return bool(re.match(r"^[a-zA-Z\s\-']+$", person))


def _validate_company_name(company: str) -> bool:
    """Validate company name for LinkedIn search.

    Args:
        company: Company name to validate

    Returns:
        True if valid, False otherwise.
    """
    if not company or len(company) < 1 or len(company) > 255:
        return False
    # Allow alphanumeric, spaces, hyphens, dots
    return bool(re.match(r"^[a-zA-Z0-9\s\-\.&]+$", company))


def _extract_profile_info(html: str) -> dict[str, Any]:
    """Extract profile information from LinkedIn public profile page.

    Args:
        html: HTML content from LinkedIn profile

    Returns:
        Dict with name, headline, location, summary.
    """
    info: dict[str, Any] = {}

    # Extract name (usually in <h1> or title)
    name_patterns = [
        r"<h1[^>]*class=\"[^\"]*name[^\"]*\">([^<]+)</h1>",
        r"<title>([^|]+)\|",
    ]

    for pattern in name_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            info["name"] = match.group(1).strip()
            break

    # Extract headline (job title/current role)
    headline_patterns = [
        r"<h2[^>]*class=\"[^\"]*headline[^\"]*\">([^<]+)</h2>",
        r"<p[^>]*class=\"[^\"]*headline[^\"]*\">([^<]+)</p>",
    ]

    for pattern in headline_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            info["headline"] = match.group(1).strip()
            break

    # Extract location
    location_patterns = [
        r"<span[^>]*class=\"[^\"]*location[^\"]*\">([^<]+)</span>",
    ]

    for pattern in location_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            info["location"] = match.group(1).strip()
            break

    # Extract summary/about
    summary_patterns = [
        r"<section[^>]*class=\"[^\"]*about[^\"]*\">([^<]*)<",
        r"<p[^>]*class=\"[^\"]*summary[^\"]*\">([^<]+)</p>",
    ]

    for pattern in summary_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            info["summary"] = match.group(1).strip()[:300]
            break

    return info


def _extract_company_info(html: str) -> dict[str, Any]:
    """Extract company information from LinkedIn company page.

    Args:
        html: HTML content from LinkedIn company page

    Returns:
        Dict with company name, industry, size, location.
    """
    info: dict[str, Any] = {}

    # Extract company name
    name_patterns = [
        r"<h1[^>]*class=\"[^\"]*company-name[^\"]*\">([^<]+)</h1>",
        r"<title>([^|]+)\s*\|",
    ]

    for pattern in name_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            info["name"] = match.group(1).strip()
            break

    # Extract industry
    industry_patterns = [
        r"<span[^>]*class=\"[^\"]*industry[^\"]*\">([^<]+)</span>",
    ]

    for pattern in industry_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            info["industry"] = match.group(1).strip()
            break

    # Extract employee count
    size_patterns = [
        r"([0-9,]+)\s+employees?",
        r"(\d+[KM]?)\s+on LinkedIn",
    ]

    for pattern in size_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            try:
                size_str = match.group(1).replace(",", "")
                if size_str.endswith("K"):
                    info["employee_count"] = int(float(size_str[:-1]) * 1000)
                elif size_str.endswith("M"):
                    info["employee_count"] = int(float(size_str[:-1]) * 1_000_000)
                else:
                    info["employee_count"] = int(float(size_str))
            except (ValueError, AttributeError):
                pass
            break

    # Extract location
    location_patterns = [
        r"<span[^>]*class=\"[^\"]*location[^\"]*\">([^<]+)</span>",
    ]

    for pattern in location_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            info["location"] = match.group(1).strip()
            break

    # Extract description/about
    about_patterns = [
        r"<p[^>]*class=\"[^\"]*about[^\"]*\">([^<]+)</p>",
    ]

    for pattern in about_patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            info["description"] = match.group(1).strip()[:300]
            break

    return info


@handle_tool_errors("research_linkedin_intel")
async def research_linkedin_intel(
    company: str = "",
    person: str = "",
    query: str = "",
) -> dict[str, Any]:
    """Gather OSINT intelligence on LinkedIn public profiles and companies.

    Utilizes Google dorking and public LinkedIn pages to extract profile
    information without requiring API access or authentication.
    Does NOT require API keys and only accesses publicly available information.

    Args:
        company: Specific company name to investigate
        person: Specific person name to investigate
        query: Free-form search query (future enhancement)

    Returns:
        Dict with profiles_found, company_info, employees, skills.
    """
    # Validate inputs
    if person and not _validate_person_name(person):
        return {
            "status": "error",
            "error": "invalid person name: letters, spaces, hyphens, apostrophes only",
            "person": person,
            "profiles_found": [],
        }

    if company and not _validate_company_name(company):
        return {
            "status": "error",
            "error": "invalid company name",
            "company": company,
            "company_info": {},
            "employees": [],
        }

    if not company and not person and not query:
        return {
            "status": "error",
            "error": "provide either company, person, or query",
            "profiles_found": [],
            "company_info": {},
        }

    result: dict[str, Any] = {
        "status": "success",
        "company": company,
        "person": person,
        "query": query,
        "profiles_found": [],
        "company_info": {},
        "employees": [],
        "skills": [],
    }

    # Investigate company
    if company:
        url = f"https://www.linkedin.com/company/{company.lower().replace(' ', '-')}"
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
                html = await fetch_text(client, url, headers={"User-Agent": _USER_AGENT})
                if html:
                    company_info = _extract_company_info(html)
                    result["company_info"] = company_info

                    logger.info(
                        "linkedin_intel company=%s industry=%s",
                        company,
                        company_info.get("industry"),
                    )

        except httpx.TimeoutException:
            result["errors"] = result.get("errors", []) + [f"company lookup timeout: {company}"]
            logger.warning("linkedin_intel timeout company=%s", company)
        except Exception as e:
            result["errors"] = result.get("errors", []) + [f"company lookup failed: {e}"]
            logger.error("linkedin_intel error company=%s error=%s", company, e)

    # Investigate person
    if person:
        # Try direct profile URL
        person_slug = person.lower().replace(" ", "-")
        url = f"https://www.linkedin.com/in/{person_slug}"

        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
                html = await fetch_text(client, url, headers={"User-Agent": _USER_AGENT})
                if html:
                    profile_info = _extract_profile_info(html)
                    profile_info["url"] = url

                    result["profiles_found"].append(profile_info)

                    logger.info(
                        "linkedin_intel person=%s headline=%s",
                        person,
                        profile_info.get("headline"),
                    )

        except httpx.TimeoutException:
            result["errors"] = result.get("errors", []) + [f"person lookup timeout: {person}"]
        except Exception as e:
            result["errors"] = result.get("errors", []) + [f"person lookup failed: {e}"]
            logger.error("linkedin_intel error person=%s error=%s", person, e)

    has_data = bool(result.get("company_info")) or bool(result.get("profiles_found"))
    has_errors = bool(result.get("errors"))
    if has_errors and not has_data:
        result["status"] = "error"
    elif has_errors and has_data:
        result["status"] = "partial"

    return result
