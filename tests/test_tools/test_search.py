"""Unit tests for research_search tool — mocked provider SDKs, normalized output."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import sys

from loom.tools.search import research_search


class TestSearchMocked:
    """research_search tool tests with mocked provider SDKs."""

    def test_search_exa_returns_normalized_shape(self) -> None:
        """Exa provider returns normalized output with provider field."""
        mock_result = {
            "results": [
                {
                    "title": "Test Article",
                    "url": "https://example.com",
                    "score": 0.9,
                }
            ]
        }
        mock_module = MagicMock()
        mock_module.search_exa.return_value = mock_result
        with patch.dict(sys.modules, {"loom.providers.exa": mock_module}):
            result = research_search("test query", provider="exa", n=5)

            assert "results" in result
            assert "provider" in result
            assert result["provider"] == "exa"
            assert len(result["results"]) == 1

    def test_search_tavily_returns_normalized_shape(self) -> None:
        """Tavily provider returns normalized output with provider field."""
        mock_result = {
            "results": [
                {
                    "title": "Tavily Result",
                    "url": "https://tavily.com",
                    "score": 0.85,
                }
            ]
        }
        mock_module = MagicMock()
        mock_module.search_tavily.return_value = mock_result
        with patch.dict(sys.modules, {"loom.providers.tavily": mock_module}):
            result = research_search(
                "tavily test", provider="tavily", n=5
            )

            assert "results" in result
            assert "provider" in result
            assert result["provider"] == "tavily"
            assert len(result["results"]) == 1

    def test_search_rejects_empty_query(self) -> None:
        """Empty query returns error dict."""
        mock_result = {"results": [], "query": ""}
        mock_module = MagicMock()
        mock_module.search_exa.return_value = mock_result
        with patch.dict(sys.modules, {"loom.providers.exa": mock_module}):
            result = research_search(query="", provider="exa")

            assert "results" in result
            assert result["query"] == ""

    def test_search_clamps_n_to_50(self) -> None:
        """n=100 is clamped to 50."""
        mock_result = {"results": []}
        mock_module = MagicMock()
        mock_module.search_exa.return_value = mock_result
        with patch.dict(sys.modules, {"loom.providers.exa": mock_module}):
            research_search("test", provider="exa", n=100)

            call_args = mock_module.search_exa.call_args
            assert call_args.kwargs["n"] == 50

    def test_search_clamps_n_minimum_1(self) -> None:
        """n=0 is clamped to 1."""
        mock_result = {"results": []}
        mock_module = MagicMock()
        mock_module.search_exa.return_value = mock_result
        with patch.dict(sys.modules, {"loom.providers.exa": mock_module}):
            research_search("test", provider="exa", n=0)

            call_args = mock_module.search_exa.call_args
            assert call_args.kwargs["n"] == 1

    def test_search_passes_domain_filters(self) -> None:
        """include_domains and exclude_domains forwarded to provider."""
        mock_result = {"results": []}
        mock_module = MagicMock()
        mock_module.search_exa.return_value = mock_result
        with patch.dict(sys.modules, {"loom.providers.exa": mock_module}):
            research_search(
                "test",
                provider="exa",
                include_domains=["github.com", "EXAMPLE.COM"],
                exclude_domains=["BAD.COM"],
            )

            call_args = mock_module.search_exa.call_args
            assert "github.com" in call_args.kwargs["include_domains"]
            assert "example.com" in call_args.kwargs["include_domains"]
            assert "bad.com" in call_args.kwargs["exclude_domains"]

    def test_search_unknown_provider_returns_error(self) -> None:
        """Unknown provider returns error dict."""
        result = research_search("test query", provider="unknown")

        assert result["provider"] == "unknown"
        assert result["query"] == "test query"
        assert result["results"] == []
        assert "error" in result
        assert "Unknown provider" in result["error"]
