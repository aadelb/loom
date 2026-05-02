"""CLI fallback provider for LLM calls when all API providers are rate-limited.

Uses local CLI tools (gemini, kimi, codex) as last-resort providers.
These tools use OAuth/local auth and have separate rate limits from APIs.
"""
from __future__ import annotations

import asyncio
import json
import logging
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
        Dict with: response (str), provider (str), via ("cli"), error (str|None)
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
            return {
                "response": response,
                "provider": provider["name"],
                "via": "cli",
                "error": None,
            }
        else:
            logger.debug("cli_empty_response provider=%s", provider["name"])

    return {
        "response": "",
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
    return result.get("response", "")
