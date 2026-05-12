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
# Prevents consecutive separators (.. __ --)
_USERNAME_RE = re.compile(r"^(?!.*[._-]{2})[a-zA-Z0-9._-]{1,100}$")


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
    username: str = "",
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
    if not query and username:
        query = username
        query_type = "username"

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
    """Check Gravatar profile for email.

    WARNING: MD5 hash of email is cryptographically reversible via rainbow tables.
    Only used internally for Gravatar API; not exposed to caller for privacy.
    """
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
    }


async def _check_pgp(client: httpx.AsyncClient, email: str) -> dict[str, Any]:
    """Check OpenPGP keyserver for email.

    Returns up to 10 keys per email. If more keys exist, includes truncated flag.
    """
    try:
        url = f"https://keys.openpgp.org/vks/v1/by-email/{quote(email)}"
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            keys = data.get("keys", [])
            total_count = len(keys)
            limited_keys = keys[:10]
            return {
                "keys": limited_keys,
                "key_count": len(limited_keys),
                "total_key_count": total_count,
                "truncated": total_count > 10,
            }
    except Exception as e:
        logger.debug("pgp check failed: %s", e)

    return {
        "keys": [],
        "key_count": 0,
        "total_key_count": 0,
        "truncated": False,
    }


async def _check_github_commits(
    client: httpx.AsyncClient, email: str
) -> dict[str, Any]:
    """Check GitHub for commits by email.

    Uses unauthenticated search (rate limit: 10 req/min).
    Email is sent in plaintext URL; consider authentication for privacy.
    """
    try:
        url = f"https://api.github.com/search/commits?q={quote(email)}"
        resp = await client.get(url, timeout=15.0)
        # 403: rate limited; treat as no commits found
        if resp.status_code == 200:
            data = resp.json()
            commit_count = data.get("total_count", 0)
            return {"commit_count": commit_count}
        elif resp.status_code == 403:
            logger.warning("GitHub rate limited (10 req/min unauthenticated)")
    except Exception as e:
        logger.debug("github commits check failed: %s", e)

    return {"commit_count": 0}


async def _check_platforms(client: httpx.AsyncClient, username: str) -> list[dict[str, Any]]:
    """Check username existence on common platforms via HEAD/GET requests.

    Note: Some platforms (Twitter/X, Instagram) return 200 for missing profiles.
    Results marked with 'unreliable': True should be manually verified.
    Discord endpoint is deprecated; results unreliable.
    """
    platforms = [
        ("GitHub", f"https://github.com/{username}", False),
        ("Twitter/X", f"https://x.com/{username}", True),  # Unreliable: redirects to search
        ("Reddit", f"https://www.reddit.com/user/{username}/about.json", False),
        ("HackerNews", f"https://news.ycombinator.com/user?id={username}", False),
        ("GitLab", f"https://gitlab.com/{username}", False),
        ("Keybase", f"https://keybase.io/{username}", False),
        ("LinkedIn", f"https://linkedin.com/in/{username}", False),
        ("Instagram", f"https://instagram.com/{username}", True),  # Unreliable: returns 200 for missing
        ("TikTok", f"https://www.tiktok.com/@{username}", False),
        ("Discord", f"https://discord.com/api/v10/users/@me", True),  # Unreliable: requires auth
    ]

    results: list[dict[str, Any]] = []

    for platform_name, url, is_unreliable in platforms:
        exists = False
        try:
            # Use GET for Reddit (requires JSON response check)
            if platform_name == "Reddit":
                resp = await client.get(url, timeout=10.0, follow_redirects=True)
                exists = resp.status_code == 200
            else:
                resp = await client.head(url, timeout=10.0, follow_redirects=True)
                exists = resp.status_code == 200
        except Exception:
            pass

        results.append(
            {
                "platform": platform_name,
                "url": url,
                "exists": exists,
                "unreliable": is_unreliable,
            }
        )

    return results


async def _check_whois(client: httpx.AsyncClient, domain: str) -> dict[str, Any]:
    """Check WHOIS registrant information via RDAP.

    Returns registrant name/organization or empty strings if GDPR-protected.
    vCard format: ["type", [["params..."], "value"], ...]
    """
    try:
        url = f"https://rdap.org/domain/{domain}"
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            contacts = data.get("entities", [])
            for contact in contacts:
                if "registrant" in contact.get("roles", []):
                    # Extract name from vcard: ["fn", [["type", "text"], value], ...]
                    vcard_array = contact.get("vcardArray", [])
                    name = ""
                    organization = ""
                    if len(vcard_array) > 1:
                        for item in vcard_array[1]:
                            if isinstance(item, list) and len(item) >= 4:
                                # vCard format: [type, params, type, value]
                                if item[0] == "fn" and len(item) > 3:
                                    name = str(item[3]) if item[3] else ""
                                elif item[0] == "org" and len(item) > 3:
                                    organization = str(item[3]) if item[3] else ""
                    return {"name": name, "organization": organization}
    except Exception as e:
        logger.debug("whois check failed: %s", e)

    return {"name": "", "organization": ""}


async def _check_dns_soa(client: httpx.AsyncClient, domain: str) -> str:
    """Check DNS SOA record for admin email.

    SOA format: nameserver hostmaster serial refresh retry expire minimum
    Converts hostmaster from DNS format (dots) to email format (@).
    Example: hostmaster.example.com. → hostmaster@example.com
    """
    try:
        url = f"https://dns.google/resolve?name={domain}&type=SOA"
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            answers = data.get("Answer", [])
            for answer in answers:
                # Verify this is SOA type
                if answer.get("type") != 1:  # 1 = SOA
                    continue
                soa_data = answer.get("data", "")
                if soa_data:
                    parts = soa_data.split()
                    if len(parts) >= 2:
                        hostmaster = parts[1]
                        # Convert DNS format to email: dots (.) to @ after first label
                        # hostmaster.example.com. → hostmaster@example.com
                        if "." in hostmaster:
                            labels = hostmaster.rstrip(".").split(".")
                            if len(labels) >= 2:
                                # First label is user, rest is domain
                                email = labels[0] + "@" + ".".join(labels[1:])
                                return email
                        return hostmaster  # Fallback to raw format
    except Exception as e:
        logger.debug("dns check failed: %s", e)

    return ""
