"""Multi-tool parallel executor — run N tools concurrently."""

from __future__ import annotations

import asyncio
import importlib
import logging
import time
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("loom.tools.parallel_executor")


class ToolTask(BaseModel):
    """Single tool task specification."""

    tool: str = Field(..., description="Tool name, e.g. 'research_fetch'")
    params: dict[str, Any] = Field(default_factory=dict, description="Tool parameters")

    model_config = {"extra": "forbid", "strict": True}


class ParallelExecutorParams(BaseModel):
    """Parameters for research_parallel_execute tool."""

    tools: list[dict[str, Any]] = Field(
        ..., description="List of {'tool': 'research_xxx', 'params': {...}}"
    )
    timeout_seconds: int = Field(30, description="Timeout per tool in seconds")

    model_config = {"extra": "forbid", "strict": True}


class ParallelPlanExecutorParams(BaseModel):
    """Parameters for research_parallel_plan_and_execute tool."""

    goal: str = Field(..., description="Research goal/query")
    max_parallel: int = Field(5, description="Max concurrent tools")

    model_config = {"extra": "forbid", "strict": True}


async def research_parallel_execute(
    tools: list[dict[str, Any]] | str, timeout_seconds: int = 30
) -> dict[str, Any]:
    """Execute multiple tools in parallel.

    Args:
        tools: List of {"tool": "research_xxx", "params": {...}}
        timeout_seconds: Timeout per tool

    Returns:
        Dict with results, timing stats, and speedup factor
    """
    # Coerce string to list of dict
    if isinstance(tools, str):
        tools = [{"tool": tools, "params": {}}]

    start_time = time.perf_counter()
    results = []
    tasks = []

    for tool_spec in tools:
        tool_name = tool_spec.get("tool", "").strip()
        params = tool_spec.get("params", {})

        try:
            # Dynamically import tool module
            parts = tool_name.rsplit("_", 1)
            if len(parts) != 2 or parts[0] != "research":
                raise ValueError(f"Invalid tool name: {tool_name}")

            module_name = parts[1]
            module = importlib.import_module(f"loom.tools.{module_name}")
            func = getattr(module, tool_name, None)

            if not func:
                raise AttributeError(f"Tool {tool_name} not found in module {module_name}")

            # Wrap in asyncio.wait_for with timeout
            async def call_tool(fn, p, tn):
                tool_start = time.perf_counter()
                try:
                    result = await asyncio.wait_for(fn(**p), timeout=timeout_seconds)
                    duration = (time.perf_counter() - tool_start) * 1000
                    return {
                        "tool": tn,
                        "success": True,
                        "result": result,
                        "duration_ms": duration,
                    }
                except asyncio.TimeoutError:
                    duration = (time.perf_counter() - tool_start) * 1000
                    return {
                        "tool": tn,
                        "success": False,
                        "error": f"Timeout after {timeout_seconds}s",
                        "duration_ms": duration,
                    }
                except Exception as e:
                    duration = (time.perf_counter() - tool_start) * 1000
                    return {
                        "tool": tn,
                        "success": False,
                        "error": str(e),
                        "duration_ms": duration,
                    }

            tasks.append(call_tool(func, params, tool_name))

        except Exception as e:
            results.append(
                {
                    "tool": tool_spec.get("tool", "unknown"),
                    "success": False,
                    "error": str(e),
                    "duration_ms": 0,
                }
            )

    # Execute all tasks concurrently
    if tasks:
        task_results = await asyncio.gather(*tasks, return_exceptions=False)
        results.extend(task_results)

    total_time = (time.perf_counter() - start_time) * 1000
    sequential_estimate = sum(r.get("duration_ms", 0) for r in results)
    speedup = sequential_estimate / total_time if total_time > 0 else 0

    successes = sum(1 for r in results if r.get("success", False))
    failures = len(results) - successes

    return {
        "total": len(results),
        "successes": successes,
        "failures": failures,
        "results": results,
        "total_duration_ms": round(total_time, 2),
        "sequential_estimate_ms": round(sequential_estimate, 2),
        "speedup_factor": round(speedup, 2),
    }


async def research_parallel_plan_and_execute(
    goal: str, max_parallel: int = 5
) -> dict[str, Any]:
    """Plan and execute relevant tools in parallel based on goal.

    Args:
        goal: Research goal or query
        max_parallel: Max concurrent tools to run

    Returns:
        Dict with selected tools, results, and speedup
    """
    # Tool keyword mapping for intelligent selection
    tool_keywords = {
        "research_fetch": [
            "fetch",
            "download",
            "page",
            "website",
            "url",
            "html",
            "content",
        ],
        "research_spider": [
            "crawl",
            "multi",
            "batch",
            "urls",
            "links",
            "spider",
        ],
        "research_search": ["search", "find", "query", "discover", "query"],
        "research_github": ["github", "repo", "code", "open source"],
        "research_deep": ["deep", "comprehensive", "full", "detailed", "analysis"],
        "research_llm_summarize": [
            "summarize",
            "summary",
            "brief",
            "tldr",
            "extract",
        ],
    }

    goal_lower = goal.lower()
    selected_tools = []

    for tool_name, keywords in tool_keywords.items():
        if any(kw in goal_lower for kw in keywords):
            selected_tools.append(tool_name)

    # Default to search if no matches
    if not selected_tools:
        selected_tools = ["research_search"]

    # Limit to max_parallel
    selected_tools = selected_tools[:max_parallel]

    # Build tool specs with goal as input
    tool_specs = [{"tool": tool, "params": {"goal": goal}} for tool in selected_tools]

    # Execute in parallel
    result = await research_parallel_execute(tool_specs, timeout_seconds=30)

    return {
        "goal": goal,
        "tools_selected": selected_tools,
        "results": result["results"],
        "speedup_factor": result["speedup_factor"],
        "total_duration_ms": result["total_duration_ms"],
    }
