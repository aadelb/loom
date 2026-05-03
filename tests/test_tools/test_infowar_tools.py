"""Unit tests for infowar_tools — narrative tracking, bot detection, censorship analysis."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from loom.tools.infowar_tools import (
    _analyze_posting_times,
    _arxiv_search,
    _diff_robots_rules,
    _dns_lookup_doh,
    _hn_search,
    _lumen_database_check,
    _reddit_search,
    _robots_txt_cdx,
    _robots_txt_content,
    research_bot_detector,
    research_censorship_detector,
    research_deleted_social,
    research_narrative_tracker,
    research_robots_archaeology,
)


class TestNarrativeTrackerHelper:
    """Helper functions for narrative tracker."""

    @pytest.mark.asyncio
    async def test_hn_search_returns_posts(self) -> None:
        """HN search returns formatted post objects."""
        client = httpx.AsyncClient()
        with patch("loom.tools.infowar_tools._fetch_json") as mock_fetch:
            mock_fetch.return_value = {
                "hits": [
                    {
                        "title": "AI News",
                        "url": "https://example.com",
                        "author": "user1",
                        "created_at": "2026-04-28T10:00:00Z",
                        "points": 100,
                        "num_comments": 50,
                    }
                ]
            }
            results = await _hn_search(client, "AI", 72)
            assert len(results) == 1
            assert results[0]["platform"] == "hn"
            assert results[0]["title"] == "AI News"
            assert results[0]["author"] == "user1"

    @pytest.mark.asyncio
    async def test_hn_search_empty_response(self) -> None:
        """HN search handles missing hits gracefully."""
        client = httpx.AsyncClient()
        with patch("loom.tools.infowar_tools._fetch_json") as mock_fetch:
            mock_fetch.return_value = None
            results = await _hn_search(client, "AI", 72)
            assert results == []

    @pytest.mark.asyncio
    async def test_reddit_search_returns_posts(self) -> None:
        """Reddit search returns formatted post objects."""
        client = httpx.AsyncClient()
        with patch("loom.tools.infowar_tools._fetch_json") as mock_fetch:
            mock_fetch.return_value = {
                "data": [
                    {
                        "title": "Reddit Post",
                        "full_link": "https://reddit.com/r/test/comments/123",
                        "author": "user2",
                        "created_utc": 1704067200,
                        "score": 200,
                        "num_comments": 30,
                        "subreddit": "test",
                    }
                ]
            }
            results = await _reddit_search(client, "test", 72)
            assert len(results) == 1
            assert results[0]["platform"] == "reddit"
            assert results[0]["subreddit"] == "test"

    @pytest.mark.asyncio
    async def test_reddit_search_empty_response(self) -> None:
        """Reddit search handles missing data gracefully."""
        client = httpx.AsyncClient()
        with patch("loom.tools.infowar_tools._fetch_json") as mock_fetch:
            mock_fetch.return_value = None
            results = await _reddit_search(client, "test", 72)
            assert results == []

    @pytest.mark.asyncio
    async def test_arxiv_search_parses_xml(self) -> None:
        """arXiv search parses XML response."""
        client = httpx.AsyncClient()
        xml_response = """<?xml version="1.0"?>
