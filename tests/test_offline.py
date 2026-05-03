"""Unit tests for offline mode — cache-first fallback and stale data indicators."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from loom import cache as cache_module
from loom.cache import CacheStore
from loom.offline import serve_stale_or_error



pytestmark = pytest.mark.asyncio
class TestCacheGetWithMetadata:
    """Tests for CacheStore.get_with_metadata() — freshness metadata retrieval."""

    async def test_get_with_metadata_existing(self, tmp_cache_dir: Path) -> None:
        """get_with_metadata() returns cached data with metadata for existing entry."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_key_1"
        value = {"text": "example content", "status": "ok"}

        cache.put(key, value)
        result = cache.get_with_metadata(key)

        assert result is not None
        assert result["data"] == value
        assert "cached_at" in result
        assert "freshness_hours" in result
        assert "is_stale" in result
        assert result["is_stale"] is False  # Should be fresh (just cached)

    async def test_get_with_metadata_missing(self, tmp_cache_dir: Path) -> None:
        """get_with_metadata() returns None for missing keys."""
        cache = CacheStore(tmp_cache_dir)
        result = cache.get_with_metadata("nonexistent_key")
        assert result is None

    async def test_freshness_hours_calculation(self, tmp_cache_dir: Path) -> None:
        """get_with_metadata() correctly calculates freshness_hours."""
        cache = CacheStore(tmp_cache_dir)
        key = "freshness_test"
        value = {"data": "test"}

        cache.put(key, value)

        # Immediately retrieve
        result = cache.get_with_metadata(key)
        assert result is not None
        assert result["freshness_hours"] < 1  # Should be just created (< 1 hour old)
        assert result["freshness_hours"] >= 0

    async def test_is_stale_flag_fresh(self, tmp_cache_dir: Path) -> None:
        """get_with_metadata() marks data as non-stale when freshness < 24 hours."""
        cache = CacheStore(tmp_cache_dir)
        key = "fresh_data"
        value = {"data": "recent"}

        cache.put(key, value)
        result = cache.get_with_metadata(key)

        assert result is not None
        assert result["is_stale"] is False
        assert result["freshness_hours"] < 24

    async def test_is_stale_flag_old_data(self, tmp_cache_dir: Path) -> None:
        """get_with_metadata() marks data as stale when freshness > 24 hours."""
        cache = CacheStore(tmp_cache_dir)
        key = "old_data"
        value = {"data": "old"}

        # Create cache entry manually with old mtime
        path = cache._cache_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"data": "old"}', encoding="utf-8")

        # Manually set mtime to 25 hours ago
        old_time = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=25)).timestamp()
        import os

        os.utime(path, (old_time, old_time))

        result = cache.get_with_metadata(key)
        assert result is not None
        assert result["is_stale"] is True
        assert result["freshness_hours"] > 24

    async def test_get_with_metadata_cached_at_iso_format(self, tmp_cache_dir: Path) -> None:
        """get_with_metadata() returns cached_at in ISO 8601 format."""
        cache = CacheStore(tmp_cache_dir)
        key = "iso_test"
        value = {"data": "test"}

        cache.put(key, value)
        result = cache.get_with_metadata(key)

        assert result is not None
        cached_at = result["cached_at"]
        assert "T" in cached_at  # ISO format includes T separator
        assert "+" in cached_at or "Z" in cached_at or cached_at.endswith("00:00")  # UTC indicator
        # Try parsing to verify it's valid ISO
        dt.datetime.fromisoformat(cached_at)

    async def test_get_with_metadata_roundtrip(self, tmp_cache_dir: Path) -> None:
        """get_with_metadata() and get() retrieve same data (different formats)."""
        cache = CacheStore(tmp_cache_dir)
        key = "roundtrip_test"
        value = {"text": "content", "count": 42}

        cache.put(key, value)

        # get() returns just the data
        plain = cache.get(key)
        # get_with_metadata() returns wrapped data
        wrapped = cache.get_with_metadata(key)

        assert plain == value
        assert wrapped is not None
        assert wrapped["data"] == value


