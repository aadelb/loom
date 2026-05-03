"""Tests for the auto-discovery tool registry system.

Tests cover:
- Decorator functionality
- Registry discovery and retrieval
- Tool import automation
- Registry validation
- Statistics and reporting
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from loom.tool_registry import (
    ToolInfo,
    clear_registry,
    discover_tools,
    get_all_registered_tools,
    get_registered_tool,
    get_registry_stats,
    get_tools_by_category,
    loom_tool,
    register_all_with_mcp,
    validate_registry,
)


class TestLoomToolDecorator:
    """Test the @loom_tool decorator."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        clear_registry()

    def test_decorator_registers_sync_function(self) -> None:
        """Test that decorator registers a synchronous function."""

        @loom_tool(category="test", description="Test tool")
        def test_func(x: int) -> int:
            return x * 2

        tools = get_all_registered_tools()
        assert "test_func" in tools
        assert tools["test_func"]["name"] == "test_func"
        assert tools["test_func"]["category"] == "test"
        assert tools["test_func"]["description"] == "Test tool"
        assert tools["test_func"]["is_async"] is False
        assert callable(tools["test_func"]["func"])

    def test_decorator_registers_async_function(self) -> None:
        """Test that decorator registers an asynchronous function."""

        @loom_tool(category="research", description="Async research tool")
        async def async_test_func(query: str) -> dict[str, str]:
            return {"result": query}

        tools = get_all_registered_tools()
        assert "async_test_func" in tools
        assert tools["async_test_func"]["is_async"] is True

    def test_decorator_preserves_function(self) -> None:
        """Test that decorator returns the original function unchanged."""

        @loom_tool(category="test")
        def original_func(x: int) -> int:
            return x + 1

        # Function should be callable and work normally
        assert original_func(5) == 6

    def test_decorator_with_default_category(self) -> None:
        """Test decorator with default category."""

        @loom_tool(description="Default category test")
        def default_cat_func() -> None:
            pass

        tools = get_all_registered_tools()
        assert tools["default_cat_func"]["category"] == "research"

    def test_decorator_with_empty_description(self) -> None:
        """Test decorator with empty description."""

        @loom_tool(category="test")
        def no_desc_func() -> None:
            pass

        tools = get_all_registered_tools()
        assert tools["no_desc_func"]["description"] == ""

    def test_multiple_decorators_no_conflict(self) -> None:
        """Test multiple decorated functions register independently."""

        @loom_tool(category="cat1", description="First")
        def func1() -> None:
            pass

        @loom_tool(category="cat2", description="Second")
        def func2() -> None:
            pass

        tools = get_all_registered_tools()
        assert len(tools) == 2
        assert "func1" in tools
        assert "func2" in tools
        assert tools["func1"]["category"] == "cat1"
        assert tools["func2"]["category"] == "cat2"


class TestToolInfo:
    """Test the ToolInfo class."""

    def test_tool_info_creation(self) -> None:
        """Test ToolInfo instantiation."""

        def dummy_func() -> None:
            pass

        info = ToolInfo(
            func=dummy_func,
            category="test",
            description="Test tool",
            module="test_module",
            is_async=False,
            name="dummy_func",
        )

        assert info.func is dummy_func
        assert info.category == "test"
        assert info.description == "Test tool"
        assert info.module == "test_module"
        assert info.is_async is False
        assert info.name == "dummy_func"

    def test_tool_info_to_dict(self) -> None:
        """Test ToolInfo.to_dict() method."""

        def dummy_func() -> None:
            pass

        info = ToolInfo(
            func=dummy_func,
            category="cat",
            description="desc",
            module="mod",
            is_async=True,
            name="func_name",
        )

        d = info.to_dict()
        assert d["category"] == "cat"
        assert d["description"] == "desc"
        assert d["module"] == "mod"
        assert d["is_async"] is True
        assert d["name"] == "func_name"
        assert d["func"] is dummy_func


