"""research_leak_scan — Scan for data exposure across public sources."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote

import httpx

from loom.config import CONFIG

logger = logging.getLogger("loom.tools.leak_scan")

# API endpoints for leak detection
HIBP_BREACH_URL = "https://haveibeenpwned.com/api/v3/breachedaccount"
SHODAN_INTERNETDB = "https://internetdb.shodan.io/{ip}"
CRT_SH = "https://crt.sh/?q=%25{domain}&output=json"
GITHUB_CODE_SEARCH = "https://api.github.com/search/code"


async def _get_json(
    client: httpx.AsyncClient, url: str, headers: dict[str, str] | None = None, timeout: float = 20.0
) -> Any:
    """Fetch JSON from URL with optional headers."""
    try:
        resp = await client.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("leak_scan json fetch failed: %s", exc)
    return None


async def _get_text(
    client: httpx.AsyncClient, url: str, headers: dict[str, str] | None = None, timeout: float = 15.0
) -> str:
    """Fetch text from URL with optional headers."""
    try:
        resp = await client.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("leak_scan text fetch failed: %s", exc)
    return ""


async def _check_hibp_breaches(
    client: httpx.AsyncClient, email: str
) -> tuple[int, list[dict[str, Any]]]:
    """Check HaveIBeenPwned for email breaches.

    Returns:
        Tuple of (count, exposures list)
    """
    api_key = CONFIG.get("HIBP_API_KEY", "").strip()
    if not api_key:
        logger.debug("HIBP_API_KEY not configured")
        return 0, []

    headers = {
        "User-Agent": "Loom-Research/1.0",
        "hibp-api-key": api_key,
    }

    data = await _get_json(client, f"{HIBP_BREACH_URL}/{quote(email)}", headers=headers)
    if not data:
        return 0, []

    exposures = []
    for breach in data:
        exposures.append({
            "source": "HaveIBeenPwned",
            "type": "email_breach",
            "description": f"Email found in {breach.get('Name', 'Unknown')} breach ({breach.get('BreachDate', 'Unknown date')})",
            "severity": "high",
            "url": f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(email)}",
        })

    return len(exposures), exposures


async def _check_github_secrets(
    client: httpx.AsyncClient, query: str
) -> tuple[int, list[dict[str, Any]]]:
    """Check GitHub code search for exposed secrets.

    Returns:
        Tuple of (count, exposures list)
    """
    # Limit query to max 255 chars for GitHub API
    query_part = query[:200] if query else ""
    search_query = f'{query_part}+filename:.env OR filename:config.json OR filename:secrets'

    params = {"q": search_query, "per_page": 10, "sort": "indexed"}

    headers = {
        "User-Agent": "Loom-Research/1.0",
        "Accept": "application/vnd.github.v3+json",
    }

    resp = await client.get(GITHUB_CODE_SEARCH, params=params, headers=headers, timeout=20.0)
    if resp.status_code != 200:
        logger.debug("GitHub search failed: %s", resp.status_code)
        return 0, []

    try:
        data = resp.json()
    except Exception as exc:
        logger.debug("GitHub JSON parse failed: %s", exc)
        return 0, []

    exposures = []
    results = data.get("items", [])[:5]  # Limit to top 5
    for item in results:
        exposures.append({
            "source": "GitHub",
            "type": "code_exposure",
            "description": f"Potential secrets in {item.get('path', 'unknown')} at {item.get('repository', {}).get('full_name', 'unknown')}",
            "severity": "critical",
            "url": item.get("html_url", ""),
        })

    return len(exposures), exposures


async def _check_shodan_internetdb(
    client: httpx.AsyncClient, ip: str
) -> tuple[int, list[dict[str, Any]]]:
    """Check Shodan InternetDB for exposed databases.

    Returns:
        Tuple of (count, exposures list)
    """
    data = await _get_json(client, SHODAN_INTERNETDB.format(ip=ip), timeout=15.0)
    if not data:
        return 0, []

    exposures = []

    # Check for exposed databases on common ports
    ports = data.get("ports", [])
    exposed_databases = {
        27017: {"service": "MongoDB", "severity": "critical"},
        6379: {"service": "Redis", "severity": "critical"},
        9200: {"service": "Elasticsearch", "severity": "high"},
        3306: {"service": "MySQL", "severity": "high"},
        5432: {"service": "PostgreSQL", "severity": "high"},
        1433: {"service": "MSSQL", "severity": "high"},
    }

    for port in ports:
        if port in exposed_databases:
            svc = exposed_databases[port]["service"]
            severity = exposed_databases[port]["severity"]
            exposures.append({
                "source": "Shodan InternetDB",
                "type": "exposed_database",
                "description": f"{svc} database exposed on port {port}",
                "severity": severity,
                "url": f"https://internetdb.shodan.io/{ip}",
            })

    return len(exposures), exposures


async def _check_certificate_transparency(
    client: httpx.AsyncClient, domain: str
) -> tuple[int, list[dict[str, Any]]]:
    """Check Certificate Transparency logs for domain exposure.

    Returns:
        Tuple of (count, exposures list)
    """
    data = await _get_json(client, CRT_SH.format(domain=quote(domain)), timeout=30.0)
    if not data:
        return 0, []

    exposures = []
    emails: set[str] = set()

    # Extract emails from certificate Subject Alternative Names
    for cert in data:
        name_value = cert.get("name_value", "")
        # Look for email patterns in name_value
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        found_emails = re.findall(email_pattern, name_value)
        emails.update(found_emails)

    for email in list(emails)[:10]:  # Limit to top 10 unique emails
        exposures.append({
            "source": "Certificate Transparency",
            "type": "email_disclosure",
            "description": f"Email {email} disclosed in certificate for {domain}",
            "severity": "medium",
            "url": f"https://crt.sh/?q=%25.{domain}",
        })

    return len(exposures), exposures


async def _check_pastebin_dork(
    client: httpx.AsyncClient, query: str
) -> tuple[int, list[dict[str, Any]]]:
    """Search Pastebin via DuckDuckGo for exposed data.

    Returns:
        Tuple of (count, exposures list)
    """
    # Use DuckDuckGo to search Pastebin (no API key required)
    dork = f"site:pastebin.com {query}"

    try:
        # DuckDuckGo HTML search (no formal API, but searchable via HTTP)
        resp = await client.get(
            "https://duckduckgo.com/",
            params={"q": dork, "t": "h"},
            timeout=15.0,
            headers={"User-Agent": "Loom-Research/1.0"},
        )
        if resp.status_code != 200:
            return 0, []

        # Parse HTML for Pastebin links
        exposures = []
        pastebin_pattern = r"https://pastebin\.com/[a-zA-Z0-9]+"
        matches = re.findall(pastebin_pattern, resp.text)

        for url in list(set(matches))[:5]:  # Limit to top 5 unique
            exposures.append({
                "source": "Pastebin",
                "type": "paste_disclosure",
                "description": f"Potential exposure found on Pastebin matching query {query}",
                "severity": "medium",
                "url": url,
            })

        return len(exposures), exposures

    except Exception as exc:
        logger.debug("Pastebin dork search failed: %s", exc)
        return 0, []


async def _check_trello_dork(
    client: httpx.AsyncClient, query: str
) -> tuple[int, list[dict[str, Any]]]:
    """Search Trello via DuckDuckGo for public boards.

    Returns:
        Tuple of (count, exposures list)
    """
    dork = f"site:trello.com {query}"

    try:
        resp = await client.get(
            "https://duckduckgo.com/",
            params={"q": dork, "t": "h"},
            timeout=15.0,
            headers={"User-Agent": "Loom-Research/1.0"},
        )
        if resp.status_code != 200:
            return 0, []

        # Parse HTML for Trello links
        exposures = []
        trello_pattern = r"https://trello\.com/b/[a-zA-Z0-9]+"
        matches = re.findall(trello_pattern, resp.text)

        for url in list(set(matches))[:5]:  # Limit to top 5 unique
            exposures.append({
                "source": "Trello",
                "type": "board_disclosure",
                "description": f"Public Trello board potentially exposing data for {query}",
                "severity": "medium",
                "url": url,
            })

        return len(exposures), exposures

    except Exception as exc:
        logger.debug("Trello dork search failed: %s", exc)
        return 0, []


def _is_valid_ip(ip: str) -> bool:
    """Validate IPv4 address format."""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        try:
            num = int(part)
            if num < 0 or num > 255:
                return False
        except ValueError:
            return False
    return True


def _is_valid_email(email: str) -> bool:
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False
    if len(email) > 254:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def _is_valid_domain(domain: str) -> bool:
    """Validate domain format."""
    if not domain or not isinstance(domain, str):
        return False
    if len(domain) > 255:
        return False
    # Basic domain validation: at least one dot and valid chars
    pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, domain))


async def research_leak_scan(
    target: str,
    target_type: str = "domain",
) -> dict[str, Any]:
    """Scan for data exposure across ethical public sources.

    Checks 6+ sources for leaked data: HaveIBeenPwned (email breaches),
    GitHub code search (exposed secrets), Shodan InternetDB (exposed databases),
    Certificate Transparency (email disclosure), Pastebin (pastes), and
    Trello (public boards).

    Args:
        target: The target to scan (domain, email, IP, or keyword)
        target_type: Type of target - "domain", "email", "ip", or "keyword" (default: "domain")

    Returns:
        Dict with keys:
          - target: input target
          - target_type: type of target scanned
          - sources_checked: list of sources queried
          - total_exposures: int (total count)
          - exposures: list of dicts {source, type, description, severity, url}
          - errors: dict of {source: error_message} if any failed
    """

    # Validate target based on type
    if target_type == "email":
        if not _is_valid_email(target):
            return {
                "target": target,
                "target_type": target_type,
                "error": "Invalid email format",
                "sources_checked": [],
                "total_exposures": 0,
                "exposures": [],
            }
    elif target_type == "ip":
        if not _is_valid_ip(target):
            return {
                "target": target,
                "target_type": target_type,
                "error": "Invalid IP address format",
                "sources_checked": [],
                "total_exposures": 0,
                "exposures": [],
            }
    elif target_type == "domain":
        if not _is_valid_domain(target):
            return {
                "target": target,
                "target_type": target_type,
                "error": "Invalid domain format",
                "sources_checked": [],
                "total_exposures": 0,
                "exposures": [],
            }
    # keyword is always valid

    logger.info("leak_scan target=%s target_type=%s", target, target_type)

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            exposures: list[dict[str, Any]] = []
            sources_checked: list[str] = []
            errors: dict[str, str] = {}

            # Prepare tasks based on target type
            tasks: dict[str, Any] = {}

            if target_type == "email":
                tasks["HaveIBeenPwned"] = _check_hibp_breaches(client, target)
                tasks["Pastebin"] = _check_pastebin_dork(client, target)
                tasks["Trello"] = _check_trello_dork(client, target)

            elif target_type == "ip":
                tasks["Shodan InternetDB"] = _check_shodan_internetdb(client, target)

            elif target_type == "domain":
                tasks["Certificate Transparency"] = _check_certificate_transparency(client, target)
                tasks["GitHub"] = _check_github_secrets(client, target)
                tasks["Pastebin"] = _check_pastebin_dork(client, target)
                tasks["Trello"] = _check_trello_dork(client, target)

            elif target_type == "keyword":
                tasks["GitHub"] = _check_github_secrets(client, target)
                tasks["Pastebin"] = _check_pastebin_dork(client, target)
                tasks["Trello"] = _check_trello_dork(client, target)

            # Execute all tasks concurrently
            if tasks:
                results = await asyncio.gather(
                    *tasks.values(),
                    return_exceptions=True,
                )

                for source_name, result in zip(tasks.keys(), results):
                    sources_checked.append(source_name)

                    if isinstance(result, Exception):
                        errors[source_name] = str(result)
                        logger.debug("leak_scan %s failed: %s", source_name, result)
                    else:
                        count, source_exposures = result
                        exposures.extend(source_exposures)

            # Sort by severity (critical > high > medium > low)
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            exposures.sort(
                key=lambda x: (severity_order.get(x.get("severity", "low"), 999), -len(x.get("url", "")))
            )

            result = {
                "target": target,
                "target_type": target_type,
                "sources_checked": sources_checked,
                "total_exposures": len(exposures),
                "exposures": exposures,
            }

            if errors:
                result["errors"] = errors

            return result

    return await _run()
