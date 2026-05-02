"""Tool registration modules — split from server.py for maintainability.

Each sub-module registers a category of tools with the FastMCP instance.
Import and call register_all_tools(mcp) to register everything.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP


def register_all_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register all tool categories with the MCP server.

    This replaces the monolithic _register_tools() in server.py
    by delegating to category-specific registration functions.
    """
    from loom.registrations.core import register_core_tools
    from loom.registrations.llm import register_llm_tools
    from loom.registrations.reframe import register_reframe_tools
    from loom.registrations.adversarial import register_adversarial_tools
    from loom.registrations.infrastructure import register_infrastructure_tools
    from loom.registrations.intelligence import register_intelligence_tools
    from loom.registrations.research import register_research_tools
    from loom.registrations.devops import register_devops_tools

    register_core_tools(mcp, wrap_tool)
    register_llm_tools(mcp, wrap_tool)
    register_reframe_tools(mcp, wrap_tool)
    register_adversarial_tools(mcp, wrap_tool)
    register_infrastructure_tools(mcp, wrap_tool)
    register_intelligence_tools(mcp, wrap_tool)
    register_research_tools(mcp, wrap_tool)
    register_devops_tools(mcp, wrap_tool)
