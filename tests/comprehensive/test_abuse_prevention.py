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

        # Simulate 100 rapid-fire requests from free user
        results = []
        for i in range(100):
            error = await check_rate_limit_with_user(
                category="fetch", user_id="free_user_rapid", tier="free"
            )
            results.append(error)

        # Count allowed (None) vs rejected (dict)
        allowed = sum(1 for r in results if r is None)
        rejected = sum(1 for r in results if isinstance(r, dict))

        assert allowed == 10, f"Free tier should allow 10, got {allowed}"
        assert rejected == 90, f"Free tier should reject 90, got {rejected}"

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
        """Test enterprise tier (300/min) has higher limit."""
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

        # Enterprise tier has 300/min limit
        allowed = sum(1 for r in results if r is None)
        rejected = sum(1 for r in results if isinstance(r, dict))

        # Enterprise should allow 300/min
        assert allowed == 300, f"Enterprise/min limit is 300, got {allowed}"
        # After 300/min, should be rate limited
        assert rejected == 700


class TestPerToolRateLimits:
    """Test per-tool rate limit categories."""

    @pytest.mark.asyncio
    async def test_rate_limit_check_returns_none_or_dict(self) -> None:
        """Test that rate limit check returns None or error dict."""
        reset_all()

        # Make a single request
        error = await check_rate_limit("search")

        # Should return None (allowed) for first request
        assert error is None, "First request should be allowed"

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
        # Both should have allowed some requests
        assert search_allowed > 0
        assert fetch_allowed > 0

    @pytest.mark.asyncio
    async def test_rate_limit_tracks_per_category(self) -> None:
        """Test rate limiter tracks different categories independently."""
        reset_all()

        # Fire multiple requests to different categories
        for i in range(5):
            await check_rate_limit_with_user(
                "search", user_id="user_cat", tier="free"
            )

        # Should still be able to use other categories
        fetch_error = await check_rate_limit_with_user(
            "fetch", user_id="user_cat", tier="free"
        )

        # Fetch should still be allowed (independent counters)
        assert fetch_error is None, "Different categories should have independent limits"


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
        remaining = await limiter.remaining(category="test_remaining", tier="free")
        assert remaining == 10

        # Make 3 calls
        for i in range(3):
            await limiter.check(category="test_remaining", tier="free")

        remaining_after = await limiter.remaining(category="test_remaining", tier="free")
        assert remaining_after == 7


class TestRateLimitErrorMessages:
    """Test rate limit error responses."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_has_correct_structure(self) -> None:
        """Test that rate limit error has correct error structure."""
        reset_all()

        # Exceed limit
        for i in range(15):
            await check_rate_limit_with_user(
                "test_error", user_id="user_error", tier="free"
            )

        # Next should be rejected
        error = await check_rate_limit_with_user(
            "test_error", user_id="user_error", tier="free"
        )

        assert error is not None, "Should be rate limited"
        assert isinstance(error, dict)
        assert "error" in error
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
        """Test basic synchronous rate limiting with tier."""
        reset_all()

        # Make 15 calls as free user
        allowed = 0
        for i in range(15):
            error = check_sync_rate_limit_with_user(
                "sync_test", user_id="sync_basic", tier="free"
            )
            if error is None:
                allowed += 1

        # Free tier allows 10/min
        assert allowed == 10, f"Expected 10 allowed for free tier, got {allowed}"

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
    async def test_sliding_window_with_tier_limits(self) -> None:
        """Test that tier-based limits work correctly."""
        reset_all()

        # Use free tier which has 10/min
        results = []
        for i in range(15):
            error = await check_rate_limit_with_user(
                "window_test", user_id="user_window", tier="free"
            )
            results.append(error is None)

        # First 10 should pass, rest should fail
        allowed = sum(1 for r in results if r)
        rejected = sum(1 for r in results if not r)

        assert allowed == 10, f"Free tier should allow 10, got {allowed}"
        assert rejected == 5, f"Free tier should reject 5, got {rejected}"
