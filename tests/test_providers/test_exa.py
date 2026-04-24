"""Tests for Exa search provider."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_exa_module():
    """Ensure clean import state for each test."""
    sys.modules.pop("loom.providers.exa", None)
    yield
    sys.modules.pop("loom.providers.exa", None)


class TestSearchExa:
    def test_missing_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            from loom.providers.exa import search_exa

            result = search_exa("test query")
            assert result["error"] == "EXA_API_KEY not set"
            assert result["results"] == []
            assert result["query"] == "test query"

    def test_sdk_not_installed(self):
        with (
            patch.dict("os.environ", {"EXA_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"exa_py": None}),
        ):
            from loom.providers.exa import search_exa

            result = search_exa("test query")
            assert "not installed" in result["error"]

    def test_basic_search(self):
        mock_result = SimpleNamespace(
            url="https://example.com",
            title="Example",
            text="Example text content for testing",
            score=0.95,
            published_date="2024-01-01",
        )
        mock_response = SimpleNamespace(results=[mock_result])
        mock_exa_cls = MagicMock()
        mock_exa_cls.return_value.search_and_contents.return_value = mock_response
        mock_exa_mod = MagicMock()
        mock_exa_mod.Exa = mock_exa_cls

        with (
            patch.dict("os.environ", {"EXA_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"exa_py": mock_exa_mod}),
        ):
            from loom.providers.exa import search_exa

            result = search_exa("test query", n=5)

        assert "error" not in result
        assert len(result["results"]) == 1
        assert result["results"][0]["url"] == "https://example.com"
        assert result["results"][0]["title"] == "Example"
        assert result["results"][0]["score"] == 0.95

    def test_domain_filtering(self):
        mock_exa_cls = MagicMock()
        mock_exa_cls.return_value.search_and_contents.return_value = SimpleNamespace(results=[])
        mock_exa_mod = MagicMock()
        mock_exa_mod.Exa = mock_exa_cls

        with (
            patch.dict("os.environ", {"EXA_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"exa_py": mock_exa_mod}),
        ):
            from loom.providers.exa import search_exa

            search_exa("test", include_domains=["example.com"], exclude_domains=["bad.com"])

        call_kwargs = mock_exa_cls.return_value.search_and_contents.call_args
        assert call_kwargs.kwargs.get("include_domains") == ["example.com"]
        assert call_kwargs.kwargs.get("exclude_domains") == ["bad.com"]

    def test_date_range(self):
        mock_exa_cls = MagicMock()
        mock_exa_cls.return_value.search_and_contents.return_value = SimpleNamespace(results=[])
        mock_exa_mod = MagicMock()
        mock_exa_mod.Exa = mock_exa_cls

        with (
            patch.dict("os.environ", {"EXA_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"exa_py": mock_exa_mod}),
        ):
            from loom.providers.exa import search_exa

            search_exa("test", start_date="2024-01-01", end_date="2024-12-31")

        call_kwargs = mock_exa_cls.return_value.search_and_contents.call_args
        assert call_kwargs.kwargs.get("start_published_date") == "2024-01-01"
        assert call_kwargs.kwargs.get("end_published_date") == "2024-12-31"

    def test_snippet_truncation(self):
        long_text = "x" * 1000
        mock_result = SimpleNamespace(
            url="https://example.com", title="T", text=long_text, score=0.5, published_date=None
        )
        mock_exa_cls = MagicMock()
        mock_exa_cls.return_value.search_and_contents.return_value = SimpleNamespace(
            results=[mock_result]
        )
        mock_exa_mod = MagicMock()
        mock_exa_mod.Exa = mock_exa_cls

        with (
            patch.dict("os.environ", {"EXA_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"exa_py": mock_exa_mod}),
        ):
            from loom.providers.exa import search_exa

            result = search_exa("test")

        assert len(result["results"][0]["snippet"]) == 500

    def test_api_error(self):
        mock_exa_cls = MagicMock()
        mock_exa_cls.return_value.search_and_contents.side_effect = RuntimeError("API down")
        mock_exa_mod = MagicMock()
        mock_exa_mod.Exa = mock_exa_cls

        with (
            patch.dict("os.environ", {"EXA_API_KEY": "test-key"}),
            patch.dict("sys.modules", {"exa_py": mock_exa_mod}),
        ):
            from loom.providers.exa import search_exa

            result = search_exa("test")

        assert "API down" in result["error"]
        assert result["results"] == []
