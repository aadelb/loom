"""Unit tests for SecretManager API key validation and rotation.

Tests cover:
- Key format validation (prefix, length, base64)
- Key rotation without restart
- Expiration tracking and staleness alerts
- Health status reporting
- Singleton pattern
"""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from loom.secret_manager import (
    KEY_CONFIGS,
    ALWAYS_AVAILABLE,
    SecretManager,
    get_secret_manager,
)


class TestSecretManagerValidation:
    """Test API key validation logic."""

    def test_validate_valid_groq_key(self) -> None:
        """Test validation of a valid Groq API key."""
        mgr = SecretManager()
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_validkeylongerthan20chars"}):
            mgr._load_keys_from_env()
            result = mgr.validate_key("groq")
            assert result["valid"] is True
            assert result["present"] is True
            assert result["format_check"] is True
            assert result["length_check"] is True
            assert result["prefix_check"] is True

    def test_validate_missing_key(self) -> None:
        """Test validation when key is not in environment."""
        mgr = SecretManager()
        with patch.dict(os.environ, {}, clear=True):
            mgr._load_keys_from_env()
            result = mgr.validate_key("groq")
            assert result["valid"] is False
            assert result["present"] is False
            assert result["error"] == "Key not present"

    def test_validate_key_too_short(self) -> None:
        """Test validation fails when key is too short."""
        mgr = SecretManager()
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_short"}):
            mgr._load_keys_from_env()
            result = mgr.validate_key("groq")
            assert result["valid"] is False
            assert result["length_check"] is False
            assert "too short" in result["error"].lower()

    def test_validate_key_wrong_prefix(self) -> None:
        """Test validation fails when key has wrong prefix."""
        mgr = SecretManager()
        with patch.dict(os.environ, {"GROQ_API_KEY": "wrong_prefixvalidkeylongerthan20"}):
            mgr._load_keys_from_env()
            result = mgr.validate_key("groq")
            assert result["valid"] is False
            assert result["prefix_check"] is False

    def test_validate_key_invalid_characters(self) -> None:
        """Test validation fails when key contains invalid characters."""
        mgr = SecretManager()
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_key!@#$%^&*()validlong"}):
            mgr._load_keys_from_env()
            result = mgr.validate_key("groq")
            assert result["valid"] is False
            assert result["format_check"] is False

    def test_validate_unknown_provider(self) -> None:
        """Test validation of unknown provider returns error."""
        mgr = SecretManager()
        result = mgr.validate_key("unknown_provider")
        assert result["valid"] is False
        assert "unknown provider" in result["error"].lower()

    def test_validate_all_keys(self) -> None:
        """Test validating all configured keys at once."""
        mgr = SecretManager()
        env_updates = {
            "GROQ_API_KEY": "gsk_validkeylongerthan20chars",
            "OPENAI_API_KEY": "sk_validkeylongerthan20charsmore",
        }
        with patch.dict(os.environ, env_updates):
            mgr._load_keys_from_env()
            results = mgr.validate_all_keys()

            assert "groq" in results
            assert "openai" in results
            assert results["groq"]["valid"] is True
            assert results["openai"]["valid"] is True

    def test_is_valid_base64(self) -> None:
        """Test base64 validation helper."""
        mgr = SecretManager()
        assert mgr._is_valid_base64("gsk_validkey123") is True
        assert mgr._is_valid_base64("sk-hyphens_and_underscores") is True
        assert mgr._is_valid_base64("") is False
        assert mgr._is_valid_base64("key!@#$%^&*()") is False


