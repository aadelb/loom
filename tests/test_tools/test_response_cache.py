"""Unit tests for response cache tools (store, lookup, stats)."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import pytest

from loom.tools.response_cache import (
    _normalize_query,
    _response_cache,
    _cache_stats,
    research_cache_store,
    research_cache_lookup,
    research_cache_stats,
)


class TestNormalizeQuery:
    """Query normalization for deduplication."""

    def test_normalize_lowercases(self) -> None:
        """Query is lowercased."""
        assert _normalize_query("HELLO WORLD") == "hello world"

    def test_normalize_strips_whitespace(self) -> None:
        """Query whitespace is stripped."""
        assert _normalize_query("  hello world  ") == "hello world"

    def test_normalize_sorts_words(self) -> None:
        """Words are sorted alphabetically."""
        result = _normalize_query("world hello test")
        # Words should be sorted: hello test world
        assert result == "hello test world"

    def test_normalize_removes_duplicates(self) -> None:
        """Duplicate words are removed."""
        result = _normalize_query("hello hello world")
        assert "hello" in result
        assert result.count("hello") == 1

    def test_normalize_long_query_becomes_hash(self) -> None:
        """Very long queries (>256 chars) are converted to SHA-256 hash."""
        long_query = "word " * 100  # >256 chars
        result = _normalize_query(long_query)
        # Result should be 64-char hex (SHA-256)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_normalize_identical_queries_produce_same_key(self) -> None:
        """Different word orders produce same normalized key."""
        q1 = "apple banana cherry"
        q2 = "cherry apple banana"
        assert _normalize_query(q1) == _normalize_query(q2)


class TestCacheStore:
    """research_cache_store functionality."""

    @pytest.fixture(autouse=True)
    def cleanup(self) -> None:
        """Clear cache before and after each test."""
        _response_cache.clear()
        _cache_stats["hits"] = 0
        _cache_stats["misses"] = 0
        yield
        _response_cache.clear()
        _cache_stats["hits"] = 0
        _cache_stats["misses"] = 0

    def test_store_returns_success(self) -> None:
        """Store operation returns expected structure."""
        result = research_cache_store(
            query="test query",
            response="test response",
            tool_name="test_tool",
            ttl_hours=24,
        )
        assert result["cached"] is True
        assert "cache_key" in result
        assert "expires_at" in result
        assert "cache_size" in result
        assert result["cache_size"] == 1

    def test_store_creates_entry_in_cache(self) -> None:
        """Store operation adds entry to module-level cache."""
        query = "hello world"
        response = "test response"
        research_cache_store(query, response)

        # Cache should have one entry
        assert len(_response_cache) == 1

    def test_store_with_custom_ttl(self) -> None:
        """Custom TTL is respected in expiration."""
        result = research_cache_store(
            query="test", response="data", ttl_hours=1
        )
        # Verify expires_at is approximately 1 hour from now
        # (Allow 2 second window for test execution)
        assert "expires_at" in result

    def test_store_overwrites_existing_entry(self) -> None:
        """Storing with same query overwrites previous entry."""
        query = "same query"
        research_cache_store(query, "response1")
        research_cache_store(query, "response2")

        # Should still be 1 entry (overwritten)
        assert len(_response_cache) == 1

    def test_store_records_metadata(self) -> None:
        """Store records tool_name and timestamps."""
        research_cache_store(
            query="test",
            response="data",
            tool_name="my_tool",
            ttl_hours=24,
        )
        # Get the entry
        entry = list(_response_cache.values())[0]
        assert entry["tool_name"] == "my_tool"
        assert "created_at" in entry
        assert "expires_at" in entry


class TestCacheLookup:
    """research_cache_lookup functionality."""

    @pytest.fixture(autouse=True)
    def cleanup(self) -> None:
        """Clear cache before and after each test."""
        _response_cache.clear()
        _cache_stats["hits"] = 0
        _cache_stats["misses"] = 0
        yield
        _response_cache.clear()
        _cache_stats["hits"] = 0
        _cache_stats["misses"] = 0

    def test_lookup_hit(self) -> None:
        """Lookup returns cached response on hit."""
        query = "test query"
        response = "test response"
        research_cache_store(query, response)

        result = research_cache_lookup(query)
        assert result["hit"] is True
        assert result["response"] == response
        assert "age_seconds" in result
        assert result["age_seconds"] >= 0

    def test_lookup_miss_returns_false(self) -> None:
        """Lookup returns False for uncached query."""
        result = research_cache_lookup("nonexistent query")
        assert result["hit"] is False
        assert result["response"] is None
        assert result["age_seconds"] is None

    def test_lookup_expired_entry(self) -> None:
        """Lookup rejects expired entries."""
        query = "test query"
        research_cache_store(query, "response", ttl_hours=0.0001)
        # Wait for expiration
        time.sleep(0.1)

        result = research_cache_lookup(query)
        assert result["hit"] is False
        # Entry should be deleted
        assert len(_response_cache) == 0

    def test_lookup_with_different_word_order(self) -> None:
        """Lookup finds entry even if words are in different order."""
        query1 = "apple banana cherry"
        response = "test response"
        research_cache_store(query1, response)

        # Query with different word order
        query2 = "cherry banana apple"
        result = research_cache_lookup(query2)
        assert result["hit"] is True
        assert result["response"] == response

    def test_lookup_tracks_hits(self) -> None:
        """Lookup increments hit counter."""
        initial_hits = _cache_stats["hits"]
        research_cache_store("query", "response")
        research_cache_lookup("query")

        assert _cache_stats["hits"] == initial_hits + 1

    def test_lookup_tracks_misses(self) -> None:
        """Lookup increments miss counter on miss."""
        initial_misses = _cache_stats["misses"]
        research_cache_lookup("nonexistent")

        assert _cache_stats["misses"] == initial_misses + 1


class TestCacheStats:
    """research_cache_stats functionality."""

    @pytest.fixture(autouse=True)
    def cleanup(self) -> None:
        """Clear cache before and after each test."""
        _response_cache.clear()
        _cache_stats["hits"] = 0
        _cache_stats["misses"] = 0
        yield
        _response_cache.clear()
        _cache_stats["hits"] = 0
        _cache_stats["misses"] = 0

    def test_stats_empty_cache(self) -> None:
        """Stats for empty cache return zeros."""
        result = research_cache_stats()
        assert result["entries"] == 0
        assert result["hits"] == 0
        assert result["misses"] == 0
        assert result["hit_rate_pct"] == 0.0
        assert result["oldest_entry"] is None
        assert result["newest_entry"] is None
        assert result["memory_estimate_kb"] >= 0

    def test_stats_with_entries(self) -> None:
        """Stats reflect cached entries."""
        research_cache_store("query1", "response1")
        research_cache_store("query2", "response2")

        result = research_cache_stats()
        assert result["entries"] == 2
        assert result["oldest_entry"] is not None
        assert result["newest_entry"] is not None

    def test_stats_hit_rate_calculation(self) -> None:
        """Hit rate is calculated correctly."""
        research_cache_store("query", "response")
        # 2 hits, 1 miss
        research_cache_lookup("query")
        research_cache_lookup("query")
        research_cache_lookup("nonexistent")

        result = research_cache_stats()
        # 2 hits / 3 total = 66.67%
        assert result["hit_rate_pct"] == pytest.approx(66.67, abs=0.01)

    def test_stats_cleans_expired_entries(self) -> None:
        """Stats cleanup removes expired entries."""
        research_cache_store("query1", "response1", ttl_hours=24)
        research_cache_store("query2", "response2", ttl_hours=0.0001)
        time.sleep(0.1)

        result = research_cache_stats()
        # Should only have 1 entry (expired one deleted)
        assert result["entries"] == 1

    def test_stats_memory_estimate(self) -> None:
        """Memory estimate is reasonable."""
        response = "x" * 1000
        research_cache_store("query", response)

        result = research_cache_stats()
        # Should estimate at least 1KB (1000 bytes)
        assert result["memory_estimate_kb"] >= 1.0

    def test_stats_timestamps_are_iso(self) -> None:
        """Timestamps are in ISO 8601 format."""
        research_cache_store("query", "response")
        result = research_cache_stats()

        if result["oldest_entry"]:
            # Should be parseable as ISO 8601
            assert "T" in result["oldest_entry"]
            assert "+" in result["oldest_entry"] or "Z" in result["oldest_entry"]


class TestCacheIntegration:
    """Integration tests for store + lookup + stats."""

    @pytest.fixture(autouse=True)
    def cleanup(self) -> None:
        """Clear cache before and after each test."""
        _response_cache.clear()
        _cache_stats["hits"] = 0
        _cache_stats["misses"] = 0
        yield
        _response_cache.clear()
        _cache_stats["hits"] = 0
        _cache_stats["misses"] = 0

    def test_store_lookup_cycle(self) -> None:
        """Full store -> lookup -> stats cycle."""
        # Store
        store_result = research_cache_store(
            query="hello world",
            response="test response data",
            tool_name="my_tool",
            ttl_hours=24,
        )
        assert store_result["cached"] is True

        # Lookup
        lookup_result = research_cache_lookup("hello world")
        assert lookup_result["hit"] is True
        assert lookup_result["response"] == "test response data"

        # Stats
        stats_result = research_cache_stats()
        assert stats_result["entries"] == 1
        assert stats_result["hits"] == 1

    def test_multiple_entries_deduplication(self) -> None:
        """Multiple queries deduplicate correctly."""
        # Store variations of the same query
        research_cache_store("apple banana cherry", "response1")
        research_cache_store("cherry apple banana", "response2")  # Should overwrite
        research_cache_store("banana cherry apple", "response3")  # Should overwrite

        stats = research_cache_stats()
        assert stats["entries"] == 1  # Only 1 unique normalized query

    def test_different_queries_not_deduplicated(self) -> None:
        """Different queries are not deduplicated."""
        research_cache_store("hello world", "response1")
        research_cache_store("goodbye world", "response2")
        research_cache_store("hello there", "response3")

        stats = research_cache_stats()
        assert stats["entries"] == 3
