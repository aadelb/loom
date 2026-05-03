"""Tests for research_dead_content tool."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from loom.tools.dead_content import research_dead_content
from loom.validators import UrlSafetyError



pytestmark = pytest.mark.asyncio
class TestResearchDeadContent:
    """Unit tests for research_dead_content function."""

    async def test_invalid_url_returns_error(self) -> None:
        """Test that invalid URLs are rejected."""
        result = await research_dead_content(url="not-a-url")
        assert "error" in result
        assert result["is_deleted"] is False
        assert result["found_in"] == []

    async def test_private_ip_url_returns_error(self) -> None:
        """Test that private IP URLs are rejected for SSRF safety."""
        result = await research_dead_content(url="http://127.0.0.1:8080")
        assert "error" in result
        assert result["is_deleted"] is False

    async def test_loopback_url_returns_error(self) -> None:
        """Test that loopback URLs are rejected."""
        result = await research_dead_content(url="http://localhost/test")
        assert "error" in result
        assert result["is_deleted"] is False

    @patch("loom.tools.dead_content.httpx.AsyncClient")
    async def test_wayback_machine_found(self, mock_client_class: Mock) -> None:
        """Test successful Wayback Machine snapshot detection."""
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock Wayback Machine response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            ["urlkey", "timestamp", "original", "statuscode", "mimetype"],
            ["com,example)/", "20200101000000", "http://example.com/", "200", "text/html"],
            ["com,example)/", "20200102000000", "http://example.com/", "200", "text/html"],
        ]
        mock_client.get.return_value = mock_resp

        # Call with mocked responses
        mock_client.head.return_value.status_code = 404  # Other sources fail

        result = await research_dead_content(url="https://example.com", include_snapshots=True)

        assert result["is_deleted"] is True
        assert "wayback_machine" in result["found_in"]
        assert len(result["snapshots"]) > 0
        assert result["snapshots"][0]["source"] == "wayback_machine"

    @patch("loom.tools.dead_content.httpx.AsyncClient")
    async def test_archive_today_found(self, mock_client_class: Mock) -> None:
        """Test successful Archive.today snapshot detection."""
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # First source (Wayback) fails
        mock_resp_fail = MagicMock()
        mock_resp_fail.status_code = 404
        mock_resp_fail.json.return_value = []

        # Archive.today succeeds
        mock_resp_archive = MagicMock()
        mock_resp_archive.status_code = 200
        mock_resp_archive.url = "https://archive.ph/12345"

        # Setup sequential responses
        mock_client.get.return_value = mock_resp_fail
        mock_client.head.side_effect = [mock_resp_archive, mock_resp_fail, mock_resp_fail]

        result = await research_dead_content(url="https://example.com", include_snapshots=True)

        assert "archive_today" in result["found_in"]

    @patch("loom.tools.dead_content.httpx.AsyncClient")
    async def test_no_archives_found(self, mock_client_class: Mock) -> None:
        """Test when no archives are found."""
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # All sources return 404 or empty
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = []

        mock_client.get.return_value = mock_resp
        mock_client.head.return_value = mock_resp

        result = await research_dead_content(url="https://example.com")

        assert result["is_deleted"] is False
        assert result["found_in"] == []
        assert result["snapshots"] == []

    async def test_max_sources_clamping(self) -> None:
        """Test that max_sources is clamped to valid range."""
        with patch("loom.tools.dead_content.httpx.AsyncClient"):
            # Should clamp 100 to 6 (max available sources)
            result = await research_dead_content(url="https://example.com", max_sources=100)
            # total_sources_checked should be at most 6
            assert result["total_sources_checked"] <= 6

    async def test_max_sources_minimum(self) -> None:
        """Test that max_sources minimum is 1."""
        with patch("loom.tools.dead_content.httpx.AsyncClient"):
            result = await research_dead_content(url="https://example.com", max_sources=0)
            # Should at least check 1 source
            assert result["total_sources_checked"] >= 1

    @patch("loom.tools.dead_content.httpx.AsyncClient")
    async def test_snapshots_excluded_when_flag_false(self, mock_client_class: Mock) -> None:
        """Test that snapshots are not included when include_snapshots=False."""
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock Wayback Machine response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            ["urlkey", "timestamp", "original", "statuscode", "mimetype"],
            ["com,example)/", "20200101000000", "http://example.com/", "200", "text/html"],
        ]
        mock_client.get.return_value = mock_resp
        mock_client.head.return_value.status_code = 404

        result = await research_dead_content(
            url="https://example.com", include_snapshots=False
        )

        assert result["is_deleted"] is True
        assert "wayback_machine" in result["found_in"]
        assert len(result["snapshots"]) == 0

    async def test_response_structure(self) -> None:
        """Test that response has all required fields."""
        with patch("loom.tools.dead_content.httpx.AsyncClient"):
            result = await research_dead_content(url="https://example.com")

            # Verify required fields
            assert "url" in result
            assert "found_in" in result
            assert "snapshots" in result
            assert "is_deleted" in result
            assert "total_sources_checked" in result
            assert "checked_at" in result

            # Verify types
            assert isinstance(result["url"], str)
            assert isinstance(result["found_in"], list)
            assert isinstance(result["snapshots"], list)
            assert isinstance(result["is_deleted"], bool)
            assert isinstance(result["total_sources_checked"], int)
            assert isinstance(result["checked_at"], str)

    @patch("loom.tools.dead_content.httpx.AsyncClient")
    async def test_handles_malformed_json(self, mock_client_class: Mock) -> None:
        """Test graceful handling of malformed JSON responses."""
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock response that raises JSON decode error
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = json.JSONDecodeError("bad json", "", 0)

        mock_client.get.return_value = mock_resp
        mock_client.head.return_value.status_code = 404

        # Should not raise, should handle gracefully
        result = await research_dead_content(url="https://example.com")

        assert result["is_deleted"] is False
        assert result["found_in"] == []

    @patch("loom.tools.dead_content.httpx.AsyncClient")
    async def test_handles_network_timeout(self, mock_client_class: Mock) -> None:
        """Test graceful handling of network timeouts."""
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock timeout exception
        import httpx

        mock_client.get.side_effect = httpx.TimeoutException("timeout")
        mock_client.head.side_effect = httpx.TimeoutException("timeout")

        # Should not raise, should handle gracefully
        result = await research_dead_content(url="https://example.com")

        assert result["is_deleted"] is False
        assert result["found_in"] == []
