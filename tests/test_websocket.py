"""Tests for WebSocket real-time update functionality.

Tests the WebSocketManager class and integration with the MCP server.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.websocket import WebSocketManager, get_ws_manager


@pytest.mark.asyncio
class TestWebSocketManager:
    """Test WebSocketManager singleton and core functionality."""

    def test_singleton_pattern(self) -> None:
        """Test that get_ws_manager returns the same instance."""
        mgr1 = get_ws_manager()
        mgr2 = get_ws_manager()
        assert mgr1 is mgr2

    @pytest.mark.asyncio
    async def test_broadcast_with_no_connections(self) -> None:
        """Test that broadcast succeeds when no clients are connected."""
        mgr = WebSocketManager()
        # Should not raise
        await mgr.broadcast("test.event", {"data": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_adds_timestamp(self) -> None:
        """Test that broadcast automatically adds timestamp if missing."""
        mgr = WebSocketManager()

        # Mock a WebSocket connection
        mock_ws = AsyncMock()
        mgr.connections.add(mock_ws)

        await mgr.broadcast("test.event", {"data": "test"})

        # Verify timestamp was added
        call_args = mock_ws.send_text.call_args
        assert call_args is not None
        message = json.loads(call_args[0][0])
        assert "timestamp" in message["data"]
        assert message["event"] == "test.event"

    @pytest.mark.asyncio
    async def test_broadcast_tool_started(self) -> None:
        """Test broadcasting tool started event."""
        mgr = WebSocketManager()
        mock_ws = AsyncMock()
        mgr.connections.add(mock_ws)

        await mgr.broadcast_tool_started("research_fetch", "job_123")

        call_args = mock_ws.send_text.call_args
        assert call_args is not None
        message = json.loads(call_args[0][0])
        assert message["event"] == "tool.started"
        assert message["data"]["tool_name"] == "research_fetch"
        assert message["data"]["job_id"] == "job_123"

    @pytest.mark.asyncio
    async def test_broadcast_tool_completed(self) -> None:
        """Test broadcasting tool completed event."""
        mgr = WebSocketManager()
        mock_ws = AsyncMock()
        mgr.connections.add(mock_ws)

        await mgr.broadcast_tool_completed("research_fetch", "job_123", 1500, True)

        call_args = mock_ws.send_text.call_args
        assert call_args is not None
        message = json.loads(call_args[0][0])
        assert message["event"] == "tool.completed"
        assert message["data"]["tool_name"] == "research_fetch"
        assert message["data"]["job_id"] == "job_123"
        assert message["data"]["duration_ms"] == 1500
        assert message["data"]["success"] is True

    @pytest.mark.asyncio
    async def test_broadcast_tool_failed(self) -> None:
        """Test broadcasting tool failed event."""
        mgr = WebSocketManager()
        mock_ws = AsyncMock()
        mgr.connections.add(mock_ws)

        await mgr.broadcast_tool_failed("research_fetch", "Connection timeout")

        call_args = mock_ws.send_text.call_args
        assert call_args is not None
        message = json.loads(call_args[0][0])
        assert message["event"] == "tool.failed"
        assert message["data"]["tool_name"] == "research_fetch"
        assert message["data"]["error"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_broadcast_health_changed(self) -> None:
        """Test broadcasting health status change."""
        mgr = WebSocketManager()
        mock_ws = AsyncMock()
        mgr.connections.add(mock_ws)

        details = {"memory_mb": 256, "tool_count": 303}
        await mgr.broadcast_health_changed("healthy", details)

        call_args = mock_ws.send_text.call_args
        assert call_args is not None
        message = json.loads(call_args[0][0])
        assert message["event"] == "health.changed"
        assert message["data"]["status"] == "healthy"
        assert message["data"]["details"] == details

    @pytest.mark.asyncio
    async def test_broadcast_alert(self) -> None:
        """Test broadcasting alert event."""
        mgr = WebSocketManager()
        mock_ws = AsyncMock()
        mgr.connections.add(mock_ws)

        await mgr.broadcast_alert("critical", "High memory usage detected")

        call_args = mock_ws.send_text.call_args
        assert call_args is not None
        message = json.loads(call_args[0][0])
        assert message["event"] == "alert"
        assert message["data"]["level"] == "critical"
        assert message["data"]["message"] == "High memory usage detected"

    @pytest.mark.asyncio
    async def test_broadcast_skips_failed_connections(self) -> None:
        """Test that broadcast removes and skips failed connections."""
        mgr = WebSocketManager()
        good_ws = AsyncMock()
        bad_ws = AsyncMock()
        bad_ws.send_text.side_effect = Exception("Connection lost")

        mgr.connections.add(good_ws)
        mgr.connections.add(bad_ws)

        await mgr.broadcast("test.event", {"data": "test"})

        # Good connection should still have the message
        assert good_ws.send_text.called
        # Bad connection should be removed
        assert bad_ws not in mgr.connections

    @pytest.mark.asyncio
    async def test_connect_without_auth(self) -> None:
        """Test connecting without authentication (when not required)."""
        import os

        # Temporarily disable auth
        old_auth = os.environ.get("LOOM_AUTH_REQUIRED")
        os.environ["LOOM_AUTH_REQUIRED"] = "false"

        try:
            mgr = WebSocketManager()
            mock_ws = AsyncMock()
            mock_ws.query_params = {}
            mock_ws.client = ("127.0.0.1", 12345)

            result = await mgr.connect(mock_ws)

            assert result is True
            assert mock_ws in mgr.connections
            mock_ws.accept.assert_called_once()
        finally:
            if old_auth:
                os.environ["LOOM_AUTH_REQUIRED"] = old_auth
            else:
                os.environ.pop("LOOM_AUTH_REQUIRED", None)

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """Test disconnecting a WebSocket."""
        mgr = WebSocketManager()
        mock_ws = AsyncMock()
        mgr.connections.add(mock_ws)

        assert len(mgr.connections) == 1
        await mgr.disconnect(mock_ws)
        assert len(mgr.connections) == 0

    @pytest.mark.asyncio
    async def test_extract_api_key_from_query(self) -> None:
        """Test extracting API key from query parameters."""
        mock_ws = MagicMock()
        mock_ws.query_params = {"X-API-Key": "test-key-123"}

        api_key = WebSocketManager._extract_api_key_from_query(mock_ws)
        assert api_key == "test-key-123"

    @pytest.mark.asyncio
    async def test_extract_api_key_from_query_lowercase(self) -> None:
        """Test extracting API key with lowercase parameter name."""
        mock_ws = MagicMock()
        mock_ws.query_params = {"x-api-key": "test-key-456"}

        api_key = WebSocketManager._extract_api_key_from_query(mock_ws)
        assert api_key == "test-key-456"

    @pytest.mark.asyncio
    async def test_extract_api_key_not_found(self) -> None:
        """Test when API key is not in query parameters."""
        mock_ws = MagicMock()
        mock_ws.query_params = {}

        api_key = WebSocketManager._extract_api_key_from_query(mock_ws)
        assert api_key is None

    def test_get_client_addr_with_client(self) -> None:
        """Test extracting client IP address."""
        mock_ws = MagicMock()
        mock_ws.client = ("192.168.1.100", 54321)

        addr = WebSocketManager._get_client_addr(mock_ws)
        assert addr == "192.168.1.100"

    def test_get_client_addr_without_client(self) -> None:
        """Test when client address is not available."""
        mock_ws = MagicMock()
        mock_ws.client = None

        addr = WebSocketManager._get_client_addr(mock_ws)
        assert addr == "unknown"
