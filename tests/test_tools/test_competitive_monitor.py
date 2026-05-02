"""Tests for competitive_monitor tool."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from loom.tools.competitive_monitor import (
    DEFAULT_COMPETITORS,
    LOOM_CAPABILITIES,
    research_competitive_advantage,
    research_monitor_competitors,
)


class TestMonitorCompetitors:
    """Tests for research_monitor_competitors function."""

    @pytest.mark.asyncio
    async def test_monitor_competitors_default_list(self):
        """Test monitoring with default competitor list."""
        mock_repo_data = {
            "stargazers_count": 1500,
            "forks_count": 200,
            "open_issues_count": 45,
            "language": "Python",
            "description": "Test repo",
            "pushed_at": "2024-01-15T10:00:00Z",
            "watchers_count": 100,
            "html_url": "https://github.com/test/repo",
        }

        mock_release_data = {
            "tag_name": "v1.0.0",
            "published_at": "2024-01-10T10:00:00Z",
            "prerelease": False,
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            # Mock repo data response
            repo_response = AsyncMock()
            repo_response.status_code = 200
            repo_response.json.return_value = mock_repo_data

            # Mock release data response
            release_response = AsyncMock()
            release_response.status_code = 200
            release_response.json.return_value = mock_release_data

            # Alternate between repo and release responses
            mock_get.side_effect = [
                repo_response,
                release_response,
            ] * len(DEFAULT_COMPETITORS)

            result = await research_monitor_competitors()

        assert result["timestamp"]
        assert "competitors" in result
        assert "threat_level" in result
        assert "aggregate_stats" in result
        assert result["threat_level"] in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_monitor_competitors_custom_list(self):
        """Test monitoring with custom competitor list."""
        custom_competitors = ["user/repo1", "user/repo2"]

        with patch("httpx.AsyncClient.get") as mock_get:
            repo_response = AsyncMock()
            repo_response.status_code = 200
            repo_response.json.return_value = {
                "stargazers_count": 500,
                "forks_count": 50,
                "open_issues_count": 10,
                "language": "Python",
                "description": "Test",
                "pushed_at": "2024-01-15T10:00:00Z",
                "watchers_count": 30,
                "html_url": "https://github.com/user/repo1",
            }

            release_response = AsyncMock()
            release_response.status_code = 200
            release_response.json.return_value = {
                "tag_name": "v0.5.0",
                "published_at": "2024-01-10T10:00:00Z",
                "prerelease": False,
            }

            mock_get.side_effect = [
                repo_response,
                release_response,
            ] * len(custom_competitors)

            result = await research_monitor_competitors(competitors=custom_competitors)

        assert result["timestamp"]
        assert "competitors" in result
        assert len(result["competitors"]) <= len(custom_competitors)

    @pytest.mark.asyncio
    async def test_monitor_competitors_http_error_handling(self):
        """Test handling of HTTP errors from GitHub API."""
        with patch("httpx.AsyncClient.get") as mock_get:
            error_response = AsyncMock()
            error_response.status_code = 404
            mock_get.return_value = error_response

            result = await research_monitor_competitors(
                competitors=["nonexistent/repo"]
            )

        assert result["timestamp"]
        assert "competitors" in result
        # Should handle error gracefully
        if result["competitors"]:
            assert "error" in result["competitors"][0] or "stars" in result["competitors"][0]

    @pytest.mark.asyncio
    async def test_monitor_competitors_recent_activity_detection(self):
        """Test detection of recent activity."""
        # Repo with recent commit (1 day ago)
        mock_repo_data = {
            "stargazers_count": 1000,
            "forks_count": 100,
            "open_issues_count": 20,
            "language": "Python",
            "description": "Active repo",
            "pushed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "watchers_count": 50,
            "html_url": "https://github.com/active/repo",
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            repo_response = AsyncMock()
            repo_response.status_code = 200
            repo_response.json.return_value = mock_repo_data

            release_response = AsyncMock()
            release_response.status_code = 200
            release_response.json.return_value = {
                "tag_name": "v2.0.0",
                "published_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "prerelease": False,
            }

            mock_get.side_effect = [repo_response, release_response]

            result = await research_monitor_competitors(
                competitors=["active/repo"]
            )

        assert "latest_changes" in result
        # Recent activity should be detected
        if result["latest_changes"]:
            assert "repo" in result["latest_changes"][0]
            assert "last_commit_days_ago" in result["latest_changes"][0]

    @pytest.mark.asyncio
    async def test_monitor_competitors_threat_level_calculation(self):
        """Test threat level calculation based on metrics."""
        # High star count should trigger higher threat level
        mock_repo_data = {
            "stargazers_count": 15000,
            "forks_count": 2000,
            "open_issues_count": 150,
            "language": "Python",
            "description": "Popular repo",
            "pushed_at": "2024-01-15T10:00:00Z",
            "watchers_count": 500,
            "html_url": "https://github.com/popular/repo",
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            repo_response = AsyncMock()
            repo_response.status_code = 200
            repo_response.json.return_value = mock_repo_data

            release_response = AsyncMock()
            release_response.status_code = 200
            release_response.json.return_value = {
                "tag_name": "v3.0.0",
                "published_at": "2024-01-10T10:00:00Z",
                "prerelease": False,
            }

            mock_get.side_effect = [
                repo_response,
                release_response,
            ] * 4  # For all DEFAULT_COMPETITORS

            result = await research_monitor_competitors()

        assert result["threat_level"] in ["low", "medium", "high"]
        # With high stars, threat level should be elevated
        if result["aggregate_stats"]["total_stars"] > 10000:
            assert result["threat_level"] == "high"

    @pytest.mark.asyncio
    async def test_monitor_competitors_result_structure(self):
        """Test that result has expected structure."""
        with patch("httpx.AsyncClient.get") as mock_get:
            repo_response = AsyncMock()
            repo_response.status_code = 200
            repo_response.json.return_value = {
                "stargazers_count": 1000,
                "forks_count": 100,
                "open_issues_count": 20,
                "language": "Python",
                "description": "Test",
                "pushed_at": "2024-01-15T10:00:00Z",
                "watchers_count": 50,
                "html_url": "https://github.com/test/repo",
            }

            release_response = AsyncMock()
            release_response.status_code = 200
            release_response.json.return_value = {
                "tag_name": "v1.0.0",
                "published_at": "2024-01-10T10:00:00Z",
                "prerelease": False,
            }

            mock_get.side_effect = [
                repo_response,
                release_response,
            ] * 4

            result = await research_monitor_competitors()

        # Verify required fields
        assert "timestamp" in result
        assert "competitors" in result
        assert "latest_changes" in result
        assert "threat_level" in result
        assert "aggregate_stats" in result

        # Verify aggregate stats structure
        agg = result["aggregate_stats"]
        assert "total_repos" in agg
        assert "total_stars" in agg
        assert "avg_open_issues" in agg
        assert "recent_activity_count" in agg

    @pytest.mark.asyncio
    async def test_monitor_competitors_exception_handling(self):
        """Test handling of exceptions during monitoring."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.side_effect = Exception("Connection error")
            mock_client_class.return_value = mock_instance

            result = await research_monitor_competitors()

        assert result["timestamp"]
        assert "error" in result
        assert result["threat_level"] == "unknown"

    @pytest.mark.asyncio
    async def test_monitor_competitors_missing_release(self):
        """Test handling when repo has no releases."""
        with patch("httpx.AsyncClient.get") as mock_get:
            repo_response = AsyncMock()
            repo_response.status_code = 200
            repo_response.json.return_value = {
                "stargazers_count": 500,
                "forks_count": 50,
                "open_issues_count": 10,
                "language": "Python",
                "description": "No releases",
                "pushed_at": "2024-01-15T10:00:00Z",
                "watchers_count": 30,
                "html_url": "https://github.com/test/norepo",
            }

            # Release endpoint returns 404
            release_response = AsyncMock()
            release_response.status_code = 404

            mock_get.side_effect = [repo_response, release_response] * 4

            result = await research_monitor_competitors()

        assert result["timestamp"]
        assert "competitors" in result
        # Should still process repos without releases


