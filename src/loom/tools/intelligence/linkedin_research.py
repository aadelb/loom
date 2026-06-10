"""LinkedIn research tools — Voyager API via StaffSpy + direct HTTP fallback.

Primary: StaffSpy library wrapping LinkedIn's internal Voyager API.
Auth: session_file pickle (pre-authenticated) or email/password login.
All sync StaffSpy calls run via asyncio.to_thread() to avoid blocking.

Env vars:
  LINKEDIN_EMAIL       — LinkedIn login email
  LINKEDIN_PASSWORD    — LinkedIn login password
  LINKEDIN_SESSION_FILE — Path to StaffSpy session pickle (default: /tmp/staffspy_session.pkl)
  LINKEDIN_LI_AT       — li_at cookie value (direct Voyager fallback)
  LINKEDIN_JSESSIONID  — JSESSIONID cookie value (direct Voyager fallback)
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import re
from typing import Any

import requests

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.linkedin_research")

_SESSION_FILE = os.environ.get("LINKEDIN_SESSION_FILE", "/tmp/staffspy_session.pkl")
_LI_EMAIL = os.environ.get("LINKEDIN_EMAIL", "")
_LI_PASSWORD = os.environ.get("LINKEDIN_PASSWORD", "")
_LI_AT = os.environ.get("LINKEDIN_LI_AT", "")
_JSESSIONID = os.environ.get("LINKEDIN_JSESSIONID", "")
# Optional CAPTCHA solver key — when set, StaffSpy's browser login can clear a
# LinkedIn challenge during auto-relogin. Unset (None) = current behaviour.
_SOLVER_KEY = os.environ.get("CAPSOLVER_API_KEY", "") or os.environ.get("SOLVER_API_KEY", "")

_VOYAGER_BASE = "https://www.linkedin.com/voyager/api"
_VOYAGER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; U; Android 4.4.2; en-us; SCH-I535 Build/KOT49H) "
        "AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30"
    ),
    "X-RestLi-Protocol-Version": "2.0.0",
    "X-Li-Track": '{"clientVersion":"1.13.1665"}',
    "Accept": "application/vnd.linkedin.normalized+json+2.1",
}


def _can_relogin() -> bool:
    """True when stored email+password let us rebuild an expired session."""
    return bool(_LI_EMAIL and _LI_PASSWORD)


def _get_staffspy_account(force_relogin: bool = False):
    """Create a StaffSpy LinkedInAccount. Returns None on failure.

    Normal order: reuse the saved session pickle (fast, no browser), else log
    in with stored email/password (browser flow, writes a fresh pickle).

    force_relogin=True removes the (stale) pickle first so the email/password
    login runs and rebuilds it — the auto-relogin path for an expired li_at.
    A CAPTCHA solver key (if configured) is passed so the browser login can
    clear a LinkedIn challenge.
    """
    try:
        from staffspy import LinkedInAccount

        if force_relogin and _SESSION_FILE and os.path.exists(_SESSION_FILE):
            try:
                os.remove(_SESSION_FILE)
            except OSError as e:
                logger.warning("could not remove stale session %s: %s", _SESSION_FILE, e)

        if not force_relogin and _SESSION_FILE and os.path.exists(_SESSION_FILE):
            return LinkedInAccount(session_file=_SESSION_FILE)
        if _LI_EMAIL and _LI_PASSWORD:
            kwargs: dict[str, Any] = {
                "username": _LI_EMAIL,
                "password": _LI_PASSWORD,
                "session_file": _SESSION_FILE,
            }
            if _SOLVER_KEY:
                kwargs["solver_api_key"] = _SOLVER_KEY
            return LinkedInAccount(**kwargs)
    except Exception as e:
        logger.warning("StaffSpy login failed (force_relogin=%s): %s", force_relogin, e)
    return None


def _scrape_staff(company_name: str, search_term: str, max_results: int):
    """Run StaffSpy scrape_staff with auto-relogin on a stale session.

    An expired li_at baked into the session pickle makes StaffSpy return an
    empty frame (or raise) rather than signalling auth failure. When we used
    the pickle and email/password are configured, treat an empty/failed result
    as a stale session: delete the pickle, re-login (rebuilding it) and retry
    once. Returns the staff DataFrame or None.
    """
    used_pickle = bool(_SESSION_FILE and os.path.exists(_SESSION_FILE))
    account = _get_staffspy_account()
    staff = None
    if account is not None:
        try:
            staff = account.scrape_staff(
                company_name=company_name,
                search_term=search_term,
                max_results=max_results,
            )
        except Exception as e:
            logger.warning("StaffSpy scrape failed (pickle=%s): %s", used_pickle, e)
            staff = None

    if (staff is None or len(staff) == 0) and used_pickle and _can_relogin():
        logger.info("StaffSpy session appears stale; re-logging in with stored credentials")
        account = _get_staffspy_account(force_relogin=True)
        if account is not None:
            try:
                staff = account.scrape_staff(
                    company_name=company_name,
                    search_term=search_term,
                    max_results=max_results,
                )
            except Exception as e:
                logger.warning("StaffSpy scrape failed after relogin: %s", e)
                staff = None
    return staff


def _clean_row(row: Any) -> dict[str, Any]:
    """Convert a pandas Series row to a JSON-safe dict."""
    result = {}
    for k, v in row.items():
        if v is None or (hasattr(v, "__class__") and v.__class__.__name__ == "NAType"):
            result[k] = None
        elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            result[k] = None
        else:
            result[k] = v
    return result


def _voyager_session() -> requests.Session | None:
    """Build a raw Voyager API session from li_at cookie. Returns None if no cookie."""
    li_at = _LI_AT
    jsessionid = _JSESSIONID

    if not li_at:
        session_json = os.environ.get("LINKEDIN_SESSION_JSON", "")
        if not session_json:
            for path in [
                "/data/gcp-migration/SharedModels/linkedin_session.json",
                os.path.expanduser("~/.loom/linkedin_session.json"),
            ]:
                if os.path.exists(path):
                    session_json = path
                    break

        if session_json and os.path.exists(session_json):
            try:
                with open(session_json) as f:
                    data = json.load(f)
                cookies = {c["name"]: c["value"] for c in data.get("cookies", [])}
                li_at = cookies.get("li_at", "")
                jsessionid = cookies.get("JSESSIONID", "")
            except Exception:
                pass

    if not li_at:
        return None

    session = requests.Session()
    session.cookies.set("li_at", li_at, domain=".linkedin.com")
    if jsessionid:
        session.cookies.set("JSESSIONID", jsessionid, domain=".linkedin.com")
        csrf = jsessionid.replace('"', "")
    else:
        csrf = ""

    headers = dict(_VOYAGER_HEADERS)
    if csrf:
        headers["csrf-token"] = csrf
    session.headers.update(headers)
    return session


def _voyager_get(path: str) -> dict | None:
    """Make a GET request to the Voyager API. Returns parsed JSON or None."""
    session = _voyager_session()
    if not session:
        return None
    try:
        url = f"{_VOYAGER_BASE}/{path}" if not path.startswith("http") else path
        resp = session.get(url, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        logger.warning("Voyager %s returned %d", path, resp.status_code)
    except Exception as e:
        logger.warning("Voyager request failed: %s", e)
    return None


def _extract_profile_from_voyager(data: dict) -> dict[str, Any]:
    """Extract profile fields from Voyager profileView response."""
    profile = data.get("profile", data)
    mini = profile.get("miniProfile", {})

    first = mini.get("firstName", profile.get("firstName", ""))
    last = mini.get("lastName", profile.get("lastName", ""))
    name = f"{first} {last}".strip()

    occupation = mini.get("occupation", "")
    headline = profile.get("headline", occupation)
    location_name = profile.get("locationName", "")
    geo = profile.get("geoLocationName", location_name)
    industry = profile.get("industryName", "")
    summary = profile.get("summary", "")
    public_id = mini.get("publicIdentifier", profile.get("publicIdentifier", ""))

    pic_data = mini.get("picture", profile.get("profilePicture", {}))
    pic_url = ""
    if isinstance(pic_data, dict):
        artifacts = pic_data.get("displayImageReference", {}).get("vectorImage", {}).get("artifacts", [])
        if artifacts:
            root = pic_data.get("displayImageReference", {}).get("vectorImage", {}).get("rootUrl", "")
            pic_url = root + artifacts[-1].get("fileIdentifyingUrlPathSegment", "")

    experiences = []
    for pos in profile.get("positionView", {}).get("elements", []):
        company_name = pos.get("companyName", "")
        title = pos.get("title", "")
        time_period = pos.get("timePeriod", {})
        start = time_period.get("startDate", {})
        end = time_period.get("endDate", {})
        start_str = f"{start.get('month', '')}/{start.get('year', '')}" if start else ""
        end_str = f"{end.get('month', '')}/{end.get('year', '')}" if end else "Present"
        experiences.append({
            "company": company_name,
            "title": title,
            "start": start_str,
            "end": end_str,
        })

    education = []
    for edu in profile.get("educationView", {}).get("elements", []):
        education.append({
            "school": edu.get("schoolName", ""),
            "degree": edu.get("degreeName", ""),
            "field": edu.get("fieldOfStudy", ""),
        })

    return {
        "name": name,
        "headline": headline,
        "location": geo,
        "industry": industry,
        "about": summary,
        "profile_url": f"https://www.linkedin.com/in/{public_id}" if public_id else "",
        "profile_photo": pic_url,
        "experiences": experiences,
        "education": education,
        "public_id": public_id,
    }


def _staffspy_profile(username: str, company: str = "") -> dict[str, Any] | None:
    """Fetch profile via StaffSpy. Returns dict or None."""
    try:
        search_company = company or "linkedin"
        staff = _scrape_staff(
            company_name=search_company,
            search_term=username,
            max_results=1,
        )
        if staff is not None and len(staff) > 0:
            row = _clean_row(staff.iloc[0])
            return {
                "name": row.get("name", ""),
                "headline": row.get("position", row.get("title", "")),
                "location": row.get("location", ""),
                "about": row.get("about", ""),
                "profile_url": row.get("profile_url", row.get("linkedin_url", "")),
                "profile_photo": row.get("profile_photo", ""),
                "followers": row.get("followers", 0),
                "connections": row.get("connections", 0),
                "experiences": [],
                "education": [],
                "emails": row.get("emails", []),
                "source": "staffspy_voyager",
            }
    except Exception as e:
        logger.warning("StaffSpy profile failed: %s", e)
    return None


def _staffspy_employees(company: str, search_term: str = "", limit: int = 10) -> list[dict] | None:
    """Fetch company employees via StaffSpy."""
    try:
        staff = _scrape_staff(
            company_name=company,
            search_term=search_term,
            max_results=min(limit, 50),
        )
        if staff is not None and len(staff) > 0:
            employees = []
            for _, row in staff.iterrows():
                cleaned = _clean_row(row)
                employees.append({
                    "name": cleaned.get("name", ""),
                    "title": cleaned.get("position", cleaned.get("title", "")),
                    "location": cleaned.get("location", ""),
                    "profile_url": cleaned.get("profile_url", cleaned.get("linkedin_url", "")),
                    "emails": cleaned.get("emails", []),
                })
            return employees
    except Exception as e:
        logger.warning("StaffSpy employees failed: %s", e)
    return None


@handle_tool_errors("research_linkedin_profile")
async def research_linkedin_profile(
    username: str,
    company: str = "",
) -> dict[str, Any]:
    """Get full LinkedIn profile: experience, education, skills, emails.

    Uses LinkedIn Voyager API (internal REST API) via StaffSpy or direct
    li_at cookie authentication.

    Args:
        username: LinkedIn username (e.g. "satyanadella", "williamhgates")
        company: Company context for search (optional, improves accuracy)

    Returns:
        Dict with name, headline, location, about, experiences, education,
        profile_photo, profile_url
    """
    result = await asyncio.to_thread(_voyager_get, f"identity/profiles/{username}/profileView")
    if result:
        profile = _extract_profile_from_voyager(result)
        profile["username"] = username
        profile["source"] = "voyager_direct"
        return profile

    staffspy_result = await asyncio.to_thread(_staffspy_profile, username, company)
    if staffspy_result:
        staffspy_result["username"] = username
        return staffspy_result

    return {
        "username": username,
        "error": "LinkedIn session expired. Set LINKEDIN_LI_AT env var or refresh session file.",
        "hint": "Login to LinkedIn in a browser and export the li_at cookie, or run: ssh hetzner 'python3 -c \"from staffspy import LinkedInAccount; a = LinkedInAccount(username=..., password=...); print(a)\"'",
        "source": "none",
    }


@handle_tool_errors("research_linkedin_company")
async def research_linkedin_company(
    company_name: str,
    max_staff: int = 5,
) -> dict[str, Any]:
    """Get LinkedIn company info and top staff members.

    Args:
        company_name: LinkedIn company slug (e.g. "google", "anthropic")
        max_staff: Number of staff to return (1-25, default 5)

    Returns:
        Dict with company info and top employees
    """
    result = await asyncio.to_thread(
        _voyager_get,
        f"organization/companies?q=universalName&universalName={company_name}",
    )

    company_info: dict[str, Any] = {"company": company_name, "source": "voyager_direct"}

    if result:
        elements = result.get("elements", [])
        if elements:
            co = elements[0]
            company_info.update({
                "name": co.get("name", company_name),
                "description": co.get("description", ""),
                "industry": co.get("companyIndustries", [{}])[0].get("localizedName", "") if co.get("companyIndustries") else "",
                "website": co.get("companyPageUrl", ""),
                "employee_count": co.get("staffCount", 0),
                "headquarters": co.get("headquarter", {}).get("city", ""),
                "logo_url": "",
                "company_url": f"https://www.linkedin.com/company/{company_name}",
            })

    employees = await asyncio.to_thread(_staffspy_employees, company_name, "", min(max_staff, 25))
    if employees:
        company_info["top_staff"] = employees[:max_staff]
        company_info["staff_fetched"] = len(employees)
    elif not result:
        company_info["error"] = "LinkedIn session expired"

    return company_info


@handle_tool_errors("research_linkedin_search")
async def research_linkedin_search(
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
    if company:
        employees = await asyncio.to_thread(_staffspy_employees, company, query, min(limit, 25))
        if employees:
            return {
                "query": query,
                "company": company,
                "source": "staffspy_voyager",
                "results": employees,
                "count": len(employees),
            }

    keywords_encoded = requests.utils.quote(query)
    search_url = (
        f"graphql?variables=(start:0,query:(flagshipSearchIntent:SEARCH_SRP,"
        f"queryParameters:List((key:keywords,value:List({keywords_encoded})),(key:resultType,value:List(PEOPLE))),"
        f"includeFiltersInResponse:false),count:{min(limit, 25)})"
        f"&queryId=voyagerSearchDashClusters.66adc6056cf4138949ca5dcb31bb1749"
    )
    result = await asyncio.to_thread(_voyager_get, search_url)
    if result:
        people = []
        for element in result.get("included", []):
            if element.get("$type", "").endswith("MiniProfile") or "firstName" in element:
                first = element.get("firstName", "")
                last = element.get("lastName", "")
                people.append({
                    "name": f"{first} {last}".strip(),
                    "headline": element.get("occupation", ""),
                    "location": element.get("locationName", ""),
                    "profile_url": f"https://www.linkedin.com/in/{element.get('publicIdentifier', '')}",
                })
        if people:
            return {
                "query": query,
                "company": company,
                "source": "voyager_direct",
                "results": people[:limit],
                "count": len(people),
            }

    return {
        "query": query,
        "company": company,
        "source": "none",
        "results": [],
        "count": 0,
        "error": "LinkedIn session expired or no results",
    }


@handle_tool_errors("research_linkedin_jobs")
async def research_linkedin_jobs(
    query: str,
    location: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Search LinkedIn job listings.

    Uses JobSpy library as primary engine with Voyager API fallback.

    Args:
        query: Job title or keywords
        location: Location filter
        limit: Max results (1-100, default 10)

    Returns:
        Dict with job listings: title, company, location, link, date
    """
    try:
        from jobspy import scrape_jobs

        jobs_df = await asyncio.to_thread(
            scrape_jobs,
            site_name=["linkedin"],
            search_term=query,
            location=location or "United States",
            results_wanted=min(limit, 100),
            hours_old=72,
        )
        if jobs_df is not None and len(jobs_df) > 0:
            jobs = []
            for _, row in jobs_df.iterrows():
                cleaned = _clean_row(row)
                jobs.append({
                    "title": cleaned.get("title", ""),
                    "company": cleaned.get("company_name", cleaned.get("company", "")),
                    "location": cleaned.get("location", ""),
                    "link": cleaned.get("job_url", ""),
                    "date_posted": str(cleaned.get("date_posted", "")),
                    "description": str(cleaned.get("description", ""))[:300],
                })
            return {
                "query": query,
                "location": location,
                "source": "jobspy_linkedin",
                "jobs": jobs,
                "count": len(jobs),
            }
    except ImportError:
        logger.info("jobspy not installed, trying Voyager API")
    except Exception as e:
        logger.warning("JobSpy failed: %s", e)

    keywords_encoded = requests.utils.quote(query)
    loc_encoded = requests.utils.quote(location) if location else ""
    job_url = (
        f"graphql?variables=(start:0,query:(flagshipSearchIntent:SEARCH_SRP,"
        f"queryParameters:List((key:keywords,value:List({keywords_encoded}))"
        f"{f',(key:locationUnion,value:List({loc_encoded}))' if loc_encoded else ''},"
        f"(key:resultType,value:List(JOBS))),"
        f"includeFiltersInResponse:false),count:{min(limit, 25)})"
        f"&queryId=voyagerSearchDashClusters.66adc6056cf4138949ca5dcb31bb1749"
    )
    result = await asyncio.to_thread(_voyager_get, job_url)
    if result:
        jobs = []
        for element in result.get("included", []):
            title = element.get("title", "")
            if title and element.get("$type", "").endswith(("JobPosting", "JobResult")):
                jobs.append({
                    "title": title,
                    "company": element.get("companyName", ""),
                    "location": element.get("formattedLocation", ""),
                    "link": element.get("jobPostingUrl", ""),
                })
        if jobs:
            return {
                "query": query,
                "location": location,
                "source": "voyager_direct",
                "jobs": jobs[:limit],
                "count": len(jobs),
            }

    return {
        "query": query,
        "location": location,
        "source": "none",
        "jobs": [],
        "count": 0,
        "error": "No jobs found or session expired. Install jobspy for better results: pip install python-jobspy",
    }


