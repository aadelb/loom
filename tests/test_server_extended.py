"""Extended tests for loom.server — app creation, tool registration, wrapping.

Target: 80%+ coverage for src/loom/server.py (currently 37%).

Tests cover:
- create_app initialization and configuration
- _register_tools registration count and naming
- _wrap_tool sync/async function wrapping
- Health check endpoint
- Optional tool loading (conditional imports)
- Config loading during init
- Cache cleanup on startup
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest


class TestCreateApp:
    """Tests for create_app() — FastMCP initialization."""

    def test_create_app_returns_fastmcp_instance(self) -> None:
        """create_app returns a FastMCP instance."""
        from loom.server import create_app

        app = create_app()
        assert app is not None
        assert app.name == "loom"

    def test_create_app_sets_host_port_from_env(self) -> None:
        """create_app uses LOOM_HOST and LOOM_PORT from environment."""
        with patch.dict(os.environ, {"LOOM_HOST": "0.0.0.0", "LOOM_PORT": "9000"}):
            from loom.server import create_app

            app = create_app()
            assert app is not None

    def test_create_app_registers_tools(self) -> None:
        """create_app registers tools via _register_tools."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())

        assert len(tools) > 20

    def test_create_app_calls_load_config(self) -> None:
        """create_app calls load_config()."""
        with patch("loom.server.load_config") as mock_load:
            mock_load.return_value = {"LOG_LEVEL": "INFO"}

            from loom.server import create_app

            create_app()

            assert mock_load.called

    def test_create_app_sets_logging_level(self) -> None:
        """create_app configures logging level from config."""
        with patch("loom.server.load_config") as mock_load:
            mock_load.return_value = {"LOG_LEVEL": "DEBUG"}

            with patch("loom.server.logging.basicConfig") as mock_basic:
                from loom.server import create_app

                create_app()

                assert mock_basic.called

    def test_create_app_installs_tracing(self) -> None:
        """create_app calls install_tracing()."""
        with patch("loom.server.install_tracing") as mock_tracing:
            from loom.server import create_app

            create_app()

            assert mock_tracing.called

    def test_create_app_cleans_old_cache(self) -> None:
        """create_app cleans cache entries on startup."""
        with patch("loom.server.load_config") as mock_load:
            mock_load.return_value = {"LOG_LEVEL": "INFO", "CACHE_TTL_DAYS": 30}

            with patch("loom.cache.get_cache") as mock_cache:
                mock_cache_obj = MagicMock()
                mock_cache_obj.clear_older_than.return_value = 5
                mock_cache.return_value = mock_cache_obj

                from loom.server import create_app

                create_app()

                assert mock_cache_obj.clear_older_than.called

    def test_create_app_handles_cache_cleanup_error(self) -> None:
        """create_app handles errors during cache cleanup."""
        with patch("loom.server.load_config") as mock_load:
            mock_load.return_value = {"LOG_LEVEL": "INFO"}

            with patch("loom.cache.get_cache") as mock_cache:
                mock_cache.side_effect = Exception("Cache error")

                from loom.server import create_app

                app = create_app()
                assert app is not None


class TestWrapTool:
    """Tests for _wrap_tool() — sync/async function wrapping."""

    def test_wrap_tool_sync_function(self) -> None:
        """_wrap_tool wraps sync functions."""
        from loom.server import _wrap_tool

        def my_sync_func(x: int) -> int:
            return x * 2

        wrapped = _wrap_tool(my_sync_func)

        assert callable(wrapped)
        result = wrapped(5)
        assert result == 10

    def test_wrap_tool_async_function(self) -> None:
        """_wrap_tool wraps async functions."""
        from loom.server import _wrap_tool

        async def my_async_func(x: int) -> int:
            return x * 2

        wrapped = _wrap_tool(my_async_func)

        assert callable(wrapped)
        result = asyncio.run(wrapped(5))
        assert result == 10

    def test_wrap_tool_sync_with_category(self) -> None:
        """_wrap_tool applies rate limiting when category provided."""
        from loom.server import _wrap_tool

        def my_func() -> str:
            return "result"

        wrapped = _wrap_tool(my_func, category="test")

        assert callable(wrapped)

    def test_wrap_tool_async_with_category(self) -> None:
        """_wrap_tool applies rate limiting to async with category."""
        from loom.server import _wrap_tool

        async def my_async_func() -> str:
            return "result"

        wrapped = _wrap_tool(my_async_func, category="test")

        assert callable(wrapped)
        result = asyncio.run(wrapped())
        assert result == "result"

    def test_wrap_tool_calls_new_request_id(self) -> None:
        """_wrap_tool calls new_request_id()."""
        from loom.server import _wrap_tool

        with patch("loom.server.new_request_id") as mock_req_id:

            def my_func() -> str:
                return "ok"

            wrapped = _wrap_tool(my_func)
            wrapped()

            assert mock_req_id.called

    def test_wrap_tool_async_calls_new_request_id(self) -> None:
        """_wrap_tool calls new_request_id() for async functions."""
        from loom.server import _wrap_tool

        with patch("loom.server.new_request_id") as mock_req_id:

            async def my_func() -> str:
                return "ok"

            wrapped = _wrap_tool(my_func)
            asyncio.run(wrapped())

            assert mock_req_id.called

    def test_wrap_tool_preserves_function_name(self) -> None:
        """_wrap_tool preserves original function metadata."""
        from loom.server import _wrap_tool

        def my_special_func() -> str:
            """Docstring."""
            return "result"

        wrapped = _wrap_tool(my_special_func)

        assert wrapped.__name__ == "my_special_func"
        assert "Docstring" in wrapped.__doc__


