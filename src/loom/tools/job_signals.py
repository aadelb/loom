"""Hidden job market tools for recruitment intelligence.

Provides:
- research_funding_signal: Detect hiring signals from funding/growth indicators
- research_stealth_hire_scanner: Find hidden job opportunities not on job boards
- research_interviewer_profiler: Build a profile of a potential interviewer
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.job_signals")


async def _get_json(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> Any:
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("job_signals json fetch failed: %s", exc)
    return None


async def _get_text(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> str:
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("job_signals text fetch failed: %s", exc)
    return ""


async def _fetch_sec_filings(
    client: httpx.AsyncClient, company: str
) -> dict[str, Any]:
    """Fetch and parse recent SEC filings for hiring signals."""
    try:
        # Search SEC EDGAR for recent filings
        search_url = (
            f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company={quote(company)}"
            "&type=&dateb=&owner=exclude&count=100&output=json"
        )
        data = await _get_json(client, search_url, timeout=20.0)

        if not data or "filings" not in data:
            return {"cik": None, "filings": []}

        cik = data.get("cik_str")
        filings = data.get("filings", {}).get("recent", [])

        # Filter for hiring-related filings (S-1, 8-K, SC 13D)
        hiring_filings = []
        for filing in filings[:50]:
            form_type = filing.get("form", "")
            if form_type in ("S-1", "8-K", "SC 13D", "10-K", "10-Q"):
                filing_date = filing.get("filingDate", "")
                accession = filing.get("accessionNumber", "")

                # Extract document URL
                doc_url = (
                    f"https://www.sec.gov/cgi-bin/viewer?action=view&"
                    f"cik={cik}&accession_number={accession}&xbrl_type=v"
                )

                hiring_filings.append(
                    {
                        "form": form_type,
                        "date": filing_date,
                        "accession": accession,
                        "url": doc_url,
                    }
                )

        return {"cik": cik, "filings": hiring_filings}
    except Exception as exc:
        logger.debug("sec_filings fetch failed: %s", exc)
        return {"cik": None, "filings": []}


async def _fetch_github_activity(
    client: httpx.AsyncClient, company: str
) -> dict[str, Any]:
    """Analyze GitHub org activity for new projects and hiring signals."""
    try:
        company_slug = company.lower().replace(" ", "-").replace(".", "")
        repos_url = f"https://api.github.com/orgs/{quote(company_slug)}/repos?sort=created&per_page=30"

        data = await _get_json(client, repos_url, timeout=15.0)
        if not data or isinstance(data, dict) and "message" in data:
            return {"repos": [], "activity_level": "unknown"}

        if not isinstance(data, list):
            return {"repos": [], "activity_level": "unknown"}

        # Calculate activity metrics
        recent_repos = []
        for repo in data[:20]:
            created_at = repo.get("created_at", "")
            pushed_at = repo.get("pushed_at", "")
            recent_repos.append(
                {
                    "name": repo.get("name", ""),
                    "created_at": created_at,
                    "pushed_at": pushed_at,
                    "description": repo.get("description", ""),
                    "language": repo.get("language", "unknown"),
                    "stars": repo.get("stargazers_count", 0),
                }
            )

        # Determine activity level
        activity_level = "low"
        if len(recent_repos) > 15:
            activity_level = "high"
        elif len(recent_repos) > 8:
            activity_level = "medium"

        return {"repos": recent_repos, "activity_level": activity_level}
    except Exception as exc:
        logger.debug("github_activity fetch failed: %s", exc)
        return {"repos": [], "activity_level": "unknown"}


async def _fetch_crt_sh_subdomains(
    client: httpx.AsyncClient, domain: str
) -> list[str]:
    """Fetch new subdomains from Certificate Transparency logs."""
    try:
        url = f"https://crt.sh/?q=%25.{quote(domain)}&output=json"
        data = await _get_json(client, url, timeout=30.0)

        if not data or not isinstance(data, list):
            return []

        subdomains: set[str] = set()
        for entry in data:
            name_value = entry.get("name_value", "")
            for line in name_value.split("\n"):
                line = line.strip().lstrip("*.")
                if line and (line.endswith(f".{domain}") or line == domain):
                    # Filter for likely new services (not www, mail, etc.)
                    if not any(
                        prefix in line.lower()
                        for prefix in ["www", "mail", "smtp", "pop", "imap"]
                    ):
                        subdomains.add(line)

        return sorted(subdomains)[:30]
    except Exception as exc:
        logger.debug("crt_sh fetch failed: %s", exc)
        return []


async def _fetch_github_jobs_keywords(
    client: httpx.AsyncClient, keywords: str
) -> list[dict[str, Any]]:
    """Search GitHub repos mentioning job opportunities."""
    try:
        safe_keywords = quote(keywords)
        search_url = (
            f"https://api.github.com/search/repositories?"
            f"q={safe_keywords}+hiring+in:readme&per_page=10"
        )

        data = await _get_json(client, search_url, timeout=15.0)
        if not data or "items" not in data:
            return []

        jobs = []
        for item in data.get("items", [])[:10]:
            jobs.append(
                {
                    "source": "GitHub",
                    "title": item.get("name", ""),
                    "url": item.get("html_url", ""),
                    "description": item.get("description", ""),
                    "stars": item.get("stargazers_count", 0),
                }
            )

        return jobs
    except Exception as exc:
        logger.debug("github_jobs fetch failed: %s", exc)
        return []


async def _fetch_hackernews_hiring(
    client: httpx.AsyncClient, keywords: str
) -> list[dict[str, Any]]:
    """Fetch HackerNews Who's Hiring comments matching keywords."""
    try:
        safe_keywords = quote(keywords)
        search_url = (
            f"https://hn.algolia.com/api/v1/search?query={safe_keywords}&"
            f"tags=comment,ask_hn&hitsPerPage=15"
        )

        data = await _get_json(client, search_url, timeout=15.0)
        if not data or "hits" not in data:
            return []

        jobs = []
        for hit in data.get("hits", [])[:10]:
            jobs.append(
                {
                    "source": "HackerNews",
                    "title": hit.get("story_title", "") or hit.get("title", ""),
                    "url": hit.get("story_url", "") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    "snippet": hit.get("comment_text", "")[:200],
                    "points": hit.get("points", 0),
                }
            )

        return jobs
    except Exception as exc:
        logger.debug("hackernews_hiring fetch failed: %s", exc)
        return []


