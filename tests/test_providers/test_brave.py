"""Tests for Brave Search provider."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def _clear_brave_module():
    sys.modules.pop("loom.providers.brave", None)
    yield
    sys.modules.pop("loom.providers.brave", None)


class TestSearchBrave:
    def test_missing_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            from loom.providers.brave import search_brave

            result = search_brave("test query")
            assert result["error"] == "BRAVE_API_KEY not set"
            assert result["results"] == []

    def test_basic_search(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "url": "https://example.com",
                        "title": "Example",
                        "description": "An example page",
                        "page_age": "2024-01-15",
                    }
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch.dict("os.environ", {"BRAVE_API_KEY": "test-key"}),
            patch("loom.providers.brave._get_brave_client") as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.brave import search_brave

            result = search_brave("test query", n=5)

        assert "error" not in result
        assert len(result["results"]) == 1
        assert result["results"][0]["url"] == "https://example.com"
        assert result["results"][0]["snippet"] == "An example page"
        assert result["results"][0]["published_date"] == "2024-01-15"

    def test_n_capped_at_20(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"web": {"results": []}}
        mock_response.raise_for_status = MagicMock()

        with (
            patch.dict("os.environ", {"BRAVE_API_KEY": "key"}),
            patch("loom.providers.brave._get_brave_client") as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.brave import search_brave

            search_brave("test", n=50)

        call_args = mock_client.get.call_args
        assert call_args.kwargs.get("params", {}).get("count") == 20

    def test_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "rate limited", request=MagicMock(), response=mock_response
        )

        with (
            patch.dict("os.environ", {"BRAVE_API_KEY": "key"}),
            patch("loom.providers.brave._get_brave_client") as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.brave import search_brave

            result = search_brave("test")

        assert "HTTP 429" in result["error"]

    def test_snippet_truncation(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "web": {"results": [{"url": "https://x.com", "title": "T", "description": "z" * 1000}]}
        }
        mock_response.raise_for_status = MagicMock()

        with (
            patch.dict("os.environ", {"BRAVE_API_KEY": "key"}),
            patch("loom.providers.brave._get_brave_client") as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            from loom.providers.brave import search_brave

            result = search_brave("test")

        assert len(result["results"][0]["snippet"]) == 500

    def test_connection_error(self):
        with (
            patch.dict("os.environ", {"BRAVE_API_KEY": "key"}),
            patch("loom.providers.brave._get_brave_client") as mock_get_client,
        ):
            mock_client = MagicMock()
            mock_client.get.side_effect = httpx.ConnectError("DNS failed")
            mock_get_client.return_value = mock_client

            from loom.providers.brave import search_brave

            result = search_brave("test")

        assert "search failed" in result["error"]
