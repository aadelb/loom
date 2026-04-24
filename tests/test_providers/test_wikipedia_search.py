"""Tests for Wikipedia search provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_wiki_module():
    sys.modules.pop("loom.providers.wikipedia_search", None)
    yield
    sys.modules.pop("loom.providers.wikipedia_search", None)


class TestSearchWikipedia:
    def test_basic_search(self):
        mock_opensearch_resp = MagicMock()
        mock_opensearch_resp.status_code = 200
        mock_opensearch_resp.json.return_value = [
            "test",
            ["Test Article"],
            [""],
            ["https://en.wikipedia.org/wiki/Test_Article"],
        ]
        mock_opensearch_resp.raise_for_status = MagicMock()

        mock_summary_resp = MagicMock()
        mock_summary_resp.status_code = 200
        mock_summary_resp.json.return_value = {
            "title": "Test Article",
            "extract": "This is a test article about testing.",
            "thumbnail": {"source": "https://img.example.com/thumb.jpg"},
            "description": "A test article",
        }

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = [mock_opensearch_resp, mock_summary_resp]

        with patch("httpx.Client", return_value=mock_client):
            from loom.providers.wikipedia_search import search_wikipedia

            result = search_wikipedia("test", n=1)

        assert "error" not in result
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Test Article"
        assert "test article" in result["results"][0]["snippet"].lower()

    def test_no_results(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = ["test", [], [], []]
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.providers.wikipedia_search import search_wikipedia

            result = search_wikipedia("xyznonexistent")

        assert result["results"] == []

    def test_connection_error(self):
        import httpx

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = httpx.ConnectError("DNS failed")

        with patch("httpx.Client", return_value=mock_client):
            from loom.providers.wikipedia_search import search_wikipedia

            result = search_wikipedia("test")

        assert "DNS failed" in result["error"]