@pytest.fixture(autouse=True)
def reset_cache_singleton() -> None:
    """Reset the global cache singleton before each test to use tmp_cache_dir."""
    cache_module._cache_singleton = None
    yield
    cache_module._cache_singleton = None


class TestServeStaleOrError:
    """Tests for serve_stale_or_error() — offline fallback behavior."""

    async def test_serve_stale_cache_hit(self, tmp_cache_dir: Path) -> None:
        """serve_stale_or_error() returns stale data when cache hit and provider fails."""
        # Setup cache with temp dir
        cache = CacheStore(tmp_cache_dir)
        cache_key = "search_results::query::example"
        cached_data = {"results": [{"id": 1, "title": "Result 1"}]}

        cache.put(cache_key, cached_data)

        # Temporarily replace global singleton with our test cache
        original_singleton = cache_module._cache_singleton
        cache_module._cache_singleton = cache
        try:
            # Simulate provider failure
            error = ConnectionError("Provider timeout")
            response = serve_stale_or_error(cache_key, error)

            assert response["source"] == "cache_fallback"
            assert response["data"] == cached_data
            assert response["is_stale"] is True
            assert "cached_at" in response
            assert "freshness_hours" in response
            assert "original_error" in response
            assert "Provider timeout" in response["original_error"]
        finally:
            cache_module._cache_singleton = original_singleton

    async def test_serve_stale_no_cache(self, tmp_cache_dir: Path) -> None:
        """serve_stale_or_error() returns error dict when no cache available."""
        cache = CacheStore(tmp_cache_dir)
        cache_key = "missing_cache::key"

        original_singleton = cache_module._cache_singleton
        cache_module._cache_singleton = cache
        try:
            error = TimeoutError("Request timeout after 30s")
            response = serve_stale_or_error(cache_key, error)

            assert response["source"] == "error"
            assert response["data"] is None
            assert response["is_stale"] is False
            assert response["error"] == "provider_unavailable"
            assert "Request timeout after 30s" in response["message"]
        finally:
            cache_module._cache_singleton = original_singleton

    async def test_stale_response_structure_complete(self, tmp_cache_dir: Path) -> None:
        """Stale response includes all required fields."""
        cache = CacheStore(tmp_cache_dir)
        cache_key = "fetch::url::https://example.com"
        cached_data = {"html": "<html>...</html>"}

        cache.put(cache_key, cached_data)

        original_singleton = cache_module._cache_singleton
        cache_module._cache_singleton = cache
        try:
            error = Exception("HTTP 503 Service Unavailable")
            response = serve_stale_or_error(cache_key, error)

            # Required fields for stale response
            required_fields = {
                "data",
                "cached_at",
                "freshness_hours",
                "is_stale",
                "source",
                "original_error",
            }
            assert required_fields.issubset(set(response.keys()))
            assert response["is_stale"] is True
        finally:
            cache_module._cache_singleton = original_singleton

    async def test_error_response_structure_complete(self, tmp_cache_dir: Path) -> None:
        """Error response includes all required fields."""
        cache = CacheStore(tmp_cache_dir)
        cache_key = "nonexistent::cache"

        original_singleton = cache_module._cache_singleton
        cache_module._cache_singleton = cache
        try:
            error = RuntimeError("Internal server error")
            response = serve_stale_or_error(cache_key, error)

            # Required fields for error response
            required_fields = {"data", "is_stale", "error", "message", "source"}
            assert required_fields.issubset(set(response.keys()))
            assert response["data"] is None
            assert response["is_stale"] is False
            assert response["error"] == "provider_unavailable"
        finally:
            cache_module._cache_singleton = original_singleton

    async def test_original_error_preserved_in_stale(self, tmp_cache_dir: Path) -> None:
        """original_error field preserves the exception message."""
        cache = CacheStore(tmp_cache_dir)
        cache_key = "error_message_test"
        cache.put(cache_key, {"test": "data"})

        original_singleton = cache_module._cache_singleton
        cache_module._cache_singleton = cache
        try:
            error_msg = "DNS resolution failed for api.example.com"
            error = OSError(error_msg)
            response = serve_stale_or_error(cache_key, error)

            assert error_msg in response["original_error"]
        finally:
            cache_module._cache_singleton = original_singleton

    async def test_different_exceptions_handled(self, tmp_cache_dir: Path) -> None:
        """serve_stale_or_error() handles various exception types."""
        cache = CacheStore(tmp_cache_dir)
        cache_key = "exception_type_test"
        cache.put(cache_key, {"data": "cached"})

        original_singleton = cache_module._cache_singleton
        cache_module._cache_singleton = cache
        try:
            # Try various exception types
            exceptions = [
                ConnectionError("Network unreachable"),
                TimeoutError("Request timeout"),
                RuntimeError("Internal error"),
                OSError("I/O error"),
            ]

            for exc in exceptions:
                response = serve_stale_or_error(cache_key, exc)
                assert response["source"] == "cache_fallback"
                assert response["data"] == {"data": "cached"}
                assert str(exc) in response["original_error"]
        finally:
            cache_module._cache_singleton = original_singleton

    async def test_freshness_hours_in_stale_response(self, tmp_cache_dir: Path) -> None:
        """Freshness hours correctly reflected in stale response."""
        cache = CacheStore(tmp_cache_dir)
        cache_key = "freshness_reflection"
        cache.put(cache_key, {"result": "old"})

        # Manually age the cache entry (try .json.gz first, then .json)
        path = cache._cache_path(cache_key)
        gz_path = path.with_suffix(".json.gz")
        actual_path = gz_path if gz_path.exists() else path
        old_time = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=12)).timestamp()
        import os

        os.utime(actual_path, (old_time, old_time))

        original_singleton = cache_module._cache_singleton
        cache_module._cache_singleton = cache
        try:
            error = Exception("Provider down")
            response = serve_stale_or_error(cache_key, error)

            assert response["is_stale"] is True
            # Freshness should be around 12 hours (with some tolerance for execution time)
            assert 11.9 < response["freshness_hours"] < 12.1
        finally:
            cache_module._cache_singleton = original_singleton


