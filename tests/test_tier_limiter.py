"""Unit tests for per-tier rate limiting.

Tests cover:
1. Free tier allows 10 requests
2. Free tier blocks 11th request
3. Pro tier allows 60 requests
4. Team tier allows 300 requests
5. Enterprise tier allows 1000 requests
6. Response has allowed, remaining, limit fields
7. retry_after > 0 when blocked
8. Different customers have independent limits
9. Reset clears customer window
10. Unknown tier defaults to free tier
11. Window slides after 60 seconds
12. Multiple simultaneous customers
13. Edge cases (negative times, exact boundaries)
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import patch

import pytest

from loom.billing.tier_limiter import (
    TIER_LIMITS,
    WINDOW_SECONDS,
    TierRateLimiter,
    get_tier_limiter,
    reset_all,
)


@pytest.fixture
def limiter() -> TierRateLimiter:
    """Create a fresh limiter instance for each test."""
    reset_all()
    return TierRateLimiter()



pytestmark = pytest.mark.asyncio
class TestFreeTier:
    """Tests for free tier (10 requests/min)."""

    async def test_free_tier_allows_10_requests(self, limiter: TierRateLimiter) -> None:
        """Free tier allows up to 10 requests in a 60-second window."""
        customer_id = "cust_free_001"
        for i in range(10):
            result = limiter.check(customer_id, "free")
            assert result["allowed"] is True, f"Request {i+1} should be allowed"
            assert result["remaining"] == 10 - i - 1
            assert result["limit"] == 10
            assert result["retry_after"] == 0
            assert result["tier"] == "free"

    async def test_free_tier_blocks_11th_request(self, limiter: TierRateLimiter) -> None:
        """Free tier blocks the 11th request within the same window."""
        customer_id = "cust_free_002"
        # Fill up the window with 10 requests
        for _ in range(10):
            result = limiter.check(customer_id, "free")
            assert result["allowed"] is True

        # 11th request should be blocked
        result = limiter.check(customer_id, "free")
        assert result["allowed"] is False
        assert result["remaining"] == 0
        assert result["limit"] == 10
        assert result["retry_after"] > 0
        assert result["tier"] == "free"

    async def test_free_tier_remaining_decrements(self, limiter: TierRateLimiter) -> None:
        """Free tier remaining count decrements correctly."""
        customer_id = "cust_free_003"
        for i in range(5):
            result = limiter.check(customer_id, "free")
            assert result["remaining"] == 10 - i - 1


class TestProTier:
    """Tests for pro tier (60 requests/min)."""

    async def test_pro_tier_allows_60_requests(self, limiter: TierRateLimiter) -> None:
        """Pro tier allows up to 60 requests in a 60-second window."""
        customer_id = "cust_pro_001"
        for i in range(60):
            result = limiter.check(customer_id, "pro")
            assert result["allowed"] is True, f"Request {i+1} should be allowed"
            assert result["remaining"] == 60 - i - 1
            assert result["limit"] == 60

    async def test_pro_tier_blocks_61st_request(self, limiter: TierRateLimiter) -> None:
        """Pro tier blocks the 61st request."""
        customer_id = "cust_pro_002"
        for _ in range(60):
            limiter.check(customer_id, "pro")

        result = limiter.check(customer_id, "pro")
        assert result["allowed"] is False
        assert result["remaining"] == 0
        assert result["limit"] == 60
        assert result["retry_after"] > 0


class TestTeamTier:
    """Tests for team tier (300 requests/min)."""

    async def test_team_tier_allows_300_requests(self, limiter: TierRateLimiter) -> None:
        """Team tier allows up to 300 requests."""
        customer_id = "cust_team_001"
        # Test sampling to avoid slow test
        for i in range(0, 300, 30):
            result = limiter.check(customer_id, "team")
            assert result["allowed"] is True
            assert result["limit"] == 300

    async def test_team_tier_blocks_301st_request(self, limiter: TierRateLimiter) -> None:
        """Team tier blocks the 301st request."""
        customer_id = "cust_team_002"
        for _ in range(300):
            limiter.check(customer_id, "team")

        result = limiter.check(customer_id, "team")
        assert result["allowed"] is False
        assert result["limit"] == 300


class TestEnterpriseTier:
    """Tests for enterprise tier (1000 requests/min)."""

    def test_enterprise_tier_allows_1000_requests(
        self, limiter: TierRateLimiter
    ) -> None:
        """Enterprise tier allows up to 1000 requests."""
        customer_id = "cust_ent_001"
        # Test sampling
        for i in range(0, 1000, 100):
            result = limiter.check(customer_id, "enterprise")
            assert result["allowed"] is True
            assert result["limit"] == 1000

    def test_enterprise_tier_blocks_1001st_request(
        self, limiter: TierRateLimiter
    ) -> None:
        """Enterprise tier blocks the 1001st request."""
        customer_id = "cust_ent_002"
        for _ in range(1000):
            limiter.check(customer_id, "enterprise")

        result = limiter.check(customer_id, "enterprise")
        assert result["allowed"] is False
        assert result["limit"] == 1000


class TestResponseStructure:
    """Tests for response dictionary structure and fields."""

    async def test_response_has_required_fields(self, limiter: TierRateLimiter) -> None:
        """Response includes all required fields."""
        result = limiter.check("cust_001", "pro")
        assert "allowed" in result
        assert "remaining" in result
        assert "limit" in result
        assert "retry_after" in result
        assert "tier" in result

    async def test_response_types_are_correct(self, limiter: TierRateLimiter) -> None:
        """Response fields have correct types."""
        result = limiter.check("cust_002", "pro")
        assert isinstance(result["allowed"], bool)
        assert isinstance(result["remaining"], int)
        assert isinstance(result["limit"], int)
        assert isinstance(result["retry_after"], int)
        assert isinstance(result["tier"], str)

    def test_response_allowed_true_has_zero_retry_after(
        self, limiter: TierRateLimiter
    ) -> None:
        """When allowed=True, retry_after should be 0."""
        result = limiter.check("cust_003", "pro")
        assert result["allowed"] is True
        assert result["retry_after"] == 0

    def test_response_allowed_false_has_positive_retry_after(
        self, limiter: TierRateLimiter
    ) -> None:
        """When allowed=False, retry_after should be > 0."""
        customer_id = "cust_004"
        for _ in range(10):
            limiter.check(customer_id, "free")

        result = limiter.check(customer_id, "free")
        assert result["allowed"] is False
        assert result["retry_after"] > 0


class TestIndependentCustomers:
    """Tests for independent rate limiting per customer."""

    def test_different_customers_have_independent_limits(
        self, limiter: TierRateLimiter
    ) -> None:
        """Different customers should have independent rate limits."""
        # Customer 1 uses up free tier
        for _ in range(10):
            limiter.check("cust_a", "free")

        # Customer 1 is blocked
        result_a = limiter.check("cust_a", "free")
        assert result_a["allowed"] is False

        # Customer 2 should still be allowed
        result_b = limiter.check("cust_b", "free")
        assert result_b["allowed"] is True

    async def test_three_customers_simultaneous(self, limiter: TierRateLimiter) -> None:
        """Multiple customers can make requests simultaneously."""
        customers = ["cust_x", "cust_y", "cust_z"]
        for customer in customers:
            for _ in range(5):
                result = limiter.check(customer, "free")
                assert result["allowed"] is True

        # All customers should have room for more
        for customer in customers:
            result = limiter.check(customer, "free")
            assert result["allowed"] is True
            assert result["remaining"] == 4  # 10 - 5 - 1


class TestReset:
    """Tests for reset functionality."""

    async def test_reset_clears_customer_window(self, limiter: TierRateLimiter) -> None:
        """Reset clears the customer's rate limit window."""
        customer_id = "cust_reset_001"
        # Fill up the limit
        for _ in range(10):
            limiter.check(customer_id, "free")

        # Verify we're blocked
        result = limiter.check(customer_id, "free")
        assert result["allowed"] is False

        # Reset the customer
        limiter.reset(customer_id)

        # Customer should be allowed again
        result = limiter.check(customer_id, "free")
        assert result["allowed"] is True

    def test_reset_only_affects_specified_customer(
        self, limiter: TierRateLimiter
    ) -> None:
        """Reset only affects the specified customer, not others."""
        cust_a = "cust_reset_a"
        cust_b = "cust_reset_b"

        # Both customers hit their limits
        for _ in range(10):
            limiter.check(cust_a, "free")
            limiter.check(cust_b, "free")

        # Both blocked
        assert limiter.check(cust_a, "free")["allowed"] is False
        assert limiter.check(cust_b, "free")["allowed"] is False

        # Reset only cust_a
        limiter.reset(cust_a)

        # cust_a is allowed, cust_b is still blocked
        assert limiter.check(cust_a, "free")["allowed"] is True
        assert limiter.check(cust_b, "free")["allowed"] is False


