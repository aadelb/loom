"""Career trajectory and market velocity intelligence tools.

Provides:
- research_career_trajectory: Build a comprehensive career profile combining academic,
  GitHub, and ORCID data with analysis of career progression.
- research_market_velocity: Measure how fast a skill/technology is growing in the job
  market by analyzing GitHub trends, discussion frequency, and academic momentum.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

from loom.http_helpers import fetch_json, fetch_text

logger = logging.getLogger("loom.tools.career_trajectory")


async def _search_semantic_scholar(
    client: httpx.AsyncClient, person_name: str
) -> dict[str, Any]:
    """Search for author on Semantic Scholar."""
    url = f"https://api.semanticscholar.org/graph/v1/author/search?query={quote(person_name)}&limit=5"
    data = await fetch_json(client, url)
    if data is None:
        return {}
    if not data or "data" not in data:
        return {}

    # Find best match by name similarity
    best_match = None
    for author in data.get("data", []):
        if person_name.lower() in author.get("name", "").lower():
            best_match = author
            break
    best_match = best_match or (data.get("data", [{}])[0] if data.get("data") else None)

    if not best_match:
        return {}

    author_id = best_match.get("authorId")
    if not author_id:
        return {}

    # Fetch author details including papers
    detail_url = f"https://api.semanticscholar.org/graph/v1/author/{author_id}?fields=papers,hIndex"
    detail = await fetch_json(client, detail_url)

    if not detail:
        return {}

    papers = detail.get("papers", [])
    h_index = detail.get("hIndex", 0)

    # Extract topics from papers
    topics: dict[str, int] = {}
    for paper in papers[:50]:  # Analyze first 50 papers
        for field in paper.get("fieldsOfStudy", []):
            topics[field] = topics.get(field, 0) + 1

    return {
        "author_id": author_id,
        "name": best_match.get("name", ""),
        "paper_count": len(papers),
        "h_index": h_index,
        "topics": sorted(
            topics.items(), key=lambda x: x[1], reverse=True
        )[:10],  # Top 10
    }


async def _search_github_user(
    client: httpx.AsyncClient, person_name: str
) -> dict[str, Any]:
    """Search for GitHub user."""
    url = f"https://api.github.com/search/users?q={quote(person_name)}&per_page=5"
    data = await fetch_json(client, url)

    if data is None or not isinstance(data, dict) or "items" not in data or len(data["items"]) == 0:
        return {}

    user = data["items"][0]
    username = user.get("login")

    if not username:
        return {}

    # Fetch user repos
    repos_url = f"https://api.github.com/users/{username}/repos?per_page=100&type=owner"
    repos = await fetch_json(client, repos_url)

    if not isinstance(repos, list):
        repos = []

    # Analyze repos
    languages: dict[str, int] = {}
    total_stars = 0
    total_repos = len(repos)

    for repo in repos:
        stars = repo.get("stargazers_count", 0)
        total_stars += stars
        lang = repo.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1

    return {
        "username": username,
        "profile_url": user.get("html_url", ""),
        "repo_count": total_repos,
        "total_stars": total_stars,
        "languages": sorted(
            languages.items(), key=lambda x: x[1], reverse=True
        )[:10],
        "avatar_url": user.get("avatar_url", ""),
        "company": user.get("company", ""),
        "location": user.get("location", ""),
    }


async def _search_orcid(client: httpx.AsyncClient, person_name: str) -> dict[str, Any]:
    """Search for ORCID profile."""
    url = f"https://pub.orcid.org/v3.0/search/?q={quote(person_name)}"
    data = await fetch_json(client, url)

    if data is None or not isinstance(data, dict) or "result" not in data or len(data["result"]) == 0:
        return {}

    result = data["result"][0]
    orcid_id = result.get("orcid-identifier", {}).get("path", "")

    if not orcid_id:
        return {}

    # Fetch detailed profile
    detail_url = f"https://pub.orcid.org/v3.0/{orcid_id}"
    detail = await fetch_json(client, detail_url)

    if not detail:
        return {}

    person_data = detail.get("person", {})
    name = person_data.get("name", {})
    full_name = f"{name.get('given-names', {}).get('value', '')} {name.get('family-name', {}).get('value', '')}"

    # Count works
    works = detail.get("activities-summary", {}).get("works", {}).get("group", [])
    work_count = sum(len(w.get("work-summary", [])) for w in works)

    return {
        "orcid_id": orcid_id,
        "name": full_name.strip(),
        "profile_url": f"https://orcid.org/{orcid_id}",
        "work_count": work_count,
        "biography": person_data.get("biography", {}).get("value", ""),
    }


def _analyze_career_stages(
    scholar: dict[str, Any], github: dict[str, Any], orcid: dict[str, Any]
) -> dict[str, Any]:
    """Analyze career progression based on available data."""
    stages = []

    # Academic progression
    if scholar and scholar.get("paper_count"):
        paper_count = scholar["paper_count"]
        h_index = scholar.get("h_index", 0)

        if h_index > 30:
            stage = "Late Career / Senior Researcher"
            description = "Highly cited researcher with significant impact"
        elif h_index > 15:
            stage = "Mid Career / Established Researcher"
            description = "Well-published researcher with notable citations"
        elif h_index > 5:
            stage = "Early Career Researcher"
            description = "Active researcher building publication record"
        else:
            stage = "Graduate Student / Early Researcher"
            description = "Beginning academic career"

        stages.append(
            {
                "stage": stage,
                "description": description,
                "source": "academic",
                "metrics": {
                    "papers": paper_count,
                    "h_index": h_index,
                },
            }
        )

    # GitHub progression
    if github and github.get("repo_count"):
        repo_count = github["repo_count"]
        total_stars = github.get("total_stars", 0)

        if total_stars > 10000:
            stage = "Senior Open Source Developer"
            description = "Highly influential open source contributor"
        elif total_stars > 1000:
            stage = "Experienced Open Source Developer"
            description = "Well-recognized open source contributor"
        elif repo_count > 20:
            stage = "Active Open Source Developer"
            description = "Regular open source contributor"
        else:
            stage = "Learning / Emerging Developer"
            description = "Building open source portfolio"

        stages.append(
            {
                "stage": stage,
                "description": description,
                "source": "github",
                "metrics": {
                    "repos": repo_count,
                    "stars": total_stars,
                },
            }
        )

    return {
        "stages": stages,
        "estimated_experience_level": (
            "Senior" if any(s["source"] == "academic" for s in stages) else "Mid-Level"
        )
        if stages
        else "Unknown",
    }


def _determine_trajectory(
    scholar: dict[str, Any], github: dict[str, Any]
) -> str:
    """Determine growth trajectory: rising, stable, or declining."""
    # Simplified heuristic based on available data
    signals = []

    if scholar:
        # Strong h-index suggests continuing impact
        h_index = scholar.get("h_index", 0)
        if h_index > 20:
            signals.append("rising")
        elif h_index > 5:
            signals.append("stable")
        else:
            signals.append("rising")  # Early career growth

    if github:
        repo_count = github.get("repo_count", 0)
        if repo_count > 50:
            signals.append("rising")
        elif repo_count > 10:
            signals.append("stable")

    if not signals:
        return "unknown"

    # Majority vote
    rising_count = signals.count("rising")
    stable_count = signals.count("stable")

    if rising_count > stable_count:
        return "rising"
    elif stable_count > rising_count:
        return "stable"
    else:
        return "stable"


async def research_career_trajectory(person_name: str, domain: str = "") -> dict[str, Any]:
    """Build a career trajectory profile by combining multiple data sources.

    Analyzes academic publications (Semantic Scholar), open source work (GitHub),
    and institutional affiliations (ORCID) to construct a comprehensive career
    profile with growth trajectory analysis.

    Args:
        person_name: Full name of the person (e.g., "Yann LeCun", "Jeremy Howard")
        domain: Optional domain filter (e.g., "machine-learning", "blockchain") to
                narrow results (not strictly enforced, advisory only)

    Returns:
        Dict with keys:
        - person_name: Input name
        - academic_publications: count, h_index, topics (list of top fields)
        - github_activity: username, repos, languages, stars
        - orcid_profile: orcid_id, work_count, biography
        - career_stages: list of identified career stages with descriptions
        - growth_trajectory: "rising", "stable", "declining", or "unknown"
        - experience_level: "Junior", "Mid-Level", "Senior", or "Unknown"
        - combined_impact_score: float 0-100 synthesizing all sources
    """
    try:
        async def _run() -> dict[str, Any]:
            if not person_name or len(person_name) > 200:
                return {
                    "person_name": person_name,
                    "error": "person_name must be 1-200 characters",
                }

            person_name_clean = person_name.strip()
            logger.info("career_trajectory query=%s domain=%s", person_name_clean, domain)

            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=20.0,
            ) as client:
                # Fetch from all sources in parallel
                scholar_task = _search_semantic_scholar(client, person_name_clean)
                github_task = _search_github_user(client, person_name_clean)
                orcid_task = _search_orcid(client, person_name_clean)

                scholar, github, orcid = await asyncio.gather(
                    scholar_task, github_task, orcid_task, return_exceptions=True
                )

                # Handle exceptions from gather
                if isinstance(scholar, Exception):
                    logger.debug("scholar_lookup_exception: %s", scholar)
                    scholar = {}
                if isinstance(github, Exception):
                    logger.debug("github_lookup_exception: %s", github)
                    github = {}
                if isinstance(orcid, Exception):
                    logger.debug("orcid_lookup_exception: %s", orcid)
                    orcid = {}

                # Ensure all are dicts
                scholar = scholar if isinstance(scholar, dict) else {}
                github = github if isinstance(github, dict) else {}
                orcid = orcid if isinstance(orcid, dict) else {}

                # Analyze stages and trajectory
                career_analysis = _analyze_career_stages(scholar, github, orcid)
                trajectory = _determine_trajectory(scholar, github)

                # Calculate impact score
                impact_score = 0.0
                if scholar:
                    h_index = scholar.get("h_index", 0)
                    paper_count = scholar.get("paper_count", 0)
                    impact_score += min(h_index * 2, 30)  # Max 30 for h-index
                    impact_score += min(paper_count * 0.5, 20)  # Max 20 for papers

                if github:
                    repo_count = github.get("repo_count", 0)
                    stars = github.get("total_stars", 0)
                    impact_score += min(repo_count, 15)  # Max 15 for repos
                    impact_score += min(stars / 100, 35)  # Max 35 for stars

                impact_score = min(impact_score, 100)  # Cap at 100

                return {
                    "person_name": person_name_clean,
                    "domain_filter": domain,
                    "academic_publications": {
                        "count": scholar.get("paper_count", 0),
                        "h_index": scholar.get("h_index", 0),
                        "topics": [t[0] for t in scholar.get("topics", [])],
                        "semantic_scholar_id": scholar.get("author_id"),
                    },
                    "github_activity": {
                        "username": github.get("username"),
                        "profile_url": github.get("profile_url"),
                        "repo_count": github.get("repo_count", 0),
                        "total_stars": github.get("total_stars", 0),
                        "primary_languages": [
                            l[0] for l in github.get("languages", [])
                        ],
                        "company": github.get("company"),
                        "location": github.get("location"),
                    },
                    "orcid_profile": {
                        "orcid_id": orcid.get("orcid_id"),
                        "profile_url": orcid.get("profile_url"),
                        "work_count": orcid.get("work_count", 0),
                        "biography": orcid.get("biography"),
                    },
                    "career_stages": career_analysis["stages"],
                    "growth_trajectory": trajectory,
                    "experience_level": career_analysis["estimated_experience_level"],
                    "combined_impact_score": round(impact_score, 1),
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_career_trajectory"}


async def _search_github_trending(
    client: httpx.AsyncClient, skill: str
) -> dict[str, Any]:
    """Search for trending repositories related to skill."""
    url = f"https://api.github.com/search/repositories?q={quote(skill)}&sort=stars&order=desc&per_page=20"
    data = await fetch_json(client, url)

    if data is None or not isinstance(data, dict) or "items" not in data:
        return {}

    items = data.get("items", [])
    total_stars = sum(r.get("stargazers_count", 0) for r in items)
    avg_stars = total_stars / len(items) if items else 0

    # Calculate repo age and creation momentum
    creation_dates: dict[str, int] = {}
    for repo in items:
        created_at = repo.get("created_at", "")
        if created_at:
            month_key = created_at[:7]  # YYYY-MM
            creation_dates[month_key] = creation_dates.get(month_key, 0) + 1

    return {
        "total_count": data.get("total_count", 0),
        "top_repos": len(items),
        "total_stars": total_stars,
        "avg_stars": round(avg_stars, 0),
        "creation_momentum": creation_dates,
    }


async def _search_hacker_news(
    client: httpx.AsyncClient, skill: str
) -> dict[str, Any]:
    """Search HackerNews for discussions about skill."""
    url = f"https://hn.algolia.com/api/v1/search?query={quote(skill)}&tags=story&hitsPerPage=50"
    data = await fetch_json(client, url)

    if data is None or not isinstance(data, dict) or "hits" not in data:
        return {}

    hits = data.get("hits", [])
    return {
        "total_hits": data.get("nbHits", 0),
        "recent_discussions": len(hits),
        "top_stories": [
            {
                "title": h.get("title"),
                "points": h.get("points", 0),
                "num_comments": h.get("num_comments", 0),
            }
            for h in hits[:5]
        ],
    }


async def _search_arxiv_papers(
    client: httpx.AsyncClient, skill: str
) -> dict[str, Any]:
    """Search arXiv for papers mentioning skill."""
    # arXiv API query
    search_query = quote(f"all:{skill}")
    url = f"https://export.arxiv.org/api/query?search_query={search_query}&start=0&max_results=100&sortBy=submittedDate&sortOrder=descending"

    text = await fetch_text(client, url)

    if not text or not isinstance(text, str):
        return {}

    # Parse XML response
    entry_pattern = re.compile(r'<entry>.*?</entry>', re.DOTALL)
    entries = entry_pattern.findall(text)

    # Group by month
    papers_by_month: dict[str, int] = {}
    for entry in entries[:100]:
        # Extract published date
        pub_match = re.search(r'<published>(\d{4}-\d{2})', entry)
        if pub_match:
            month_key = pub_match.group(1)
            papers_by_month[month_key] = papers_by_month.get(month_key, 0) + 1

    total_papers = len(entries)

    return {
        "total_papers": total_papers,
        "papers_by_month": papers_by_month,
        "recent_months": len(papers_by_month),
    }


async def research_market_velocity(skill: str, location: str = "remote") -> dict[str, Any]:
    """Measure how fast a skill/technology is growing in the job market.

    Analyzes GitHub trending repositories, HackerNews discussion frequency,
    and arXiv academic papers to determine market adoption velocity.

    Args:
        skill: Technology/skill name (e.g., "machine learning", "rust", "kubernetes")
        location: Job market location filter - "remote", "silicon-valley", "us", etc.
                 (advisory, not strictly enforced)

    Returns:
        Dict with keys:
        - skill: Input skill name
        - location: Job market location
        - github_momentum: total_stars, avg_stars_per_repo, repo_creation_rate
        - discussion_velocity: hn_recent_discussions, avg_points_per_story
        - academic_momentum: total_papers, papers_per_month (avg), growth_trend
        - overall_velocity: "hot", "warm", "stable", or "cooling"
        - demand_trend: "rapidly_growing", "growing", "stable", or "declining"
        - confidence_score: float 0-100 based on data availability
    """
    try:
        async def _run() -> dict[str, Any]:
            if not skill or len(skill) > 100:
                return {
                    "skill": skill,
                    "error": "skill must be 1-100 characters",
                }

            skill_clean = skill.strip().lower()
            logger.info("market_velocity query=%s location=%s", skill_clean, location)

            async with httpx.AsyncClient(
                follow_redirects=True,
                headers={"User-Agent": "Loom-Research/1.0"},
                timeout=20.0,
            ) as client:
                # Fetch from all sources in parallel
                github_task = _search_github_trending(client, skill_clean)
                hn_task = _search_hacker_news(client, skill_clean)
                arxiv_task = _search_arxiv_papers(client, skill_clean)

                github, hn, arxiv = await asyncio.gather(
                    github_task, hn_task, arxiv_task, return_exceptions=True
                )

                github = github if isinstance(github, dict) else {}
                hn = hn if isinstance(hn, dict) else {}
                arxiv = arxiv if isinstance(arxiv, dict) else {}

                # Calculate momentum metrics
                github_stars = github.get("total_stars", 0)
                github_repos = github.get("top_repos", 0)
                avg_stars = github.get("avg_stars", 0)

                hn_discussions = hn.get("recent_discussions", 0)
                hn_stories = hn.get("top_stories", [])
                avg_hn_points = (
                    sum(s.get("points", 0) for s in hn_stories) / len(hn_stories)
                    if hn_stories
                    else 0
                )

                arxiv_papers = arxiv.get("total_papers", 0)
                papers_by_month = arxiv.get("papers_by_month", {})
                avg_papers_per_month = (
                    arxiv_papers / len(papers_by_month) if papers_by_month else 0
                )

                # Determine velocity
                signals = []

                # GitHub signal
                if github_stars > 5000:
                    signals.append(("hot", 3))
                elif github_stars > 1000:
                    signals.append(("warm", 2))
                elif github_stars > 100:
                    signals.append(("stable", 1))
                else:
                    signals.append(("cooling", 0))

                # HN signal
                if hn_discussions > 30:
                    signals.append(("hot", 3))
                elif hn_discussions > 10:
                    signals.append(("warm", 2))
                elif hn_discussions > 0:
                    signals.append(("stable", 1))
                else:
                    signals.append(("cooling", 0))

                # Academic signal
                if avg_papers_per_month > 2:
                    signals.append(("hot", 3))
                elif avg_papers_per_month > 0.5:
                    signals.append(("warm", 2))
                elif arxiv_papers > 0:
                    signals.append(("stable", 1))
                else:
                    signals.append(("cooling", 0))

                # Determine overall velocity
                if not signals:
                    overall_velocity = "unknown"
                    demand_trend = "unknown"
                    confidence = 0.0
                else:
                    avg_signal = sum(s[1] for s in signals) / len(signals)
                    if avg_signal >= 2.5:
                        overall_velocity = "hot"
                        demand_trend = "rapidly_growing"
                    elif avg_signal >= 1.5:
                        overall_velocity = "warm"
                        demand_trend = "growing"
                    elif avg_signal >= 0.5:
                        overall_velocity = "stable"
                        demand_trend = "stable"
                    else:
                        overall_velocity = "cooling"
                        demand_trend = "declining"

                    # Calculate confidence (0-100)
                    data_points = (
                        (1 if github else 0)
                        + (1 if hn else 0)
                        + (1 if arxiv else 0)
                    )
                    confidence = (data_points / 3) * 100

                return {
                    "skill": skill_clean,
                    "location": location,
                    "github_momentum": {
                        "total_stars": github_stars,
                        "avg_stars_per_repo": round(avg_stars, 0),
                        "top_repos_analyzed": github_repos,
                        "repo_count": github.get("total_count", 0),
                    },
                    "discussion_velocity": {
                        "recent_discussions": hn_discussions,
                        "avg_points_per_story": round(avg_hn_points, 1),
                        "top_stories": hn_stories,
                    },
                    "academic_momentum": {
                        "total_papers": arxiv_papers,
                        "avg_papers_per_month": round(avg_papers_per_month, 2),
                        "months_with_papers": len(papers_by_month),
                    },
                    "overall_velocity": overall_velocity,
                    "demand_trend": demand_trend,
                    "confidence_score": round(confidence, 1),
                }

        return await _run()
    except Exception as exc:
        return {"error": str(exc), "tool": "research_market_velocity"}