@handle_tool_errors("research_linkedin_employees")
async def research_linkedin_employees(
    company: str,
    search_term: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Find employees of a company with detailed profiles.

    Uses StaffSpy (Voyager API) to scrape employee data.

    Args:
        company: Company name/slug (e.g. "google", "anthropic")
        search_term: Filter by role/name (optional)
        limit: Max employees (1-50, default 10)

    Returns:
        Dict with employees: name, title, location, profile link, emails
    """
    employees = await asyncio.to_thread(
        _staffspy_employees, company, search_term, min(limit, 50)
    )
    if employees:
        return {
            "company": company,
            "search_term": search_term,
            "source": "staffspy_voyager",
            "employees": employees,
            "count": len(employees),
        }

    return {
        "company": company,
        "search_term": search_term,
        "source": "none",
        "employees": [],
        "count": 0,
        "error": "StaffSpy login failed. Refresh LinkedIn session or set LINKEDIN_LI_AT.",
    }


@handle_tool_errors("research_linkedin_posts")
async def research_linkedin_posts(
    username: str = "",
    company: str = "",
    limit: int = 10,
) -> dict[str, Any]:
    """Get LinkedIn activity for a person or company.

    Note: Full post content requires LinkedIn's UGC API with OAuth.
    This tool returns profile activity metadata via the Voyager API.

    Args:
        username: LinkedIn username
        company: Company slug
        limit: Max items

    Returns:
        Dict with profile/company activity overview
    """
    target = username or company
    if not target:
        return {"error": "Provide either username or company"}

    if username:
        profile = await research_linkedin_profile(username=username)
        profile["note"] = "Full post feed requires LinkedIn UGC API with OAuth"
        return profile

    company_data = await research_linkedin_company(company_name=company, max_staff=0)
    company_data["note"] = "Full post feed requires LinkedIn UGC API with OAuth"
    return company_data