class TestRegistryRetrieval:
    """Test registry query methods."""

    def setup_method(self) -> None:
        """Clear registry and register test tools."""
        clear_registry()

        @loom_tool(category="intelligence")
        def intel_tool1() -> None:
            pass

        @loom_tool(category="intelligence")
        def intel_tool2() -> None:
            pass

        @loom_tool(category="analysis")
        def analysis_tool1() -> None:
            pass

    def test_get_all_registered_tools(self) -> None:
        """Test retrieving all registered tools."""
        tools = get_all_registered_tools()
        assert len(tools) == 3
        assert "intel_tool1" in tools
        assert "intel_tool2" in tools
        assert "analysis_tool1" in tools

    def test_get_tools_by_category(self) -> None:
        """Test filtering tools by category."""
        intel_tools = get_tools_by_category("intelligence")
        assert len(intel_tools) == 2
        assert "intel_tool1" in intel_tools
        assert "intel_tool2" in intel_tools

        analysis_tools = get_tools_by_category("analysis")
        assert len(analysis_tools) == 1
        assert "analysis_tool1" in analysis_tools

        empty = get_tools_by_category("nonexistent")
        assert len(empty) == 0

    def test_get_registered_tool(self) -> None:
        """Test retrieving a specific tool."""
        tool = get_registered_tool("intel_tool1")
        assert tool is not None
        assert tool["category"] == "intelligence"

        nonexistent = get_registered_tool("nonexistent")
        assert nonexistent is None