async def _fetch_reddit_hiring(
    client: httpx.AsyncClient, keywords: str
) -> list[dict[str, Any]]:
    """Fetch Reddit hiring posts from r/forhire and similar subreddits."""
    try:
        safe_keywords = quote(keywords)
        search_url = (
            f"https://www.reddit.com/r/forhire/search.json?q={safe_keywords}&limit=15"
        )

        data = await _get_json(client, search_url, timeout=15.0)
        if not data or "data" not in data or "children" not in data["data"]:
            return []

        jobs = []
        for child in data["data"]["children"][:10]:
            post = child.get("data", {})
            jobs.append(
                {
                    "source": "Reddit",
                    "title": post.get("title", ""),
                    "url": f"https://reddit.com{post.get('permalink', '')}",
                    "snippet": post.get("selftext", "")[:200],
                    "upvotes": post.get("ups", 0),
                }
            )

        return jobs
    except Exception as exc:
        logger.debug("reddit_hiring fetch failed: %s", exc)
        return []


async def _fetch_github_profile(
    client: httpx.AsyncClient, username: str
) -> dict[str, Any]:
    """Fetch GitHub profile and top repos for a person."""
    try:
        safe_username = quote(username.lower().replace(" ", ""))
        profile_url = f"https://api.github.com/users/{safe_username}"
        repos_url = (
            f"https://api.github.com/users/{safe_username}/repos?"
            f"sort=stars&per_page=10"
        )

        profile_data = await _get_json(client, profile_url, timeout=10.0)
        repos_data = await _get_json(client, repos_url, timeout=10.0)

        if not profile_data or "message" in profile_data:
            return {"found": False}

        repos = []
        if repos_data and isinstance(repos_data, list):
            for repo in repos_data[:5]:
                repos.append(
                    {
                        "name": repo.get("name", ""),
                        "language": repo.get("language", ""),
                        "stars": repo.get("stargazers_count", 0),
                        "description": repo.get("description", ""),
                    }
                )

        return {
            "found": True,
            "username": profile_data.get("login", ""),
            "name": profile_data.get("name", ""),
            "bio": profile_data.get("bio", ""),
            "company": profile_data.get("company", ""),
            "location": profile_data.get("location", ""),
            "blog": profile_data.get("blog", ""),
            "followers": profile_data.get("followers", 0),
            "public_repos": profile_data.get("public_repos", 0),
            "top_repos": repos,
        }
    except Exception as exc:
        logger.debug("github_profile fetch failed: %s", exc)
        return {"found": False}


