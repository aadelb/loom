"""Tests for Firecrawl search provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_firecrawl_module():
    sys.modules.pop("loom.providers.firecrawl", None)
    yield
    sys.modules.pop("loom.providers.firecrawl", None)


class TestSearchFirecrawl:
    def test_missing_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            from loom.providers.firecrawl import search_firecrawl

            result = search_firecrawl("test query")
            assert result["error"] == "FIRECRAWL_API_KEY not set"
            assert result["results"] == []

    def test_sdk_not_installed(self):
        with (
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"firecrawl": None}),
        ):
            from loom.providers.firecrawl import search_firecrawl

            result = search_firecrawl("test query")
            assert "not installed" in result["error"]

    def test_basic_search_list_response(self):
        mock_app_cls = MagicMock()
        mock_app_cls.return_value.search.return_value = [
            {"url": "https://example.com", "title": "Example", "description": "Desc", "score": 0.9}
        ]
        mock_fc_mod = MagicMock()
        mock_fc_mod.FirecrawlApp = mock_app_cls

        with (
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "key"}),
            patch.dict("sys.modules", {"firecrawl": mock_fc_mod}),
        ):
            from loom.providers.firecrawl import search_firecrawl

            result = search_firecrawl("test")

        assert "error" not in result
        assert len(result["results"]) == 1
        assert result["results"][0]["url"] == "https://example.com"
        assert result["results"][0]["snippet"] == "Desc"

    def test_basic_search_dict_response(self):
        mock_app_cls = MagicMock()
        mock_app_cls.return_value.search.return_value = {
            "data": [{"url": "https://example.com", "title": "T", "description": "D"}]
        }
        mock_fc_mod = MagicMock()
        mock_fc_mod.FirecrawlApp = mock_app_cls

        with (
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "key"}),
            patch.dict("sys.modules", {"firecrawl": mock_fc_mod}),
        ):
            from loom.providers.firecrawl import search_firecrawl

            result = search_firecrawl("test")

        assert len(result["results"]) == 1

    def test_client_side_domain_include(self):
        mock_app_cls = MagicMock()
        mock_app_cls.return_value.search.return_value = [
            {"url": "https://example.com/page", "title": "Good", "description": ""},
            {"url": "https://other.com/page", "title": "Bad", "description": ""},
        ]
        mock_fc_mod = MagicMock()
        mock_fc_mod.FirecrawlApp = mock_app_cls

        with (
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "key"}),
            patch.dict("sys.modules", {"firecrawl": mock_fc_mod}),
        ):
            from loom.providers.firecrawl import search_firecrawl

            result = search_firecrawl("test", include_domains=["example.com"])

        assert len(result["results"]) == 1
        assert result["results"][0]["url"] == "https://example.com/page"

    def test_client_side_domain_exclude(self):
        mock_app_cls = MagicMock()
        mock_app_cls.return_value.search.return_value = [
            {"url": "https://example.com/page", "title": "Good", "description": ""},
            {"url": "https://bad.com/page", "title": "Bad", "description": ""},
        ]
        mock_fc_mod = MagicMock()
        mock_fc_mod.FirecrawlApp = mock_app_cls

        with (
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "key"}),
            patch.dict("sys.modules", {"firecrawl": mock_fc_mod}),
        ):
            from loom.providers.firecrawl import search_firecrawl

            result = search_firecrawl("test", exclude_domains=["bad.com"])

        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Good"

    def test_api_error(self):
        mock_app_cls = MagicMock()
        mock_app_cls.return_value.search.side_effect = RuntimeError("API down")
        mock_fc_mod = MagicMock()
        mock_fc_mod.FirecrawlApp = mock_app_cls

        with (
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "key"}),
            patch.dict("sys.modules", {"firecrawl": mock_fc_mod}),
        ):
            from loom.providers.firecrawl import search_firecrawl

            result = search_firecrawl("test")

        assert "API down" in result["error"]

    def test_snippet_truncation(self):
        mock_app_cls = MagicMock()
        mock_app_cls.return_value.search.return_value = [
            {"url": "https://x.com", "title": "T", "description": "d" * 1000}
        ]
        mock_fc_mod = MagicMock()
        mock_fc_mod.FirecrawlApp = mock_app_cls

        with (
            patch.dict("os.environ", {"FIRECRAWL_API_KEY": "key"}),
            patch.dict("sys.modules", {"firecrawl": mock_fc_mod}),
        ):
            from loom.providers.firecrawl import search_firecrawl

            result = search_firecrawl("test")

        assert len(result["results"][0]["snippet"]) == 500
