"""Lightpanda AI-native headless browser backend — fetch and extract from pages.

Lightpanda is an AI-native headless browser that understands web content semantically.
This module wraps the lightpanda binary with subprocess execution for content extraction,
link discovery, and JavaScript-enabled rendering.

Uses Lightpanda as a subprocess since it's not easily pip-installable as a library.
"""

from __future__ import annotations
from loom.error_responses import handle_tool_errors

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from typing import Any

logger = logging.getLogger("loom.tools.lightpanda_backend")


def _check_lightpanda_available() -> tuple[bool, str]:
    """Check if Lightpanda binary is available.

    Returns:
        Tuple of (available: bool, message: str)
    """
    try:
        result = subprocess.run(
            ["lightpanda", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, "Lightpanda CLI found"
        else:
            return False, f"Lightpanda version check failed: {result.stderr}"
    except FileNotFoundError:
        return False, (
            "Lightpanda CLI not found. Install from: https://github.com/PSPDFKit/lightpanda"
        )
    except subprocess.TimeoutExpired:
        return False, "Lightpanda CLI timeout during version check"
    except Exception as exc:
        return False, f"Lightpanda availability check error: {str(exc)}"


@handle_tool_errors("research_lightpanda_fetch")
async def research_lightpanda_fetch(
    url: str,
    javascript: bool = True,
    wait_for: str | None = None,
    extract_links: bool = False,
) -> dict[str, Any]:
    """Fetch and extract content from a page using Lightpanda AI browser.

    Uses Lightpanda's AI-native understanding to semantically extract page content,
    with optional JavaScript rendering and DOM-ready waiting.

    Args:
        url: URL to fetch
        javascript: Enable JavaScript execution (default True)
        wait_for: CSS selector to wait for before extracting (optional)
        extract_links: Extract all links from the page (default False)

    Returns:
        Dict with:
        - url: The requested URL
        - status: "success" or "error"
        - content: Extracted page content (text/semantic)
        - links: List of extracted links (if extract_links=True)
        - javascript_enabled: Whether JS was executed
        - lightpanda_available: bool indicating if Lightpanda is available
        - error: error message if fetch failed (optional)
    """
    # Check if lightpanda is available
    available, msg = _check_lightpanda_available()
    if not available:
        return {
            "url": url,
            "status": "error",
            "lightpanda_available": False,
            "error": msg,
        }

    output_file = None
    try:
        # Validate URL format (basic check)
        if not url.startswith(("http://", "https://")):
            return {
                "url": url,
                "status": "error",
                "lightpanda_available": True,
                "error": "URL must start with http:// or https://",
            }

        # Create temp file for JSON output
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            output_file = tmp.name

        # Build lightpanda command
        cmd = ["lightpanda", "fetch", url, "--output", output_file]

        # Add JavaScript flag
        if javascript:
            cmd.append("--javascript")

        # Add wait-for selector if provided
        if wait_for:
            cmd.extend(["--wait-for", wait_for])

        # Add link extraction flag
        if extract_links:
            cmd.append("--extract-links")

        # Run lightpanda in executor to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            ),
        )

        output: dict[str, Any] = {
            "url": url,
            "lightpanda_available": True,
            "javascript_enabled": javascript,
        }

        # Parse the JSON output
        try:
            with open(output_file, "r") as f:
                lightpanda_output = json.load(f)

            # Lightpanda output format: {content, links (optional), metadata}
            output["status"] = "success"
            output["content"] = lightpanda_output.get("content", "")

            if extract_links and "links" in lightpanda_output:
                output["links"] = lightpanda_output["links"]
            else:
                output["links"] = []

            # Include metadata if available
            if "metadata" in lightpanda_output:
                output["metadata"] = lightpanda_output["metadata"]

            logger.info(
                f"lightpanda_fetch_success: {url} (js={javascript}, "
                f"content_length={len(output['content'])})"
            )

        except (json.JSONDecodeError, IOError) as exc:
            output["status"] = "error"
            output["error"] = f"Failed to parse Lightpanda output: {str(exc)}"

        return output

    except subprocess.TimeoutExpired:
        return {
            "url": url,
            "status": "error",
            "lightpanda_available": True,
            "error": "Lightpanda fetch timed out after 60 seconds",
        }
    except Exception as exc:
        logger.exception(f"lightpanda_fetch_error: {url}, {exc}")
        return {
            "url": url,
            "status": "error",
            "lightpanda_available": True,
            "error": f"Lightpanda fetch error: {str(exc)}",
        }
    finally:
        # Clean up temp file
        if output_file and os.path.exists(output_file):
            try:
                os.unlink(output_file)
            except OSError:
                logger.warning(f"Failed to clean up temp file: {output_file}")


@handle_tool_errors("research_lightpanda_batch")
async def research_lightpanda_batch(
    urls: list[str],
    javascript: bool = True,
    wait_for: str | None = None,
    extract_links: bool = False,
    timeout: int = 60,
) -> dict[str, Any]:
    """Batch fetch multiple URLs using Lightpanda AI browser.

    Performs Lightpanda fetches for multiple URLs sequentially to avoid
    overwhelming the system.

    Args:
        urls: List of URLs to fetch
        javascript: Enable JavaScript execution for all (default True)
        wait_for: CSS selector to wait for before extracting (optional)
        extract_links: Extract all links from pages (default False)
        timeout: Timeout in seconds per fetch (default 60)

    Returns:
        Dict with:
        - urls_checked: count of URLs fetched
        - results: dict mapping URL -> fetch result
        - success_count: count of successful fetches
        - lightpanda_available: bool indicating if Lightpanda is available
        - error: error message if batch failed (optional)
    """
    # Check if lightpanda is available upfront
    available, msg = _check_lightpanda_available()
    if not available:
        return {
            "urls_checked": 0,
            "results": {},
            "success_count": 0,
            "lightpanda_available": False,
            "error": msg,
        }

    validated = []
    try:
        # Validate and deduplicate URLs
        seen = set()
        for url in urls:
            if isinstance(url, str):
                url_clean = url.strip()
            else:
                url_clean = ""
            if url_clean and url_clean.startswith(("http://", "https://")):
                if url_clean not in seen:
                    validated.append(url_clean)
                    seen.add(url_clean)
            else:
                logger.warning(f"Skipping invalid URL {url}")

        if not validated:
            return {
                "urls_checked": 0,
                "results": {},
                "success_count": 0,
                "lightpanda_available": True,
                "error": "No valid URLs provided",
            }

        # Perform fetches
        results = {}
        success_count = 0

        for url in validated:
            fetch_result = await research_lightpanda_fetch(
                url=url,
                javascript=javascript,
                wait_for=wait_for,
                extract_links=extract_links,
            )
            results[url] = fetch_result
            if fetch_result.get("status") == "success":
                success_count += 1

        return {
            "urls_checked": len(validated),
            "results": results,
            "success_count": success_count,
            "lightpanda_available": True,
        }

    except Exception as exc:
        logger.exception(f"lightpanda_batch_error: {exc}")
        return {
            "urls_checked": len(validated),
            "results": {},
            "success_count": 0,
            "lightpanda_available": True,
            "error": f"Batch fetch error: {str(exc)}",
        }