class TestOfflineModeIntegration:
    """Integration tests for offline mode end-to-end."""

    async def test_offline_flow_with_fresh_cache(self, tmp_cache_dir: Path) -> None:
        """Full offline flow: cache fresh, provider fails, stale data served."""
        cache = CacheStore(tmp_cache_dir)
        cache_key = "integration::fresh::data"
        expected_data = {"results": [1, 2, 3]}

        # Simulate successful fetch that gets cached
        cache.put(cache_key, expected_data)

        original_singleton = cache_module._cache_singleton
        cache_module._cache_singleton = cache
        try:
            # Simulate provider failure
            provider_error = ConnectionError("Cannot reach provider")
            fallback_response = serve_stale_or_error(cache_key, provider_error)

            # Offline mode should serve cached data
            assert fallback_response["data"] == expected_data
            assert fallback_response["source"] == "cache_fallback"
        finally:
            cache_module._cache_singleton = original_singleton

    async def test_offline_flow_no_cache_graceful(self, tmp_cache_dir: Path) -> None:
        """Full offline flow: no cache, provider fails, graceful error."""
        cache = CacheStore(tmp_cache_dir)
        cache_key = "integration::no_cache"

        # No cache exists
        assert cache.get(cache_key) is None

        original_singleton = cache_module._cache_singleton
        cache_module._cache_singleton = cache
        try:
            # Provider fails
            provider_error = TimeoutError("30s timeout")
            fallback_response = serve_stale_or_error(cache_key, provider_error)

            # Should gracefully degrade without crashing
            assert fallback_response["error"] == "provider_unavailable"
            assert fallback_response["data"] is None
            assert fallback_response["source"] == "error"
        finally:
            cache_module._cache_singleton = original_singleton
