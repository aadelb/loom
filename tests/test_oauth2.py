"""Tests for OAuth2 provider scaffold."""

from __future__ import annotations

import pytest

from loom.oauth2 import (
    OAuth2Provider,
    ProviderConfig,
    SUPPORTED_PROVIDERS,
    research_oauth2_status,
)


class TestProviderConfig:
    """Test ProviderConfig dataclass."""

    def test_provider_config_fields(self) -> None:
        """Test ProviderConfig has all required fields."""
        config = SUPPORTED_PROVIDERS["google"]
        assert isinstance(config, ProviderConfig)
        assert config.auth_url.startswith("https://")
        assert config.token_url.startswith("https://")
        assert config.userinfo_url.startswith("https://")
        assert "openid" in config.scopes

    def test_all_providers_configured(self) -> None:
        """Test all three providers are configured."""
        assert "google" in SUPPORTED_PROVIDERS
        assert "azure" in SUPPORTED_PROVIDERS
        assert "okta" in SUPPORTED_PROVIDERS
        assert len(SUPPORTED_PROVIDERS) == 3


class TestOAuth2Provider:
    """Test OAuth2Provider class."""

    def test_init_google(self) -> None:
        """Test initializing Google provider."""
        provider = OAuth2Provider(
            provider="google",
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="http://localhost/callback",
        )
        assert provider.provider == "google"
        assert provider.client_id == "test_id"
        assert provider.config.auth_url == SUPPORTED_PROVIDERS["google"].auth_url

    def test_init_azure(self) -> None:
        """Test initializing Azure provider."""
        provider = OAuth2Provider(
            provider="azure",
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="http://localhost/callback",
        )
        assert provider.provider == "azure"

    def test_init_okta(self) -> None:
        """Test initializing Okta provider."""
        provider = OAuth2Provider(
            provider="okta",
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="http://localhost/callback",
        )
        assert provider.provider == "okta"

    def test_init_invalid_provider(self) -> None:
        """Test initialization with invalid provider raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            OAuth2Provider(
                provider="invalid",
                client_id="test_id",
                client_secret="test_secret",
                redirect_uri="http://localhost/callback",
            )

    def test_get_authorization_url_without_state(self) -> None:
        """Test generating authorization URL without state."""
        provider = OAuth2Provider(
            provider="google",
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost/callback",
        )
        url = provider.get_authorization_url()
        assert url.startswith(SUPPORTED_PROVIDERS["google"].auth_url)
        assert "client_id=test_client" in url
        assert "redirect_uri=" in url
        assert "response_type=code" in url
        assert "scope=" in url

    def test_get_authorization_url_with_state(self) -> None:
        """Test generating authorization URL with CSRF state."""
        provider = OAuth2Provider(
            provider="google",
            client_id="test_client",
            client_secret="test_secret",
            redirect_uri="http://localhost/callback",
        )
        url = provider.get_authorization_url(state="random_state_123")
        assert "state=random_state_123" in url


class TestResearchOAuth2Status:
    """Test research_oauth2_status function."""

    @pytest.mark.asyncio
    async def test_oauth2_status(self) -> None:
        """Test OAuth2 status endpoint."""
        status = await research_oauth2_status()
        assert "supported_providers" in status
        assert "providers" in status
        assert "note" in status
        assert len(status["supported_providers"]) == 3
        assert status["supported_providers"] == ["google", "azure", "okta"]

    @pytest.mark.asyncio
    async def test_oauth2_status_provider_configs(self) -> None:
        """Test provider configs in status."""
        status = await research_oauth2_status()
        for provider_name in ["google", "azure", "okta"]:
            assert provider_name in status["providers"]
            provider_info = status["providers"][provider_name]
            assert "auth_url" in provider_info
            assert "token_url" in provider_info
            assert "userinfo_url" in provider_info
            assert "scopes" in provider_info
            assert "configured" in provider_info
