"""research_identity_resolve — Link online identities using only public data."""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.identity_resolve")


def research_identity_resolve(
    email: str = "",
    username: str = "",
    check_gravatar: bool = True,
    check_pgp: bool = True,
    check_github: bool = True,
) -> dict[str, Any]:
    """Link online identities using only public data.

    Cross-platform identity resolver that checks Gravatar, PGP keyservers,
    GitHub, and social media platforms for identity presence and linkage.
    All checks use passive, public data sources.

    Args:
        email: Email address to resolve (optional)
        username: Username to resolve (optional)
        check_gravatar: Check Gravatar profile for email (default: True)
        check_pgp: Check PGP keyserver for email (default: True)
        check_github: Check GitHub for email or username (default: True)

    Returns:
        Dict with:
          - email: input email (if provided)
          - username: input username (if provided)
          - gravatar: {exists, profile_url}
          - pgp: {key_found, key_count}
          - github: {exists, profile} (basic name, bio, repos, followers, created)
          - platforms_found: [{platform, url, exists}]
          - total_platforms_checked: int
          - total_matches: int (across all sources)
          - identity_confidence: "high" | "medium" | "low"
    """
    result: dict[str, Any] = {
        "total_matches": 0,
        "total_platforms_checked": 0,
        "platforms_found": [],
    }

    if email:
        result["email"] = email

    if username:
        result["username"] = username

    match_count = 0

    try:
        with httpx.Client(timeout=10.0) as client:
            # Gravatar check (email only)
            if email and check_gravatar:
                gravatar = _check_gravatar(client, email)
                result["gravatar"] = gravatar
                if gravatar["exists"]:
                    match_count += 1

            # PGP keys check (email only)
            if email and check_pgp:
                pgp = _check_pgp(client, email)
                result["pgp"] = pgp
                if pgp["key_found"]:
                    match_count += 1

            # GitHub check (email or username)
            if check_github and (email or username):
                github = _check_github(client, email, username)
                result["github"] = github
                if github["exists"]:
                    match_count += 1

            # Username enumeration on platforms
            if username:
                platforms = _check_platforms(client, username)
                result["platforms_found"] = [p for p in platforms if p["exists"]]
                result["total_platforms_checked"] = len(platforms)
                # Count platforms found toward total matches
                match_count += len(result["platforms_found"])

    except Exception as e:
        logger.exception("Identity resolve failed: %s", e)
        result["error"] = f"Resolution failed: {type(e).__name__}"
        return result

    # Calculate confidence
    result["total_matches"] = match_count
    if match_count >= 5:
        confidence = "high"
    elif match_count >= 3:
        confidence = "medium"
    elif match_count >= 1:
        confidence = "low"
    else:
        confidence = "none"

    result["identity_confidence"] = confidence

    return result


def _check_gravatar(client: httpx.Client, email: str) -> dict[str, Any]:
    """Check Gravatar profile for email."""
    email_lower = email.lower().strip()
    email_hash = hashlib.md5(email_lower.encode()).hexdigest()
    gravatar_url = f"https://gravatar.com/avatar/{email_hash}?d=404"

    try:
        resp = client.head(gravatar_url, timeout=10.0, follow_redirects=True)
        exists = resp.status_code == 200
    except Exception:
        exists = False

    return {
        "exists": exists,
        "profile_url": gravatar_url if exists else None,
    }


def _check_pgp(client: httpx.Client, email: str) -> dict[str, Any]:
    """Check OpenPGP keyserver for email."""
    try:
        url = f"https://keys.openpgp.org/vks/v1/by-email/{quote(email)}"
        resp = client.get(url, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            keys = data.get("keys", [])
            return {
                "key_found": len(keys) > 0,
                "key_count": len(keys),
            }
    except Exception as e:
        logger.debug("pgp check failed: %s", e)

    return {
        "key_found": False,
        "key_count": 0,
    }


def _check_github(client: httpx.Client, email: str = "", username: str = "") -> dict[str, Any]:
    """Check GitHub for email or username."""
    result: dict[str, Any] = {
        "exists": False,
        "profile": None,
    }

    try:
        # Try username first
        if username:
            url = f"https://api.github.com/users/{username}"
            resp = client.get(url, timeout=15.0)
            if resp.status_code == 200:
                data = resp.json()
                result["exists"] = True
                result["profile"] = {
                    "name": data.get("name") or data.get("login"),
                    "bio": data.get("bio"),
                    "repos": data.get("public_repos", 0),
                    "followers": data.get("followers", 0),
                    "created": data.get("created_at"),
                }
                return result

        # Try email search
        if email:
            url = f"https://api.github.com/search/users?q={quote(email)}+in:email"
            resp = client.get(url, timeout=15.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("total_count", 0) > 0:
                    # Found user by email
                    result["exists"] = True
                    items = data.get("items", [])
                    if items:
                        user = items[0]
                        result["profile"] = {
                            "name": user.get("login"),
                            "bio": None,
                            "repos": user.get("public_repos", 0),
                            "followers": user.get("followers", 0),
                            "created": user.get("created_at"),
                        }

    except Exception as e:
        logger.debug("github check failed: %s", e)

    return result


def _check_platforms(client: httpx.Client, username: str) -> list[dict[str, Any]]:
    """Check username existence on common platforms via HEAD requests."""
    platforms = [
        ("GitHub", f"https://github.com/{username}"),
        ("Twitter/X", f"https://x.com/{username}"),
        ("Reddit", f"https://www.reddit.com/user/{username}"),
        ("HackerNews", f"https://news.ycombinator.com/user?id={username}"),
        ("GitLab", f"https://gitlab.com/{username}"),
        ("Keybase", f"https://keybase.io/{username}"),
        ("LinkedIn", f"https://linkedin.com/in/{username}"),
        ("Instagram", f"https://instagram.com/{username}"),
    ]

    results: list[dict[str, Any]] = []

    for platform_name, url in platforms:
        exists = False
        try:
            resp = client.head(url, timeout=10.0, follow_redirects=True)
            exists = resp.status_code == 200
        except Exception:
            pass

        results.append(
            {
                "platform": platform_name,
                "url": url,
                "exists": exists,
            }
        )

    return results
