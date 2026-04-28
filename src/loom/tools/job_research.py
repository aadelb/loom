"""Job market research tools for employment intelligence.

Tools:
- research_job_search: Search job listings across multiple free sources
- research_job_market: Aggregate job market intelligence for a role
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections import Counter
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.job_research")

_DEFAULT_TIMEOUT = 30.0


def _get_http_client() -> httpx.AsyncClient:
    """Return a shared async httpx client."""
    return httpx.AsyncClient(
        timeout=_DEFAULT_TIMEOUT,
        follow_redirects=True,
        limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
    )


async def _search_adzuna(
    query: str,
    location: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search Adzuna API for job listings.

    Requires ADZUNA_APP_ID and ADZUNA_APP_KEY environment variables.
    """
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        logger.debug("adzuna_skipped: missing API credentials")
        return []

    results: list[dict[str, Any]] = []
    try:
        async with _get_http_client() as client:
            # Adzuna uses country codes in URL; default to GB
            country = "gb"

            params: dict[str, str | int] = {
                "app_id": app_id,
                "app_key": app_key,
                "what": query,
                "results_per_page": limit,
            }
            if location:
                params["where"] = location

            url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"

            logger.debug("adzuna_fetch query=%s location=%s", query[:50], location)

            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            for job in data.get("results", []):
                salary_min = job.get("salary_min")
                salary_max = job.get("salary_max")

                salary_str = None
                if salary_min and salary_max:
                    salary_str = f"£{salary_min:,} - £{salary_max:,}"
                elif salary_min:
                    salary_str = f"£{salary_min:,}+"
                elif salary_max:
                    salary_str = f"up to £{salary_max:,}"

                results.append(
                    {
                        "title": job.get("title", ""),
                        "company": job.get("company", {}).get("display_name", ""),
                        "location": job.get("location", {}).get("display_name", location or ""),
                        "url": job.get("redirect_url", ""),
                        "salary": salary_str,
                        "remote": False,  # Adzuna doesn't provide remote flag
                        "source": "adzuna",
                        "date_posted": job.get("created", None),
                    }
                )

        logger.info("adzuna_success count=%d", len(results))

    except httpx.HTTPStatusError as e:
        logger.warning("adzuna_api_error status=%d", e.response.status_code)
    except Exception as e:
        logger.warning("adzuna_fetch_failed: %s", e)

    return results


