"""Tests for result_aggregator module.

Tests gather_results, deduplicate_by, filter_by_score, merge_results, and rank_results.
"""

from __future__ import annotations

import pytest

from loom.result_aggregator import (
    deduplicate_by,
    filter_by_score,
    gather_results,
    merge_results,
    rank_results,
)


class TestGatherResults:
    """Test gather_results function."""

    def test_gather_results_all_success(self) -> None:
        """Test gathering all successful results."""
        results = [
            {"id": 1, "data": "a"},
            {"id": 2, "data": "b"},
            {"id": 3, "data": "c"},
        ]
        successes, errors = gather_results(results)
        assert len(successes) == 3
        assert len(errors) == 0

    def test_gather_results_with_errors(self) -> None:
        """Test separating errors from successes."""
        results = [
            {"id": 1, "data": "a"},
            {"id": 2, "error": "failed"},
            {"id": 3, "data": "c"},
        ]
        successes, errors = gather_results(results)
        assert len(successes) == 2
        assert len(errors) == 1
        assert errors[0]["id"] == 2

    def test_gather_results_all_errors(self) -> None:
        """Test all results are errors."""
        results = [
            {"error": "error 1"},
            {"error": "error 2"},
        ]
        successes, errors = gather_results(results)
        assert len(successes) == 0
        assert len(errors) == 2

    def test_gather_results_empty_list(self) -> None:
        """Test empty results list."""
        successes, errors = gather_results([])
        assert successes == []
        assert errors == []

    def test_gather_results_custom_error_key(self) -> None:
        """Test custom error key."""
        results = [
            {"status": "ok"},
            {"status": "failed", "failure": "connection error"},
        ]
        successes, errors = gather_results(results, error_key="failure")
        assert len(successes) == 1
        assert len(errors) == 1

    def test_gather_results_empty_error_string(self) -> None:
        """Test that empty error string is not treated as error."""
        results = [
            {"error": ""},
            {"error": "failed"},
        ]
        successes, errors = gather_results(results)
        assert len(successes) == 1
        assert len(errors) == 1

    def test_gather_results_false_error_value(self) -> None:
        """Test that False error value is not treated as error."""
        results = [
            {"error": False, "data": "ok"},
            {"error": True, "msg": "failed"},
        ]
        successes, errors = gather_results(results)
        assert len(successes) == 1


class TestDeduplicateBy:
    """Test deduplicate_by function."""

    def test_deduplicate_basic(self) -> None:
        """Test basic deduplication by key."""
        items = [
            {"url": "http://example.com", "title": "Example"},
            {"url": "http://test.com", "title": "Test"},
            {"url": "http://example.com", "title": "Example Again"},
        ]
        result = deduplicate_by(items, "url")
        assert len(result) == 2
        assert result[0]["url"] == "http://example.com"

    def test_deduplicate_case_sensitive(self) -> None:
        """Test case-sensitive deduplication."""
        items = [
            {"name": "Alice"},
            {"name": "alice"},
        ]
        result = deduplicate_by(items, "name", case_insensitive=False)
        assert len(result) == 2

    def test_deduplicate_case_insensitive(self) -> None:
        """Test case-insensitive deduplication."""
        items = [
            {"name": "Alice"},
            {"name": "ALICE"},
            {"name": "alice"},
        ]
        result = deduplicate_by(items, "name", case_insensitive=True)
        assert len(result) == 1
        assert result[0]["name"] == "Alice"

    def test_deduplicate_normalize_url(self) -> None:
        """Test URL normalization removes trailing slashes and query params."""
        items = [
            {"url": "http://example.com/path/"},
            {"url": "http://example.com/path"},
            {"url": "http://example.com/path?param=1"},
        ]
        result = deduplicate_by(items, "url", normalize_url=True)
        assert len(result) == 1

    def test_deduplicate_missing_key(self) -> None:
        """Test deduplication with missing key in some items."""
        items = [
            {"url": "http://a.com"},
            {"title": "no url"},
            {"url": "http://a.com"},
        ]
        result = deduplicate_by(items, "url")
        assert len(result) == 2

    def test_deduplicate_empty_value(self) -> None:
        """Test that empty values are deduplicated."""
        items = [
            {"id": ""},
            {"id": ""},
            {"id": "123"},
        ]
        result = deduplicate_by(items, "id")
        assert len(result) == 2

    def test_deduplicate_preserves_first(self) -> None:
        """Test that first occurrence is preserved."""
        items = [
            {"id": "1", "data": "first"},
            {"id": "1", "data": "second"},
        ]
        result = deduplicate_by(items, "id")
        assert len(result) == 1
        assert result[0]["data"] == "first"

    def test_deduplicate_empty_list(self) -> None:
        """Test deduplication of empty list."""
        result = deduplicate_by([], "key")
        assert result == []


