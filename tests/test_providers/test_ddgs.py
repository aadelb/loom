"""Tests for DuckDuckGo search provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_ddgs_module():
    sys.modules.pop("loom.providers.ddgs", None)
    yield
    sys.modules.pop("loom.providers.ddgs", None)


class TestSearchDdgs:
    def test_sdk_not_installed(self):
        with patch.dict("sys.modules", {"ddgs": None}):
            from loom.providers.ddgs import search_ddgs

            result = search_ddgs("test query")
            assert "not installed" in result["error"]

    def test_basic_search(self):
        mock_ddgs_cls = MagicMock()
        mock_ddgs_cls.return_value.text.return_value = [
            {"title": "Example", "href": "https://example.com", "body": "Example text"},
        ]
        mock_ddgs_mod = MagicMock()
        mock_ddgs_mod.DDGS = mock_ddgs_cls

        with patch.dict("sys.modules", {"ddgs": mock_ddgs_mod}):
            from loom.providers.ddgs import search_ddgs

            result = search_ddgs("test", n=5)

        assert "error" not in result
        assert len(result["results"]) == 1
        assert result["results"][0]["url"] == "https://example.com"
        assert result["results"][0]["title"] == "Example"

    def test_empty_results(self):
        mock_ddgs_cls = MagicMock()
        mock_ddgs_cls.return_value.text.return_value = []
        mock_ddgs_mod = MagicMock()
        mock_ddgs_mod.DDGS = mock_ddgs_cls

        with patch.dict("sys.modules", {"ddgs": mock_ddgs_mod}):
            from loom.providers.ddgs import search_ddgs

            result = search_ddgs("nothing")

        assert result["results"] == []
        assert "error" not in result

    def test_error_handling(self):
        mock_ddgs_cls = MagicMock()
        mock_ddgs_cls.return_value.text.side_effect = RuntimeError("rate limited")
        mock_ddgs_mod = MagicMock()
        mock_ddgs_mod.DDGS = mock_ddgs_cls

        with patch.dict("sys.modules", {"ddgs": mock_ddgs_mod}):
            from loom.providers.ddgs import search_ddgs

            result = search_ddgs("test")

        assert "rate limited" in result["error"]

    def test_snippet_truncation(self):
        mock_ddgs_cls = MagicMock()
        mock_ddgs_cls.return_value.text.return_value = [
            {"title": "T", "href": "https://x.com", "body": "b" * 1000},
        ]
        mock_ddgs_mod = MagicMock()
        mock_ddgs_mod.DDGS = mock_ddgs_cls

        with patch.dict("sys.modules", {"ddgs": mock_ddgs_mod}):
            from loom.providers.ddgs import search_ddgs

            result = search_ddgs("test")

        assert len(result["results"][0]["snippet"]) == 500
