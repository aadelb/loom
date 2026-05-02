"""Pipeline Auto-Composer: generates optimal multi-tool pipelines from natural language goals.

Given a research goal (e.g., "scan for vulnerabilities in example.com"),
auto-generates an ordered, parallelizable pipeline of tools with params,
timing, and execution plan.

Algorithm:
1. DECOMPOSE goal into sub-tasks via keyword extraction
2. SELECT best tools per sub-task by matching keywords against tool registry
3. DETERMINE execution order (fetch → analysis → scoring → output)
4. IDENTIFY parallelism (tools at same stage run concurrently)
5. ESTIMATE time & cost per step
6. RETURN structured pipeline with parallelization metadata
"""

from __future__ import annotations

import asyncio
import ast
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.auto_pipeline")

# Keyword-to-tool-stage mapping
_TASK_KEYWORDS = {
    "scan": ("fetch", "security"),
    "search": ("search", "discovery"),
    "find": ("search", "discovery"),
    "analyze": ("analysis", "processing"),
    "extract": ("analysis", "processing"),
    "summarize": ("analysis", "output"),
    "report": ("output", "formatting"),
    "rank": ("scoring", "evaluation"),
    "score": ("scoring", "evaluation"),
    "profile": ("analysis", "intelligence"),
    "monitor": ("monitoring", "tracking"),
    "compare": ("analysis", "evaluation"),
}

# Stage ordering: lower numbers = earlier execution
_STAGE_ORDER = {
    "fetch": 1,
    "search": 1,
    "discovery": 1,
    "security": 2,
    "processing": 2,
    "analysis": 2,
    "intelligence": 2,
    "evaluation": 3,
    "scoring": 3,
    "ranking": 3,
    "monitoring": 3,
    "tracking": 3,
    "formatting": 4,
    "output": 4,
}

# Estimated execution time per stage (ms)
_STAGE_TIMES = {
    "fetch": 2000,
    "search": 1500,
    "discovery": 2000,
    "security": 3000,
    "processing": 1000,
    "analysis": 2000,
    "intelligence": 2500,
    "evaluation": 1500,
    "scoring": 1000,
    "ranking": 800,
    "monitoring": 4000,
    "tracking": 2000,
    "formatting": 500,
    "output": 300,
}


def _get_tool_registry() -> dict[str, dict[str, Any]]:
    """Scan tools/ directory for tool functions and their docstrings.

    Returns:
        Dict mapping tool_name → {docstring, module, category, keywords}
    """
    registry = {}
    tools_dir = Path(__file__).parent

    for py_file in tools_dir.glob("*.py"):
        if py_file.name.startswith("_") or py_file.name == "auto_pipeline.py":
            continue

        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("research_"):
                    doc = ast.get_docstring(node) or ""
                    # Extract first line as summary
                    summary = doc.split("\n")[0] if doc else ""
                    # Extract keywords from docstring
                    keywords = set(re.findall(r"\b[a-z_]+\b", summary.lower()))
                    keywords.update(re.findall(r"\b[a-z_]+\b", node.name.lower()))

                    registry[node.name] = {
                        "module": py_file.name.replace(".py", ""),
                        "summary": summary,
                        "docstring": doc,
                        "keywords": keywords,
                    }
        except Exception as e:
            logger.debug("tool_registry_scan_failed: %s: %s", py_file, e)

    return registry