<feed>
<entry>
<title>Test Paper</title>
<author><name>John Doe</name></author>
<published>2026-04-28T10:00:00Z</published>
<id>http://arxiv.org/abs/2604.12345v1</id>
</entry>
</feed>"""
        with patch("loom.tools.infowar_tools._fetch_text") as mock_fetch:
            mock_fetch.return_value = xml_response
            results = await _arxiv_search(client, "AI", 72)
            assert len(results) == 1
            assert results[0]["platform"] == "arxiv"
            assert "Test Paper" in results[0]["title"]

    @pytest.mark.asyncio
    async def test_arxiv_search_empty_response(self) -> None:
        """arXiv search handles empty response."""
        client = httpx.AsyncClient()
        with patch("loom.tools.infowar_tools._fetch_text") as mock_fetch:
            mock_fetch.return_value = ""
            results = await _arxiv_search(client, "AI", 72)
            assert results == []


class TestNarrativeTracker:
    """research_narrative_tracker function."""

    @pytest.mark.asyncio
    async def test_narrative_tracker_returns_expected_shape(self) -> None:
        """Narrative tracker returns expected result shape."""
        with patch("loom.tools.infowar_tools.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with patch("loom.tools.infowar_tools._hn_search") as mock_hn:
                with patch("loom.tools.infowar_tools._reddit_search") as mock_reddit:
                    with patch("loom.tools.infowar_tools._arxiv_search") as mock_arxiv:
                        mock_hn.return_value = [
                            {
                                "platform": "hn",
                                "title": "Test",
                                "timestamp": "2026-04-28T10:00:00Z",
                                "score": 100,
                            }
                        ]
                        mock_reddit.return_value = []
                        mock_arxiv.return_value = []

                        result = await research_narrative_tracker("AI safety", hours_back=72)

                        assert "topic" in result
                        assert result["topic"] == "AI safety"
                        assert "hours_back" in result
                        assert result["hours_back"] == 72
                        assert "total_posts" in result
                        assert "velocity_posts_per_hour" in result
                        assert "reach_platforms" in result
                        assert "timeline" in result
                        assert isinstance(result["timeline"], list)
                        assert "platforms" in result
                        assert isinstance(result["platforms"], dict)
                        assert "top_posts" in result

    @pytest.mark.asyncio
    async def test_narrative_tracker_no_results(self) -> None:
        """Narrative tracker handles no results gracefully."""
        with patch("loom.tools.infowar_tools.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with patch("loom.tools.infowar_tools._hn_search") as mock_hn:
                with patch("loom.tools.infowar_tools._reddit_search") as mock_reddit:
                    with patch("loom.tools.infowar_tools._arxiv_search") as mock_arxiv:
                        mock_hn.return_value = []
                        mock_reddit.return_value = []
                        mock_arxiv.return_value = []

                        result = await research_narrative_tracker("nonexistent", hours_back=72)

                        assert result["total_posts"] == 0
                        assert result["velocity_posts_per_hour"] == 0.0


class TestBotDetectorHelper:
    """Helper functions for bot detector."""

    @pytest.mark.asyncio
    async def test_analyze_posting_times_detects_clusters(self) -> None:
        """Posting time analysis detects clusters."""
        posts = [
            {
                "timestamp": "2026-04-28T10:00:00Z",
                "author": "user1",
                "title": "Post 1",
            },
            {
                "timestamp": "2026-04-28T10:02:00Z",
                "author": "user2",
                "title": "Post 2",
            },
            {
                "timestamp": "2026-04-28T10:03:00Z",
                "author": "user3",
                "title": "Post 3",
            },
        ]
        result = await _analyze_posting_times(posts)
        assert "suspicious_clusters" in result
        assert "coordination_score" in result
        assert result["coordination_score"] >= 0
        assert result["coordination_score"] <= 100


class TestBotDetector:
    """research_bot_detector function."""

    @pytest.mark.asyncio
    async def test_bot_detector_subreddit(self) -> None:
        """Bot detector analyzes subreddit."""
        with patch("loom.tools.infowar_tools.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with patch("loom.tools.infowar_tools._reddit_search") as mock_reddit:
                with patch("loom.tools.infowar_tools._hn_search") as mock_hn:
                    mock_reddit.return_value = [
                        {
                            "platform": "reddit",
                            "title": "Test",
                            "author": "user1",
                            "timestamp": "2026-04-28T10:00:00Z",
                        }
                    ]
                    mock_hn.return_value = []

                    result = await research_bot_detector(subreddit="programming")

                    assert "accounts_analyzed" in result
                    assert "posts_analyzed" in result
                    assert "suspicious_clusters" in result
                    assert "coordination_score" in result
                    assert result["subreddit"] == "programming"

    @pytest.mark.asyncio
    async def test_bot_detector_empty_results(self) -> None:
        """Bot detector handles no results."""
        with patch("loom.tools.infowar_tools.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with patch("loom.tools.infowar_tools._reddit_search") as mock_reddit:
                with patch("loom.tools.infowar_tools._hn_search") as mock_hn:
                    mock_reddit.return_value = []
                    mock_hn.return_value = []

                    result = await research_bot_detector(subreddit="")

                    assert result["accounts_analyzed"] == 0
                    assert result["posts_analyzed"] == 0
                    assert result["coordination_score"] == 0


class TestCensorshipDetectorHelper:
    """Helper functions for censorship detector."""

    @pytest.mark.asyncio
    async def test_dns_lookup_doh_google(self) -> None:
        """DNS lookup via Google DoH."""
        client = httpx.AsyncClient()
        with patch("loom.tools.infowar_tools._fetch_json") as mock_fetch:
            mock_fetch.return_value = {
                "Answer": [{"data": "1.2.3.4"}, {"data": "5.6.7.8"}]
            }
            result = await _dns_lookup_doh(
                client, "example.com", "https://dns.google/resolve"
            )
            assert result["provider"] == "google"
            assert "1.2.3.4" in result["answers"]
            assert result["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_dns_lookup_doh_failure(self) -> None:
        """DNS lookup handles failure."""
        client = httpx.AsyncClient()
        with patch("loom.tools.infowar_tools._fetch_json") as mock_fetch:
            mock_fetch.return_value = None
            result = await _dns_lookup_doh(
                client, "example.com", "https://dns.google/resolve"
            )
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_lumen_database_check(self) -> None:
        """Lumen database check returns notices."""
        client = httpx.AsyncClient()
        with patch("loom.tools.infowar_tools._fetch_json") as mock_fetch:
            mock_fetch.return_value = {
                "notices": [
                    {
                        "id": "123",
                        "title": "DMCA Notice",
                        "sender": "Acme Corp",
                        "date_sent": "2026-04-28",
                        "action_taken": "blocked",
                    }
                ]
            }
            result = await _lumen_database_check(client, "example.com")
            assert len(result) == 1
            assert result[0]["notice_id"] == "123"
            assert "DMCA" in result[0]["title"]


class TestCensorshipDetector:
    """research_censorship_detector function."""

    @pytest.mark.asyncio
    async def test_censorship_detector_returns_shape(self) -> None:
        """Censorship detector returns expected shape."""
        with patch("loom.tools.infowar_tools.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with patch("loom.tools.infowar_tools._dns_lookup_doh") as mock_dns:
                with patch(
                    "loom.tools.infowar_tools._lumen_database_check"
                ) as mock_lumen:
                    mock_dns.return_value = {
                        "provider": "google",
                        "status": "resolved",
                        "answers": ["1.2.3.4"],
                    }
                    mock_lumen.return_value = []

                    result = await research_censorship_detector("example.com")

                    assert "url" in result
                    assert "domain" in result
                    assert "dns_consistent" in result
                    assert isinstance(result["dns_consistent"], bool)
                    assert "dns_providers_checked" in result
                    assert "blocked_providers" in result
                    assert isinstance(result["blocked_providers"], list)
                    assert "takedown_notices_found" in result
                    assert "notices" in result


class TestDeletedSocialHelper:
    """Helper functions for deleted social recovery."""

    @pytest.mark.asyncio
    async def test_robots_txt_cdx(self) -> None:
        """Robots.txt CDX search returns versions."""
        client = httpx.AsyncClient()
        with patch("loom.tools.infowar_tools._fetch_json") as mock_fetch:
            mock_fetch.return_value = [
                ["timestamp", "original", "statuscode"],  # Header row
                ["20260101000000", "https://example.com/robots.txt", "200"],
                ["20260102000000", "https://example.com/robots.txt", "200"],
            ]
            result = await _robots_txt_cdx(client, "https://example.com", 10)
            assert len(result) == 2
            assert result[0]["timestamp"] == "20260101000000"

    @pytest.mark.asyncio
    async def test_robots_txt_content(self) -> None:
        """Robots.txt content fetch returns text."""
        client = httpx.AsyncClient()
        with patch("loom.tools.infowar_tools._fetch_text") as mock_fetch:
            mock_fetch.return_value = "User-agent: *\nDisallow: /admin"
            result = await _robots_txt_content(
                client, "https://web.archive.org/web/20260101000000/example.com/robots.txt"
            )
            assert "Disallow" in result


class TestDeletedSocial:
    """research_deleted_social function."""

    @pytest.mark.asyncio
    async def test_deleted_social_twitter_detection(self) -> None:
        """Deleted social detects Twitter platform."""
        with patch("loom.tools.infowar_tools.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with patch("loom.tools.infowar_tools._wayback_search_social") as mock_wayback:
                mock_wayback.return_value = []

                result = await research_deleted_social(
                    "https://twitter.com/user/status/123456"
                )

                assert result["platform"] == "twitter"
                assert "url" in result
                assert "snapshots_found" in result

    @pytest.mark.asyncio
    async def test_deleted_social_reddit_detection(self) -> None:
        """Deleted social detects Reddit platform."""
        with patch("loom.tools.infowar_tools.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with patch("loom.tools.infowar_tools._wayback_search_social") as mock_wayback:
                mock_wayback.return_value = []

                result = await research_deleted_social("https://reddit.com/r/test/comments/123")

                assert result["platform"] == "reddit"

    @pytest.mark.asyncio
    async def test_deleted_social_unknown_platform(self) -> None:
        """Deleted social handles unknown platform."""
        with patch("loom.tools.infowar_tools.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with patch("loom.tools.infowar_tools._wayback_search_social") as mock_wayback:
                mock_wayback.return_value = []

                result = await research_deleted_social("https://example.com/page")

                assert result["platform"] == "unknown"


class TestRobotsArchaeology:
    """research_robots_archaeology function."""

    @pytest.mark.asyncio
    async def test_robots_archaeology_returns_shape(self) -> None:
        """Robots archaeology returns expected shape."""
        with patch("loom.tools.infowar_tools.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with patch("loom.tools.infowar_tools._robots_txt_cdx") as mock_cdx:
                with patch("loom.tools.infowar_tools._robots_txt_content") as mock_content:
                    mock_cdx.return_value = [
                        {
                            "timestamp": "20260101000000",
                            "archive_url": "https://web.archive.org/web/20260101000000/example.com/robots.txt",
                        }
                    ]
                    mock_content.return_value = "User-agent: *\nDisallow: /admin"

                    result = await research_robots_archaeology("example.com", snapshots=10)

                    assert "domain" in result
                    assert "versions_found" in result
                    assert "changes" in result
                    assert isinstance(result["changes"], list)
                    assert "hidden_paths_timeline" in result

    @pytest.mark.asyncio
    async def test_robots_archaeology_no_versions(self) -> None:
        """Robots archaeology handles no versions found."""
        with patch("loom.tools.infowar_tools.httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client_class.return_value = mock_client

            with patch("loom.tools.infowar_tools._robots_txt_cdx") as mock_cdx:
                mock_cdx.return_value = []

                result = await research_robots_archaeology("example.com", snapshots=10)

                assert result["versions_found"] == 0
                assert result["changes"] == []


class TestDiffRobotsRules:
    """_diff_robots_rules function."""

    def test_diff_robots_rules_additions(self) -> None:
        """Diff detects added rules."""
        old = "User-agent: *\nDisallow: /old"
        new = "User-agent: *\nDisallow: /old\nDisallow: /new"
        added, removed = _diff_robots_rules(old, new)
        assert "Disallow: /new" in added
        assert len(removed) == 0

    def test_diff_robots_rules_removals(self) -> None:
        """Diff detects removed rules."""
        old = "User-agent: *\nDisallow: /admin\nDisallow: /private"
        new = "User-agent: *\nDisallow: /admin"
        added, removed = _diff_robots_rules(old, new)
        assert "Disallow: /private" in removed
        assert len(added) == 0

    def test_diff_robots_rules_changes(self) -> None:
        """Diff detects additions and removals."""
        old = "User-agent: *\nDisallow: /old"
        new = "User-agent: *\nDisallow: /new"
        added, removed = _diff_robots_rules(old, new)
        assert "Disallow: /new" in added
        assert "Disallow: /old" in removed

    def test_diff_robots_rules_empty(self) -> None:
        """Diff handles identical content."""
        content = "User-agent: *\nDisallow: /admin"
        added, removed = _diff_robots_rules(content, content)
        assert len(added) == 0
        assert len(removed) == 0
