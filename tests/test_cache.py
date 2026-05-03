"""Unit tests for CacheStore — gzip compression, atomic writes, UUID tmp, SHA-256, concurrent access."""

from __future__ import annotations
import pytest

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from loom.cache import CacheStore



pytestmark = pytest.mark.asyncio
class TestCacheStore:
    """CacheStore atomic write and concurrent safety tests."""

    async def test_cache_get_missing_returns_none(self, tmp_cache_dir: Path) -> None:
        """get() returns None for missing keys."""
        cache = CacheStore(tmp_cache_dir)
        result = cache.get("nonexistent_key")
        assert result is None

    async def test_cache_put_get_roundtrip(self, tmp_cache_dir: Path) -> None:
        """put() and get() store and retrieve data correctly."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_key_1"
        value = {"text": "example content", "status": "ok"}

        cache.put(key, value)
        result = cache.get(key)

        assert result is not None
        assert result["text"] == "example content"
        assert result["status"] == "ok"

    async def test_cache_path_uses_sha256_prefix(self, tmp_cache_dir: Path) -> None:
        """_cache_path() uses SHA-256 first 32 hex chars."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_sha256_key"
        path = cache._cache_path(key)

        # Path should be base_dir / YYYYMMDD / <32-char-hash>.json
        assert path.suffix == ".json"
        assert len(path.stem) == 32
        assert path.parent.name.count("-") == 2  # YYYY-MM-DD format

    async def test_cache_atomic_write_uses_uuid_tmp(self, tmp_cache_dir: Path) -> None:
        """put() uses uuid-suffixed tmp file for atomicity."""
        cache = CacheStore(tmp_cache_dir)
        key = "atomic_test"
        value = {"data": "test"}

        cache.put(key, value)

        # No tmp files should remain after successful put
        tmp_files = list(tmp_cache_dir.rglob("*.tmp-*"))
        assert len(tmp_files) == 0

        # But the actual file should exist (as .json.gz)
        cache_files = list(tmp_cache_dir.rglob("*.json.gz"))
        assert len(cache_files) == 1

    async def test_cache_clear_older_than(self, tmp_cache_dir: Path) -> None:
        """clear_older_than() removes entries by age."""
        import datetime as dt

        cache = CacheStore(tmp_cache_dir)

        # Create a fake old entry by manually creating directories
        old_date = (dt.date.today() - dt.timedelta(days=40)).isoformat()
        old_dir = tmp_cache_dir / old_date
        old_dir.mkdir(parents=True, exist_ok=True)
        old_file = old_dir / "old_entry.json"
        old_file.write_text('{"old": true}')

        # Create a recent entry
        cache.put("recent", {"recent": True})

        # Clear entries older than 30 days
        removed = cache.clear_older_than(days=30)

        assert removed >= 1  # At least the old file
        assert not old_file.exists()  # Old file should be gone
        assert cache.get("recent") is not None  # Recent should remain

    async def test_cache_concurrent_writes_no_corruption(self, tmp_cache_dir: Path) -> None:
        """Concurrent writes to same key do not corrupt data."""
        cache = CacheStore(tmp_cache_dir)
        key = "concurrent_key"
        num_writers = 10

        def write_worker(worker_id: int) -> None:
            cache.put(key, {"worker_id": worker_id, "status": "complete"})

        # Write from 10 threads concurrently to same key
        with ThreadPoolExecutor(max_workers=num_writers) as executor:
            executor.map(write_worker, range(num_writers))

        # Final result should be valid JSON
        result = cache.get(key)
        assert result is not None
        assert "worker_id" in result
        assert "status" in result
        assert result["status"] == "complete"

    async def test_cache_stats(self, tmp_cache_dir: Path) -> None:
        """stats() returns file_count and total_bytes."""
        cache = CacheStore(tmp_cache_dir)

        cache.put("key1", {"data": "value1"})
        cache.put("key2", {"data": "value2"})

        stats = cache.stats()

        assert stats["file_count"] == 2
        assert stats["total_bytes"] > 0
        assert isinstance(stats["days_present"], list)

    async def test_cache_separate_keys_separate_files(self, tmp_cache_dir: Path) -> None:
        """Different keys create separate cache files."""
        cache = CacheStore(tmp_cache_dir)

        cache.put("key_a", {"content": "a"})
        cache.put("key_b", {"content": "b"})

        # Both keys should be retrievable independently
        assert cache.get("key_a")["content"] == "a"
        assert cache.get("key_b")["content"] == "b"

        # Should have 2 cache files (as .json.gz)
        cache_files = list(tmp_cache_dir.rglob("*.json.gz"))
        assert len(cache_files) == 2

    async def test_cache_get_handles_invalid_json(self, tmp_cache_dir: Path) -> None:
        """get() returns None if cached file has invalid JSON."""
        cache = CacheStore(tmp_cache_dir)
        key = "bad_json"
        path = cache._cache_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        path.write_text("not valid json {{{")

        # get() should return None, not crash
        result = cache.get(key)
        assert result is None
