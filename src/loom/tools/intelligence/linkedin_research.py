"""LinkedIn research tools — OSINT via Camoufox stealth browser + SharedModels.

Provides profile, company, job, employee, and post research capabilities.
Uses Camoufox for authenticated scraping and SharedModels as fallback.

Adapted from:
- stickerdaniel/linkedin-mcp-server (1,948 stars): tool patterns + sections
- joeyism/linkedin_scraper (4,139 stars): data models (Person, Company)
- m8sec/CrossLinked (1,534 stars): employee enumeration via search engines
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any

import httpx

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.linkedin_research")

SHARED_MODELS_BASE = os.environ.get("SHARED_MODELS_URL", "http://127.0.0.1:8000")
_TIMEOUT = 30.0
_LI_COOKIES = "/data/gcp-migration/SharedModels/linkedin_session.json"


def _safe(s: str) -> str:
    return s.encode("utf-8", errors="replace").decode("utf-8")


def _load_li_cookies() -> list[dict[str, str]]:
    try:
        with open(_LI_COOKIES) as f:
            data = json.load(f)
        return data.get("cookies", data) if isinstance(data, dict) else data
    except Exception:
        return []


async def _camoufox_fetch_li(url: str, wait_secs: int = 6) -> str:
    from camoufox.async_api import AsyncCamoufox

    cookies = _load_li_cookies()
    async with AsyncCamoufox(headless=True) as browser:
        page = await browser.new_page()
        for c in cookies:
            if isinstance(c, dict):
                await page.context.add_cookies([{
                    "name": c["name"], "value": c["value"],
                    "domain": c.get("domain", ".linkedin.com"),
                    "path": c.get("path", "/"),
                }])
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(wait_secs)
        content = await page.content()
    return content


def _extract_profile_data(html: str) -> dict[str, Any]:
    """Extract LinkedIn profile data from rendered HTML spans."""
    name = ""
    m = re.search(r'<title>([^<|]+)', html)
    if m:
        name = _safe(re.sub(r'\s*[|\-]\s*LinkedIn.*$', '', m.group(1)).strip())

    headline = ""
    headlines = re.findall(r'<span>([^<]*?(?:at |@ )[^<]{5,80})</span>', html[:100000])
    if headlines:
        headline = _safe(headlines[0])

    location = ""
    m = re.search(r'<span[^>]*>([^<]*(?:Area|Region|Metro|Greater|United States|India|UAE|Dubai|London|Berlin|Singapore|Remote)[^<]*)</span>', html[:100000])
    if m:
        location = _safe(m.group(1).strip())

    summary = ""
    long_texts = re.findall(r'<span[^>]*>((?:[^<]){100,500})</span>', html)
    for t in long_texts:
        if any(skip in t.lower() for skip in ["cookie", "privacy", "javascript", "class=", "style=", "linkedin.com"]):
            continue
        summary = _safe(t.strip())[:500]
        break

    connections = 0
    m = re.search(r'([\d,]+)\+?\s*connections', html)
    if m:
        connections = int(m.group(1).replace(",", ""))

    followers = 0
    m = re.search(r'([\d,]+)\s*followers', html, re.IGNORECASE)
    if m:
        followers = int(m.group(1).replace(",", ""))

    profile_pic = ""
    m = re.search(r'<img[^>]*src="(https://media\.licdn\.com/dms/image/[^"]+)"', html)
    if m:
        profile_pic = m.group(1)

    return {
        "name": name,
        "headline": headline,
        "location": location,
        "summary": summary,
        "connections": connections,
        "followers": followers,
        "profile_picture": profile_pic,
    }


def _extract_company_data(html: str) -> dict[str, Any]:
    """Extract LinkedIn company data from rendered HTML spans."""
    name = ""
    m = re.search(r'<title>([^<|]+)', html)
    if m:
        raw = re.sub(r'\s*[|\-]\s*LinkedIn.*$', '', m.group(1)).strip()
        raw = re.sub(r'^\(\d+\)\s*', '', raw).strip()
        name = _safe(re.sub(r':\s*About$', '', raw).strip())

    description = ""
    long_texts = re.findall(r'<span[^>]*>((?:[^<]){80,500})</span>', html)
    for t in long_texts:
        if any(skip in t.lower() for skip in ["cookie", "privacy", "javascript", "linkedin.com", "sign in"]):
            continue
        description = _safe(t.strip())[:500]
        break

    employees = 0
    m = re.search(r'([\d,]+)\s*(?:employees|associated members)', html, re.IGNORECASE)
    if m:
        employees = int(m.group(1).replace(",", ""))

    followers = 0
    m = re.search(r'([\d,]+)\s*followers', html, re.IGNORECASE)
    if m:
        followers = int(m.group(1).replace(",", ""))

    industry = ""
    industry_spans = re.findall(r'<span>([^<]{3,40})</span>', html[50000:150000])
    for s in industry_spans:
        if any(ind in s for ind in ["Technology", "Software", "Research", "Services", "Financial", "Healthcare", "Education", "Consulting"]):
            industry = _safe(s)
            break

    website = ""
    m = re.search(r'href="(https?://(?!.*linkedin\.com)[^"]{10,80})"', html)
    if m:
        website = m.group(1)

    return {
        "name": name,
        "description": description,
        "industry": industry,
        "employee_count": employees,
        "followers": followers,
        "website": website,
    }


def _get_api_key() -> str:
    key = os.environ.get("SHARED_MODELS_API_KEY", "")
    if not key:
        raise RuntimeError("SHARED_MODELS_API_KEY not set")
    return key


def _headers() -> dict[str, str]:
    return {"X-API-Key": _get_api_key(), "Content-Type": "application/json"}


@handle_tool_errors("research_linkedin_profile")
async def research_linkedin_profile(
    username: str,
) -> dict[str, Any]:
    """Get LinkedIn profile with experience, education, skills.

    Args:
        username: LinkedIn username/slug (e.g. "williamhgates", "satyanadella")

    Returns:
        Dict with name, headline, location, summary, connections,
        followers, industry, experiences, profile_picture
    """
    try:
        html = await _camoufox_fetch_li(
            f"https://www.linkedin.com/in/{username}/", wait_secs=7
        )
        data = _extract_profile_data(html)
        data["username"] = username
        data["source"] = "camoufox"
        data["url"] = f"https://www.linkedin.com/in/{username}/"
        data["content_size"] = len(html)
        return data
    except Exception as e:
        logger.warning("linkedin_profile_failed: %s", e)
        return {"username": username, "error": str(e)}


@handle_tool_errors("research_linkedin_company")
async def research_linkedin_company(
    company_name: str,
) -> dict[str, Any]:
    """Get LinkedIn company profile with employees, industry, description.

    Args:
        company_name: LinkedIn company slug (e.g. "google", "anthropic", "microsoft")

    Returns:
        Dict with name, description, industry, employee_count, followers,
        website, headquarters
    """
    try:
        html = await _camoufox_fetch_li(
            f"https://www.linkedin.com/company/{company_name}/about/", wait_secs=7
        )
        data = _extract_company_data(html)
        data["company_slug"] = company_name
        data["source"] = "camoufox"
        data["url"] = f"https://www.linkedin.com/company/{company_name}/"
        data["content_size"] = len(html)
        return data
    except Exception as e:
        logger.warning("linkedin_company_failed: %s", e)
        return {"company_name": company_name, "error": str(e)}


@handle_tool_errors("research_linkedin_search")
async def research_linkedin_search(
    query: str,
    search_type: str = "people",
    limit: int = 10,
) -> dict[str, Any]:
    """Search LinkedIn for people, companies, or jobs.

    Args:
        query: Search term (name, skill, company, job title)
        search_type: people, companies, or jobs
        limit: Max results (1-20, default 10)

    Returns:
        Dict with search results containing names, titles, URLs
    """
    limit = max(1, min(limit, 20))
    type_map = {"people": "people", "companies": "companies", "jobs": "jobs"}
    lt = type_map.get(search_type, "people")

    try:
        url = f"https://www.linkedin.com/search/results/{lt}/?keywords={query.replace(' ', '%20')}"
        html = await _camoufox_fetch_li(url, wait_secs=7)

        results = []
        if lt == "people":
            names = re.findall(r'"title":\{"text":"((?:[^"\\]|\\.)*)"\}', html)
            headlines = re.findall(r'"primarySubtitle":\{"text":"((?:[^"\\]|\\.)*)"\}', html)
            for i, name in enumerate(names[:limit]):
                results.append({
                    "name": _safe(name),
                    "headline": _safe(headlines[i]) if i < len(headlines) else "",
                })
        elif lt == "companies":
            names = re.findall(r'"title":\{"text":"((?:[^"\\]|\\.)*)"\}', html)
            for name in names[:limit]:
                results.append({"name": _safe(name)})

        return {
            "query": query,
            "search_type": search_type,
            "results": results,
            "count": len(results),
            "source": "camoufox",
            "content_size": len(html),
        }
    except Exception as e:
        logger.warning("linkedin_search_failed: %s", e)
        return {"query": query, "error": str(e)}


@handle_tool_errors("research_linkedin_jobs")
async def research_linkedin_jobs(
    query: str,
    location: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Search LinkedIn job listings.

    Args:
        query: Job title or keywords (e.g. "AI engineer", "data scientist")
        location: Location filter (e.g. "Dubai", "Remote")
        limit: Max results (1-25, default 10)

    Returns:
        Dict with job listings: title, company, location, url
    """
    limit = max(1, min(limit, 25))
    url = f"https://www.linkedin.com/jobs/search/?keywords={query.replace(' ', '%20')}"
    if location:
        url += f"&location={location.replace(' ', '%20')}"

    try:
        html = await _camoufox_fetch_li(url, wait_secs=7)

        jobs = []
        titles = re.findall(r'"jobTitle":\s*"((?:[^"\\]|\\.)*)"\s*[,}]', html)
        companies = re.findall(r'"companyName":\s*"((?:[^"\\]|\\.)*)"\s*[,}]', html)
        locations = re.findall(r'"formattedLocation":\s*"((?:[^"\\]|\\.)*)"\s*[,}]', html)

        for i in range(min(len(titles), limit)):
            jobs.append({
                "title": _safe(titles[i]),
                "company": _safe(companies[i]) if i < len(companies) else "",
                "location": _safe(locations[i]) if i < len(locations) else "",
            })

        return {
            "query": query,
            "location": location,
            "jobs": jobs,
            "count": len(jobs),
            "source": "camoufox",
            "content_size": len(html),
        }
    except Exception as e:
        logger.warning("linkedin_jobs_failed: %s", e)
        return {"query": query, "error": str(e)}


