"""Per-tool rate limiter with configurable limits using token bucket algorithm."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from mcp.types import TextContent

logger = logging.getLogger("loom.tools.rate_limiter")

# Token bucket state: {tool_name: {tokens, last_refill, limit, throttle_count}}
_rate_limiters: dict[str, dict[str, Any]] = {}


def _get_limiter(tool_name: str, calls_per_minute: int = 60) -> dict[str, Any]:
    """Get or create token bucket for a tool."""
    if tool_name not in _rate_limiters:
        _rate_limiters[tool_name] = {
            "tokens": calls_per_minute,
            "last_refill": time.time(),
            "limit": calls_per_minute,
            "throttle_count": 0,
        }
    return _rate_limiters[tool_name]


def _refill_tokens(limiter: dict[str, Any]) -> None:
    """Refill tokens based on elapsed time since last refill."""
    now = time.time()
    elapsed = now - limiter["last_refill"]
    refill_rate = limiter["limit"] / 60.0  # tokens per second
    refill = refill_rate * elapsed
    limiter["tokens"] = min(limiter["limit"], limiter["tokens"] + refill)
    limiter["last_refill"] = now


async def research_ratelimit_check(tool_name: str) -> dict[str, Any]:
    """Check if a tool call is allowed under current rate limits.

    Uses token bucket algorithm: each tool gets N tokens/minute, each call costs 1 token.

    Args:
        tool_name: Name of the tool to check

    Returns:
        Dict with: allowed, tool, remaining_tokens, reset_in_seconds, limit
    """
    limiter = _get_limiter(tool_name)
    _refill_tokens(limiter)

    allowed = limiter["tokens"] >= 1.0
    if allowed:
        limiter["tokens"] -= 1.0

    reset_in = 60.0 - (time.time() - limiter["last_refill"])
    reset_in = max(0, reset_in)

    if not allowed:
        limiter["throttle_count"] += 1

    return {
        "allowed": allowed,
        "tool": tool_name,
        "remaining_tokens": round(limiter["tokens"], 2),
        "reset_in_seconds": round(reset_in, 2),
        "limit": limiter["limit"],
    }


async def research_ratelimit_configure(
    tool_name: str, calls_per_minute: int = 60
) -> dict[str, Any]:
    """Set custom rate limit for a specific tool.

    Args:
        tool_name: Name of the tool to configure
        calls_per_minute: New limit (default 60)

    Returns:
        Dict with: tool, new_limit, previous_limit
    """
    limiter = _get_limiter(tool_name)
    previous_limit = limiter["limit"]

    limiter["limit"] = calls_per_minute
    limiter["tokens"] = min(limiter["tokens"], calls_per_minute)

    return {
        "tool": tool_name,
        "new_limit": calls_per_minute,
        "previous_limit": previous_limit,
    }


async def research_ratelimit_status() -> dict[str, Any]:
    """Show rate limit status for all configured tools.

    Returns:
        Dict with: limiters list, total_configured, total_throttled_today
    """
    limiters_info = []
    total_throttled = 0

    for tool_name, limiter in sorted(_rate_limiters.items()):
        _refill_tokens(limiter)
        limiters_info.append({
            "tool": tool_name,
            "limit": limiter["limit"],
            "current_tokens": round(limiter["tokens"], 2),
            "last_refill": time.ctime(limiter["last_refill"]),
            "throttle_count": limiter["throttle_count"],
        })
        total_throttled += limiter["throttle_count"]

    return {
        "limiters": limiters_info,
        "total_configured": len(_rate_limiters),
        "total_throttled_today": total_throttled,
    }
