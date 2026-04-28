"""Tests for real-time monitoring tool (realtime_monitor)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.realtime_monitor import research_realtime_monitor


class TestResearchRealtimeMonitor:
    """Test realtime_monitor core functionality."""

    def test_empty_topics_returns_empty_result(self) -> None:
        """Empty topics list returns empty result."""
        result = research_realtime_monitor([])

        assert result["topics"] == []
        assert result["total_mentions"] == 0
        assert result["mentions_by_topic"] == {}
        assert result["mentions_by_source"] == {}
        assert result["recent_items"] == []

    def test_single_topic_all_sources(self) -> None:
        """Query single topic across all sources."""
        mock_items = [
            {
                "topic": "Python",
                "source": "HackerNews",
                "title": "Test Story",
                "url": "https://example.com",
                "timestamp": "2026-04-28T10:00:00+00:00",
                "score": 42.0,
            }
        ]

        with patch("loom.tools.realtime_monitor._fetch_hackernews", new_callable=AsyncMock) as mock_hn:
            with patch("loom.tools.realtime_monitor._fetch_reddit", new_callable=AsyncMock) as mock_reddit:
                with patch("loom.tools.realtime_monitor._fetch_arxiv", new_callable=AsyncMock) as mock_arxiv:
                    with patch("loom.tools.realtime_monitor._fetch_newsapi", new_callable=AsyncMock) as mock_news:
                        with patch(
                            "loom.tools.realtime_monitor._fetch_wikipedia_changes", new_callable=AsyncMock
                        ) as mock_wiki:
                            mock_hn.return_value = mock_items
                            mock_reddit.return_value = []
                            mock_arxiv.return_value = []
                            mock_news.return_value = []
                            mock_wiki.return_value = []

                            result = research_realtime_monitor(["Python"], hours_back=24)

                            assert result["topics"] == ["Python"]
                            assert result["time_range_hours"] == 24
                            assert result["total_mentions"] == 1
                            assert result["mentions_by_topic"]["Python"] == 1
                            assert result["mentions_by_source"]["hackernews"] == 1
                            assert len(result["recent_items"]) == 1
                            assert result["recent_items"][0]["title"] == "Test Story"

    def test_multiple_topics(self) -> None:
        """Query multiple topics."""
        items_python = [
            {
                "topic": "Python",
                "source": "HackerNews",
                "title": "Python Story",
                "url": "https://example.com",
                "timestamp": "2026-04-28T10:00:00+00:00",
                "score": 10.0,
            }
        ]
        items_ai = [
            {
                "topic": "AI",
                "source": "arXiv",
                "title": "AI Paper",
                "url": "https://arxiv.org/abs/123",
                "timestamp": "2026-04-28",
                "score": 0.0,
            }
        ]

        with patch("loom.tools.realtime_monitor._fetch_hackernews", new_callable=AsyncMock) as mock_hn:
            with patch("loom.tools.realtime_monitor._fetch_reddit", new_callable=AsyncMock) as mock_reddit:
                with patch("loom.tools.realtime_monitor._fetch_arxiv", new_callable=AsyncMock) as mock_arxiv:
                    with patch("loom.tools.realtime_monitor._fetch_newsapi", new_callable=AsyncMock) as mock_news:
                        with patch(
                            "loom.tools.realtime_monitor._fetch_wikipedia_changes", new_callable=AsyncMock
                        ) as mock_wiki:
                            # HackerNews returns item for Python topic
                            mock_hn.side_effect = lambda client, topic, hours: (
                                items_python if topic == "Python" else []
                            )
                            mock_reddit.return_value = []
                            # arXiv returns item for AI topic
                            mock_arxiv.side_effect = lambda client, topic: (
                                items_ai if topic == "AI" else []
                            )
                            mock_news.return_value = []
                            mock_wiki.return_value = []

                            result = research_realtime_monitor(["Python", "AI"])

                            assert result["topics"] == ["Python", "AI"]
                            assert result["total_mentions"] == 2
                            assert result["mentions_by_topic"]["Python"] == 1
                            assert result["mentions_by_topic"]["AI"] == 1
                            assert len(result["recent_items"]) == 2

    def test_specific_sources_filter(self) -> None:
        """Only query specified sources."""
        mock_items = [
            {
                "topic": "Python",
                "source": "Reddit",
                "title": "Reddit Post",
                "url": "https://reddit.com",
                "timestamp": "2026-04-28T10:00:00+00:00",
                "score": 50.0,
            }
        ]

        with patch("loom.tools.realtime_monitor._fetch_reddit", new_callable=AsyncMock) as mock_reddit:
            with patch("loom.tools.realtime_monitor._fetch_hackernews", new_callable=AsyncMock) as mock_hn:
                mock_reddit.return_value = mock_items
                # If HackerNews is called, fail the test
                mock_hn.side_effect = AssertionError("HackerNews should not be called")

                result = research_realtime_monitor(["Python"], sources=["reddit"])

                # Verify only Reddit was called
                mock_reddit.assert_called()
                assert result["mentions_by_source"]["reddit"] == 1
                # HackerNews should not be in the result
                assert result["mentions_by_source"].get("hackernews", 0) == 0

    def test_items_sorted_by_timestamp_newest_first(self) -> None:
        """Results are sorted by timestamp, newest first."""
        older_item = {
            "topic": "News",
            "source": "HackerNews",
            "title": "Older Story",
            "url": "https://example.com/old",
            "timestamp": "2026-04-27T10:00:00+00:00",
            "score": 10.0,
        }
        newer_item = {
            "topic": "News",
            "source": "HackerNews",
            "title": "Newer Story",
            "url": "https://example.com/new",
            "timestamp": "2026-04-28T15:00:00+00:00",
            "score": 20.0,
        }
        middle_item = {
            "topic": "News",
            "source": "HackerNews",
            "title": "Middle Story",
            "url": "https://example.com/middle",
            "timestamp": "2026-04-28T12:00:00+00:00",
            "score": 15.0,
        }

        with patch("loom.tools.realtime_monitor._fetch_hackernews", new_callable=AsyncMock) as mock_hn:
            with patch("loom.tools.realtime_monitor._fetch_reddit", new_callable=AsyncMock) as mock_reddit:
                with patch("loom.tools.realtime_monitor._fetch_arxiv", new_callable=AsyncMock) as mock_arxiv:
                    with patch("loom.tools.realtime_monitor._fetch_newsapi", new_callable=AsyncMock) as mock_news:
                        with patch(
                            "loom.tools.realtime_monitor._fetch_wikipedia_changes", new_callable=AsyncMock
                        ) as mock_wiki:
                            # Return items in mixed order
                            mock_hn.return_value = [older_item, newer_item, middle_item]
                            mock_reddit.return_value = []
                            mock_arxiv.return_value = []
                            mock_news.return_value = []
                            mock_wiki.return_value = []

                            result = research_realtime_monitor(["News"])

                            items = result["recent_items"]
                            assert len(items) == 3
                            # Verify sorted newest first
                            assert items[0]["title"] == "Newer Story"
                            assert items[1]["title"] == "Middle Story"
                            assert items[2]["title"] == "Older Story"

    def test_mentions_by_source_aggregation(self) -> None:
        """Mentions are correctly aggregated by source."""
        hn_items = [
            {
                "topic": "Python",
                "source": "HackerNews",
                "title": "HN Story 1",
                "url": "https://hn.com/1",
                "timestamp": "2026-04-28T10:00:00+00:00",
                "score": 10.0,
            },
            {
                "topic": "Python",
                "source": "HackerNews",
                "title": "HN Story 2",
                "url": "https://hn.com/2",
                "timestamp": "2026-04-28T11:00:00+00:00",
                "score": 20.0,
            },
        ]
        reddit_items = [
            {
                "topic": "Python",
                "source": "Reddit",
                "title": "Reddit Post",
                "url": "https://reddit.com/1",
                "timestamp": "2026-04-28T12:00:00+00:00",
                "score": 50.0,
            }
        ]

        with patch("loom.tools.realtime_monitor._fetch_hackernews", new_callable=AsyncMock) as mock_hn:
            with patch("loom.tools.realtime_monitor._fetch_reddit", new_callable=AsyncMock) as mock_reddit:
                with patch("loom.tools.realtime_monitor._fetch_arxiv", new_callable=AsyncMock) as mock_arxiv:
                    with patch("loom.tools.realtime_monitor._fetch_newsapi", new_callable=AsyncMock) as mock_news:
                        with patch(
                            "loom.tools.realtime_monitor._fetch_wikipedia_changes", new_callable=AsyncMock
                        ) as mock_wiki:
                            mock_hn.return_value = hn_items
                            mock_reddit.return_value = reddit_items
                            mock_arxiv.return_value = []
                            mock_news.return_value = []
                            mock_wiki.return_value = []

                            result = research_realtime_monitor(["Python"])

                            assert result["mentions_by_source"]["hackernews"] == 2
                            assert result["mentions_by_source"]["reddit"] == 1
                            assert result["total_mentions"] == 3

    def test_hours_back_parameter_passed(self) -> None:
        """hours_back parameter is passed to HackerNews fetch."""
        with patch("loom.tools.realtime_monitor._fetch_hackernews", new_callable=AsyncMock) as mock_hn:
            with patch("loom.tools.realtime_monitor._fetch_reddit", new_callable=AsyncMock) as mock_reddit:
                with patch("loom.tools.realtime_monitor._fetch_arxiv", new_callable=AsyncMock) as mock_arxiv:
                    with patch("loom.tools.realtime_monitor._fetch_newsapi", new_callable=AsyncMock) as mock_news:
                        with patch(
                            "loom.tools.realtime_monitor._fetch_wikipedia_changes", new_callable=AsyncMock
                        ) as mock_wiki:
                            mock_hn.return_value = []
                            mock_reddit.return_value = []
                            mock_arxiv.return_value = []
                            mock_news.return_value = []
                            mock_wiki.return_value = []

                            research_realtime_monitor(["Python"], hours_back=48)

                            # Verify hours_back was passed to HackerNews
                            _, kwargs = mock_hn.call_args
                            assert kwargs.get("hours_back") == 48 or (
                                len(mock_hn.call_args[0]) >= 3 and mock_hn.call_args[0][2] == 48
                            )

    def test_invalid_sources_ignored(self) -> None:
        """Invalid source names are silently ignored."""
        with patch("loom.tools.realtime_monitor._fetch_hackernews", new_callable=AsyncMock) as mock_hn:
            with patch("loom.tools.realtime_monitor._fetch_reddit", new_callable=AsyncMock) as mock_reddit:
                with patch("loom.tools.realtime_monitor._fetch_arxiv", new_callable=AsyncMock) as mock_arxiv:
                    with patch("loom.tools.realtime_monitor._fetch_newsapi", new_callable=AsyncMock) as mock_news:
                        with patch(
                            "loom.tools.realtime_monitor._fetch_wikipedia_changes", new_callable=AsyncMock
                        ) as mock_wiki:
                            mock_hn.return_value = []
                            mock_reddit.return_value = []
                            mock_arxiv.return_value = []
                            mock_news.return_value = []
                            mock_wiki.return_value = []

                            # Include invalid source name
                            result = research_realtime_monitor(
                                ["Python"], sources=["reddit", "invalid_source", "arxiv"]
                            )

                            # Should only call valid sources
                            assert mock_reddit.called
                            assert mock_arxiv.called
                            assert not mock_hn.called  # hackernews not in sources list
                            assert result["mentions_by_source"].get("invalid_source") is None

    def test_mentions_by_topic_aggregation(self) -> None:
        """Mentions are correctly aggregated by topic."""
        python_items = [
            {
                "topic": "Python",
                "source": "HackerNews",
                "title": "Python Story",
                "url": "https://hn.com/py",
                "timestamp": "2026-04-28T10:00:00+00:00",
                "score": 10.0,
            }
        ]
        rust_items = [
            {
                "topic": "Rust",
                "source": "HackerNews",
                "title": "Rust Story 1",
                "url": "https://hn.com/rust1",
                "timestamp": "2026-04-28T11:00:00+00:00",
                "score": 20.0,
            },
            {
                "topic": "Rust",
                "source": "HackerNews",
                "title": "Rust Story 2",
                "url": "https://hn.com/rust2",
                "timestamp": "2026-04-28T12:00:00+00:00",
                "score": 30.0,
            },
        ]

        with patch("loom.tools.realtime_monitor._fetch_hackernews", new_callable=AsyncMock) as mock_hn:
            with patch("loom.tools.realtime_monitor._fetch_reddit", new_callable=AsyncMock) as mock_reddit:
                with patch("loom.tools.realtime_monitor._fetch_arxiv", new_callable=AsyncMock) as mock_arxiv:
                    with patch("loom.tools.realtime_monitor._fetch_newsapi", new_callable=AsyncMock) as mock_news:
                        with patch(
                            "loom.tools.realtime_monitor._fetch_wikipedia_changes", new_callable=AsyncMock
                        ) as mock_wiki:
                            # Return different items for different topics
                            def hn_side_effect(client, topic, hours):  # type: ignore
                                if topic == "Python":
                                    return python_items
                                elif topic == "Rust":
                                    return rust_items
                                return []

                            mock_hn.side_effect = hn_side_effect
                            mock_reddit.return_value = []
                            mock_arxiv.return_value = []
                            mock_news.return_value = []
                            mock_wiki.return_value = []

                            result = research_realtime_monitor(["Python", "Rust"])

                            assert result["mentions_by_topic"]["Python"] == 1
                            assert result["mentions_by_topic"]["Rust"] == 2
                            assert result["total_mentions"] == 3


class TestHackerNewsFetch:
    """Test HackerNews-specific fetch logic."""

    @pytest.mark.asyncio
    async def test_hackernews_parse_response(self, mock_httpx_transport) -> None:
        """Test HackerNews response parsing."""
        from loom.tools import realtime_monitor

        mock_response = {
            "hits": [
                {
                    "title": "Test Story",
                    "url": "https://example.com",
                    "points": 42,
                    "created_at": "2026-04-28T10:00:00Z",
                    "objectID": "12345",
                }
            ]
        }

        import json
        from httpx import Response

        transport = mock_httpx_transport
        transport.mock_response = lambda url, status=200, json_data=None: Response(
            status_code=status, content=json.dumps(json_data or {}).encode()
        )

        import httpx

        async with httpx.AsyncClient(transport=transport) as client:
            # Mock the request
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = mock_response
                mock_get.return_value = mock_resp

                items = await realtime_monitor._fetch_hackernews(client, "Python", 24)

                assert len(items) > 0


class TestRedditFetch:
    """Test Reddit-specific fetch logic."""

    @pytest.mark.asyncio
    async def test_reddit_parse_response(self) -> None:
        """Test Reddit response parsing."""
        from loom.tools import realtime_monitor

        mock_response = {
            "data": {
                "children": [
                    {
                        "data": {
                            "title": "Python Discussion",
                            "permalink": "/r/python/comments/123/title",
                            "score": 100,
                            "created_utc": 1714303200,  # 2026-04-28
                        }
                    }
                ]
            }
        }

        import httpx

        async with httpx.AsyncClient() as client:
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = mock_response
                mock_get.return_value = mock_resp

                items = await realtime_monitor._fetch_reddit(client, "Python")

                assert len(items) == 1
                assert items[0]["title"] == "Python Discussion"
                assert items[0]["score"] == 100.0


class TestArxivFetch:
    """Test arXiv-specific fetch logic."""

    @pytest.mark.asyncio
    async def test_arxiv_parse_atom_feed(self) -> None:
        """Test arXiv Atom feed parsing."""
        from loom.tools import realtime_monitor

        atom_response = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Test Paper Title</title>
    <id>http://arxiv.org/abs/2304.12345v1</id>
    <published>2026-04-28T10:00:00Z</published>
  </entry>
</feed>"""

        import httpx

        async with httpx.AsyncClient() as client:
            with patch("httpx.AsyncClient.get") as mock_get:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.text = atom_response
                mock_get.return_value = mock_resp

                items = await realtime_monitor._fetch_arxiv(client, "machine learning")

                assert len(items) == 1
                assert "Test Paper Title" in items[0]["title"]
                assert "arxiv.org" in items[0]["url"]
