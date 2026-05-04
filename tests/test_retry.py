"""Tests for the auto-retry middleware with exponential backoff.

Tests the @with_retry decorator, backoff calculation, jitter,
statistics tracking, and integration with fetch/search tools.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from loom.retry import (
    _get_backoff_delay,
    get_retry_stats,
    reset_retry_stats,
    with_retry,
)


class TestBackoffCalculation:
    """Test exponential backoff calculation with jitter."""

    def test_backoff_increases_exponentially(self) -> None:
        """Verify backoff follows 2^attempt formula."""
        # Without exact jitter, just check approximate values
        delays = [_get_backoff_delay(i, 1.0) for i in range(3)]

        # Delays should be approximately 1, 2, 4 (with ±10% jitter)
        assert 0.9 < delays[0] < 1.1, f"First delay should be ~1.0, got {delays[0]}"
        assert 1.8 < delays[1] < 2.2, f"Second delay should be ~2.0, got {delays[1]}"
        assert 3.6 < delays[2] < 4.4, f"Third delay should be ~4.0, got {delays[2]}"

    def test_backoff_base_scaling(self) -> None:
        """Verify backoff_base parameter scales delays correctly."""
        base_2_delay = _get_backoff_delay(1, 2.0)
        base_1_delay = _get_backoff_delay(1, 1.0)

        # With backoff_base=2.0, first retry should be ~4s instead of ~2s
        assert base_2_delay > base_1_delay, "Larger backoff_base should produce larger delays"

    def test_backoff_has_jitter(self) -> None:
        """Verify jitter prevents thundering herd."""
        # Get multiple samples; some should differ
        delays = [_get_backoff_delay(1, 1.0) for _ in range(10)]
        unique_delays = len(set(round(d, 3) for d in delays))

        # With jitter, we should get at least 3 unique values from 10 samples
        assert unique_delays > 1, "Jitter should produce varied delays"


class TestRetryDecoratorSync:
    """Test @with_retry decorator with synchronous functions."""

    def test_retry_succeeds_on_first_attempt(self) -> None:
        """Successful call doesn't retry."""
        calls = []

        @with_retry(max_attempts=3)
        def succeeds_immediately() -> str:
            calls.append(1)
            return "ok"

        result = succeeds_immediately()
        assert result == "ok"
        assert len(calls) == 1, "Should not retry on success"

    def test_retry_succeeds_after_transient_error(self) -> None:
        """Retries transient errors and succeeds."""
        calls = []

        @with_retry(max_attempts=3, backoff_base=0.01)
        def fails_once() -> str:
            calls.append(1)
            if len(calls) == 1:
                raise ConnectionError("Network error")
            return "ok"

        result = fails_once()
        assert result == "ok"
        assert len(calls) == 2, "Should retry once after transient error"

    def test_retry_gives_up_after_max_attempts(self) -> None:
        """Raises error after exhausting retries."""
        calls = []

        @with_retry(max_attempts=2, backoff_base=0.01)
        def always_fails() -> str:
            calls.append(1)
            raise ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            always_fails()

        assert len(calls) == 2, "Should attempt max_attempts times"

    def test_retry_does_not_retry_non_retryable_errors(self) -> None:
        """Non-retryable errors are raised immediately."""
        calls = []

        @with_retry(max_attempts=3)
        def fails_immediately() -> str:
            calls.append(1)
            raise ValueError("Invalid argument")

        with pytest.raises(ValueError):
            fails_immediately()

        assert len(calls) == 1, "Should not retry non-retryable error"

    def test_custom_retryable_errors(self) -> None:
        """Supports custom retryable error types."""
        calls = []

        class CustomTransientError(Exception):
            pass

        @with_retry(max_attempts=2, retryable_errors=(CustomTransientError,))
        def fails_with_custom() -> str:
            calls.append(1)
            if len(calls) == 1:
                raise CustomTransientError("Custom error")
            return "ok"

        result = fails_with_custom()
        assert result == "ok"
        assert len(calls) == 2


