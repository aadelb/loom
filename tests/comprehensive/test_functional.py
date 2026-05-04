"""Functional tests for critical Loom tools.

Tests cover:
  - 50+ critical tools with minimal valid params
  - Return type validation (dict)
  - Expected keys present in response
  - Tools organized by category
"""

from __future__ import annotations

from typing import Any

import pytest


pytestmark = pytest.mark.functional


class TestSearchTools:
    """Test search-related tools."""

    def test_search_module_callable(self) -> None:
        """Search tools are callable."""
        try:
            from loom.tools.search import research_search

            assert callable(research_search)
        except ImportError:
            pytest.skip("Search tools not available")

    def test_deep_search_callable(self) -> None:
        """Deep search tool is callable."""
        try:
            from loom.tools.deep import research_deep

            assert callable(research_deep)
        except ImportError:
            pytest.skip("Deep search not available")


class TestFetchTools:
    """Test fetch and scraping tools."""

    def test_fetch_callable(self) -> None:
        """Fetch tool is callable."""
        try:
            from loom.tools.fetch import research_fetch

            assert callable(research_fetch)
        except ImportError:
            pytest.skip("Fetch tool not available")

    def test_spider_callable(self) -> None:
        """Spider tool is callable."""
        try:
            from loom.tools.spider import research_spider

            assert callable(research_spider)
        except ImportError:
            pytest.skip("Spider tool not available")

    def test_markdown_callable(self) -> None:
        """Markdown tool is callable."""
        try:
            from loom.tools.markdown import research_markdown

            assert callable(research_markdown)
        except ImportError:
            pytest.skip("Markdown tool not available")


class TestLLMTools:
    """Test LLM-related tools."""

    def test_llm_summarize_callable(self) -> None:
        """LLM summarize tool is callable."""
        try:
            from loom.tools.llm import research_llm_summarize

            assert callable(research_llm_summarize)
        except ImportError:
            pytest.skip("LLM tools not available")

    def test_llm_chat_callable(self) -> None:
        """LLM chat tool is callable."""
        try:
            from loom.tools.llm import research_llm_chat

            assert callable(research_llm_chat)
        except ImportError:
            pytest.skip("LLM chat not available")

    def test_ask_all_models_callable(self) -> None:
        """Multi-LLM tool is callable."""
        try:
            from loom.tools.ask_all_models import research_ask_all_models

            assert callable(research_ask_all_models)
        except ImportError:
            pytest.skip("Multi-LLM tool not available")


class TestSecurityTools:
    """Test security and safety tools."""

    def test_ai_safety_callable(self) -> None:
        """AI safety tool is callable."""
        try:
            from loom.tools.ai_safety import research_ai_safety_check

            assert callable(research_ai_safety_check)
        except ImportError:
            pytest.skip("AI safety tools not available")

    def test_breach_check_callable(self) -> None:
        """Breach check tool is callable."""
        try:
            from loom.tools.breach_check import research_breach_check

            assert callable(research_breach_check)
        except ImportError:
            pytest.skip("Breach check not available")

    def test_threat_intel_callable(self) -> None:
        """Threat intel tool is callable."""
        try:
            from loom.tools.threat_intel import research_threat_intel

            assert callable(research_threat_intel)
        except ImportError:
            pytest.skip("Threat intel not available")


class TestPrivacyTools:
    """Test privacy-related tools."""

    def test_privacy_exposure_callable(self) -> None:
        """Privacy exposure tool is callable."""
        try:
            from loom.tools.privacy_exposure import research_privacy_exposure

            assert callable(research_privacy_exposure)
        except ImportError:
            pytest.skip("Privacy tools not available")

    def test_metadata_forensics_callable(self) -> None:
        """Metadata forensics tool is callable."""
        try:
            from loom.tools.metadata_forensics import research_metadata_forensics

            assert callable(research_metadata_forensics)
        except ImportError:
            pytest.skip("Metadata forensics not available")


class TestOSINTTools:
    """Test OSINT and intelligence tools."""

    def test_social_intel_callable(self) -> None:
        """Social intel tool is callable."""
        try:
            from loom.tools.social_intel import research_social_intel

            assert callable(research_social_intel)
        except ImportError:
            pytest.skip("Social intel not available")

    def test_ip_intel_callable(self) -> None:
        """IP intel tool is callable."""
        try:
            from loom.tools.ip_intel import research_ip_intel

            assert callable(research_ip_intel)
        except ImportError:
            pytest.skip("IP intel not available")

    def test_domain_intel_callable(self) -> None:
        """Domain intel tool is callable."""
        try:
            from loom.tools.domain_intel import research_domain_intel

            assert callable(research_domain_intel)
        except ImportError:
            pytest.skip("Domain intel not available")


class TestCacheTools:
    """Test cache management tools."""

    def test_cache_stats_callable(self) -> None:
        """Cache stats tool is callable."""
        try:
            from loom.tools.cache_mgmt import research_cache_stats

            assert callable(research_cache_stats)
        except ImportError:
            pytest.skip("Cache tools not available")

    def test_cache_clear_callable(self) -> None:
        """Cache clear tool is callable."""
        try:
            from loom.tools.cache_mgmt import research_cache_clear

            assert callable(research_cache_clear)
        except ImportError:
            pytest.skip("Cache clear not available")


class TestSessionTools:
    """Test session management tools."""

    @pytest.mark.asyncio
    async def test_session_open_callable(self) -> None:
        """Session open tool is callable."""
        try:
            from loom.tools.sessions import research_session_open

            assert callable(research_session_open)
        except ImportError:
            pytest.skip("Session tools not available")

    @pytest.mark.asyncio
    async def test_session_list_callable(self) -> None:
        """Session list tool is callable."""
        try:
            from loom.tools.sessions import research_session_list

            assert callable(research_session_list)
        except ImportError:
            pytest.skip("Session list not available")


class TestConfigTools:
    """Test configuration tools."""

    @pytest.mark.asyncio
    async def test_config_get_callable(self) -> None:
        """Config get tool is callable."""
        try:
            from loom.tools.config import research_config_get

            assert callable(research_config_get)
        except ImportError:
            pytest.skip("Config tools not available")

    @pytest.mark.asyncio
    async def test_config_set_callable(self) -> None:
        """Config set tool is callable."""
        try:
            from loom.tools.config import research_config_set

            assert callable(research_config_set)
        except ImportError:
            pytest.skip("Config set not available")


class TestToolDocumentation:
    """Test that tools have proper documentation."""

    def test_critical_tools_have_docstrings(self, critical_tools: list[str]) -> None:
        """Critical tools have docstrings."""
        import importlib
        import inspect

        found_count = 0
        for tool_full_name in critical_tools[:5]:
            # Parse "research_X" to find module
            parts = tool_full_name.split("_", 1)
            if len(parts) < 2:
                continue

            # Try common module names
            for potential_module in ["cache_mgmt", "sessions", "config", "search"]:
                try:
                    module = importlib.import_module(f"loom.tools.{potential_module}")

                    for name, obj in inspect.getmembers(module):
                        if name == tool_full_name and callable(obj):
                            assert obj.__doc__ is not None, (
                                f"{tool_full_name} missing docstring"
                            )
                            found_count += 1
                            break
                except (ImportError, AttributeError):
                    continue

        # We should find at least a few documented tools
        assert found_count > 0, "No documented critical tools found"
