"""Unit tests for LLM provider cascade and availability logic."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.providers.base import LLMResponse
from loom.providers.nvidia_nim import NvidiaNimProvider
from loom.providers.openai_provider import OpenAIProvider
from loom.tools.llm import _build_provider_chain, _call_with_cascade


@pytest.fixture
def clear_env_keys():
    """Clear LLM API keys for clean testing."""
    old_nvidia = os.environ.pop("NVIDIA_NIM_API_KEY", None)
    old_openai = os.environ.pop("OPENAI_API_KEY", None)
    old_anthropic = os.environ.pop("ANTHROPIC_API_KEY", None)
    yield
    if old_nvidia:
        os.environ["NVIDIA_NIM_API_KEY"] = old_nvidia
    if old_openai:
        os.environ["OPENAI_API_KEY"] = old_openai
    if old_anthropic:
        os.environ["ANTHROPIC_API_KEY"] = old_anthropic


@pytest.fixture
def reset_providers():
    """Reset global provider cache."""
    from loom.tools import llm as llm_module

    old = llm_module._PROVIDERS.copy()
    llm_module._PROVIDERS.clear()
    yield
    llm_module._PROVIDERS.clear()
    llm_module._PROVIDERS.update(old)


class TestBuildProviderChain:
    """Tests for _build_provider_chain() function."""

    def test_build_chain_respects_config_order(
        self, clear_env_keys: None, reset_providers: None
    ) -> None:
        """Verify chain respects CONFIG["LLM_CASCADE_ORDER"]."""
        os.environ["NVIDIA_NIM_API_KEY"] = "nvapi-test-123"
        os.environ["OPENAI_API_KEY"] = "sk-test-456"
        with patch("loom.tools.llm.CONFIG") as m:
            m.get.side_effect = lambda k, d: (
                ["openai", "nvidia"] if k == "LLM_CASCADE_ORDER" else d
            )
            m.__bool__.return_value = True
            chain = _build_provider_chain()
            assert len(chain) >= 2
            assert chain[0].name == "openai"
            assert chain[1].name == "nvidia"

    def test_build_chain_with_override_returns_single(
        self, clear_env_keys: None, reset_providers: None
    ) -> None:
        """Verify provider_override returns single-item chain."""
        os.environ["NVIDIA_NIM_API_KEY"] = "nvapi-test-123"
        with patch("loom.tools.llm.CONFIG") as m:
            m.get.return_value = None
            m.__bool__.return_value = True
            chain = _build_provider_chain(override="nvidia")
            assert len(chain) == 1
            assert chain[0].name == "nvidia"

    def test_build_chain_skips_unavailable(
        self, clear_env_keys: None, reset_providers: None
    ) -> None:
        """Verify cascade skips unavailable providers."""
        os.environ["OPENAI_API_KEY"] = "sk-test-456"
        os.environ.pop("NVIDIA_NIM_API_KEY", None)
        with patch("loom.tools.llm.CONFIG") as m:
            m.get.side_effect = lambda k, d: (
                ["nvidia", "openai"] if k == "LLM_CASCADE_ORDER" else d
            )
            m.__bool__.return_value = True
            chain = _build_provider_chain()
            assert any(p.name == "openai" for p in chain)


class TestCallWithCascade:
    """Tests for _call_with_cascade() async function."""

    @pytest.mark.asyncio
    async def test_cascade_falls_through_on_failure(
        self, clear_env_keys: None, reset_providers: None
    ) -> None:
        """First provider fails, second succeeds."""
        os.environ["NVIDIA_NIM_API_KEY"] = "nvapi-test-1"
        os.environ["OPENAI_API_KEY"] = "sk-test-2"
        with patch("loom.tools.llm._build_provider_chain") as mb:
            with patch("loom.tools.llm._get_cost_tracker") as mct:
                mct.return_value.add_cost = MagicMock()
                m_nvidia = MagicMock()
                m_nvidia.name = "nvidia"
                m_nvidia.available.return_value = True
                m_nvidia.chat = AsyncMock(side_effect=TimeoutError())
                m_openai = MagicMock()
                m_openai.name = "openai"
                m_openai.available.return_value = True
                m_openai.chat = AsyncMock(
                    return_value=LLMResponse(
                        text="OpenAI OK", model="gpt-5-mini", input_tokens=100,
                        output_tokens=50, cost_usd=0.05, latency_ms=200,
                        provider="openai", finish_reason="stop"
                    )
                )
                mb.return_value = [m_nvidia, m_openai]
                with patch("loom.tools.llm.CONFIG") as mc:
                    mc.get.return_value = None
                    mc.__bool__.return_value = True
                    r = await _call_with_cascade([{"role": "user", "content": "test"}])
                    assert r.provider == "openai"

    @pytest.mark.asyncio
    async def test_cascade_all_fail_raises_runtime_error(
        self, clear_env_keys: None, reset_providers: None
    ) -> None:
        """All providers fail → RuntimeError with sanitized message."""
        os.environ["NVIDIA_NIM_API_KEY"] = "nvapi-test-1"
        os.environ["OPENAI_API_KEY"] = "sk-test-2"
        with patch("loom.tools.llm._build_provider_chain") as mb:
            m_nvidia = MagicMock()
            m_nvidia.name = "nvidia"
            m_nvidia.available.return_value = True
            m_nvidia.chat = AsyncMock(side_effect=TimeoutError())
            m_openai = MagicMock()
            m_openai.name = "openai"
            m_openai.available.return_value = True
            m_openai.chat = AsyncMock(
                side_effect=Exception("Error sk-test-key-secret")
            )
            mb.return_value = [m_nvidia, m_openai]
            with patch("loom.tools.llm.CONFIG") as mc:
                mc.get.return_value = None
                mc.__bool__.return_value = True
                with pytest.raises(RuntimeError) as e:
                    await _call_with_cascade([{"role": "user", "content": "test"}])
                assert "sk-test-key" not in str(e.value)
                assert "all providers failed" in str(e.value)

    @pytest.mark.asyncio
    async def test_cascade_respects_provider_override(
        self, clear_env_keys: None, reset_providers: None
    ) -> None:
        """provider_override forces a single provider."""
        os.environ["NVIDIA_NIM_API_KEY"] = "nvapi-test-1"
        with patch("loom.tools.llm._build_provider_chain") as mb:
            with patch("loom.tools.llm._get_cost_tracker") as mct:
                mct.return_value.add_cost = MagicMock()
                m_nvidia = MagicMock()
                m_nvidia.name = "nvidia"
                m_nvidia.available.return_value = True
                m_nvidia.chat = AsyncMock(
                    return_value=LLMResponse(
                        text="NVIDIA OK", model="meta/llama-4", input_tokens=100,
                        output_tokens=50, cost_usd=0.0, latency_ms=150,
                        provider="nvidia", finish_reason="stop"
                    )
                )
                mb.return_value = [m_nvidia]
                with patch("loom.tools.llm.CONFIG") as mc:
                    mc.get.return_value = None
                    mc.__bool__.return_value = True
                    r = await _call_with_cascade(
                        [{"role": "user", "content": "test"}],
                        provider_override="nvidia"
                    )
                    assert r.provider == "nvidia"
                    mb.assert_called_once_with(override="nvidia")


class TestNvidiaNimAvailable:
    """Tests for NvidiaNimProvider.available()."""

    def test_nvidia_available_with_key(self, clear_env_keys: None) -> None:
        """available() True with API key set."""
        os.environ["NVIDIA_NIM_API_KEY"] = "nvapi-test-key-123"
        assert NvidiaNimProvider().available() is True

    def test_nvidia_unavailable_without_key(self, clear_env_keys: None) -> None:
        """available() False without API key."""
        os.environ.pop("NVIDIA_NIM_API_KEY", None)
        assert NvidiaNimProvider().available() is False

    def test_nvidia_unavailable_with_whitespace_key(
        self, clear_env_keys: None
    ) -> None:
        """available() False for whitespace-only keys (CRITICAL #2)."""
        os.environ["NVIDIA_NIM_API_KEY"] = "  "
        assert NvidiaNimProvider().available() is False

    def test_nvidia_unavailable_with_empty_string(
        self, clear_env_keys: None
    ) -> None:
        """available() False for empty string."""
        os.environ["NVIDIA_NIM_API_KEY"] = ""
        assert NvidiaNimProvider().available() is False


class TestOpenAIAvailable:
    """Tests for OpenAIProvider.available()."""

    def test_openai_available_with_key(self, clear_env_keys: None) -> None:
        """available() True with API key set."""
        os.environ["OPENAI_API_KEY"] = "sk-test-key-123"
        assert OpenAIProvider().available() is True

    def test_openai_unavailable_without_key(self, clear_env_keys: None) -> None:
        """available() False without API key."""
        os.environ.pop("OPENAI_API_KEY", None)
        assert OpenAIProvider().available() is False

    def test_openai_unavailable_with_empty_string(
        self, clear_env_keys: None
    ) -> None:
        """available() False for empty string."""
        os.environ["OPENAI_API_KEY"] = ""
        assert OpenAIProvider().available() is False

    def test_openai_unavailable_with_whitespace_key(
        self, clear_env_keys: None
    ) -> None:
        """available() False for whitespace-only keys (CRITICAL #2)."""
        os.environ["OPENAI_API_KEY"] = "  \t\n  "
        assert OpenAIProvider().available() is False
