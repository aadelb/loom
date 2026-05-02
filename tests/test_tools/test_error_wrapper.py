"""Tests for error_wrapper decorator and error tracking tools."""

from __future__ import annotations

import asyncio
import pytest

from loom.tools.error_wrapper import (
    safe_tool_call,
    research_error_stats,
    research_error_clear,
)


@pytest.mark.asyncio
async def test_safe_tool_call_async_success():
    """Test safe_tool_call decorator with successful async function."""

    @safe_tool_call
    async def successful_async_tool(x: int, y: int) -> int:
        return x + y

    result = await successful_async_tool(3, 4)
    assert result == 7


@pytest.mark.asyncio
async def test_safe_tool_call_async_exception():
    """Test safe_tool_call decorator catches async exceptions."""

    @safe_tool_call
    async def failing_async_tool(x: int) -> int:
        raise ValueError("Test error message")

    result = await failing_async_tool(1)
    assert isinstance(result, dict)
    assert result["error"] == "Test error message"
    assert result["error_type"] == "ValueError"
    assert result["tool"] == "failing_async_tool"
    assert "timestamp" in result
    assert "traceback" in result


def test_safe_tool_call_sync_success():
    """Test safe_tool_call decorator with successful sync function."""

    @safe_tool_call
    def successful_sync_tool(x: int, y: int) -> int:
        return x * y

    result = successful_sync_tool(3, 4)
    assert result == 12


def test_safe_tool_call_sync_exception():
    """Test safe_tool_call decorator catches sync exceptions."""

    @safe_tool_call
    def failing_sync_tool(x: int) -> int:
        raise RuntimeError("Sync error")

    result = failing_sync_tool(1)
    assert isinstance(result, dict)
    assert result["error"] == "Sync error"
    assert result["error_type"] == "RuntimeError"
    assert result["tool"] == "failing_sync_tool"


@pytest.mark.asyncio
async def test_error_stats_empty():
    """Test research_error_stats with no errors recorded."""
    await research_error_clear()
    result = await research_error_stats()

    assert result["status"] == "ok"
    assert result["total_errors"] == 0
    assert result["total_tools_with_errors"] == 0


@pytest.mark.asyncio
async def test_error_tracking():
    """Test error statistics tracking across multiple failures."""
    await research_error_clear()

    @safe_tool_call
    async def tracked_tool_a() -> None:
        raise ValueError("Error A")

    @safe_tool_call
    async def tracked_tool_b() -> None:
        raise KeyError("Error B")

    # Trigger errors
    await tracked_tool_a()
    await tracked_tool_a()
    await tracked_tool_b()

    # Check stats
    stats = await research_error_stats()
    assert stats["total_errors"] == 3
    assert stats["total_tools_with_errors"] == 2

    assert "tracked_tool_a" in stats["error_data"]
    assert stats["error_data"]["tracked_tool_a"]["count"] == 2
    assert stats["error_data"]["tracked_tool_a"]["error_types"]["ValueError"] == 2

    assert "tracked_tool_b" in stats["error_data"]
    assert stats["error_data"]["tracked_tool_b"]["count"] == 1
    assert stats["error_data"]["tracked_tool_b"]["error_types"]["KeyError"] == 1


@pytest.mark.asyncio
async def test_error_clear():
    """Test research_error_clear resets statistics."""
    # Ensure some errors are tracked
    @safe_tool_call
    async def some_tool() -> None:
        raise Exception("test")

    await some_tool()
    await some_tool()

    # Verify errors are tracked
    stats_before = await research_error_stats()
    assert stats_before["total_errors"] > 0

    # Clear
    clear_result = await research_error_clear()
    assert clear_result["status"] == "ok"
    assert clear_result["cleared"] is True
    assert clear_result["previous_error_count"] >= 2

    # Verify cleared
    stats_after = await research_error_stats()
    assert stats_after["total_errors"] == 0
    assert stats_after["total_tools_with_errors"] == 0


@pytest.mark.asyncio
async def test_decorator_preserves_signature():
    """Test that decorator preserves function name and docstring."""

    @safe_tool_call
    async def documented_tool(x: int) -> int:
        """This is a documented tool."""
        return x * 2

    assert documented_tool.__name__ == "documented_tool"
    assert documented_tool.__doc__ == "This is a documented tool."


@pytest.mark.asyncio
async def test_multiple_error_types():
    """Test tracking different exception types."""
    await research_error_clear()

    @safe_tool_call
    async def multi_error_tool(error_type: str) -> None:
        if error_type == "value":
            raise ValueError("value error")
        elif error_type == "key":
            raise KeyError("key error")
        elif error_type == "type":
            raise TypeError("type error")

    await multi_error_tool("value")
    await multi_error_tool("key")
    await multi_error_tool("type")
    await multi_error_tool("value")

    stats = await research_error_stats()
    assert stats["error_data"]["multi_error_tool"]["count"] == 4
    assert stats["error_data"]["multi_error_tool"]["error_types"]["ValueError"] == 2
    assert stats["error_data"]["multi_error_tool"]["error_types"]["KeyError"] == 1
    assert stats["error_data"]["multi_error_tool"]["error_types"]["TypeError"] == 1
