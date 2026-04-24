"""Tests for arXiv search provider."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_arxiv_module():
    sys.modules.pop("loom.providers.arxiv_search", None)
    yield
    sys.modules.pop("loom.providers.arxiv_search", None)


class TestSearchArxiv:
    def test_sdk_not_installed(self):
        with patch.dict("sys.modules", {"arxiv": None}):
            from loom.providers.arxiv_search import search_arxiv

            result = search_arxiv("test query")
            assert "not installed" in result["error"]

    def test_basic_search(self):
        from datetime import datetime

        mock_paper = SimpleNamespace(
            entry_id="https://arxiv.org/abs/2401.00001",
            title="Test Paper",
            summary="This is a test paper about transformers",
            published=datetime(2024, 1, 1),
            authors=[SimpleNamespace(name="Author One"), SimpleNamespace(name="Author Two")],
            categories=["cs.AI", "cs.CL"],
            pdf_url="https://arxiv.org/pdf/2401.00001",
        )

        mock_arxiv = MagicMock()
        mock_arxiv.SortCriterion.Relevance = "relevance"
        mock_arxiv.SortCriterion.LastUpdatedDate = "updated"
        mock_arxiv.SortCriterion.SubmittedDate = "submitted"
        mock_arxiv.Client.return_value.results.return_value = [mock_paper]
        mock_arxiv.Search = MagicMock()

        with patch.dict("sys.modules", {"arxiv": mock_arxiv}):
            from loom.providers.arxiv_search import search_arxiv

            result = search_arxiv("transformer", n=5)

        assert "error" not in result
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Test Paper"
        assert result["results"][0]["authors"] == ["Author One", "Author Two"]
        assert result["results"][0]["pdf_url"] == "https://arxiv.org/pdf/2401.00001"

    def test_empty_results(self):
        mock_arxiv = MagicMock()
        mock_arxiv.SortCriterion.Relevance = "relevance"
        mock_arxiv.Client.return_value.results.return_value = []
        mock_arxiv.Search = MagicMock()

        with patch.dict("sys.modules", {"arxiv": mock_arxiv}):
            from loom.providers.arxiv_search import search_arxiv

            result = search_arxiv("nothing")

        assert result["results"] == []

    def test_api_error(self):
        mock_arxiv = MagicMock()
        mock_arxiv.SortCriterion.Relevance = "relevance"
        mock_arxiv.Client.return_value.results.side_effect = RuntimeError("API error")
        mock_arxiv.Search = MagicMock()

        with patch.dict("sys.modules", {"arxiv": mock_arxiv}):
            from loom.providers.arxiv_search import search_arxiv

            result = search_arxiv("test")

        assert "API error" in result["error"]
