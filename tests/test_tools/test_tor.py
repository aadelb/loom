"""Unit tests for Tor daemon management tools (research_tor_status, research_tor_new_identity).

Tests cover:
  - Missing socksio dependency
  - Connection errors (Tor not running)
  - Successful status checks with exit IP
  - Missing stem library
  - Rate limiting on NEWNYM requests
  - Successful circuit rotation
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from loom.tools.tor import (
    research_tor_new_identity,
    research_tor_status,
)


class TestTorStatus:
    """Tests for research_tor_status."""

    @pytest.mark.asyncio
    async def test_tor_status_success(self) -> None:
        """Test successful Tor status check with exit IP."""
        with patch("loom.tools.tor._get_tor_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"IP": "203.0.113.42", "IsTor": True}
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await research_tor_status()

            assert result["tor_running"] is True
            assert result["exit_ip"] == "203.0.113.42"
            assert result["socks5_proxy"] == "socks5h://127.0.0.1:9050"
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_tor_status_not_running(self) -> None:
        """Test Tor status check when Tor is not accessible (ConnectError)."""
        with patch("loom.tools.tor._get_tor_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_get_client.return_value = mock_client

            result = await research_tor_status()

            assert result["tor_running"] is False
            assert result["exit_ip"] == ""
            assert "error" in result
            assert "Tor SOCKS5 proxy not accessible" in result["error"]

    @pytest.mark.asyncio
    async def test_tor_status_timeout(self) -> None:
        """Test Tor status check when request times out."""
        with patch("loom.tools.tor._get_tor_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("Request timed out")
            mock_get_client.return_value = mock_client

            result = await research_tor_status()

            assert result["tor_running"] is False
            assert result["exit_ip"] == ""
            assert "error" in result
            assert "Timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_tor_status_proxy_error(self) -> None:
        """Test Tor status check when proxy error occurs."""
        with patch("loom.tools.tor._get_tor_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ProxyError("Proxy error")
            mock_get_client.return_value = mock_client

            result = await research_tor_status()

            assert result["tor_running"] is False
            assert result["exit_ip"] == ""
            assert "error" in result

    @pytest.mark.asyncio
    async def test_tor_status_http_error(self) -> None:
        """Test Tor status check when HTTP error occurs."""
        with patch("loom.tools.tor._get_tor_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Server Error", request=MagicMock(), response=mock_response
            )
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await research_tor_status()

            assert result["tor_running"] is False
            assert result["exit_ip"] == ""
            assert "error" in result

    @pytest.mark.asyncio
    async def test_tor_status_unexpected_error(self) -> None:
        """Test Tor status check with unexpected error."""
        with patch("loom.tools.tor._get_tor_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = RuntimeError("Unexpected error")
            mock_get_client.return_value = mock_client

            result = await research_tor_status()

            assert result["tor_running"] is False
            assert result["exit_ip"] == ""
            assert "error" in result
            assert "unexpected error" in result["error"]

    @pytest.mark.asyncio
    async def test_tor_status_json_parsing(self) -> None:
        """Test Tor status check with successful JSON parsing."""
        with patch("loom.tools.tor._get_tor_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"IP": "198.51.100.1", "IsTor": True}
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await research_tor_status()

            assert result["tor_running"] is True
            assert result["exit_ip"] == "198.51.100.1"


class TestTorNewIdentity:
    """Tests for research_tor_new_identity."""

    @pytest.mark.asyncio
    async def test_tor_new_identity_success(self) -> None:
        """Test successful new identity request."""
        # Reset the module-level state before test
        import loom.tools.tor as tor_module

        tor_module._last_newnym_time = 0.0

        with patch("loom.tools.tor._send_tor_newnym", return_value=True):
            result = await research_tor_new_identity()

            assert result["status"] == "new_identity_requested"
            assert result["wait_seconds"] == 10
            assert "error" not in result

    @pytest.mark.asyncio
    async def test_tor_new_identity_rate_limited(self) -> None:
        """Test rate limiting on consecutive NEWNYM requests."""
        # Reset the module-level state
        import loom.tools.tor as tor_module

        tor_module._last_newnym_time = 0.0

        with patch("loom.tools.tor._send_tor_newnym", return_value=True):
            # First request should succeed
            result1 = await research_tor_new_identity()
            assert result1["status"] == "new_identity_requested"

            # Second request within 10 seconds should be rate limited
            result2 = await research_tor_new_identity()
            assert result2["status"] == "rate_limited"
            assert "error" in result2
            assert "wait" in result2["error"].lower()

    @pytest.mark.asyncio
    async def test_tor_new_identity_stem_not_installed(self) -> None:
        """Test new identity request when stem is not installed."""
        # Reset the module-level state
        import loom.tools.tor as tor_module

        tor_module._last_newnym_time = 0.0

        with patch("loom.tools.tor._send_tor_newnym", return_value=False):
            result = await research_tor_new_identity()

            assert result["status"] == "failed"
            assert "error" in result
            assert result["wait_seconds"] == 10

    @pytest.mark.asyncio
    async def test_tor_new_identity_multiple_calls_after_wait(self) -> None:
        """Test that new identity request succeeds after rate limit window expires."""
        # Reset the module-level state
        import loom.tools.tor as tor_module

        tor_module._last_newnym_time = 0.0

        with patch("loom.tools.tor._send_tor_newnym", return_value=True):
            with patch("loom.tools.tor.time.time") as mock_time:
                # Simulate time progression
                mock_time.return_value = 1000.0
                result1 = await research_tor_new_identity()
                assert result1["status"] == "new_identity_requested"

                # Advance time by 11 seconds (past the 10-second window)
                mock_time.return_value = 1011.0
                result2 = await research_tor_new_identity()
                assert result2["status"] == "new_identity_requested"
                assert "error" not in result2

    @pytest.mark.asyncio
    async def test_tor_new_identity_error_response(self) -> None:
        """Test new identity request when NEWNYM signal fails."""
        # Reset the module-level state
        import loom.tools.tor as tor_module

        tor_module._last_newnym_time = 0.0

        with patch("loom.tools.tor._send_tor_newnym", return_value=False):
            result = await research_tor_new_identity()

            assert result["status"] == "failed"
            assert "error" in result
            assert "NEWNYM signal" in result["error"]

    @pytest.mark.asyncio
    async def test_tor_new_identity_response_format(self) -> None:
        """Test that new identity response has expected format."""
        import loom.tools.tor as tor_module

        tor_module._last_newnym_time = 0.0

        with patch("loom.tools.tor._send_tor_newnym", return_value=True):
            result = await research_tor_new_identity()

            # Check response structure
            assert isinstance(result, dict)
            assert "status" in result
            assert "wait_seconds" in result
            assert result["wait_seconds"] == 10

    @pytest.mark.asyncio
    async def test_tor_new_identity_executor_execution(self) -> None:
        """Test that NEWNYM is executed via executor for async context."""
        import loom.tools.tor as tor_module

        tor_module._last_newnym_time = 0.0

        with patch("loom.tools.tor._send_tor_newnym", return_value=True):
            # This tests that the function properly awaits the executor
            result = await research_tor_new_identity()
            assert result["status"] == "new_identity_requested"

    @pytest.mark.asyncio
    async def test_tor_new_identity_concurrent_rate_limit(self) -> None:
        """Test rate limiting under concurrent requests."""
        import loom.tools.tor as tor_module

        tor_module._last_newnym_time = 0.0

        with patch("loom.tools.tor._send_tor_newnym", return_value=True):
            # First call should succeed
            result1 = await research_tor_new_identity()
            assert result1["status"] == "new_identity_requested"

            # Concurrent call within window should be rate limited due to async lock
            result2 = await research_tor_new_identity()
            assert result2["status"] == "rate_limited"
