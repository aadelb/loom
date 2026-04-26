"""Tests for NewsAPI search provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def _clear_newsapi_module():
    sys.modules.pop("loom.providers.newsapi_search", None)
    yield
    sys.modules.pop("loom.providers.newsapi_search", None)


class TestSearchNewsAPI:
    def test_missing_api_key(self):
        """Test returns error when NEWS_API_KEY is not set."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.providers.newsapi_search import search_newsapi

            result = search_newsapi("test query")

            assert result["error"] == "NEWS_API_KEY not set"
            assert result["results"] == []

    def test_success(self):
        """Test successful news search with mocked httpx."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "articles": [
                {
                    "url": "https://example.com/article",
                    "title": "Breaking News",
                    "description": "Important story",
                    "publishedAt": "2024-01-15T10:00:00Z",
                },
                {
                    "url": "https://example.com/article2",
                    "title": "Another Story",
                    "description": "Another important story",
                    "publishedAt": "2024-01-15T09:00:00Z",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"NEWS_API_KEY": "test-key"}), patch(
            "loom.providers.newsapi_search._get_newsapi_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.newsapi_search import search_newsapi

            result = search_newsapi("technology", n=10)

            assert "error" not in result
            assert len(result["results"]) == 2
            assert result["results"][0]["title"] == "Breaking News"
            assert result["results"][0]["snippet"] == "Important story"
            assert result["query"] == "technology"

    def test_n_capped_at_100(self):
        """Test that n parameter is capped at 100."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"articles": []}
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"NEWS_API_KEY": "key"}), patch(
            "loom.providers.newsapi_search._get_newsapi_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.newsapi_search import search_newsapi

            search_newsapi("test", n=500)

            call_args = mock_client.get.call_args
            assert call_args.kwargs["params"]["pageSize"] == 100

    def test_snippet_truncation(self):
        """Test that description is truncated to 500 chars."""
        long_description = "x" * 1000
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "articles": [
                {
                    "url": "https://example.com",
                    "title": "Test",
                    "description": long_description,
                    "publishedAt": "2024-01-15T10:00:00Z",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"NEWS_API_KEY": "key"}), patch(
            "loom.providers.newsapi_search._get_newsapi_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.newsapi_search import search_newsapi

            result = search_newsapi("test")

            assert len(result["results"][0]["snippet"]) == 500

    def test_http_error_429(self):
        """Test handling of HTTP 429 rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Rate Limited", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"NEWS_API_KEY": "key"}), patch(
            "loom.providers.newsapi_search._get_newsapi_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.newsapi_search import search_newsapi

            result = search_newsapi("test")

            assert "search failed" in result["error"]
            assert result["results"] == []

    def test_http_error_401(self):
        """Test handling of HTTP 401 unauthorized error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        with patch.dict("os.environ", {"NEWS_API_KEY": "invalid"}), patch(
            "loom.providers.newsapi_search._get_newsapi_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.newsapi_search import search_newsapi

            result = search_newsapi("test")

            assert "search failed" in result["error"]

    def test_connection_error(self):
        """Test handling of connection error."""
        with patch.dict("os.environ", {"NEWS_API_KEY": "key"}), patch(
            "loom.providers.newsapi_search._get_newsapi_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.ConnectError("DNS failed")
            mock_get_client.return_value = mock_client

            from loom.providers.newsapi_search import search_newsapi

            result = search_newsapi("test")

            assert "search failed" in result["error"]
            assert result["results"] == []

    def test_empty_description_handling(self):
        """Test handling of articles with missing description."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "articles": [
                {
                    "url": "https://example.com",
                    "title": "News",
                    "description": None,
                    "publishedAt": "2024-01-15T10:00:00Z",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.dict("os.environ", {"NEWS_API_KEY": "key"}), patch(
            "loom.providers.newsapi_search._get_newsapi_client"
        ) as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.newsapi_search import search_newsapi

            result = search_newsapi("test")

            assert result["results"][0]["snippet"] == ""
