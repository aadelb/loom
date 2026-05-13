"""Pipeline Auto-Composer: generates optimal multi-tool pipelines from natural language goals.

Given a research goal (e.g., "scan for vulnerabilities"), auto-generates an ordered,
parallelizable pipeline of tools with params, timing, and execution plan.

Algorithm: Decompose → Select tools → Determine order → Identify parallelism → Estimate time.
"""

from __future__ import annotations

import ast
import logging
import re
from pathlib import Path
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.auto_pipeline")

# Keyword-to-stage mapping
_STAGES = {
    "scan": "fetch",
    "search": "search",
    "find": "search",
    "analyze": "analysis",
    "extract": "analysis",
    "summarize": "output",
    "report": "output",
    "rank": "scoring",
    "score": "scoring",
    "profile": "analysis",
    "monitor": "monitoring",
    "compare": "analysis",
}

_STAGE_ORDER = {
    "fetch": 1,
    "search": 1,
    "security": 2,
    "processing": 2,
    "analysis": 2,
    "intelligence": 2,
    "evaluation": 3,
    "scoring": 3,
    "monitoring": 3,
    "output": 4,
}

_STAGE_TIMES = {s: {1: 2000, 2: 2000, 3: 1500, 4: 500}.get(_STAGE_ORDER.get(s, 99), 1000) for s in _STAGE_ORDER}


def _get_tool_registry() -> dict[str, dict[str, Any]]:
    """Scan tools/ directory via AST for tool functions and docstrings."""
    registry = {}
    tools_dir = Path(__file__).parent

    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name.startswith("_") or py_file.name == "auto_pipeline.py":
            continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("research_"):
                    doc = ast.get_docstring(node) or ""
                    summary = doc.split("\n")[0]
                    keywords = set(re.findall(r"\b[a-z_]+\b", (summary + " " + node.name).lower()))
                    registry[node.name] = {"module": py_file.stem, "keywords": keywords}
        except Exception as e:
            logger.debug("scan_failed: %s: %s", py_file.name, e)

    return registry


def _decompose(goal: str) -> list[dict[str, Any]]:
    """Decompose goal into sub-tasks via keyword extraction."""
    goal_lower = goal.lower()
    tasks = []

    for keyword, stage in _STAGES.items():
        if keyword in goal_lower:
            tasks.append({"keyword": keyword, "stage": stage, "order": _STAGE_ORDER.get(stage, 99)})

    if not tasks:
        # Default to search if no keywords matched
        tasks.append({"keyword": "search", "stage": "search", "order": 1})

    tasks.sort(key=lambda x: x["order"])
    return tasks


