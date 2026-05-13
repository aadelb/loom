"""Stagehand integration — vision-first browser automation."""

from __future__ import annotations

import json
import logging
import tempfile
from typing import Any
from pydantic import BaseModel, field_validator

from loom.error_responses import handle_tool_errors
from loom.validators import validate_url

logger = logging.getLogger("loom.tools.stagehand_backend")
_browser = None


class StagehandActParams(BaseModel):
    """Parameters for research_stagehand_act."""

    url: str
    instruction: str
    screenshot: bool = False
    timeout: int = 30
    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("instruction")
    @classmethod
    def validate_instruction(cls, v: str) -> str:
        if not v or len(v) > 2000:
            raise ValueError("instruction 1-2000 chars")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 5 or v > 120:
            raise ValueError("timeout 5-120 seconds")
        return v


class StagehandExtractParams(BaseModel):
    """Parameters for research_stagehand_extract."""

    url: str
    schema: dict[str, Any]
    timeout: int = 30
    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("schema")
    @classmethod
    def validate_schema(cls, v: dict[str, Any]) -> dict[str, Any]:
        if not v:
            raise ValueError("schema cannot be empty")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 5 or v > 120:
            raise ValueError("timeout 5-120 seconds")
        return v


async def _get_browser():
    """Lazy-initialize Playwright browser."""
    global _browser
    if _browser:
        return _browser
    try:
        from playwright.async_api import async_playwright
        pw = async_playwright()
        _pw_ctx = await pw.__aenter__()
        _browser = await _pw_ctx.chromium.launch(headless=True)
        return _browser
    except ImportError:
        raise ImportError("playwright not installed: pip install playwright")
    except Exception as exc:
        logger.error("playwright_launch_failed error=%s", exc)
        raise


async def _call_llm_vision(page: str, ss: str | None, instr: str) -> str:
    """Call LLM vision to analyze page."""
    try:
        from loom.tools.llm import research_llm_answer
    except ImportError:
        return "LLM tools not available"
    prompt = f"Instruction: {instr}\n\nPage:\n{page[:5000]}"
    if ss:
        prompt += f"\nScreenshot: {ss}"
    try:
        r = await research_llm_answer(prompt)
        return r.get("answer", str(r)) if isinstance(r, dict) else str(r)
    except Exception as exc:
        logger.error("llm_vision_failed error=%s", exc)
        return f"Error: {exc}"


@handle_tool_errors("research_stagehand_act")
async def research_stagehand_act(url: str, instruction: str, screenshot: bool = False) -> dict[str, Any]:
    """Execute browser instruction with vision-guided automation.

    Args:
        url: Target URL
        instruction: Natural language instruction (1-2000 chars)
        screenshot: Capture screenshot (default False)

    Returns:
        Dict with url, instruction, actions_taken, result_text, screenshot_path, error.
    """
    params = StagehandActParams(url=url, instruction=instruction, screenshot=screenshot)
    result: dict[str, Any] = {
        "url": params.url, "instruction": params.instruction, "actions_taken": [],
        "result_text": "", "screenshot_path": None
    }

    try:
        browser = await _get_browser()
        page = await browser.new_page()
        try:
            await page.goto(params.url, wait_until="networkidle", timeout=params.timeout * 1000)
            result["actions_taken"].append(f"Navigated to {params.url}")

            ss_path = None
            if params.screenshot:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                    f.write(await page.screenshot())
                    ss_path = f.name
                    result["screenshot_path"] = ss_path
                    result["actions_taken"].append(f"Screenshot: {ss_path}")

            page_text = await page.evaluate("() => document.body.innerText")
            result["result_text"] = await _call_llm_vision(page_text, ss_path, params.instruction)
            return result
        finally:
            await page.close()
    except ImportError as exc:
        result["error"] = f"Playwright unavailable: {exc}"
        return result
    except Exception as exc:
        logger.error("stagehand_act_failed url=%s error=%s", params.url, exc)
        result["error"] = str(exc)
        return result


@handle_tool_errors("research_stagehand_extract")
async def research_stagehand_extract(url: str, schema: dict[str, Any] | str) -> dict[str, Any]:
    """Extract structured data from page matching schema using LLM vision.

    Args:
        url: Target URL
        schema: Dict with field names/descriptions for extraction

    Returns:
        Dict with url, extracted_data, confidence, error.
    """
    # Coerce string schema to dict
    if isinstance(schema, str):
        schema = {"extract": schema}

    params = StagehandExtractParams(url=url, schema=schema)
    result: dict[str, Any] = {"url": params.url, "extracted_data": {}, "confidence": 0.0}

    try:
        browser = await _get_browser()
        page = await browser.new_page()
        try:
            await page.goto(params.url, wait_until="networkidle", timeout=params.timeout * 1000)
            page_text = await page.evaluate("() => document.body.innerText")

            try:
                from loom.tools.llm import research_llm_answer
            except ImportError:
                result["error"] = "LLM tools not available"
                return result

            prompt = f"Extract schema:\n{json.dumps(params.schema)}\n\nPage:\n{page_text[:3000]}\n\nReturn JSON with extracted data and 'confidence' (0-1)."
            r = await research_llm_answer(prompt)
            text = r.get("answer", str(r)) if isinstance(r, dict) else str(r)

            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    result["confidence"] = min(1.0, max(0.0, data.pop("confidence", 0.5)))
                    result["extracted_data"] = data
            except (json.JSONDecodeError, ValueError):
                pass
            return result
        finally:
            await page.close()
    except ImportError as exc:
        result["error"] = f"Playwright unavailable: {exc}"
        return result
    except Exception as exc:
        logger.error("stagehand_extract_failed url=%s error=%s", params.url, exc)
        result["error"] = str(exc)
        return result
