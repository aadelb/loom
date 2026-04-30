"""Tests for semantic cache system."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from loom.semantic_cache import (
    SemanticCache,
    _compute_ngram_overlap,
    _compute_tfidf_similarity,
    _compute_word_overlap,
    _tokenize,
)


class TestTokenization:
    """Test text tokenization utilities."""

    def test_tokenize_simple(self) -> None:
        """Tokenize simple text."""
        tokens = _tokenize("Hello World")
        assert tokens == ["hello", "world"]

    def test_tokenize_punctuation(self) -> None:
        """Remove punctuation during tokenization."""
        tokens = _tokenize("Hello, World! How are you?")
        assert tokens == ["hello", "world", "how", "are", "you"]

    def test_tokenize_empty(self) -> None:
        """Handle empty text."""
        tokens = _tokenize("")
        assert tokens == []

    def test_tokenize_numbers(self) -> None:
        """Preserve numbers during tokenization."""
        tokens = _tokenize("version 1.0 release")
        assert "1" in tokens and "0" in tokens


class TestSimilarityMetrics:
    """Test similarity computation functions."""

    def test_word_overlap_identical(self) -> None:
        """Identical tokens have overlap 1.0."""
        tokens = ["hello", "world"]
        sim = _compute_word_overlap(tokens, tokens)
        assert sim == 1.0

    def test_word_overlap_disjoint(self) -> None:
        """Completely different tokens have overlap 0.0."""
        tokens1 = ["hello", "world"]
        tokens2 = ["foo", "bar"]
        sim = _compute_word_overlap(tokens1, tokens2)
        assert sim == 0.0

    def test_word_overlap_partial(self) -> None:
        """Partial overlap gives intermediate score."""
        tokens1 = ["hello", "world"]
        tokens2 = ["hello", "universe"]
        sim = _compute_word_overlap(tokens1, tokens2)
        # 1 intersection, 3 union => 1/3 ≈ 0.333
        assert 0.33 < sim < 0.34

    def test_word_overlap_empty(self) -> None:
        """Empty tokens return 0.0."""
        sim = _compute_word_overlap([], ["hello"])
        assert sim == 0.0

    def test_ngram_overlap_identical(self) -> None:
        """Identical text has ngram overlap 1.0."""
        text = "hello world"
        sim = _compute_ngram_overlap(text, text)
        assert sim == 1.0

    def test_ngram_overlap_disjoint(self) -> None:
        """Completely different text has ngram overlap 0.0."""
        sim = _compute_ngram_overlap("aaa", "bbb")
        assert sim == 0.0

    def test_ngram_overlap_partial(self) -> None:
        """Partial overlap gives intermediate score."""
        # "hello" and "hallo" share some 3-grams but not all
        sim = _compute_ngram_overlap("hello", "hallo")
        assert 0.0 < sim < 1.0

    def test_tfidf_similarity_identical(self) -> None:
        """Identical tokens have TF-IDF similarity 1.0."""
        tokens = ["hello", "world"]
        sim = _compute_tfidf_similarity(tokens, tokens)
        assert abs(sim - 1.0) < 0.001

    def test_tfidf_similarity_disjoint(self) -> None:
        """Completely different tokens have TF-IDF similarity 0.0."""
        tokens1 = ["hello", "world"]
        tokens2 = ["foo", "bar"]
        sim = _compute_tfidf_similarity(tokens1, tokens2)
        assert sim == 0.0

    def test_tfidf_similarity_partial(self) -> None:
        """Partial token overlap gives intermediate score."""
        tokens1 = ["hello", "world", "test"]
        tokens2 = ["hello", "universe"]
        sim = _compute_tfidf_similarity(tokens1, tokens2)
        assert 0.2 < sim < 0.5


class TestSemanticCache:
    """Test SemanticCache class."""

    @pytest.fixture
    def temp_cache_dir(self) -> Path:
        """Temporary cache directory for testing."""
        with TemporaryDirectory(prefix="test_semantic_cache_") as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cache(self, temp_cache_dir: Path) -> SemanticCache:
        """SemanticCache instance with temp directory."""
        return SemanticCache(cache_dir=temp_cache_dir, similarity_threshold=0.92)

    def test_init_creates_directory(self, temp_cache_dir: Path) -> None:
        """Initialize creates cache directory."""
        cache = SemanticCache(cache_dir=temp_cache_dir)
        assert cache.cache_dir.exists()
        assert cache.cache_dir.is_dir()

    def test_default_threshold(self) -> None:
        """Default threshold is 0.92."""
        cache = SemanticCache()
        assert cache.threshold == 0.92

    def test_threshold_clamping(self) -> None:
        """Threshold is clamped to [0.0, 1.0]."""
        cache1 = SemanticCache(similarity_threshold=-0.5)
        assert cache1.threshold == 0.0

        cache2 = SemanticCache(similarity_threshold=1.5)
        assert cache2.threshold == 1.0

    def test_similarity_identical_queries(self, cache: SemanticCache) -> None:
        """Identical queries have similarity 1.0."""
        query = "what is machine learning?"
        sim = cache.similarity(query, query)
        assert sim == 1.0

    def test_similarity_completely_different(self, cache: SemanticCache) -> None:
        """Completely different queries have low similarity."""
        sim = cache.similarity("hello world", "xyz abc")
        assert sim < 0.3

    def test_similarity_partial_overlap(self, cache: SemanticCache) -> None:
        """Similar queries have reasonable similarity."""
        query1 = "machine learning basics"
        query2 = "what is machine learning"
        sim = cache.similarity(query1, query2)
        # Should have some overlap but not necessarily > 0.5
        assert 0.0 < sim < 1.0

    def test_similarity_empty_query(self, cache: SemanticCache) -> None:
        """Empty queries have 0.0 similarity."""
        sim = cache.similarity("", "hello")
        assert sim == 0.0

    @pytest.mark.asyncio
    async def test_put_and_get_exact_match(self, cache: SemanticCache) -> None:
        """Exact match returns cached response."""
        query = "what is AI?"
        response = "AI is artificial intelligence."
        model = "test-model"

        await cache.put(query, response, model=model)
        result = await cache.get(query, model=model)

        assert result is not None
        assert result["cached_response"] == response
        assert result["original_query"] == query
        assert result["similarity_score"] == 1.0
        assert result["is_semantic_match"] is False

    @pytest.mark.asyncio
    async def test_put_and_get_no_match_below_threshold(self, cache: SemanticCache) -> None:
        """Query below threshold returns None."""
        await cache.put("machine learning", "ML response", model="test")

        # Completely different query should not match
        result = await cache.get("cooking recipes", model="test")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_no_match(self, cache: SemanticCache) -> None:
        """Completely different query returns None."""
        await cache.put("machine learning", "ML response", model="test")

        result = await cache.get("cooking recipes", model="test")
        assert result is None

    @pytest.mark.asyncio
    async def test_model_specific_caching(self, cache: SemanticCache) -> None:
        """Same query cached separately per model."""
        query = "what is AI?"

        # Cache with model-1
        await cache.put(query, "Response from model-1", model="model-1")

        # Cache with model-2
        await cache.put(query, "Response from model-2", model="model-2")

        # Get with model-1 should return model-1 response
        result1 = await cache.get(query, model="model-1")
        assert result1["cached_response"] == "Response from model-1"

        # Get with model-2 should return model-2 response
        result2 = await cache.get(query, model="model-2")
        assert result2["cached_response"] == "Response from model-2"

    @pytest.mark.asyncio
    async def test_get_stats(self, cache: SemanticCache) -> None:
        """Stats tracking works correctly."""
        query = "test query"
        response = "test response"

        # Record a cache miss
        await cache.get(query, model="test")
        stats = cache.get_stats()
        assert stats["total_queries"] == 1
        assert stats["cache_misses"] == 1
        assert stats["cache_hits"] == 0
        assert stats["hit_rate"] == 0.0

        # Put a response
        await cache.put(query, response, model="test")

        # Record a cache hit
        await cache.get(query, model="test")
        stats = cache.get_stats()
        assert stats["total_queries"] == 2
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["hit_rate"] == 50.0

    @pytest.mark.asyncio
    async def test_stats_estimated_savings(self, cache: SemanticCache) -> None:
        """Estimated savings tracked in stats."""
        # 10 cache hits should give estimated savings
        for i in range(10):
            await cache.put(f"query-{i}", f"response-{i}", model="test")
            await cache.get(f"query-{i}", model="test")

        stats = cache.get_stats()
        # 10 hits * $0.001 per hit = $0.01
        assert stats["estimated_savings_usd"] >= 0.01

    @pytest.mark.asyncio
    async def test_persistent_cache_across_instances(self, temp_cache_dir: Path) -> None:
        """Cache persists across instance creation."""
        query = "persistent query"
        response = "persistent response"

        # Create first instance and cache
        cache1 = SemanticCache(cache_dir=temp_cache_dir)
        await cache1.put(query, response, model="test")

        # Create second instance and verify cache is loaded
        cache2 = SemanticCache(cache_dir=temp_cache_dir)
        result = await cache2.get(query, model="test")

        assert result is not None
        assert result["cached_response"] == response

    @pytest.mark.asyncio
    async def test_empty_query_ignored(self, cache: SemanticCache) -> None:
        """Empty queries are ignored."""
        await cache.put("", "response", model="test")
        assert len(cache.index) == 0

    @pytest.mark.asyncio
    async def test_empty_response_ignored(self, cache: SemanticCache) -> None:
        """Empty responses are ignored."""
        await cache.put("query", "", model="test")
        assert len(cache.index) == 0

    @pytest.mark.asyncio
    async def test_duplicate_put_skipped(self, cache: SemanticCache) -> None:
        """Duplicate puts are skipped (not overwritten)."""
        query = "test query"
        response1 = "first response"
        response2 = "second response"

        await cache.put(query, response1, model="test")
        await cache.put(query, response2, model="test")

        result = await cache.get(query, model="test")
        assert result["cached_response"] == response1  # Original cached

    @pytest.mark.asyncio
    async def test_metadata_storage(self, cache: SemanticCache) -> None:
        """Metadata is stored and retrievable."""
        query = "test query"
        response = "test response"
        metadata = {"cost_usd": 0.001, "tokens": 100}

        await cache.put(query, response, model="test", metadata=metadata)

        # Reload from disk and check metadata is there
        cache2 = SemanticCache(cache_dir=cache.cache_dir)
        entry = list(cache2.index.values())[0]
        assert entry["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_stats_entries_cached(self, cache: SemanticCache) -> None:
        """Stats report entries_cached correctly."""
        assert cache.get_stats()["entries_cached"] == 0

        await cache.put("query1", "response1", model="test")
        await cache.put("query2", "response2", model="test")

        assert cache.get_stats()["entries_cached"] == 2


class TestCacheConcurrency:
    """Test concurrent cache operations."""

    @pytest.fixture
    def temp_cache_dir(self) -> Path:
        """Temporary cache directory for concurrency tests."""
        with TemporaryDirectory(prefix="test_concurrent_") as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cache(self, temp_cache_dir: Path) -> SemanticCache:
        """SemanticCache for concurrency tests."""
        return SemanticCache(cache_dir=temp_cache_dir)

    @pytest.mark.asyncio
    async def test_concurrent_puts(self, cache: SemanticCache) -> None:
        """Concurrent puts are handled safely."""
        tasks = []
        for i in range(10):
            task = cache.put(f"query-{i}", f"response-{i}", model="test")
            tasks.append(task)

        await asyncio.gather(*tasks)
        assert len(cache.index) == 10

    @pytest.mark.asyncio
    async def test_concurrent_gets(self, cache: SemanticCache) -> None:
        """Concurrent gets are handled safely."""
        # Pre-populate cache
        for i in range(5):
            await cache.put(f"query-{i}", f"response-{i}", model="test")

        # Concurrent gets
        tasks = []
        for i in range(5):
            task = cache.get(f"query-{i}", model="test")
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        assert all(r is not None for r in results)

    @pytest.mark.asyncio
    async def test_concurrent_puts_and_gets(self, cache: SemanticCache) -> None:
        """Mixed concurrent puts and gets."""
        async def put_and_get(i: int) -> None:
            await cache.put(f"query-{i}", f"response-{i}", model="test")
            await cache.get(f"query-{i}", model="test")

        tasks = [put_and_get(i) for i in range(10)]
        await asyncio.gather(*tasks)

        stats = cache.get_stats()
        assert stats["cache_hits"] > 0
        assert stats["total_queries"] > 0


class TestCacheIntegration:
    """Integration tests with real file I/O."""

    @pytest.fixture
    def temp_cache_dir(self) -> Path:
        """Temporary cache directory for integration tests."""
        with TemporaryDirectory(prefix="test_integration_") as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def cache(self, temp_cache_dir: Path) -> SemanticCache:
        """SemanticCache with temp directory."""
        return SemanticCache(cache_dir=temp_cache_dir)

    @pytest.mark.asyncio
    async def test_gzip_compression(self, cache: SemanticCache) -> None:
        """Cache files are gzip compressed."""
        query = "test query"
        response = "x" * 1000  # Large response

        await cache.put(query, response, model="test")

        # Check that .json.gz file exists
        cache_files = list(cache.cache_dir.rglob("*.json.gz"))
        assert len(cache_files) > 0

        # Verify it's actually gzip compressed
        import gzip

        gz_file = cache_files[0]
        with gzip.open(gz_file, "rt", encoding="utf-8") as f:
            data = json.load(f)
            assert data["response"] == response

    @pytest.mark.asyncio
    async def test_cache_loading_on_init(self, temp_cache_dir: Path) -> None:
        """Index is loaded from disk on init."""
        query = "persistent query"
        response = "persistent response"

        # Create and populate cache
        cache1 = SemanticCache(cache_dir=temp_cache_dir)
        await cache1.put(query, response, model="test")
        assert len(cache1.index) == 1

        # Create new instance — should load from disk
        cache2 = SemanticCache(cache_dir=temp_cache_dir)
        assert len(cache2.index) == 1
        assert list(cache2.index.values())[0]["query"] == query

    @pytest.mark.asyncio
    async def test_multiple_models_isolation(self, cache: SemanticCache) -> None:
        """Different models don't share cache entries."""
        query = "same query"

        await cache.put(query, "model1-response", model="model1")
        await cache.put(query, "model2-response", model="model2")

        # Getting with wrong model returns None (no match)
        result_wrong = await cache.get(query, model="model3")
        assert result_wrong is None

        # Getting with correct model works
        result1 = await cache.get(query, model="model1")
        assert result1["cached_response"] == "model1-response"

    @pytest.mark.asyncio
    async def test_query_tokens_stored(self, cache: SemanticCache) -> None:
        """Query tokens are stored in cache entries."""
        query = "test query with words"
        response = "response"

        await cache.put(query, response, model="test")

        # Reload from disk and check tokens
        cache2 = SemanticCache(cache_dir=cache.cache_dir)
        entry = list(cache2.index.values())[0]
        assert "tokens" in entry
        assert "test" in entry["tokens"]
        assert "query" in entry["tokens"]