async def _fetch_semantic_scholar(
    client: httpx.AsyncClient, person_name: str
) -> dict[str, Any]:
    """Fetch academic publications from Semantic Scholar."""
    try:
        safe_name = quote(person_name)
        search_url = f"https://api.semanticscholar.org/graph/v1/author/search?query={safe_name}&limit=5"

        data = await _get_json(client, search_url, timeout=15.0)
        if not data or "data" not in data:
            return {"publications": []}

        authors = data.get("data", [])
        publications = []

        for author in authors[:1]:  # Get top match
            author_id = author.get("authorId")
            if not author_id:
                continue

            papers_url = (
                f"https://api.semanticscholar.org/graph/v1/author/{author_id}/papers?"
                f"limit=10&fields=title,year,citationCount,publicationVenue"
            )
            papers = await _get_json(client, papers_url, timeout=15.0)

            if papers and "data" in papers:
                for paper in papers.get("data", [])[:5]:
                    publications.append(
                        {
                            "title": paper.get("title", ""),
                            "year": paper.get("year"),
                            "citations": paper.get("citationCount", 0),
                            "venue": paper.get("publicationVenue", {}).get("name", ""),
                        }
                    )

        return {"publications": publications}
    except Exception as exc:
        logger.debug("semantic_scholar fetch failed: %s", exc)
        return {"publications": []}


async def _fetch_hackernews_activity(
    client: httpx.AsyncClient, person_name: str
) -> dict[str, Any]:
    """Fetch HackerNews comments and submissions for a person."""
    try:
        safe_name = quote(person_name)
        search_url = (
            f"https://hn.algolia.com/api/v1/search?query={safe_name}&"
            f"tags=author&hitsPerPage=20"
        )

        data = await _get_json(client, search_url, timeout=15.0)
        if not data or "hits" not in data:
            return {"comments": [], "submissions": [], "karma_indicators": []}

        comments = []
        submissions = []

        for hit in data.get("hits", [])[:20]:
            if hit.get("comment_text"):
                comments.append(
                    {
                        "text": hit.get("comment_text", "")[:150],
                        "points": hit.get("points", 0),
                    }
                )
            elif hit.get("story_title"):
                submissions.append(
                    {
                        "title": hit.get("story_title", ""),
                        "url": hit.get("story_url", ""),
                        "points": hit.get("points", 0),
                    }
                )

        # Extract tech interests from comments/posts
        tech_keywords = [
            "python",
            "javascript",
            "rust",
            "golang",
            "java",
            "machine learning",
            "ai",
            "devops",
            "aws",
            "kubernetes",
        ]
        all_text = " ".join([c.get("text", "") for c in comments])
        tech_stack = [
            tech
            for tech in tech_keywords
            if tech.lower() in all_text.lower()
        ]

        return {
            "comments": comments[:5],
            "submissions": submissions[:5],
            "tech_interests": tech_stack,
        }
    except Exception as exc:
        logger.debug("hackernews_activity fetch failed: %s", exc)
        return {"comments": [], "submissions": [], "tech_interests": []}


