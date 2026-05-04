"""Tool registration modules — split from server.py for maintainability.

Each sub-module registers a category of tools with the FastMCP instance.
Import and call register_all_tools(mcp) to register everything.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

_log = logging.getLogger("loom.registrations")


def register_all_tools(mcp: FastMCP, wrap_tool) -> None:
    """Register all tool categories with the MCP server.

    This replaces the monolithic _register_tools() in server.py
    by delegating to category-specific registration functions.

    At the end, logs a WARNING summary if any tools failed to register.
    """
    from loom.registrations.adversarial import register_adversarial_tools
    from loom.registrations.core import register_core_tools
    from loom.registrations.devops import register_devops_tools
    from loom.registrations.infrastructure import register_infrastructure_tools
    from loom.registrations.intelligence import register_intelligence_tools
    from loom.registrations.llm import (
        register_compression_tools,
        register_llm_tools,
    )
    from loom.registrations.reframe import register_reframe_tools
    from loom.registrations.remaining import register_remaining_tools
    from loom.registrations.research import register_research_tools
    from loom.registrations.tracking import get_registration_stats

    _categories = [
        ("core", register_core_tools),
        ("llm", register_llm_tools),
        ("compression", register_compression_tools),
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

    # Log summary at end of registration
    stats = get_registration_stats()
    total_loaded = stats.get("total_loaded", 0)
    total_failed = stats.get("total_failed", 0)
    health = stats.get("health_status", "unknown")

    if total_failed > 0:
        failed_tools = [
            f"  - {e['category']}: {e['function']} ({e['error'][:80]})"
            for e in stats.get("registration_errors", [])
        ]
        _log.warning(
            "registration_summary loaded=%d failed=%d health_status=%s "
            "failed_tools=[%s]",
            total_loaded,
            total_failed,
            health,
            ", ".join(failed_tools[:5]),  # Show first 5 failures in log
        )
    else:
        _log.info("registration_summary loaded=%d health_status=%s", total_loaded, health)


def get_registration_stats() -> dict:
    """Get tool registration statistics for health endpoint.

    Returns statistics on which tools loaded successfully vs failed
    during server startup, organized by category.
    """
    from loom.registrations.tracking import get_registration_stats as _get_stats

    return _get_stats()


def get_registration_errors() -> list[dict]:
    """Get all registration errors with detailed information.

    Returns list of error dicts with: category, function, error, timestamp
    """
    from loom.registrations.tracking import get_registration_errors as _get_errors

    return _get_errors()

# Auto-register all tools missed by category registration files
try:
    from loom.registrations.auto_missing import register_missing_tools as _reg_missing
except ImportError:
    _reg_missing = None

_original_register = register_all_tools

def register_all_tools(mcp, wrap_tool):
    _original_register(mcp, wrap_tool)
    if _reg_missing:
        try:
            _reg_missing(mcp, wrap_tool)
        except Exception:
            pass
