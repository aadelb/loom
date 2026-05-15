"""Unit tests for social_graph tool — relationship graph analysis."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.intelligence.social_graph import (
    _extract_hn_topics,
    _fetch_github_data,
    _fetch_hackernews_data,
    _fetch_reddit_data,
    _fetch_semanticscholar_data,
    research_social_graph,
)


class TestExtractHnTopics:
    """Tests for HN topic extraction utility."""

    def test_extract_single_topic(self) -> None:
        """Extract single keyword from title."""
        topics = _extract_hn_topics("Building a Python WebServer", "https://example.com")
        assert "python" in topics

    def test_extract_multiple_topics(self) -> None:
        """Extract multiple keywords from title."""
        topics = _extract_hn_topics("Rust vs Python for DevOps Security", "https://example.com")
        assert any(t in topics for t in ["rust", "python", "devops", "security"])

    def test_extract_from_url(self) -> None:
        """Extract topics from URL domain."""
        topics = _extract_hn_topics("Latest Research", "https://arxiv.org/abs/1234.5678")
        assert "research" in topics

    def test_extract_github_topic(self) -> None:
        """Extract open source topic from GitHub URL."""
        topics = _extract_hn_topics("Cool Project", "https://github.com/user/repo")
        assert "open source" in topics

    def test_fallback_to_general(self) -> None:
        """Return general when no topics match."""
        topics = _extract_hn_topics("Xyz123 Abc456", "https://example.com/xyz")
        assert len(topics) > 0  # Should have fallback

    def test_no_duplicates(self) -> None:
        """Topics list has no duplicates."""
        topics = _extract_hn_topics("Python Python Python", "https://example.com")
        assert topics.count("python") <= 1


class TestFetchGithubData:
    """Tests for GitHub data fetching."""

    @pytest.mark.asyncio
    async def test_main_node_added(self) -> None:
        """Main user node is always added."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=[])

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        nodes, _edges = await _fetch_github_data(mock_client, "testuser")

        assert len(nodes) > 0
        assert nodes[0]["id"] == "github:testuser"
        assert nodes[0]["platform"] == "github"

    @pytest.mark.asyncio
    async def test_no_repos(self) -> None:
        """Handle case with no repos gracefully."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        nodes, edges = await _fetch_github_data(mock_client, "testuser")

        assert len(nodes) == 1  # Only main node
        assert len(edges) == 0

    @pytest.mark.asyncio
    async def test_single_repo_with_contributors(self) -> None:
        """Fetch single repo and build contributor edges."""
        repos_response = [{"name": "repo1"}]
        contributors_response = [
            {"login": "user1"},
            {"login": "user2"},
        ]

        mock_client = AsyncMock()

        async def mock_get(url, **kwargs):
            response = AsyncMock()
            if "repos" in url and "contributors" not in url:
                response.status_code = 200
                response.json = MagicMock(return_value=repos_response)
            elif "contributors" in url:
                response.status_code = 200
                response.json = MagicMock(return_value=contributors_response)
            else:
                response.status_code = 404
                response.json = MagicMock(return_value=None)
            return response

        mock_client.get = mock_get

        nodes, edges = await _fetch_github_data(mock_client, "testuser")

        assert any(n["id"] == "github:user1" for n in nodes)
        assert any(n["id"] == "github:user2" for n in nodes)
        assert len(edges) > 0

    @pytest.mark.asyncio
    async def test_co_contributor_edges(self) -> None:
        """Build edges between co-contributors on same repo."""
        repos_response = [{"name": "repo1"}]
        contributors_response = [
            {"login": "user1"},
            {"login": "user2"},
            {"login": "user3"},
        ]

        mock_client = AsyncMock()

        async def mock_get(url, **kwargs):
            response = AsyncMock()
            if "repos" in url and "contributors" not in url:
                response.status_code = 200
                response.json = MagicMock(return_value=repos_response)
            elif "contributors" in url:
                response.status_code = 200
                response.json = MagicMock(return_value=contributors_response)
            else:
                response.status_code = 404
                response.json = MagicMock(return_value=None)
            return response

        mock_client.get = mock_get

        _nodes, edges = await _fetch_github_data(mock_client, "testuser")

        # Should have edges between co-contributors
        co_contributor_edges = [
            e for e in edges if e[2] == "co-contributor"
        ]
        assert len(co_contributor_edges) > 0


class TestFetchRedditData:
    """Tests for Reddit data fetching."""

    @pytest.mark.asyncio
    async def test_main_node_added(self) -> None:
        """Main user node is added."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"data": {"children": []}})

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        nodes, _edges = await _fetch_reddit_data(mock_client, "testuser")

        assert len(nodes) > 0
        assert nodes[0]["id"] == "reddit:testuser"
        assert nodes[0]["platform"] == "reddit"

    @pytest.mark.asyncio
    async def test_no_comments(self) -> None:
        """Handle case with no comments gracefully."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        nodes, edges = await _fetch_reddit_data(mock_client, "testuser")

        assert len(nodes) == 1  # Only main node
        assert len(edges) == 0

    @pytest.mark.asyncio
    async def test_extract_subreddit_activity(self) -> None:
        """Extract subreddit activity from comments."""
        comments_response = {
            "data": {
                "children": [
                    {
                        "data": {
                            "subreddit": "python",
                            "body": "Great post!",
                        }
                    },
                    {
                        "data": {
                            "subreddit": "python",
                            "body": "Totally agree",
                        }
                    },
                    {
                        "data": {
                            "subreddit": "rust",
                            "body": "Nice example",
                        }
                    },
                ]
            }
        }

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=comments_response)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        nodes, _edges = await _fetch_reddit_data(mock_client, "testuser")

        # Should have subreddit nodes
        assert any(n["name"] == "r/python" for n in nodes)
        assert any(n["name"] == "r/rust" for n in nodes)

    @pytest.mark.asyncio
    async def test_extract_mentions(self) -> None:
        """Extract u/ mentions from comment text."""
        comments_response = {
            "data": {
                "children": [
                    {
                        "data": {
                            "subreddit": "python",
                            "body": "u/johndoe said something nice",
                        }
                    },
                ]
            }
        }

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=comments_response)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        nodes, _edges = await _fetch_reddit_data(mock_client, "testuser")

        # Should have mentioned user node
        assert any(n["id"] == "reddit:johndoe" for n in nodes)


class TestFetchHackernewsData:
    """Tests for HackerNews data fetching."""

    @pytest.mark.asyncio
    async def test_main_node_added(self) -> None:
        """Main user node is added."""
        user_response = {"karma": 1000, "submitted": []}

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=user_response)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        nodes, _edges = await _fetch_hackernews_data(mock_client, "testuser")

        assert len(nodes) > 0
        assert nodes[0]["id"] == "hn:testuser"
        assert nodes[0]["platform"] == "hackernews"

    @pytest.mark.asyncio
    async def test_no_user_data(self) -> None:
        """Handle case with no user data gracefully."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=None)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        nodes, edges = await _fetch_hackernews_data(mock_client, "testuser")

        assert len(nodes) == 1  # Only main node
        assert len(edges) == 0

    @pytest.mark.asyncio
    async def test_extract_submission_topics(self) -> None:
        """Extract topics from user submissions."""
        user_response = {"karma": 1000, "submitted": [12345]}
        story_response = {
            "title": "Building Python Machine Learning Models",
            "url": "https://example.com/article",
        }

        mock_client = AsyncMock()

        async def mock_get(url, **kwargs):
            response = AsyncMock()
            if "user" in url:
                response.status_code = 200
                response.json = MagicMock(return_value=user_response)
            elif "item" in url:
                response.status_code = 200
                response.json = MagicMock(return_value=story_response)
            else:
                response.status_code = 404
                response.json = MagicMock(return_value=None)
            return response

        mock_client.get = mock_get

        nodes, _edges = await _fetch_hackernews_data(mock_client, "testuser")

        # Should have topic nodes
        topic_nodes = [n for n in nodes if "topic" in n["id"]]
        assert len(topic_nodes) > 0


