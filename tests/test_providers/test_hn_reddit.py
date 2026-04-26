"""Tests for HackerNews and Reddit search providers."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_module_cache():
    """Ensure clean import state for each test."""
    sys.modules.pop("loom.providers.hn_reddit", None)
    yield
    sys.modules.pop("loom.providers.hn_reddit", None)


class TestSearchHackerNews:
    def test_basic_search(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "hits": [
                {
                    "url": "https://example.com",
                    "title": "Example Post",
                    "story_text": "This is a story.",
                    "points": 100,
                    "num_comments": 50,
                    "author": "user1",
                    "created_at": "2024-01-01T00:00:00Z",
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.providers.hn_reddit import search_hackernews

            result = search_hackernews("test query")

        assert "results" in result
        assert "query" in result
        assert "source" in result
        assert result["query"] == "test query"
        assert result["source"] == "hackernews"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Example Post"
        assert result["results"][0]["points"] == 100
        assert "error" not in result

    def test_empty_results(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"hits": []}
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.providers.hn_reddit import search_hackernews

            result = search_hackernews("empty test")

        assert result["results"] == []
        assert result["query"] == "empty test"

    def test_error_handling(self):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("API down")

        with patch("httpx.Client", return_value=mock_client):
            from loom.providers.hn_reddit import search_hackernews

            result = search_hackernews("error test")

        assert result["results"] == []
        assert result["query"] == "error test"
        assert "search failed" in result["error"]


class TestSearchReddit:
    def test_basic_search(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "permalink": "/r/test/comments/123/example/",
                            "title": "Reddit Post",
                            "selftext": "Post content.",
                            "score": 500,
                            "num_comments": 100,
                            "subreddit": "test",
                            "author": "redditor1",
                            "created_utc": 1600000000,
                        }
                    }
                ]
            }
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.providers.hn_reddit import search_reddit

            result = search_reddit("test query")

        assert "results" in result
        assert "query" in result
        assert "source" in result
        assert result["query"] == "test query"
        assert result["source"] == "reddit"
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Reddit Post"
        assert result["results"][0]["score"] == 500
        assert result["results"][0]["url"] == "https://www.reddit.com/r/test/comments/123/example/"
        assert "error" not in result

    def test_subreddit_filter(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": {"children": []}}
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_resp

        with patch("httpx.Client", return_value=mock_client):
            from loom.providers.hn_reddit import search_reddit

            search_reddit("test query", subreddit="python")

        mock_client.get.assert_called_once()
        args, kwargs = mock_client.get.call_args
        assert "r/python/search.json" in args[0]
        assert kwargs["params"]["restrict_sr"] == "on"

    def test_error_handling(self):
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.side_effect = Exception("Reddit API down")

        with patch("httpx.Client", return_value=mock_client):
            from loom.providers.hn_reddit import search_reddit

            result = search_reddit("error test")

        assert result["results"] == []
        assert result["query"] == "error test"
        assert "search failed" in result["error"]
