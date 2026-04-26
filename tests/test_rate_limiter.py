"""Tests for rate limiter module (async and sync)."""

from __future__ import annotations

import asyncio
import threading
import time
from unittest.mock import patch

import pytest

from loom.rate_limiter import (
    RateLimiter,
    SyncRateLimiter,
    _get_limiter,
    _get_sync_limiter,
    check_rate_limit,
    rate_limited,
    reset_all,
    sync_rate_limited,
)


class TestRateLimiter:
    """Tests for async RateLimiter."""

    def test_init(self):
        """Test RateLimiter initialization."""
        limiter = RateLimiter(max_calls=10, window_seconds=60)
        assert limiter.max_calls == 10
        assert limiter.window_seconds == 60

    @pytest.mark.asyncio
    async def test_check_under_limit(self):
        """Test check returns True when under limit."""
        limiter = RateLimiter(max_calls=3, window_seconds=60)
        assert await limiter.check() is True
        assert await limiter.check() is True
        assert await limiter.check() is True

    @pytest.mark.asyncio
    async def test_check_at_limit(self):
        """Test check returns False when at limit."""
        limiter = RateLimiter(max_calls=2, window_seconds=60)
        assert await limiter.check() is True
        assert await limiter.check() is True
        assert await limiter.check() is False  # 3rd call exceeds limit

    @pytest.mark.asyncio
    async def test_check_with_different_keys(self):
        """Test rate limit tracking per key."""
        limiter = RateLimiter(max_calls=2, window_seconds=60)
        assert await limiter.check("key1") is True
        assert await limiter.check("key1") is True
        assert await limiter.check("key1") is False

        # Different key should start fresh
        assert await limiter.check("key2") is True
        assert await limiter.check("key2") is True
        assert await limiter.check("key2") is False

    @pytest.mark.asyncio
    async def test_check_window_expiry(self):
        """Test calls expire after window_seconds."""
        limiter = RateLimiter(max_calls=2, window_seconds=1)
        assert await limiter.check() is True
        assert await limiter.check() is True
        assert await limiter.check() is False

        # Wait for window to expire
        await asyncio.sleep(1.1)
        assert await limiter.check() is True  # Should be allowed after window expires

    def test_remaining_under_limit(self):
        """Test remaining() reports correct count."""
        limiter = RateLimiter(max_calls=5, window_seconds=60)
        assert limiter.remaining() == 5

    @pytest.mark.asyncio
    async def test_remaining_after_calls(self):
        """Test remaining() after making calls."""
        limiter = RateLimiter(max_calls=5, window_seconds=60)
        await limiter.check()
        await limiter.check()
        assert limiter.remaining() == 3

    @pytest.mark.asyncio
    async def test_remaining_at_limit(self):
        """Test remaining() returns 0 at limit."""
        limiter = RateLimiter(max_calls=2, window_seconds=60)
        await limiter.check()
        await limiter.check()
        assert limiter.remaining() == 0

    @pytest.mark.asyncio
    async def test_concurrent_checks(self):
        """Test rate limiter handles concurrent calls."""
        limiter = RateLimiter(max_calls=5, window_seconds=60)

        async def check_rate():
            return await limiter.check()

        results = await asyncio.gather(*[check_rate() for _ in range(10)])
        # Should have 5 True and 5 False
        assert sum(results) == 5
        assert len([r for r in results if not r]) == 5

    @pytest.mark.asyncio
    async def test_key_cleanup(self):
        """Test empty keys are cleaned up."""
        limiter = RateLimiter(max_calls=2, window_seconds=1)
        await limiter.check("temp_key")
        await limiter.check("temp_key")

        assert "temp_key" in limiter._calls
        await asyncio.sleep(1.1)
        await limiter.check("temp_key")  # This triggers cleanup
        # After cleanup, old entries should be removed


