"""Granular per-tool rate limiting with sliding-window counters.

Supports expensive/Tor-based tools (dark_forum, onion_discover, sandbox_run)
with lower limits, normal tools with standard limits, and a configurable default.

Uses Redis if available (distributed, fast) with in-memory fallback.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tool_rate_limiter")


TOOL_RATE_LIMITS: dict[str, int] = {
    # Expensive Tor-based tools
    "research_dark_forum": 5,  # 5/min — expensive, Tor-based forum scraping
    "research_onion_discover": 3,  # 3/min — Tor crawling, slow
    "research_sandbox_run": 2,  # 2/min — Docker execution, resource-intensive
    # Heavy multi-provider tools
    "research_full_pipeline": 10,  # 10/min — complex multi-stage pipeline
    "research_ask_all_models": 5,  # 5/min — hits all LLM providers
    # Normal research tools
    "research_fetch": 60,  # 60/min — normal web fetch
    "research_spider": 40,  # 40/min — concurrent multi-URL
    "research_search": 30,  # 30/min — search APIs
    "research_deep": 15,  # 15/min — 12-stage pipeline
    "research_markdown": 50,  # 50/min — Crawl4AI extraction
    "research_github": 50,  # 50/min — gh CLI lookups
    "research_camoufox": 10,  # 10/min — Firefox stealth mode
    "research_botasaurus": 8,  # 8/min — Botasaurus escalation
    "research_llm_summarize": 30,  # 30/min — LLM summarization
    "research_llm_extract": 30,  # 30/min — LLM extraction
    "research_llm_classify": 30,  # 30/min — LLM classification
    "research_llm_translate": 30,  # 30/min — LLM translation
    "research_llm_expand": 30,  # 30/min — LLM expansion
    "research_llm_answer": 30,  # 30/min — LLM Q&A
    "research_llm_embed": 50,  # 50/min — LLM embeddings
    "research_llm_chat": 40,  # 40/min — LLM chat
    # Intelligence & threat tools
    "research_threat_intel": 20,  # 20/min
    "research_leak_scan": 10,  # 10/min — breach databases
    "research_crypto_trace": 8,  # 8/min — blockchain analysis
    "research_social_graph": 15,  # 15/min — relationship mapping
    "research_infra_correlator": 12,  # 12/min — infrastructure linking
    # Academic & compliance tools
    "research_citation_analysis": 20,  # 20/min
    "research_retraction_check": 15,  # 15/min
    "research_grant_forensics": 10,  # 10/min
    # Safety & compliance tools (low volume expected)
    "research_prompt_injection_test": 5,  # 5/min — AI safety testing
    "research_model_fingerprint": 8,  # 8/min
    "research_bias_probe": 8,  # 8/min
    "research_safety_filter_map": 6,  # 6/min
    "research_compliance_check": 10,  # 10/min
    "research_hallucination_benchmark": 3,  # 3/min — compute-intensive
    "research_adversarial_robustness": 3,  # 3/min — compute-intensive
    # Utility & admin tools (high volume ok)
    "research_cache_stats": 120,  # 120/min — read-only
    "research_cache_clear": 5,  # 5/min — write operation
    "research_config_get": 120,  # 120/min — read-only
    "research_config_set": 10,  # 10/min — write operation
    "research_session_open": 20,  # 20/min
    "research_session_list": 120,  # 120/min — read-only
    "research_session_close": 20,  # 20/min
    "research_health_check": 120,  # 120/min — monitoring
    "research_rate_limits": 120,  # 120/min — read-only
}

# Default limit for tools not in TOOL_RATE_LIMITS
DEFAULT_RATE_LIMIT = 120  # 120/min for unlisted tools


class ToolRateLimiter:
    """Sliding-window rate limiter for individual tools.

    Tracks request timestamps per tool and user, enforcing per-minute limits.
    Uses asyncio.Lock for async-safe access with optional Redis backend.
    """

    def __init__(self, window_seconds: int = 60) -> None:
        """Initialize rate limiter.

        Args:
            window_seconds: Time window for rate limiting (default: 60 seconds = 1 minute).
        """
        self.window_seconds = window_seconds
        # Dict[tool_name][user_id] = [timestamps]
        self._calls: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._lock = asyncio.Lock()

    async def check(
        self, tool_name: str, user_id: str = "default"
    ) -> tuple[bool, int]:
        """Check if tool call is allowed for user.

        Args:
            tool_name: Name of the tool being called.
            user_id: User ID for per-user limiting (default: "default" for global).

        Returns:
            Tuple of (allowed: bool, retry_after_seconds: int).
            If allowed=False, retry_after_seconds indicates when to retry.
        """
        limit = TOOL_RATE_LIMITS.get(tool_name, DEFAULT_RATE_LIMIT)

        # Try Redis first if available
        try:
            from loom.redis_store import get_redis_store

            store = await get_redis_store()
            if store._redis_available:
                allowed = await store.rate_limit_check(
                    user_id, f"tool:{tool_name}", limit, self.window_seconds
                )
                if not allowed:
                    logger.debug(
                        "tool_rate_limit_exceeded_redis",
                        tool_name=tool_name,
                        user_id=user_id,
                        limit=limit,
                    )
                    return False, self.window_seconds
                logger.debug(
                    "tool_rate_limit_allowed_redis",
                    tool_name=tool_name,
                    user_id=user_id,
                    limit=limit,
                )
                return True, 0
        except Exception as e:
            logger.debug(
                "tool_rate_limit_redis_fallback",
                tool_name=tool_name,
                user_id=user_id,
                error=str(e),
            )
            pass  # Fall back to in-memory

        # In-memory sliding window (fallback or primary if Redis unavailable)
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            # Get timestamps for this tool+user within window
            timestamps = self._calls[tool_name][user_id]
            window = [t for t in timestamps if t > cutoff]

            if len(window) >= limit:
                # Rate limit exceeded
                logger.debug(
                    "tool_rate_limit_exceeded",
                    tool_name=tool_name,
                    user_id=user_id,
                    limit=limit,
                    current_count=len(window),
                )
                return False, self.window_seconds

            # Allow call and record timestamp
            window.append(now)
            self._calls[tool_name][user_id] = window

            # Prune old entries to prevent unbounded growth
            if len(window) > limit * 2:
                self._calls[tool_name][user_id] = window[-limit * 2 :]

            return True, 0

    async def get_remaining(
        self, tool_name: str, user_id: str = "default"
    ) -> int:
        """Get number of calls remaining in current window.

        Args:
            tool_name: Name of the tool.
            user_id: User ID for per-user limiting.

        Returns:
            Number of calls remaining before hitting rate limit.
        """
        limit = TOOL_RATE_LIMITS.get(tool_name, DEFAULT_RATE_LIMIT)

        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds

            timestamps = self._calls[tool_name][user_id]
            window = [t for t in timestamps if t > cutoff]

            return max(0, limit - len(window))

    def reset_all(self) -> None:
        """Reset all rate limit counters (for testing)."""
        self._calls.clear()


# Global instance
_instance: ToolRateLimiter | None = None
_instance_lock = asyncio.Lock()


async def get_tool_rate_limiter() -> ToolRateLimiter:
    """Get or create the global ToolRateLimiter instance."""
    global _instance
    if _instance is None:
        async with _instance_lock:
            if _instance is None:
                _instance = ToolRateLimiter(window_seconds=60)
    return _instance


async def check_tool_rate_limit(
    tool_name: str, user_id: str = "default"
) -> dict[str, Any] | None:
    """Check if tool call is allowed. Return error dict if exceeded, None if OK.

    Args:
        tool_name: Name of the tool being called.
        user_id: User ID for per-user limiting.

    Returns:
        Error dict with rate limit details if exceeded, None if OK.
    """
    limiter = await get_tool_rate_limiter()
    allowed, retry_after = await limiter.check(tool_name, user_id)

    if not allowed:
        limit = TOOL_RATE_LIMITS.get(tool_name, DEFAULT_RATE_LIMIT)
        logger.warning(
            "tool_rate_limit_exceeded tool_name=%s user_id=%s limit=%d",
            tool_name,
            user_id,
            limit,
        )
        return {
            "error": "rate_limit_exceeded",
            "tool": tool_name,
            "user_id": user_id,
            "limit_per_min": limit,
            "retry_after_seconds": retry_after,
            "message": f"Tool '{tool_name}' rate limit ({limit}/min) exceeded. Retry after {retry_after}s.",
        }

    return None


async def research_rate_limits() -> dict[str, Any]:
    """MCP tool: Show all tool rate limits and current usage.

    Returns:
        Dict with:
        - tool_limits: All configured tool limits
        - default_limit: Default limit for unconfigured tools
        - usage_stats: Current usage per tool (if available)
    """
    limiter = await get_tool_rate_limiter()

    # Build usage stats from in-memory counters
    usage_stats: dict[str, dict[str, Any]] = {}
    now = time.time()
    cutoff = now - 60  # Last minute

    for tool_name, user_dict in limiter._calls.items():
        for user_id, timestamps in user_dict.items():
            window = [t for t in timestamps if t > cutoff]
            if window:  # Only include tools with recent activity
                key = f"{tool_name}:{user_id}"
                limit = TOOL_RATE_LIMITS.get(tool_name, DEFAULT_RATE_LIMIT)
                usage_stats[key] = {
                    "tool": tool_name,
                    "user": user_id,
                    "calls_in_last_minute": len(window),
                    "limit_per_min": limit,
                    "remaining": limit - len(window),
                }

    return {
        "tool_limits": TOOL_RATE_LIMITS,
        "default_limit": DEFAULT_RATE_LIMIT,
        "window_seconds": limiter.window_seconds,
        "usage_stats": usage_stats,
        "total_tools_configured": len(TOOL_RATE_LIMITS),
    }
