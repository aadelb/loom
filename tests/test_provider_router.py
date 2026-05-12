"""Tests for provider_router module.

Tests select_provider, is_provider_available, and cascade status.
"""

from __future__ import annotations

import os
from typing import Any, Generator

import pytest

from loom.provider_router import (
    cascade_status,
    get_available_providers,
    get_provider_config,
    is_provider_available,
    select_provider,
)


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Fixture to save and restore environment variables."""
    saved_env = {}
    provider_keys = [
        "GROQ_API_KEY",
        "NVIDIA_NIM_API_KEY",
        "DEEPSEEK_API_KEY",
        "GOOGLE_AI_KEY",
        "MOONSHOT_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "VLLM_ENDPOINT",
    ]
    for key in provider_keys:
        saved_env[key] = os.environ.get(key)
        if key in os.environ:
            del os.environ[key]
    yield
    # Restore
    for key, value in saved_env.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


class TestIsProviderAvailable:
    """Test is_provider_available function."""

    def test_is_provider_available_when_set(self, clean_env: None) -> None:
        """Test provider is available when env var is set."""
        os.environ["GROQ_API_KEY"] = "test-key-123"
        assert is_provider_available("groq") is True

    def test_is_provider_available_when_not_set(self, clean_env: None) -> None:
        """Test provider is not available when env var is missing."""
        assert is_provider_available("groq") is False

    def test_is_provider_available_empty_string(self, clean_env: None) -> None:
        """Test provider is not available when env var is empty string."""
        os.environ["GROQ_API_KEY"] = ""
        assert is_provider_available("groq") is False

    def test_is_provider_available_whitespace_only(self, clean_env: None) -> None:
        """Test provider is not available when env var is whitespace."""
        os.environ["GROQ_API_KEY"] = "   "
        # After strip(), empty string = False
        assert is_provider_available("groq") is False

    def test_is_provider_available_unknown_provider(self, clean_env: None) -> None:
        """Test unknown provider returns False."""
        result = is_provider_available("unknown_provider")
        assert result is False

    def test_is_provider_available_all_providers(self, clean_env: None) -> None:
        """Test availability check for all known providers."""
        providers = ["groq", "nvidia", "deepseek", "gemini", "moonshot", "openai", "anthropic", "vllm"]
        for provider in providers:
            result = is_provider_available(provider)
            assert isinstance(result, bool)


class TestGetAvailableProviders:
    """Test get_available_providers function."""

    def test_get_available_providers_none_set(self, clean_env: None) -> None:
        """Test getting available providers when none are set."""
        providers = get_available_providers()
        assert isinstance(providers, list)
        assert len(providers) == 0

    def test_get_available_providers_one_set(self, clean_env: None) -> None:
        """Test getting available providers when one is set."""
        os.environ["GROQ_API_KEY"] = "key"
        providers = get_available_providers()
        assert "groq" in providers

    def test_get_available_providers_multiple_set(self, clean_env: None) -> None:
        """Test getting available providers when multiple are set."""
        os.environ["GROQ_API_KEY"] = "key1"
        os.environ["OPENAI_API_KEY"] = "key2"
        providers = get_available_providers()
        assert "groq" in providers
        assert "openai" in providers

    def test_get_available_providers_respects_cascade_order(self, clean_env: None) -> None:
        """Test that returned providers respect cascade order."""
        os.environ["GROQ_API_KEY"] = "key"
        os.environ["ANTHROPIC_API_KEY"] = "key"
        cascade = ["anthropic", "groq"]
        providers = get_available_providers(cascade=cascade)
        # Should return in cascade order
        assert providers[0] == "anthropic"
        assert providers[1] == "groq"


class TestSelectProvider:
    """Test select_provider function."""

    def test_select_provider_preferred_available(self, clean_env: None) -> None:
        """Test selecting preferred provider when available."""
        os.environ["GROQ_API_KEY"] = "key1"
        os.environ["OPENAI_API_KEY"] = "key2"
        selected = select_provider(preferred="groq")
        assert selected == "groq"

    def test_select_provider_preferred_not_available(self, clean_env: None) -> None:
        """Test fallback when preferred not available."""
        os.environ["OPENAI_API_KEY"] = "key"
        selected = select_provider(preferred="groq")
        assert selected == "openai"

    def test_select_provider_cascade_order(self, clean_env: None) -> None:
        """Test cascade order is respected."""
        os.environ["OPENAI_API_KEY"] = "key1"
        os.environ["GROQ_API_KEY"] = "key2"
        cascade = ["openai", "groq"]
        selected = select_provider(cascade=cascade)
        assert selected == "openai"

    def test_select_provider_exclude(self, clean_env: None) -> None:
        """Test excluding providers."""
        os.environ["GROQ_API_KEY"] = "key1"
        os.environ["OPENAI_API_KEY"] = "key2"
        selected = select_provider(exclude={"groq"})
        assert selected == "openai"

    def test_select_provider_no_available(self, clean_env: None) -> None:
        """Test returning None when no providers available."""
        selected = select_provider()
        assert selected is None

    def test_select_provider_preferred_excluded(self, clean_env: None) -> None:
        """Test that excluded preferred provider is skipped."""
        os.environ["GROQ_API_KEY"] = "key1"
        os.environ["OPENAI_API_KEY"] = "key2"
        selected = select_provider(preferred="groq", exclude={"groq"})
        assert selected == "openai"

    def test_select_provider_all_excluded(self, clean_env: None) -> None:
        """Test returning None when all available are excluded."""
        os.environ["GROQ_API_KEY"] = "key"
        selected = select_provider(exclude={"groq"})
        assert selected is None


class TestGetProviderConfig:
    """Test get_provider_config function."""

    def test_get_provider_config_available(self, clean_env: None) -> None:
        """Test getting config for available provider."""
        os.environ["GROQ_API_KEY"] = "test-key"
        config = get_provider_config("groq")
        assert config["provider"] == "groq"
        assert config["available"] is True
        assert config["api_key_set"] is True

    def test_get_provider_config_unavailable(self, clean_env: None) -> None:
        """Test getting config for unavailable provider."""
        config = get_provider_config("groq")
        assert config["provider"] == "groq"
        assert config["available"] is False
        assert config["api_key_set"] is False

    def test_get_provider_config_structure(self, clean_env: None) -> None:
        """Test config has required fields."""
        os.environ["OPENAI_API_KEY"] = "key"
        config = get_provider_config("openai")
        assert "provider" in config
        assert "env_key" in config
        assert "available" in config
        assert "api_key_set" in config


class TestCascadeStatus:
    """Test cascade_status function."""

    def test_cascade_status_returns_all_providers(self, clean_env: None) -> None:
        """Test cascade_status returns all providers."""
        status = cascade_status()
        assert len(status) >= 8  # At least the default providers

    def test_cascade_status_structure(self, clean_env: None) -> None:
        """Test cascade_status returns proper structure."""
        status = cascade_status()
        for provider_status in status:
            assert "provider" in provider_status
            assert "env_key" in provider_status
            assert "available" in provider_status
            assert isinstance(provider_status["available"], bool)

    def test_cascade_status_includes_groq(self, clean_env: None) -> None:
        """Test cascade_status includes groq."""
        status = cascade_status()
        providers = [s["provider"] for s in status]
        assert "groq" in providers

    def test_cascade_status_one_available(self, clean_env: None) -> None:
        """Test cascade_status with one available provider."""
        os.environ["GROQ_API_KEY"] = "key"
        status = cascade_status()
        groq_status = next((s for s in status if s["provider"] == "groq"), None)
        assert groq_status is not None
        assert groq_status["available"] is True


class TestProviderIntegration:
    """Integration tests combining multiple functions."""

    def test_workflow_select_and_verify(self, clean_env: None) -> None:
        """Test typical workflow: select provider and verify config."""
        os.environ["GROQ_API_KEY"] = "key1"
        os.environ["OPENAI_API_KEY"] = "key2"

        # Select a provider
        provider = select_provider()
        assert provider is not None

        # Verify it's available
        assert is_provider_available(provider)

        # Get its config
        config = get_provider_config(provider)
        assert config["available"] is True

    def test_workflow_cascade_fallback(self, clean_env: None) -> None:
        """Test cascade fallback workflow."""
        os.environ["OPENAI_API_KEY"] = "key"

        # Try to select groq (primary)
        selected = select_provider(preferred="groq")
        # Should fallback to openai
        assert selected == "openai"

        # Verify openai is available
        assert is_provider_available("openai")

        # Verify groq is not available
        assert not is_provider_available("groq")
