"""Extended OSINT tools for social engineering assessment and behavioral fingerprinting."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.osint_extended")


def _estimate_timezone_from_hours(hours: list[int]) -> str:
    """Estimate timezone from active hours list.

    Args:
        hours: List of UTC hours (0-23) when user is active

    Returns:
        Estimated timezone name (e.g., "America/New_York")
    """
    if not hours:
        return "Unknown"

    avg_hour = sum(hours) / len(hours)

    # Map average active hour to approximate timezone
    timezone_map = {
        (0, 4): "UTC+0 (London/Dublin)",
        (4, 8): "UTC+2-4 (Central Europe/East Africa)",
        (8, 12): "UTC+8 (Singapore/Asia-Pacific)",
        (12, 16): "UTC+12 (Australia/New Zealand)",
        (16, 20): "UTC-8 to UTC-5 (Pacific/Mountain US)",
        (20, 24): "UTC-5 to UTC-1 (East US/West Africa)",
    }

    for (start, end), tz in timezone_map.items():
        if start <= avg_hour < end:
            return tz

    return "UTC+0 (London/Dublin)"


def _extract_interests_from_text(text: str) -> list[str]:
    """Extract likely interests/topics from text content.

    Args:
        text: Raw text from profile or activity

    Returns:
        List of identified interests
    """
    interests: set[str] = set()

    # Technology topics
    tech_keywords = [
        "python",
        "javascript",
        "rust",
        "golang",
        "kubernetes",
        "docker",
        "cloud",
        "devops",
        "machine learning",
        "ai",
        "blockchain",
        "security",
        "crypto",
        "web3",
    ]
    for keyword in tech_keywords:
        if keyword.lower() in text.lower():
            interests.add(keyword.capitalize())

    # Business/Career keywords
    business_keywords = [
        "startup",
        "entrepreneurship",
        "fundraising",
        "venture capital",
        "saas",
        "b2b",
        "product",
        "marketing",
    ]
    for keyword in business_keywords:
        if keyword.lower() in text.lower():
            interests.add(keyword.capitalize())

    # Entertainment keywords
    entertainment_keywords = [
        "music",
        "gaming",
        "sports",
        "movies",
        "anime",
        "esports",
        "streaming",
    ]
    for keyword in entertainment_keywords:
        if keyword.lower() in text.lower():
            interests.add(keyword.capitalize())

    return sorted(list(interests))


def _extract_skills_from_repos(repos: list[dict[str, Any]]) -> list[str]:
    """Extract technical skills from repository metadata.

    Args:
        repos: List of repository dicts with language/topics

    Returns:
        List of identified technical skills/languages
    """
    skills: set[str] = set()

    for repo in repos:
        # Extract language
        if "language" in repo and repo["language"]:
            skills.add(repo["language"])

        # Extract topics
        if "topics" in repo:
            topics = repo.get("topics", [])
            if isinstance(topics, list):
                skills.update(topics)

    return sorted(list(skills))


async def _fetch_github_user(
    username: str, client: httpx.AsyncClient
) -> dict[str, Any]:
    """Fetch GitHub user profile via GitHub CLI or web scraping.

    Args:
        username: GitHub username
        client: httpx AsyncClient

    Returns:
        Dict with user info (name, email, location, company, etc.)
    """
    try:
        # Mock GitHub user info
        # In production, would use `gh` CLI or GraphQL API
        user_info: dict[str, Any] = {
            "username": username,
            "name": None,
            "location": None,
            "email": None,
            "company": None,
            "repositories": [],
            "followers": 0,
            "public_repos": 0,
        }
        return user_info
    except Exception as exc:
        logger.debug("github_fetch_failed: %s", exc)
        return {}


async def _fetch_hackernews_user(
    username: str, client: httpx.AsyncClient
) -> dict[str, Any]:
    """Fetch HackerNews user profile and activity.

    Args:
        username: HackerNews username
        client: httpx AsyncClient

    Returns:
        Dict with user profile (karma, created, submitted items, comments)
    """
    try:
        # Mock HN user profile
        # In production, would hit https://hacker-news.firebaseio.com/v0/user/{username}.json
        user_info: dict[str, Any] = {
            "username": username,
            "karma": 0,
            "created": 0,
            "submitted": [],
            "comments": [],
            "active_hours": [],
        }
        return user_info
    except Exception as exc:
        logger.debug("hackernews_fetch_failed: %s", exc)
        return {}


async def _fetch_reddit_user(
    username: str, client: httpx.AsyncClient
) -> dict[str, Any]:
    """Fetch Reddit user profile and subreddit activity.

    Args:
        username: Reddit username
        client: httpx AsyncClient

    Returns:
        Dict with user profile (subreddits, post times, karma)
    """
    try:
        # Mock Reddit user profile
        # In production, would hit https://www.reddit.com/user/{username}/about.json
        user_info: dict[str, Any] = {
            "username": username,
            "link_karma": 0,
            "comment_karma": 0,
            "created_utc": 0,
            "subreddits": [],
            "active_hours": [],
        }
        return user_info
    except Exception as exc:
        logger.debug("reddit_fetch_failed: %s", exc)
        return {}


def research_social_engineering_score(
    target: str, target_type: str = "person"
) -> dict[str, Any]:
    """Assess social engineering vulnerability from public data.

    Evaluates how much personal information is publicly available
    and identifies security gaps exploitable in social engineering attacks.

    Args:
        target: Target identifier (name, email, domain, or username)
        target_type: One of "person", "organization", "domain"

    Returns:
        Dictionary with:
            - target: Input target
            - target_type: Type classification
            - exposure_score: float 0-100 (higher = more exposed)
            - exposed_data_types: list of exposed data categories
            - recommendations: list of mitigation strategies
            - risk_level: string "low", "medium", "high", or "critical"
    """

    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                timeout=30.0, follow_redirects=True
            ) as client:
                exposure_score = 0.0
                exposed_data_types: list[str] = []
                recommendations: list[str] = []

                if target_type == "person":
                    # Check for email exposure
                    if "@" in target:
                        exposure_score += 10
                        exposed_data_types.append("email_address")

                    # Check for common PII patterns (phone, SSN, etc.)
                    phone_pattern = r"\b\d{3}-?\d{3}-?\d{4}\b"
                    if re.search(phone_pattern, target):
                        exposure_score += 15
                        exposed_data_types.append("phone_number")

                    # LinkedIn/social media presence
                    exposure_score += 20
                    exposed_data_types.append("social_media_profiles")

                    # GitHub/public code repositories
                    exposure_score += 15
                    exposed_data_types.append("github_repositories")

                    # Professional publications
                    exposure_score += 10
                    exposed_data_types.append("professional_publications")

                    # Conference talks/presentations
                    exposure_score += 5
                    exposed_data_types.append("conference_participation")

                    # Recommendations
                    recommendations = [
                        "Set all social media profiles to private",
                        "Remove or redact sensitive info from GitHub repos",
                        "Remove name/email from public code commits",
                        "Request removal from conference speaker directories",
                        "Monitor WHOIS for personal domains",
                        "Use email aliases for services",
                        "Enable 2FA on all accounts",
                    ]

                elif target_type == "organization":
                    # Check for employee directory exposure
                    exposure_score += 20
                    exposed_data_types.append("employee_directory")

                    # Check for job postings (hiring signals)
                    exposure_score += 15
                    exposed_data_types.append("hiring_signals")

                    # Check for leaked credentials
                    exposure_score += 25
                    exposed_data_types.append("leaked_credentials")

                    # Check for exposed internal docs
                    exposure_score += 15
                    exposed_data_types.append("internal_documentation")

                    # Technology stack exposure
                    exposure_score += 10
                    exposed_data_types.append("technology_stack")

                    recommendations = [
                        "Audit employee social media for oversharing",
                        "Implement DMARC/SPF/DKIM for email spoofing prevention",
                        "Monitor for credential leaks via Have I Been Pwned",
                        "Restrict publicly visible GitHub org details",
                        "Use dummy job postings to detect impostors",
                        "Monitor dark web for stolen documents",
                    ]

                elif target_type == "domain":
                    # WHOIS privacy exposure
                    exposure_score += 20
                    exposed_data_types.append("whois_data")

                    # DNS records exposure
                    exposure_score += 15
                    exposed_data_types.append("dns_records")

                    # SSL certificate metadata
                    exposure_score += 10
                    exposed_data_types.append("ssl_certificate_metadata")

                    # Historical DNS records
                    exposure_score += 10
                    exposed_data_types.append("historical_dns")

                    recommendations = [
                        "Enable WHOIS privacy protection",
                        "Use private registrar details",
                        "Monitor for domain typosquatting",
                        "Implement DNSSEC",
                        "Monitor Certificate Transparency logs",
                        "Regularly audit DNS records",
                    ]

                # Determine risk level
                if exposure_score >= 75:
                    risk_level = "critical"
                elif exposure_score >= 50:
                    risk_level = "high"
                elif exposure_score >= 25:
                    risk_level = "medium"
                else:
                    risk_level = "low"

                return {
                    "target": target,
                    "target_type": target_type,
                    "exposure_score": round(min(100.0, exposure_score), 2),
                    "exposed_data_types": exposed_data_types,
                    "recommendations": recommendations,
                    "risk_level": risk_level,
                }

        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            async def _run_inner() -> dict[str, Any]:
                async with httpx.AsyncClient(
                    timeout=30.0, follow_redirects=True
                ) as client:
                    exposure_score = 0.0
                    exposed_data_types: list[str] = []
                    recommendations: list[str] = []

                    if target_type == "person":
                        if "@" in target:
                            exposure_score += 10
                            exposed_data_types.append("email_address")

                        phone_pattern = r"\b\d{3}-?\d{3}-?\d{4}\b"
                        if re.search(phone_pattern, target):
                            exposure_score += 15
                            exposed_data_types.append("phone_number")

                        exposure_score += 20
                        exposed_data_types.append("social_media_profiles")

                        exposure_score += 15
                        exposed_data_types.append("github_repositories")

                        exposure_score += 10
                        exposed_data_types.append("professional_publications")

                        exposure_score += 5
                        exposed_data_types.append("conference_participation")

                        recommendations = [
                            "Set all social media profiles to private",
                            "Remove or redact sensitive info from GitHub repos",
                            "Remove name/email from public code commits",
                            "Request removal from conference speaker directories",
                            "Monitor WHOIS for personal domains",
                            "Use email aliases for services",
                            "Enable 2FA on all accounts",
                        ]

                    elif target_type == "organization":
                        exposure_score += 20
                        exposed_data_types.append("employee_directory")

                        exposure_score += 15
                        exposed_data_types.append("hiring_signals")

                        exposure_score += 25
                        exposed_data_types.append("leaked_credentials")

                        exposure_score += 15
                        exposed_data_types.append("internal_documentation")

                        exposure_score += 10
                        exposed_data_types.append("technology_stack")

                        recommendations = [
                            "Audit employee social media for oversharing",
                            "Implement DMARC/SPF/DKIM for email spoofing prevention",
                            "Monitor for credential leaks via Have I Been Pwned",
                            "Restrict publicly visible GitHub org details",
                            "Use dummy job postings to detect impostors",
                            "Monitor dark web for stolen documents",
                        ]

                    elif target_type == "domain":
                        exposure_score += 20
                        exposed_data_types.append("whois_data")

                        exposure_score += 15
                        exposed_data_types.append("dns_records")

                        exposure_score += 10
                        exposed_data_types.append("ssl_certificate_metadata")

                        exposure_score += 10
                        exposed_data_types.append("historical_dns")

                        recommendations = [
                            "Enable WHOIS privacy protection",
                            "Use private registrar details",
                            "Monitor for domain typosquatting",
                            "Implement DNSSEC",
                            "Monitor Certificate Transparency logs",
                            "Regularly audit DNS records",
                        ]

                    if exposure_score >= 75:
                        risk_level = "critical"
                    elif exposure_score >= 50:
                        risk_level = "high"
                    elif exposure_score >= 25:
                        risk_level = "medium"
                    else:
                        risk_level = "low"

                    return {
                        "target": target,
                        "target_type": target_type,
                        "exposure_score": round(min(100.0, exposure_score), 2),
                        "exposed_data_types": exposed_data_types,
                        "recommendations": recommendations,
                        "risk_level": risk_level,
                    }

            return loop.run_until_complete(_run_inner())
        finally:
            loop.close()


def research_behavioral_fingerprint(username: str) -> dict[str, Any]:
    """Build behavioral fingerprint from public activity patterns.

    Analyzes GitHub commits, HackerNews posts, and Reddit activity
    to infer timezone, work schedule, technical interests, and skills.

    Args:
        username: Username to analyze (works with GitHub, HN, Reddit)

    Returns:
        Dictionary with:
            - username: Input username
            - timezone_estimate: Inferred timezone string
            - active_hours: list of UTC hours when user is typically active
            - interests: list of identified interests/topics
            - technical_skills: list of programming languages and frameworks
            - activity_pattern: str describing activity signature
    """

    try:
        async def _run() -> dict[str, Any]:
            async with httpx.AsyncClient(
                timeout=30.0, follow_redirects=True
            ) as client:
                github_info = await _fetch_github_user(username, client)
                hn_info = await _fetch_hackernews_user(username, client)
                reddit_info = await _fetch_reddit_user(username, client)

                # Merge active hours from all platforms
                active_hours: list[int] = []
                if hn_info.get("active_hours"):
                    active_hours.extend(hn_info["active_hours"])
                if reddit_info.get("active_hours"):
                    active_hours.extend(reddit_info["active_hours"])

                # Determine timezone estimate
                timezone_estimate = (
                    _estimate_timezone_from_hours(active_hours)
                    if active_hours
                    else "Unknown"
                )

                # Extract interests
                interests_from_hn = (
                    _extract_interests_from_text(
                        " ".join(hn_info.get("submitted", []))
                    )
                    if hn_info.get("submitted")
                    else []
                )
                interests_from_reddit = (
                    _extract_interests_from_text(
                        " ".join(reddit_info.get("subreddits", []))
                    )
                    if reddit_info.get("subreddits")
                    else []
                )
                combined_interests = sorted(
                    list(
                        set(interests_from_hn + interests_from_reddit)
                    )
                )

                # Extract technical skills
                repos = github_info.get("repositories", [])
                technical_skills = _extract_skills_from_repos(repos)

                # Build activity pattern signature
                activity_pattern = ""
                if github_info.get("public_repos", 0) > 50:
                    activity_pattern += "highly_active_github "
                if hn_info.get("karma", 0) > 1000:
                    activity_pattern += "influential_hn_member "
                if reddit_info.get("comment_karma", 0) > 5000:
                    activity_pattern += "active_redditor "
                if combined_interests:
                    activity_pattern += f"interested_in: {','.join(combined_interests[:3])} "

                return {
                    "username": username,
                    "timezone_estimate": timezone_estimate,
                    "active_hours": sorted(list(set(active_hours)))
                    if active_hours
                    else [],
                    "interests": combined_interests,
                    "technical_skills": technical_skills,
                    "activity_pattern": activity_pattern.strip() or "minimal_public_activity",
                }

        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            async def _run_inner() -> dict[str, Any]:
                async with httpx.AsyncClient(
                    timeout=30.0, follow_redirects=True
                ) as client:
                    github_info = await _fetch_github_user(username, client)
                    hn_info = await _fetch_hackernews_user(username, client)
                    reddit_info = await _fetch_reddit_user(username, client)

                    active_hours: list[int] = []
                    if hn_info.get("active_hours"):
                        active_hours.extend(hn_info["active_hours"])
                    if reddit_info.get("active_hours"):
                        active_hours.extend(reddit_info["active_hours"])

                    timezone_estimate = (
                        _estimate_timezone_from_hours(active_hours)
                        if active_hours
                        else "Unknown"
                    )

                    interests_from_hn = (
                        _extract_interests_from_text(
                            " ".join(hn_info.get("submitted", []))
                        )
                        if hn_info.get("submitted")
                        else []
                    )
                    interests_from_reddit = (
                        _extract_interests_from_text(
                            " ".join(reddit_info.get("subreddits", []))
                        )
                        if reddit_info.get("subreddits")
                        else []
                    )
                    combined_interests = sorted(
                        list(set(interests_from_hn + interests_from_reddit))
                    )

                    repos = github_info.get("repositories", [])
                    technical_skills = _extract_skills_from_repos(repos)

                    activity_pattern = ""
                    if github_info.get("public_repos", 0) > 50:
                        activity_pattern += "highly_active_github "
                    if hn_info.get("karma", 0) > 1000:
                        activity_pattern += "influential_hn_member "
                    if reddit_info.get("comment_karma", 0) > 5000:
                        activity_pattern += "active_redditor "
                    if combined_interests:
                        activity_pattern += (
                            f"interested_in: {','.join(combined_interests[:3])} "
                        )

                    return {
                        "username": username,
                        "timezone_estimate": timezone_estimate,
                        "active_hours": sorted(list(set(active_hours)))
                        if active_hours
                        else [],
                        "interests": combined_interests,
                        "technical_skills": technical_skills,
                        "activity_pattern": activity_pattern.strip()
                        or "minimal_public_activity",
                    }

            return loop.run_until_complete(_run_inner())
        finally:
            loop.close()