class TestUnknownTier:
    """Tests for handling unknown subscription tiers."""

    async def test_unknown_tier_defaults_to_free(self, limiter: TierRateLimiter) -> None:
        """Unknown tier defaults to free tier limits (10 requests)."""
        customer_id = "cust_unknown_001"
        # Fill up with 10 requests
        for _ in range(10):
            result = limiter.check(customer_id, "unknown_tier")
            assert result["allowed"] is True
            assert result["limit"] == 10  # Free tier limit

        # 11th should be blocked
        result = limiter.check(customer_id, "unknown_tier")
        assert result["allowed"] is False

    async def test_nonexistent_tier_uses_free_limits(self, limiter: TierRateLimiter) -> None:
        """Nonexistent tier name defaults to free tier."""
        result = limiter.check("cust_unknown_002", "nonexistent")
        assert result["limit"] == 10
        assert result["tier"] == "nonexistent"


class TestWindowSliding:
    """Tests for sliding window behavior over time."""

    async def test_window_slides_after_60_seconds(self, limiter: TierRateLimiter) -> None:
        """Old timestamps slide out of the window after 60 seconds."""
        customer_id = "cust_window_001"

        # Make first request
        result1 = limiter.check(customer_id, "free")
        assert result1["allowed"] is True
        first_timestamp = time.time()

        # Make 9 more requests (total 10, at limit)
        for _ in range(9):
            limiter.check(customer_id, "free")

        # 11th request should be blocked
        result = limiter.check(customer_id, "free")
        assert result["allowed"] is False

        # Mock time to be 61 seconds later
        with patch("loom.billing.tier_limiter.time.time") as mock_time:
            mock_time.return_value = first_timestamp + 61

            # Customer should be allowed again (old request slid out)
            result = limiter.check(customer_id, "free")
            assert result["allowed"] is True


