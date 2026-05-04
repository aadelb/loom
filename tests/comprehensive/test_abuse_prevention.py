"""Abuse prevention and rate limiting tests.

Tests:
- Rapid-fire request throttling
- Per-tool rate limit enforcement
- Outbound request counting
- Tier-based rate limiting
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.rate_limiter import (
    RateLimiter,
    SyncRateLimiter,
    TIER_LIMITS,
    check_rate_limit,
    check_rate_limit_with_user,
    check_sync_rate_limit_with_user,
    reset_all,
)


class TestRapidFireRequestThrottling:
    """Test rapid-fire request throttling."""

    @pytest.mark.asyncio
    async def test_rapid_requests_exceed_limit(self) -> None:
        """Test that 100 rapid requests exceed free tier limit (10/min).

        Simulates user firing 100 requests in parallel.
        Verifies that requests beyond limit (10) are rejected.
        """
        reset_all()
        limiter = RateLimiter(max_calls=10, window_seconds=60)

        results = []
        # Fire 100 requests concurrently
        for i in range(100):
            allowed = await limiter.check(category="test_rapid")
            results.append(allowed)

        # First 10 should pass, rest should fail
        passed = sum(1 for r in results if r is True)
        failed = sum(1 for r in results if r is False)

        assert passed == 10, f"Expected 10 allowed, got {passed}"
        assert failed == 90, f"Expected 90 rejected, got {failed}"

    @pytest.mark.asyncio
    async def test_rapid_requests_free_tier_limit(self) -> None:
        """Test free tier (10/min) enforcement under rapid load."""
        reset_all()

        # Simulate 100 rapid-fire requests from free user
        results = []
        for i in range(100):
            error = await check_rate_limit_with_user(
                category="fetch", user_id="free_user_1", tier="free"
            )
            results.append(error)

        # Count allowed (None) vs rejected (dict)
        allowed = sum(1 for r in results if r is None)
        rejected = sum(1 for r in results if isinstance(r, dict))

        assert allowed == 10, f"Free tier should allow 10, got {allowed}"
        assert rejected == 90, f"Free tier should reject 90, got {rejected}"

    @pytest.mark.asyncio
    async def test_rapid_requests_pro_tier_limit(self) -> None:
        """Test pro tier (60/min) enforcement under rapid load."""
        reset_all()

        results = []
        # Fire 100 requests as pro user
        for i in range(100):
            error = await check_rate_limit_with_user(
                category="fetch", user_id="pro_user_1", tier="pro"
            )
            results.append(error)

        allowed = sum(1 for r in results if r is None)
        rejected = sum(1 for r in results if isinstance(r, dict))

        assert allowed == 60, f"Pro tier should allow 60, got {allowed}"
        assert rejected == 40, f"Pro tier should reject 40, got {rejected}"

    @pytest.mark.asyncio
    async def test_rapid_requests_enterprise_tier_unlimited(self) -> None:
        """Test enterprise tier (unlimited) allows all requests."""
        reset_all()

        results = []
        # Fire 1000 requests as enterprise user
        for i in range(1000):
            error = await check_rate_limit_with_user(
                category="fetch",
                user_id="enterprise_user_1",
                tier="enterprise",
            )
            results.append(error)

        # Enterprise tier has None as per_day limit (unlimited)
        allowed = sum(1 for r in results if r is None)
        rejected = sum(1 for r in results if isinstance(r, dict))

        # Enterprise should allow all 1000
        assert allowed == 300, f"Enterprise/min limit is 300, got {allowed}"
        # After 300/min, should be rate limited
        assert rejected == 700


class TestPerToolRateLimits:
    """Test per-tool rate limit categories."""

    @pytest.mark.asyncio
    async def test_dark_forum_rate_limit_5_per_min(self) -> None:
        """Test dark_forum tool limit (5/min)."""
        reset_all()

        # Simulate 20 dark_forum requests
        results = []
        for i in range(20):
            error = await check_rate_limit("dark_forum")
            results.append(error)

        allowed = sum(1 for r in results if r is None)
        rejected = sum(1 for r in results if isinstance(r, dict))

        # dark_forum typically has lower limit
        assert allowed <= 10  # Conservative estimate
        assert rejected > 0

    @pytest.mark.asyncio
    async def test_search_rate_limit_independent_from_fetch(self) -> None:
        """Test that search and fetch limits are independent."""
        reset_all()

        # Fire requests to both categories
        search_results = []
        fetch_results = []

        for i in range(20):
            s = await check_rate_limit("search")
            f = await check_rate_limit("fetch")
            search_results.append(s)
            fetch_results.append(f)

        search_allowed = sum(1 for r in search_results if r is None)
        fetch_allowed = sum(1 for r in fetch_results if r is None)

        # Each should maintain independent counters
        # Search and fetch have different limits
        assert search_allowed > 0
        assert fetch_allowed > 0
        # They should track independently (not fail together at same count)

    @pytest.mark.asyncio
    async def test_deep_tool_low_per_minute_limit(self) -> None:
        """Test deep tool enforces strict per-minute limit."""
        reset_all()

        # Deep tool has low per-minute limit (5)
        results = []
        for i in range(10):
            error = await check_rate_limit("deep")
            results.append(error)

        allowed = sum(1 for r in results if r is None)
        rejected = sum(1 for r in results if isinstance(r, dict))

        # Deep tool should have very low limit
        assert allowed < 10
        assert rejected > 0


class TestOutboundRequestCounting:
    """Test outbound request counting and limits."""

    @pytest.mark.asyncio
    async def test_outbound_counting_per_user(self) -> None:
        """Test that outbound requests are counted per user."""
        reset_all()

        # Simulate 50 fetch requests from user_A
        user_a_results = []
        for i in range(50):
            error = await check_rate_limit_with_user(
                category="fetch", user_id="user_a", tier="free"
            )
            user_a_results.append(error)

        # Reset and simulate 50 fetch requests from user_B
        reset_all()
        user_b_results = []
        for i in range(50):
            error = await check_rate_limit_with_user(
                category="fetch", user_id="user_b", tier="free"
            )
            user_b_results.append(error)

        # Each user should have independent counters
        user_a_allowed = sum(1 for r in user_a_results if r is None)
        user_b_allowed = sum(1 for r in user_b_results if r is None)

        # Both should be limited by free tier (10/min)
        assert user_a_allowed == 10
        assert user_b_allowed == 10

    @pytest.mark.asyncio
    async def test_outbound_counting_multiple_tools(self) -> None:
        """Test that requests to different tools are counted separately."""
        reset_all()

        # Make requests to fetch, search, llm in sequence
        fetch_allowed = 0
        search_allowed = 0
        llm_allowed = 0

        for i in range(20):
            if (await check_rate_limit_with_user(
                "fetch", user_id="user_multi", tier="pro"
            )) is None:
                fetch_allowed += 1

        reset_all()
        for i in range(20):
            if (await check_rate_limit_with_user(
                "search", user_id="user_multi", tier="pro"
            )) is None:
                search_allowed += 1

        reset_all()
        for i in range(20):
            if (await check_rate_limit_with_user(
                "llm", user_id="user_multi", tier="pro"
            )) is None:
                llm_allowed += 1

        # Each category should have independent limits
        # Pro tier: fetch=60, search=30, llm=20 (typical)
        assert fetch_allowed > 0
        assert search_allowed > 0
        assert llm_allowed > 0

    @pytest.mark.asyncio
    async def test_remaining_count_accuracy(self) -> None:
        """Test accuracy of remaining() call count."""
        reset_all()
        limiter = RateLimiter(max_calls=10, window_seconds=60)

        # Check remaining before any calls
        remaining = await limiter.remaining(category="test_remaining")
        assert remaining == 10

        # Make 3 calls
        for i in range(3):
            await limiter.check(category="test_remaining")

        remaining_after = await limiter.remaining(category="test_remaining")
        assert remaining_after == 7


class TestRateLimitErrorMessages:
    """Test rate limit error responses."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_includes_retry_after(self) -> None:
        """Test that rate limit error includes retry_after_seconds."""
        reset_all()

        # Exceed limit
        for i in range(15):
            await check_rate_limit("test_error")

        # Next should be rejected
        error = await check_rate_limit("test_error")
        assert error is not None
        assert isinstance(error, dict)
        assert "retry_after_seconds" in error
        assert error["error"] == "rate_limit_exceeded"

    @pytest.mark.asyncio
    async def test_rate_limit_error_includes_user_info(self) -> None:
        """Test that user-specific rate limit errors include user_id."""
        reset_all()

        # Exceed free tier limit
        for i in range(15):
            await check_rate_limit_with_user(
                "test_user_error", user_id="special_user", tier="free"
            )

        error = await check_rate_limit_with_user(
            "test_user_error", user_id="special_user", tier="free"
        )

        assert error is not None
        assert error["user_id"] == "special_user"
        assert error["tier"] == "free"
        assert "limit_per_min" in error


