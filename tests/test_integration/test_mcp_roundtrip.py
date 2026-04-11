"""Integration tests for MCP roundtrip — spawn server in-process, call tools.

Tests that tools are registered with MCP and respond correctly.
"""

from __future__ import annotations

import pytest

pytest.mark.integration
pytest.importorskip("loom.server")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_server_lists_tools() -> None:
    """MCP server /tools/list returns all expected tools."""
    pytest.skip("Full MCP integration requires FastMCP server startup")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_tool_fetch_roundtrip() -> None:
    """Calling research_fetch through MCP returns expected response."""
    pytest.skip("Full MCP integration requires FastMCP server startup")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_tool_search_roundtrip() -> None:
    """Calling research_search through MCP returns expected response."""
    pytest.skip("Full MCP integration requires FastMCP server startup")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_tool_session_roundtrip() -> None:
    """Session management tools work through MCP roundtrip."""
    pytest.skip("Full MCP integration requires FastMCP server startup")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_mcp_error_handling() -> None:
    """MCP layer properly serializes errors from tools."""
    pytest.skip("Full MCP integration requires FastMCP server startup")
