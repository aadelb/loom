"""research_consistency_pressure — Build compliance momentum via past responses.

Stores model outputs and constructs pressure prompts that reference past
compliance behavior. Uses foot-in-the-door tactics with topic-based escalation.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from mcp.types import TextContent

from loom.consistency_pressure import ConsistencyPressure
from loom.params import (
    ConsistencyPressureHistoryParams,
    ConsistencyPressureParams,
    ConsistencyPressureRecordParams,
)

logger = logging.getLogger("loom.tools.consistency_pressure")


def _get_pressure_engine() -> ConsistencyPressure:
    """Get or create global consistency pressure engine.

    Uses LOOM_CONSISTENCY_PATH env var if set, otherwise defaults to ~/.loom/consistency/
    """
    storage_path = os.environ.get("LOOM_CONSISTENCY_PATH", "~/.loom/consistency/")
    return ConsistencyPressure(storage_path=storage_path)


async def research_consistency_pressure(
    model: str,
    target_prompt: str,
    max_references: int = 5,
) -> dict[str, Any]:
    """Build a prompt with consistency pressure references.

    Takes a target prompt and augments it with references to the model's
    past compliance behavior. Uses multiple pressure mechanisms:
    1. Past compliance citations ("You previously answered similar questions")
    2. Compliance rate reminder ("Your compliance rate is X%")
    3. Session turn references ("In turn N, you provided detailed info")
    4. Foot-in-the-door escalation (easy → harder compliance)

    Args:
        model: Model identifier (e.g., 'gpt-4', 'claude-opus')
        target_prompt: The prompt to inject pressure into (max 10000 chars)
        max_references: Max number of past responses to cite (1-20, default 5)

    Returns:
        Dict with:
        - pressure_prompt: str (constructed prompt with references)
        - references_used: int (number of past responses cited)
        - estimated_effectiveness: float (0-1 based on compliance history)
        - strategy: str (which pressure mechanism was applied)
        - compliance_history: dict (stats about model)
    """
    engine = _get_pressure_engine()
    result = await engine.build_pressure_prompt(
        model=model,
        target_prompt=target_prompt,
        max_references=max_references,
    )
    return result


async def research_consistency_pressure_record(
    model: str,
    prompt: str,
    response: str,
    complied: bool,
) -> dict[str, Any]:
    """Record a model's response for future pressure building.

    Stores: timestamp, prompt_hash, response_snippet, complied, topic.
    Enforces max 1000 entries per model (oldest dropped on overflow).

    Args:
        model: Model identifier
        prompt: Prompt that was sent (max 10000 chars)
        response: Model's response (max 50000 chars)
        complied: Whether model complied with the request

    Returns:
        Dict with:
        - recorded: bool (success flag)
        - model: str (model identifier)
        - timestamp: str (ISO timestamp)
        - entry_count: int (total entries for model, or error if failed)
    """
    engine = _get_pressure_engine()
    result = await engine.record(
        model=model,
        prompt=prompt,
        response=response,
        complied=complied,
    )
    return result


async def research_consistency_pressure_history(
    model: str,
) -> dict[str, Any]:
    """Get model's compliance history and stats.

    Returns aggregated statistics about a model's past responses:
    - Total entries recorded
    - Compliance rate (% of complied requests)
    - Topic distribution
    - Oldest and newest timestamps

    Args:
        model: Model identifier

    Returns:
        Dict with:
        - model: str (model identifier)
        - total_entries: int (number of recorded interactions)
        - complied_count: int (number of complied responses)
        - compliance_rate: float (0-1, rounded to 3 decimals)
        - topics: dict[str, int] (topic → count)
        - oldest_timestamp: str | None (ISO timestamp)
        - newest_timestamp: str | None (ISO timestamp)
    """
    engine = _get_pressure_engine()
    result = await engine.get_compliance_history(model=model)
    return result


async def tool_consistency_pressure(
    model: str,
    target_prompt: str,
    max_references: int = 5,
) -> list[TextContent]:
    """MCP wrapper for research_consistency_pressure."""
    result = await research_consistency_pressure(
        model=model,
        target_prompt=target_prompt,
        max_references=max_references,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def tool_consistency_pressure_record(
    model: str,
    prompt: str,
    response: str,
    complied: bool,
) -> list[TextContent]:
    """MCP wrapper for research_consistency_pressure_record."""
    result = await research_consistency_pressure_record(
        model=model,
        prompt=prompt,
        response=response,
        complied=complied,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def tool_consistency_pressure_history(
    model: str,
) -> list[TextContent]:
    """MCP wrapper for research_consistency_pressure_history."""
    result = await research_consistency_pressure_history(model=model)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
