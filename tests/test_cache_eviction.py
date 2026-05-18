"""Tests for CacheStore TTL and size-based LRU eviction."""

from __future__ import annotations

import datetime as dt
import gzip
import json
import os
import time
from pathlib import Path
from typing import Any

import pytest

from loom.cache import CacheStore


pytestmark = pytest.mark.asyncio


class TestTTLEviction:
    """TTL eviction on get() — files older than cache_ttl_hours are deleted."""

    async def test_get_expired_compressed_returns_none(self, tmp_cache_dir: Path) -> None:
        """get() returns None and deletes a .json.gz file older than TTL."""
        cache = CacheStore(tmp_cache_dir, cache_ttl_hours=1)
        key = "expired_compressed"
        value = {"data": "old"}

        cache.put(key, value)
        gz_path = cache._cache_path(key).with_suffix(".json.gz")

        # Age the file to 2 hours old
        old_time = time.time() - (2 * 3600)
        os.utime(gz_path, (old_time, old_time))

        result = cache.get(key)
        assert result is None
        assert not gz_path.exists()

    async def test_get_expired_legacy_returns_none(self, tmp_cache_dir: Path) -> None:
        """get() returns None and deletes a legacy .json file older than TTL."""
        cache = CacheStore(tmp_cache_dir, cache_ttl_hours=1)
        key = "expired_legacy"
        value = {"data": "old"}

        # Manually create legacy file
        p = cache._cache_path(key)
        p.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

        # Age the file
        old_time = time.time() - (2 * 3600)
        os.utime(p, (old_time, old_time))

        result = cache.get(key)
        assert result is None
        assert not p.exists()

    async def test_get_fresh_compressed_still_returns_data(self, tmp_cache_dir: Path) -> None:
        """get() still returns data for a fresh file."""
        cache = CacheStore(tmp_cache_dir, cache_ttl_hours=24)
        key = "fresh_compressed"
        value = {"data": "fresh"}

        cache.put(key, value)
        result = cache.get(key)
        assert result == value

    async def test_get_fresh_legacy_still_returns_data(self, tmp_cache_dir: Path) -> None:
        """get() still returns data for a fresh legacy file."""
        cache = CacheStore(tmp_cache_dir, cache_ttl_hours=24)
        key = "fresh_legacy"
        value = {"data": "fresh"}

        p = cache._cache_path(key)
        p.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

        result = cache.get(key)
        assert result == value

    async def test_ttl_zero_means_immediate_expiry(self, tmp_cache_dir: Path) -> None:
        """cache_ttl_hours=0 expires every file immediately."""
        cache = CacheStore(tmp_cache_dir, cache_ttl_hours=0)
        key = "immediate_expire"
        value = {"data": "gone"}

        cache.put(key, value)
        result = cache.get(key)
        assert result is None

    async def test_ttl_slow_path_expired(self, tmp_cache_dir: Path) -> None:
        """Slow-path get() (search all dirs) also evicts expired files."""
        cache = CacheStore(tmp_cache_dir, cache_ttl_hours=1)
        key = "slow_path_expired"
        value = {"data": "old"}

        # Put in today's dir, then move to an older date dir to force slow path
        cache.put(key, value)
        gz_path = cache._cache_path(key).with_suffix(".json.gz")

        old_date = (dt.date.today() - dt.timedelta(days=2)).isoformat()
        old_dir = tmp_cache_dir / old_date
        old_dir.mkdir(parents=True, exist_ok=True)
        new_path = old_dir / gz_path.name
        gz_path.rename(new_path)

        old_time = time.time() - (2 * 3600)
        os.utime(new_path, (old_time, old_time))

        result = cache.get(key)
        assert result is None
        assert not new_path.exists()

    async def test_default_ttl_from_env(self, tmp_cache_dir: Path) -> None:
        """CACHE_TTL_HOURS can be set via environment variable."""
        import os

        orig = os.environ.get("LOOM_CACHE_TTL_HOURS")
        try:
            os.environ["LOOM_CACHE_TTL_HOURS"] = "42"
            cache = CacheStore(tmp_cache_dir)
            assert cache.cache_ttl_hours == 42
        finally:
            if orig is None:
                os.environ.pop("LOOM_CACHE_TTL_HOURS", None)
            else:
                os.environ["LOOM_CACHE_TTL_HOURS"] = orig