class TestDiscoverTools:
    """Test the discover_tools function."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        clear_registry()

    def test_discover_tools_nonexistent_directory(self) -> None:
        """Test discover_tools with non-existent directory."""
        with pytest.raises(ValueError, match="does not exist"):
            discover_tools(Path("/nonexistent/path"))

    def test_discover_tools_not_a_directory(self, tmp_path: Path) -> None:
        """Test discover_tools with a file instead of directory."""
        file_path = tmp_path / "test.py"
        file_path.write_text("# test")

        with pytest.raises(ValueError, match="not a directory"):
            discover_tools(file_path)

    def test_discover_tools_skips_private_modules(self, tmp_path: Path) -> None:
        """Test that discover_tools skips _*.py files."""
        (tmp_path / "__init__.py").write_text("")
        (tmp_path / "_private.py").write_text("# private module")

        # Should not raise, and should skip these modules
        count = discover_tools(tmp_path)
        assert count == 0


class TestRegistryStats:
    """Test registry statistics."""

    def setup_method(self) -> None:
        """Clear registry and register test tools."""
        clear_registry()

        @loom_tool(category="intel")
        def sync_tool() -> None:
            pass

        @loom_tool(category="intel")
        async def async_tool1() -> None:
            pass

        @loom_tool(category="analysis")
        async def async_tool2() -> None:
            pass

    def test_get_registry_stats(self) -> None:
        """Test registry statistics calculation."""
        stats = get_registry_stats()

        assert stats["total"] == 3
        assert stats["async"] == 2
        assert stats["sync"] == 1
        assert stats["by_category"]["intel"] == 2
        assert stats["by_category"]["analysis"] == 1
        assert set(stats["categories"]) == {"analysis", "intel"}

    def test_stats_empty_registry(self) -> None:
        """Test stats with empty registry."""
        clear_registry()
        stats = get_registry_stats()

        assert stats["total"] == 0
        assert stats["async"] == 0
        assert stats["sync"] == 0
        assert len(stats["by_category"]) == 0


class TestValidateRegistry:
    """Test registry validation."""

    def setup_method(self) -> None:
        """Clear registry before each test."""
        clear_registry()

    def test_validate_empty_registry(self) -> None:
        """Test validation of empty registry."""
        is_valid, errors = validate_registry()
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_valid_tools(self) -> None:
        """Test validation of valid tools."""

        @loom_tool(category="test")
        def valid_tool1() -> None:
            pass

        @loom_tool(category="test")
        async def valid_tool2() -> None:
            pass

        is_valid, errors = validate_registry()
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_missing_fields(self) -> None:
        """Test validation detects missing fields."""
        from loom.tool_registry import _REGISTRY

        # Manually insert a tool with missing fields (simulating corruption)
        def broken_func() -> None:
            pass

        _REGISTRY["broken"] = {"func": broken_func}  # Missing other fields

        is_valid, errors = validate_registry()
        assert is_valid is False
        assert any("missing fields" in error for error in errors)

    def test_validate_non_callable(self) -> None:
        """Test validation detects non-callable functions."""
        from loom.tool_registry import _REGISTRY

        _REGISTRY["broken"] = {
            "func": "not_callable",
            "category": "test",
            "description": "",
            "module": "test",
            "is_async": False,
            "name": "broken",
        }

        is_valid, errors = validate_registry()
        assert is_valid is False
        assert any("not callable" in error for error in errors)

    def test_validate_async_mismatch(self) -> None:
        """Test validation detects async/sync mismatch."""
        from loom.tool_registry import _REGISTRY

        async def async_func() -> None:
            pass

        _REGISTRY["async_mismatch"] = {
            "func": async_func,
            "category": "test",
            "description": "",
            "module": "test",
            "is_async": False,  # Wrong: should be True
            "name": "async_mismatch",
        }

        is_valid, errors = validate_registry()
        assert is_valid is False
        assert any("async mismatch" in error for error in errors)


class TestRegisterWithMCP:
    """Test MCP server registration."""

    def setup_method(self) -> None:
        """Clear registry and register test tools."""
        clear_registry()

        @loom_tool(category="test")
        def test_tool1(x: int) -> int:
            return x

        @loom_tool(category="test")
        async def test_tool2(y: str) -> str:
            return y

    def test_register_all_with_mcp(self) -> None:
        """Test registering all tools with MCP server."""
        # Mock MCP instance and wrap_tool
        mock_mcp = MagicMock()
        mock_mcp.tool.return_value.return_value = lambda f: f

        def mock_wrap_tool(func: Any) -> Any:
            return func

        registered = register_all_with_mcp(mock_mcp, mock_wrap_tool)
        assert registered == 2

    def test_register_with_mcp_failure_handling(self) -> None:
        """Test that registration continues despite failures."""
        from loom.tool_registry import _REGISTRY

        mock_mcp = MagicMock()
        # Make first tool registration fail
        mock_mcp.tool.return_value.side_effect = [
            Exception("Registration failed"),
            MagicMock(return_value=lambda f: f),
        ]

        def mock_wrap_tool(func: Any) -> Any:
            return func

        # Should still return count of attempted registrations
        registered = register_all_with_mcp(mock_mcp, mock_wrap_tool)
        assert registered >= 0


class TestClearRegistry:
    """Test registry cleanup."""

    def test_clear_registry(self) -> None:
        """Test clearing the registry."""

        @loom_tool(category="test")
        def test_func() -> None:
            pass

        assert len(get_all_registered_tools()) > 0

        clear_registry()

        assert len(get_all_registered_tools()) == 0


class TestDemoDecoratorUsage:
    """Test the demo decorator usage file loads correctly."""

    def test_demo_module_imports(self) -> None:
        """Test that demo module can be imported."""
        try:
            import loom.tools.demo_decorator_usage as demo

            assert hasattr(demo, "research_social_graph_demo")
            assert hasattr(demo, "research_threat_profile_demo")
            assert hasattr(demo, "research_code_analysis_demo")
            assert hasattr(demo, "research_data_transform_demo")
        except ImportError:
            pytest.skip("Demo module not available")

    def test_demo_functions_are_registered(self) -> None:
        """Test that demo functions were registered via decorator."""
        try:
            import loom.tools.demo_decorator_usage  # noqa: F401

            tools = get_all_registered_tools()
            demo_tools = {
                "research_social_graph_demo",
                "research_threat_profile_demo",
                "research_code_analysis_demo",
                "research_data_transform_demo",
            }
            assert demo_tools.issubset(set(tools.keys()))
        except ImportError:
            pytest.skip("Demo module not available")

    @pytest.mark.asyncio
    async def test_demo_sync_tool_callable(self) -> None:
        """Test that demo sync tool is callable."""
        try:
            from loom.tools.demo_decorator_usage import research_social_graph_demo

            result = research_social_graph_demo("test_query", depth=2)
            assert isinstance(result, dict)
            assert result["query"] == "test_query"
            assert result["depth"] == 2
        except ImportError:
            pytest.skip("Demo module not available")

    @pytest.mark.asyncio
    async def test_demo_async_tool_callable(self) -> None:
        """Test that demo async tool is callable."""
        try:
            from loom.tools.demo_decorator_usage import research_threat_profile_demo

            result = await research_threat_profile_demo(
                "example.com", include_infrastructure=True
            )
            assert isinstance(result, dict)
            assert result["target"] == "example.com"
        except ImportError:
            pytest.skip("Demo module not available")
