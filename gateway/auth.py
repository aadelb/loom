"""Authentication layer for gateway routing.

Delegates to loom.auth.ApiKeyVerifier for token validation.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("gateway.auth")


class GatewayAuthProvider:
    """Gateway authentication provider using Loom's ApiKeyVerifier."""

    def __init__(self) -> None:
        """Initialize authentication provider."""
        try:
            from loom.auth import ApiKeyVerifier
            self.verifier = ApiKeyVerifier()
            logger.info("auth_initialized ApiKeyVerifier from loom.auth")
        except ImportError:
            logger.warning("loom.auth not available, falling back to simple API key check")
            self.verifier = None

    async def verify_bearer_token(self, token: str) -> dict[str, Any] | None:
        """Verify a bearer token.

        Args:
            token: Bearer token to verify

        Returns:
            Auth context dict with client_id and scopes if valid, None otherwise.
        """
        if not token:
            logger.warning("auth_failed empty_token")
            return None

        if self.verifier:
            # Use Loom's ApiKeyVerifier
            access_token = await self.verifier.verify_token(token)
            if access_token:
                return {
                    "client_id": access_token.client_id,
                    "scopes": access_token.scopes,
                    "token": access_token.token,
                }
            return None

        # Fallback: simple env-based API key check
        api_key = os.environ.get("LOOM_API_KEY", "")
        if api_key and token == api_key:
            logger.info("auth_success client_id=gateway_api_key")
            return {
                "client_id": "gateway_api_key",
                "scopes": ["*"],
                "token": token,
            }

        logger.warning("auth_failed token_mismatch")
        return None

    def extract_bearer_token(self, authorization_header: str | None) -> str | None:
        """Extract bearer token from Authorization header.

        Args:
            authorization_header: Authorization header value (e.g., 'Bearer token123')

        Returns:
            Extracted token string or None if invalid format.
        """
        if not authorization_header:
            return None

        parts = authorization_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.debug("auth_invalid_header_format header=%s", authorization_header[:20])
            return None

        return parts[1]
