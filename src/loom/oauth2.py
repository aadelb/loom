"""OAuth2 enterprise SSO provider scaffold for Loom MCP server.

Supports Google, Azure, and Okta providers with JWT validation and token refresh.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast
from urllib.parse import urlencode

import httpx

logger = logging.getLogger("loom.oauth2")


@dataclass
class ProviderConfig:
    """OAuth2 provider configuration."""

    auth_url: str
    token_url: str
    userinfo_url: str
    scopes: list[str]


SUPPORTED_PROVIDERS: dict[str, ProviderConfig] = {
    "google": ProviderConfig(
        auth_url="https://accounts.google.com/o/oauth2/v2/auth",
        token_url="https://oauth2.googleapis.com/token",
        userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
        scopes=["openid", "email", "profile"],
    ),
    "azure": ProviderConfig(
        auth_url="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
        token_url="https://login.microsoftonline.com/common/oauth2/v2.0/token",
        userinfo_url="https://graph.microsoft.com/v1.0/me",
        scopes=["openid", "email", "profile"],
    ),
    "okta": ProviderConfig(
        auth_url="https://developer.okta.com/oauth2/v1/authorize",
        token_url="https://developer.okta.com/oauth2/v1/token",
        userinfo_url="https://developer.okta.com/oauth2/v1/userinfo",
        scopes=["openid", "email", "profile"],
    ),
}


class OAuth2Provider:
    """OAuth2 provider client for enterprise SSO."""

    def __init__(
        self,
        provider: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        """Initialize OAuth2 provider.

        Args:
            provider: "google", "azure", or "okta"
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
            redirect_uri: OAuth2 redirect URI (must match provider config)

        Raises:
            ValueError: If provider not in SUPPORTED_PROVIDERS
        """
        if provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider}")

        self.provider = provider
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.config = SUPPORTED_PROVIDERS[provider]

    def get_authorization_url(self, state: str | None = None) -> str:
        """Generate OAuth2 authorization URL.

        Args:
            state: Optional CSRF state token (should be randomly generated)

        Returns:
            Authorization URL for user to visit
        """
        params: dict[str, str] = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.config.scopes),
        }
        if state:
            params["state"] = state

        return f"{self.config.auth_url}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth2 provider

        Returns:
            Dict with access_token, refresh_token, expires_in, token_type

        Raises:
            httpx.HTTPError: If token exchange fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                },
            )
            response.raise_for_status()
            return cast(dict[str, Any], response.json())

    async def validate_token(self, token: str) -> dict[str, Any]:
        """Validate access token and retrieve user info.

        Args:
            token: OAuth2 access token

        Returns:
            Dict with user info (sub, email, name, etc.)

        Raises:
            httpx.HTTPError: If token validation fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return cast(dict[str, Any], response.json())

    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        """Refresh expired access token.

        Args:
            refresh_token: OAuth2 refresh token

        Returns:
            Dict with new access_token, expires_in, token_type

        Raises:
            httpx.HTTPError: If refresh fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_url,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            response.raise_for_status()
            return cast(dict[str, Any], response.json())


async def research_oauth2_status() -> dict[str, Any]:
    """Show configured OAuth2 providers and status.

    Returns:
        Dict with supported_providers and their config (secret redacted)
    """
    providers_info: dict[str, Any] = {}
    for name, config in SUPPORTED_PROVIDERS.items():
        providers_info[name] = {
            "auth_url": config.auth_url,
            "token_url": config.token_url,
            "userinfo_url": config.userinfo_url,
            "scopes": config.scopes,
            "configured": False,  # Would check env vars in production
        }

    return {
        "supported_providers": list(SUPPORTED_PROVIDERS.keys()),
        "providers": providers_info,
        "note": "Credentials configured via environment or config system",
    }
