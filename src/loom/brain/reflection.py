"""Brain Reflection Layer — Evaluate results, decide retry/chain/done."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from loom.brain.prompts import REFLECTION_SYSTEM, REFLECTION_USER
from loom.brain.types import QualityMode

logger = logging.getLogger("loom.brain.reflection")


def evaluate_result(
    query: str,
    tool_name: str,
    result: dict[str, Any],
    quality_mode: QualityMode = QualityMode.AUTO,
) -> dict[str, Any]:
    """Evaluate whether a tool result satisfies the query.

    Returns:
        Dict with keys: complete (bool), reason (str), next_action (done|retry|chain)
    """
    if not result.get("success", False):
        error = result.get("error", "unknown error")
        return {
            "complete": False,
            "reason": f"Tool failed: {error}",
            "next_action": "retry",
        }

    tool_output = result.get("result")

    if tool_output is None:
        return {
            "complete": False,
            "reason": "Tool returned no output",
            "next_action": "retry",
        }

    if isinstance(tool_output, dict) and tool_output.get("error"):
        return {
            "complete": False,
            "reason": f"Tool returned error: {tool_output['error']}",
            "next_action": "retry",
        }

    if _is_empty_result(tool_output):
        return {
            "complete": False,
            "reason": "Result is empty or contains no data",
            "next_action": "chain",
        }

    if quality_mode == QualityMode.ECONOMY:
        return {"complete": True, "reason": "Economy mode: first result accepted", "next_action": "done"}

    completeness = _assess_completeness(query, tool_output)
    if completeness >= 0.7:
        return {"complete": True, "reason": "Result appears complete", "next_action": "done"}
    elif completeness >= 0.4:
        return {
            "complete": False,
            "reason": "Partial result — may benefit from additional tools",
            "next_action": "chain",
        }
    else:
        return {
            "complete": False,
            "reason": "Result doesn't adequately address the query",
            "next_action": "retry",
        }


def _is_empty_result(output: Any) -> bool:
    """Check if output is effectively empty."""
    if output is None:
        return True
    if isinstance(output, str) and len(output.strip()) < 10:
        return True
    if isinstance(output, dict):
        results = output.get("results", output.get("data", output.get("items")))
        if isinstance(results, list) and len(results) == 0:
            return True
        if not any(v for v in output.values() if v is not None and v != "" and v != []):
            return True
    if isinstance(output, list) and len(output) == 0:
        return True
    return False


def _assess_completeness(query: str, output: Any) -> float:
    """Heuristic completeness score (0.0–1.0) based on output richness and semantic alignment.

    Combines structural richness (keys, items) with semantic alignment
    (how many query terms appear in the result).
    """
    score = 0.0

    if isinstance(output, dict):
        non_empty_keys = sum(
            1 for v in output.values()
            if v is not None and v != "" and v != [] and v != {}
        )
        score += min(non_empty_keys / 5, 0.4)

        results = output.get("results", output.get("data", output.get("items", [])))
        if isinstance(results, list):
            score += min(len(results) / 5, 0.3)

        output_str = json.dumps(output, default=str)
        if len(output_str) > 500:
            score += 0.2
        elif len(output_str) > 100:
            score += 0.1

    elif isinstance(output, str):
        if len(output) > 200:
            score += 0.5
        elif len(output) > 50:
            score += 0.3

        # Semantic alignment: check how many query terms appear in result
        semantic_overlap = _assess_semantic_alignment(query, output)
        score += semantic_overlap * 0.3

    elif isinstance(output, list):
        score += min(len(output) / 5, 0.5)

    return min(score, 1.0)


def _assess_semantic_alignment(query: str, result_text: str) -> float:
    """Assess semantic alignment between query and result.

    Returns 0.0–1.0 score based on what fraction of query terms appear in result.
    Only counts words > 3 chars to filter stop words.
    """
    query_words = set(w.lower() for w in query.split() if len(w) > 3)
    result_words = set(w.lower() for w in result_text.split() if len(w) > 3)

    if not query_words:
        return 0.0

    matches = sum(1 for w in query_words if w in result_words)
    coverage = matches / len(query_words)
    return min(coverage, 1.0)


async def reflect_with_llm(
    query: str,
    tool_name: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    """Use NVIDIA NIM LLM for deeper reflection (max mode only)."""
    try:
        from loom.providers.nvidia_nim import NvidiaNimProvider

        provider = NvidiaNimProvider()
        if not await asyncio.to_thread(provider.available):
            return evaluate_result(query, tool_name, result, QualityMode.MAX)

        result_summary = _summarize_result(result)
        prompt = REFLECTION_USER.format(
            query=query, tool_name=tool_name, result_summary=result_summary
        )

        response = await asyncio.to_thread(
            provider.chat,
            messages=[
                {"role": "system", "content": REFLECTION_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=200,
            temperature=0.1,
        )

        text = response.text if hasattr(response, "text") else str(response)
        return _parse_reflection_response(text)
    except Exception as exc:
        logger.debug("LLM reflection failed: %s", exc)
        return evaluate_result(query, tool_name, result, QualityMode.MAX)


def _summarize_result(result: dict[str, Any]) -> str:
    """Create a brief summary of a tool result for LLM reflection."""
    output = result.get("result", {})
    if isinstance(output, dict):
        keys = list(output.keys())[:10]
        preview = {k: str(output[k])[:100] for k in keys}
        return json.dumps(preview, indent=2)
    elif isinstance(output, str):
        return output[:500]
    return str(output)[:500]


def _parse_reflection_response(text: str) -> dict[str, Any]:
    """Parse LLM reflection response into structured dict."""
    import re

    json_patterns = [
        re.compile(r"```json\s*\n?(.*?)\n?```", re.DOTALL),
        re.compile(r"\{[^{}]*\}"),
    ]
    for pattern in json_patterns:
        match = pattern.search(text)
        if match:
            try:
                data = json.loads(match.group(1) if match.lastindex else match.group(0))
                if "complete" in data:
                    return {
                        "complete": bool(data["complete"]),
                        "reason": data.get("reason", ""),
                        "next_action": data.get("next_action", "done"),
                    }
            except (json.JSONDecodeError, IndexError):
                continue

    if "complete" in text.lower() and "true" in text.lower():
        return {"complete": True, "reason": "LLM assessed as complete", "next_action": "done"}

    return {"complete": False, "reason": "Could not parse LLM reflection", "next_action": "done"}
