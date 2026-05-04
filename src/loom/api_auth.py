"""API key authentication middleware for Loom MCP server.

Provides Starlette ASGI middleware that enforces X-API-Key header validation
for securing the MCP API. Exempt endpoints include /health, /versions, /metrics
and their v1-prefixed variants.

Configuration:
- LOOM_AUTH_REQUIRED (bool, default: False) — Enable authentication enforcement
- LOOM_API_KEYS (str, comma-separated) — Valid API keys
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

log = logging.getLogger("loom.api_auth")

# Paths that bypass authentication (case-insensitive)
EXEMPT_PATHS = {
    "/health",
    "/v1/health",
    "/versions",
    "/v1/versions",
    "/metrics",
    "/v1/metrics",
    "/mcp",  # MCP protocol endpoint handled separately
}


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
    """Check if authentication is enabled via LOOM_AUTH_REQUIRED.

    Returns:
        True if LOOM_AUTH_REQUIRED=true (case-insensitive), False otherwise
    """
    return os.environ.get("LOOM_AUTH_REQUIRED", "false").lower() == "true"


def _is_exempt_path(path: str) -> bool:
    """Check if path is exempt from authentication.

    Args:
        path: Request path (e.g., "/health", "/v1/health")

    Returns:
        True if path should bypass authentication
    """
    return path.lower() in EXEMPT_PATHS


class ApiKeyAuthMiddleware:
    """ASGI middleware for X-API-Key based authentication.

    Validates incoming requests against a whitelist of API keys.
    Exempt paths (health checks, metrics) bypass validation.

    Attributes:
        app: Wrapped ASGI application
        auth_required: Whether authentication is enabled
        api_keys: Set of valid API keys
    """

    def __init__(self, app: Any) -> None:
        """Initialize middleware.

        Args:
            app: The ASGI application to wrap
        """
        self.app = app
        self.auth_required = _is_auth_required()
        self.api_keys = _get_api_keys()

        if self.auth_required and not self.api_keys:
            log.warning(
                "auth_middleware_misconfigured "
                "LOOM_AUTH_REQUIRED=true but LOOM_API_KEYS is empty; "
                "all requests will be rejected"
            )

    async def __call__(self, scope: dict, receive: Any, send: Any) -> Any:
        """Process the request with API key validation.

        Args:
            scope: ASGI scope dict
            receive: ASGI receive callable
            send: ASGI send callable
        """
        # Only intercept HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract path from scope
        path = scope.get("path", "/")

        # Skip authentication for exempt paths
        if _is_exempt_path(path):
            await self.app(scope, receive, send)
            return

        # If auth not required, allow all requests
        if not self.auth_required:
            await self.app(scope, receive, send)
            return

        # Extract X-API-Key header from request
        api_key = self._extract_api_key(scope)

        # Validate API key
        if not api_key or api_key not in self.api_keys:
            log.warning(
                "auth_middleware_rejected "
                "path=%s method=%s remote_addr=%s",
                path,
                scope.get("method", "UNKNOWN"),
                self._get_remote_addr(scope),
            )
            await self._send_unauthorized(send)
            return

        log.debug(
            "auth_middleware_accepted "
            "path=%s method=%s",
            path,
            scope.get("method", "UNKNOWN"),
        )

        # Request authorized, pass to app
        await self.app(scope, receive, send)

    @staticmethod
    def _extract_api_key(scope: dict) -> str | None:
        """Extract X-API-Key header from ASGI scope.

        Args:
            scope: ASGI scope dict

        Returns:
            API key value or None if header not found
        """
        headers = scope.get("headers", [])
        for header_name, header_value in headers:
            # Headers are bytes in ASGI
            if header_name.lower() == b"x-api-key":
                return header_value.decode("utf-8", errors="ignore")
        return None

    @staticmethod
    def _get_remote_addr(scope: dict) -> str:
        """Extract client IP address from ASGI scope.

        Args:
            scope: ASGI scope dict

        Returns:
            Client IP address or "unknown"
        """
        client = scope.get("client")
        if client:
            return client[0]
        return "unknown"

    @staticmethod
    async def _send_unauthorized(send: Any) -> None:
        """Send 401 Unauthorized JSON response.

        Args:
            send: ASGI send callable
        """
        body = json.dumps({
            "error": "unauthorized",
            "message": "Missing or invalid X-API-Key header",
            "status": 401,
        }).encode("utf-8")

        await send({
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("utf-8")),
            ],
        })

        await send({
            "type": "http.response.body",
            "body": body,
            "more_body": False,
        })
