"""Unit tests for research_search tool — provider cascade, normalized output."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("loom.tools.search")

from loom.tools.search import research_search


class TestSearch:
    """research_search tool tests."""

    def test_search_rejects_empty_query(self) -> None:
        """Search rejects empty query."""
        result = research_search(query="")

        assert "error" in result
        assert result["results"] == []

    def test_search_normalized_output(self) -> None:
        """Search result has normalized output shape."""
        # Without EXA_API_KEY, should return fallback structure
        import os
        old_key = os.environ.pop("EXA_API_KEY", None)

        try:
            result = research_search(query="test", n=10, provider="exa")

            # Should have standard response structure
            assert "provider" in result
            assert "results" in result
            assert isinstance(result["results"], list)
        finally:
            if old_key:
                os.environ["EXA_API_KEY"] = old_key

    def test_search_graceful_fallback_no_key(self) -> None:
        """Search gracefully falls back when API key not set."""
        import os

        old_exa = os.environ.pop("EXA_API_KEY", None)

        try:
            result = research_search(query="test", provider="exa")

            # Should have error or empty results, but not crash
            assert "results" in result or "error" in result
        finally:
            if old_exa:
                os.environ["EXA_API_KEY"] = old_exa

    def test_search_include_domains_filtering(self) -> None:
        """Search accepts include_domains parameter without error."""
        # Just verify that include_domains parameter is accepted
        result = research_search(
            query="test",
            include_domains=["example.com"],
            provider="exa",
        )

        # Should return a valid response structure
        assert "provider" in result
        assert "results" in result
        # If no API key, should have error key or empty results
        if result.get("results"):
            assert isinstance(result["results"], list)

    def test_search_exclude_domains_filtering(self) -> None:
        """Search accepts exclude_domains parameter without error."""
        # Just verify that exclude_domains parameter is accepted
        result = research_search(
            query="test",
            exclude_domains=["bad.com"],
            provider="exa",
        )

        # Should return a valid response structure
        assert "provider" in result
        assert "results" in result
        # If no API key, should have error key or empty results
        if result.get("results"):
            assert isinstance(result["results"], list)
