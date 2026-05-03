"""Unit tests for DarkSearch.io search provider.

Tests cover:
  - Successful darkweb search via API
  - Empty results handling
  - Rate limiting (429)
  - HTTP errors
  - Result format validation
"""

from __future__ import annotations
import pytest

from unittest.mock import MagicMock, patch

import httpx

from loom.providers.darksearch_search import search_darksearch



pytestmark = pytest.mark.asyncio
class TestDarkSearchSearch:
    """Tests for DarkSearch search functionality."""

    async def test_search_darksearch_success(self) -> None:
        """Test successful DarkSearch API search with results."""
        api_response = {
            "data": [
                {
                    "link": "https://example.onion/page1",
                    "title": "Example Onion Market",
                    "description": "A marketplace on the dark web",
                },
                {
                    "link": "https://another.onion/page2",
                    "title": "Anonymous Forum",
                    "description": "Discussion forum for privacy advocates",
                },
            ]
        }

        with patch("loom.providers.darksearch_search._get_darksearch_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = api_response
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_darksearch("privacy", n=10)

            assert result["query"] == "privacy"
            assert len(result["results"]) == 2
            assert result["results"][0]["url"] == "https://example.onion/page1"
            assert result["results"][0]["title"] == "Example Onion Market"

    async def test_search_darksearch_empty_results(self) -> None:
        """Test DarkSearch search with no results."""
        api_response = {"data": []}

        with patch("loom.providers.darksearch_search._get_darksearch_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = api_response
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_darksearch("nonexistent query", n=10)

            assert result["query"] == "nonexistent query"
            assert result["results"] == []
            assert "error" not in result

    async def test_search_darksearch_rate_limited(self) -> None:
        """Test DarkSearch search when rate limited (HTTP 429)."""
        with patch("loom.providers.darksearch_search._get_darksearch_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "429 Too Many Requests", request=MagicMock(), response=mock_response
            )
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_darksearch("test query", n=10)

            assert result["query"] == "test query"
            assert result["results"] == []
            assert "error" in result
            assert result["error"] == "rate_limited"

    async def test_search_darksearch_http_error(self) -> None:
        """Test DarkSearch search with non-429 HTTP error."""
        with patch("loom.providers.darksearch_search._get_darksearch_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Server Error", request=MagicMock(), response=mock_response
            )
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_darksearch("test query", n=10)

            assert result["query"] == "test query"
            assert result["results"] == []
            assert "error" in result
            assert "HTTP 500" in result["error"]

    async def test_search_darksearch_connection_error(self) -> None:
        """Test DarkSearch search with connection error."""
        with patch("loom.providers.darksearch_search._get_darksearch_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")
            mock_get_client.return_value = mock_client

            result = search_darksearch("test query", n=10)

            assert result["query"] == "test query"
            assert result["results"] == []
            assert "error" in result

    async def test_search_darksearch_result_format(self) -> None:
        """Test that DarkSearch results follow expected format."""
        api_response = {
            "data": [
                {
                    "link": "https://test.onion",
                    "title": "Test Title",
                    "description": "Test description",
                }
            ]
        }

        with patch("loom.providers.darksearch_search._get_darksearch_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = api_response
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_darksearch("test", n=5)

            # Validate result structure
            assert isinstance(result, dict)
            assert "results" in result
            assert "query" in result
            assert result["query"] == "test"
            assert isinstance(result["results"], list)

            # Validate each result
            for item in result["results"]:
                assert isinstance(item, dict)
                assert "url" in item
                assert "title" in item
                assert "snippet" in item

    async def test_search_darksearch_result_truncation(self) -> None:
        """Test that DarkSearch results are truncated to max length."""
        long_title = "A" * 300
        long_snippet = "B" * 600

        api_response = {
            "data": [
                {
                    "link": "https://test.onion",
                    "title": long_title,
                    "description": long_snippet,
                }
            ]
        }

        with patch("loom.providers.darksearch_search._get_darksearch_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = api_response
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_darksearch("test", n=5)

            if result["results"]:
                for item in result["results"]:
                    assert len(item["title"]) <= 200
                    assert len(item["snippet"]) <= 500

    async def test_search_darksearch_missing_link(self) -> None:
        """Test that results without 'link' field are filtered out."""
        api_response = {
            "data": [
                {
                    "link": "https://valid.onion",
                    "title": "Valid Result",
                    "description": "This has a link",
                },
                {
                    "title": "Invalid Result",
                    "description": "This is missing a link",
                },
            ]
        }

        with patch("loom.providers.darksearch_search._get_darksearch_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = api_response
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_darksearch("test", n=10)

            # Only result with valid link should be included
            assert len(result["results"]) == 1
            assert result["results"][0]["url"] == "https://valid.onion"

    async def test_search_darksearch_max_results_respected(self) -> None:
        """Test that search respects n parameter for max results."""
        api_response = {
            "data": [
                {
                    "link": f"https://test{i}.onion",
                    "title": f"Test {i}",
                    "description": f"Snippet {i}",
                }
                for i in range(5)
            ]
        }

        with patch("loom.providers.darksearch_search._get_darksearch_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.json.return_value = api_response
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_darksearch("test", n=2)

            assert len(result["results"]) == 2