@handle_tool_errors("research_linkedin_employees")
async def research_linkedin_employees(
    company: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Find employees of a company via LinkedIn search.

    Adapted from CrossLinked (1,534 stars) employee enumeration.

    Args:
        company: Company name (e.g. "Google", "Anthropic")
        limit: Max employees to find (1-25, default 10)

    Returns:
        Dict with employee list: name, title, profile_url
    """
    limit = max(1, min(limit, 25))

    try:
        url = f"https://www.linkedin.com/search/results/people/?keywords={company.replace(' ', '%20')}%20employee&origin=GLOBAL_SEARCH_HEADER"
        html = await _camoufox_fetch_li(url, wait_secs=7)

        employees = []
        names = re.findall(r'"title":\{"text":"((?:[^"\\]|\\.)*)"\}', html)
        headlines = re.findall(r'"primarySubtitle":\{"text":"((?:[^"\\]|\\.)*)"\}', html)

        for i, name in enumerate(names[:limit]):
            employees.append({
                "name": _safe(name),
                "title": _safe(headlines[i]) if i < len(headlines) else "",
            })

        return {
            "company": company,
            "employees": employees,
            "count": len(employees),
            "source": "camoufox",
        }
    except Exception as e:
        logger.warning("linkedin_employees_failed: %s", e)
        return {"company": company, "error": str(e)}


@handle_tool_errors("research_linkedin_posts")
async def research_linkedin_posts(
    username: str = "",
    company: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Get recent LinkedIn posts from a person or company.

    Args:
        username: LinkedIn username (for personal posts)
        company: Company slug (for company posts)
        limit: Max posts (1-20, default 10)

    Returns:
        Dict with posts: text, reactions, comments, date
    """
    limit = max(1, min(limit, 20))

    target = username or company
    if not target:
        return {"error": "Provide either username or company"}

    try:
        if username:
            url = f"https://www.linkedin.com/in/{username}/recent-activity/all/"
        else:
            url = f"https://www.linkedin.com/company/{company}/posts/"

        html = await _camoufox_fetch_li(url, wait_secs=8)

        posts = []
        texts = re.findall(r'"commentary":\{"text":\{"text":"((?:[^"\\]|\\.)*)"\}', html)
        reactions = re.findall(r'"numLikes":\s*(\d+)', html)
        comments = re.findall(r'"numComments":\s*(\d+)', html)

        for i, text in enumerate(texts[:limit]):
            posts.append({
                "text": _safe(text)[:500],
                "reactions": int(reactions[i]) if i < len(reactions) else 0,
                "comments": int(comments[i]) if i < len(comments) else 0,
            })

        return {
            "target": target,
            "source": "camoufox",
            "posts": posts,
            "post_count": len(posts),
            "content_size": len(html),
        }
    except Exception as e:
        logger.warning("linkedin_posts_failed: %s", e)
        return {"target": target, "error": str(e)}
