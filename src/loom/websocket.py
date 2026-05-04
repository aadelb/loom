"""Real-time WebSocket endpoint for Loom MCP server.

Provides a WebSocket server that broadcasts tool execution events and health
status changes to all connected clients. Includes authentication via X-API-Key
in query parameters or first message.

Events:
- tool.started: {tool_name, job_id, timestamp}
- tool.completed: {tool_name, job_id, duration_ms, success}
- tool.failed: {tool_name, error}
- health.changed: {status, details}
- alert: {level, message}

Usage:
    ws = WebsocketManager()
    await ws.broadcast("tool.started", {"tool_name": "research_fetch", ...})
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect

log = logging.getLogger("loom.websocket")


def _get_api_keys() -> set[str]:
    """Load valid API keys from LOOM_API_KEYS environment variable.

    Returns:
        Set of valid API keys (empty if not configured)
    """
    keys_str = os.environ.get("LOOM_API_KEYS", "")
    if not keys_str:
        return set()
    return {key.strip() for key in keys_str.split(",") if key.strip()}


def _is_auth_required() -> bool:
    """Check if WebSocket authentication is enabled.

    Returns:
        True if LOOM_AUTH_REQUIRED=true (case-insensitive), False otherwise
    """
    return os.environ.get("LOOM_AUTH_REQUIRED", "false").lower() == "true"


class WebSocketManager:
    """Manages WebSocket connections and broadcasts events to all clients.

    Maintains a set of active connections and provides methods to broadcast
    events (tool execution, health status, alerts) to all connected clients.
    Handles authentication via X-API-Key.

    Attributes:
        connections: Set of active WebSocket connections
        auth_required: Whether authentication is enabled
        api_keys: Set of valid API keys
    """

    def __init__(self) -> None:
        """Initialize WebSocket manager."""
        self.connections: set[WebSocket] = set()
        self.auth_required = _is_auth_required()
        self.api_keys = _get_api_keys()

        if self.auth_required and not self.api_keys:
            log.warning(
                "websocket_auth_misconfigured "
                "LOOM_AUTH_REQUIRED=true but LOOM_API_KEYS is empty; "
                "all connections will be rejected"
            )

    async def connect(self, ws: WebSocket) -> bool:
        """Accept and authenticate a WebSocket connection.

        Performs authentication check if enabled. API key can be provided via:
        1. X-API-Key query parameter: ws://localhost:8787/ws?X-API-Key=...
        2. First message: {"api_key": "..."}

        Args:
            ws: The WebSocket connection

        Returns:
            True if connection accepted, False if rejected

        Raises:
            WebSocketDisconnect: If connection is closed during handshake
        """
        # Check authentication if enabled
        if self.auth_required:
            api_key = self._extract_api_key_from_query(ws)

            # If not in query params, check first message
            if not api_key:
                api_key = await self._extract_api_key_from_message(ws)

            # Validate API key
            if not api_key or api_key not in self.api_keys:
                log.warning(
                    "websocket_auth_rejected client=%s",
                    self._get_client_addr(ws),
                )
                await ws.close(code=1008, reason="Unauthorized")
                return False

        await ws.accept()
        self.connections.add(ws)
        log.info(
            "websocket_connected "
            "client=%s total_connections=%d",
            self._get_client_addr(ws),
            len(self.connections),
        )
        return True

    async def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket connection from the manager.

        Args:
            ws: The WebSocket connection to remove
        """
        self.connections.discard(ws)
        log.info(
            "websocket_disconnected "
            "client=%s total_connections=%d",
            self._get_client_addr(ws),
            len(self.connections),
        )

    async def broadcast(self, event: str, data: dict[str, Any]) -> None:
        """Broadcast an event to all connected clients.

        Sends JSON-serialized event to all active connections. Automatically
        adds timestamp if not present. Silently skips failed sends.

        Args:
            event: Event type (e.g., "tool.started", "health.changed")
            data: Event data dictionary
        """
        # Ensure timestamp is present
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(UTC).isoformat()

        payload = {
            "event": event,
            "data": data,
        }

        message = json.dumps(payload)
        log.debug("websocket_broadcast event=%s clients=%d", event, len(self.connections))

        # Send to all connected clients
        disconnected = []
        for ws in list(self.connections):
            try:
                await ws.send_text(message)
            except Exception as e:
                log.debug(
                    "websocket_send_failed "
                    "event=%s client=%s error=%s",
                    event,
                    self._get_client_addr(ws),
                    str(e),
                )
                disconnected.append(ws)

        # Remove failed connections
        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast_tool_started(
        self,
        tool_name: str,
        job_id: str,
    ) -> None:
        """Broadcast a tool.started event.

        Args:
            tool_name: Name of the tool
            job_id: Unique job identifier
        """
        await self.broadcast(
            "tool.started",
            {
                "tool_name": tool_name,
                "job_id": job_id,
            },
        )

    async def broadcast_tool_completed(
        self,
        tool_name: str,
        job_id: str,
        duration_ms: int,
        success: bool,
    ) -> None:
        """Broadcast a tool.completed event.

        Args:
            tool_name: Name of the tool
            job_id: Unique job identifier
            duration_ms: Execution duration in milliseconds
            success: Whether execution succeeded
        """
        await self.broadcast(
            "tool.completed",
            {
                "tool_name": tool_name,
                "job_id": job_id,
                "duration_ms": duration_ms,
                "success": success,
            },
        )

    async def broadcast_tool_failed(
        self,
        tool_name: str,
        error: str,
    ) -> None:
        """Broadcast a tool.failed event.

        Args:
            tool_name: Name of the tool
            error: Error message
        """
        await self.broadcast(
            "tool.failed",
            {
                "tool_name": tool_name,
                "error": error,
            },
        )

    async def broadcast_health_changed(
        self,
        status: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Broadcast a health.changed event.

        Args:
            status: Health status (healthy, degraded, unhealthy)
            details: Optional details dictionary
        """
        await self.broadcast(
            "health.changed",
            {
                "status": status,
                "details": details or {},
            },
        )

    async def broadcast_alert(
        self,
        level: str,
        message: str,
    ) -> None:
        """Broadcast an alert event.

        Args:
            level: Alert level (info, warning, error, critical)
            message: Alert message
        """
        await self.broadcast(
            "alert",
            {
                "level": level,
                "message": message,
            },
        )

    @staticmethod
    def _extract_api_key_from_query(ws: WebSocket) -> str | None:
        """Extract X-API-Key from query parameters.

        Args:
            ws: The WebSocket connection

        Returns:
            API key value or None if not found
        """
        query_params = ws.query_params
        return query_params.get("X-API-Key") or query_params.get("x-api-key")

    @staticmethod
    async def _extract_api_key_from_message(ws: WebSocket) -> str | None:
        """Extract API key from first WebSocket message.

        Expects JSON message with "api_key" field.

        Args:
            ws: The WebSocket connection

        Returns:
            API key value or None if not found or message is invalid
        """
        try:
            message = await ws.receive_text()
            data = json.loads(message)
            return data.get("api_key")
        except (json.JSONDecodeError, WebSocketDisconnect, Exception) as e:
            log.debug("websocket_auth_message_parse_failed error=%s", str(e))
            return None

    @staticmethod
    def _get_client_addr(ws: WebSocket) -> str:
        """Extract client IP address from WebSocket scope.

        Args:
            ws: The WebSocket connection

        Returns:
            Client IP address or "unknown"
        """
        try:
            client = ws.client
            if client:
                return client[0]
        except Exception:
            pass
        return "unknown"


# Global WebSocket manager instance
_ws_manager: WebSocketManager | None = None


def get_ws_manager() -> WebSocketManager:
    """Get or create the global WebSocket manager instance.

    Returns:
        The WebSocket manager singleton
    """
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
