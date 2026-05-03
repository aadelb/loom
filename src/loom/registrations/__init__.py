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
    from loom.registrations.remaining import register_remaining_tools
    from loom.registrations.devops import register_devops_tools

    import logging
    _log = logging.getLogger("loom.registrations")
    _categories = [
        ("core", register_core_tools),
        ("llm", register_llm_tools),
        ("reframe", register_reframe_tools),
        ("adversarial", register_adversarial_tools),
        ("infrastructure", register_infrastructure_tools),
        ("intelligence", register_intelligence_tools),
        ("research", register_research_tools),
        ("remaining", register_remaining_tools),
        ("devops", register_devops_tools),
    ]
    for name, register_fn in _categories:
        try:
            register_fn(mcp, wrap_tool)
        except Exception as e:
            _log.error("registration_failed category=%s error=%s", name, str(e)[:200])


def get_registration_stats() -> dict:
    """Get tool registration statistics for health endpoint.

    Returns statistics on which tools loaded successfully vs failed
    during server startup, organized by category.
    """
    from loom.registrations.tracking import get_registration_stats as _get_stats
    return _get_stats()
