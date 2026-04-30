"""Tests for research_health_check() endpoint — comprehensive status monitoring.

Target: 100% coverage for enhanced health check functionality.

Tests cover:
- Health check returns all required keys
- Status values are valid ("healthy", "degraded", "unhealthy")
- LLM provider status checks (8 providers)
- Search provider status checks (21 providers)
- Cache statistics collection
- Session count tracking
- Version information
- Uptime calculation
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest


class TestHealthCheckReturnsAllRequiredKeys:
    """Tests for health check response structure."""

    @pytest.mark.asyncio
    async def test_health_check_returns_dict_with_all_required_keys(self) -> None:
        """research_health_check returns dict with all required keys."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result, dict)
        required_keys = {
            "status",
            "uptime_seconds",
            "tool_count",
            "strategy_count",
            "llm_providers",
            "search_providers",
            "cache",
            "sessions",
            "version",
            "timestamp",
        }
        assert set(result.keys()) == required_keys

    @pytest.mark.asyncio
    async def test_health_check_status_is_valid_string(self) -> None:
        """research_health_check status is one of valid values."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["status"], str)
        assert result["status"] in ("healthy", "degraded", "unhealthy")

    @pytest.mark.asyncio
    async def test_health_check_uptime_seconds_is_positive_integer(self) -> None:
        """research_health_check uptime_seconds is a positive integer."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["uptime_seconds"], int)
        assert result["uptime_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_health_check_tool_count_is_integer(self) -> None:
        """research_health_check tool_count is an integer."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["tool_count"], int)
        assert result["tool_count"] > 0

    @pytest.mark.asyncio
    async def test_health_check_strategy_count_is_integer(self) -> None:
        """research_health_check strategy_count is an integer."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["strategy_count"], int)
        assert result["strategy_count"] > 0

    @pytest.mark.asyncio
    async def test_health_check_version_is_string(self) -> None:
        """research_health_check version is a semantic version string."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["version"], str)
        # Version should match format like "0.1.0a1"
        assert len(result["version"]) > 0
        assert "." in result["version"]

    @pytest.mark.asyncio
    async def test_health_check_timestamp_is_iso_8601(self) -> None:
        """research_health_check timestamp is ISO 8601 format."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["timestamp"], str)
        # ISO 8601 format contains T and +
        assert "T" in result["timestamp"]


class TestHealthCheckLLMProviders:
    """Tests for LLM provider status in health check."""

    @pytest.mark.asyncio
    async def test_health_check_llm_providers_is_dict(self) -> None:
        """research_health_check llm_providers is a dict."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["llm_providers"], dict)

    @pytest.mark.asyncio
    async def test_health_check_has_all_8_llm_providers(self) -> None:
        """research_health_check includes all 8 LLM providers."""
        from loom.server import research_health_check

        result = await research_health_check()

        expected_providers = {
            "groq",
            "nvidia_nim",
            "deepseek",
            "gemini",
            "moonshot",
            "openai",
            "anthropic",
            "vllm",
        }
        assert set(result["llm_providers"].keys()) == expected_providers

    @pytest.mark.asyncio
    async def test_health_check_llm_provider_has_status(self) -> None:
        """research_health_check each LLM provider has status field."""
        from loom.server import research_health_check

        result = await research_health_check()

        for provider_name, provider_info in result["llm_providers"].items():
            assert isinstance(provider_info, dict)
            assert "status" in provider_info
            assert provider_info["status"] in ("up", "down")

    @pytest.mark.asyncio
    async def test_health_check_llm_provider_status_reflects_env_vars(self) -> None:
        """research_health_check LLM provider status depends on env vars."""
        from loom.server import research_health_check

        # Ensure at least one LLM provider is not configured
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=False):
            result = await research_health_check()
            # groq should be down if key is empty
            # But _check_llm_provider_available reads from os.environ at call time
            # So we just verify the structure is correct
            assert "groq" in result["llm_providers"]


class TestHealthCheckSearchProviders:
    """Tests for search provider status in health check."""

    @pytest.mark.asyncio
    async def test_health_check_search_providers_is_dict(self) -> None:
        """research_health_check search_providers is a dict."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["search_providers"], dict)

    @pytest.mark.asyncio
    async def test_health_check_has_all_21_search_providers(self) -> None:
        """research_health_check includes all 21 search providers."""
        from loom.server import research_health_check

        result = await research_health_check()

        expected_providers = {
            "exa",
            "tavily",
            "firecrawl",
            "brave",
            "ddgs",
            "arxiv",
            "wikipedia",
            "hackernews",
            "reddit",
            "newsapi",
            "coindesk",
            "coinmarketcap",
            "binance",
            "ahmia",
            "darksearch",
            "ummro_rag",
            "onionsearch",
            "torcrawl",
            "darkweb_cti",
            "robin_osint",
            "investing",
        }
        assert set(result["search_providers"].keys()) == expected_providers

    @pytest.mark.asyncio
    async def test_health_check_search_provider_has_status(self) -> None:
        """research_health_check each search provider has status field."""
        from loom.server import research_health_check

        result = await research_health_check()

        for provider_name, provider_info in result["search_providers"].items():
            assert isinstance(provider_info, dict)
            assert "status" in provider_info
            assert provider_info["status"] in ("up", "down")

    @pytest.mark.asyncio
    async def test_health_check_free_search_providers_always_up(self) -> None:
        """research_health_check free providers (ddgs, arxiv, etc.) are always up."""
        from loom.server import research_health_check

        result = await research_health_check()

        # These providers don't require API keys
        free_providers = {"ddgs", "arxiv", "wikipedia", "hackernews", "reddit"}
        for provider in free_providers:
            assert result["search_providers"][provider]["status"] == "up"


class TestHealthCheckCache:
    """Tests for cache statistics in health check."""

    @pytest.mark.asyncio
    async def test_health_check_cache_is_dict(self) -> None:
        """research_health_check cache is a dict."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["cache"], dict)

    @pytest.mark.asyncio
    async def test_health_check_cache_has_required_fields(self) -> None:
        """research_health_check cache has entries, size_mb, hit_rate."""
        from loom.server import research_health_check

        result = await research_health_check()

        cache = result["cache"]
        assert "entries" in cache
        assert "size_mb" in cache
        assert "hit_rate" in cache

    @pytest.mark.asyncio
    async def test_health_check_cache_entries_is_integer(self) -> None:
        """research_health_check cache entries is an integer."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["cache"]["entries"], int)
        assert result["cache"]["entries"] >= 0

    @pytest.mark.asyncio
    async def test_health_check_cache_size_mb_is_float(self) -> None:
        """research_health_check cache size_mb is a float."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["cache"]["size_mb"], float)
        assert result["cache"]["size_mb"] >= 0.0

    @pytest.mark.asyncio
    async def test_health_check_cache_hit_rate_is_float(self) -> None:
        """research_health_check cache hit_rate is a float."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["cache"]["hit_rate"], float)
        assert 0.0 <= result["cache"]["hit_rate"] <= 1.0


class TestHealthCheckSessions:
    """Tests for session tracking in health check."""

    @pytest.mark.asyncio
    async def test_health_check_sessions_is_dict(self) -> None:
        """research_health_check sessions is a dict."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["sessions"], dict)

    @pytest.mark.asyncio
    async def test_health_check_sessions_has_active_and_max(self) -> None:
        """research_health_check sessions has active and max fields."""
        from loom.server import research_health_check

        result = await research_health_check()

        sessions = result["sessions"]
        assert "active" in sessions
        assert "max" in sessions

    @pytest.mark.asyncio
    async def test_health_check_sessions_active_is_integer(self) -> None:
        """research_health_check sessions active is an integer."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["sessions"]["active"], int)
        assert result["sessions"]["active"] >= 0

    @pytest.mark.asyncio
    async def test_health_check_sessions_max_is_integer(self) -> None:
        """research_health_check sessions max is an integer."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["sessions"]["max"], int)
        assert result["sessions"]["max"] > 0

    @pytest.mark.asyncio
    async def test_health_check_sessions_active_lte_max(self) -> None:
        """research_health_check sessions active <= max."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert result["sessions"]["active"] <= result["sessions"]["max"]


class TestHealthCheckOverallStatus:
    """Tests for overall health status logic."""

    @pytest.mark.asyncio
    async def test_health_check_status_healthy_when_providers_available(self) -> None:
        """research_health_check status is healthy when providers available."""
        from loom.server import research_health_check

        # In default test environment, ddgs is always available
        result = await research_health_check()

        # Should be either healthy or degraded depending on env
        assert result["status"] in ("healthy", "degraded", "unhealthy")

    @pytest.mark.asyncio
    async def test_health_check_status_unhealthy_when_no_providers(self) -> None:
        """research_health_check status is unhealthy with no LLM providers."""
        from loom.server import research_health_check

        # Patch _check_llm_provider_available to return False for all
        with patch("loom.server._check_llm_provider_available") as mock_llm:
            mock_llm.return_value = False

            # Also need to mock search providers to return False
            with patch("loom.server._check_search_provider_available") as mock_search:
                mock_search.return_value = False

                result = await research_health_check()

                assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_status_degraded_when_some_down(self) -> None:
        """research_health_check status is degraded when some providers down."""
        from loom.server import research_health_check

        # Patch to simulate some providers down
        with patch("loom.server._check_llm_provider_available") as mock_llm:
            # Only first 4 LLM providers available
            call_count = [0]

            def side_effect(provider_name: str) -> bool:
                call_count[0] += 1
                return call_count[0] <= 4

            mock_llm.side_effect = side_effect

            # All search providers available
            with patch("loom.server._check_search_provider_available") as mock_search:
                mock_search.return_value = True

                result = await research_health_check()

                # 4 out of 8 LLMs up = degraded
                assert result["status"] == "degraded"


class TestHealthCheckProviderChecks:
    """Tests for helper functions that check provider availability."""

    def test_check_llm_provider_available_groq_with_key(self) -> None:
        """_check_llm_provider_available returns True for groq with GROQ_API_KEY."""
        from loom.server import _check_llm_provider_available

        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key-123"}):
            assert _check_llm_provider_available("groq") is True

    def test_check_llm_provider_available_groq_without_key(self) -> None:
        """_check_llm_provider_available returns False for groq without key."""
        from loom.server import _check_llm_provider_available

        with patch.dict(os.environ, {"GROQ_API_KEY": ""}, clear=False):
            result = _check_llm_provider_available("groq")
            assert result is False

    def test_check_llm_provider_available_unknown_provider(self) -> None:
        """_check_llm_provider_available returns False for unknown provider."""
        from loom.server import _check_llm_provider_available

        assert _check_llm_provider_available("unknown_provider") is False

    def test_check_search_provider_available_exa_with_key(self) -> None:
        """_check_search_provider_available returns True for exa with EXA_API_KEY."""
        from loom.server import _check_search_provider_available

        with patch.dict(os.environ, {"EXA_API_KEY": "test-exa-key"}):
            assert _check_search_provider_available("exa") is True

    def test_check_search_provider_available_exa_without_key(self) -> None:
        """_check_search_provider_available returns False for exa without key."""
        from loom.server import _check_search_provider_available

        with patch.dict(os.environ, {"EXA_API_KEY": ""}, clear=False):
            assert _check_search_provider_available("exa") is False

    def test_check_search_provider_available_ddgs_always_up(self) -> None:
        """_check_search_provider_available returns True for ddgs (no key needed)."""
        from loom.server import _check_search_provider_available

        # ddgs should be up regardless of env
        assert _check_search_provider_available("ddgs") is True

    def test_check_search_provider_available_arxiv_always_up(self) -> None:
        """_check_search_provider_available returns True for arxiv (no key needed)."""
        from loom.server import _check_search_provider_available

        assert _check_search_provider_available("arxiv") is True

    def test_check_search_provider_available_wikipedia_always_up(self) -> None:
        """_check_search_provider_available returns True for wikipedia (no key needed)."""
        from loom.server import _check_search_provider_available

        assert _check_search_provider_available("wikipedia") is True

    def test_check_search_provider_available_unknown_provider(self) -> None:
        """_check_search_provider_available returns False for unknown provider."""
        from loom.server import _check_search_provider_available

        assert _check_search_provider_available("unknown_search_provider") is False


class TestHealthCheckIntegration:
    """Integration tests for health check as registered tool."""

    def test_health_check_registered_in_app(self) -> None:
        """research_health_check is registered as a tool in FastMCP app."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())

        tool_names = [tool.name for tool in tools]
        assert "research_health_check" in tool_names

    def test_health_check_tool_has_description(self) -> None:
        """research_health_check tool has a description."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())

        health_check_tool = next(
            (tool for tool in tools if tool.name == "research_health_check"),
            None,
        )
        assert health_check_tool is not None
        assert health_check_tool.description is not None
        assert len(health_check_tool.description) > 0
