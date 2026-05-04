"""Unit tests for quota tracking system.

Tests for:
- Recording usage (requests and tokens)
- Remaining quota calculation
- Near-limit detection (80% threshold)
- Fallback decision (quota exhausted)
- Reset time calculation
- In-memory and Redis backends
"""

from __future__ import annotations

import pytest
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import patch, MagicMock

from loom.quota_tracker import (
    QuotaTracker,
    QuotaStatus,
    QUOTA_LIMITS,
    get_quota_tracker,
    record_usage,
    get_remaining,
)


class TestQuotaStatus:
    """Test QuotaStatus dataclass."""

    def test_remaining_calculations(self):
        """Test that remaining quota is correctly calculated."""
        now = datetime.now(UTC)
        status = QuotaStatus(
            provider="groq",
            requests_this_minute=10,
            requests_today=100,
            tokens_this_minute=1000,
            tokens_today=5000,
            requests_limit_per_minute=30,
            requests_limit_per_day=14400,
            tokens_limit_per_minute=6000,
            tokens_limit_per_day=200000,
            reset_time_utc=now + timedelta(hours=12),
        )

        assert status.requests_remaining_per_minute() == 20
        assert status.requests_remaining_per_day() == 14300
        assert status.tokens_remaining_per_minute() == 5000
        assert status.tokens_remaining_per_day() == 195000

    def test_percent_usage_calculations(self):
        """Test that usage percentages are correctly calculated."""
        now = datetime.now(UTC)
        status = QuotaStatus(
            provider="groq",
            requests_this_minute=15,
            requests_today=7200,
            tokens_this_minute=3000,
            tokens_today=100000,
            requests_limit_per_minute=30,
            requests_limit_per_day=14400,
            tokens_limit_per_minute=6000,
            tokens_limit_per_day=200000,
            reset_time_utc=now + timedelta(hours=12),
        )

        assert status.requests_used_percent_minute() == 50.0
        assert status.requests_used_percent_day() == 50.0
        assert status.tokens_used_percent_minute() == 50.0
        assert status.tokens_used_percent_day() == 50.0

    def test_to_dict_serialization(self):
        """Test conversion to JSON-serializable dict."""
        now = datetime.now(UTC)
        status = QuotaStatus(
            provider="groq",
            requests_this_minute=5,
            requests_today=50,
            tokens_this_minute=500,
            tokens_today=2000,
            requests_limit_per_minute=30,
            requests_limit_per_day=14400,
            tokens_limit_per_minute=6000,
            tokens_limit_per_day=200000,
            reset_time_utc=now,
        )

        result = status.to_dict()

        assert result["provider"] == "groq"
        assert result["requests_this_minute"] == 5
        assert result["requests_remaining_per_minute"] == 25
        assert "reset_time_utc" in result
        assert isinstance(result["reset_time_utc"], str)


class TestQuotaTrackerBasics:
    """Test basic quota tracker functionality."""

    def test_singleton_pattern(self):
        """Test that get_quota_tracker returns same instance."""
        tracker1 = get_quota_tracker()
        tracker2 = get_quota_tracker()
        assert tracker1 is tracker2

    def test_invalid_provider_raises_error(self):
        """Test that invalid provider name raises ValueError."""
        tracker = QuotaTracker()

        with pytest.raises(ValueError, match="unknown provider"):
            tracker.record_usage("invalid_provider")

        with pytest.raises(ValueError, match="unknown provider"):
            tracker.get_remaining("invalid_provider")

        with pytest.raises(ValueError, match="unknown provider"):
            tracker.get_status("invalid_provider")

    def test_all_providers_configured(self):
        """Test that all expected free-tier providers are configured."""
        assert "groq" in QUOTA_LIMITS
        assert "nvidia_nim" in QUOTA_LIMITS
        assert "gemini" in QUOTA_LIMITS

        for provider, limits in QUOTA_LIMITS.items():
            assert "requests_per_minute" in limits
            assert "requests_per_day" in limits
            assert "tokens_per_minute" in limits
            assert "tokens_per_day" in limits


