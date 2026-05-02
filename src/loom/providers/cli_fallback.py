"""CLI fallback provider for LLM calls when all API providers are rate-limited.

Uses local CLI tools (gemini, kimi, codex) as last-resort providers.
These tools use OAuth/local auth and have separate rate limits from APIs.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
from typing import Any

logger = logging.getLogger("loom.providers.cli_fallback")


async def _run_cli(cmd: list[str], timeout: float = 120.0) -> str:
    """Run a CLI command and return stdout."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode == 0:
            return stdout.decode("utf-8", errors="replace").strip()
        logger.debug("cli_failed cmd=%s rc=%d stderr=%s", cmd[0], proc.returncode, stderr[:200])
        return ""
    except asyncio.TimeoutError:
        logger.warning("cli_timeout cmd=%s timeout=%s", cmd[0], timeout)
        proc.kill()
        return ""
    except Exception as e:
        logger.debug("cli_error cmd=%s: %s", cmd[0], e)
        return ""


def _cli_available(name: str) -> bool:
    """Check if a CLI tool is installed."""
    return shutil.which(name) is not None


def _extract_json_from_cli(raw_text: str) -> dict[str, Any]:
    """Extract JSON from raw CLI response.

    Tries multiple strategies:
    1. Direct JSON parsing
    2. ```json ... ``` code block extraction
    3. { ... } pattern extraction
    4. Fallback to wrapped text

    Args:
        raw_text: Raw response from CLI tool

    Returns:
        Dict with either parsed JSON or {"text": raw_text, "source": "cli_fallback"}
    """
    if not raw_text:
        return {"text": "", "source": "cli_fallback"}

    # Strategy 1: Try direct JSON parse
    try:
        result = json.loads(raw_text)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: Extract from ```json ... ``` code block
    json_block_match = re.search(r"```json\s*(.*?)\s*```", raw_text, re.DOTALL)
    if json_block_match:
        try:
            result = json.loads(json_block_match.group(1))
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 3: Extract first { ... } pattern
    brace_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if brace_match:
        try:
            result = json.loads(brace_match.group(0))
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 4: Fallback — wrap in dict
    logger.debug("cli_json_extraction_failed, wrapping as text")
    return {"text": raw_text, "source": "cli_fallback"}


# === CLI Provider Registry ===

CLI_PROVIDERS = [
    {
        "name": "gemini",
        "binary": "gemini",
        "build_cmd": lambda prompt, max_tokens: [
            "gemini", "-m", "gemini-3-pro-preview",
            "--approval-mode", "yolo",
            prompt,
        ],
        "priority": 1,
    },
    {
        "name": "kimi",
        "binary": "kimi",
        "build_cmd": lambda prompt, max_tokens: [
            "kimi", "--yolo", "-p", prompt,
        ],
        "priority": 2,
    },
    {
        "name": "codex",
        "binary": "codex",
        "build_cmd": lambda prompt, max_tokens: [
            "codex", "exec", "-m", "gpt-5.2-codex",
            "-s", "workspace-write", prompt,
        ],
        "priority": 3,
    },
]


async def cli_llm_call(
    prompt: str,
    max_tokens: int = 2000,
    preferred_cli: str | None = None,
) -> dict[str, Any]:
    """Call LLM via CLI tools as fallback when all APIs are rate-limited.

    Tries CLI tools in priority order: gemini → kimi → codex.
    Each uses OAuth/local auth with separate rate limits.

    Args:
        prompt: The prompt to send
        max_tokens: Max tokens (advisory, CLIs don't always respect this)
        preferred_cli: Force a specific CLI ("gemini", "kimi", "codex")

    Returns:
        Dict with: response (dict|str), provider (str), via ("cli"), error (str|None)
    """
    # If preferred CLI specified, try it first
    if preferred_cli:
        providers = [p for p in CLI_PROVIDERS if p["name"] == preferred_cli] + CLI_PROVIDERS
    else:
        providers = CLI_PROVIDERS

    for provider in providers:
        binary = provider["binary"]
        if not _cli_available(binary):
            logger.debug("cli_not_available: %s", binary)
            continue

        cmd = provider["build_cmd"](prompt, max_tokens)
        logger.info("cli_attempting provider=%s", provider["name"])

        response = await _run_cli(cmd, timeout=120.0)

        if response and len(response) > 50:
            logger.info("cli_success provider=%s response_len=%d", provider["name"], len(response))
            # Extract JSON if present, otherwise wrap raw text
            parsed_response = _extract_json_from_cli(response)
            return {
                "response": parsed_response,
                "provider": provider["name"],
                "via": "cli",
                "error": None,
            }
        else:
            logger.debug("cli_empty_response provider=%s", provider["name"])

    return {
        "response": {"text": "", "source": "cli_fallback"},
        "provider": "none",
        "via": "cli",
        "error": "All CLI providers failed or unavailable",
    }


async def cli_cascade_call(
    prompt: str,
    max_tokens: int = 2000,
) -> str:
    """Simple interface: try all CLIs and return the response text or empty string."""
    result = await cli_llm_call(prompt, max_tokens)
    response = result.get("response", "")

    # Handle both dict (parsed JSON) and string (raw text)
    if isinstance(response, dict):
        # If parsed JSON, try to extract text field, otherwise serialize
        return response.get("text", json.dumps(response))
    return str(response)
