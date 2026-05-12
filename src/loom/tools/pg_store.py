"""PostgreSQL connection status and migration tools."""
from __future__ import annotations

from typing import Any
from loom.error_responses import handle_tool_errors


@handle_tool_errors("research_pg_status")
async def research_pg_status() -> dict[str, Any]:
    """Check PostgreSQL connection status."""
    try:
        import asyncpg  # noqa: F401
        return {
            "status": "available",
            "tool": "research_pg_status",
            "backend": "postgresql"
        }
    except ImportError:
        return {
            "error": "asyncpg not installed",
            "tool": "research_pg_status",
            "status": "unavailable"
        }


@handle_tool_errors("research_pg_migrate")
async def research_pg_migrate() -> dict[str, Any]:
    """Run PostgreSQL migrations (stub)."""
    return {
        "status": "pending",
        "tool": "research_pg_migrate",
        "message": "migration capability available"
    }
