"""research_deception_job_scan — Analyze job postings for deception signals."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.deception_job_scanner")

# Red flag patterns for job scams
URGENCY_KEYWORDS = [
    "immediately",
    "urgently",
    "asap",
    "no experience needed",
    "no qualifications",
    "guaranteed",
    "high pay",
    "easy money",
    "minimal effort",
]

MLM_KEYWORDS = [
    "commission-based",
    "pyramid",
    "network",
    "referral",
    "downline",
    "recruit",
    "build your team",
    "unlimited income",
]

ADVANCE_FEE_KEYWORDS = [
    "upfront payment",
    "deposit",
    "fee",
    "training cost",
    "certification fee",
    "processing fee",
]

GREEN_FLAG_KEYWORDS = [
    "competitive salary",
    "benefits",
    "401k",
    "health insurance",
    "retirement",
    "vacation",
    "pto",
    "stock options",
    "transparent",
    "glassdoor",
]


def _extract_salary_range(text: str) -> tuple[int, int, bool] | None:
    """Extract salary range from text.

    Returns:
        Tuple of (min, max, is_vague) or None if not found
    """
    # Pattern for explicit ranges: $40,000 - $60,000
    range_pattern = r"\$?(\d{2,3},?\d{3}|[0-9]+)\s*(?:-|to)\s*\$?(\d{2,3},?\d{3}|[0-9]+)"
    matches = re.findall(range_pattern, text)
    if matches:
        try:
            min_val = int(matches[0][0].replace(",", ""))
            max_val = int(matches[0][1].replace(",", ""))
            if min_val > 0 and max_val > 0:
                return (min_val, max_val, False)
        except (ValueError, IndexError):
            pass

    # Pattern for "up to" or "starting at"
    single_pattern = r"(?:up to|starting at|from)?\s*\$?(\d{2,3},?\d{3}|[0-9]+)"
    single_matches = re.findall(single_pattern, text.lower())
    if single_matches:
        try:
            val = int(single_matches[0].replace(",", ""))
            if val > 0:
                return (val, val, True)
        except ValueError:
            pass

    return None


def _count_pattern_matches(text: str, patterns: list[str]) -> int:
    """Count how many patterns appear in text."""
    count = 0
    text_lower = text.lower()
    for pattern in patterns:
        if pattern.lower() in text_lower:
            count += re.findall(re.escape(pattern.lower()), text_lower).__len__()
    return count


def _estimate_domain_age(domain: str) -> int | None:
    """Estimate domain age in days via WHOIS lookup.

    Returns:
        Age in days or None if lookup fails
    """

    async def _whois_lookup() -> int | None:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=30.0,
            ) as client:
                # Use whois.arin.net simple lookup
                resp = await client.get(
                    f"https://www.whois.com/whois/{domain}",
                    timeout=10.0,
                    follow_redirects=False,
                )
                if resp.status_code == 200:
                    text = resp.text
                    # Look for "Created Date" or "registration date"
                    created_match = re.search(
                        r"created[:\s]*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE
                    )
                    if created_match:
                        try:
                            created_date = datetime.fromisoformat(
                                created_match.group(1)
                            ).replace(tzinfo=UTC)
                            age_days = (datetime.now(UTC) - created_date).days
                            return age_days
                        except (ValueError, AttributeError):
                            pass
        except Exception as exc:
            logger.debug("whois lookup failed: %s", exc)
        return None

    try:
        return asyncio.run(_whois_lookup())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_whois_lookup())
        finally:
            loop.close()


def _search_company_glassdoor(company_name: str) -> int:
    """Count Glassdoor mentions for company via search.

    Returns:
        Number of Glassdoor reviews/mentions found
    """

    async def _glassdoor_search() -> int:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=30.0,
            ) as client:
                # Search Google for "company glassdoor reviews"
                search_url = (
                    f"https://duckduckgo.com/?q={quote(company_name)}+glassdoor+"
                    f"reviews&format=json"
                )
                resp = await client.get(search_url, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    # DuckDuckGo returns results, count mentions
                    results = data.get("results", [])
                    return len(
                        [r for r in results if "glassdoor" in r.get("url", "").lower()]
                    )
        except Exception as exc:
            logger.debug("glassdoor search failed: %s", exc)
        return 0

    try:
        return asyncio.run(_glassdoor_search())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_glassdoor_search())
        finally:
            loop.close()


def research_deception_job_scan(
    job_url: str = "", job_text: str = ""
) -> dict[str, Any]:
    """Analyze job posting for deception signals.

    Checks for vague salary ranges, excessive requirements, red flags
    (urgency language, MLM patterns, advance fees), and validates company
    via WHOIS age and Glassdoor presence.

    Args:
        job_url: URL of job posting (optional, for context)
        job_text: Job posting text to analyze

    Returns:
        Dict with risk_score (0-100), red_flags list, green_flags list,
        company_age_days, and glassdoor_mentions
    """
    if not job_text:
        return {
            "error": "job_text is required",
            "risk_score": 0,
            "red_flags": [],
            "green_flags": [],
            "company_age_days": None,
            "glassdoor_mentions": 0,
        }

    if len(job_text) < 50:
        return {
            "error": "job_text must be at least 50 characters",
            "risk_score": 0,
            "red_flags": [],
            "green_flags": [],
            "company_age_days": None,
            "glassdoor_mentions": 0,
        }

    red_flags: list[str] = []
    green_flags: list[str] = []
    risk_score = 0

    # Check salary information
    salary_info = _extract_salary_range(job_text)
    if salary_info is None:
        red_flags.append("no_salary_mentioned")
        risk_score += 15
    elif salary_info[2]:  # is_vague
        red_flags.append("vague_salary_range")
        risk_score += 10
    else:
        green_flags.append("explicit_salary_range")

    # Check for urgency language
    urgency_count = _count_pattern_matches(job_text, URGENCY_KEYWORDS)
    if urgency_count >= 3:
        red_flags.append("excessive_urgency_language")
        risk_score += 20
    elif urgency_count >= 1:
        red_flags.append("some_urgency_language")
        risk_score += 5

    # Check for MLM patterns
    mlm_count = _count_pattern_matches(job_text, MLM_KEYWORDS)
    if mlm_count >= 2:
        red_flags.append("mlm_characteristics")
        risk_score += 25
    elif mlm_count >= 1:
        red_flags.append("potential_mlm_elements")
        risk_score += 10

    # Check for advance fee language
    fee_count = _count_pattern_matches(job_text, ADVANCE_FEE_KEYWORDS)
    if fee_count >= 2:
        red_flags.append("advance_fee_scam_indicators")
        risk_score += 30
    elif fee_count >= 1:
        red_flags.append("potential_fees_mentioned")
        risk_score += 10

    # Check for green flags
    green_count = _count_pattern_matches(job_text, GREEN_FLAG_KEYWORDS)
    if green_count >= 3:
        green_flags.append("comprehensive_benefits_mentioned")
        risk_score -= 10
    elif green_count >= 1:
        green_flags.append("some_benefits_mentioned")
        risk_score -= 5

    # Extract company name and check domain age
    company_match = re.search(
        r"(?:company|employer|hiring|at)[\s:]*([A-Za-z0-9\s&\-]+?)(?:\.|,|$)",
        job_text,
        re.IGNORECASE,
    )
    company_name = company_match.group(1).strip() if company_match else None
    company_age_days = None
    glassdoor_mentions = 0

    if company_name and len(company_name) > 2 and len(company_name) < 100:
        # Try to get WHOIS age
        company_age_days = _estimate_domain_age(company_name)
        if company_age_days is not None and company_age_days < 30:
            red_flags.append("brand_new_domain")
            risk_score += 15
        elif company_age_days is not None and company_age_days < 180:
            red_flags.append("recently_registered_domain")
            risk_score += 5
        elif company_age_days is not None:
            green_flags.append("established_domain")
            risk_score -= 5

        # Check Glassdoor presence
        glassdoor_mentions = _search_company_glassdoor(company_name)
        if glassdoor_mentions > 0:
            green_flags.append("verified_on_glassdoor")
            risk_score -= 10
        else:
            red_flags.append("no_glassdoor_presence")
            risk_score += 10

    # Check for requirement inflation
    requirement_match = re.findall(
        r"(\d+)\+?\s*years?\s+of\s+experience", job_text, re.IGNORECASE
    )
    if requirement_match:
        total_exp = sum(int(m) for m in requirement_match)
        if total_exp > 20:
            red_flags.append("excessive_experience_requirements")
            risk_score += 10

    # Clamp risk score to 0-100
    risk_score = max(0, min(100, risk_score))

    return {
        "risk_score": risk_score,
        "red_flags": red_flags,
        "green_flags": green_flags,
        "company_age_days": company_age_days,
        "glassdoor_mentions": glassdoor_mentions,
        "company_name": company_name,
        "job_url": job_url,
        "analysis_timestamp": datetime.now(UTC).isoformat(),
    }