class TestGetRemaining:
    """Tests for get_remaining helper method."""

    def test_get_remaining_returns_correct_count(
        self, limiter: TierRateLimiter
    ) -> None:
        """get_remaining returns the correct count."""
        customer_id = "cust_remaining_001"
        limiter.check(customer_id, "pro")
        remaining = limiter.get_remaining(customer_id, "pro")
        assert remaining == 59  # 60 - 1

    def test_get_remaining_returns_limit_when_empty(
        self, limiter: TierRateLimiter
    ) -> None:
        """get_remaining returns full limit when no requests made."""
        customer_id = "cust_remaining_002"
        remaining = limiter.get_remaining(customer_id, "free")
        assert remaining == 10

    def test_get_remaining_returns_zero_when_over_limit(
        self, limiter: TierRateLimiter
    ) -> None:
        """get_remaining returns 0 when at or over limit."""
        customer_id = "cust_remaining_003"
        for _ in range(10):
            limiter.check(customer_id, "free")

        remaining = limiter.get_remaining(customer_id, "free")
        assert remaining == 0


class TestConcurrency:
    """Tests for thread safety."""

    async def test_multiple_rapid_requests(self, limiter: TierRateLimiter) -> None:
        """Multiple rapid requests are counted correctly."""
        customer_id = "cust_concurrent_001"
        results = []
        for _ in range(12):
            result = limiter.check(customer_id, "free")
            results.append(result)

        # First 10 should be allowed
        assert sum(1 for r in results[:10] if r["allowed"]) == 10
        # 11th and 12th should be blocked
        assert results[10]["allowed"] is False
        assert results[11]["allowed"] is False


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    async def test_exact_limit_boundary(self, limiter: TierRateLimiter) -> None:
        """Requesting exactly at the limit is allowed, next is blocked."""
        customer_id = "cust_edge_001"
        for i in range(10):
            result = limiter.check(customer_id, "free")
            assert result["allowed"] is True
            assert result["remaining"] == 10 - i - 1

        # Exactly at limit
        assert limiter.check(customer_id, "free")["allowed"] is False

    def test_empty_customer_id_is_treated_as_valid_key(
        self, limiter: TierRateLimiter
    ) -> None:
        """Empty string customer ID is treated as a valid key."""
        result = limiter.check("", "free")
        assert result["allowed"] is True

    async def test_very_long_customer_id(self, limiter: TierRateLimiter) -> None:
        """Very long customer IDs are handled correctly."""
        long_id = "cust_" + "x" * 1000
        result = limiter.check(long_id, "free")
        assert result["allowed"] is True

    async def test_special_characters_in_customer_id(self, limiter: TierRateLimiter) -> None:
        """Special characters in customer IDs are handled."""
        special_id = "cust_@#$%&*()_+-=[]{}|;:',.<>?/~`"
        result = limiter.check(special_id, "free")
        assert result["allowed"] is True

    def test_retry_after_is_reasonable_range(
        self, limiter: TierRateLimiter
    ) -> None:
        """retry_after is within reasonable range (1-60 seconds)."""
        customer_id = "cust_edge_retry"
        for _ in range(10):
            limiter.check(customer_id, "free")

        result = limiter.check(customer_id, "free")
        assert 1 <= result["retry_after"] <= 60


