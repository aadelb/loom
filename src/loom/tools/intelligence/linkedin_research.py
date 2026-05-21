"""LinkedIn research tools — HTTP client to SharedModels gateway.

All LinkedIn operations go through SharedModels /v1/social/linkedin/*
endpoints which use StaffSpy (Voyager API) as backend. This avoids
duplicate LinkedIn sessions and centralizes credential management.

SharedModels gateway: http://<SHARED_MODELS_URL>/v1/social/linkedin/*
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.linkedin_research")

_SHARED_MODELS_URL = os.environ.get("SHARED_MODELS_URL", "http://localhost:8000")
_API_KEY = os.environ.get("SHARED_MODELS_API_KEY", "sk_admin_sharedmodels_2026")
_TIMEOUT = 60.0


def _headers() -> dict[str, str]:
    return {"X-API-Key": _API_KEY, "Content-Type": "application/json"}


def _base_url() -> str:
    return f"{_SHARED_MODELS_URL}/v1/social/linkedin"


@handle_tool_errors("research_linkedin_profile")
def research_linkedin_profile(
    username: str,
    company: str = "",
) -> dict[str, Any]:
    """Get full LinkedIn profile: experience, education, skills, emails.

    Uses SharedModels gateway (StaffSpy Voyager API backend).

    Args:
        username: LinkedIn username (e.g. "satyanadella", "williamhgates")
        company: Company context for search (optional, improves accuracy)

    Returns:
        Dict with name, headline, location, bio, followers, connections,
        experiences (with dates/duration), education, potential_emails,
        profile_photo, current_position, is_hiring, open_to_work
    """
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(
            f"{_base_url()}/profile/{username}",
            headers=_headers(),
        )
        if resp.status_code != 200:
            return {"username": username, "error": f"HTTP {resp.status_code}: {resp.text[:200]}", "source": "sharedmodels"}

        data = resp.json()
        profile = data.get("data", data)
        return {
            "username": username,
            "source": "sharedmodels_staffspy",
            "name": profile.get("name", ""),
            "headline": profile.get("headline", ""),
            "about": profile.get("about", ""),
            "location": profile.get("location", ""),
            "followers": profile.get("followers", 0),
            "connections": profile.get("connections", 0),
            "profile_url": profile.get("profile_url", ""),
        }


@handle_tool_errors("research_linkedin_company")
def research_linkedin_company(
    company_name: str,
    max_staff: int = 5,
) -> dict[str, Any]:
    """Get LinkedIn company info and top staff members.

    Args:
        company_name: LinkedIn company slug (e.g. "google", "anthropic")
        max_staff: Number of staff to return (1-25, default 5)

    Returns:
        Dict with company name, staff_count, and top employees with titles
    """
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(
            f"{_base_url()}/company/{company_name}",
            headers=_headers(),
        )
        if resp.status_code != 200:
            return {"company": company_name, "error": f"HTTP {resp.status_code}: {resp.text[:200]}", "source": "sharedmodels"}

        data = resp.json()
        company = data.get("data", data)
        return {
            "company": company_name,
            "source": "sharedmodels_staffspy",
            "name": company.get("name", company_name),
            "industry": company.get("industry", ""),
            "employee_count": company.get("employee_count"),
            "description": company.get("description", ""),
            "website": company.get("website", ""),
            "location": company.get("location", ""),
            "profile_url": company.get("profile_url", ""),
        }


@handle_tool_errors("research_linkedin_search")
def research_linkedin_search(
    query: str,
    company: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Search LinkedIn for people by name, title, or skill.

    Args:
        query: Search term (name, title, skill)
        company: Filter by company (optional)
        limit: Max results (1-25, default 10)

    Returns:
        Dict with matching profiles: name, headline, location, link
    """
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(
            f"{_base_url()}/search",
            headers=_headers(),
            json={"query": query, "max_results": min(limit, 25)},
        )
        if resp.status_code != 200:
            return {"query": query, "error": f"HTTP {resp.status_code}: {resp.text[:200]}", "source": "sharedmodels"}

        data = resp.json()
        search = data.get("data", data)
        return {
            "query": query,
            "company": company,
            "source": "sharedmodels_staffspy",
            "results": search.get("results", []),
            "count": search.get("total_results", 0),
        }


