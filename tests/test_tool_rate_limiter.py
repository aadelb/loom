"""Tests for granular per-tool rate limiting.

Tests the ToolRateLimiter class and check_tool_rate_limit function with
per-tool limits (expensive tools, normal tools, utilities).
"""

import asyncio
import pytest
from loom.tool_rate_limiter import (
    ToolRateLimiter,
    TOOL_RATE_LIMITS,
    DEFAULT_RATE_LIMIT,
    check_tool_rate_limit,
    research_rate_limits,
    get_tool_rate_limiter,
)


@pytest.mark.unit
async def test_tool_rate_limiter_creation():
    """Test creating a ToolRateLimiter instance."""
    limiter = ToolRateLimiter(window_seconds=60)
    assert limiter.window_seconds == 60
    assert limiter._calls == {}


@pytest.mark.unit
async def test_dark_forum_low_limit():
    """Test that dark_forum has low rate limit (5/min)."""
    assert TOOL_RATE_LIMITS["research_dark_forum"] == 5
    assert TOOL_RATE_LIMITS["research_onion_discover"] == 3
    assert TOOL_RATE_LIMITS["research_sandbox_run"] == 2


@pytest.mark.unit
async def test_normal_tools_higher_limits():
    """Test that normal tools have higher rate limits."""
    assert TOOL_RATE_LIMITS["research_fetch"] == 60
    assert TOOL_RATE_LIMITS["research_search"] == 30
    assert TOOL_RATE_LIMITS["research_deep"] == 15


@pytest.mark.unit
async def test_utility_tools_high_limits():
    """Test that utility/read-only tools have high limits."""
    assert TOOL_RATE_LIMITS["research_cache_stats"] == 120
    assert TOOL_RATE_LIMITS["research_config_get"] == 120
    assert TOOL_RATE_LIMITS["research_health_check"] == 120


@pytest.mark.unit
async def test_default_limit():
    """Test that default limit is 120/min."""
    assert DEFAULT_RATE_LIMIT == 120


@pytest.mark.unit
async def test_tool_rate_limiter_check_allowed():
    """Test that check returns (True, 0) when allowed."""
    limiter = ToolRateLimiter(window_seconds=60)
    allowed, retry_after = await limiter.check("research_fetch", user_id="user1")
    assert allowed is True
    assert retry_after == 0


@pytest.mark.unit
async def test_tool_rate_limiter_check_limited():
    """Test that check returns (False, 60) when rate limited."""
    limiter = ToolRateLimiter(window_seconds=60)
    tool_name = "research_fetch"
    limit = TOOL_RATE_LIMITS[tool_name]

    # Make calls up to the limit
    for i in range(limit):
        allowed, _ = await limiter.check(tool_name, user_id="user1")
        assert allowed is True

    # Next call should be rate limited
    allowed, retry_after = await limiter.check(tool_name, user_id="user1")
    assert allowed is False
    assert retry_after == 60


@pytest.mark.unit
async def test_tool_rate_limiter_per_user():
    """Test that rate limiting is per-user."""
    limiter = ToolRateLimiter(window_seconds=60)
    tool_name = "research_search"
    limit = TOOL_RATE_LIMITS[tool_name]

    # User1: fill their quota
    for i in range(limit):
        allowed, _ = await limiter.check(tool_name, user_id="user1")
        assert allowed is True

    # User1: next call is limited
    allowed, retry_after = await limiter.check(tool_name, user_id="user1")
    assert allowed is False

    # User2: should still have quota
    allowed, retry_after = await limiter.check(tool_name, user_id="user2")
    assert allowed is True


@pytest.mark.unit
async def test_expensive_tool_low_limit():
    """Test that expensive tools have lower limits."""
    limiter = ToolRateLimiter(window_seconds=60)
    dark_forum_limit = TOOL_RATE_LIMITS["research_dark_forum"]
    fetch_limit = TOOL_RATE_LIMITS["research_fetch"]

    assert dark_forum_limit == 5
    assert fetch_limit == 60
    assert dark_forum_limit < fetch_limit


@pytest.mark.unit
async def test_get_remaining():
    """Test get_remaining returns correct count."""
    limiter = ToolRateLimiter(window_seconds=60)
    tool_name = "research_fetch"
    limit = TOOL_RATE_LIMITS[tool_name]

    # Initially, all should be remaining
    remaining = await limiter.get_remaining(tool_name, user_id="user1")
    assert remaining == limit

    # After one call, should have limit - 1 remaining
    await limiter.check(tool_name, user_id="user1")
    remaining = await limiter.get_remaining(tool_name, user_id="user1")
    assert remaining == limit - 1

    # Make calls to reach limit
    for i in range(limit - 1):
        await limiter.check(tool_name, user_id="user1")

    # Should have 0 remaining
    remaining = await limiter.get_remaining(tool_name, user_id="user1")
    assert remaining == 0


@pytest.mark.unit
async def test_check_tool_rate_limit_allowed():
    """Test check_tool_rate_limit returns None when allowed."""
    # Reset the global instance
    from loom import tool_rate_limiter
    tool_rate_limiter._instance = None

    result = await check_tool_rate_limit("research_fetch", user_id="testuser")
    assert result is None


@pytest.mark.unit
async def test_check_tool_rate_limit_exceeded():
    """Test check_tool_rate_limit returns error dict when exceeded."""
    from loom import tool_rate_limiter
    tool_rate_limiter._instance = None  # Reset

    limiter = await get_tool_rate_limiter()
    tool_name = "research_deep"
    limit = TOOL_RATE_LIMITS[tool_name]

    # Fill quota
    for i in range(limit):
        await check_tool_rate_limit(tool_name, user_id="testuser2")

    # Next check should return error dict
    result = await check_tool_rate_limit(tool_name, user_id="testuser2")
    assert result is not None
    assert result["error"] == "rate_limit_exceeded"
    assert result["tool"] == tool_name
    assert result["limit_per_min"] == limit
    assert "retry_after_seconds" in result
    assert "message" in result


@pytest.mark.unit
async def test_research_rate_limits_response():
    """Test research_rate_limits returns proper response."""
    result = await research_rate_limits()

    assert "tool_limits" in result
    assert "default_limit" in result
    assert "window_seconds" in result
    assert "usage_stats" in result
    assert "total_tools_configured" in result

    assert result["default_limit"] == DEFAULT_RATE_LIMIT
    assert result["window_seconds"] == 60
    assert result["total_tools_configured"] == len(TOOL_RATE_LIMITS)


@pytest.mark.unit
async def test_unlisted_tool_uses_default():
    """Test that unlisted tools use DEFAULT_RATE_LIMIT."""
    limiter = ToolRateLimiter(window_seconds=60)
    tool_name = "research_some_new_tool"

    # Should use DEFAULT_RATE_LIMIT
    for i in range(DEFAULT_RATE_LIMIT):
        allowed, _ = await limiter.check(tool_name, user_id="user1")
        assert allowed is True

    # Next call should be limited
    allowed, retry_after = await limiter.check(tool_name, user_id="user1")
    assert allowed is False


@pytest.mark.unit
async def test_reset_all():
    """Test reset_all clears all counters."""
    limiter = ToolRateLimiter(window_seconds=60)
    tool_name = "research_fetch"

    # Make a call
    await limiter.check(tool_name, user_id="user1")
    assert len(limiter._calls) > 0

    # Reset
    limiter.reset_all()
    assert limiter._calls == {}

    # After reset, should allow calls again
    allowed, _ = await limiter.check(tool_name, user_id="user1")
    assert allowed is True