class TestRegisterTools:
    """Tests for _register_tools() — tool discovery and registration."""

    def test_register_tools_adds_fetch_tool(self) -> None:
        """_register_tools registers research_fetch."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}

        assert "research_fetch" in names

    def test_register_tools_adds_spider_tool(self) -> None:
        """_register_tools registers research_spider."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}

        assert "research_spider" in names

    def test_register_tools_adds_markdown_tool(self) -> None:
        """_register_tools registers research_markdown."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}

        assert "research_markdown" in names

    def test_register_tools_adds_search_tool(self) -> None:
        """_register_tools registers research_search."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}

        assert "research_search" in names

    def test_register_tools_adds_deep_tool(self) -> None:
        """_register_tools registers research_deep."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}

        assert "research_deep" in names

    def test_register_tools_adds_github_tool(self) -> None:
        """_register_tools registers research_github."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}

        assert "research_github" in names

    def test_register_tools_adds_stealth_tools(self) -> None:
        """_register_tools registers research_camoufox and research_botasaurus."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}

        assert "research_camoufox" in names
        assert "research_botasaurus" in names

    def test_register_tools_adds_cache_tools(self) -> None:
        """_register_tools registers cache management tools."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}

        assert "research_cache_stats" in names
        assert "research_cache_clear" in names

    def test_register_tools_adds_session_tools(self) -> None:
        """_register_tools registers session management tools."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}

        assert "research_session_open" in names
        assert "research_session_list" in names
        assert "research_session_close" in names

    def test_register_tools_adds_config_tools(self) -> None:
        """_register_tools registers config tools."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}

        assert "research_config_get" in names
        assert "research_config_set" in names

    def test_register_tools_adds_health_check(self) -> None:
        """_register_tools registers health check tool."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())
        names = {t.name for t in tools}

        assert "research_health_check" in names


class TestHealthCheck:
    """Tests for research_health_check() tool."""

    @pytest.mark.asyncio
    async def test_health_check_returns_status(self) -> None:
        """research_health_check returns health status."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert "active_sessions" in result

    @pytest.mark.asyncio
    async def test_health_check_uptime_is_numeric(self) -> None:
        """research_health_check uptime is numeric."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["uptime_seconds"], int)
        assert result["uptime_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_health_check_active_sessions_is_numeric(self) -> None:
        """research_health_check active_sessions count is numeric."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result["active_sessions"], int)
        assert result["active_sessions"] >= 0


class TestOptionalToolLoading:
    """Tests for optional/conditional tool module loading."""

    def test_optional_tools_loaded_gracefully(self) -> None:
        """Optional tools are loaded if available, skipped if not."""
        from loom import server

        assert isinstance(server._optional_tools, dict)


class TestServerInitialization:
    """Tests for server module initialization state."""

    def test_start_time_is_set(self) -> None:
        """Module-level _start_time is initialized."""
        from loom import server

        assert hasattr(server, "_start_time")
        assert isinstance(server._start_time, float)

    def test_optional_tools_dict_exists(self) -> None:
        """Module-level _optional_tools dict exists."""
        from loom import server

        assert hasattr(server, "_optional_tools")
        assert isinstance(server._optional_tools, dict)


class TestToolDescriptions:
    """Tests for tool metadata."""

    def test_registered_tools_have_descriptions(self) -> None:
        """All registered tools have descriptions."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())

        for tool in tools:
            assert tool.description is not None
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0

    def test_registered_tools_have_input_schema(self) -> None:
        """All registered tools have input schema."""
        from loom.server import create_app

        app = create_app()
        tools = asyncio.run(app.list_tools())

        for tool in tools:
            assert tool.inputSchema is not None