async def _search_remoteok(
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search RemoteOK API for remote job listings."""
    results: list[dict[str, Any]] = []
    try:
        async with _get_http_client() as client:
            url = "https://remoteok.com/api"

            logger.debug("remoteok_fetch query=%s", query[:50])

            resp = await client.get(url)
            resp.raise_for_status()
            jobs = resp.json()

            # Filter by query (search in title and description)
            query_lower = query.lower()
            matched = 0

            for job in jobs:
                if matched >= limit:
                    break

                title = job.get("title", "").lower()
                description = job.get("description", "").lower()
                tags = job.get("tags", [])

                if query_lower in title or query_lower in description or any(
                    query_lower in tag.lower() for tag in tags
                ):
                    matched += 1

                    # Parse salary if available
                    salary_str = None
                    if job.get("salary"):
                        salary_str = str(job["salary"])

                    results.append(
                        {
                            "title": job.get("title", ""),
                            "company": job.get("company", ""),
                            "location": "Remote",
                            "url": job.get("url", ""),
                            "salary": salary_str,
                            "remote": True,
                            "source": "remoteok",
                            "date_posted": job.get("date", None),
                        }
                    )

        logger.info("remoteok_success count=%d", len(results))

    except Exception as e:
        logger.warning("remoteok_fetch_failed: %s", e)

    return results


async def _search_hn_hiring(
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search HN 'Who is Hiring' threads via Algolia API."""
    results: list[dict[str, Any]] = []
    try:
        async with _get_http_client() as client:
            # Search for "Ask HN: Who is hiring" stories
            url = "https://hn.algolia.com/api/v1/search"

            logger.debug("hn_hiring_fetch query=%s", query[:50])

            # First, find "Ask HN: Who is hiring" stories
            params: dict[str, str | int] = {
                "query": "Ask HN: Who is hiring",
                "tags": "story",
                "numericFilters": "created_at_i>0",
                "hitsPerPage": 5,
            }

            resp = await client.get(url, params=params)
            resp.raise_for_status()
            stories = resp.json()

            # For each story, search comments for the job query
            for story in stories.get("hits", []):
                story_id = story.get("objectID")
                if not story_id:
                    continue

                # Search comments in this story
                comment_params: dict[str, str | int] = {
                    "query": query,
                    "tags": f"comment,story_{story_id}",
                    "numericFilters": "created_at_i>0",
                    "hitsPerPage": limit - len(results),
                }

                comment_resp = await client.get(url, params=comment_params)
                comment_resp.raise_for_status()
                comments = comment_resp.json()

                for comment in comments.get("hits", []):
                    if len(results) >= limit:
                        break

                    results.append(
                        {
                            "title": comment.get("text", "")[:100],
                            "company": "HN User",
                            "location": "Remote (HN)",
                            "url": f"https://news.ycombinator.com/item?id={comment.get('objectID', '')}",
                            "salary": None,
                            "remote": True,
                            "source": "hn_hiring",
                            "date_posted": (
                                datetime.fromtimestamp(
                                    comment.get("created_at_i", 0), UTC
                                ).isoformat()
                                if comment.get("created_at_i")
                                else None
                            ),
                        }
                    )

                if len(results) >= limit:
                    break

        logger.info("hn_hiring_success count=%d", len(results))

    except Exception as e:
        logger.warning("hn_hiring_fetch_failed: %s", e)

    return results


async def _search_github_jobs(
    query: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Search for job postings on GitHub via search for job board sites."""
    results: list[dict[str, Any]] = []
    try:
        async with _get_http_client() as client:
            # Use DuckDuckGo for site-specific search
            url = "https://api.duckduckgo.com/"

            # Search common job board sites
            job_sites = [
                "greenhouse.io",
                "lever.co",
                "ashbyhq.com",
                "workable.com",
                "breezy.hr",
            ]

            for site in job_sites:
                if len(results) >= limit:
                    break

                search_query = f'{query} site:{site}'

                logger.debug("github_jobs_fetch query=%s site=%s", query[:30], site)

                params: dict[str, str | int] = {
                    "q": search_query,
                    "format": "json",
                    "no_html": 1,
                }

                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()

                for result in data.get("Results", [])[:5]:
                    if len(results) >= limit:
                        break

                    results.append(
                        {
                            "title": result.get("Result", "")[:80],
                            "company": site.split(".")[0].title(),
                            "location": "Global",
                            "url": result.get("FirstURL", ""),
                            "salary": None,
                            "remote": True,
                            "source": "job_boards",
                            "date_posted": None,
                        }
                    )

        logger.info("github_jobs_success count=%d", len(results))

    except Exception as e:
        logger.warning("github_jobs_fetch_failed: %s", e)

    return results


async def research_job_search(
    query: str,
    location: str | None = None,
    remote_only: bool = False,
    limit: int = 20,
) -> dict[str, Any]:
    """Search job listings across multiple free sources.

    Searches:
    1. Adzuna API (if credentials available)
    2. RemoteOK (remote jobs)
    3. HN 'Who is Hiring' threads (via Algolia)
    4. Job board sites (via DuckDuckGo)

    Args:
        query: job title or keyword to search for
        location: location filter (optional)
        remote_only: if True, filter to remote jobs only
        limit: max total results across all sources (default 20)

    Returns:
        Dict with keys: query, location, remote_only, results (list of job dicts),
        sources_searched (int), total_results (int)
    """
    logger.info(
        "job_search query=%s location=%s remote_only=%s limit=%d",
        query[:50],
        location,
        remote_only,
        limit,
    )

    try:
        # Run searches in parallel
        tasks = [
            _search_adzuna(query, location, limit),
            _search_remoteok(query, limit),
            _search_hn_hiring(query, limit),
            _search_github_jobs(query, limit),
        ]

        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results and filter exceptions
        flattened: list[dict[str, Any]] = []
        sources_found = 0

        for result in all_results:
            if isinstance(result, Exception):
                logger.warning("job_search_parallel_error: %s", result)
                continue
            if isinstance(result, list) and result:
                sources_found += 1
                flattened.extend(result)

        # Filter by remote_only if requested
        if remote_only:
            flattened = [job for job in flattened if job.get("remote", False)]

        # Deduplicate by URL (if URL exists)
        seen: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for job in flattened:
            url = job.get("url", "")
            if url and url in seen:
                continue
            if url:
                seen.add(url)
            deduped.append(job)

        # Trim to limit
        final_results = deduped[:limit]

        logger.info(
            "job_search_complete query=%s results=%d sources=%d",
            query[:50],
            len(final_results),
            sources_found,
        )

        return {
            "query": query,
            "location": location,
            "remote_only": remote_only,
            "results": final_results,
            "sources_searched": sources_found,
            "total_results": len(final_results),
        }

    except Exception as e:
        logger.error("job_search_failed: %s", e)
        return {
            "query": query,
            "location": location,
            "remote_only": remote_only,
            "results": [],
            "sources_searched": 0,
            "total_results": 0,
            "error": str(e),
        }


def _extract_skills(text: str, limit: int = 50) -> list[str]:
    """Extract common tech/business keywords from text."""
    if not text:
        return []

    # Common tech and business keywords
    skill_patterns = [
        # Programming languages
        r"\b(python|javascript|typescript|java|c\+\+|c#|rust|go|ruby|php|swift|kotlin)\b",
        # Frameworks/libraries
        r"\b(react|vue|angular|django|flask|spring|fastapi|nodejs|node\.js|express|webpack)\b",
        # Cloud/DevOps
        r"\b(aws|azure|gcp|kubernetes|docker|jenkins|terraform|ci\/cd|devops)\b",
        # Databases
        r"\b(sql|postgresql|mysql|mongodb|redis|dynamodb|cassandra|elasticsearch)\b",
        # Other tech
        r"\b(machine learning|ai|nlp|big data|data science|api|rest|graphql|microservices)\b",
        # Business skills
        r"\b(agile|scrum|leadership|communication|project management|problem solving)\b",
    ]

    text_lower = text.lower()
    matches: list[str] = []

    for pattern in skill_patterns:
        found = re.findall(pattern, text_lower, re.IGNORECASE)
        matches.extend(found)

    return matches[:limit] if matches else []


async def research_job_market(
    role: str,
    location: str | None = None,
) -> dict[str, Any]:
    """Aggregate job market intelligence for a role.

    Performs job search and analyzes:
    - Total listing count
    - Salary ranges (if available)
    - Top mentioned skills/technologies
    - Demand score (normalized 0-1)
    - Remote job percentage

    Args:
        role: job role/title to research
        location: optional location filter

    Returns:
        Dict with keys: role, location, total_listings, salary_range,
        top_skills, demand_score, sources, remote_percentage
    """
    logger.info("job_market query=%s location=%s", role[:50], location)

    try:
        # Get comprehensive search
        search_result = await research_job_search(
            query=role,
            location=location,
            remote_only=False,
            limit=50,  # Get more results for market analysis
        )

        jobs = search_result.get("results", [])

        if not jobs:
            return {
                "role": role,
                "location": location,
                "total_listings": 0,
                "salary_range": {"min": None, "max": None, "currency": "GBP/USD"},
                "top_skills": [],
                "demand_score": 0.0,
                "sources": [],
                "remote_percentage": 0.0,
            }

        # Count by source
        sources_count: dict[str, int] = Counter()
        for job in jobs:
            sources_count[job.get("source", "unknown")] += 1

        # Extract salaries
        salaries: list[float] = []
        salary_pattern = r"£?([\d,]+)"

        for job in jobs:
            salary_str = job.get("salary", "")
            if salary_str:
                # Try to extract min salary
                matches = re.findall(salary_pattern, str(salary_str))
                if matches:
                    try:
                        sal = float(matches[0].replace(",", ""))
                        salaries.append(sal)
                    except ValueError:
                        pass

        salary_min = None
        salary_max = None
        if salaries:
            salary_min = f"£{int(min(salaries)):,}"
            salary_max = f"£{int(max(salaries)):,}"

        # Extract and count skills from job descriptions/titles
        all_skills: list[str] = []
        for job in jobs:
            title = job.get("title", "")
            description = job.get("title", "")  # Use title as proxy for description
            skills = _extract_skills(f"{title} {description}")
            all_skills.extend(skills)

        # Top skills by frequency
        skill_counts = Counter(all_skills)
        top_skills = [
            {"skill": skill, "mentions": count}
            for skill, count in skill_counts.most_common(10)
        ]

        # Demand score (normalized to 0-1)
        # Based on number of listings and diversity of sources
        demand_score = min(1.0, (len(jobs) / 50.0) * (len(sources_count) / 4.0))

        # Remote percentage
        remote_jobs = sum(1 for job in jobs if job.get("remote", False))
        remote_pct = (remote_jobs / len(jobs) * 100.0) if jobs else 0.0

        logger.info(
            "job_market_complete role=%s listings=%d remote_pct=%.1f",
            role[:50],
            len(jobs),
            remote_pct,
        )

        return {
            "role": role,
            "location": location,
            "total_listings": len(jobs),
            "salary_range": {
                "min": salary_min,
                "max": salary_max,
                "currency": "GBP/USD",
            },
            "top_skills": top_skills,
            "demand_score": round(demand_score, 2),
            "sources": [
                {"name": source, "listings": count}
                for source, count in sorted(sources_count.items(), key=lambda x: x[1], reverse=True)
            ],
            "remote_percentage": round(remote_pct, 1),
        }

    except Exception as e:
        logger.error("job_market_failed: %s", e)
        return {
            "role": role,
            "location": location,
            "total_listings": 0,
            "salary_range": {"min": None, "max": None, "currency": "GBP/USD"},
            "top_skills": [],
            "demand_score": 0.0,
            "sources": [],
            "remote_percentage": 0.0,
            "error": str(e),
        }