class TestFetchSemanticScholarData:
    """Tests for Semantic Scholar data fetching."""

    @pytest.mark.asyncio
    async def test_no_author_found(self) -> None:
        """Handle case with no author found gracefully."""
        search_response: dict[str, list[dict[str, str]]] = {"data": []}

        with patch("loom.tools.social_graph.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value=search_response)
            mock_client.get = AsyncMock(return_value=mock_response)

            mock_client_class.return_value = mock_client

            nodes, edges = await _fetch_semanticscholar_data("NonexistentAuthor")

            assert len(nodes) == 0
            assert len(edges) == 0

    @pytest.mark.asyncio
    async def test_author_found_no_papers(self) -> None:
        """Author found but no papers."""
        search_response = {
            "data": [
                {
                    "authorId": "author123",
                    "name": "John Doe",
                }
            ]
        }
        papers_response: dict[str, list[dict[str, Any]]] = {"data": []}

        with patch("loom.tools.social_graph.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            async def mock_get(url, **kwargs):
                response = AsyncMock()
                if "search" in url:
                    response.status_code = 200
                    response.json = MagicMock(return_value=search_response)
                elif "papers" in url:
                    response.status_code = 200
                    response.json = MagicMock(return_value=papers_response)
                else:
                    response.status_code = 404
                    response.json = MagicMock(return_value=None)
                return response

            mock_client.get = mock_get
            mock_client_class.return_value = mock_client

            nodes, edges = await _fetch_semanticscholar_data("John Doe")

            assert len(nodes) == 1  # Only main author node
            assert len(edges) == 0


@pytest.mark.asyncio
class TestResearchSocialGraph:
    """Tests for main research_social_graph function."""

    async def test_invalid_username(self) -> None:
        """Reject empty or invalid username."""
        result = await research_social_graph("")
        assert "error" in result
        assert result["nodes"] == []
        assert result["edges"] == []

    async def test_username_too_long(self) -> None:
        """Reject username exceeding length limit."""
        long_username = "a" * 300
        result = await research_social_graph(long_username)
        assert "error" in result
        assert "exceeds 255" in result["error"]

    async def test_none_username(self) -> None:
        """Reject None username."""
        result = await research_social_graph(None)
        assert "error" in result

    async def test_valid_username_github_only(self) -> None:
        """Analyze GitHub platform only."""
        with patch("loom.tools.intelligence.social_graph._fetch_github_data") as mock_github:
            mock_github.return_value = (
                [{"id": "github:testuser", "platform": "github", "name": "testuser"}],
                [],
            )

            result = await research_social_graph("testuser", platforms=["github"])

            assert result["username"] == "testuser"
            assert "github" in result["platforms_analyzed"]
            assert len(result["nodes"]) > 0

    async def test_no_valid_platforms(self) -> None:
        """Reject when no valid platforms specified."""
        result = await research_social_graph("testuser", platforms=["invalid_platform"])
        assert "error" in result
        assert "no valid platforms" in result["error"]

    async def test_default_platforms(self) -> None:
        """Use default platforms when none specified."""
        with patch("loom.tools.intelligence.social_graph._fetch_github_data") as mock_github, \
             patch("loom.tools.intelligence.social_graph._fetch_reddit_data") as mock_reddit, \
             patch("loom.tools.intelligence.social_graph._fetch_hackernews_data") as mock_hn:

            mock_github.return_value = (
                [{"id": "github:testuser", "platform": "github", "name": "testuser"}],
                [],
            )
            mock_reddit.return_value = ([], [])
            mock_hn.return_value = ([], [])

            result = await research_social_graph("testuser")

            # Should attempt to analyze default platforms
            assert isinstance(result, dict)
            assert "username" in result
            assert "nodes" in result
            assert "edges" in result

    async def test_deduplication(self) -> None:
        """Deduplicate nodes and edges."""
        with patch("loom.tools.intelligence.social_graph._fetch_github_data") as mock_github, \
             patch("loom.tools.intelligence.social_graph._fetch_reddit_data") as mock_reddit:

            # Both platforms return same node/edge (simulating duplicate)
            shared_node = {"id": "user:john", "platform": "shared", "name": "john"}
            shared_edge = ("user:john", "user:jane", "knows", 1)

            mock_github.return_value = (
                [{"id": "github:testuser", "platform": "github", "name": "testuser"}, shared_node],
                [shared_edge],
            )
            mock_reddit.return_value = (
                [shared_node],
                [shared_edge],
            )

            result = await research_social_graph("testuser", platforms=["github", "reddit"])

            # Count occurrences of the shared node
            shared_count = sum(1 for n in result["nodes"] if n["id"] == "user:john")
            assert shared_count == 1, "Nodes should be deduplicated"

    async def test_response_structure(self) -> None:
        """Response has required fields."""
        with patch("loom.tools.intelligence.social_graph._fetch_github_data") as mock_github:
            mock_github.return_value = (
                [{"id": "github:testuser", "platform": "github", "name": "testuser"}],
                [],
            )

            result = await research_social_graph("testuser", platforms=["github"])

            assert "username" in result
            assert "nodes" in result
            assert "edges" in result
            assert "platforms_analyzed" in result
            assert "total_connections" in result
            assert isinstance(result["nodes"], list)
            assert isinstance(result["edges"], list)
            assert isinstance(result["platforms_analyzed"], list)
            assert isinstance(result["total_connections"], int)

    async def test_connection_count(self) -> None:
        """total_connections matches edges count."""
        with patch("loom.tools.intelligence.social_graph._fetch_github_data") as mock_github:
            edge1 = ("github:user1", "github:user2", "collaborated", 1)
            edge2 = ("github:user2", "github:user3", "collaborated", 1)

            mock_github.return_value = (
                [
                    {"id": "github:testuser", "platform": "github", "name": "testuser"},
                    {"id": "github:user1", "platform": "github", "name": "user1"},
                    {"id": "github:user2", "platform": "github", "name": "user2"},
                    {"id": "github:user3", "platform": "github", "name": "user3"},
                ],
                [edge1, edge2],
            )

            result = await research_social_graph("testuser", platforms=["github"])

            assert result["total_connections"] == len(result["edges"])
