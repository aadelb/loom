"""Identity resolution — link online identities using only public data."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.identity_resolve")


async def _get_json(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> Any:
    """Fetch JSON from URL, return None on error."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("identity_resolve json fetch failed: %s", exc)
    return None


async def _get_text(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> str:
    """Fetch plain text from URL, return empty string on error."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("identity_resolve text fetch failed: %s", exc)
    return ""


async def _head_exists(
    client: httpx.AsyncClient, url: str, timeout: float = 10.0
) -> bool:
    """Check if URL exists via HEAD request."""
    try:
        resp = await client.head(url, timeout=timeout, follow_redirects=True)
        return resp.status_code == 200
    except Exception:
        return False


async def _gravatar_check(client: httpx.AsyncClient, email: str) -> dict[str, Any]:
    """Check Gravatar profile for email."""
    email_lower = email.lower().strip()
    email_hash = hashlib.md5(email_lower.encode()).hexdigest()
    gravatar_url = f"https://gravatar.com/avatar/{email_hash}?d=404"

    exists = await _head_exists(client, gravatar_url)

    return {
        "exists": exists,
        "url": gravatar_url,
        "hash": email_hash,
    }


async def _pgp_keys_check(client: httpx.AsyncClient, email: str) -> list[dict[str, Any]]:
    """Check OpenPGP keyserver for email."""
    try:
        url = f"https://keys.openpgp.org/vks/v1/by-email/{quote(email)}"
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            data = resp.json()
            keys = data.get("keys", [])
            return [
                {
                    "keyid": k.get("keyid", ""),
                    "uids": k.get("uids", []),
                    "created": k.get("created", ""),
                }
                for k in keys[:10]
            ]
    except Exception as exc:
        logger.debug("pgp keys check failed: %s", exc)
    return []


async def _github_commits_check(client: httpx.AsyncClient, email: str) -> int:
    """Count commits by email via GitHub API."""
    try:
        url = f"https://api.github.com/search/commits?q=author-email:{quote(email)}"
        headers = {"Accept": "application/vnd.github.cloak-preview+json"}
        resp = await client.get(url, timeout=15.0, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("total_count", 0)
    except Exception as exc:
        logger.debug("github commits check failed: %s", exc)
    return 0


async def _username_platform_check(
    client: httpx.AsyncClient, username: str
) -> list[dict[str, Any]]:
    """Check username existence on common platforms via HEAD requests."""
    platforms = [
        ("GitHub", f"https://github.com/{username}"),
        ("Reddit", f"https://reddit.com/user/{username}"),
        ("HackerNews", f"https://news.ycombinator.com/user?id={username}"),
        ("Twitter/X", f"https://x.com/{username}"),
        ("Instagram", f"https://instagram.com/{username}"),
        ("LinkedIn", f"https://linkedin.com/in/{username}"),
        ("GitLab", f"https://gitlab.com/{username}"),
        ("Keybase", f"https://keybase.io/{username}"),
        ("Medium", f"https://medium.com/@{username}"),
        ("Dev.to", f"https://dev.to/{username}"),
    ]

    results: list[dict[str, Any]] = []
    tasks = [
        (platform_name, _head_exists(client, url))
        for platform_name, url in platforms
    ]

    responses = await asyncio.gather(*[task[1] for task in tasks])
    for (platform_name, url), exists in zip(tasks, responses):
        results.append(
            {
                "platform": platform_name,
                "url": url,
                "exists": exists,
            }
        )

    return results


async def _whois_registrant_check(client: httpx.AsyncClient, domain: str) -> dict[str, Any]:
    """Extract WHOIS registrant info via RDAP."""
    try:
        url = f"https://rdap.org/domain/{quote(domain)}"
        data = await _get_json(client, url, timeout=20.0)
        if data:
            registrant = {}
            # Extract registrant contact info if available
            contacts = data.get("entities", [])
            for contact in contacts:
                if "registrant" in contact.get("roles", []):
                    registrant = {
                        "name": contact.get("vcardArray", [None, None])[1][1][3] if len(contact.get("vcardArray", [None, None])) > 1 else "",
                        "organization": contact.get("vcardArray", [None, None])[1][2][3] if len(contact.get("vcardArray", [None, None])) > 2 else "",
                    }
                    break
            return registrant or {"name": "", "organization": ""}
    except Exception as exc:
        logger.debug("whois registrant check failed: %s", exc)
    return {"name": "", "organization": ""}


async def _dns_soa_email_check(client: httpx.AsyncClient, domain: str) -> str:
    """Extract SOA email via Google DNS."""
    try:
        url = f"https://dns.google/resolve?name={quote(domain)}&type=SOA"
        data = await _get_json(client, url, timeout=10.0)
        if data and "Answer" in data:
            for answer in data["Answer"]:
                if answer.get("type") == 6:  # SOA record type
                    data_str = answer.get("data", "")
                    # SOA format: primary ns, responsible email, ...
                    parts = data_str.split()
                    if len(parts) > 1:
                        return parts[1]
    except Exception as exc:
        logger.debug("dns soa email check failed: %s", exc)
    return ""


def research_identity_resolve(
    query: str, query_type: str = "email"
) -> dict[str, Any]:
    """Link online identities using only public data.

    Resolves emails to Gravatar profiles, PGP keys, GitHub commits;
    usernames to social media profiles; and domains to WHOIS/DNS
    registrant information.

    Args:
        query: email, username, or domain to resolve
        query_type: "email", "username", or "domain"

    Returns:
        Dict with ``query``, ``query_type``, and resolution results:
        - For email: ``gravatar``, ``pgp_keys``, ``github_commits``
        - For username: ``platforms_found`` (list of platform checks)
        - For domain: ``whois_registrant``, ``dns_soa_email``
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            result: dict[str, Any] = {
                "query": query,
                "query_type": query_type,
            }

            if query_type == "email":
                # Resolve email to gravatar, pgp, github
                gravatar_task = _gravatar_check(client, query)
                pgp_task = _pgp_keys_check(client, query)
                github_task = _github_commits_check(client, query)

                gravatar, pgp_keys, github_commits = await asyncio.gather(
                    gravatar_task, pgp_task, github_task
                )

                result.update(
                    {
                        "gravatar": gravatar,
                        "pgp_keys": pgp_keys,
                        "pgp_keys_count": len(pgp_keys),
                        "github_commits": github_commits,
                    }
                )

            elif query_type == "username":
                # Resolve username to platforms
                platforms = await _username_platform_check(client, query)
                platforms_found = [p for p in platforms if p["exists"]]

                result.update(
                    {
                        "platforms_checked": len(platforms),
                        "platforms_found_count": len(platforms_found),
                        "platforms_found": platforms_found,
                        "all_platforms": platforms,
                    }
                )

            elif query_type == "domain":
                # Resolve domain to whois, dns
                whois_task = _whois_registrant_check(client, query)
                dns_soa_task = _dns_soa_email_check(client, query)

                whois_registrant, dns_soa_email = await asyncio.gather(
                    whois_task, dns_soa_task
                )

                result.update(
                    {
                        "whois_registrant": whois_registrant,
                        "dns_soa_email": dns_soa_email,
                    }
                )

            return result

    try:
        return asyncio.run(_run())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run())
        finally:
            loop.close()