class TestCompetitiveAdvantage:
    """Tests for research_competitive_advantage function."""

    def test_competitive_advantage_returns_structure(self):
        """Test that function returns expected structure."""
        result = research_competitive_advantage()

        assert "timestamp" in result
        assert "loom" in result
        assert "competitors" in result
        assert "gaps_to_fill" in result
        assert "overall_position" in result

    def test_competitive_advantage_loom_section(self):
        """Test Loom capabilities section."""
        result = research_competitive_advantage()

        loom = result["loom"]
        assert "tools_count" in loom
        assert "strategies_count" in loom
        assert "models_supported" in loom
        assert "advantages" in loom

        assert loom["tools_count"] == LOOM_CAPABILITIES["tools_count"]
        assert loom["strategies_count"] == LOOM_CAPABILITIES["strategies_count"]
        assert isinstance(loom["advantages"], list)
        assert len(loom["advantages"]) > 0

    def test_competitive_advantage_competitors_section(self):
        """Test competitors section."""
        result = research_competitive_advantage()

        competitors = result["competitors"]
        assert isinstance(competitors, dict)
        assert len(competitors) > 0

        # Each competitor should have advantages listed
        for name, advantages in competitors.items():
            assert isinstance(advantages, list)
            assert len(advantages) > 0

    def test_competitive_advantage_gaps_section(self):
        """Test gaps to fill section."""
        result = research_competitive_advantage()

        gaps = result["gaps_to_fill"]
        assert isinstance(gaps, list)
        # Should identify some gaps
        assert len(gaps) > 0

    def test_competitive_advantage_position_summary(self):
        """Test overall position summary."""
        result = research_competitive_advantage()

        position = result["overall_position"]
        assert isinstance(position, str)
        assert len(position) > 0
        # Should mention Loom's key differentiators
        assert any(keyword in position.lower() for keyword in ["strategy", "comprehensive", "loom"])

    def test_competitive_advantage_timestamp_format(self):
        """Test that timestamp is valid ISO format."""
        result = research_competitive_advantage()

        timestamp = result["timestamp"]
        # Should be parseable as ISO datetime
        try:
            datetime.fromisoformat(timestamp)
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {timestamp}")

    def test_competitive_advantage_consistent_data(self):
        """Test consistency between different calls."""
        result1 = research_competitive_advantage()
        result2 = research_competitive_advantage()

        # Tools/strategies count should be consistent
        assert result1["loom"]["tools_count"] == result2["loom"]["tools_count"]
        assert result1["loom"]["strategies_count"] == result2["loom"]["strategies_count"]

        # Competitors should be the same
        assert set(result1["competitors"].keys()) == set(result2["competitors"].keys())

    def test_competitive_advantage_mentions_all_competitors(self):
        """Test that all expected competitors are mentioned."""
        result = research_competitive_advantage()

        competitors = result["competitors"]
        # Should have entries for known competitors
        assert len(competitors) >= 3

    @pytest.mark.unit
    def test_competitive_advantage_error_handling(self):
        """Test that function handles errors gracefully."""
        # This test verifies the function doesn't raise exceptions
        try:
            result = research_competitive_advantage()
            assert result is not None
        except Exception as exc:
            pytest.fail(f"Function raised exception: {exc}")

    def test_competitive_advantage_loom_advantages_mention_scale(self):
        """Test that Loom advantages mention its scale advantages."""
        result = research_competitive_advantage()

        advantages = result["loom"]["advantages"]
        advantages_text = " ".join(advantages).lower()

        # Should mention key scale advantages
        assert "220" in advantages_text or "tool" in advantages_text
        assert "957" in advantages_text or "strateg" in advantages_text

    def test_competitive_advantage_includes_future_gaps(self):
        """Test that gaps include strategic future improvements."""
        result = research_competitive_advantage()

        gaps = result["gaps_to_fill"]
        gaps_text = " ".join(gaps).lower()

        # Should suggest improvements like UI, reporting, etc.
        assert any(keyword in gaps_text for keyword in ["dashboard", "ui", "report", "fine-tun"])


