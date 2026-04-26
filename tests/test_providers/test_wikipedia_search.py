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
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "query": {
                "search": [
                    {
                        "title": "Test Article",
                        "snippet": "This is a test article about testing.",
                    }
                ]
            }
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp

        with patch("loom.providers.wikipedia_search._get_wiki_client", return_value=mock_client):
            from loom.providers.wikipedia_search import search_wikipedia

            result = search_wikipedia("test", n=1)

        assert "error" not in result
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Test Article"
        assert "test article" in result["results"][0]["snippet"].lower()

    def test_no_results(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"query": {"search": []}}
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp

        with patch("loom.providers.wikipedia_search._get_wiki_client", return_value=mock_client):
            from loom.providers.wikipedia_search import search_wikipedia

            result = search_wikipedia("xyznonexistent")

        assert result["results"] == []

    def test_connection_error(self):
        import httpx

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("DNS failed")

        with patch("loom.providers.wikipedia_search._get_wiki_client", return_value=mock_client):
            from loom.providers.wikipedia_search import search_wikipedia

            result = search_wikipedia("test")

        assert "search failed" in result["error"]