class TestSecretManagerRotation:
    """Test API key rotation."""

    def test_rotate_key_success(self) -> None:
        """Test successful key rotation."""
        mgr = SecretManager()
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_oldkeylongerthan20chars"}):
            mgr._load_keys_from_env()
            success = mgr.rotate_key("groq", "gsk_newkeylongerthan20chars")
            assert success is True
            assert mgr.get_key("groq") == "gsk_newkeylongerthan20chars"

    def test_rotate_key_invalid_new_key(self) -> None:
        """Test rotation fails when new key is invalid."""
        mgr = SecretManager()
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_oldkeylongerthan20chars"}):
            mgr._load_keys_from_env()
            old_key = mgr.get_key("groq")
            # Try to rotate to an invalid key (wrong prefix)
            success = mgr.rotate_key("groq", "wrong_prefixshortkey")
            assert success is False
            # Old key should be preserved
            assert mgr._keys["groq"] == old_key

    def test_rotate_key_not_supported(self) -> None:
        """Test rotation fails for providers that don't support it."""
        mgr = SecretManager()
        with patch.dict(os.environ, {"VLLM_ENDPOINT": "http://localhost:8000"}):
            mgr._load_keys_from_env()
            # vLLM doesn't support rotation
            success = mgr.rotate_key("vllm", "http://newlocation:8000")
            # Should succeed because validation passes, but config says not supported
            # Actually vLLM has rotation_supported=False, so should fail
            assert success is False

    def test_rotate_updates_last_used(self) -> None:
        """Test rotation updates last_used timestamp."""
        mgr = SecretManager()
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_oldkeylongerthan20chars"}):
            mgr._load_keys_from_env()
            mgr._last_used["groq"] = None
            mgr.rotate_key("groq", "gsk_newkeylongerthan20chars")
            assert mgr._last_used["groq"] is not None
            assert isinstance(mgr._last_used["groq"], datetime)

    def test_rotate_unknown_provider(self) -> None:
        """Test rotation fails for unknown provider."""
        mgr = SecretManager()
        success = mgr.rotate_key("unknown_provider", "somekey")
        assert success is False


class TestSecretManagerTracking:
    """Test last-used timestamp tracking."""

    def test_get_key_updates_last_used(self) -> None:
        """Test that calling get_key updates the last_used timestamp."""
        mgr = SecretManager()
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_validkeylongerthan20chars"}):
            mgr._load_keys_from_env()
            mgr._last_used["groq"] = None

            mgr.get_key("groq")
            assert mgr._last_used["groq"] is not None

    def test_get_last_used(self) -> None:
        """Test retrieving last_used timestamp."""
        mgr = SecretManager()
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_validkeylongerthan20chars"}):
            mgr._load_keys_from_env()
            now = datetime.now(UTC)
            mgr._last_used["groq"] = now

            retrieved = mgr.get_last_used("groq")
            assert retrieved == now

    def test_get_expiry_placeholder(self) -> None:
        """Test get_expiry returns None (placeholder for future use)."""
        mgr = SecretManager()
        expiry = mgr.get_expiry("groq")
        assert expiry is None


class TestSecretManagerHealth:
    """Test health status reporting."""

    def test_get_health_all_valid(self) -> None:
        """Test health status when all keys are valid."""
        mgr = SecretManager()
        env_updates = {
            "GROQ_API_KEY": "gsk_validkeylongerthan20chars",
            "OPENAI_API_KEY": "sk_validkeylongerthan20charsmore",
        }
        with patch.dict(os.environ, env_updates):
            mgr._load_keys_from_env()
            mgr.validate_all_keys()
            health = mgr.get_health()

            assert health["overall_status"] == "healthy"
            assert health["valid_keys"] >= 2
            assert "providers" in health
            assert "timestamp" in health

    def test_get_health_no_keys(self) -> None:
        """Test health status when no keys are configured."""
        mgr = SecretManager()
        with patch.dict(os.environ, {}, clear=True):
            mgr._load_keys_from_env()
            mgr.validate_all_keys()
            health = mgr.get_health()

            assert health["overall_status"] == "unhealthy"
            assert health["valid_keys"] == 0
            assert health["missing_keys"] > 0

    def test_get_health_stale_keys(self) -> None:
        """Test health status alerts on stale keys."""
        mgr = SecretManager()
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_validkeylongerthan20chars"}):
            mgr._load_keys_from_env()
            mgr.validate_all_keys()

            # Mark key as used 8 days ago
            mgr._last_used["groq"] = datetime.now(UTC) - timedelta(days=8)
            health = mgr.get_health()

            assert health["overall_status"] == "degraded"
            assert "groq" in health["stale_keys"]

    def test_get_health_providers_detail(self) -> None:
        """Test health status includes detailed provider info."""
        mgr = SecretManager()
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_validkeylongerthan20chars"}):
            mgr._load_keys_from_env()
            mgr.validate_all_keys()
            health = mgr.get_health()

            assert "groq" in health["providers"]
            provider_info = health["providers"]["groq"]
            assert "status" in provider_info
            assert "present" in provider_info
            assert "valid" in provider_info
            assert "last_used" in provider_info


