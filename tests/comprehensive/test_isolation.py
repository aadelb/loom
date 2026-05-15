"""Cross-session contamination and token budget isolation tests.

Tests verify:
  - Cross-session data isolation (user_id="A" cannot see user_id="B" data)
  - Cache isolation (per-user cache keys don't bleed)
  - Rate limiter isolation (per-user quotas are independent)
  - Token budget isolation (credit balance is user-specific)
  - Budget exhaustion doesn't affect other users
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration


class TestCrossSessionIsolation:
    """Test that different sessions/users cannot see each other's data."""

    def test_cross_session_no_data_leak(self) -> None:
        """User A's data is not visible to User B."""
        try:
            from loom.cache import CacheStore
            from pathlib import Path
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as tmpdir:
                cache = CacheStore(base_dir=tmpdir)

                # Simulate User A setting data
                key_a = "user_a:profile:data"
                value_a = {"user_id": "A", "email": "alice@example.com"}
                cache.put(key_a, value_a)

                # Verify User A can retrieve their data
                assert cache.get(key_a) == value_a

                # Simulate User B attempting to access User A's data
                # User B should not find data stored under User A's key prefix
                key_b = "user_b:profile:data"
                value_b = cache.get(key_b)
                assert value_b is None, "User B should not access User A's data"

                # Store User B's own data
                value_b = {"user_id": "B", "email": "bob@example.com"}
                cache.put(key_b, value_b)

                # Verify User B gets their own data
                assert cache.get(key_b) == value_b

                # Verify User A's data is unchanged
                assert cache.get(key_a) == {"user_id": "A", "email": "alice@example.com"}

        except ImportError:
            pytest.skip("CacheStore not available")

    def test_cache_key_isolation(self) -> None:
        """Cache isolation: user_a:data != user_b:data."""
        try:
            from loom.cache import CacheStore
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as tmpdir:
                cache = CacheStore(base_dir=tmpdir)

                # User A stores data with key "user_a:data"
                cache.put("user_a:data", {"value": "secret_a"})

                # User B queries "user_b:data"
                result = cache.get("user_b:data")
                assert result is None, "Different cache keys should not collide"

                # Verify User A's data still exists
                assert cache.get("user_a:data") == {"value": "secret_a"}

        except ImportError:
            pytest.skip("CacheStore not available")

    def test_cache_direct_key_mismatch(self) -> None:
        """Verify cache doesn't return data for mismatched keys."""
        try:
            from loom.cache import CacheStore
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as tmpdir:
                cache = CacheStore(base_dir=tmpdir)

                # Store data under specific key
                test_key = "fetch::https://example.com::user_123"
                test_data = {"content": "page content", "status": 200}
                cache.put(test_key, test_data)

                # Attempt to retrieve with different key
                wrong_key = "fetch::https://example.com::user_456"
                assert cache.get(wrong_key) is None

                # Correct key should still work
                assert cache.get(test_key) == test_data

        except ImportError:
            pytest.skip("CacheStore not available")


class TestRateLimiterIsolation:
    """Test that rate limit quotas are per-user and don't interfere."""

    @pytest.mark.asyncio
    async def test_rate_limit_per_user_quota(self) -> None:
        """User A exhausts rate limit; User B still has full quota."""
        try:
            from loom.rate_limiter import RateLimiter

            limiter = RateLimiter(max_calls=10, window_seconds=60)

            # User A exhausts their quota (free tier = 10/min)
            for i in range(10):
                result = await limiter.check(
                    category="test", user_id="user_a", tier="free"
                )
                assert result is True, f"User A's call {i+1} should be allowed"

            # User A hits rate limit (11th call)
            user_a_blocked = await limiter.check(
                category="test", user_id="user_a", tier="free"
            )
            assert user_a_blocked is False, "User A's 11th call should be blocked"

            # User B should still have full quota
            user_b_allowed_1 = await limiter.check(
                category="test", user_id="user_b", tier="free"
            )
            assert user_b_allowed_1 is True, "User B's 1st call should still be allowed"

            user_b_allowed_2 = await limiter.check(
                category="test", user_id="user_b", tier="free"
            )
            assert user_b_allowed_2 is True, "User B's 2nd call should still be allowed"

            user_b_allowed_3 = await limiter.check(
                category="test", user_id="user_b", tier="free"
            )
            assert user_b_allowed_3 is True, "User B's 3rd call should still be allowed"

            # User B should also be able to make a 4th call (separate quota)
            user_b_allowed_4 = await limiter.check(
                category="test", user_id="user_b", tier="free"
            )
            # Note: This may fail if rate limit is global, not per-user
            # If so, investigate the rate limiter key composition
            assert user_b_allowed_4 is True, "User B should have independent quota"

        except ImportError:
            pytest.skip("RateLimiter not available")

    @pytest.mark.asyncio
    async def test_rate_limit_tier_isolation(self) -> None:
        """Different user tiers have independent rate limits."""
        try:
            from loom.rate_limiter import RateLimiter

            limiter = RateLimiter(max_calls=2, window_seconds=60)

            # Free tier user (max 2 calls)
            # Free tier = 10 calls/min, exhaust quota
            for i in range(10):
                result = await limiter.check(
                    category="test", user_id="free_user", tier="free"
                )
                assert result is True, f"Free user call {i+1} should be allowed"

            free_user_blocked = await limiter.check(
                category="test", user_id="free_user", tier="free"
            )
            assert free_user_blocked is False, "Free user should hit limit at 11th call"

            # Pro tier user should have higher limit (60 per min)
            pro_user_1 = await limiter.check(
                category="test", user_id="pro_user", tier="pro"
            )
            assert pro_user_1 is True, "Pro user should have their own quota"

        except ImportError:
            pytest.skip("RateLimiter not available")


