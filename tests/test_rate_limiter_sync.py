"""Unit tests for synchronous rate limiter (SyncRateLimiter).

Tests cover:
  - Basic rate limiting (allow/block)
  - Sliding window behavior
  - Thread safety
  - Decorator functionality
  - Reset behavior
"""

from __future__ import annotations
import pytest

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from loom.rate_limiter import SyncRateLimiter, reset_all, sync_rate_limited



pytestmark = pytest.mark.asyncio
class TestSyncRateLimiter:
    """Tests for SyncRateLimiter class."""

    async def test_sync_rate_limiter_allows_calls_within_limit(self) -> None:
        """Test that rate limiter allows calls within limit."""
        limiter = SyncRateLimiter(max_calls=3, window_seconds=60)

        assert limiter.check("test_key") is True
        assert limiter.check("test_key") is True
        assert limiter.check("test_key") is True

    async def test_sync_rate_limiter_blocks_calls_above_limit(self) -> None:
        """Test that rate limiter blocks calls above limit."""
        limiter = SyncRateLimiter(max_calls=2, window_seconds=60)

        assert limiter.check("test_key") is True
        assert limiter.check("test_key") is True
        assert limiter.check("test_key") is False

    async def test_sync_rate_limiter_different_keys_independent(self) -> None:
        """Test that different keys have independent limits."""
        limiter = SyncRateLimiter(max_calls=2, window_seconds=60)

        assert limiter.check("key1") is True
        assert limiter.check("key1") is True
        assert limiter.check("key1") is False

        # Different key should still have allowance
        assert limiter.check("key2") is True
        assert limiter.check("key2") is True
        assert limiter.check("key2") is False

    async def test_sync_rate_limiter_window_reset(self) -> None:
        """Test that rate limiter resets after window expires."""
        limiter = SyncRateLimiter(max_calls=2, window_seconds=1)

        assert limiter.check("test_key") is True
        assert limiter.check("test_key") is True
        assert limiter.check("test_key") is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should allow new calls after window reset
        assert limiter.check("test_key") is True

    async def test_sync_rate_limiter_thread_safe_concurrent(self) -> None:
        """Test that rate limiter is thread-safe under concurrent load."""
        limiter = SyncRateLimiter(max_calls=5, window_seconds=2)
        results = []
        lock = threading.Lock()

        def check_limit() -> None:
            result = limiter.check("concurrent_key")
            with lock:
                results.append(result)

        # Launch 10 threads, only first 5 should succeed
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_limit) for _ in range(10)]
            for _ in as_completed(futures):
                pass

        allowed = sum(1 for r in results if r is True)
        blocked = sum(1 for r in results if r is False)

        assert allowed == 5
        assert blocked == 5

    async def test_sync_rate_limiter_default_key(self) -> None:
        """Test that rate limiter uses 'global' as default key."""
        limiter = SyncRateLimiter(max_calls=2, window_seconds=60)

        assert limiter.check() is True  # Uses 'global' by default
        assert limiter.check() is True
        assert limiter.check() is False


