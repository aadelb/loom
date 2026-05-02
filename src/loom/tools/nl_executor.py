"""Natural Language Tool Executor - plain English instruction → tool execution → result."""

from __future__ import annotations

import importlib
import inspect
import re
import time
from typing import Any

import structlog

logger = structlog.get_logger("loom.tools.nl_executor")


TOOL_CATEGORIES = {
    "security": [
        "research_security_headers",
        "research_cert_analyzer",
        "research_breach_check",
        "research_vuln_intel",
        "research_cve_lookup",
    ],
    "search": [
        "research_search",
        "research_deep",
        "research_github",
        "research_multi_search",
    ],
    "analysis": [
        "research_hcs_scorer",
        "research_stealth_score",
        "research_model_profiler",
        "research_toxicity_checker",
        "research_fact_checker",
    ],
    "monitoring": [
        "research_change_monitor",
        "research_drift_monitor",
        "research_realtime_monitor",
    ],
    "reframing": [
        "research_prompt_reframe",
        "research_auto_reframe",
    ],
    "export": [
        "research_export_json",
        "research_export_csv",
    ],
}

ACTION_TO_CATEGORY = [
    (r"\b(evaluate|score|assess|measure)\b", "analysis"),
    (r"\b(scan|audit|check|verify)\b", "security"),
    (r"\b(search|find|discover|lookup|query)\b", "search"),
    (r"\b(analyze)\b", "analysis"),
    (r"\b(monitor|track|watch|observe)\b", "monitoring"),
    (r"\b(reframe|bypass|rephrase|transform)\b", "reframing"),
    (r"\b(export|save|download|report)\b", "export"),
]


def _extract_action(instruction: str) -> str | None:
    """Extract action verb from instruction."""
    instruction_lower = instruction.lower()
    for pattern, category in ACTION_TO_CATEGORY:
        if re.search(pattern, instruction_lower):
            return category
    return None


def _extract_url(instruction: str) -> str | None:
    """Extract URL or domain from instruction using regex."""
    url_pattern = r"https?://[^\s]+"
    match = re.search(url_pattern, instruction)
    if match:
        return match.group()

    domain_pattern = r"(?:www\.)?([a-z0-9-]+\.)+[a-z]{2,}"
    match = re.search(domain_pattern, instruction.lower())
    if match:
        return match.group()
    return None


def _extract_query(instruction: str, action_category: str) -> str:
    """Extract query/target from instruction."""
    action_pattern = r"\b(scan|audit|check|verify|analyze|search|find|discover|reframe|export|monitor|evaluate|score|assess|measure)\b\s+"
    query = re.sub(action_pattern, "", instruction, count=1, flags=re.IGNORECASE)
    return query.strip()


def _extract_number(instruction: str, default: int = 10) -> int:
    """Extract limit/count number from instruction."""
    match = re.search(r"\b(\d+)\b", instruction)
    return int(match.group(1)) if match else default


def _extract_model_name(instruction: str) -> str | None:
    """Extract model name from instruction (gpt, claude, llama, etc.)."""
    models = [
        "gpt-3.5", "gpt-4", "claude", "llama", "mistral",
        "phi", "falcon", "gemini", "deepseek", "groq",
    ]
    instruction_lower = instruction.lower()
    for model in models:
        if model in instruction_lower:
            return model
    return None


def _select_tool(
    category: str | None,
    instruction: str,
    url: str | None,
) -> str:
    """Select best tool based on category and instruction."""
    if not category:
        return "research_search"

    category_tools = TOOL_CATEGORIES.get(category, [])
    if not category_tools:
        return "research_search"

    instruction_lower = instruction.lower()
    keyword_scores = {}

    for tool in category_tools:
        tool_keywords = tool.replace("research_", "").split("_")
        score = sum(1 for kw in tool_keywords if kw in instruction_lower)
        keyword_scores[tool] = score

    best_tool = max(keyword_scores, key=keyword_scores.get) if keyword_scores else category_tools[0]
    return best_tool


async def _get_tool_function(tool_name: str) -> Any:
    """Dynamically import and return tool function."""
    try:
        parts = tool_name.split("_")
        module_name = f"loom.tools.{parts[1]}"

        module = importlib.import_module(module_name)
        return getattr(module, tool_name, None)
    except (ImportError, AttributeError) as e:
        logger.error("tool_import_failed", tool_name=tool_name, error=str(e))
        return None


async def research_do(instruction: str) -> dict:
    """Execute a plain English instruction as a research tool call.

    Maps instruction → action → tool → params → execute → result.

    Args:
        instruction: Plain English instruction like "scan example.com for headers"

    Returns:
        Dict with keys:
        - instruction: original instruction
        - tool_selected: tool function name
        - params_used: generated parameters
        - success: bool
        - result: tool output or error
        - execution_ms: execution time in milliseconds
        - alternatives: list of other tools considered
    """
    start_time = time.time()
    alternatives = []

    try:
        action_category = _extract_action(instruction)
        url = _extract_url(instruction)
        query = _extract_query(instruction, action_category or "")
        limit = _extract_number(instruction)
        model_name = _extract_model_name(instruction)

        selected_tool = _select_tool(action_category, instruction, url)
        alternatives = TOOL_CATEGORIES.get(action_category or "search", [])[:3]

        tool_func = await _get_tool_function(selected_tool)

        if not tool_func:
            return {
                "instruction": instruction,
                "tool_selected": selected_tool,
                "params_used": {},
                "success": False,
                "result": f"Tool not found or not available: {selected_tool}",
                "execution_ms": int((time.time() - start_time) * 1000),
                "alternatives": alternatives,
            }

        params = {}
        if url:
            params["url"] = url
        if query:
            params["query"] = query
        if "n" in str(tool_func.__code__.co_varnames):
            params["n"] = min(limit, 50)
        if model_name:
            if "model" in str(tool_func.__code__.co_varnames):
                params["model"] = model_name

        logger.info(
            "nl_execution_start",
            instruction=instruction,
            tool=selected_tool,
            params=params,
        )

        if inspect.iscoroutinefunction(tool_func):
            result = await tool_func(**params)
        else:
            result = tool_func(**params)

        execution_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "nl_execution_success",
            tool=selected_tool,
            execution_ms=execution_ms,
        )

        return {
            "instruction": instruction,
            "tool_selected": selected_tool,
            "params_used": params,
            "success": True,
            "result": result,
            "execution_ms": execution_ms,
            "alternatives": alternatives,
        }

    except Exception as e:
        execution_ms = int((time.time() - start_time) * 1000)
        logger.error(
            "nl_execution_failed",
            instruction=instruction,
            error=str(e),
            execution_ms=execution_ms,
        )

        return {
            "instruction": instruction,
            "tool_selected": "",
            "params_used": {},
            "success": False,
            "result": f"Execution failed: {str(e)}",
            "execution_ms": execution_ms,
            "alternatives": alternatives,
        }
