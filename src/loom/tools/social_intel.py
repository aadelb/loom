"""Social media intelligence tools — profile discovery and verification."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import httpx

from loom.validators import validate_url

logger = logging.getLogger("loom.tools.social_intel")

_HTTP_TIMEOUT = 10.0

# Platform URL patterns
PLATFORM_PATTERNS: dict[str, str] = {
    "github": "https://github.com/{username}",
    "twitter": "https://x.com/{username}",
    "reddit": "https://www.reddit.com/user/{username}",
    "hackernews": "https://news.ycombinator.com/user?id={username}",
    "linkedin": "https://www.linkedin.com/in/{username}",
    "medium": "https://medium.com/@{username}",
    "dev.to": "https://dev.to/{username}",
    "keybase": "https://keybase.io/{username}",
}

# Username validation: alphanumeric, underscore, hyphen
_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_username(username: str) -> bool:
    """Validate that username contains only safe characters.

    Args:
        username: Username to validate

    Returns:
        True if valid, False otherwise.
    """
    if not username or len(username) < 1 or len(username) > 255:
        return False
    return bool(_USERNAME_PATTERN.match(username))


async def _check_profile_exists(username: str, platform: str, url: str) -> tuple[str, str, str]:
    """Check if a profile exists at a given URL (non-blocking).

    Args:
        username: Username being checked
        platform: Platform name
        url: Full profile URL

    Returns:
        Tuple of (platform, status, url) where status is "exists", "not_found", or "unknown".
    """
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, follow_redirects=False) as client:
            resp = await client.head(url, headers={"User-Agent": "Mozilla/5.0"})

            if resp.status_code == 200:
                return (platform, "exists", url)
            elif resp.status_code == 404:
                return (platform, "not_found", url)
            else:
                # Try GET as fallback for HEAD-rejecting servers
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    return (platform, "exists", url)
                elif resp.status_code == 404:
                    return (platform, "not_found", url)
                else:
                    return (platform, "unknown", url)
    except TimeoutError:
        logger.debug("profile_check_timeout platform=%s username=%s", platform, username)
        return (platform, "unknown", url)
    except Exception as e:
        logger.debug("profile_check_error platform=%s username=%s error=%s", platform, username, e)
        return (platform, "unknown", url)


async def research_social_search(
    username: str,
    platforms: list[str] | None = None,
) -> dict[str, Any]:
    """Check if a username exists across social media platforms.

    Validates the username and checks HTTP 200 vs 404 on profile URLs.
    Does NOT scrape content — only checks existence.

    Args:
        username: Username to search for
        platforms: List of platform names to check. Defaults to all supported platforms.

    Returns:
        Dict with ``username``, ``platforms_checked``, ``found`` (list), ``not_found`` (list),
        ``unknown`` (list), ``total_found``.
    """
    # Validate username
    if not _validate_username(username):
        return {
            "username": username,
            "platforms_checked": 0,
            "found": [],
            "not_found": [],
            "unknown": [],
            "total_found": 0,
            "error": "invalid username: must be alphanumeric, underscore, or hyphen (1-255 chars)",
        }

    # Determine which platforms to check
    platforms_to_check = platforms or list(PLATFORM_PATTERNS.keys())

    # Filter to known platforms
    unknown_platforms = [p for p in platforms_to_check if p not in PLATFORM_PATTERNS]
    if unknown_platforms:
        logger.warning("unknown_platforms username=%s platforms=%s", username, unknown_platforms)

    platforms_to_check = [p for p in platforms_to_check if p in PLATFORM_PATTERNS]

    if not platforms_to_check:
        return {
            "username": username,
            "platforms_checked": 0,
            "found": [],
            "not_found": [],
            "unknown": [],
            "total_found": 0,
            "error": "no valid platforms specified",
        }

    # Build URLs for each platform
    check_tasks: list[tuple[str, str, str]] = []
    for platform in platforms_to_check:
        url_template = PLATFORM_PATTERNS[platform]
        url = url_template.format(username=username)
        check_tasks.append((username, platform, url))

    # Run checks concurrently
    found: list[dict[str, str]] = []
    not_found: list[str] = []
    unknown: list[str] = []

    # Execute checks directly without asyncio.run (we're already in async context)
    tasks = [_check_profile_exists(u, p, url) for u, p, url in check_tasks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.error("social_search_exception: %s", result)
            continue

        platform, status, url = result
        if status == "exists":
            found.append({"platform": platform, "url": url, "status": "exists"})
        elif status == "not_found":
            not_found.append(platform)
        else:
            unknown.append(platform)

    logger.info(
        "social_search completed username=%s platforms_checked=%d found=%d not_found=%d unknown=%d",
        username,
        len(platforms_to_check),
        len(found),
        len(not_found),
        len(unknown),
    )

    return {
        "username": username,
        "platforms_checked": len(platforms_to_check),
        "found": found,
        "not_found": not_found,
        "unknown": unknown,
        "total_found": len(found),
    }


async def research_social_profile(url: str) -> dict[str, Any]:
    """Extract public profile metadata from a social media URL.

    Fetches the page and extracts Open Graph metadata (og:title, og:description, og:image).
    Detects platform from URL structure.

    Args:
        url: Social media profile URL

    Returns:
        Dict with ``url``, ``platform`` (detected), ``name``, ``bio``, ``avatar_url``, ``metadata``.
    """
    # Validate URL
    try:
        url = validate_url(url)
    except ValueError as e:
        logger.warning("invalid_profile_url url=%s error=%s", url, e)
        return {
            "url": url,
            "platform": "unknown",
            "name": None,
            "bio": None,
            "avatar_url": None,
            "metadata": {},
            "error": str(e),
        }

    # Detect platform from URL
    platform = _detect_platform(url)

    # Fetch page
    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            html = resp.text
    except Exception as e:
        logger.warning("profile_fetch_failed url=%s error=%s", url, e)
        return {
            "url": url,
            "platform": platform,
            "name": None,
            "bio": None,
            "avatar_url": None,
            "metadata": {},
            "error": str(e),
        }

    # Extract Open Graph metadata
    metadata = _extract_og_metadata(html)

    name = metadata.get("og:title")
    bio = metadata.get("og:description")
    avatar_url = metadata.get("og:image")

    logger.info(
        "profile_extracted url=%s platform=%s name=%s",
        url,
        platform,
        name or "unknown",
    )

    return {
        "url": url,
        "platform": platform,
        "name": name,
        "bio": bio,
        "avatar_url": avatar_url,
        "metadata": metadata,
    }


def _detect_platform(url: str) -> str:
    """Detect social platform from URL.

    Args:
        url: Profile URL

    Returns:
        Platform name (e.g. "github", "twitter") or "unknown".
    """
    url_lower = url.lower()
    if "github.com" in url_lower:
        return "github"
    elif "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    elif "reddit.com" in url_lower:
        return "reddit"
    elif "linkedin.com" in url_lower:
        return "linkedin"
    elif "medium.com" in url_lower:
        return "medium"
    elif "dev.to" in url_lower:
        return "dev.to"
    elif "keybase.io" in url_lower:
        return "keybase"
    elif "ycombinator.com" in url_lower:
        return "hackernews"
    return "unknown"


def _extract_og_metadata(html: str) -> dict[str, str]:
    """Extract Open Graph metadata from HTML.

    Args:
        html: HTML page content

    Returns:
        Dict of og:* metadata (og:title, og:description, og:image, etc.).
    """
    metadata = {}
    import re

    # Match both property and name attributes
    # <meta property="og:title" content="..."> or <meta name="og:title" content="...">
    pattern = r'<meta\s+(?:property|name)="(og:[^"]+)"\s+content="([^"]+)"'
    for match in re.finditer(pattern, html, re.IGNORECASE):
        key, value = match.groups()
        metadata[key] = value

    return metadata
