"""Vast.ai GPU provisioning research tool.

Tools:
- research_vastai_search: Search for available GPU instances by type and price
- research_vastai_status: Get current account balance and running instances
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_json
logger = logging.getLogger("loom.tools.vastai")

_VASTAI_API_BASE = "https://console.vast.ai/api/v0"

@handle_tool_errors("research_vastai_search")

async def research_vastai_search(
    gpu_type: str = "RTX 4090",
    max_price: float = 1.0,
    n: int = 5,
) -> dict[str, Any]:
    """Search for available GPU instances on Vast.ai.

    Args:
        gpu_type: GPU model (e.g. "RTX 4090", "A100", "H100")
        max_price: max hourly price in USD
        n: max number of results to return

    Returns:
        Dict with 'results' list (instances with gpu_name, price_per_hour,
        ram_gb, storage_gb, location) or 'error' key if request fails.
    """
    api_key = os.environ.get("VASTAI_API_KEY")
    if not api_key:
        return {
            "error": "VASTAI_API_KEY environment variable not set",
            "results": [],
        }

    headers = {"Authorization": f"Bearer {api_key}"}
    params = {
        "gpu": gpu_type,
        "max_price": max_price,
        "limit": n,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            data = await fetch_json(client,
                f"{_VASTAI_API_BASE}/bundles/",
                headers=headers,
                params=params,
            )
            if not data:
                logger.debug("vastai_no_data gpu_type=%s", gpu_type)
                return {"gpu_type": gpu_type, "max_price": max_price, "results": []}

            instances = []
            for item in data.get("bundles", [])[:n]:
                instances.append(
                    {
                        "gpu_name": item.get("gpu_name", ""),
                        "price_per_hour": item.get("price_per_hour"),
                        "ram_gb": item.get("ram_gb"),
                        "storage_gb": item.get("storage_gb"),
                        "location": item.get("location", ""),
                        "instance_id": item.get("id"),
                    }
                )

            logger.info(
                "vastai_search gpu_type=%s max_price=%.2f found=%d",
                gpu_type,
                max_price,
                len(instances),
            )

            return {
                "gpu_type": gpu_type,
                "max_price": max_price,
                "results": instances,
            }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return {"error": "Invalid VASTAI_API_KEY", "results": []}
        logger.warning("vastai_api_error status=%d", e.response.status_code)
        return {"error": f"API error: {e.response.status_code}", "results": []}
    except Exception as e:
        logger.warning("vastai_search_failed: %s", e)
        return {"error": str(e), "results": []}

@handle_tool_errors("research_vastai_status")

async def research_vastai_status() -> dict[str, Any]:
    """Get Vast.ai account status (balance and running instances).

    Returns:
        Dict with 'balance' (USD), 'running_instances' (count),
        or 'error' key if request fails.
    """
    api_key = os.environ.get("VASTAI_API_KEY")
    if not api_key:
        return {
            "error": "VASTAI_API_KEY environment variable not set",
            "balance": 0.0,
            "running_instances": 0,
        }

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            data = await fetch_json(client,
                f"{_VASTAI_API_BASE}/users/current/",
                headers=headers,
            )
            if not data:
                logger.debug("vastai_no_user_data")
                return {"balance": 0.0, "running_instances": 0}

            balance = data.get("balance", 0.0)
            running_instances = len(data.get("instances", []))

            logger.info("vastai_status balance=%.2f running=%d", balance, running_instances)

            return {
                "balance": float(balance),
                "running_instances": running_instances,
                "user_id": data.get("id"),
            }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return {
                "error": "Invalid VASTAI_API_KEY",
                "balance": 0.0,
                "running_instances": 0,
            }
        logger.warning("vastai_api_error status=%d", e.response.status_code)
        return {
            "error": f"API error: {e.response.status_code}",
            "balance": 0.0,
            "running_instances": 0,
        }
    except Exception as e:
        logger.warning("vastai_status_failed: %s", e)
        return {
            "error": str(e),
            "balance": 0.0,
            "running_instances": 0,
        }
