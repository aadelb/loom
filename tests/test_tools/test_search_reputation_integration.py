"""Integration tests for search.py with reputation filtering."""
from __future__ import annotations

import pytest

from loom.tools.core.search import _apply_reputation_filter


class TestSearchReputationIntegration:
    """Tests for reputation filtering integration in search module."""

    def test_apply_reputation_filter_empty_results(self):
        """Filtering empty results returns empty without error."""
        result = {"provider": "test", "query": "query", "results": []}
        filtered = _apply_reputation_filter(result)
        assert filtered["results"] == []

    def test_apply_reputation_filter_adds_scores(self):
        """Filtering adds reputation scores to results."""
        result = {
            "provider": "test",
            "query": "query",
            "results": [
                {"url": "https://arxiv.org/paper", "title": "Paper"},
                {"url": "https://example.com/page", "title": "Page"},
            ],
        }
        filtered = _apply_reputation_filter(result)
        assert len(filtered["results"]) == 2
        assert filtered["results"][0]["reputation_score"] == 95
        assert filtered["results"][1]["reputation_score"] == 50

    def test_apply_reputation_filter_no_results_key(self):
        """Filtering handles results with no 'results' key."""
        result = {"provider": "test", "query": "query", "error": "test error"}
        filtered = _apply_reputation_filter(result)
        assert filtered == result

    def test_apply_reputation_filter_non_list_results(self):
        """Filtering handles non-list results gracefully."""
        result = {"provider": "test", "query": "query", "results": "not a list"}
        filtered = _apply_reputation_filter(result)
        assert filtered["results"] == "not a list"

    def test_apply_reputation_filter_preserves_metadata(self):
        """Filtering preserves provider, query, and other fields."""
        result = {
            "provider": "exa",
            "query": "python asyncio",
            "results": [{"url": "https://arxiv.org/paper"}],
            "metadata": {"total": 1},
        }
        filtered = _apply_reputation_filter(result)
        assert filtered["provider"] == "exa"
        assert filtered["query"] == "python asyncio"
        assert filtered["metadata"]["total"] == 1

    def test_apply_reputation_filter_with_link_field(self):
        """Filtering works with 'link' field in results."""
        result = {
            "provider": "test",
            "query": "query",
            "results": [
                {"link": "https://arxiv.org/paper", "title": "Paper"},
            ],
        }
        filtered = _apply_reputation_filter(result)
        assert filtered["results"][0]["reputation_score"] == 95