class TestSizeEviction:
    """Size-based LRU eviction on put() — oldest files removed when over limit."""

    async def test_put_evicts_oldest_when_over_limit(self, tmp_cache_dir: Path) -> None:
        """put() evicts oldest files when total size exceeds max_size_bytes."""
        # Very small limit so we can trigger eviction easily
        cache = CacheStore(tmp_cache_dir, max_size_bytes=80)

        # Write two small entries; each compressed JSON is ~35 bytes
        cache.put("key1", {"data": "a" * 100})
        cache.put("key2", {"data": "b" * 100})

        # Force key1 to be older than key2
        gz1 = cache._cache_path("key1").with_suffix(".json.gz")
        gz2 = cache._cache_path("key2").with_suffix(".json.gz")
        old_time = time.time() - 3600
        os.utime(gz1, (old_time, old_time))

        # Third put should trigger eviction of key1 (oldest)
        cache.put("key3", {"data": "c" * 100})

        # key1 should have been evicted, key2 and key3 remain
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None

    async def test_put_no_eviction_when_under_limit(self, tmp_cache_dir: Path) -> None:
        """put() does not evict anything when total size is under limit."""
        cache = CacheStore(tmp_cache_dir, max_size_bytes=10_000_000)

        cache.put("key1", {"data": "value1"})
        cache.put("key2", {"data": "value2"})
        cache.put("key3", {"data": "value3"})

        assert cache.get("key1") is not None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None

    async def test_put_eviction_respects_mtime_not_name(self, tmp_cache_dir: Path) -> None:
        """Eviction uses mtime (LRU), not alphabetical order."""
        cache = CacheStore(tmp_cache_dir, max_size_bytes=80)

        cache.put("aaa", {"data": "a" * 100})
        cache.put("zzz", {"data": "z" * 100})

        gz_aaa = cache._cache_path("aaa").with_suffix(".json.gz")
        gz_zzz = cache._cache_path("zzz").with_suffix(".json.gz")

        # Make zzz older despite being alphabetically last
        old_time = time.time() - 3600
        os.utime(gz_zzz, (old_time, old_time))

        cache.put("middle", {"data": "m" * 100})

        # zzz was oldest, so it should be evicted
        assert cache.get("zzz") is None
        assert cache.get("aaa") is not None
        assert cache.get("middle") is not None

    async def test_zero_max_size_disables_eviction(self, tmp_cache_dir: Path) -> None:
        """max_size_bytes=0 disables size-based eviction."""
        cache = CacheStore(tmp_cache_dir, max_size_bytes=0)

        cache.put("key1", {"data": "a" * 100})
        cache.put("key2", {"data": "b" * 100})
        cache.put("key3", {"data": "c" * 100})

        assert cache.get("key1") is not None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None

    async def test_default_max_size_from_env(self, tmp_cache_dir: Path) -> None:
        """MAX_SIZE_BYTES can be set via environment variable."""
        import os

        orig = os.environ.get("LOOM_CACHE_MAX_SIZE_BYTES")
        try:
            os.environ["LOOM_CACHE_MAX_SIZE_BYTES"] = "2048"
            cache = CacheStore(tmp_cache_dir)
            assert cache.max_size_bytes == 2048
        finally:
            if orig is None:
                os.environ.pop("LOOM_CACHE_MAX_SIZE_BYTES", None)
            else:
                os.environ["LOOM_CACHE_MAX_SIZE_BYTES"] = orig


class TestBackwardCompatibility:
    """Ensure existing CacheStore behavior is preserved."""

    async def test_existing_constructor_signature(self, tmp_cache_dir: Path) -> None:
        """CacheStore(base_dir) still works as before."""
        cache = CacheStore(tmp_cache_dir)
        cache.put("key", {"data": "value"})
        assert cache.get("key") == {"data": "value"}

    async def test_singleton_still_works(self, tmp_cache_dir: Path) -> None:
        """get_cache() singleton still works with new defaults."""
        from loom.cache import get_cache, _cache_singleton
        import loom.cache

        # Reset singleton
        loom.cache._cache_singleton = None

        import os
        orig = os.environ.get("LOOM_CACHE_DIR")
        try:
            os.environ["LOOM_CACHE_DIR"] = str(tmp_cache_dir)
            cache1 = get_cache()
            cache2 = get_cache()
            assert cache1 is cache2
            assert cache1.cache_ttl_hours == 24
            assert cache1.max_size_bytes == 1_073_741_824
        finally:
            if orig is None:
                os.environ.pop("LOOM_CACHE_DIR", None)
            else:
                os.environ["LOOM_CACHE_DIR"] = orig
            loom.cache._cache_singleton = None
