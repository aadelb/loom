"""Tool Chain Composer — define and execute multi-tool pipelines."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.chain_composer")


def _get_chains_dir() -> Path:
    """Get or create ~/.loom/chains directory."""
    chains_dir = Path.home() / ".loom" / "chains"
    chains_dir.mkdir(parents=True, exist_ok=True)
    return chains_dir


def _get_tool_names() -> set[str]:
    """Return set of all valid research_xxx tool names."""
    # Core tools + common optional tools that start with research_
    core_tools = {
        "fetch", "spider", "markdown", "search", "deep", "github",
        "camoufox", "botasaurus", "cache_stats", "cache_clear",
        "session_open", "session_list", "session_close",
        "config_get", "config_set", "health_check",
    }
    # Prefix with research_ for validation
    return {f"research_{tool}" for tool in core_tools}


async def research_chain_define(
    name: str,
    steps: list[dict],
) -> dict[str, Any]:
    """Define a reusable tool chain (pipeline).

    Each step: {"tool": "research_xxx", "params": {...}, "condition": "always"|"on_success"|"on_failure"}

    Args:
        name: Chain identifier (alphanumeric, dashes, underscores)
        steps: List of step dicts with tool, params, and optional condition

    Returns:
        Dict with chain_name, steps_count, saved: True
    """
    # Validate chain name
    if not name or not all(c.isalnum() or c in "-_" for c in name):
        raise ValueError("Chain name must be alphanumeric with dashes/underscores")

    if not steps:
        raise ValueError("Steps list cannot be empty")

    valid_tools = _get_tool_names()
    valid_conditions = {"always", "on_success", "on_failure"}

    for i, step in enumerate(steps):
        if "tool" not in step:
            raise ValueError(f"Step {i}: missing 'tool' key")

        tool_name = step["tool"]
        if tool_name not in valid_tools:
            raise ValueError(f"Step {i}: unknown tool '{tool_name}' (expected research_xxx)")

        if "params" not in step:
            raise ValueError(f"Step {i}: missing 'params' key")

        condition = step.get("condition", "always")
        if condition not in valid_conditions:
            raise ValueError(f"Step {i}: invalid condition '{condition}'")

    # Save chain as JSON
    chains_dir = _get_chains_dir()
    chain_path = chains_dir / f"{name}.json"

    chain_data = {
        "name": name,
        "steps": steps,
        "created": datetime.now(UTC).isoformat(),
        "runs": 0,
    }

    chain_path.write_text(json.dumps(chain_data, indent=2))
    logger.info("chain_defined", name=name, steps_count=len(steps))

    return {
        "chain_name": name,
        "steps_count": len(steps),
        "saved": True,
    }


async def research_chain_list() -> dict[str, Any]:
    """List all defined chains with metadata.

    Returns:
        Dict with chains (list of {name, steps_count, created, last_run}), total
    """
    chains_dir = _get_chains_dir()

    if not chains_dir.exists():
        return {"chains": [], "total": 0}

    chains = []
    for chain_file in sorted(chains_dir.glob("*.json")):
        try:
            data = json.loads(chain_file.read_text())
            chains.append({
                "name": data.get("name", chain_file.stem),
                "steps_count": len(data.get("steps", [])),
                "created": data.get("created"),
                "last_run": data.get("last_run"),
            })
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("chain_list_read_error", path=chain_file, error=str(e))

    logger.info("chain_list_retrieved", total=len(chains))

    return {
        "chains": chains,
        "total": len(chains),
    }


async def research_chain_describe(name: str) -> dict[str, Any]:
    """Show details of a specific chain.

    Args:
        name: Chain identifier

    Returns:
        Dict with name, steps, created, runs_count
    """
    chains_dir = _get_chains_dir()
    chain_path = chains_dir / f"{name}.json"

    if not chain_path.exists():
        raise FileNotFoundError(f"Chain '{name}' not found")

    try:
        data = json.loads(chain_path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Chain '{name}' has invalid JSON: {e}")

    steps_summary = []
    for step in data.get("steps", []):
        steps_summary.append({
            "tool": step.get("tool"),
            "params_summary": ", ".join(step.get("params", {}).keys()),
            "condition": step.get("condition", "always"),
        })

    logger.info("chain_described", name=name, steps_count=len(steps_summary))

    return {
        "name": name,
        "steps": steps_summary,
        "created": data.get("created"),
        "runs_count": data.get("runs", 0),
    }