def research_funding_signal(company: str, domain: str = "") -> dict[str, Any]:
    """Detect hiring signals from funding/growth indicators.

    Analyzes:
    - Recent SEC filings (S-1 IPO, 8-K acquisitions, SC 13D events)
    - GitHub organization activity and new repo creation
    - Certificate Transparency logs for new subdomains (new products/services)

    Args:
        company: Company name (e.g., "OpenAI", "Anthropic")
        domain: Optional domain for subdomain enumeration (e.g., "openai.com")

    Returns:
        Dict with keys:
        - company: company name
        - funding_signals: list of funding/growth events
        - hiring_likelihood: "high", "medium", or "low"
        - evidence: summary of findings
        - new_subdomains: list of recently registered subdomains (product signals)
        - github_activity: GitHub org activity level
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            company_clean = company.strip()

            if not company_clean or len(company_clean) > 200:
                return {
                    "company": company,
                    "error": "company must be 1-200 characters",
                }

            logger.info("funding_signal query=%s", company_clean)

            # Parallel fetch tasks
            sec_task = _fetch_sec_filings(client, company_clean)
            github_task = _fetch_github_activity(client, company_clean)
            subdomains_task = (
                _fetch_crt_sh_subdomains(client, domain)
                if domain and len(domain) < 100
                else asyncio.sleep(0)
            )

            sec_data, github_data = await asyncio.gather(
                sec_task, github_task, return_exceptions=True
            )

            new_subdomains = []
            if domain:
                try:
                    new_subdomains = await _fetch_crt_sh_subdomains(client, domain)
                except Exception as exc:
                    logger.debug("subdomain fetch failed: %s", exc)

            # Interpret signals
            hiring_signals = []
            hiring_likelihood = "low"
            evidence_items = []

            if isinstance(sec_data, dict):
                for filing in sec_data.get("filings", [])[:5]:
                    form = filing.get("form", "")
                    date = filing.get("date", "")
                    if form == "S-1":
                        hiring_signals.append(f"IPO filing ({date})")
                        hiring_likelihood = "high"
                        evidence_items.append(
                            "Company filing for IPO - major scaling phase"
                        )
                    elif form == "8-K":
                        hiring_signals.append(f"Major event filed ({date})")
                        if hiring_likelihood != "high":
                            hiring_likelihood = "medium"
                    elif form == "SC 13D":
                        hiring_signals.append(f"Acquisition signal ({date})")
                        if hiring_likelihood != "high":
                            hiring_likelihood = "medium"
                        evidence_items.append("Company acquired or major investor")

            if isinstance(github_data, dict):
                activity = github_data.get("activity_level", "")
                if activity == "high":
                    hiring_signals.append("High GitHub activity (new projects)")
                    if hiring_likelihood != "high":
                        hiring_likelihood = "medium"
                    evidence_items.append(
                        f"Active development - {len(github_data.get('repos', []))} recent repos"
                    )
                elif activity == "medium":
                    if hiring_likelihood == "low":
                        hiring_likelihood = "medium"

            if new_subdomains:
                hiring_signals.append(
                    f"New subdomains/services ({len(new_subdomains)} detected)"
                )
                if hiring_likelihood != "high":
                    hiring_likelihood = "medium"
                evidence_items.append(
                    f"New infrastructure discovered - expanding operations"
                )

            evidence = (
                " | ".join(evidence_items)
                if evidence_items
                else "No major hiring signals detected"
            )

            return {
                "company": company_clean,
                "funding_signals": hiring_signals,
                "hiring_likelihood": hiring_likelihood,
                "evidence": evidence,
                "new_subdomains": new_subdomains,
                "github_activity": github_data.get("activity_level", "unknown")
                if isinstance(github_data, dict)
                else "unknown",
            }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


def research_stealth_hire_scanner(
    keywords: str, location: str = ""
) -> dict[str, Any]:
    """Find hidden job opportunities not advertised on traditional job boards.

    Searches:
    - GitHub repos with hiring mentions in READMEs
    - HackerNews "Who's Hiring" threads
    - Reddit r/forhire and related subreddits

    Args:
        keywords: Job search keywords (e.g., "Python engineer", "DevOps")
        location: Optional location filter

    Returns:
        Dict with keys:
        - keywords: search keywords used
        - location: location filter (if provided)
        - stealth_jobs_found: list of {source, title, url, snippet}
        - total_found: count of opportunities discovered
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            keywords_clean = keywords.strip()

            if not keywords_clean or len(keywords_clean) > 200:
                return {
                    "keywords": keywords,
                    "error": "keywords must be 1-200 characters",
                }

            logger.info("stealth_hire_scanner query=%s", keywords_clean)

            # Parallel fetch from all sources
            github_task = _fetch_github_jobs_keywords(client, keywords_clean)
            hackernews_task = _fetch_hackernews_hiring(client, keywords_clean)
            reddit_task = _fetch_reddit_hiring(client, keywords_clean)

            github_jobs, hackernews_jobs, reddit_jobs = await asyncio.gather(
                github_task, hackernews_task, reddit_task, return_exceptions=True
            )

            # Consolidate results
            all_jobs = []

            if isinstance(github_jobs, list):
                all_jobs.extend(github_jobs)
            if isinstance(hackernews_jobs, list):
                all_jobs.extend(hackernews_jobs)
            if isinstance(reddit_jobs, list):
                all_jobs.extend(reddit_jobs)

            # Filter by location if provided
            if location:
                location_lower = location.lower()
                all_jobs = [
                    j
                    for j in all_jobs
                    if location_lower
                    in (j.get("title", "") + j.get("snippet", "")).lower()
                ]

            return {
                "keywords": keywords_clean,
                "location": location,
                "stealth_jobs_found": all_jobs[:50],
                "total_found": len(all_jobs),
            }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()