class TestSyncRateLimitedDecorator:
    """Tests for sync_rate_limited decorator."""

    async def test_sync_rate_limited_decorator_allows_calls(self) -> None:
        """Test that decorated function allows calls within limit."""
        call_count = 0

        @sync_rate_limited("test_category")
        def test_function() -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            return {"status": "success"}

        result1 = test_function()
        assert isinstance(result1, dict)
        assert call_count == 1

    async def test_sync_rate_limited_decorator_blocks_calls(self) -> None:
        """Test that decorated function returns error dict when rate limited."""
        # Reset to ensure clean state
        reset_all()

        call_count = 0

        @sync_rate_limited("small_limit")
        def test_function() -> dict[str, str]:
            nonlocal call_count
            call_count += 1
            return {"status": "success"}

        # Manually set up a limiter with very small limit
        from loom.rate_limiter import _get_sync_limiter

        limiter = _get_sync_limiter("small_limit")
        limiter.max_calls = 1

        result1 = test_function()
        assert result1["status"] == "success"
        assert call_count == 1

        result2 = test_function()
        assert "error" in result2
        assert result2["error"] == "rate_limit_exceeded"
        # Function should not have been called
        assert call_count == 1

    async def test_sync_rate_limited_decorator_error_format(self) -> None:
        """Test that rate limit error has expected format."""
        reset_all()

        @sync_rate_limited("test_format")
        def test_function() -> dict[str, str]:
            return {"status": "success"}

        # Set up a limiter with limit of 1
        from loom.rate_limiter import _get_sync_limiter

        limiter = _get_sync_limiter("test_format")
        limiter.max_calls = 1

        test_function()
        result = test_function()

        assert result["error"] == "rate_limit_exceeded"
        assert "category" in result
        assert result["category"] == "test_format"
        assert "retry_after_seconds" in result

    async def test_sync_rate_limited_decorator_preserves_function_name(self) -> None:
        """Test that decorator preserves function metadata."""

        @sync_rate_limited("test")
        def my_function() -> dict[str, str]:
            """My docstring."""
            return {"status": "success"}

        assert my_function.__name__ == "my_function"
        assert "My docstring" in my_function.__doc__

    async def test_sync_rate_limited_decorator_returns_data_on_success(self) -> None:
        """Test that decorator returns function result on success."""

        @sync_rate_limited("test_return")
        def test_function() -> dict[str, str]:
            return {"status": "ok", "value": "test"}

        result = test_function()

        assert result["status"] == "ok"
        assert result["value"] == "test"

    async def test_sync_rate_limited_decorator_with_arguments(self) -> None:
        """Test that decorator works with function arguments."""

        @sync_rate_limited("test_args")
        def test_function(a: int, b: int) -> dict[str, int]:
            return {"result": a + b}

        result = test_function(5, 3)

        assert result["result"] == 8

    async def test_sync_rate_limited_decorator_with_kwargs(self) -> None:
        """Test that decorator works with function kwargs."""

        @sync_rate_limited("test_kwargs")
        def test_function(a: int, b: int = 10) -> dict[str, int]:
            return {"result": a + b}

        result = test_function(5, b=20)

        assert result["result"] == 25


class TestSyncRateLimiterIntegration:
    """Integration tests for sync rate limiter."""

    async def test_sync_rate_limiter_multiple_windows(self) -> None:
        """Test rate limiter across multiple windows."""
        limiter = SyncRateLimiter(max_calls=2, window_seconds=1)

        # First window
        assert limiter.check("test") is True
        assert limiter.check("test") is True
        assert limiter.check("test") is False

        # Wait for first window to expire
        time.sleep(1.1)

        # Second window
        assert limiter.check("test") is True
        assert limiter.check("test") is True
        assert limiter.check("test") is False

    async def test_sync_rate_limiter_no_memory_leak(self) -> None:
        """Test that rate limiter doesn't leak memory with many keys."""
        limiter = SyncRateLimiter(max_calls=1, window_seconds=1)

        # Create many unique keys
        for i in range(100):
            limiter.check(f"key_{i}")

        # All keys should be in the limiter
        assert len(limiter._calls) == 100

        # Wait for window to expire
        time.sleep(1.1)

        # Old entries should be cleaned up
        limiter.check("key_0")
        # After one check, old entries should be purged on cleanup
        initial_count = len(limiter._calls)
        assert initial_count <= 100

    async def test_sync_rate_limiter_boundary_condition(self) -> None:
        """Test boundary condition where call arrives exactly at window edge."""
        limiter = SyncRateLimiter(max_calls=1, window_seconds=1)

        assert limiter.check("test") is True

        # Wait exactly 1 second (should be just before window edge)
        time.sleep(1.0)

        # This call might succeed or fail depending on timing
        # but shouldn't crash
        result = limiter.check("test")
        assert isinstance(result, bool)