@pytest.mark.integration
class TestCompetitiveMonitorIntegration:
    """Integration tests with mock HTTP responses."""

    @pytest.mark.asyncio
    async def test_monitor_competitors_with_realistic_data(self):
        """Test with realistic GitHub API response data."""
        realistic_garak_data = {
            "stargazers_count": 8900,
            "forks_count": 1200,
            "open_issues_count": 124,
            "language": "Python",
            "description": "Red-teaming LLMs with Garak",
            "pushed_at": "2024-01-14T14:32:00Z",
            "watchers_count": 250,
            "html_url": "https://github.com/leondz/garak",
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            repo_response = AsyncMock()
            repo_response.status_code = 200
            repo_response.json.return_value = realistic_garak_data

            release_response = AsyncMock()
            release_response.status_code = 200
            release_response.json.return_value = {
                "tag_name": "v0.9.8",
                "published_at": "2024-01-08T10:00:00Z",
                "prerelease": False,
            }

            mock_get.side_effect = [repo_response, release_response] * 4

            result = await research_monitor_competitors(
                competitors=["leondz/garak"]
            )

        assert result["timestamp"]
        assert result["threat_level"] in ["low", "medium", "high"]
        assert len(result["competitors"]) > 0

        repo = result["competitors"][0]
        assert repo["stars"] == 8900
        assert repo["forks"] == 1200
        assert repo["language"] == "Python"