class TestQuotaTrackerInMemory:
    """Test in-memory quota tracking."""

    def test_record_and_retrieve_usage(self):
        """Test recording and retrieving usage."""
        tracker = QuotaTracker()
        tracker._redis_available = False  # Force in-memory mode

        # Record first request
        tracker.record_usage("groq", tokens=100)
        status = tracker.get_status("groq")

        assert status.requests_this_minute == 1
        assert status.requests_today == 1
        assert status.tokens_this_minute == 100
        assert status.tokens_today == 100

        # Record second request
        tracker.record_usage("groq", tokens=200)
        status = tracker.get_status("groq")

        assert status.requests_this_minute == 2
        assert status.requests_today == 2
        assert status.tokens_this_minute == 300
        assert status.tokens_today == 300

    def test_record_without_tokens(self):
        """Test recording request without tokens."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        tracker.record_usage("groq")  # No tokens
        status = tracker.get_status("groq")

        assert status.requests_this_minute == 1
        assert status.tokens_this_minute == 0

    def test_get_remaining_dict(self):
        """Test get_remaining returns correct structure."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        tracker.record_usage("nvidia_nim", tokens=1000)
        remaining = tracker.get_remaining("nvidia_nim")

        assert "requests_remaining_per_minute" in remaining
        assert "requests_remaining_per_day" in remaining
        assert "tokens_remaining_per_minute" in remaining
        assert "tokens_remaining_per_day" in remaining

        assert remaining["requests_remaining_per_minute"] == 19  # 20 - 1
        assert remaining["tokens_remaining_per_minute"] == 3000  # 4000 - 1000


class TestQuotaNearLimitDetection:
    """Test near-limit detection."""

    def test_is_near_limit_requests_per_minute(self):
        """Test detection of near-limit based on requests per minute."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        # Record 25 of 30 requests (83% of limit)
        for _ in range(25):
            tracker.record_usage("groq", tokens=100)

        # Default threshold is 0.8 (80%)
        assert tracker.is_near_limit("groq", threshold=0.8) is True
        assert tracker.is_near_limit("groq", threshold=0.9) is False

    def test_is_near_limit_tokens_per_minute(self):
        """Test detection of near-limit based on tokens per minute."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        # Record 5100 of 6000 tokens per minute (85%)
        tracker.record_usage("groq", tokens=5100)

        assert tracker.is_near_limit("groq", threshold=0.8) is True
        assert tracker.is_near_limit("groq", threshold=0.9) is False

    def test_is_near_limit_requests_per_day(self):
        """Test detection of near-limit based on requests per day."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        # Mock the day usage (11500 of 14400 = 80%)
        day_key = tracker._current_day_key()
        tracker._requests_per_day["groq"][day_key] = 11500

        assert tracker.is_near_limit("groq", threshold=0.8) is True


class TestQuotaFallbackDecision:
    """Test fallback decision logic."""

    def test_should_fallback_when_requests_exhausted(self):
        """Test fallback when request quota exhausted."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        # Record all 30 requests for this minute
        minute_key = tracker._current_minute_key()
        tracker._requests_per_minute["groq"][minute_key] = 30

        assert tracker.should_fallback("groq") is True

    def test_should_fallback_when_tokens_exhausted(self):
        """Test fallback when token quota exhausted."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        # Record all 6000 tokens for this minute
        minute_key = tracker._current_minute_key()
        tracker._tokens_per_minute["groq"][minute_key] = 6000

        assert tracker.should_fallback("groq") is True

    def test_should_not_fallback_under_limit(self):
        """Test no fallback when under limit."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        # Record moderate usage
        tracker.record_usage("groq", tokens=1000)

        assert tracker.should_fallback("groq") is False

    def test_should_fallback_day_limit_exceeded(self):
        """Test fallback when daily quota exhausted."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        # Max out daily requests
        day_key = tracker._current_day_key()
        tracker._requests_per_day["groq"][day_key] = 14400

        assert tracker.should_fallback("groq") is True


class TestResetTime:
    """Test reset time calculation."""

    def test_reset_time_is_next_utc_midnight(self):
        """Test that reset time is calculated as next UTC midnight."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        status = tracker.get_status("groq")

        # Reset time should be after current time
        assert status.reset_time_utc > datetime.now(UTC)

        # Reset time should be on the next day at midnight
        assert status.reset_time_utc.hour == 0
        assert status.reset_time_utc.minute == 0
        assert status.reset_time_utc.second == 0


