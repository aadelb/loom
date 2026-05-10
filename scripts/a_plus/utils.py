"""Shared utilities for A+ automation scripts.

Provides model routing via Loom's own LLM provider infrastructure.
"""
from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path
from typing import Any

# Ensure src/loom is importable
_src = Path(__file__).resolve().parent.parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


async def call_model(
    model: str,
    system: str,
    user: str,
    max_tokens: int = 4000,
) -> str:
    """Route to the correct AI model via Loom's providers.

    Args:
        model: One of "gemini", "kimi", "deepseek", "nvidia"
        system: System prompt
        user: User prompt
        max_tokens: Maximum response tokens

    Returns:
        Model response text
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    if model == "gemini":
        from loom.providers.gemini_provider import GeminiProvider
        provider = GeminiProvider()
        resp = await provider.chat(messages=messages, max_tokens=max_tokens)
        return resp.text

    elif model == "kimi":
        from loom.providers.moonshot_provider import MoonshotProvider
        provider = MoonshotProvider()
        resp = await provider.chat(messages=messages, max_tokens=max_tokens)
        return resp.text

    elif model == "deepseek":
        from loom.providers.deepseek_provider import DeepSeekProvider
        provider = DeepSeekProvider()
        resp = await provider.chat(messages=messages, max_tokens=max_tokens)
        return resp.text

    elif model == "nvidia":
        from loom.providers.nvidia_nim import NvidiaNimProvider
        provider = NvidiaNimProvider()
        resp = await provider.chat(messages=messages, max_tokens=max_tokens)
        return resp.text

    else:
        raise ValueError(f"Unknown model: {model}. Use: gemini, kimi, deepseek, nvidia")


def read_prompt(name: str) -> str:
    """Read a prompt template from prompts/ directory."""
    prompt_dir = Path(__file__).parent / "prompts"
    path = prompt_dir / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text()


def discover_tools_in_category(category: str) -> list[Path]:
    """Discover tool files for a given registration category.

    Reads registrations/<category>.py to find imported tool modules.
    """
    reg_dir = _src / "loom" / "registrations"
    reg_file = reg_dir / f"{category}.py"
    if not reg_file.exists():
        raise FileNotFoundError(f"Registration file not found: {reg_file}")

    tools_dir = _src / "loom" / "tools"
    tool_files: list[Path] = []

    for line in reg_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("from loom.tools."):
            parts = line.split("from loom.tools.")[1].split(" import")[0]
            module_name = parts.strip()
            tool_path = tools_dir / f"{module_name}.py"
            if tool_path.exists() and tool_path not in tool_files:
                tool_files.append(tool_path)

    return tool_files


def run_async(coro: Any) -> Any:
    """Run an async function from sync context."""
    return asyncio.run(coro)
