"""Tool call router for gateway - forwards requests to appropriate backend."""

from __future__ import annotations

import httpx
import json
import logging
from typing import Any

from gateway.config import BackendConfig, BackendService

logger = logging.getLogger("gateway.router")


class ToolRouter:
    """Routes tool calls to appropriate backend service."""

    def __init__(self, config: BackendConfig) -> None:
        """Initialize router with backend configuration.

        Args:
            config: BackendConfig instance with service definitions.
        """
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client.

        Returns:
            AsyncClient for making requests to backends.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=None)
        return self._client

    async def resolve_backend(self, tool_name: str) -> BackendService | None:
        """Resolve the backend service for a given tool.

        Args:
            tool_name: Tool name (e.g., 'research_fetch')

        Returns:
            BackendService to use, or None if no backend available.
        """
        service = self.config.get_service(tool_name)
        if service:
            logger.debug(
                "route_resolved tool=%s backend=%s",
                tool_name,
                service.name,
            )
            return service
        logger.warning("route_unresolved tool=%s no_backend_available", tool_name)
        return None

    async def call_tool(
        self,
        tool_name: str,
        params: dict[str, Any],
        auth_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Forward tool call to appropriate backend.

        Args:
            tool_name: Tool name to call
            params: Tool parameters
            auth_context: Optional authentication context from gateway

        Returns:
            Tool response from backend

        Raises:
            httpx.HTTPError: If backend request fails
            ValueError: If no backend found for tool
        """
        backend = await self.resolve_backend(tool_name)
        if not backend:
            raise ValueError(f"No backend available for tool: {tool_name}")

        client = await self._get_client()

        # Build MCP tool/call request for backend
        # The backend expects a POST to /mcp with method="tools/call"
        request_body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params,
            },
        }

        try:
            logger.debug(
                "route_request tool=%s backend=%s",
                tool_name,
                backend.name,
            )

            response = await client.post(
                f"{backend.url}/mcp",
                json=request_body,
                timeout=backend.timeout_seconds,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "loom-gateway/1.0",
                },
            )

            response.raise_for_status()
            result = response.json()

            logger.debug(
                "route_success tool=%s backend=%s",
                tool_name,
                backend.name,
            )

            return result

        except httpx.TimeoutException as e:
            logger.error(
                "route_timeout tool=%s backend=%s timeout=%d",
                tool_name,
                backend.name,
                backend.timeout_seconds,
            )
            raise

        except httpx.HTTPStatusError as e:
            logger.error(
                "route_http_error tool=%s backend=%s status=%d",
                tool_name,
                backend.name,
                e.response.status_code,
            )
            raise

        except Exception as e:
            logger.error(
                "route_error tool=%s backend=%s error=%s",
                tool_name,
                backend.name,
                str(e),
            )
            raise

    async def close(self) -> None:
        """Close async HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