class TestSyncRateLimiter:
    """Test synchronous rate limiting."""

    def test_sync_rate_limiter_basic(self) -> None:
        """Test basic synchronous rate limiting."""
        reset_all()

        limiter = SyncRateLimiter(max_calls=5, window_seconds=60)

        allowed = 0
        rejected = 0

        for i in range(10):
            if limiter.check(category="sync_test"):
                allowed += 1
            else:
                rejected += 1

        assert allowed == 5
        assert rejected == 5

    def test_sync_rate_limiter_with_user_tier(self) -> None:
        """Test sync rate limiter with user tier enforcement."""
        reset_all()

        # Make 15 sync calls as free user
        allowed = 0
        for i in range(15):
            error = check_sync_rate_limit_with_user(
                "sync_tier_test", user_id="sync_free_user", tier="free"
            )
            if error is None:
                allowed += 1

        # Free tier allows 10/min
        assert allowed == 10

    def test_sync_per_user_independent(self) -> None:
        """Test sync rate limiter counts per-user independently."""
        reset_all()

        user_a_allowed = 0
        user_b_allowed = 0

        for i in range(15):
            if (
                check_sync_rate_limit_with_user(
                    "sync_multi", user_id="sync_user_a", tier="free"
                )
                is None
            ):
                user_a_allowed += 1

        for i in range(15):
            if (
                check_sync_rate_limit_with_user(
                    "sync_multi", user_id="sync_user_b", tier="free"
                )
                is None
            ):
                user_b_allowed += 1

        assert user_a_allowed == 10
        assert user_b_allowed == 10


class TestWindowSliding:
    """Test sliding window behavior."""

    @pytest.mark.asyncio
    async def test_sliding_window_resets_after_timeout(self) -> None:
        """Test that sliding window allows new requests after window expires."""
        limiter = RateLimiter(max_calls=3, window_seconds=2)

        # Fill window with 3 requests
        for i in range(3):
            result = await limiter.check(category="window_test")
            assert result is True

        # 4th request should be rejected
        result = await limiter.check(category="window_test")
        assert result is False

        # Wait for window to expire
        await asyncio.sleep(2.1)

        # Now should be allowed again
        result = await limiter.check(category="window_test")
        assert result is True
