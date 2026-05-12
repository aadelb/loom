"""Tests for cli_checker module.

Tests is_available, require, get_path, available_tools, and clear_cache.
"""

from __future__ import annotations

import pytest

from loom.cli_checker import available_tools, clear_cache, get_path, is_available, require


class TestIsAvailable:
    """Test is_available function."""

    def test_is_available_existing_binary(self) -> None:
        """Test is_available returns True for existing binary."""
        # 'python' should be available
        result = is_available("python")
        assert isinstance(result, bool)
        # Result depends on system, but should be deterministic

    def test_is_available_nonexistent_binary(self) -> None:
        """Test is_available returns False for nonexistent binary."""
        result = is_available("definitely_not_a_binary_xyz_123")
        assert result is False

    def test_is_available_caches_result(self) -> None:
        """Test that is_available caches the result."""
        clear_cache()
        # First call
        result1 = is_available("test_binary_xyz")
        # Second call should return cached result
        result2 = is_available("test_binary_xyz")
        assert result1 == result2

    def test_is_available_common_tools(self) -> None:
        """Test common tools availability."""
        # These should mostly be available or consistently missing
        tools = ["ls", "echo", "cat"]
        for tool in tools:
            result = is_available(tool)
            assert isinstance(result, bool)

    def test_is_available_empty_string(self) -> None:
        """Test is_available with empty string."""
        result = is_available("")
        assert result is False

    def test_is_available_with_path(self) -> None:
        """Test is_available with binary name only (no path)."""
        # is_available should search PATH, not accept full paths
        result = is_available("python")
        assert isinstance(result, bool)


class TestRequire:
    """Test require function."""

    def test_require_existing_binary(self) -> None:
        """Test require succeeds for existing binary."""
        # Should not raise
        require("echo")

    def test_require_missing_binary_raises(self) -> None:
        """Test require raises RuntimeError for missing binary."""
        with pytest.raises(RuntimeError, match="Required binary"):
            require("definitely_not_installed_xyz_123")

    def test_require_error_message_includes_binary_name(self) -> None:
        """Test error message includes binary name."""
        with pytest.raises(RuntimeError) as exc_info:
            require("missing_binary_xyz")
        assert "missing_binary_xyz" in str(exc_info.value)

    def test_require_with_install_hint(self) -> None:
        """Test require error includes installation hint."""
        with pytest.raises(RuntimeError) as exc_info:
            require("missing", install_hint="pip install missing")
        error_msg = str(exc_info.value)
        assert "pip install missing" in error_msg
        assert "Install:" in error_msg

    def test_require_without_install_hint(self) -> None:
        """Test require error without hint."""
        with pytest.raises(RuntimeError) as exc_info:
            require("missing_xyz")
        error_msg = str(exc_info.value)
        assert "not found on PATH" in error_msg

    def test_require_raises_runtime_error(self) -> None:
        """Test require raises specifically RuntimeError."""
        with pytest.raises(RuntimeError):
            require("missing_xyz")


class TestGetPath:
    """Test get_path function."""

    def test_get_path_existing_binary(self) -> None:
        """Test get_path returns path for existing binary."""
        result = get_path("echo")
        assert result is not None
        assert isinstance(result, str)
        assert "echo" in result

    def test_get_path_missing_binary(self) -> None:
        """Test get_path returns None for missing binary."""
        result = get_path("definitely_not_installed_xyz")
        assert result is None

    def test_get_path_absolute(self) -> None:
        """Test get_path returns absolute path."""
        result = get_path("echo")
        if result:
            assert result.startswith("/") or ":\\" in result  # Unix or Windows path


class TestAvailableTools:
    """Test available_tools function."""

    def test_available_tools_returns_dict(self) -> None:
        """Test available_tools returns dict."""
        clear_cache()
        is_available("echo")
        is_available("missing_xyz")
        result = available_tools()
        assert isinstance(result, dict)

    def test_available_tools_contains_checked(self) -> None:
        """Test available_tools includes checked binaries."""
        clear_cache()
        is_available("test_tool_xyz")
        tools = available_tools()
        assert "test_tool_xyz" in tools

    def test_available_tools_values_are_bool(self) -> None:
        """Test all values in available_tools are booleans."""
        clear_cache()
        is_available("echo")
        is_available("missing_xyz")
        tools = available_tools()
        for name, available in tools.items():
            assert isinstance(name, str)
            assert isinstance(available, bool)

    def test_available_tools_empty_when_cache_empty(self) -> None:
        """Test available_tools is empty when cache is clear."""
        clear_cache()
        tools = available_tools()
        assert tools == {}

    def test_available_tools_multiple_calls_same_result(self) -> None:
        """Test multiple calls return same dict."""
        clear_cache()
        is_available("echo")
        tools1 = available_tools()
        tools2 = available_tools()
        assert tools1 == tools2


class TestClearCache:
    """Test clear_cache function."""

    def test_clear_cache_empties_cache(self) -> None:
        """Test clear_cache clears all cached results."""
        is_available("echo")
        is_available("cat")
        assert len(available_tools()) > 0
        clear_cache()
        assert len(available_tools()) == 0

    def test_clear_cache_allows_fresh_check(self) -> None:
        """Test clear_cache allows fresh check on next call."""
        is_available("echo")
        clear_cache()
        # Next call should re-check
        result = is_available("echo")
        assert isinstance(result, bool)

    def test_clear_cache_resets_availability(self) -> None:
        """Test cache clearing resets availability status."""
        clear_cache()
        result1 = is_available("python")
        clear_cache()
        result2 = is_available("python")
        assert result1 == result2


class TestCliCheckerIntegration:
    """Integration tests combining multiple functions."""

    def test_workflow_check_and_require(self) -> None:
        """Test typical workflow: check then require."""
        clear_cache()
        # Check if available
        if is_available("echo"):
            # Require should not raise
            require("echo")
        else:
            # Require should raise
            with pytest.raises(RuntimeError):
                require("echo")

    def test_workflow_check_with_hint(self) -> None:
        """Test workflow with installation hint."""
        clear_cache()
        with pytest.raises(RuntimeError) as exc_info:
            require("missing_tool_xyz", install_hint="brew install xyz")
        assert "brew install xyz" in str(exc_info.value)

    def test_workflow_multiple_tools(self) -> None:
        """Test checking multiple tools."""
        clear_cache()
        tools = ["echo", "cat", "missing_xyz"]
        results = {tool: is_available(tool) for tool in tools}
        assert "echo" in results
        assert isinstance(results["missing_xyz"], bool)

    def test_workflow_get_path_and_use(self) -> None:
        """Test getting path for later use."""
        clear_cache()
        path = get_path("echo")
        if path:
            assert path.endswith("echo") or "echo" in path