def research_interviewer_profiler(
    person_name: str, company: str = ""
) -> dict[str, Any]:
    """Build a comprehensive profile of a potential interviewer from public data.

    Analyzes:
    - GitHub profile and top repositories
    - Academic publications (Semantic Scholar)
    - HackerNews comments and submissions (interests, expertise)
    - Inferred tech stack and expertise areas

    Args:
        person_name: Full name of the person (e.g., "Sam Altman")
        company: Optional company affiliation for context

    Returns:
        Dict with keys:
        - person_name: name searched
        - company: associated company (if provided)
        - github_profile: GitHub profile info if found
        - publications: list of academic papers
        - tech_interests: inferred tech stack and areas
        - hackernews_activity: public forum activity
        - talking_points: suggested conversation topics
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            person_clean = person_name.strip()

            if not person_clean or len(person_clean) > 200:
                return {
                    "person_name": person_name,
                    "error": "person_name must be 1-200 characters",
                }

            logger.info(
                "interviewer_profiler query=%s company=%s",
                person_clean,
                company,
            )

            # Parallel fetch tasks
            github_task = _fetch_github_profile(client, person_clean)
            scholar_task = _fetch_semantic_scholar(client, person_clean)
            hackernews_task = _fetch_hackernews_activity(client, person_clean)

            github_data, scholar_data, hn_data = await asyncio.gather(
                github_task, scholar_task, hackernews_task, return_exceptions=True
            )

            # Build tech stack from multiple sources
            tech_stack = []
            talking_points = []

            if isinstance(github_data, dict) and github_data.get("found"):
                for repo in github_data.get("top_repos", []):
                    lang = repo.get("language")
                    if lang and lang not in tech_stack:
                        tech_stack.append(lang)

                if github_data.get("bio"):
                    talking_points.append(
                        f"GitHub bio mentions: {github_data.get('bio')}"
                    )

            if isinstance(hn_data, dict):
                tech_interests = hn_data.get("tech_interests", [])
                tech_stack.extend([t for t in tech_interests if t not in tech_stack])

                for submission in hn_data.get("submissions", [])[:2]:
                    talking_points.append(
                        f"Published on HN: {submission.get('title', '')}"
                    )

            if isinstance(scholar_data, dict):
                pubs = scholar_data.get("publications", [])
                if pubs:
                    talking_points.append(
                        f"Researching: {pubs[0].get('title', '')} "
                        f"({pubs[0].get('year')})"
                    )

            return {
                "person_name": person_clean,
                "company": company,
                "github_profile": github_data if isinstance(github_data, dict) else None,
                "publications": scholar_data.get("publications", [])
                if isinstance(scholar_data, dict)
                else [],
                "tech_interests": tech_stack[:10],
                "hackernews_activity": hn_data
                if isinstance(hn_data, dict)
                else {},
                "talking_points": talking_points[:5],
            }

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
