"""Vision-based web analysis using Playwright and LLM."""

from __future__ import annotations

import base64
import json
import logging
from typing import Any

from loom.error_responses import handle_tool_errors
logger = logging.getLogger("loom.tools.vision_agent")

@handle_tool_errors("research_vision_browse")

async def research_vision_browse(url: str, task: str) -> dict[str, Any]:
    """Screenshot a URL and analyze with LLM.

    Takes a screenshot using Playwright (or fallback HTML fetch), sends to
    LLM with task description, returns analysis and suggested actions.

    Args:
        url: URL to screenshot and analyze
        task: analysis task (e.g., "Check if login form present")

    Returns:
        Dict with: url, task, screenshot_taken, analysis, suggested_actions
    """
    from loom.validators import validate_url
    from loom.tools.core.fetch import research_fetch
    from loom.tools.llm.llm import _get_provider

    try:
        url = validate_url(url)
    except Exception as e:
        logger.error("url_validation_failed url=%s error=%s", url, e)
        return {
            "url": url,
            "task": task,
            "screenshot_taken": False,
            "analysis": f"Invalid URL: {str(e)}",
            "suggested_actions": [],
        }
    screenshot_taken = False
    screenshot_data = None

    try:
        import playwright.async_api as pw
        async with pw.async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1280, "height": 720})
            await page.goto(url, wait_until="networkidle", timeout=15000)
            screenshot_bytes = await page.screenshot(type="png")
            screenshot_data = base64.b64encode(screenshot_bytes).decode()
            screenshot_taken = True
            await browser.close()
    except Exception as e:
        logger.debug("playwright_screenshot_failed url=%s error=%s", url, e)

    content_description = ""
    if not screenshot_taken:
        try:
            result = await research_fetch(url, mode="http", max_chars=5000)
            if result.get("text"):
                content_description = f"\nPage HTML:\n{result['text'][:2000]}"
        except Exception as e:
            logger.warning("fallback_fetch_failed url=%s error=%s", url, e)

    provider = _get_provider("groq")
    prompt = (
        f"Analyze this web page for task: {task}\n"
        f"{'Screenshot captured.' if screenshot_taken else 'Analyzing content.'}"
        f"{content_description}\n"
        f"Return JSON: analysis, suggested_actions (list), confidence"
    )

    messages = []
    if screenshot_taken and screenshot_data:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/png", "data": screenshot_data
                }},
            ],
        })
    else:
        messages.append({"role": "user", "content": prompt})

    try:
        response = await provider.chat(messages, max_tokens=500)
        analysis_text = response.text if hasattr(response, "text") else str(response)
        try:
            parsed = json.loads(analysis_text)
            analysis = parsed.get("analysis", analysis_text)
            suggested_actions = parsed.get("suggested_actions", [])
        except (json.JSONDecodeError, AttributeError):
            analysis = analysis_text
            suggested_actions = []
        return {
            "url": url,
            "task": task,
            "screenshot_taken": screenshot_taken,
            "analysis": analysis,
            "suggested_actions": suggested_actions if isinstance(suggested_actions, list) else [],
        }
    except Exception as e:
        logger.error("llm_analysis_failed url=%s error=%s", url, e)
        return {
            "url": url,
            "task": task,
            "screenshot_taken": screenshot_taken,
            "analysis": f"Error: {str(e)}",
            "suggested_actions": [],
        }

@handle_tool_errors("research_vision_compare")

async def research_vision_compare(url1: str, url2: str) -> dict[str, Any]:
    """Compare visual layouts of two URLs.

    Fetches content from both URLs and compares visual layout and structure.

    Args:
        url1: first URL to compare
        url2: second URL to compare

    Returns:
        Dict with: url1, url2, similarities, differences, layout_match_score
    """
    from loom.validators import validate_url
    from loom.tools.core.fetch import research_fetch
    from loom.tools.llm.llm import _get_provider

    if not url1 or not url1.strip():
        raise ValueError("url1 is required and cannot be empty")
    if not url2 or not url2.strip():
        raise ValueError("url2 is required and cannot be empty")

    try:
        url1 = validate_url(url1)
        url2 = validate_url(url2)
    except Exception as e:
        logger.error("url_validation_failed error=%s", e)
        return {
            "url1": url1, "url2": url2, "similarities": [], "differences": [],
            "layout_match_score": 0, "error": f"Invalid URL: {str(e)}",
        }

    try:
        result1 = await research_fetch(url1, mode="http", max_chars=3000)
        result2 = await research_fetch(url2, mode="http", max_chars=3000)
        content1 = result1.get("text", "")[:2000]
        content2 = result2.get("text", "")[:2000]
    except Exception as e:
        logger.error("fetch_compare_failed error=%s", e)
        return {
            "url1": url1, "url2": url2, "similarities": [], "differences": [],
            "layout_match_score": 0, "error": str(e),
        }

    provider = _get_provider("groq")
    prompt = (
        f"Compare layouts:\n\nPage 1:\n{content1}\n\n"
        f"Page 2:\n{content2}\n\n"
        f"Return JSON: similarities (list), differences (list), layout_match_score (0-100)"
    )

    try:
        response = await provider.chat([{"role": "user", "content": prompt}], max_tokens=600)
        analysis_text = response.text if hasattr(response, "text") else str(response)
        parsed = json.loads(analysis_text)
        return {
            "url1": url1, "url2": url2,
            "similarities": parsed.get("similarities", []),
            "differences": parsed.get("differences", []),
            "layout_match_score": int(parsed.get("layout_match_score", 0)),
        }
    except Exception as e:
        logger.error("vision_compare_llm_failed error=%s", e)
        return {
            "url1": url1, "url2": url2, "similarities": [], "differences": [],
            "layout_match_score": 0, "error": str(e),
        }
