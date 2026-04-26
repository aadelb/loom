"""Tests for Tavily search provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_tavily_module():
    sys.modules.pop("loom.providers.tavily", None)
    yield
    sys.modules.pop("loom.providers.tavily", None)


class TestSearchTavily:
    def test_missing_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            from loom.providers.tavily import search_tavily

            result = search_tavily("test query")
            assert result["error"] == "TAVILY_API_KEY not set"
            assert result["results"] == []

    def test_sdk_not_installed(self):
        with (
            patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"tavily": None}),
        ):
            from loom.providers.tavily import search_tavily

            result = search_tavily("test query")
            assert "not installed" in result["error"]

    def test_basic_search(self):
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.search.return_value = {
            "results": [
                {
                    "url": "https://example.com",
                    "title": "Example",
                    "content": "Example content",
                    "score": 0.87,
                    "published_date": "2024-06-01",
                }
            ]
        }
        mock_tavily_mod = MagicMock()
        mock_tavily_mod.TavilyClient = mock_client_cls

        with (
            patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"tavily": mock_tavily_mod}),
        ):
            from loom.providers.tavily import search_tavily

            result = search_tavily("test query", n=5)

        assert "error" not in result
        assert len(result["results"]) == 1
        assert result["results"][0]["snippet"] == "Example content"
        assert result["results"][0]["score"] == 0.87

    def test_content_mapped_to_snippet(self):
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.search.return_value = {
            "results": [{"url": "https://x.com", "title": "X", "content": "Long content here"}]
        }
        mock_tavily_mod = MagicMock()
        mock_tavily_mod.TavilyClient = mock_client_cls

        with (
            patch.dict("os.environ", {"TAVILY_API_KEY": "key"}),
            patch.dict("sys.modules", {"tavily": mock_tavily_mod}),
        ):
            from loom.providers.tavily import search_tavily

            result = search_tavily("test")

        assert result["results"][0]["snippet"] == "Long content here"

    def test_domain_filtering(self):
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.search.return_value = {"results": []}
        mock_tavily_mod = MagicMock()
        mock_tavily_mod.TavilyClient = mock_client_cls

        with (
            patch.dict("os.environ", {"TAVILY_API_KEY": "key"}),
            patch.dict("sys.modules", {"tavily": mock_tavily_mod}),
        ):
            from loom.providers.tavily import search_tavily

            search_tavily("test", include_domains=["example.com"])

        call_kwargs = mock_client_cls.return_value.search.call_args
        assert call_kwargs.kwargs.get("include_domains") == ["example.com"]

    def test_api_error(self):
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.search.side_effect = RuntimeError("rate limited")
        mock_tavily_mod = MagicMock()
        mock_tavily_mod.TavilyClient = mock_client_cls

        with (
            patch.dict("os.environ", {"TAVILY_API_KEY": "key"}),
            patch.dict("sys.modules", {"tavily": mock_tavily_mod}),
        ):
            from loom.providers.tavily import search_tavily

            result = search_tavily("test")

        assert "search failed" in result["error"]

    def test_snippet_truncation(self):
        mock_client_cls = MagicMock()
        mock_client_cls.return_value.search.return_value = {
            "results": [{"url": "https://x.com", "title": "X", "content": "y" * 1000}]
        }
        mock_tavily_mod = MagicMock()
        mock_tavily_mod.TavilyClient = mock_client_cls

        with (
            patch.dict("os.environ", {"TAVILY_API_KEY": "key"}),
            patch.dict("sys.modules", {"tavily": mock_tavily_mod}),
        ):
            from loom.providers.tavily import search_tavily

            result = search_tavily("test")

        assert len(result["results"][0]["snippet"]) == 500
