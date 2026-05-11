"""MCP tool wrapper for model behavioral drift monitoring."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

try:
    from mcp.types import TextContent
except ImportError:
    TextContent = None  # type: ignore[assignment,misc]

try:
    from loom.drift_monitor import DriftMonitor
    from loom.params import DriftMonitorParams
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False
    DriftMonitor = None  # type: ignore[assignment,misc]
    DriftMonitorParams = None  # type: ignore[assignment,misc]

logger = logging.getLogger("loom.tools.drift_monitor")


async def research_drift_monitor(
    prompts: list[str] | str,
    model_name: str,
    mode: str = "check",
    storage_path: str = "~/.loom/drift/",
) -> dict[str, Any]:
    """Monitor model behavioral drift over time.

    Establishes baselines and detects when model safety behavior changes significantly.
    Tracks refusal rates, response characteristics, and safety scores.

    Args:
        prompts: List of test prompts or single prompt string (required)
        model_name: Name of the model being tested (required)
        mode: "baseline" to create baseline, "check" to compare against baseline (default: check)
        storage_path: Path to store drift data (default: ~/.loom/drift/)

    Returns:
        Dict with drift analysis:
        - For baseline mode: {model_name, baseline_date, prompt_count, refusal_rate, hcs_avg}
        - For check mode: {model_name, baseline_date, check_date, refusal_rate_baseline,
                         refusal_rate_current, refusal_drift_pct, hcs_avg_baseline,
                         hcs_avg_current, hcs_drift, alert_level, per_prompt_changes,
                         recommendations}
    """
    if not _DEPS_AVAILABLE:
        return {"error": "Dependencies not available (loom.drift_monitor)", "tool": "research_drift_monitor"}
    try:
        # Coerce string to list before validation
        if isinstance(prompts, str):
            prompts = [prompts]

        # Validate parameters
        params = DriftMonitorParams(
            prompts=prompts,
            model_name=model_name,
            mode=mode,
            storage_path=storage_path,
        )

        monitor = DriftMonitor(storage_path=params.storage_path)

        if params.mode == "baseline":
            # Dummy callback for testing - in real usage this would be provided by caller
            async def dummy_callback(prompt: str) -> str:
                return f"Response to: {prompt[:50]}..."

            result = await monitor.run_baseline(
                prompts=params.prompts,
                model_callback=dummy_callback,
                model_name=params.model_name,
            )
            logger.info("baseline_created model=%s prompts=%d", params.model_name, len(params.prompts))
            return result
        else:
            # Check mode - requires existing baseline
            async def dummy_callback(prompt: str) -> str:
                return f"Response to: {prompt[:50]}..."

            try:
                result = await monitor.run_check(
                    prompts=params.prompts,
                    model_callback=dummy_callback,
                    model_name=params.model_name,
                )
                logger.info("check_completed model=%s alert_level=%s", params.model_name, result["alert_level"])
                return result
            except ValueError as e:
                logger.error("check_failed model=%s error=%s", params.model_name, str(e))
                return {
                    "error": str(e),
                    "model_name": params.model_name,
                    "message": f"No baseline found for {params.model_name}. Run with mode='baseline' first.",
                }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_drift_monitor"}


async def tool_drift_monitor(
    prompts: list[str] | str,
    model_name: str,
    mode: str = "check",
    storage_path: str = "~/.loom/drift/",
) -> list[TextContent]:
    """MCP wrapper for research_drift_monitor."""
    result = await research_drift_monitor(
        prompts=prompts,
        model_name=model_name,
        mode=mode,
        storage_path=storage_path,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def research_drift_monitor_list(
    storage_path: str = "~/.loom/drift/",
) -> dict[str, list[str]]:
    """List all stored drift monitor baselines by model.

    Args:
        storage_path: Path to drift data storage (default: ~/.loom/drift/)

    Returns:
        Dict mapping model_name -> list of baseline dates
    """
    try:
        monitor = DriftMonitor(storage_path=storage_path)
        result = monitor.list_baselines()
        logger.info("baselines_listed count=%d", len(result))
        return result
    except Exception as exc:
        return {"error": str(exc), "tool": "research_drift_monitor_list"}


async def tool_drift_monitor_list(
    storage_path: str = "~/.loom/drift/",
) -> list[TextContent]:
    """MCP wrapper for research_drift_monitor_list."""
    result = await research_drift_monitor_list(storage_path=storage_path)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
