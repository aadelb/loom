"""Telegram OSINT intelligence — public channel discovery and analysis."""

from __future__ import annotations
try:
    from loom.text_utils import truncate
except ImportError:
    def truncate(text, max_chars=500, *, suffix="..."):
        if len(text) <= max_chars: return text
        return text[:max_chars - len(suffix)] + suffix



import logging
import re
from typing import Any
import httpx

from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_text

logger = logging.getLogger("loom.tools.telegram_osint")

_HTTP_TIMEOUT = 15.0
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _validate_channel_name(channel: str) -> bool:
    """Validate Telegram channel name format.

    Args:
        channel: Channel name to validate

    Returns:
        True if valid, False otherwise.
    """
    if not channel or len(channel) < 1 or len(channel) > 255:
        return False
    # Telegram channel/group names: alphanumeric, underscore only
    return bool(re.match(r"^[a-zA-Z0-9_]+$", channel))


def _validate_username(username: str) -> bool:
    """Validate Telegram username format.

    Args:
        username: Username to validate

    Returns:
        True if valid, False otherwise.
    """
    if not username or len(username) < 1 or len(username) > 255:
        return False
    return bool(re.match(r"^[a-zA-Z0-9_]+$", username))


def _extract_member_count(html: str) -> int | None:
    """Extract member count from Telegram channel page HTML.

    Args:
        html: HTML content from Telegram channel page

    Returns:
        Member count as integer, or None if not found.
    """
    # Try to find patterns like "123K members" or "1.2M members"
    patterns = [
        r"([0-9.]+[KMB]?)\s+members?",
        r"([0-9]+)\s+subscribers?",
        r"([0-9.]+[KMB]?)\s+subscribers?",
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            try:
                count_str = match.group(1).upper()
                if "K" in count_str:
                    return int(float(count_str.replace("K", "")) * 1000)
                elif "M" in count_str:
                    return int(float(count_str.replace("M", "")) * 1_000_000)
                elif "B" in count_str:
                    return int(float(count_str.replace("B", "")) * 1_000_000_000)
                else:
                    return int(float(count_str))
            except (ValueError, AttributeError):
                continue

    return None


def _extract_description(html: str) -> str | None:
    """Extract channel/group description from HTML.

    Args:
        html: HTML content from Telegram channel page

    Returns:
        Description text, or None if not found.
    """
    # Try common meta description patterns
    patterns = [
        r'<meta\s+name="description"\s+content="([^"]*)"',
        r'<meta\s+property="og:description"\s+content="([^"]*)"',
        r'<div class="tgme_page_description">([^<]*)</div>',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            description = match.group(1).strip()
            if description:
                return description

    return None


def _extract_title(html: str) -> str | None:
    """Extract channel/group title from HTML.

    Args:
        html: HTML content from Telegram channel page

    Returns:
        Title text, or None if not found.
    """
    patterns = [
        r"<title>([^<]+)</title>",
        r'<meta\s+property="og:title"\s+content="([^"]*)"',
        r'<h1[^>]*>([^<]+)</h1>',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            if title:
                return title

    return None


def _extract_image_url(html: str) -> str | None:
    """Extract channel/group avatar image URL.

    Args:
        html: HTML content from Telegram channel page

    Returns:
        Image URL, or None if not found.
    """
    patterns = [
        r'<meta\s+property="og:image"\s+content="([^"]*)"',
        r'<img\s+(?:[^>]*\s+)?src="([^"]*avatar[^"]*)"',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            url = match.group(1).strip()
            if url:
                return url

    return None


def _extract_recent_messages(html: str, limit: int = 10) -> list[dict[str, Any]]:
    """Extract recent messages from Telegram channel page.

    Args:
        html: HTML content from Telegram channel page
        limit: Maximum number of messages to extract

    Returns:
        List of message dicts with text and timestamp.
    """
    messages: list[dict[str, Any]] = []

    # Try to find message containers
    message_pattern = r'<div[^>]*class="tgme_widget_message[^>]*>([^<]*(?:<[^>]*>[^<]*)*?)</div>'

    for match in re.finditer(message_pattern, html, re.IGNORECASE):
        if len(messages) >= limit:
            break

        message_html = match.group(1)

        # Extract text
        text_match = re.search(r"<div[^>]*class=\"[^\"]*text[^\"]*\">([^<]*)</div>", message_html)
        text = text_match.group(1).strip() if text_match else ""

        # Extract timestamp
        time_match = re.search(r"<a[^>]*class=\"tgme_widget_message_date[^>]*>([^<]+)</a>", message_html)
        timestamp = time_match.group(1).strip() if time_match else ""

        if text or timestamp:
            messages.append({"text": truncate(text, 500), "timestamp": timestamp})

    return messages


@handle_tool_errors("research_telegram_intel")
async def research_telegram_intel(
    query: str = "",
    channel: str = "",
    username: str = "",
) -> dict[str, Any]:
    """Gather OSINT intelligence on Telegram public channels and groups.

    Fetches public channel information from Telegram's web interface (t.me).
    Does NOT require API keys and only accesses publicly available information.

    Args:
        query: Free-form search query for channels (future enhancement)
        channel: Specific channel name to investigate (e.g., "channelname")
        username: Specific Telegram user/bot to investigate

    Returns:
        Dict with channel_info, messages, member_count, related_channels, and status.
    """
    # Validate inputs
    if channel and not _validate_channel_name(channel):
        return {
            "status": "error",
            "error": "invalid channel name: alphanumeric and underscore only",
            "channel": channel,
            "channel_info": {},
            "messages": [],
            "member_count": None,
            "related_channels": [],
        }

    if username and not _validate_username(username):
        return {
            "status": "error",
            "error": "invalid username: alphanumeric and underscore only",
            "username": username,
            "user_info": {},
            "related_channels": [],
        }

    # Target channel or username
    if not channel and not username and not query:
        return {
            "status": "error",
            "error": "provide either channel, username, or query",
            "channel_info": {},
            "messages": [],
            "member_count": None,
            "related_channels": [],
        }

    result: dict[str, Any] = {
        "status": "success",
        "channel": channel,
        "username": username,
        "query": query,
        "channel_info": {},
        "messages": [],
        "member_count": None,
        "related_channels": [],
    }

    # Investigate channel
    if channel:
        url = f"https://t.me/s/{channel}"
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": _USER_AGENT})

                if resp.status_code == 404:
                    result["status"] = "not_found"
                    result["error"] = f"Channel '{channel}' not found"
                    return result

                if resp.status_code != 200:
                    result["status"] = "error"
                    result["error"] = f"HTTP {resp.status_code}"
                    return result

                html = resp.text

                # Extract channel information
                title = _extract_title(html)
                description = _extract_description(html)
                member_count = _extract_member_count(html)
                avatar_url = _extract_image_url(html)

                result["channel_info"] = {
                    "title": title,
                    "description": description,
                    "url": url,
                    "avatar_url": avatar_url,
                }

                result["member_count"] = member_count

                # Extract recent messages
                messages = _extract_recent_messages(html, limit=15)
                result["messages"] = messages

                # Log success
                logger.info(
                    "telegram_intel channel=%s members=%s messages=%d",
                    channel,
                    member_count,
                    len(messages),
                )

        except httpx.TimeoutException:
            result["status"] = "error"
            result["error"] = "Request timeout"
            logger.warning("telegram_intel timeout channel=%s", channel)
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error("telegram_intel error channel=%s error=%s", channel, e)

    # Investigate username/bot
    if username:
        url = f"https://t.me/{username}"
        try:
            async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": _USER_AGENT})

                if resp.status_code == 404:
                    if not channel:
                        result["status"] = "not_found"
                        result["error"] = f"Username '{username}' not found"
                        return result
                    else:
                        result["user_not_found"] = f"Username '{username}' not found"

                if resp.status_code != 200:
                    result["status"] = "error"
                    result["error"] = f"HTTP {resp.status_code}"
                    return result

                html = resp.text

                # Extract user/bot information
                title = _extract_title(html)
                description = _extract_description(html)
                avatar_url = _extract_image_url(html)

                result["user_info"] = {
                    "username": username,
                    "title": title,
                    "bio": description,
                    "url": url,
                    "avatar_url": avatar_url,
                }

                logger.info("telegram_intel username=%s title=%s", username, title)

        except httpx.TimeoutException:
            result["status"] = "error"
            result["error"] = "Request timeout"
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error("telegram_intel error username=%s error=%s", username, e)

    return result
