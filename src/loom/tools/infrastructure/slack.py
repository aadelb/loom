"""Slack integration for sending research results to channels.

Tool:
- research_slack_notify: Send research results to a Slack channel
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any
import httpx

from loom.error_responses import handle_tool_errors
try:
    from loom.text_utils import truncate
except ImportError:
    def truncate(text, max_chars=500, *, suffix="..."):
        if len(text) <= max_chars: return text
        return text[:max_chars - len(suffix)] + suffix


logger = logging.getLogger("loom.tools.slack")

# Slack API endpoints
_SLACK_API_BASE = "https://slack.com/api"
_SLACK_CHAT_POSTMESSAGE = f"{_SLACK_API_BASE}/chat.postMessage"
_SLACK_AUTH_TEST = f"{_SLACK_API_BASE}/auth.test"

# Channel validation regex: #channel-name or C123ABC456
_CHANNEL_PATTERN = re.compile(r"^(?:#[a-zA-Z0-9_-]+|C[A-Z0-9]{8,})$")

# Constraints
MAX_TEXT_CHARS = 4000


def _validate_channel(channel: str) -> bool:
    """Validate Slack channel format.

    Args:
        channel: channel name or ID (#channel or C123...)

    Returns:
        True if valid format, False otherwise
    """
    if not channel:
        return False
    return bool(_CHANNEL_PATTERN.match(channel))


@handle_tool_errors("research_slack_notify")
async def research_slack_notify(
    channel: str,
    text: str,
    thread_ts: str | None = None,
    blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Send research results to a Slack channel.

    Sends a message to Slack via chat.postMessage API. Supports both plain text
    and rich formatting via Block Kit.

    Uses SLACK_BOT_TOKEN environment variable for authentication. Token should be
    a bot token (xoxb-*) with chat:write scope.

    Args:
        channel: channel name (#channel) or channel ID (C123...). Use #channel-name
            for public channels, @username for direct messages. Channel IDs are preferred.
        text: plain text message (max 4000 chars). Required if blocks not provided.
        thread_ts: optional timestamp to reply in thread (e.g., "1234567890.123456")
        blocks: optional Block Kit blocks array for rich formatting
            (https://api.slack.com/block-kit)

    Returns:
        Dict with keys:
        - status: "sent" on success, "failed" on error
        - channel: channel name/ID message was sent to
        - ts: message timestamp (unique ID) on success
        - error: error message on failure
        - details: additional error context if available
    """
    # Validate channel format
    if not _validate_channel(channel):
        logger.warning("slack_invalid_channel: %s", channel)
        return {
            "status": "failed",
            "channel": channel,
            "error": "invalid channel format",
            "details": "channel must be #channel-name or C123ABC...",
        }

    # Validate text length
    if not text and not blocks:
        return {
            "status": "failed",
            "channel": channel,
            "error": "either text or blocks must be provided",
        }

    if text and len(text) > MAX_TEXT_CHARS:
        logger.warning("slack_text_too_long: %d chars", len(text))
        return {
            "status": "failed",
            "channel": channel,
            "error": f"text exceeds {MAX_TEXT_CHARS} chars",
        }

    # Get bot token from environment
    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if not slack_token:
        logger.error("slack_missing_token")
        return {
            "status": "failed",
            "channel": channel,
            "error": "missing SLACK_BOT_TOKEN environment variable",
            "details": "set SLACK_BOT_TOKEN to your bot token (xoxb-*)",
        }

    if not slack_token.startswith("xoxb-"):
        logger.error("slack_invalid_token_format")
        return {
            "status": "failed",
            "channel": channel,
            "error": "invalid token format",
            "details": "token must be a bot token starting with xoxb-",
        }

    # Build request payload
    payload: dict[str, Any] = {
        "channel": channel,
    }

    if text:
        payload["text"] = text

    if blocks:
        payload["blocks"] = blocks

    if thread_ts:
        payload["thread_ts"] = thread_ts

    # Send to Slack
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {slack_token}",
                "Content-Type": "application/json",
            }

            logger.info("slack_posting channel=%s thread_ts=%s", channel, thread_ts)

            response = await client.post(
                _SLACK_CHAT_POSTMESSAGE,
                json=payload,
                headers=headers,
            )

            # Check for HTTP errors
            if response.status_code != 200:
                logger.error(
                    "slack_http_error status=%d body=%s",
                    response.status_code,
                    response.text,
                )
                return {
                    "status": "failed",
                    "channel": channel,
                    "error": f"HTTP {response.status_code}",
                    "details": truncate(response.text, 500),
                }

            # Parse response
            result = response.json()

            # Slack API returns ok=true/false
            if not result.get("ok"):
                error_msg = result.get("error", "unknown error")
                logger.warning("slack_api_error channel=%s: %s", channel, error_msg)

                # Handle specific errors
                if error_msg == "token_revoked":
                    return {
                        "status": "failed",
                        "channel": channel,
                        "error": "bot token is revoked",
                        "details": "regenerate token in Slack workspace settings",
                    }
                elif error_msg == "no_permission":
                    return {
                        "status": "failed",
                        "channel": channel,
                        "error": "bot lacks permission to post in channel",
                        "details": "add bot to channel or grant chat:write scope",
                    }
                elif error_msg == "channel_not_found":
                    return {
                        "status": "failed",
                        "channel": channel,
                        "error": "channel not found",
                    }
                elif "rate_limited" in error_msg:
                    retry_after = result.get("retry_after", 60)
                    return {
                        "status": "failed",
                        "channel": channel,
                        "error": "rate limited",
                        "details": f"retry after {retry_after} seconds",
                    }
                else:
                    return {
                        "status": "failed",
                        "channel": channel,
                        "error": error_msg,
                    }

            # Success
            message_ts = result.get("ts", "")
            logger.info("slack_sent channel=%s ts=%s", channel, message_ts)

            return {
                "status": "sent",
                "channel": channel,
                "ts": message_ts,
            }

    except httpx.TimeoutException:
        logger.error("slack_timeout channel=%s", channel)
        return {
            "status": "failed",
            "channel": channel,
            "error": "Slack API request timeout",
            "details": "try again in a moment",
        }
    except httpx.HTTPError as e:
        logger.error("slack_http_error channel=%s: %s", channel, e)
        return {
            "status": "failed",
            "channel": channel,
            "error": "network error",
            "details": str(e)[:200],
        }
    except Exception as e:
        logger.error("slack_unexpected_error channel=%s: %s", channel, e)
        return {
            "status": "failed",
            "channel": channel,
            "error": "unexpected error",
            "details": str(e)[:200],
        }
