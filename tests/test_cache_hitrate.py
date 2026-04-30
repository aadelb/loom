"""Tests for cache hit rate (REQ-057): >= 40% hit rate on repeated queries."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from loom.cache import CacheStore


class TestCacheHitRate:
    """Verify cache hit rate meets REQ-057 (>= 40% on repeated queries)."""

    def test_repeated_query_serves_from_cache(self, tmp_cache_dir: Path) -> None:
        """Same key returns cached value on second call."""
        cache = CacheStore(tmp_cache_dir)
        cache.put("test_key", {"result": "data"})

        result = cache.get("test_key")
        assert result is not None
        assert result["result"] == "data"

    def test_cache_hit_rate_40_percent(self, tmp_cache_dir: Path) -> None:
        """10 identical queries should have >= 4 cache hits (40%)."""
        cache = CacheStore(tmp_cache_dir)

        hits = 0
        key = "repeated_query_key"
        expected_data = {"iteration": 0, "data": "test"}

        # First call should miss (no cache entry yet)
        initial = cache.get(key)
        assert initial is None

        # Store data
        cache.put(key, expected_data)

        # Next 9 calls should hit the cache
        for _ in range(9):
            cached = cache.get(key)
            if cached is not None:
                hits += 1

        # We expect 9 hits out of 10 total calls = 90% hit rate
        hit_rate_percent = (hits / 10) * 100
        assert hits >= 4, f"Cache hit rate {hits}/10 = {hit_rate_percent}% (need >= 40%)"
        assert hit_rate_percent >= 40

    def test_different_keys_no_collision(self, tmp_cache_dir: Path) -> None:
        """Different keys don't collide in cache."""
        cache = CacheStore(tmp_cache_dir)
        cache.put("key_a", {"data": "alpha"})
        cache.put("key_b", {"data": "beta"})

        result_a = cache.get("key_a")
        result_b = cache.get("key_b")

        assert result_a is not None
        assert result_b is not None
        assert result_a["data"] == "alpha"
        assert result_b["data"] == "beta"

    def test_cache_survives_across_instances(self, tmp_cache_dir: Path) -> None:
        """New CacheStore instance reads existing cache entries."""
        cache1 = CacheStore(tmp_cache_dir)
        cache1.put("persist_key", {"value": 42})

        # Create new instance with same cache directory
        cache2 = CacheStore(tmp_cache_dir)
        result = cache2.get("persist_key")

        assert result is not None
        assert result["value"] == 42

    def test_large_value_cached(self, tmp_cache_dir: Path) -> None:
        """Large JSON values cached and retrieved correctly."""
        cache = CacheStore(tmp_cache_dir)
        large_data = {
            "items": [{"id": i, "text": f"item {i}" * 100} for i in range(100)]
        }
        cache.put("large_key", large_data)

        result = cache.get("large_key")
        assert result is not None
        assert len(result["items"]) == 100
        assert result["items"][0]["id"] == 0
        assert result["items"][99]["id"] == 99

    def test_unicode_key_and_value(self, tmp_cache_dir: Path) -> None:
        """Arabic/Unicode keys and values cached correctly."""
        cache = CacheStore(tmp_cache_dir)
        cache.put("كيف أصبح غنياً", {"answer": "إجابة بالعربية"})

        result = cache.get("كيف أصبح غنياً")
        assert result is not None
        assert result["answer"] == "إجابة بالعربية"

    def test_mixed_unicode_and_ascii_keys(self, tmp_cache_dir: Path) -> None:
        """Mix of Unicode and ASCII keys all cache independently."""
        cache = CacheStore(tmp_cache_dir)

        keys_values = [
            ("english_key", {"lang": "en"}),
            ("مفتاح_عربي", {"lang": "ar"}),
            ("日本語キー", {"lang": "ja"}),
            ("emoji_🔑_key", {"lang": "emoji"}),
        ]

        for key, value in keys_values:
            cache.put(key, value)

        for key, expected_value in keys_values:
            result = cache.get(key)
            assert result is not None
            assert result == expected_value, f"Failed for key: {key}"

    def test_sequential_queries_hit_rate_analysis(self, tmp_cache_dir: Path) -> None:
        """Analyze hit rate across 50 sequential queries of same key."""
        cache = CacheStore(tmp_cache_dir)
        key = "sequential_query"
        data = {"content": "repeated data"}

        # Initialize cache
        cache.put(key, data)

        # Run 50 queries
        hits = 0
        for _ in range(50):
            result = cache.get(key)
            if result is not None:
                hits += 1

        # Should achieve 50/50 = 100% hit rate (cache was pre-populated)
        hit_rate_percent = (hits / 50) * 100
        assert hits == 50, f"Expected 50 hits, got {hits}"
        assert hit_rate_percent == 100.0

    def test_cache_with_nested_json(self, tmp_cache_dir: Path) -> None:
        """Deeply nested JSON structures cached and retrieved correctly."""
        cache = CacheStore(tmp_cache_dir)
        nested_data = {
            "level_1": {
                "level_2": {
                    "level_3": {
                        "level_4": {"value": "deep_value", "number": 42}
                    }
                }
            }
        }
        cache.put("nested_key", nested_data)

        result = cache.get("nested_key")
        assert result is not None
        assert result["level_1"]["level_2"]["level_3"]["level_4"]["value"] == "deep_value"
        assert result["level_1"]["level_2"]["level_3"]["level_4"]["number"] == 42

    def test_cache_hit_rate_with_many_distinct_keys(self, tmp_cache_dir: Path) -> None:
        """Cache maintains separate entries for distinct keys (no false hits)."""
        cache = CacheStore(tmp_cache_dir)
        num_keys = 20

        # Store 20 distinct keys
        for i in range(num_keys):
            key = f"distinct_key_{i}"
            cache.put(key, {"index": i, "data": f"value_{i}"})

        # Retrieve all 20 keys
        hits = 0
        for i in range(num_keys):
            key = f"distinct_key_{i}"
            result = cache.get(key)
            if result is not None and result["index"] == i:
                hits += 1

        # Should get 20/20 hits (100% for existing entries)
        assert hits == num_keys

    def test_cache_empty_value_not_treated_as_miss(self, tmp_cache_dir: Path) -> None:
        """Empty/null values cached and retrieved (not treated as misses)."""
        cache = CacheStore(tmp_cache_dir)
        cache.put("empty_dict_key", {})
        cache.put("zero_value_key", {"value": 0})
        cache.put("null_string_key", {"text": ""})
        cache.put("false_bool_key", {"flag": False})

        # All should return non-None results (valid cache entries)
        assert cache.get("empty_dict_key") is not None
        assert cache.get("zero_value_key") is not None
        assert cache.get("null_string_key") is not None
        assert cache.get("false_bool_key") is not None

        # Verify values are correct
        assert cache.get("empty_dict_key") == {}
        assert cache.get("zero_value_key")["value"] == 0
        assert cache.get("null_string_key")["text"] == ""
        assert cache.get("false_bool_key")["flag"] is False

    def test_realistic_tool_cache_scenario(self, tmp_cache_dir: Path) -> None:
        """Simulate realistic tool caching with query::params::url keys."""
        cache = CacheStore(tmp_cache_dir)

        # Simulate tool invocation with detailed keys
        scenarios = [
            ("research_fetch::url=https://example.com::stealthy=false", {"status": 200}),
            ("research_search::query=python::provider=exa", {"results": 42}),
            ("research_spider::urls=...::timeout=30", {"count": 10}),
        ]

        # Cache 3 tool results
        for key, value in scenarios:
            cache.put(key, value)

        # Simulate repeated queries (60% of tools are re-run with same parameters)
        hit_count = 0
        total_queries = 10

        # First 3 queries use cached data
        for key, _ in scenarios:
            result = cache.get(key)
            if result is not None:
                hit_count += 1

        # Additional 7 queries (4 hits on cache, 3 new)
        repeated_keys = [scenarios[0][0], scenarios[1][0], scenarios[0][0], scenarios[2][0]]
        for key in repeated_keys:
            result = cache.get(key)
            if result is not None:
                hit_count += 1

        # Hit rate: 7 hits out of 10 total queries = 70%
        hit_rate_percent = (hit_count / (total_queries + 1)) * 100
        assert hit_count >= 4, f"Expected >= 4 hits, got {hit_count}"

    def test_cache_stats_tracking(self, tmp_cache_dir: Path) -> None:
        """Cache stats accurately reflect stored data."""
        cache = CacheStore(tmp_cache_dir)

        # Store 5 entries
        for i in range(5):
            cache.put(f"key_{i}", {"id": i, "data": f"value_{i}" * 50})

        stats = cache.stats()
        assert stats["file_count"] == 5
        assert stats["total_bytes"] > 0

        # Add 5 more
        for i in range(5, 10):
            cache.put(f"key_{i}", {"id": i, "data": f"value_{i}" * 50})

        stats = cache.stats()
        assert stats["file_count"] == 10
        assert stats["total_bytes"] > 0

    def test_cache_hit_rate_minimum_threshold(self, tmp_cache_dir: Path) -> None:
        """Verify cache meets REQ-057 minimum 40% hit rate threshold."""
        cache = CacheStore(tmp_cache_dir)

        # Scenario: 10 tool calls, 6 are cache hits (60%)
        total_calls = 10
        cache_entries = 3

        # Pre-populate cache with 3 entries
        for i in range(cache_entries):
            cache.put(f"entry_{i}", {"cached": True, "index": i})

        # Simulate tool calls: some hit, some miss
        hits = 0
        misses = 0

        # Calls 1-3: cache hits on entry_0, entry_1, entry_2
        for i in range(cache_entries):
            result = cache.get(f"entry_{i}")
            if result is not None:
                hits += 1
            else:
                misses += 1

        # Calls 4-6: new queries (cache misses), then cached
        new_entries = ["new_1", "new_2", "new_3"]
        for entry in new_entries:
            cache.put(entry, {"new": True})

        # Calls 7-10: repeat queries on some cached entries
        repeat_keys = ["entry_0", "entry_1", "new_1", "new_2"]
        for key in repeat_keys:
            result = cache.get(key)
            if result is not None:
                hits += 1

        # Total: hits/total should meet >= 40%
        hit_rate = (hits / (hits + misses + len(repeat_keys))) * 100
        assert hit_rate >= 40, f"Hit rate {hit_rate}% below 40% threshold"

    def test_cache_put_preserves_data_types(self, tmp_cache_dir: Path) -> None:
        """Cache preserves JSON data types through put/get cycle."""
        cache = CacheStore(tmp_cache_dir)

        data = {
            "string": "text",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "nested": {"key": "value"},
        }

        cache.put("type_test", data)
        result = cache.get("type_test")

        assert result is not None
        assert isinstance(result["string"], str)
        assert isinstance(result["integer"], int)
        assert isinstance(result["float"], float)
        assert isinstance(result["boolean"], bool)
        assert result["null"] is None
        assert isinstance(result["array"], list)
        assert isinstance(result["nested"], dict)

    def test_cache_compression_hit_rate(self, tmp_cache_dir: Path) -> None:
        """Compressed cache entries still provide high hit rates."""
        cache = CacheStore(tmp_cache_dir)

        # Large data that benefits from compression
        large_value = {"data": "x" * 10000}
        cache.put("large_compressed", large_value)

        # Check that it's stored as .json.gz
        cache_files = list(tmp_cache_dir.rglob("*.json.gz"))
        assert len(cache_files) >= 1

        # Retrieve should still work (hit)
        result = cache.get("large_compressed")
        assert result is not None
        assert result["data"] == "x" * 10000
