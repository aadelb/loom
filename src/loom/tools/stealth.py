"""research_camoufox — Camoufox-based stealth browser for anti-bot websites.

Uses Camoufox (Firefox + anti-detection patches) to scrape Cloudflare-protected,
bot-managed, and JavaScript-heavy pages.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

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
    """Synchronous wrapper for Camoufox.

    ``camoufox`` is an untyped third-party package, so ``fox`` is cast to
    ``Any`` once inside the context manager to suppress spurious mypy
    errors on its attribute access. This is safer than scattering
    ``# type: ignore`` comments on every attribute lookup.
    """
    try:
        from camoufox import Camoufox
    except ImportError:
        return CamoufoxResult(
            url=url,
            error="Camoufox not installed: pip install camoufox",
        )

    try:
        with Camoufox() as _fox:
            fox: Any = _fox  # Camoufox has no type stubs; narrow to Any
            fox.get(url)
            fox.wait_for_page_load()
            title = fox.title
            html = fox.page_source
            text = fox.page_text
            screenshot_b64 = fox.screenshot_as_base64 if screenshot else None

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
    timeout: int | None = None,  # noqa: ASYNC109
) -> dict[str, Any]:
    """Fetch a URL using Camoufox stealth browser.

    Args:
        url: URL to fetch
        session: NOT USED (for API compatibility with other tools)
        screenshot: include base64-encoded screenshot
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


# DEPRECATED: Use research_fetch(backend="dynamic") or research_cloak_fetch. This function wraps research_fetch(mode="dynamic").
async def research_botasaurus(
    url: str,
    session: str | None = None,
    screenshot: bool = False,
    timeout: int | None = None,  # noqa: ASYNC109
) -> dict[str, Any]:
    """Fetch a URL using Botasaurus stealth browser (second stealth escalation).

    Thin wrapper over ``research_fetch(url, mode="dynamic")`` which routes
    through Botasaurus' ``@browser`` decorator. Exposed as a distinct MCP tool
    so callers can explicitly request the Chrome-based stealth path when
    Camoufox (Firefox) is blocked by the target.

    Args:
        url: URL to fetch
        session: NOT USED (for API parity with research_camoufox / research_fetch)
        screenshot: return base64-encoded screenshot alongside text
        timeout: operation timeout in seconds

    Returns:
        Dict with keys: url, title, text, html_len, fetched_at, tool, error (if any)
    """
    from loom.tools.fetch import research_fetch

    logger.info("botasaurus_start url=%s", url)
    result: dict[str, Any] = research_fetch(
        url=url,
        mode="dynamic",
        return_format="screenshot" if screenshot else "text",
        timeout=timeout,
    )
    result.setdefault("tool", "botasaurus")
    return result


def tool_camoufox(
    url: str,
    session: str | None = None,
    screenshot: bool = False,
    timeout: int | None = None,
) -> list[TextContent]:
    """MCP wrapper for research_camoufox."""
    result = asyncio.run(research_camoufox(url, session, screenshot, timeout))
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
