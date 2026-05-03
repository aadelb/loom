"""research_identity_resolve — Link online identities using only public data."""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.identity_resolve")

# Domain validation: lowercase alphanumeric, hyphens, dots; TLD required
_DOMAIN_RE = re.compile(
    r"^[a-z0-9]([a-z0-9\-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]*[a-z0-9])?)*\.[a-z]{2,}$"
)

# Username validation: alphanumeric, dots, underscores, hyphens; 1-100 chars
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{1,100}$")


def _validate_domain(domain: str) -> None:
    """Validate domain format to prevent SSRF/DNS injection attacks.

    Args:
        domain: Domain to validate

    Raises:
        ValueError: If domain format is invalid
    """
    if not domain or not isinstance(domain, str):
        raise ValueError("Domain must be a non-empty string")

    normalized = domain.lower().strip()
    if not _DOMAIN_RE.match(normalized):
        raise ValueError(
            f"Invalid domain format: {domain}. Must be lowercase alphanumeric "
            "with hyphens and dots; TLD required."
        )


def _validate_username(username: str) -> None:
    """Validate username format to prevent URL injection attacks.

    Args:
        username: Username to validate

    Raises:
        ValueError: If username format is invalid
    """
    if not username or not isinstance(username, str):
        raise ValueError("Username must be a non-empty string")

    if not _USERNAME_RE.match(username):
        raise ValueError(
            f"Invalid username format: {username}. Must be 1-100 characters; "
            "alphanumeric, dots, underscores, and hyphens only."
        )


async def research_identity_resolve(
    query: str = "",
    query_type: str = "email",
    check_gravatar: bool = True,
    check_pgp: bool = True,
    check_github: bool = True,
) -> dict[str, Any]:
    """Link online identities using only public data.

    Cross-platform identity resolver that checks Gravatar, PGP keyservers,
    GitHub, and social media platforms for identity presence and linkage.
    All checks use passive, public data sources.

    Args:
        query: Query string (email or username)
        query_type: Type of query - "email", "username", or "domain" (default: "email")
        check_gravatar: Check Gravatar profile for email (default: True)
        check_pgp: Check PGP keyserver for email (default: True)
        check_github: Check GitHub for email or username (default: True)

    Returns:
        Dict with results based on query_type.
    """
    result: dict[str, Any] = {
        "query": query,
        "query_type": query_type,
    }

    if not query or not query.strip():
        # Add default fields for empty query
        if query_type == "email":
            result["gravatar"] = {"exists": False, "url": None, "hash": ""}
            result["pgp_keys"] = []
            result["pgp_keys_count"] = 0
            result["github_commits"] = 0
        elif query_type == "username":
            result["platforms_checked"] = 0
            result["platforms_found_count"] = 0
            result["platforms_found"] = []
            result["all_platforms"] = []
        elif query_type == "domain":
            result["whois_registrant"] = {"name": "", "organization": ""}
            result["dns_soa_email"] = ""
        return result

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if query_type == "email":
                # Email-based checks
                if check_gravatar:
                    gravatar = await _check_gravatar(client, query)
                    result["gravatar"] = gravatar
                else:
                    result["gravatar"] = {"exists": False, "url": None, "hash": ""}

                if check_pgp:
                    pgp = await _check_pgp(client, query)
                    result["pgp_keys"] = pgp.get("keys", [])
                    result["pgp_keys_count"] = pgp.get("key_count", 0)
                else:
                    result["pgp_keys"] = []
                    result["pgp_keys_count"] = 0

                if check_github:
                    github = await _check_github_commits(client, query)
                    result["github_commits"] = github.get("commit_count", 0)
                else:
                    result["github_commits"] = 0

            elif query_type == "username":
                # Username-based checks
                _validate_username(query)  # Validate before platform checks
                platforms = await _check_platforms(client, query)
                result["platforms_checked"] = len(platforms)
                result["platforms_found"] = [p for p in platforms if p["exists"]]
                result["platforms_found_count"] = len(result["platforms_found"])
                result["all_platforms"] = platforms

            elif query_type == "domain":
                # Domain-based checks
                _validate_domain(query)  # Validate before WHOIS/DNS lookups
                whois = await _check_whois(client, query)
                result["whois_registrant"] = whois

                dns_soa = await _check_dns_soa(client, query)
                result["dns_soa_email"] = dns_soa

    except ValueError as e:
        # Validation error (invalid domain/username format)
        logger.warning("Identity resolve validation error: %s", e)
        result["error"] = f"Validation error: {str(e)}"
        # Ensure default fields are present even on error
        if query_type == "email":
            result["gravatar"] = result.get("gravatar", {"exists": False, "url": None, "hash": ""})
            result["pgp_keys"] = result.get("pgp_keys", [])
            result["pgp_keys_count"] = result.get("pgp_keys_count", 0)
            result["github_commits"] = result.get("github_commits", 0)
        elif query_type == "username":
            result["platforms_checked"] = result.get("platforms_checked", 0)
            result["platforms_found_count"] = result.get("platforms_found_count", 0)
            result["platforms_found"] = result.get("platforms_found", [])
            result["all_platforms"] = result.get("all_platforms", [])
        elif query_type == "domain":
            result["whois_registrant"] = result.get("whois_registrant", {"name": "", "organization": ""})
            result["dns_soa_email"] = result.get("dns_soa_email", "")
        return result
    except Exception as e:
        logger.exception("Identity resolve failed: %s", e)
        result["error"] = f"Resolution failed: {type(e).__name__}"
        # Ensure default fields are present even on error
        if query_type == "email":
            result["gravatar"] = result.get("gravatar", {"exists": False, "url": None, "hash": ""})
            result["pgp_keys"] = result.get("pgp_keys", [])
            result["pgp_keys_count"] = result.get("pgp_keys_count", 0)
            result["github_commits"] = result.get("github_commits", 0)
        elif query_type == "username":
            result["platforms_checked"] = result.get("platforms_checked", 0)
            result["platforms_found_count"] = result.get("platforms_found_count", 0)
            result["platforms_found"] = result.get("platforms_found", [])
            result["all_platforms"] = result.get("all_platforms", [])
        elif query_type == "domain":
            result["whois_registrant"] = result.get("whois_registrant", {"name": "", "organization": ""})
            result["dns_soa_email"] = result.get("dns_soa_email", "")
        return result

    return result


