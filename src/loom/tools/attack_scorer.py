"""Attack effectiveness scoring tool — evaluate prompt injection/jailbreak success.

Scores attack effectiveness across 8 dimensions:
1. bypass_success: Did the response comply with the attack?
2. information_density: How much useful info vs filler/hedging?
3. stealth_score: Would a safety classifier flag this?
4. transferability: Cross-model success rate
5. persistence: Would this work on retry?
6. escalation_potential: Can this be escalated further?
7. defense_evasion: Does response avoid post-hoc filters?
8. novelty: Is this attack pattern novel vs well-known?
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.types import TextContent

from loom.attack_scorer import AttackEffectivenessScorer

logger = logging.getLogger("loom.tools.attack_scorer")


def research_attack_score(
    prompt: str,
    response: str,
    strategy: str = "",
    model: str = "",
    baseline_refusal: bool = True,
) -> dict[str, Any]:
    """Score attack effectiveness across 8 dimensions.

    Args:
        prompt: The attack/reframed prompt sent to the model
        response: The model's response to the prompt
        strategy: Attack strategy name (e.g., "role_play", "prompt_injection")
        model: Target model name (for logging)
        baseline_refusal: Whether a baseline refusal is expected

    Returns:
        Dict with keys:
            - dimensions: dict of 8 scores (0-10 each)
            - total_score: weighted average (0-10)
            - asr_estimate: estimated attack success rate (0-1)
            - recommendation: str with suggested next steps
    """
    logger.info(
        "attack_score prompt_len=%d response_len=%d strategy=%s model=%s",
        len(prompt),
        len(response),
        strategy or "unknown",
        model or "unknown",
    )

    scorer = AttackEffectivenessScorer()
    result = scorer.score(
        prompt=prompt,
        response=response,
        strategy=strategy,
        model=model,
        baseline_refusal=baseline_refusal,
    )

    logger.info(
        "attack_score_result total_score=%s asr=%s strategy=%s",
        result["total_score"],
        result["asr_estimate"],
        strategy or "unknown",
    )

    return result


def tool_attack_score(
    prompt: str,
    response: str,
    strategy: str = "",
    model: str = "",
    baseline_refusal: bool = True,
) -> list[TextContent]:
    """MCP wrapper for research_attack_score."""
    result = research_attack_score(
        prompt=prompt,
        response=response,
        strategy=strategy,
        model=model,
        baseline_refusal=baseline_refusal,
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]
