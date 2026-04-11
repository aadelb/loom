"""research_camoufox — Camoufox‑based stealth browser for anti‑bot websites.

Uses Camoufox (Firefox + anti‑detection patches) to scrape Cloudflare‑protected,
bot‑managed, and JavaScript‑heavy pages.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, cast

from mcp.types import TextContent
from pydantic import BaseModel

from loom.validators import STEALTH_TIMEOUT

logger = logging.getLogger("loom.tools.stealth")


class CamoufoxResult(BaseModel):
    """Result from Camoufox scrape."""

    url: str
    title: str = ""
    html: str = ""
    text: str = ""
    screenshot: str | None = None
    error: str | None = None


def _fetch_camoufox(
    url: str,
    session: str | None = None,
    screenshot: bool = False,
) -> CamoufoxResult:
    """Synchronous wrapper for Camoufox."""
    # Import here to avoid startup dependency
    try:
        from camoufox import Camoufox
    except ImportError:
        return CamoufoxResult(
            url=url,
            error="Camoufox not installed: pip install camoufox",
        )

    try:
        with Camoufox() as fox:
            # Navigate
            fox.get(url)

            # Wait for page load
            fox.wait_for_page_load()

            # Extract
            title = fox.title
            html = fox.page_source
            text = fox.page_text

            # Optional screenshot
            screenshot_b64 = None
            if screenshot:
                screenshot_b64 = fox.screenshot_as_base64

            return CamoufoxResult(
                url=url,
                title=title,
                html=html,
                text=text,
                screenshot=screenshot_b64,
            )
    except Exception as e:
        logger.exception("camoufox_fetch_failed url=%s", url)
        return CamoufoxResult(url=url, error=str(e))


async def research_camoufox(
    url: str,
    session: str | None = None,
    screenshot: bool = False,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Fetch a URL using Camoufox stealth browser.

    Args:
        url: URL to fetch
        session: NOT USED (for API compatibility with other tools)
        screenshot: include base64‑encoded screenshot
        timeout: operation timeout in seconds

    Returns:
        Dict with keys: url, title, html, text, screenshot (optional), error (optional)
    """
    logger.info("camoufox_start url=%s screenshot=%s", url, screenshot)

    if timeout is None:
        timeout = STEALTH_TIMEOUT

    loop = asyncio.get_running_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: _fetch_camoufox(url, session, screenshot),
            ),
            timeout=timeout,
        )
    except TimeoutError:
        logger.warning("camoufox_timeout url=%s", url)
        return {
            "url": url,
            "error": "timeout",
            "tool": "camoufox",
        }
    except Exception as exc:
        logger.exception("camoufox_unexpected_error url=%s", url)
        return {
            "url": url,
            "error": str(exc),
            "tool": "camoufox",
        }

    # Convert to dict
    output = result.model_dump(exclude_none=True)
    output["tool"] = "camoufox"
    return output


def tool_camoufox(
    url: str,
    session: str | None = None,
    screenshot: bool = False,
    timeout: int | None = None,
) -> list[TextContent]:
    """MCP wrapper for research_camoufox."""
    result = asyncio.run(research_camoufox(url, session, screenshot, timeout))
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
