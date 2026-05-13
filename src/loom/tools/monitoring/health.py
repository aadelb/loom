"""health module — re-export for backward compatibility.

This module re-exports research_health_deep from health_deep.py
to provide backward compatibility with code that imports from loom.tools.health.
"""

from __future__ import annotations

import logging
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.health")

# Re-export research_health_deep from health_deep
try:
    from loom.tools.monitoring.health_deep import research_health_deep
except ImportError as e:
    logger.warning("Could not import research_health_deep from health_deep: %s", e)

    # Fallback: define a stub that warns the user
    @handle_tool_errors("research_health_deep")
    async def research_health_deep() -> dict[str, Any]:
        """Stub: health_deep module not available."""
        logger.error("research_health_deep stub called — health_deep not found")
        return {"error": "health_deep module not available", "status": "unknown"}

__all__ = ["research_health_deep"]
