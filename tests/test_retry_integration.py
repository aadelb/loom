"""Integration tests for retry middleware with research tools.

Tests how @with_retry integrates with fetch, search, and LLM tools.
"""

from __future__ import annotations

import pytest

from loom.retry import get_retry_stats, reset_retry_stats
from loom.tools.infrastructure.retry_stats import research_retry_stats


class TestRetryStatsAPI:
    """Test the research_retry_stats tool."""

    def test_retry_stats_empty_initially(self) -> None:
        """Stats are empty initially."""
        reset_retry_stats()
        result = research_retry_stats()

        assert result["functions_tracked"] == 0
        assert result["summary"]["total_retries"] == 0
        assert result["summary"]["recovery_rate"] == 0

    def test_retry_stats_includes_timestamp(self) -> None:
        """Stats include ISO timestamp."""
        result = research_retry_stats()

        assert "timestamp" in result
        # Should be ISO format with timezone
        assert "T" in result["timestamp"]
        assert "+" in result["timestamp"] or "Z" in result["timestamp"]

    def test_retry_stats_can_reset(self) -> None:
        """Calling with reset=True clears stats."""
        reset_retry_stats()

        # Add some stats by running a retry function
        from loom.retry import with_retry

        @with_retry(max_attempts=2, backoff_base=0.01)
        def fails_once() -> str:
            if not hasattr(fails_once, "count"):
                fails_once.count = 0
            fails_once.count += 1
            if fails_once.count < 2:
                raise ConnectionError("Error")
            return "ok"

        result = fails_once()
        assert result == "ok"

        # Check stats before reset
        stats_before = research_retry_stats()
        assert stats_before["functions_tracked"] > 0

        # Reset and check again
        stats_after = research_retry_stats(reset=True)
        assert "reset" in stats_after
        assert stats_after["reset"] is True

        # Verify stats are cleared
        empty_stats = research_retry_stats()
        assert empty_stats["functions_tracked"] == 0

    def test_retry_stats_recovery_rate_calculation(self) -> None:
        """Recovery rate is calculated correctly."""
        reset_retry_stats()

        from loom.retry import with_retry

        @with_retry(max_attempts=3, backoff_base=0.01)
        def sometimes_fails() -> str:
            if not hasattr(sometimes_fails, "count"):
                sometimes_fails.count = 0
            sometimes_fails.count += 1
            if sometimes_fails.count < 3:
                raise ConnectionError("Error")
            return "ok"

        result = sometimes_fails()
        assert result == "ok"

        stats = research_retry_stats()
        # success_after_retry=1, total_retries=2
        # recovery_rate = 1/2 = 0.5
        assert stats["summary"]["success_after_retry"] == 1
        assert stats["summary"]["total_retries"] == 2
        assert 0.49 < stats["summary"]["recovery_rate"] < 0.51  # Allow float imprecision


class TestDecoratorIntegration:
    """Test that @with_retry works with tool functions."""

    def test_decorated_function_preserves_docstring(self) -> None:
        """Decorator preserves the original function's docstring."""
        from loom.retry import with_retry

        @with_retry()
        def documented_function() -> str:
            """This is the docstring."""
            return "result"

        assert "This is the docstring." in documented_function.__doc__

    def test_decorated_function_preserves_name(self) -> None:
        """Decorator preserves the original function's name."""
        from loom.retry import with_retry

        @with_retry()
        def named_function() -> str:
            return "result"

        assert named_function.__name__ == "named_function"

    def test_decorated_async_function_is_awaitable(self) -> None:
        """Decorator preserves async function properties."""
        import asyncio
        import inspect

        from loom.retry import with_retry

        @with_retry()
        async def async_function() -> str:
            return "result"

        assert inspect.iscoroutinefunction(async_function)

    @pytest.mark.asyncio
    async def test_decorated_async_function_executes(self) -> None:
        """Decorated async function executes correctly."""
        from loom.retry import with_retry

        @with_retry()
        async def async_function() -> str:
            return "result"

        result = await async_function()
        assert result == "result"


class TestCircuitBreakerCompatibility:
    """Test that retry middleware works alongside circuit breaker.

    The retry decorator should handle transient errors within a single
    provider attempt, while the circuit breaker handles persistent failures
    across multiple providers.
    """

    def test_retry_complements_circuit_breaker_pattern(self) -> None:
        """Retry and circuit breaker serve different purposes.

        Retry: transient errors within a single provider attempt
        Circuit Breaker: persistent failures across provider cascade
        """
        # This test documents the intended usage pattern
        # Actual circuit breaker testing is in test_llm.py

        from loom.retry import with_retry

        attempt_count = 0

        @with_retry(max_attempts=3, backoff_base=0.01)
        def transient_then_permanent() -> str:
            nonlocal attempt_count
            attempt_count += 1

            # First attempt: transient error (retry)
            if attempt_count == 1:
                raise TimeoutError("Network timeout")

            # Second attempt: permanent error (don't retry)
            raise ValueError("Invalid response format")

        # Should retry first TimeoutError, then fail on ValueError
        with pytest.raises(ValueError):
            transient_then_permanent()

        assert attempt_count == 2, "Should attempt twice: timeout, then value error"
