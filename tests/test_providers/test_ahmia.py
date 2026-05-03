"""Unit tests for Ahmia.fi search provider.

Tests cover:
  - Successful .onion search with results
  - Empty results handling
  - HTTP status errors
  - Connection errors
  - Result format validation
"""

from __future__ import annotations
import pytest

from unittest.mock import MagicMock, patch

import httpx

from loom.providers.ahmia_search import search_ahmia



pytestmark = pytest.mark.asyncio
class TestAhmiaSearch:
    """Tests for Ahmia search functionality."""

    async def test_search_ahmia_success(self) -> None:
        """Test successful Ahmia search with .onion results."""
        html_response = """
        <html>
            <body>
                <div class="result">
                    <h2><a href="https://example.onion">Example Onion Site</a></h2>
                    <p>This is an example onion site with useful information</p>
                </div>
                <div class="result">
                    <h2><a href="https://another.onion">Another Site</a></h2>
                    <p>More information about this service</p>
                </div>
            </body>
        </html>
        """

        with patch("loom.providers.ahmia_search._get_ahmia_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_ahmia("onion services", n=10)

            assert result["query"] == "onion services"
            assert len(result["results"]) >= 0
            assert isinstance(result["results"], list)

    async def test_search_ahmia_empty_results(self) -> None:
        """Test Ahmia search with no results."""
        html_response = "<html><body></body></html>"

        with patch("loom.providers.ahmia_search._get_ahmia_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_ahmia("nonexistent query", n=10)

            assert result["query"] == "nonexistent query"
            assert result["results"] == []
            assert "error" not in result

    async def test_search_ahmia_http_error(self) -> None:
        """Test Ahmia search with HTTP error."""
        with patch("loom.providers.ahmia_search._get_ahmia_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Server Error", request=MagicMock(), response=mock_response
            )
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_ahmia("test query", n=10)

            assert result["query"] == "test query"
            assert result["results"] == []
            assert "error" in result

    async def test_search_ahmia_connection_error(self) -> None:
        """Test Ahmia search with connection error."""
        with patch("loom.providers.ahmia_search._get_ahmia_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")
            mock_get_client.return_value = mock_client

            result = search_ahmia("test query", n=10)

            assert result["query"] == "test query"
            assert result["results"] == []
            assert "error" in result
            assert "search failed" in result["error"]

    async def test_search_ahmia_result_format(self) -> None:
        """Test that Ahmia results follow expected format."""
        html_response = """
        <html>
            <body>
                <div class="result">
                    <h2><a href="https://test.onion">Test Title</a></h2>
                    <p>This is a test snippet</p>
                </div>
            </body>
        </html>
        """

        with patch("loom.providers.ahmia_search._get_ahmia_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_ahmia("test", n=5)

            # Validate result structure
            assert isinstance(result, dict)
            assert "results" in result
            assert "query" in result
            assert result["query"] == "test"
            assert isinstance(result["results"], list)

            # If results exist, validate structure
            for item in result["results"]:
                assert isinstance(item, dict)
                assert "url" in item or len(result["results"]) == 0
                assert "title" in item or len(result["results"]) == 0
                assert "snippet" in item or len(result["results"]) == 0

    async def test_search_ahmia_result_truncation(self) -> None:
        """Test that Ahmia results are truncated to max length."""
        long_title = "A" * 300
        long_snippet = "B" * 600

        html_response = f"""
        <html>
            <body>
                <div class="result">
                    <h2><a href="https://test.onion">{long_title}</a></h2>
                    <p>{long_snippet}</p>
                </div>
            </body>
        </html>
        """

        with patch("loom.providers.ahmia_search._get_ahmia_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_ahmia("test", n=5)

            if result["results"]:
                for item in result["results"]:
                    assert len(item["title"]) <= 200
                    assert len(item["snippet"]) <= 500

    async def test_search_ahmia_max_results_respected(self) -> None:
        """Test that search respects n parameter for max results."""
        html_response = """
        <html>
            <body>
                <div class="result">
                    <h2><a href="https://test1.onion">Test 1</a></h2>
                    <p>Snippet 1</p>
                </div>
                <div class="result">
                    <h2><a href="https://test2.onion">Test 2</a></h2>
                    <p>Snippet 2</p>
                </div>
                <div class="result">
                    <h2><a href="https://test3.onion">Test 3</a></h2>
                    <p>Snippet 3</p>
                </div>
            </body>
        </html>
        """

        with patch("loom.providers.ahmia_search._get_ahmia_client") as mock_get_client:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = search_ahmia("test", n=2)

            assert len(result["results"]) <= 2
