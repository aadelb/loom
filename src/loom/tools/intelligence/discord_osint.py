"""Discord OSINT intelligence — public server discovery and analysis."""
from __future__ import annotations

import logging
import re
from typing import Any
import httpx

from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_json, fetch_text

logger = logging.getLogger("loom.tools.discord_osint")

_HTTP_TIMEOUT = 15.0
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _validate_invite_code(invite_code: str) -> bool:
    """Validate Discord invite code format.

    Args:
        invite_code: Invite code to validate

    Returns:
        True if valid, False otherwise.
    """
    if not invite_code or len(invite_code) < 1 or len(invite_code) > 32:
        return False
    # Invite codes are alphanumeric, hyphens, underscores
    return bool(re.match(r"^[a-zA-Z0-9_-]+$", invite_code))


def _validate_server_id(server_id: str) -> bool:
    """Validate Discord server ID format.

    Args:
        server_id: Server ID to validate

    Returns:
        True if valid, False otherwise.
    """
    if not server_id or len(server_id) < 15 or len(server_id) > 20:
        return False
    # Server IDs are numeric snowflakes
    return bool(re.match(r"^\d+$", server_id))


def _parse_json_embed(html: str, key: str) -> Any:
    """Extract JSON data from Discord's embedded og: meta tags and scripts.

    Args:
        html: HTML content from Discord invite page
        key: Key to look for in JSON structures

    Returns:
        Parsed value, or None if not found.
    """
    # Try to find JSON in meta og:description or similar
    json_patterns = [
        r'<meta property="og:description" content="([^"]*)"',
        r'"(\d+)\s+members?',
        r'"(\d+)\s+online',
    ]

    for pattern in json_patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)

    return None


def _extract_server_info_from_html(html: str) -> dict[str, Any]:
    """Extract server information from Discord invite page HTML.

    Args:
        html: HTML content from Discord invite page

    Returns:
        Dict with server name, description, member count, online count.
    """
    info: dict[str, Any] = {}

    # Extract server name
    name_patterns = [
        r'<meta property="og:title" content="([^"]*)"',
        r"<title>([^|]+)\s*\|",
        r'"server_name":"([^"]+)"',
    ]

    for pattern in name_patterns:
        match = re.search(pattern, html)
        if match:
            info["server_name"] = match.group(1).strip()
            break

    # Extract description
    desc_patterns = [
        r'<meta property="og:description" content="([^"]*)"',
        r'"instant_invites_enabled":\s*([^,}]+)',
    ]

    for pattern in desc_patterns:
        match = re.search(pattern, html)
        if match:
            info["description"] = match.group(1).strip()[:300]
            break

    # Extract member count
    member_patterns = [
        r'"approximate_member_count":\s*(\d+)',
        r"(\d+)\s+members?",
        r"Joined by ([\d,]+)\s+members?",
    ]

    for pattern in member_patterns:
        match = re.search(pattern, html)
        if match:
            try:
                count_str = match.group(1).replace(",", "")
                info["member_count"] = int(count_str)
                break
            except (ValueError, AttributeError):
                continue

    # Extract online count
    online_patterns = [
        r'"approximate_presence_count":\s*(\d+)',
        r"(\d+)\s+online",
    ]

    for pattern in online_patterns:
        match = re.search(pattern, html)
        if match:
            try:
                count_str = match.group(1).replace(",", "")
                info["online_count"] = int(count_str)
                break
            except (ValueError, AttributeError):
                continue

    # Extract icon URL
    icon_patterns = [
        r'<meta property="og:image" content="([^"]*)"',
        r'"icon":"([^"]+)"',
    ]

    for pattern in icon_patterns:
        match = re.search(pattern, html)
        if match:
            info["icon_url"] = match.group(1)
            break

    # Extract verification level
    verification_patterns = [
        r'"verification_level":\s*(\d+)',
    ]

    for pattern in verification_patterns:
        match = re.search(pattern, html)
        if match:
            level = int(match.group(1))
            levels = ["None", "Low", "Medium", "High", "Very High"]
            info["verification_level"] = levels[level] if level < len(levels) else "Unknown"
            break

    return info