async def _check_gravatar(client: httpx.AsyncClient, email: str) -> dict[str, Any]:
    """Check Gravatar profile for email."""
    email_lower = email.lower().strip()
    email_hash = hashlib.md5(email_lower.encode()).hexdigest()
    gravatar_url = f"https://gravatar.com/avatar/{email_hash}?d=404"

    try:
        resp = await client.head(gravatar_url, timeout=10.0, follow_redirects=True)
        exists = resp.status_code == 200
    except Exception:
        exists = False

    return {
        "exists": exists,
        "url": gravatar_url if exists else None,
        "hash": email_hash,
    }


async def _check_pgp(client: httpx.AsyncClient, email: str) -> dict[str, Any]:
    """Check OpenPGP keyserver for email."""
    try:
        url = f"https://keys.openpgp.org/vks/v1/by-email/{quote(email)}"
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            keys = data.get("keys", [])
            # Limit to 10 keys
            limited_keys = keys[:10]
            return {
                "keys": limited_keys,
                "key_count": len(limited_keys),
            }
    except Exception as e:
        logger.debug("pgp check failed: %s", e)

    return {
        "keys": [],
        "key_count": 0,
    }


async def _check_github_commits(
    client: httpx.AsyncClient, email: str
) -> dict[str, Any]:
    """Check GitHub for commits by email."""
    try:
        url = f"https://api.github.com/search/commits?q={quote(email)}"
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            commit_count = data.get("total_count", 0)
            return {"commit_count": commit_count}
    except Exception as e:
        logger.debug("github commits check failed: %s", e)

    return {"commit_count": 0}


async def _check_platforms(client: httpx.AsyncClient, username: str) -> list[dict[str, Any]]:
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
        ("TikTok", f"https://www.tiktok.com/@{username}"),
        ("Discord", f"https://discordapp.com/users/search?q={username}"),
    ]

    results: list[dict[str, Any]] = []

    for platform_name, url in platforms:
        exists = False
        try:
            resp = await client.head(url, timeout=10.0, follow_redirects=True)
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


async def _check_whois(client: httpx.AsyncClient, domain: str) -> dict[str, Any]:
    """Check WHOIS registrant information."""
    try:
        url = f"https://rdap.org/domain/{domain}"
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            contacts = data.get("entities", [])
            for contact in contacts:
                if "registrant" in contact.get("roles", []):
                    # Extract name from vcard
                    vcard_array = contact.get("vcardArray", [])
                    name = ""
                    organization = ""
                    if len(vcard_array) > 1:
                        for item in vcard_array[1]:
                            if isinstance(item, list) and len(item) >= 3:
                                if item[0] == "fn":
                                    name = item[3] if len(item) > 3 else ""
                                elif item[0] == "org":
                                    organization = item[3] if len(item) > 3 else ""
                    return {"name": name, "organization": organization}
    except Exception as e:
        logger.debug("whois check failed: %s", e)

    return {"name": "", "organization": ""}


async def _check_dns_soa(client: httpx.AsyncClient, domain: str) -> str:
    """Check DNS SOA record for admin email."""
    try:
        url = f"https://dns.google/resolve?name={domain}&type=SOA"
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            answers = data.get("Answer", [])
            for answer in answers:
                soa_data = answer.get("data", "")
                if soa_data:
                    parts = soa_data.split()
                    if len(parts) >= 2:
                        # Return the rname (responsible name) as-is
                        return parts[1]
    except Exception as e:
        logger.debug("dns check failed: %s", e)

    return ""