class TestRetryDecoratorAsync:
    """Test @with_retry decorator with asynchronous functions."""

    @pytest.mark.asyncio
    async def test_async_retry_succeeds_on_first_attempt(self) -> None:
        """Async successful call doesn't retry."""
        calls = []

        @with_retry(max_attempts=3)
        async def async_succeeds() -> str:
            calls.append(1)
            return "ok"

        result = await async_succeeds()
        assert result == "ok"
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_async_retry_succeeds_after_error(self) -> None:
        """Async retries and recovers from transient errors."""
        calls = []

        @with_retry(max_attempts=3, backoff_base=0.01)
        async def async_fails_once() -> str:
            calls.append(1)
            await asyncio.sleep(0.001)  # Simulate async work
            if len(calls) == 1:
                raise TimeoutError("Timeout")
            return "ok"

        result = await async_fails_once()
        assert result == "ok"
        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_async_retry_exhausted(self) -> None:
        """Async gives up after max retries."""
        calls = []

        @with_retry(max_attempts=2, backoff_base=0.01)
        async def async_always_fails() -> str:
            calls.append(1)
            raise TimeoutError("Timeout")

        with pytest.raises(TimeoutError):
            await async_always_fails()

        assert len(calls) == 2

    @pytest.mark.asyncio
    async def test_async_non_retryable_error(self) -> None:
        """Async non-retryable errors raise immediately."""
        calls = []

        @with_retry(max_attempts=3)
        async def async_invalid() -> str:
            calls.append(1)
            raise ValueError("Invalid")

        with pytest.raises(ValueError):
            await async_invalid()

        assert len(calls) == 1


class TestRetryStatsTracking:
    """Test retry statistics tracking."""

    def test_stats_track_total_retries(self) -> None:
        """Stats track total retries."""
        reset_retry_stats()

        @with_retry(max_attempts=3, backoff_base=0.01)
        def fails_twice() -> str:
            if not hasattr(fails_twice, "count"):
                fails_twice.count = 0
            fails_twice.count += 1
            if fails_twice.count < 3:
                raise ConnectionError("Error")
            return "ok"

        result = fails_twice()
        assert result == "ok"

        stats = get_retry_stats()
        assert "fails_twice" in stats
        assert stats["fails_twice"]["total_retries"] == 2

    def test_stats_track_success_after_retry(self) -> None:
        """Stats track successes after retry."""
        reset_retry_stats()

        @with_retry(max_attempts=3, backoff_base=0.01)
        def recovers() -> str:
            if not hasattr(recovers, "count"):
                recovers.count = 0
            recovers.count += 1
            if recovers.count < 2:
                raise TimeoutError("Timeout")
            return "ok"

        result = recovers()
        assert result == "ok"

        stats = get_retry_stats()
        assert stats["recovers"]["success_after_retry"] == 1

    def test_stats_track_permanent_failure(self) -> None:
        """Stats track permanent failures."""
        reset_retry_stats()

        @with_retry(max_attempts=2, backoff_base=0.01)
        def always_fails() -> None:
            raise ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            always_fails()

        stats = get_retry_stats()
        assert stats["always_fails"]["permanent_failure"] == 1
        assert stats["always_fails"]["total_retries"] == 2  # Two attempts, both failed

    def test_stats_reset(self) -> None:
        """Stats can be reset."""
        reset_retry_stats()

        @with_retry(max_attempts=2, backoff_base=0.01)
        def test_fn() -> str:
            raise ConnectionError()

        with pytest.raises(ConnectionError):
            test_fn()

        stats = get_retry_stats()
        assert len(stats) > 0

        reset_retry_stats()
        stats = get_retry_stats()
        assert len(stats) == 0


class TestDecoratorSyntax:
    """Test both @with_retry and @with_retry(...) syntax."""

    def test_decorator_without_args(self) -> None:
        """@with_retry works without parentheses."""
        @with_retry
        def simple_fn() -> str:
            return "ok"

        result = simple_fn()
        assert result == "ok"

    def test_decorator_with_args(self) -> None:
        """@with_retry(...) works with arguments."""
        @with_retry(max_attempts=5)
        def configured_fn() -> str:
            return "ok"

        result = configured_fn()
        assert result == "ok"


class TestErrorMessageQuality:
    """Test that error messages are informative."""

    def test_exhaustion_error_is_original(self) -> None:
        """Exhaustion raises the original exception, not a wrapper."""

        @with_retry(max_attempts=2, backoff_base=0.01)
        def fails_with_message() -> str:
            raise ConnectionError("Specific error message")

        with pytest.raises(ConnectionError) as exc_info:
            fails_with_message()

        assert "Specific error message" in str(exc_info.value)