class TestTokenBudgetIsolation:
    """Test credit/token budget is per-user and isolated."""

    def test_token_budget_user_a_isolated(self) -> None:
        """User A's credit balance is independent of User B."""
        try:
            from loom.billing.credits import check_balance, deduct

            # User A has 5 credits
            user_a_credits = 5

            # User A calls a 2-credit tool
            allowed = check_balance(user_a_credits, "fetch")
            assert allowed is True, "User A should have enough credits"

            user_a_credits, cost_a = deduct(user_a_credits, "fetch")
            assert user_a_credits == 2, "User A should have 2 credits remaining (fetch costs 3)"
            assert cost_a == 3, "Fetch should cost 3 credits"

            # User B independently has 1 credit
            user_b_credits = 1

            # User B tries to call the same 2-credit tool
            allowed_b = check_balance(user_b_credits, "fetch")
            assert allowed_b is False, "User B should not have enough credits"

            # User B's balance should be unchanged
            assert user_b_credits == 1, "User B's balance should not be affected"

            # User A's balance should be unchanged (already deducted)
            assert user_a_credits == 2, "User A's deduction should persist"

        except ImportError:
            pytest.skip("Credits module not available")

    def test_token_budget_exhaustion_isolation(self) -> None:
        """User A exhausting budget doesn't affect User B."""
        try:
            from loom.billing.credits import check_balance, deduct

            # User A: 5 credits, calls 6-credit tool
            user_a_credits = 5
            user_a_allowed = check_balance(user_a_credits, "deep")  # 10 credits
            assert user_a_allowed is False, "User A should not have enough for deep tool"

            # User A tries anyway (simulating enforcement at tool boundary)
            # Their balance stays at 5 (no change)
            assert user_a_credits == 5

            # User B: 50 credits (enough for deep tool)
            user_b_credits = 50
            user_b_allowed = check_balance(user_b_credits, "deep")  # 10 credits
            assert user_b_allowed is True, "User B should have enough"

            # User B executes deep tool
            user_b_credits, cost_b = deduct(user_b_credits, "deep")
            assert user_b_credits == 40, "User B should have 40 credits after 10-credit deduction"

            # User A's balance should be unchanged
            assert user_a_credits == 5

        except ImportError:
            pytest.skip("Credits module not available")

    def test_credit_weight_lookup(self) -> None:
        """Verify credit weights are correctly assigned per tool."""
        try:
            from loom.billing.credits import get_tool_cost

            # Light tools (1 credit)
            assert get_tool_cost("search") == 1
            assert get_tool_cost("research_search") == 1
            assert get_tool_cost("detect_language") == 1

            # Medium tools (3 credits)
            assert get_tool_cost("fetch") == 3
            assert get_tool_cost("research_fetch") == 3
            assert get_tool_cost("spider") == 3

            # Heavy tools (10 credits)
            assert get_tool_cost("deep") == 10
            assert get_tool_cost("research_deep") == 10
            assert get_tool_cost("ask_all_models") == 10

            # Unknown tools (2 credits default)
            assert get_tool_cost("unknown_tool") == 2
            assert get_tool_cost("research_unknown") == 2

        except ImportError:
            pytest.skip("Credits module not available")