class TestModuleLevelFunctions:
    """Test module-level convenience functions."""

    def test_record_usage_module_function(self):
        """Test module-level record_usage function."""
        tracker = get_quota_tracker()
        tracker._redis_available = False

        # Clear any prior state
        tracker._requests_per_minute.clear()
        tracker._tokens_per_minute.clear()

        record_usage("groq", tokens=500)
        status = tracker.get_status("groq")

        assert status.requests_this_minute == 1
        assert status.tokens_this_minute == 500

    def test_get_remaining_module_function(self):
        """Test module-level get_remaining function."""
        tracker = get_quota_tracker()
        tracker._redis_available = False

        # Clear and record known state
        tracker._requests_per_minute.clear()
        tracker._tokens_per_minute.clear()

        record_usage("nvidia_nim", tokens=1000)
        remaining = get_remaining("nvidia_nim")

        assert remaining["requests_remaining_per_minute"] == 19
        assert remaining["tokens_remaining_per_minute"] == 3000


class TestQuotaTrackerMultiProvider:
    """Test quota tracking across multiple providers."""

    def test_independent_quotas_per_provider(self):
        """Test that quotas are tracked independently per provider."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        # Record usage for multiple providers
        tracker.record_usage("groq", tokens=1000)
        tracker.record_usage("nvidia_nim", tokens=500)
        tracker.record_usage("gemini", tokens=300)

        groq_status = tracker.get_status("groq")
        nvidia_status = tracker.get_status("nvidia_nim")
        gemini_status = tracker.get_status("gemini")

        assert groq_status.tokens_this_minute == 1000
        assert nvidia_status.tokens_this_minute == 500
        assert gemini_status.tokens_this_minute == 300

    def test_different_limits_per_provider(self):
        """Test that each provider has correct quota limits."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        groq_status = tracker.get_status("groq")
        nvidia_status = tracker.get_status("nvidia_nim")
        gemini_status = tracker.get_status("gemini")

        # Groq: 30 requests/min, 6000 tokens/min
        assert groq_status.requests_limit_per_minute == 30
        assert groq_status.tokens_limit_per_minute == 6000

        # NVIDIA NIM: 20 requests/min, 4000 tokens/min
        assert nvidia_status.requests_limit_per_minute == 20
        assert nvidia_status.tokens_limit_per_minute == 4000

        # Gemini: 15 requests/min, 1000 tokens/min
        assert gemini_status.requests_limit_per_minute == 15
        assert gemini_status.tokens_limit_per_minute == 1000


class TestQuotaTrackerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_remaining_quota(self):
        """Test behavior when exactly at quota limit."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        minute_key = tracker._current_minute_key()
        # Set to exactly at limit
        tracker._requests_per_minute["groq"][minute_key] = 30

        status = tracker.get_status("groq")
        assert status.requests_remaining_per_minute() == 0
        assert tracker.should_fallback("groq") is True

    def test_negative_remaining_returns_zero(self):
        """Test that negative remaining is clamped to zero."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        minute_key = tracker._current_minute_key()
        # Set to over limit (shouldn't happen but we're defensive)
        tracker._requests_per_minute["groq"][minute_key] = 50

        status = tracker.get_status("groq")
        # max(0, 30 - 50) = 0
        assert status.requests_remaining_per_minute() == 0

    def test_multiple_callers_same_minute(self):
        """Test concurrent calls in same minute window."""
        tracker = QuotaTracker()
        tracker._redis_available = False

        # Simulate multiple calls
        for _ in range(10):
            tracker.record_usage("groq", tokens=100)

        status = tracker.get_status("groq")
        assert status.requests_this_minute == 10
        assert status.tokens_this_minute == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