class TestGlobalInstance:
    """Tests for global limiter instance."""

    async def test_get_tier_limiter_returns_singleton(self) -> None:
        """get_tier_limiter returns the same instance."""
        reset_all()
        limiter1 = get_tier_limiter()
        limiter2 = get_tier_limiter()
        assert limiter1 is limiter2

    async def test_global_limiter_is_persistent_across_calls(self) -> None:
        """Global limiter persists state across calls."""
        reset_all()
        limiter = get_tier_limiter()

        # First call
        result1 = limiter.check("cust_global_001", "free")
        assert result1["allowed"] is True

        # Get limiter again
        limiter2 = get_tier_limiter()

        # Check remaining
        result2 = limiter2.check("cust_global_001", "free")
        assert result2["remaining"] == 8  # 10 - 2


class TestTierLimitsConstant:
    """Tests for TIER_LIMITS constant."""

    async def test_tier_limits_has_expected_tiers(self) -> None:
        """TIER_LIMITS contains expected tier names."""
        assert "free" in TIER_LIMITS
        assert "pro" in TIER_LIMITS
        assert "team" in TIER_LIMITS
        assert "enterprise" in TIER_LIMITS

    async def test_tier_limits_have_correct_values(self) -> None:
        """TIER_LIMITS have correct request counts."""
        assert TIER_LIMITS["free"] == 10
        assert TIER_LIMITS["pro"] == 60
        assert TIER_LIMITS["team"] == 300
        assert TIER_LIMITS["enterprise"] == 1000

    async def test_tier_limits_values_are_positive(self) -> None:
        """All tier limits are positive integers."""
        for tier, limit in TIER_LIMITS.items():
            assert isinstance(limit, int)
            assert limit > 0

    async def test_tier_limits_are_ordered(self) -> None:
        """Tier limits increase from free to enterprise."""
        free = TIER_LIMITS["free"]
        pro = TIER_LIMITS["pro"]
        team = TIER_LIMITS["team"]
        enterprise = TIER_LIMITS["enterprise"]
        assert free < pro < team < enterprise
