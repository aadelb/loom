"""Tool Chain Composer — define and execute multi-tool pipelines."""
from __future__ import annotations
import json, logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.chain_composer")


def _get_chains_dir() -> Path:
    chains_dir = Path.home() / ".loom" / "chains"
    chains_dir.mkdir(parents=True, exist_ok=True)
    return chains_dir


@handle_tool_errors("research_chain_define")
async def research_chain_define(name: str, steps: list[dict]) -> dict[str, Any]:
    """Define a reusable tool chain (pipeline).

    Args:
        name: Chain identifier (alphanumeric, dashes, underscores)
        steps: List of step dicts with tool, params, and optional condition

    Returns:
        Dict with chain_name, steps_count, saved: True
    """
    try:
        if not name or not all(c.isalnum() or c in "-_" for c in name):
            raise ValueError("name must be alphanumeric with dashes/underscores")
        if not steps:
            raise ValueError("steps cannot be empty")

        valid_conditions = {"always", "on_success", "on_failure"}
        for i, step in enumerate(steps):
            if "tool" not in step or "params" not in step:
                raise ValueError(f"step {i}: missing 'tool' or 'params'")
            if step.get("condition", "always") not in valid_conditions:
                raise ValueError(f"step {i}: invalid condition")

        chains_dir = _get_chains_dir()
        chain_path = chains_dir / f"{name}.json"
        chain_data = {"name": name, "steps": steps, "created": datetime.now(UTC).isoformat(), "runs": 0}
        chain_path.write_text(json.dumps(chain_data, indent=2))
        logger.info("chain_defined name=%s steps_count=%d", name, len(steps))
        return {"chain_name": name, "steps_count": len(steps), "saved": True}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_chain_define"}


@handle_tool_errors("research_chain_list")
async def research_chain_list() -> dict[str, Any]:
    """List all defined chains with metadata.

    Returns:
        Dict with chains (list of {name, steps_count, created, last_run}), total
    """
    try:
        chains_dir = _get_chains_dir()
        chains = []
        if chains_dir.exists():
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
                    logger.warning("chain_list_error path=%s error=%s", chain_file, str(e))
        logger.info("chain_list_retrieved total=%d", len(chains))
        return {"chains": chains, "total": len(chains)}
    except Exception as exc:
        return {"error": str(exc), "tool": "research_chain_list"}


@handle_tool_errors("research_chain_describe")
async def research_chain_describe(name: str) -> dict[str, Any]:
    """Show details of a specific chain.

    Args:
        name: Chain identifier

    Returns:
        Dict with name, steps, created, runs_count
    """
    try:
        chains_dir = _get_chains_dir()
        chain_path = chains_dir / f"{name}.json"
        if not chain_path.exists():
            raise FileNotFoundError(f"Chain '{name}' not found")
        try:
            data = json.loads(chain_path.read_text())
        except json.JSONDecodeError as e:
            raise ValueError(f"Chain '{name}' invalid JSON: {e}")

        steps_summary = [{
            "tool": step.get("tool"),
            "params_summary": ", ".join(step.get("params", {}).keys()),
            "condition": step.get("condition", "always"),
        } for step in data.get("steps", [])]
        logger.info("chain_described name=%s steps_count=%d", name, len(steps_summary))
        return {
            "name": name,
            "steps": steps_summary,
            "created": data.get("created"),
            "runs_count": data.get("runs", 0),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_chain_describe"}