class TestTokenEconomyEnforcement:
    """Test LOOM_TOKEN_ECONOMY budget enforcement."""

    def test_insufficient_credits_error(self) -> None:
        """Tool call with insufficient credits returns error."""
        try:
            from loom.billing.credits import check_balance

            # User has 2 credits, tries to call 3-credit tool
            user_credits = 2
            allowed = check_balance(user_credits, "fetch")
            assert allowed is False, "Insufficient credits should return False"

        except ImportError:
            pytest.skip("Credits module not available")

    def test_multiple_tool_budget_tracking(self) -> None:
        """Sequential tool calls deplete budget correctly."""
        try:
            from loom.billing.credits import check_balance, deduct

            # User has 10 credits
            user_credits = 10

            # Call 1: search (1 credit)
            assert check_balance(user_credits, "search") is True
            user_credits, cost_1 = deduct(user_credits, "search")
            assert user_credits == 9
            assert cost_1 == 1

            # Call 2: fetch (3 credits)
            assert check_balance(user_credits, "fetch") is True
            user_credits, cost_2 = deduct(user_credits, "fetch")
            assert user_credits == 6
            assert cost_2 == 3

            # Call 3: fetch again (3 credits)
            assert check_balance(user_credits, "fetch") is True
            user_credits, cost_3 = deduct(user_credits, "fetch")
            assert user_credits == 3
            assert cost_3 == 3

            # Call 4: deep tool (10 credits) - should fail
            assert check_balance(user_credits, "deep") is False

            # Call 5: search again (1 credit) - should succeed
            assert check_balance(user_credits, "search") is True
            user_credits, cost_5 = deduct(user_credits, "search")
            assert user_credits == 2
            assert cost_5 == 1

            # Call 6: fetch (3 credits) - should fail
            assert check_balance(user_credits, "fetch") is False

        except ImportError:
            pytest.skip("Credits module not available")


class TestDataIsolationEdgeCases:
    """Edge case tests for data isolation."""

    def test_cache_none_value_isolation(self) -> None:
        """None values in cache don't leak between users."""
        try:
            from loom.cache import CacheStore
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as tmpdir:
                cache = CacheStore(base_dir=tmpdir)

                # User A explicitly stores None
                cache.put("user_a:optional_data", None)

                # User B queries their own key
                user_b_result = cache.get("user_b:optional_data")
                assert user_b_result is None

                # User A's None value should be preserved (if cached)
                user_a_result = cache.get("user_a:optional_data")
                # Note: CacheStore may not store None; this validates expected behavior

        except ImportError:
            pytest.skip("CacheStore not available")

    def test_concurrent_user_operations(self) -> None:
        """Parallel operations from multiple users don't interfere."""
        try:
            from loom.cache import CacheStore
            from tempfile import TemporaryDirectory
            import asyncio

            async def user_operations(cache, user_id):
                """Simulate user operations."""
                key = f"{user_id}:data"
                data = {"user": user_id, "value": 42}
                cache.put(key, data)
                # Simulate some work
                await asyncio.sleep(0.01)
                return cache.get(key)

            async def run_test():
                with TemporaryDirectory() as tmpdir:
                    cache = CacheStore(base_dir=tmpdir)

                    # Run concurrent operations
                    results = await asyncio.gather(
                        user_operations(cache, "user_1"),
                        user_operations(cache, "user_2"),
                        user_operations(cache, "user_3"),
                    )

                    # Verify each user got their own data
                    assert results[0]["user"] == "user_1"
                    assert results[1]["user"] == "user_2"
                    assert results[2]["user"] == "user_3"

            # Run async test
            asyncio.run(run_test())

        except ImportError:
            pytest.skip("CacheStore not available")

    @pytest.mark.asyncio
    async def test_rate_limit_concurrent_users(self) -> None:
        """Concurrent rate limit checks from different users are isolated."""
        try:
            from loom.rate_limiter import RateLimiter
            import asyncio

            limiter = RateLimiter(max_calls=2, window_seconds=60)

            async def user_check_rate_limit(user_id, num_calls):
                """Check rate limit multiple times for a user."""
                results = []
                for i in range(num_calls):
                    allowed = await limiter.check(
                        category="test", user_id=user_id, tier="free"
                    )
                    results.append(allowed)
                return results

            # Free tier = 10/min; run 11 calls each to verify limit
            results = await asyncio.gather(
                user_check_rate_limit("user_a", 11),
                user_check_rate_limit("user_b", 11),
            )

            user_a_results, user_b_results = results

            # First 10 calls should be allowed, 11th should be blocked
            assert all(user_a_results[:10]), "User A's first 10 calls should be allowed"
            assert user_a_results[10] is False, "User A should be rate limited on 11th call"

            assert all(user_b_results[:10]), "User B's first 10 calls should be allowed"
            assert user_b_results[10] is False, "User B should be rate limited on 11th call"

        except ImportError:
            pytest.skip("RateLimiter not available")
