"""Vercel deployment and analytics integration.

Tools:
- research_vercel_status: Get real Vercel platform status
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from loom.error_responses import handle_tool_errors
logger = logging.getLogger("loom.tools.vercel")

@handle_tool_errors("research_vercel_status")

async def research_vercel_status() -> dict[str, Any]:
    """Get real Vercel platform status from official status page.

    Returns:
        Dict with Vercel platform status information
    """
    try:
        # Vercel's official status page API
        status_urls = [
            "https://www.vercel-status.com/api/v2/status.json",
            "https://status.vercel.com/api/v2/status.json",
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
            for status_url in status_urls:
                try:
                    response = await client.get(status_url)
                    if response.status_code == 200:
                        status_data = response.json()

                        # Parse Vercel status response
                        status_page = status_data.get("page", {})
                        components = status_data.get("components", [])
                        incidents = status_data.get("incidents", [])

                        # Build result
                        return {
                            "status": "success",
                            "platform": "Vercel",
                            "overall_status": status_page.get("status", "unknown"),
                            "components": [
                                {
                                    "name": comp.get("name"),
                                    "status": comp.get("status"),
                                    "description": comp.get("description", ""),
                                }
                                for comp in components[:10]
                            ],
                            "active_incidents": len(incidents),
                            "last_updated": status_page.get("updated_at", ""),
                            "status_page_url": "https://www.vercel-status.com/",
                        }
                except Exception as e:
                    logger.debug("vercel_status_url_failed %s: %s", status_url, e)
                    continue

        # If both URLs fail, return generic error
        return {
            "status": "unknown",
            "error": "Unable to reach Vercel status page",
            "status_page_url": "https://www.vercel-status.com/",
            "note": "Try checking https://www.vercel-status.com/ directly",
        }

    except Exception as e:
        logger.error("vercel_status_failed: %s", e)
        return {
            "status": "error",
            "error": str(e)[:200],
            "status_page_url": "https://www.vercel-status.com/",
        }
