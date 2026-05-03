"""Unit tests for CacheStore gzip compression — space savings, transparent decompression, backward compatibility."""

from __future__ import annotations
import pytest

import gzip
import json
from pathlib import Path

from loom.cache import CacheStore



pytestmark = pytest.mark.asyncio
class TestCacheCompression:
    """CacheStore gzip compression tests."""

    async def test_compressed_write(self, tmp_cache_dir: Path) -> None:
        """set value, verify .json.gz file exists."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_compressed_write"
        value = {"text": "example content", "status": "ok"}

        cache.put(key, value)

        # Should create .json.gz file, not .json
        gz_files = list(tmp_cache_dir.rglob("*.json.gz"))
        json_files = list(tmp_cache_dir.rglob("*.json"))

        assert len(gz_files) == 1, "Should create exactly one .json.gz file"
        assert len(json_files) == 0, "Should not create legacy .json files"

    async def test_compressed_read(self, tmp_cache_dir: Path) -> None:
        """set then get, verify data matches after decompression."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_compressed_read"
        value = {
            "text": "example content",
            "status": "ok",
            "nested": {
                "a": 1,
                "b": 2,
            },
        }

        cache.put(key, value)
        result = cache.get(key)

        assert result is not None
        assert result["text"] == "example content"
        assert result["status"] == "ok"
        assert result["nested"]["a"] == 1
        assert result["nested"]["b"] == 2

    async def test_compression_ratio(self, tmp_cache_dir: Path) -> None:
        """set 10KB JSON, verify .gz is < 40% of original (60%+ savings)."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_compression_ratio"

        # Create a large JSON object (10KB+)
        large_text = "x" * 10000
        value = {
            "data": large_text,
            "repeated": [large_text for _ in range(5)],
            "status": "ok",
        }

        cache.put(key, value)

        gz_files = list(tmp_cache_dir.rglob("*.json.gz"))
        assert len(gz_files) == 1

        gz_file = gz_files[0]
        gz_size = gz_file.stat().st_size

        # Estimate original uncompressed size
        original_json = json.dumps(value, ensure_ascii=False)
        original_size = len(original_json.encode("utf-8"))

        # Compression ratio should be < 40% (60%+ savings)
        compression_ratio = gz_size / original_size
        assert (
            compression_ratio < 0.40
        ), f"Compression ratio {compression_ratio:.1%} should be < 40% (60%+ savings)"

    async def test_legacy_read(self, tmp_cache_dir: Path) -> None:
        """create .json file manually, verify get() reads it (backward compat)."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_legacy_read"
        value = {"text": "legacy content", "status": "ok"}

        # Manually create legacy .json file
        p = cache._cache_path(key)
        p.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

        # get() should read it successfully
        result = cache.get(key)

        assert result is not None
        assert result["text"] == "legacy content"
        assert result["status"] == "ok"

    async def test_compressed_preferred_over_legacy(self, tmp_cache_dir: Path) -> None:
        """when both .json.gz and .json exist, prefer .json.gz."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_compressed_preferred_over_legacy"

        # Create legacy .json
        p = cache._cache_path(key)
        legacy_value = {"source": "legacy"}
        p.write_text(json.dumps(legacy_value, ensure_ascii=False), encoding="utf-8")

        # Create compressed .json.gz with different value
        gz_path = p.with_suffix(".json.gz")
        compressed_value = {"source": "compressed"}
        json_bytes = json.dumps(compressed_value, ensure_ascii=False).encode("utf-8")
        gz_path.write_bytes(gzip.compress(json_bytes, compresslevel=6))

        # get() should prefer compressed
        result = cache.get(key)

        assert result is not None
        assert result["source"] == "compressed"

    async def test_roundtrip_unicode(self, tmp_cache_dir: Path) -> None:
        """Arabic/Chinese/emoji text survives compression roundtrip."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_roundtrip_unicode"
        value = {
            "arabic": "مرحبا بالعالم",
            "chinese": "你好世界",
            "emoji": "🚀 🔥 💯",
            "mixed": "Hello مرحبا 你好 🌍",
        }

        cache.put(key, value)
        result = cache.get(key)

        assert result is not None
        assert result["arabic"] == "مرحبا بالعالم"
        assert result["chinese"] == "你好世界"
        assert result["emoji"] == "🚀 🔥 💯"
        assert result["mixed"] == "Hello مرحبا 你好 🌍"

    async def test_stats_include_compressed(self, tmp_cache_dir: Path) -> None:
        """cache stats count .gz files correctly."""
        cache = CacheStore(tmp_cache_dir)

        cache.put("key1", {"data": "value1"})
        cache.put("key2", {"data": "value2"})

        stats = cache.stats()

        assert stats["file_count"] == 2, "Should count both compressed files"
        assert stats["total_bytes"] > 0
        assert isinstance(stats["days_present"], list)

    async def test_stats_count_legacy_and_compressed(self, tmp_cache_dir: Path) -> None:
        """stats count both legacy .json and .json.gz files."""
        cache = CacheStore(tmp_cache_dir)

        # Create a compressed file
        cache.put("key1", {"data": "compressed"})

        # Create a legacy uncompressed file manually
        p = cache._cache_path("key2")
        p.write_text(json.dumps({"data": "legacy"}, ensure_ascii=False), encoding="utf-8")

        stats = cache.stats()

        assert stats["file_count"] == 2, "Should count both compressed and legacy files"
        assert stats["total_bytes"] > 0

    async def test_clear_older_than_removes_compressed(self, tmp_cache_dir: Path) -> None:
        """clear_older_than removes .json.gz files."""
        import datetime as dt

        cache = CacheStore(tmp_cache_dir)

        # Create a fake old entry by manually creating compressed file
        old_date = (dt.date.today() - dt.timedelta(days=40)).isoformat()
        old_dir = tmp_cache_dir / old_date
        old_dir.mkdir(parents=True, exist_ok=True)
        old_file = old_dir / "old_entry.json.gz"
        json_bytes = json.dumps({"old": True}).encode("utf-8")
        old_file.write_bytes(gzip.compress(json_bytes, compresslevel=6))

        # Create a recent entry
        cache.put("recent", {"recent": True})

        # Clear entries older than 30 days
        removed = cache.clear_older_than(days=30)

        assert removed >= 1, "Should remove at least the old file"
        assert not old_file.exists(), "Old compressed file should be gone"
        assert cache.get("recent") is not None, "Recent entry should remain"

    async def test_get_with_metadata_compressed(self, tmp_cache_dir: Path) -> None:
        """get_with_metadata works with compressed files."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_metadata_compressed"
        value = {"data": "test"}

        cache.put(key, value)
        result = cache.get_with_metadata(key)

        assert result is not None
        assert result["data"]["data"] == "test"
        assert result["cached_at"] is not None
        assert result["freshness_hours"] >= 0
        assert result["is_stale"] is False

    async def test_get_with_metadata_legacy(self, tmp_cache_dir: Path) -> None:
        """get_with_metadata works with legacy uncompressed files."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_metadata_legacy"
        value = {"data": "test"}

        # Manually create legacy .json file
        p = cache._cache_path(key)
        p.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

        result = cache.get_with_metadata(key)

        assert result is not None
        assert result["data"]["data"] == "test"
        assert result["cached_at"] is not None
        assert result["freshness_hours"] >= 0
        assert result["is_stale"] is False

    async def test_compressed_with_special_chars(self, tmp_cache_dir: Path) -> None:
        """compression works with special chars, quotes, escapes."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_special_chars"
        value = {
            "quotes": 'He said "Hello"',
            "backslash": "path\\to\\file",
            "newlines": "line1\nline2\nline3",
            "tabs": "col1\tcol2\tcol3",
            "null_char": "before\x00after",
        }

        cache.put(key, value)
        result = cache.get(key)

        assert result is not None
        assert result["quotes"] == 'He said "Hello"'
        assert result["backslash"] == "path\\to\\file"
        assert result["newlines"] == "line1\nline2\nline3"
        assert result["tabs"] == "col1\tcol2\tcol3"
        assert result["null_char"] == "before\x00after"

    async def test_corrupted_compressed_file_returns_none(self, tmp_cache_dir: Path) -> None:
        """get() returns None if .json.gz file is corrupted."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_corrupted_gz"
        p = cache._cache_path(key)
        gz_path = p.with_suffix(".json.gz")
        gz_path.parent.mkdir(parents=True, exist_ok=True)

        # Write corrupted gzip data
        gz_path.write_bytes(b"not valid gzip data {{{")

        # get() should return None, not crash
        result = cache.get(key)
        assert result is None

    async def test_very_large_json_compression(self, tmp_cache_dir: Path) -> None:
        """compression works with very large JSON (1MB+)."""
        cache = CacheStore(tmp_cache_dir)
        key = "test_large_json"

        # Create 1MB+ JSON
        large_data = "x" * 1000000
        value = {
            "data": large_data,
            "list": [large_data for _ in range(2)],
        }

        cache.put(key, value)
        result = cache.get(key)

        assert result is not None
        assert result["data"] == large_data
        assert len(result["list"]) == 2

        # Verify significant compression ratio
        gz_files = list(tmp_cache_dir.rglob("*.json.gz"))
        assert len(gz_files) == 1

        gz_size = gz_files[0].stat().st_size
        # Should be much smaller than 3MB (original)
        assert gz_size < 500000, "Should compress 3MB+ down to < 500KB"