class TestFilterByScore:
    """Test filter_by_score function."""

    def test_filter_by_score_basic(self) -> None:
        """Test basic score filtering."""
        items = [
            {"url": "a", "score": 0.9},
            {"url": "b", "score": 0.5},
            {"url": "c", "score": 0.3},
        ]
        result = filter_by_score(items, min_score=0.6)
        assert len(result) == 1
        assert result[0]["url"] == "a"

    def test_filter_by_score_zero_threshold(self) -> None:
        """Test filtering with zero threshold."""
        items = [
            {"score": 0.0},
            {"score": 0.5},
            {"score": 1.0},
        ]
        result = filter_by_score(items, min_score=0.0)
        assert len(result) == 3

    def test_filter_by_score_missing_score(self) -> None:
        """Test that missing score defaults to 0.0."""
        items = [
            {"id": 1},
            {"id": 2, "score": 0.8},
        ]
        result = filter_by_score(items, min_score=0.5)
        assert len(result) == 1

    def test_filter_by_score_custom_key(self) -> None:
        """Test custom score key."""
        items = [
            {"id": 1, "rating": 8},
            {"id": 2, "rating": 5},
        ]
        result = filter_by_score(items, score_key="rating", min_score=7)
        assert len(result) == 1

    def test_filter_by_score_none_value(self) -> None:
        """Test that None score is treated as 0.0."""
        items = [
            {"score": None, "id": 1},
            {"score": 0.8, "id": 2},
        ]
        result = filter_by_score(items, min_score=0.5)
        assert len(result) == 1


class TestRankResults:
    """Test rank_results function."""

    def test_rank_results_descending(self) -> None:
        """Test ranking in descending order."""
        items = [
            {"id": 1, "score": 0.5},
            {"id": 2, "score": 0.9},
            {"id": 3, "score": 0.3},
        ]
        result = rank_results(items)
        assert result[0]["score"] == 0.9
        assert result[1]["score"] == 0.5
        assert result[2]["score"] == 0.3

    def test_rank_results_ascending(self) -> None:
        """Test ranking in ascending order."""
        items = [
            {"id": 1, "score": 0.5},
            {"id": 2, "score": 0.9},
        ]
        result = rank_results(items, descending=False)
        assert result[0]["score"] == 0.5
        assert result[1]["score"] == 0.9

    def test_rank_results_with_limit(self) -> None:
        """Test ranking with limit."""
        items = [
            {"id": i, "score": 1.0 - i * 0.1} for i in range(10)
        ]
        result = rank_results(items, limit=3)
        assert len(result) == 3
        assert result[0]["score"] == 1.0

    def test_rank_results_zero_limit(self) -> None:
        """Test ranking with zero limit returns all."""
        items = [{"score": 0.5}, {"score": 0.8}]
        result = rank_results(items, limit=0)
        assert len(result) == 2

    def test_rank_results_custom_key(self) -> None:
        """Test ranking with custom score key."""
        items = [
            {"id": 1, "priority": 3},
            {"id": 2, "priority": 1},
            {"id": 3, "priority": 2},
        ]
        result = rank_results(items, score_key="priority")
        assert result[0]["priority"] == 3


class TestMergeResults:
    """Test merge_results function."""

    def test_merge_results_single_list(self) -> None:
        """Test merging single result list."""
        results = [
            {"url": "a", "score": 0.9},
            {"url": "b", "score": 0.5},
        ]
        merged = merge_results(results)
        assert len(merged) == 2

    def test_merge_results_multiple_lists(self) -> None:
        """Test merging multiple result lists."""
        list1 = [{"url": "a", "score": 0.9}]
        list2 = [{"url": "b", "score": 0.7}]
        merged = merge_results(list1, list2)
        assert len(merged) == 2

    def test_merge_results_deduplication(self) -> None:
        """Test that merge deduplicates by URL."""
        list1 = [{"url": "http://example.com/", "score": 0.9}]
        list2 = [{"url": "http://example.com", "score": 0.5}]
        merged = merge_results(list1, list2)
        assert len(merged) == 1

    def test_merge_results_ranking(self) -> None:
        """Test that merge ranks by score."""
        list1 = [{"url": "a", "score": 0.5}]
        list2 = [{"url": "b", "score": 0.9}]
        merged = merge_results(list1, list2)
        assert merged[0]["score"] == 0.9
        assert merged[1]["score"] == 0.5

    def test_merge_results_with_limit(self) -> None:
        """Test merge with limit."""
        list1 = [{"url": f"a{i}", "score": 0.9 - i * 0.1} for i in range(5)]
        list2 = [{"url": f"b{i}", "score": 0.8 - i * 0.1} for i in range(5)]
        merged = merge_results(list1, list2, limit=3)
        assert len(merged) == 3

    def test_merge_results_empty_lists(self) -> None:
        """Test merge with empty lists."""
        merged = merge_results([], [])
        assert merged == []

    def test_merge_results_custom_keys(self) -> None:
        """Test merge with custom dedup and score keys."""
        list1 = [{"id": "a", "rating": 10}]
        list2 = [{"id": "a", "rating": 5}]
        merged = merge_results(
            list1,
            list2,
            dedup_key="id",
            score_key="rating",
            limit=10,
        )
        assert len(merged) == 1
        # First occurrence (score=10) is preserved
        assert merged[0]["rating"] == 10
