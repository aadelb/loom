"""Tests for research_loader_stats MCP tool.

Tests:
- Basic tool invocation
- Stats structure
- Tool output format
"""

from __future__ import annotations

import pytest

from loom.tools.monitoring.loader_stats import research_loader_stats
from loom.tool_loader import get_loader, LazyToolLoader


@pytest.mark.asyncio
async def test_research_loader_stats_basic() -> None:
    """Test basic invocation of research_loader_stats."""
    stats = await research_loader_stats()

    assert isinstance(stats, dict)
    assert "loaded_count" in stats
    assert "failed_count" in stats
    assert "registered_count" in stats
    assert "avg_load_time_ms" in stats
    assert "load_times_by_tool" in stats
    assert "failed_tools" in stats
    assert "cache_size_count" in stats


@pytest.mark.asyncio
async def test_research_loader_stats_types() -> None:
    """Test that loader stats have correct types."""
    stats = await research_loader_stats()

    assert isinstance(stats["loaded_count"], int)
    assert isinstance(stats["failed_count"], int)
    assert isinstance(stats["registered_count"], int)
    assert isinstance(stats["avg_load_time_ms"], (int, float))
    assert isinstance(stats["load_times_by_tool"], dict)
    assert isinstance(stats["failed_tools"], list)
    assert isinstance(stats["cache_size_count"], int)


@pytest.mark.asyncio
async def test_research_loader_stats_consistency() -> None:
    """Test that cache_size_count matches loaded_count."""
    stats = await research_loader_stats()

    # cache_size_count should equal loaded_count
    assert stats["cache_size_count"] == stats["loaded_count"]


@pytest.mark.asyncio
async def test_research_loader_stats_with_mock_data() -> None:
    """Test loader stats with manually loaded tools."""
    # Use a fresh loader for this test
    loader = LazyToolLoader()
    loader.register("test_tool_1", "loom.validators", "validate_url")
    loader.register("test_tool_2", "loom.validators", "validate_url")

    # Load one tool
    loader.load("test_tool_1")

    # Replace the global loader temporarily
    import loom.tool_loader as tl
    old_loader = tl._default_loader
    tl._default_loader = loader

    try:
        stats = await research_loader_stats()

        assert stats["registered_count"] == 2
        assert stats["loaded_count"] == 1
        assert stats["failed_count"] == 0
        assert "test_tool_1" in stats["load_times_by_tool"]
    finally:
        # Restore original loader
        tl._default_loader = old_loader


@pytest.mark.asyncio
async def test_research_loader_stats_failed_tools() -> None:
    """Test that failed tools are included in stats."""
    loader = LazyToolLoader()
    loader.register("good_tool", "loom.validators", "validate_url")
    loader.register("bad_tool", "nonexistent.module", "func")

    loader.load("good_tool")

    try:
        loader.load("bad_tool")
    except ImportError:
        pass

    # Replace the global loader temporarily
    import loom.tool_loader as tl
    old_loader = tl._default_loader
    tl._default_loader = loader

    try:
        stats = await research_loader_stats()

        assert stats["failed_count"] == 1
        assert "bad_tool" in stats["failed_tools"]
    finally:
        # Restore original loader
        tl._default_loader = old_loader
