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
        self.allow_anonymous = os.environ.get("LOOM_ALLOW_ANONYMOUS", "").lower() == "true"

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify bearer token and return AccessToken if valid.

        Args:
            token: Bearer token to verify

        Returns:
            AccessToken if token is valid, None otherwise.
            If no LOOM_API_KEY is set and LOOM_ALLOW_ANONYMOUS != true,
            returns restricted token with only ["health"] scope.
            If LOOM_ALLOW_ANONYMOUS=true, allows full anonymous access.
        """
        # If API key is configured, verify token against it
        if self.api_key:
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

        # No API key configured
        if self.allow_anonymous:
            # Explicitly allowed anonymous access
            logger.debug("anonymous_access allowed via LOOM_ALLOW_ANONYMOUS=true")
            return AccessToken(
                token="anonymous",
                client_id="anonymous",
                scopes=["*"],
            )

        # Default: restrict to health checks only
        logger.debug("anonymous_access restricted to health scope only")
        return AccessToken(
            token="anonymous-restricted",
            client_id="anonymous-restricted",
            scopes=["health"],
        )
