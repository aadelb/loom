"""Bearer token authentication for Loom MCP server."""

from __future__ import annotations

import logging
import os

from mcp.server.auth.provider import AccessToken

logger = logging.getLogger("loom.auth")


class ApiKeyVerifier:
    """Verify bearer tokens against LOOM_API_KEY environment variable."""

    def __init__(self) -> None:
        """Initialize verifier with API key from environment."""
        self.api_key = os.environ.get("LOOM_API_KEY", "")

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify bearer token and return AccessToken if valid.

        Args:
            token: Bearer token to verify

        Returns:
            AccessToken if token matches LOOM_API_KEY, None otherwise.
            If no LOOM_API_KEY is set, allows anonymous access with full scopes.
        """
        # If no API key configured, allow anonymous access
        if not self.api_key:
            logger.debug("no_api_key_configured allow_anonymous")
            return AccessToken(
                token="anonymous",
                client_id="anonymous",
                scopes=["*"],
            )

        # Verify token matches configured API key
        if token == self.api_key:
            logger.info("auth_success client_id=api_key")
            return AccessToken(
                token=token,
                client_id="api_key",
                scopes=["*"],
            )

        # Token mismatch
        logger.warning(
            "auth_failed token=%s...",
            token[:8] if token else "empty",
        )
        return None