class TestSyncRateLimiter:
    """Tests for synchronous SyncRateLimiter."""

    def test_init(self):
        """Test SyncRateLimiter initialization."""
        limiter = SyncRateLimiter(max_calls=10, window_seconds=60)
        assert limiter.max_calls == 10
        assert limiter.window_seconds == 60

    def test_check_under_limit(self):
        """Test check returns True when under limit."""
        limiter = SyncRateLimiter(max_calls=3, window_seconds=60)
        assert limiter.check() is True
        assert limiter.check() is True
        assert limiter.check() is True

    def test_check_at_limit(self):
        """Test check returns False when at limit."""
        limiter = SyncRateLimiter(max_calls=2, window_seconds=60)
        assert limiter.check() is True
        assert limiter.check() is True
        assert limiter.check() is False  # 3rd call exceeds limit

    def test_check_with_different_keys(self):
        """Test rate limit tracking per key."""
        limiter = SyncRateLimiter(max_calls=2, window_seconds=60)
        assert limiter.check("key1") is True
        assert limiter.check("key1") is True
        assert limiter.check("key1") is False

        # Different key should start fresh
        assert limiter.check("key2") is True
        assert limiter.check("key2") is True
        assert limiter.check("key2") is False

    def test_check_window_expiry(self):
        """Test calls expire after window_seconds."""
        limiter = SyncRateLimiter(max_calls=2, window_seconds=1)
        assert limiter.check() is True
        assert limiter.check() is True
        assert limiter.check() is False

        # Wait for window to expire
        time.sleep(1.1)
        assert limiter.check() is True  # Should be allowed after window expires

    def test_concurrent_checks_threading(self):
        """Test rate limiter handles concurrent thread access."""
        limiter = SyncRateLimiter(max_calls=5, window_seconds=60)
        results = []
        lock = threading.Lock()

        def check_rate():
            result = limiter.check()
            with lock:
                results.append(result)

        threads = [threading.Thread(target=check_rate) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 5 True and 5 False
        assert sum(results) == 5
        assert len([r for r in results if not r]) == 5

    def test_key_cleanup(self):
        """Test empty keys are cleaned up."""
        limiter = SyncRateLimiter(max_calls=2, window_seconds=1)
        limiter.check("temp_key")
        limiter.check("temp_key")

        assert "temp_key" in limiter._calls
        time.sleep(1.1)
        limiter.check("temp_key")  # This triggers cleanup


class TestRateLimitDecorator:
    """Tests for @rate_limited decorator."""

    @pytest.mark.asyncio
    async def test_decorated_function_allowed(self):
        """Test decorated function runs when under limit."""
        reset_all()

        @rate_limited("test")
        async def test_func(x):
            return x * 2

        result = await test_func(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_decorated_function_rate_limited(self):
        """Test decorated function returns error when rate limited."""
        reset_all()

        with patch("loom.rate_limiter._get_limiter") as mock_get:
            mock_limiter = RateLimiter(max_calls=1, window_seconds=60)
            mock_get.return_value = mock_limiter

            @rate_limited("test")
            async def test_func():
                return "success"

            # First call succeeds
            result1 = await test_func()
            assert result1 == "success"

            # Second call hits rate limit
            result2 = await test_func()
            assert isinstance(result2, dict)
            assert result2["error"] == "rate_limit_exceeded"
            assert result2["category"] == "test"
            assert result2["retry_after_seconds"] == 60


class TestSyncRateLimitDecorator:
    """Tests for @sync_rate_limited decorator."""

    def test_decorated_function_allowed(self):
        """Test decorated function runs when under limit."""
        reset_all()

        @sync_rate_limited("test")
        def test_func(x):
            return x * 2

        result = test_func(5)
        assert result == 10

    def test_decorated_function_rate_limited(self):
        """Test decorated function returns error when rate limited."""
        reset_all()

        with patch("loom.rate_limiter._get_sync_limiter") as mock_get:
            mock_limiter = SyncRateLimiter(max_calls=1, window_seconds=60)
            mock_get.return_value = mock_limiter

            @sync_rate_limited("test")
            def test_func():
                return "success"

            # First call succeeds
            result1 = test_func()
            assert result1 == "success"

            # Second call hits rate limit
            result2 = test_func()
            assert isinstance(result2, dict)
            assert result2["error"] == "rate_limit_exceeded"


class TestCheckRateLimit:
    """Tests for check_rate_limit() function."""

    @pytest.mark.asyncio
    async def test_under_limit(self):
        """Test check_rate_limit returns None when under limit."""
        reset_all()
        result = await check_rate_limit("search")
        assert result is None

    @pytest.mark.asyncio
    async def test_at_limit(self):
        """Test check_rate_limit returns error dict when at limit."""
        reset_all()

        with patch("loom.rate_limiter._get_limiter") as mock_get:
            mock_limiter = RateLimiter(max_calls=1, window_seconds=60)
            mock_get.return_value = mock_limiter

            await check_rate_limit("search")
            result = await check_rate_limit("search")

            assert result is not None
            assert result["error"] == "rate_limit_exceeded"
            assert result["category"] == "search"


class TestGetLimiter:
    """Tests for _get_limiter() function."""

    def test_get_limiter_caches(self):
        """Test _get_limiter returns same instance."""
        reset_all()
        limiter1 = _get_limiter("search")
        limiter2 = _get_limiter("search")
        assert limiter1 is limiter2

    def test_get_limiter_different_categories(self):
        """Test different categories get different limiters."""
        reset_all()
        limiter_search = _get_limiter("search")
        limiter_deep = _get_limiter("deep")
        assert limiter_search is not limiter_deep

    def test_get_limiter_respects_config(self):
        """Test _get_limiter respects config values."""
        reset_all()
        with patch("loom.rate_limiter.get_config") as mock_config:
            mock_config.return_value = {
                "RATE_LIMIT_SEARCH_PER_MIN": 100,
                "get": lambda k, default: 100 if "SEARCH" in k else default,
            }

            limiter = _get_limiter("search")
            assert limiter.max_calls == 100


class TestGetSyncLimiter:
    """Tests for _get_sync_limiter() function."""

    def test_get_sync_limiter_caches(self):
        """Test _get_sync_limiter returns same instance."""
        reset_all()
        limiter1 = _get_sync_limiter("search")
        limiter2 = _get_sync_limiter("search")
        assert limiter1 is limiter2

    def test_get_sync_limiter_different_categories(self):
        """Test different categories get different limiters."""
        reset_all()
        limiter_search = _get_sync_limiter("search")
        limiter_deep = _get_sync_limiter("deep")
        assert limiter_search is not limiter_deep


class TestResetAll:
    """Tests for reset_all() function."""

    @pytest.mark.asyncio
    async def test_reset_all_clears_limiters(self):
        """Test reset_all clears all cached limiters."""
        reset_all()
        limiter1 = _get_limiter("search")
        await limiter1.check()

        reset_all()
        limiter2 = _get_limiter("search")

        # Should be a new instance with no calls
        assert limiter2 is not limiter1
        assert limiter2.remaining() == limiter2.max_calls

    def test_reset_all_clears_sync_limiters(self):
        """Test reset_all clears sync limiters."""
        reset_all()
        limiter1 = _get_sync_limiter("search")
        limiter1.check()

        reset_all()
        limiter2 = _get_sync_limiter("search")

        # Should be a new instance with no calls
        assert limiter2 is not limiter1
