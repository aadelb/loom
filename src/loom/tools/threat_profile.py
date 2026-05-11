"""Threat actor profiler — build profiles from public OSINT data."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.threat_profile")

_PLATFORMS = [
    ("github", "https://github.com/{username}"),
    ("reddit", "https://www.reddit.com/user/{username}"),
    ("hackernews", "https://news.ycombinator.com/user?id={username}"),
    ("gitlab", "https://gitlab.com/{username}"),
    ("keybase", "https://keybase.io/{username}"),
    ("medium", "https://medium.com/@{username}"),
    ("dev_to", "https://dev.to/{username}"),
    ("twitter", "https://x.com/{username}"),
    ("instagram", "https://www.instagram.com/{username}/"),
    ("linkedin", "https://www.linkedin.com/in/{username}"),
    ("pinterest", "https://www.pinterest.com/{username}/"),
    ("telegram", "https://t.me/{username}"),
    ("mastodon", "https://mastodon.social/@{username}"),
    ("youtube", "https://www.youtube.com/@{username}"),
    ("tiktok", "https://www.tiktok.com/@{username}"),
]

_PGP_KEYSERVER = "https://keys.openpgp.org/vks/v1/by-email/{email}"
_GRAVATAR = "https://gravatar.com/avatar/{hash}?d=404"
_GITHUB_USER = "https://api.github.com/users/{username}"
_HN_USER = "https://hacker-news.firebaseio.com/v0/user/{username}.json"


async def _check_platform(
    client: httpx.AsyncClient, platform: str, url: str
) -> dict[str, Any] | None:
    try:
        resp = await client.head(url, timeout=10.0, follow_redirects=True)
        if resp.status_code == 200:
            return {"platform": platform, "url": url, "exists": True}
    except Exception:
        pass
    return None


async def _check_gravatar(client: httpx.AsyncClient, email: str) -> dict[str, Any]:
    email_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()
    try:
        resp = await client.head(
            _GRAVATAR.format(hash=email_hash), timeout=10.0
        )
        return {
            "exists": resp.status_code == 200,
            "url": f"https://gravatar.com/avatar/{email_hash}",
        }
    except Exception:
        return {"exists": False, "url": ""}


async def _check_pgp(client: httpx.AsyncClient, email: str) -> list[dict[str, str]]:
    try:
        resp = await client.get(
            _PGP_KEYSERVER.format(email=quote(email)), timeout=10.0
        )
        if resp.status_code == 200:
            return [{"source": "openpgp", "email": email, "key_found": "true"}]
    except Exception:
        pass
    return []


async def _github_profile(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    try:
        resp = await client.get(
            _GITHUB_USER.format(username=username), timeout=10.0
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "name": data.get("name", ""),
                "bio": data.get("bio", ""),
                "location": data.get("location", ""),
                "company": data.get("company", ""),
                "blog": data.get("blog", ""),
                "public_repos": data.get("public_repos", 0),
                "followers": data.get("followers", 0),
                "created_at": data.get("created_at", ""),
            }
    except Exception:
        pass
    return {}


async def _hn_profile(client: httpx.AsyncClient, username: str) -> dict[str, Any]:
    data = None
    try:
        resp = await client.get(
            _HN_USER.format(username=username), timeout=10.0
        )
        if resp.status_code == 200:
            data = resp.json()
    except Exception:
        pass
    if not data:
        return {}
    return {
        "karma": data.get("karma", 0),
        "about": data.get("about", "")[:300],
        "created": data.get("created", 0),
        "submitted_count": len(data.get("submitted", [])),
    }


def _infer_timezone(created_timestamps: list[int]) -> str:
    if not created_timestamps:
        return "unknown"
    hours = [((ts % 86400) // 3600) for ts in created_timestamps]
    if not hours:
        return "unknown"
    avg_hour = sum(hours) / len(hours)
    if 6 <= avg_hour <= 18:
        return "likely_UTC_or_Americas"
    return "likely_Asia_or_Europe"


async def research_threat_profile(
    username: str,
    email: str = "",
    check_platforms: bool = True,
    max_platforms: int = 15,
) -> dict[str, Any]:
    """Build a profile of an online identity from public OSINT sources.

    Checks username existence across 15+ platforms, Gravatar and PGP
    key presence for email, GitHub and HackerNews profile data,
    and infers timezone from activity patterns.

    Args:
        username: username/handle to investigate
        email: optional email address for additional checks
        check_platforms: check username on 15+ platforms
        max_platforms: max platforms to check

    Returns:
        Dict with ``username``, ``platforms_found``, ``gravatar``,
        ``pgp_keys``, ``github_profile``, ``hn_profile``,
        ``inferred_timezone``, and ``total_presence``.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
            timeout=30.0,
        ) as client:
            tasks: list[Any] = []

            if check_platforms:
                for platform, url_tpl in _PLATFORMS[:max_platforms]:
                    url = url_tpl.format(username=username)
                    tasks.append(_check_platform(client, platform, url))

            github_task = _github_profile(client, username)
            hn_task = _hn_profile(client, username)

            gravatar_task = _check_gravatar(client, email) if email else None
            pgp_task = _check_pgp(client, email) if email else None

            platform_results = await asyncio.gather(*tasks, return_exceptions=True)
            gh_data, hn_data = await asyncio.gather(github_task, hn_task)

            gravatar_data: dict[str, Any] = {}
            pgp_data: list[dict[str, str]] = []
            if gravatar_task:
                gravatar_data = await gravatar_task
            if pgp_task:
                pgp_data = await pgp_task

            platforms_found: list[dict[str, Any]] = []
            for result in platform_results:
                if isinstance(result, dict) and result.get("exists"):
                    platforms_found.append(result)

            timestamps = []
            if hn_data.get("created"):
                timestamps.append(hn_data["created"])

            return {
                "username": username,
                "email": email,
                "platforms_found": platforms_found,
                "platforms_checked": min(len(_PLATFORMS), max_platforms),
                "total_presence": len(platforms_found),
                "gravatar": gravatar_data,
                "pgp_keys": pgp_data,
                "github_profile": gh_data,
                "hn_profile": hn_data,
                "inferred_timezone": _infer_timezone(timestamps),
            }

    return await _run()