class TestSecretManagerSingleton:
    """Test singleton pattern."""

    def test_get_secret_manager_singleton(self) -> None:
        """Test that get_secret_manager returns the same instance."""
        mgr1 = get_secret_manager()
        mgr2 = get_secret_manager()
        assert mgr1 is mgr2

    def test_singleton_thread_safety(self) -> None:
        """Test singleton is thread-safe."""
        import threading

        results = []

        def get_manager() -> None:
            mgr = get_secret_manager()
            results.append(id(mgr))

        threads = [threading.Thread(target=get_manager) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All threads should get the same instance
        assert len(set(results)) == 1


class TestSecretManagerKeyConfigs:
    """Test KEY_CONFIGS structure."""

    def test_all_llm_providers_configured(self) -> None:
        """Test that all 8 LLM providers are in KEY_CONFIGS."""
        llm_providers = [
            "groq",
            "nvidia_nim",
            "deepseek",
            "gemini",
            "moonshot",
            "openai",
            "anthropic",
            "vllm",
        ]
        for provider in llm_providers:
            assert provider in KEY_CONFIGS
            assert "env_var" in KEY_CONFIGS[provider]
            assert "prefix" in KEY_CONFIGS[provider]
            assert "min_length" in KEY_CONFIGS[provider]
            assert "rotation_supported" in KEY_CONFIGS[provider]

    def test_all_search_providers_configured(self) -> None:
        """Test that all search providers needing keys are configured."""
        search_providers = [
            "exa",
            "tavily",
            "firecrawl",
            "brave",
            "newsapi",
            "coinmarketcap",
        ]
        for provider in search_providers:
            assert provider in KEY_CONFIGS

    def test_always_available_providers(self) -> None:
        """Test that always-available providers are properly marked."""
        assert "ddgs" in ALWAYS_AVAILABLE
        assert "arxiv" in ALWAYS_AVAILABLE
        assert "wikipedia" in ALWAYS_AVAILABLE
        assert "hackernews" in ALWAYS_AVAILABLE
        assert "reddit" in ALWAYS_AVAILABLE


class TestSecretHealthMCP:
    """Test research_secret_health MCP tool."""

    @pytest.mark.asyncio
    async def test_research_secret_health_basic(self) -> None:
        """Test basic MCP tool execution."""
        from loom.secret_manager import research_secret_health

        with patch.dict(
            os.environ,
            {"GROQ_API_KEY": "gsk_validkeylongerthan20chars"},
        ):
            # Force refresh of singleton
            from loom import secret_manager
            secret_manager._manager = None
            get_secret_manager()

            result = await research_secret_health()

            assert "overall_status" in result
            assert "valid_keys" in result
            assert "missing_keys" in result
            assert "stale_keys" in result
            assert "providers" in result
            assert "timestamp" in result
            assert "always_available" in result

    @pytest.mark.asyncio
    async def test_research_secret_health_response_format(self) -> None:
        """Test MCP tool response format is correct."""
        from loom.secret_manager import research_secret_health

        result = await research_secret_health()

        # Verify all expected fields
        assert isinstance(result["overall_status"], str)
        assert result["overall_status"] in ["healthy", "degraded", "unhealthy"]
        assert isinstance(result["valid_keys"], int)
        assert isinstance(result["missing_keys"], int)
        assert isinstance(result["stale_keys"], list)
        assert isinstance(result["providers"], dict)
        assert isinstance(result["always_available"], list)