def _select_tools(tasks: list[dict[str, Any]], registry: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Select best tools per task by keyword overlap."""
    selected = []

    for task in tasks:
        task_kw = {task["keyword"]}
        best_tool = None
        best_score = 0

        for tool_name, info in registry.items():
            overlap = len(task_kw & info["keywords"])
            if overlap > best_score:
                best_score = overlap
                best_tool = tool_name

        if not best_tool:
            best_tool = next(iter(registry.keys())) if registry else "research_search"

        tool_info = registry.get(best_tool, {"module": "search", "keywords": set()})
        selected.append({
            "tool": best_tool,
            "module": tool_info["module"],
            "stage": task["stage"],
        })

    return selected


def _order_and_parallelize(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign execution order and parallel groups."""
    tools.sort(key=lambda t: _STAGE_ORDER.get(t["stage"], 99))

    group = 0
    current_stage = None

    for i, tool in enumerate(tools):
        if tool["stage"] != current_stage:
            current_stage = tool["stage"]
            group += 1

        tool["step"] = i + 1
        tool["parallel_group"] = group
        tool["stage_order"] = _STAGE_ORDER.get(tool["stage"], 99)

    return tools


def _extract_params(goal: str, tool: str) -> dict[str, str]:
    """Extract relevant parameters from goal."""
    params = {}

    urls = re.findall(r"https?://[^\s]+", goal)
    if urls:
        params["url"] = urls[0]
        params["urls"] = urls

    domains = re.findall(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}", goal)
    if domains:
        params["domain"] = domains[0]
        params["domains"] = domains

    query_match = re.search(r"(?:for|about|on|analyze)\s+([^.!?]+)", goal)
    if query_match:
        query = query_match.group(1).strip()[:100]
        params["query"] = query
        params["search_term"] = query

    if "github" in tool.lower():
        params["max_results"] = "10"
    if "fetch" in tool.lower() or "spider" in tool.lower():
        params["mode"] = "stealthy"
    if "search" in tool.lower():
        params["max_results"] = "5"

    return params


def _estimate_time(tools: list[dict[str, Any]], optimize_for: str) -> dict[str, Any]:
    """Estimate execution time and speedup."""
    stages = {}
    for tool in tools:
        stage = tool["stage"]
        time_ms = _STAGE_TIMES.get(stage, 1000)
        pg = tool["parallel_group"]

        if pg not in stages:
            stages[pg] = time_ms
        else:
            stages[pg] = max(stages[pg], time_ms)

    sequential_ms = sum(_STAGE_TIMES.get(t["stage"], 1000) for t in tools)
    parallel_ms = sum(stages.values()) if stages else 0

    # Apply optimization
    if optimize_for == "speed":
        parallel_ms = int(parallel_ms * 0.7)
    elif optimize_for == "quality":
        parallel_ms = int(parallel_ms * 1.3)

    speedup = sequential_ms / parallel_ms if parallel_ms > 0 else 1.0

    return {
        "total_ms": parallel_ms,
        "sequential_ms": sequential_ms,
        "speedup": round(speedup, 2),
    }


@handle_tool_errors("research_auto_pipeline")
async def research_auto_pipeline(
    goal: str,
    max_steps: int = 7,
    optimize_for: str = "quality",
) -> dict[str, Any]:
    """Auto-generate optimal multi-tool pipeline from a natural language goal.

    Args:
        goal: Natural language research goal (e.g., "scan example.com for vulnerabilities")
        max_steps: Maximum pipeline depth (default 7)
        optimize_for: One of "speed", "quality", "cost" (default "quality")

    Returns:
        Dict with goal, pipeline (list of steps), timing, parallelization info, metadata.
    """
    if not goal or len(goal) > 500:
        return {
            "error": "goal must be 1-500 characters",
            "goal": goal,
            "pipeline": [],
            "total_steps": 0,
            "parallel_groups": 0,
        }

    logger.info("auto_pipeline_start goal=%s optimize_for=%s", goal, optimize_for)

    # Phase 1-3: Decompose, select, order
    registry = _get_tool_registry()
    tasks = _decompose(goal)
    tools = _select_tools(tasks, registry)
    tools = _order_and_parallelize(tools)

    if len(tools) > max_steps:
        tools = tools[:max_steps]

    # Phase 4-5: Extract params and estimate
    pipeline = []
    for tool in tools:
        params = _extract_params(goal, tool["tool"])
        pipeline.append({
            "step": tool["step"],
            "tool": tool["tool"],
            "module": tool["module"],
            "task": f"{tool['stage']} operation",
            "params": params,
            "stage": tool["stage"],
            "parallel_group": tool["parallel_group"],
            "keywords_matched": list({tool["stage"]}),
            "estimated_ms": _STAGE_TIMES.get(tool["stage"], 1000),
            "reason": f"Best match for {tool['stage']} task",
        })

    timing = _estimate_time(tools, optimize_for)
    parallel_groups = max([t["parallel_group"] for t in tools], default=0) if tools else 0

    result = {
        "goal": goal,
        "pipeline": pipeline,
        "total_steps": len(pipeline),
        "parallel_groups": parallel_groups,
        "estimated_total_ms": timing["total_ms"],
        "estimated_sequential_ms": timing["sequential_ms"],
        "estimated_speedup_vs_sequential": timing["speedup"],
        "optimize_for": optimize_for,
        "registry_size": len(registry),
        "tasks_identified": len(tasks),
    }

    logger.info(
        "auto_pipeline_generated steps=%d groups=%d speedup=%.2fx",
        result["total_steps"],
        parallel_groups,
        timing["speedup"],
    )

    return result