def _decompose_goal(goal: str) -> list[dict[str, Any]]:
    """Decompose goal into sub-tasks via keyword extraction.

    Returns:
        List of sub-tasks: [{task, keywords, stage}]
    """
    goal_lower = goal.lower()
    tasks = []
    seen_stages = set()

    for keyword, (stage, category) in _TASK_KEYWORDS.items():
        if keyword in goal_lower:
            tasks.append(
                {
                    "task": f"{keyword} operation",
                    "keywords": [keyword],
                    "stage": stage,
                    "category": category,
                    "stage_order": _STAGE_ORDER.get(stage, 99),
                }
            )
            seen_stages.add(stage)

    # If no tasks matched, infer from general goal keywords
    if not tasks:
        if any(w in goal_lower for w in ["vulnerability", "security", "threat"]):
            tasks.append({"task": "security scan", "keywords": ["scan"], "stage": "security", "category": "security", "stage_order": 2})
        if any(w in goal_lower for w in ["research", "data", "collect"]):
            tasks.append({"task": "data collection", "keywords": ["search"], "stage": "search", "category": "discovery", "stage_order": 1})
        if not tasks:
            tasks.append({"task": "general research", "keywords": ["search"], "stage": "search", "category": "discovery", "stage_order": 1})

    # Sort by stage order
    tasks.sort(key=lambda x: x["stage_order"])
    return tasks


