"""Unit tests for loom.server — tool registration and app creation."""

from __future__ import annotations

import asyncio

import pytest


class TestServerCreateApp:
    """create_app() initializes correctly."""

    def test_create_app_returns_fastmcp(self) -> None:
        """create_app() returns a FastMCP instance."""
        from loom.server import create_app

        app = create_app()
        assert app is not None
        assert app.name == "loom"

    def test_create_app_registers_minimum_tools(self) -> None:
        """create_app() registers at least 30 tools."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        assert len(tools) >= 30, f"expected >= 30 tools, got {len(tools)}"

    def test_all_tool_names_follow_convention(self) -> None:
        """Every registered tool name starts with 'research_' or 'find_' or 'fetch_'."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        valid_prefixes = ("research_", "find_", "fetch_")
        for t in tools:
            assert t.name.startswith(valid_prefixes), (
                f"tool {t.name} doesn't follow naming convention"
            )

    def test_tool_names_are_unique(self) -> None:
        """No duplicate tool names."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = [t.name for t in tools]
        assert len(names) == len(set(names)), f"duplicates: {[n for n in names if names.count(n) > 1]}"

    def test_expected_tools_present(self) -> None:
        """All promised tool names are registered."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}
        expected = {
            "research_fetch",
            "research_spider",
            "research_markdown",
            "research_search",
            "research_deep",
            "research_github",
            "research_camoufox",
            "research_botasaurus",
            "research_cache_stats",
            "research_cache_clear",
            "research_session_open",
            "research_session_list",
            "research_session_close",
            "research_config_get",
            "research_config_set",
            "research_llm_summarize",
            "research_llm_extract",
            "research_llm_classify",
            "research_llm_translate",
            "research_llm_query_expand",
            "research_llm_answer",
            "research_llm_embed",
            "research_llm_chat",
            "research_health_check",
        }
        missing = expected - names
        assert not missing, f"missing tools: {missing}"
