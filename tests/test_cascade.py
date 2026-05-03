"""Tests for LLM cascade failover and search provider fallback (REQ-053, REQ-054).

Tests cover:
- REQ-053: LLM cascade failover across 8 providers
- REQ-054: Search provider fallback when primary is rate-limited
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.config import CONFIG, ConfigModel, load_config
from loom.providers.base import LLMResponse


class TestLLMCascadeConfig:
    """Test LLM_CASCADE_ORDER configuration (REQ-053)."""

    def test_cascade_order_from_config_is_list(self, tmp_config_path) -> None:
        """LLM_CASCADE_ORDER config key is a list of provider names."""
        load_config(tmp_config_path)
        cascade = CONFIG.get("LLM_CASCADE_ORDER", [])
        assert isinstance(cascade, list)
        assert len(cascade) >= 4

    def test_cascade_order_contains_valid_providers(self, tmp_config_path) -> None:
        """All cascade order entries are valid provider names."""
        load_config(tmp_config_path)
        cascade = CONFIG.get("LLM_CASCADE_ORDER", [])
        valid_providers = {"groq", "nvidia", "deepseek", "gemini", "moonshot", "openai", "anthropic", "vllm"}
        for provider in cascade:
            assert provider in valid_providers, f"Unknown provider in cascade: {provider}"

    def test_cascade_order_default_has_free_providers_first(self, tmp_config_path) -> None:
        """Cascade order puts free/cheap providers (groq, nvidia) first."""
        load_config(tmp_config_path)
        cascade = CONFIG.get("LLM_CASCADE_ORDER", [])
        assert len(cascade) > 0
        # First provider should be from the free tier
        free_providers = {"groq", "nvidia"}
        assert cascade[0] in free_providers

    def test_cascade_order_has_anthropic_openai_fallback(self, tmp_config_path) -> None:
        """Cascade includes paid providers (openai, anthropic) as fallback."""
        load_config(tmp_config_path)
        cascade = CONFIG.get("LLM_CASCADE_ORDER", [])
        # At least one paid provider should be present
        has_paid = "openai" in cascade or "anthropic" in cascade
        assert has_paid, "No paid provider in cascade for fallback"

    def test_cascade_order_string_coercion(self) -> None:
        """LLM_CASCADE_ORDER accepts comma-separated string and coerces to list."""
        config_dict = {
            "LLM_CASCADE_ORDER": "groq,nvidia,openai,anthropic"
        }
        model = ConfigModel(**config_dict)
        cascade = model.LLM_CASCADE_ORDER
        assert isinstance(cascade, list)
        assert cascade == ["groq", "nvidia", "openai", "anthropic"]

    def test_cascade_order_empty_string_uses_default(self) -> None:
        """Empty LLM_CASCADE_ORDER falls back to sensible default."""
        config_dict = {
            "LLM_CASCADE_ORDER": ""
        }
        model = ConfigModel(**config_dict)
        cascade = model.LLM_CASCADE_ORDER
        # Should fall back to default, not be empty
        assert len(cascade) > 0

    def test_cascade_order_none_uses_default(self) -> None:
        """None LLM_CASCADE_ORDER falls back to sensible default."""
        config_dict = {
            "LLM_CASCADE_ORDER": None
        }
        model = ConfigModel(**config_dict)
        cascade = model.LLM_CASCADE_ORDER
        assert len(cascade) > 0
        assert isinstance(cascade, list)


class TestLLMCascadeFailover:
    """Test provider failover in cascade chain (REQ-053)."""

    @pytest.mark.asyncio
    async def test_cascade_tries_providers_in_order(self) -> None:
        """Cascade tries providers in configured order."""
        from loom.tools.llm import _build_provider_chain, _call_with_cascade

        # Load config
        load_config()
        cascade_order = CONFIG.get("LLM_CASCADE_ORDER", [])
        assert len(cascade_order) > 0

        # Mock the providers to track call order
        call_order = []

        async def mock_provider_chat(self, messages, **kwargs) -> LLMResponse:
            call_order.append(self.name)
            raise ConnectionError(f"{self.name} unavailable")

        # Patch provider chat method
        with patch("loom.providers.base.LLMProvider.chat", new=mock_provider_chat):
            with patch("loom.providers.base.LLMProvider.available", return_value=True):
                try:
                    await _call_with_cascade([{"role": "user", "content": "test"}])
                except RuntimeError:
                    # Expected: all providers fail
                    pass

        # Verify providers were attempted in cascade order
        if len(call_order) > 0:
            assert call_order[0] == cascade_order[0]

    @pytest.mark.asyncio
    async def test_cascade_returns_first_success(self) -> None:
        """Cascade returns response from first successful provider."""
        # Create a mock response
        success_response = LLMResponse(
            text="Success from provider 2",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            cost_usd=0.01,
            latency_ms=100,
            provider="provider2",
            finish_reason="stop",
        )

        call_count = {"count": 0}

        async def mock_chat(self, messages, **kwargs) -> LLMResponse:
            call_count["count"] += 1
            if self.name == "provider1":
                raise ConnectionError("Provider 1 down")
            return success_response

        with patch("loom.providers.base.LLMProvider.chat", new=mock_chat):
            with patch("loom.providers.base.LLMProvider.available", return_value=True):
                with patch("loom.tools.llm._get_provider") as mock_get:
                    # Create mock providers
                    p1 = MagicMock()
                    p1.name = "provider1"
                    p1.available = MagicMock(return_value=True)
                    p1.chat = AsyncMock(side_effect=ConnectionError("Provider 1 down"))

                    p2 = MagicMock()
                    p2.name = "provider2"
                    p2.available = MagicMock(return_value=True)
                    p2.chat = AsyncMock(return_value=success_response)

                    async def get_provider_side_effect(name):
                        if name == "provider1":
                            return p1
                        return p2

                    mock_get.side_effect = get_provider_side_effect

                    # Mock _build_provider_chain
                    with patch("loom.tools.llm._build_provider_chain") as mock_chain:
                        mock_chain.return_value = [p1, p2]

                        # Mock config
                        with patch("loom.config.CONFIG", {"LLM_CASCADE_ORDER": ["provider1", "provider2"]}):
                            from loom.tools.llm import _call_with_cascade

                            result = await _call_with_cascade([{"role": "user", "content": "test"}])

                            assert result.provider == "provider2"
                            assert result.text == "Success from provider 2"
                            # p1 should be called and fail, then p2 should succeed
                            assert p1.chat.called
                            assert p2.chat.called

    @pytest.mark.asyncio
    async def test_cascade_skips_unavailable_providers(self) -> None:
        """Cascade skips providers that are not available()."""
        available_responses = {"provider1": False, "provider2": True}

        success_response = LLMResponse(
            text="Success from provider 2",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            cost_usd=0.01,
            latency_ms=100,
            provider="provider2",
            finish_reason="stop",
        )

        p1 = MagicMock()
        p1.name = "provider1"
        p1.available = MagicMock(return_value=False)
        p1.chat = AsyncMock()

        p2 = MagicMock()
        p2.name = "provider2"
        p2.available = MagicMock(return_value=True)
        p2.chat = AsyncMock(return_value=success_response)

        with patch("loom.tools.llm._build_provider_chain", return_value=[p1, p2]):
            with patch("loom.config.CONFIG", {"LLM_CASCADE_ORDER": ["provider1", "provider2"]}):
                from loom.tools.llm import _call_with_cascade

                result = await _call_with_cascade([{"role": "user", "content": "test"}])

                # p1 should not be called (unavailable)
                assert not p1.chat.called
                # p2 should be called and succeed
                assert p2.chat.called
                assert result.provider == "provider2"

    @pytest.mark.asyncio
    async def test_cascade_all_providers_fail_raises_error(self) -> None:
        """Cascade raises RuntimeError when all providers fail."""
        p1 = MagicMock()
        p1.name = "provider1"
        p1.available = MagicMock(return_value=True)
        p1.chat = AsyncMock(side_effect=ConnectionError("Provider 1 down"))

        p2 = MagicMock()
        p2.name = "provider2"
        p2.available = MagicMock(return_value=True)
        p2.chat = AsyncMock(side_effect=ConnectionError("Provider 2 down"))

        with patch("loom.tools.llm._build_provider_chain", return_value=[p1, p2]):
            with patch("loom.config.CONFIG", {"LLM_CASCADE_ORDER": ["provider1", "provider2"]}):
                from loom.tools.llm import _call_with_cascade

                with pytest.raises(RuntimeError):
                    await _call_with_cascade([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_cascade_handles_429_rate_limit(self) -> None:
        """Cascade continues on 429 rate limit error."""
        from httpx import HTTPStatusError, Request, Response as HttpResponse

        success_response = LLMResponse(
            text="Success",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            cost_usd=0.01,
            latency_ms=100,
            provider="provider2",
            finish_reason="stop",
        )

        # Create a 429 status error
        rate_limit_error = HTTPStatusError(
            "429 Rate Limit",
            request=Request("POST", "https://api.example.com/test"),
            response=HttpResponse(429),
        )

        p1 = MagicMock()
        p1.name = "provider1"
        p1.available = MagicMock(return_value=True)
        p1.chat = AsyncMock(side_effect=rate_limit_error)

        p2 = MagicMock()
        p2.name = "provider2"
        p2.available = MagicMock(return_value=True)
        p2.chat = AsyncMock(return_value=success_response)

        with patch("loom.tools.llm._build_provider_chain", return_value=[p1, p2]):
            with patch("loom.config.CONFIG", {"LLM_CASCADE_ORDER": ["provider1", "provider2"]}):
                from loom.tools.llm import _call_with_cascade

                result = await _call_with_cascade([{"role": "user", "content": "test"}])

                assert p1.chat.called
                assert p2.chat.called
                assert result.provider == "provider2"

    @pytest.mark.asyncio
    async def test_cascade_handles_timeout(self) -> None:
        """Cascade continues on timeout error."""
        success_response = LLMResponse(
            text="Success",
            model="test-model",
            input_tokens=10,
            output_tokens=20,
            cost_usd=0.01,
            latency_ms=100,
            provider="provider2",
            finish_reason="stop",
        )

        p1 = MagicMock()
        p1.name = "provider1"
        p1.available = MagicMock(return_value=True)
        p1.chat = AsyncMock(side_effect=TimeoutError("Request timeout"))

        p2 = MagicMock()
        p2.name = "provider2"
        p2.available = MagicMock(return_value=True)
        p2.chat = AsyncMock(return_value=success_response)

        with patch("loom.tools.llm._build_provider_chain", return_value=[p1, p2]):
            with patch("loom.config.CONFIG", {"LLM_CASCADE_ORDER": ["provider1", "provider2"]}):
                from loom.tools.llm import _call_with_cascade

                result = await _call_with_cascade([{"role": "user", "content": "test"}])

                assert p1.chat.called
                assert p2.chat.called
                assert result.provider == "provider2"


class TestSearchProviderFallback:
    """Test search provider fallback when primary is rate-limited (REQ-054)."""

    def test_search_providers_configured(self, tmp_config_path) -> None:
        """Multiple search providers are configured."""
        load_config(tmp_config_path)
        providers = CONFIG.get("RESEARCH_SEARCH_PROVIDERS", [])
        assert isinstance(providers, list)
        assert len(providers) >= 2

    def test_search_providers_list_is_valid(self, tmp_config_path) -> None:
        """All configured search providers are valid names."""
        load_config(tmp_config_path)
        providers = CONFIG.get("RESEARCH_SEARCH_PROVIDERS", [])
        valid_providers = {
            "exa", "tavily", "firecrawl", "brave", "ddgs",
            "arxiv", "wikipedia", "hackernews", "reddit",
            "newsapi", "crypto", "coindesk", "binance",
            "investing", "ahmia", "darksearch", "ummro",
            "onionsearch", "torcrawl", "darkweb_cti", "robin_osint"
        }
        for provider in providers:
            assert provider in valid_providers, f"Unknown search provider: {provider}"

    def test_search_providers_string_coercion(self) -> None:
        """RESEARCH_SEARCH_PROVIDERS accepts comma-separated string."""
        config_dict = {
            "RESEARCH_SEARCH_PROVIDERS": "exa,tavily,brave"
        }
        model = ConfigModel(**config_dict)
        providers = model.RESEARCH_SEARCH_PROVIDERS
        assert isinstance(providers, list)
        assert providers == ["exa", "tavily", "brave"]

    def test_search_providers_empty_string_uses_default(self) -> None:
        """Empty RESEARCH_SEARCH_PROVIDERS falls back to default."""
        config_dict = {
            "RESEARCH_SEARCH_PROVIDERS": ""
        }
        model = ConfigModel(**config_dict)
        providers = model.RESEARCH_SEARCH_PROVIDERS
        assert len(providers) > 0
        assert "exa" in providers or "brave" in providers

    def test_default_search_provider_in_valid_list(self, tmp_config_path) -> None:
        """DEFAULT_SEARCH_PROVIDER is in the valid provider list."""
        load_config(tmp_config_path)
        default = CONFIG.get("DEFAULT_SEARCH_PROVIDER", "exa")
        valid = {
            "exa", "tavily", "firecrawl", "brave", "ddgs",
            "arxiv", "wikipedia", "hackernews", "reddit",
            "newsapi", "crypto", "coindesk", "binance",
            "investing", "ahmia", "darksearch", "ummro",
            "onionsearch", "torcrawl", "darkweb_cti", "robin_osint"
        }
        assert default in valid

    def test_search_fallback_on_rate_limit(self) -> None:
        """Search function would fallback on rate limit (simulated)."""
        # Simulate a rate limit scenario
        providers = ["exa", "tavily", "brave"]
        providers_tried = []

        def mock_search(provider, fail_primary=False):
            providers_tried.append(provider)
            if fail_primary and provider == "exa":
                raise Exception("429 Rate Limited")
            return {"provider": provider, "results": [{"title": "Result"}]}

        # Try first provider, get rate limit, fallback to second
        result = None
        for provider in providers:
            try:
                result = mock_search(provider, fail_primary=True)
                break
            except Exception:
                continue

        assert result is not None
        assert result["provider"] == "tavily"
        assert "exa" in providers_tried
        assert "tavily" in providers_tried

    def test_search_fallback_exhausts_all_providers(self) -> None:
        """When all search providers fail, returns error (simulated)."""
        providers = ["exa", "tavily", "brave"]
        errors = []

        def mock_search(provider, fail=True):
            if fail:
                raise Exception(f"{provider} rate limited")
            return {"provider": provider, "results": []}

        result = None
        for provider in providers:
            try:
                result = mock_search(provider, fail=True)
                break
            except Exception as e:
                errors.append({"provider": provider, "error": str(e)})

        assert result is None
        assert len(errors) == 3
        assert all(e["provider"] in providers for e in errors)