def _select_tools(tasks: list[dict[str, Any]], registry: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Select best tools per task by matching keywords.

    Returns:
        List of selected tools: [{tool_name, module, task, stage, keywords_matched}]
    """
    selected = []

    for task in tasks:
        task_keywords = set(task["keywords"])
        best_match = None
        best_score = 0

        for tool_name, tool_info in registry.items():
            tool_keywords = tool_info["keywords"]
            # Score based on keyword overlap + task relevance
            overlap = len(task_keywords & tool_keywords)
            if overlap > best_score or (overlap == best_score and len(tool_name) < len(best_match or "")):
                best_score = overlap
                best_match = (tool_name, tool_info)

        if best_match:
            tool_name, tool_info = best_match
            selected.append(
                {
                    "tool": tool_name,
                    "module": tool_info["module"],
                    "task": task["task"],
                    "stage": task["stage"],
                    "keywords_matched": list(task_keywords & tool_info["keywords"]),
                }
            )

    return selected


def _determine_order(selected_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Determine execution order and parallelism groups.

    Returns:
        List of tools with: step, stage, parallel_group, stage_order
    """
    # Sort by stage order
    selected_tools.sort(key=lambda t: _STAGE_ORDER.get(t["stage"], 99))

    # Assign parallel groups (tools at same stage = same group)
    parallel_groups = {}
    group_counter = 0
    current_stage = None

    for i, tool in enumerate(selected_tools):
        stage = tool["stage"]
        if stage != current_stage:
            current_stage = stage
            group_counter += 1

        tool["step"] = i + 1
        tool["parallel_group"] = group_counter
        tool["stage_order"] = _STAGE_ORDER.get(stage, 99)

    return selected_tools


def _extract_params(goal: str, tool: str) -> dict[str, str]:
    """Extract relevant parameter values from goal.

    Returns:
        Dict of parameter candidates: {param_name: value}
    """
    params = {}

    # Extract URLs
    urls = re.findall(r"https?://[^\s]+", goal)
    if urls:
        params["url"] = urls[0]
        params["urls"] = urls

    # Extract domain names
    domains = re.findall(r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}", goal)
    if domains:
        params["domain"] = domains[0]
        params["domains"] = domains

    # Extract keywords/queries
    query_match = re.search(r"(?:for|about|on|analyze)\s+([^.!?]+)", goal)
    if query_match:
        params["query"] = query_match.group(1).strip()[:100]
        params["search_term"] = query_match.group(1).strip()[:100]

    # Tool-specific params
    if "github" in tool.lower():
        params["max_results"] = "10"
    if "fetch" in tool.lower() or "spider" in tool.lower():
        params["mode"] = "stealthy"
        params["max_chars"] = "10000"
    if "search" in tool.lower():
        params["max_results"] = "5"

    return params


def _estimate_timing(tools: list[dict[str, Any]], optimize_for: str) -> dict[str, Any]:
    """Estimate execution time and cost.

    Returns:
        Dict with: total_ms, per_tool_ms, sequential_ms, parallel_ms, speedup_factor
    """
    stages = {}
    for tool in tools:
        pg = tool["parallel_group"]
        stage = tool["stage"]
        time_ms = _STAGE_TIMES.get(stage, 1000)

        if pg not in stages:
            stages[pg] = time_ms
        else:
            stages[pg] = max(stages[pg], time_ms)

    # Sequential: sum all times
    sequential_ms = sum(stages.values())
    # Parallel: max time per group
    parallel_ms = max(stages.values()) if stages else 0

    # Adjust for optimization
    if optimize_for == "speed":
        parallel_ms = int(parallel_ms * 0.7)  # Assume 30% parallel overhead reduction
    elif optimize_for == "quality":
        parallel_ms = int(parallel_ms * 1.3)  # Add time for better quality

    speedup = sequential_ms / parallel_ms if parallel_ms > 0 else 1.0

    return {
        "total_ms": parallel_ms,
        "sequential_ms": sequential_ms,
        "parallel_ms": parallel_ms,
        "speedup_factor": round(speedup, 2),
        "per_tool_ms": {t["tool"]: _STAGE_TIMES.get(t["stage"], 1000) for t in tools},
    }


async def research_auto_pipeline(
    goal: str,
    max_steps: int = 7,
    optimize_for: str = "quality",
) -> dict[str, Any]:
    """Auto-generate optimal multi-tool pipeline from a natural language goal.

    Args:
        goal: Natural language research goal (e.g. "scan example.com for vulnerabilities")
        max_steps: Maximum pipeline depth (default 7)
        optimize_for: One of "speed", "quality", "cost" (default "quality")

    Returns:
        Dict with:
        - goal: Original goal
        - pipeline: List of steps with tool, params, stage, parallel_group
        - total_steps: Number of steps
        - parallel_groups: Number of concurrent execution stages
        - estimated_total_ms: Total execution time
        - estimated_speedup_vs_sequential: Parallelization benefit
        - optimize_for: Optimization target
        - registry_size: Number of tools scanned
    """
    if not goal or len(goal) > 500:
        return {
            "error": "goal must be 1-500 characters",
            "goal": goal,
            "pipeline": [],
            "total_steps": 0,
            "parallel_groups": 0,
        }

    # Phase 1: Scan tool registry (cache-friendly)
    logger.info("auto_pipeline_start goal=%s optimize_for=%s", goal, optimize_for)
    registry = _get_tool_registry()

    # Phase 2: Decompose goal
    tasks = _decompose_goal(goal)

    # Phase 3: Select tools
    selected_tools = _select_tools(tasks, registry)

    # Phase 4: Determine order & parallelism
    ordered_tools = _determine_order(selected_tools)

    # Phase 5: Cap at max_steps
    if len(ordered_tools) > max_steps:
        ordered_tools = ordered_tools[:max_steps]

    # Phase 6: Extract params & estimate timing
    pipeline = []
    for tool in ordered_tools:
        params = _extract_params(goal, tool["tool"])
        pipeline.append(
            {
                "step": tool["step"],
                "tool": tool["tool"],
                "module": tool["module"],
                "task": tool["task"],
                "params": params,
                "stage": tool["stage"],
                "parallel_group": tool["parallel_group"],
                "keywords_matched": tool["keywords_matched"],
                "estimated_ms": _STAGE_TIMES.get(tool["stage"], 1000),
                "reason": f"Best match for {tool['task']}",
            }
        )

    # Phase 7: Timing & speedup
    timing = _estimate_timing(ordered_tools, optimize_for)

    parallel_groups = max([t["parallel_group"] for t in pipeline], default=0)

    result = {
        "goal": goal,
        "pipeline": pipeline,
        "total_steps": len(pipeline),
        "parallel_groups": parallel_groups,
        "estimated_total_ms": timing["total_ms"],
        "estimated_sequential_ms": timing["sequential_ms"],
        "estimated_speedup_vs_sequential": timing["speedup_factor"],
        "optimize_for": optimize_for,
        "registry_size": len(registry),
        "tasks_identified": len(tasks),
    }

    logger.info(
        "auto_pipeline_generated steps=%d groups=%d speedup=%.2fx",
        result["total_steps"],
        parallel_groups,
        timing["speedup_factor"],
    )

    return result