@handle_tool_errors("research_discord_intel")
async def research_discord_intel(
    server_id: str = "",
    invite_code: str = "",
    query: str = "",
) -> dict[str, Any]:
    """Gather OSINT intelligence on Discord public servers and invites.

    Fetches public invite information from Discord's API and web interface.
    Does NOT require authentication and only accesses publicly available information.

    Args:
        server_id: Discord server ID (snowflake)
        invite_code: Discord invite code (e.g., "abc123")
        query: Free-form search query (future enhancement)

    Returns:
        Dict with server_name, member_count, description, channels_visible, online_count.
    """
    # Validate inputs
    if server_id and not _validate_server_id(server_id):
        return {
            "status": "error",
            "error": "invalid server ID: must be numeric (15-20 digits)",
            "server_id": server_id,
            "server_info": {},
        }

    if invite_code and not _validate_invite_code(invite_code):
        return {
            "status": "error",
            "error": "invalid invite code: alphanumeric, hyphens, underscores only",
            "invite_code": invite_code,
            "server_info": {},
        }

    if not server_id and not invite_code and not query:
        return {
            "status": "error",
            "error": "provide either server_id, invite_code, or query",
            "server_info": {},
        }

    result: dict[str, Any] = {
        "status": "success",
        "server_id": server_id,
        "invite_code": invite_code,
        "query": query,
        "server_info": {},
        "channels_visible": [],
    }

    # Use invite code if provided, fallback to server ID
    target = invite_code or server_id

    if not target:
        return {
            "status": "error",
            "error": "no valid target provided",
            "server_info": {},
        }

    # Try Discord API endpoint for invite information
    api_url = f"https://discord.com/api/v10/invites/{target}"

    try:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
            # Try API endpoint first
            api_resp = await client.get(
                f"{api_url}?with_counts=true",
                headers={"User-Agent": _USER_AGENT},
            )

            if api_resp.status_code == 200:
                try:
                    data = api_resp.json()

                    # Extract information from API response
                    guild = data.get("guild", {})
                    guild_id = guild.get("id", "")
                    icon_hash = guild.get("icon")
                    icon_url = (
                        f"https://cdn.discordapp.com/icons/{guild_id}/{icon_hash}.png"
                        if icon_hash and guild_id else None
                    )
                    server_info = {
                        "server_name": guild.get("name"),
                        "server_id": guild_id,
                        "description": guild.get("description"),
                        "member_count": data.get("approximate_member_count"),
                        "online_count": data.get("approximate_presence_count"),
                        "icon_url": icon_url,
                        "verification_level": guild.get("verification_level"),
                        "invite_code": target,
                    }

                    # Extract channels if available
                    channels = data.get("channels", [])
                    result["channels_visible"] = [
                        {
                            "id": ch.get("id"),
                            "name": ch.get("name"),
                            "type": ch.get("type"),
                        }
                        for ch in channels[:10]  # Limit to first 10
                    ]

                    result["server_info"] = {
                        k: v for k, v in server_info.items() if v is not None
                    }

                    logger.info(
                        "discord_intel invite=%s server=%s members=%s",
                        target,
                        server_info.get("server_name"),
                        server_info.get("member_count"),
                    )

                    return result

                except Exception as e:
                    logger.warning("discord_intel api parse error invite=%s: %s", target, e)

            elif api_resp.status_code == 404:
                result["status"] = "not_found"
                result["error"] = f"Invite '{target}' not found or expired"
                return result

            elif api_resp.status_code == 429:
                result["status"] = "rate_limited"
                result["error"] = "Rate limited by Discord API"
                return result

    except httpx.TimeoutException:
        result["status"] = "error"
        result["error"] = "Request timeout"
        logger.warning("discord_intel timeout invite=%s", target)
        return result
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error("discord_intel error invite=%s error=%s", target, e)
        return result

    # Fallback: Try Discord's web interface for invite preview
    if invite_code:
        web_url = f"https://discord.gg/{invite_code}"
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, follow_redirects=False) as client:
                web_resp = await client.get(web_url, headers={"User-Agent": _USER_AGENT})

                if web_resp.status_code in (200, 307):
                    html = web_resp.text
                    server_info = _extract_server_info_from_html(html)

                    if server_info:
                        result["server_info"] = server_info
                        logger.info(
                            "discord_intel web invite=%s server=%s",
                            invite_code,
                            server_info.get("server_name"),
                        )

        except Exception as e:
            logger.debug("discord_intel web fallback failed invite=%s: %s", invite_code, e)

    return result