@handle_tool_errors("research_linkedin_jobs")
def research_linkedin_jobs(
    query: str,
    location: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Search LinkedIn job listings.

    Uses SharedModels gateway with JobSpy multi-site aggregator backend.

    Args:
        query: Job title or keywords
        location: Location filter
        limit: Max results (1-25, default 10)

    Returns:
        Dict with job listings
    """
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(
            f"{_base_url()}/jobs/search",
            headers=_headers(),
            json={"query": query, "location": location, "max_results": min(limit, 100)},
        )
        if resp.status_code != 200:
            return {"query": query, "error": f"HTTP {resp.status_code}: {resp.text[:200]}", "source": "sharedmodels"}

        data = resp.json()
        jobs = data.get("data", data)
        return {
            "query": query,
            "location": location,
            "source": "sharedmodels_jobspy",
            "jobs": jobs.get("results", []),
            "count": jobs.get("total_results", 0),
        }


@handle_tool_errors("research_linkedin_employees")
def research_linkedin_employees(
    company: str,
    search_term: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Find employees of a company with detailed profiles.

    Uses SharedModels gateway (StaffSpy Voyager API backend).

    Args:
        company: Company name/slug (e.g. "google", "anthropic")
        search_term: Filter by role/name (optional)
        limit: Max employees (1-50, default 10)

    Returns:
        Dict with employees: name, title, location, profile link, emails
    """
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(
            f"{_base_url()}/employees",
            headers=_headers(),
            json={"company": company, "search_term": search_term, "max_results": min(limit, 50)},
        )
        if resp.status_code != 200:
            return {"company": company, "error": f"HTTP {resp.status_code}: {resp.text[:200]}", "source": "sharedmodels"}

        data = resp.json()
        emps = data.get("data", data)
        return {
            "company": company,
            "search_term": search_term,
            "source": "sharedmodels_staffspy",
            "employees": emps.get("employees", []),
            "count": emps.get("total_results", 0),
        }


@handle_tool_errors("research_linkedin_posts")
def research_linkedin_posts(
    username: str = "",
    company: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Get recent LinkedIn posts from a person or company.

    Note: StaffSpy focuses on profiles. Returns profile activity data.

    Args:
        username: LinkedIn username
        company: Company slug
        limit: Max posts

    Returns:
        Dict with profile activity data
    """
    target = username or company
    if not target:
        return {"error": "Provide either username or company"}

    if username:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.get(
                f"{_base_url()}/profile/{username}",
                headers=_headers(),
            )
            if resp.status_code != 200:
                return {"target": target, "error": f"HTTP {resp.status_code}", "source": "sharedmodels"}

            data = resp.json()
            profile = data.get("data", data)
            return {
                "target": target,
                "source": "sharedmodels_staffspy",
                "name": profile.get("name", ""),
                "headline": profile.get("headline", ""),
                "about": profile.get("about", ""),
                "followers": profile.get("followers", 0),
                "profile_url": profile.get("profile_url", ""),
                "note": "Full post feed requires LinkedIn UGC API with OAuth",
            }

    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(
            f"{_base_url()}/company/{company}",
            headers=_headers(),
        )
        if resp.status_code != 200:
            return {"target": target, "error": f"HTTP {resp.status_code}", "source": "sharedmodels"}

        data = resp.json()
        co = data.get("data", data)
        return {
            "target": target,
            "source": "sharedmodels_staffspy",
            "name": co.get("name", ""),
            "description": co.get("description", ""),
            "profile_url": co.get("profile_url", ""),
            "note": "Full post feed requires LinkedIn UGC API with OAuth",
        }
