"""Tool Composition Optimizer — finds fastest/cheapest path through multi-tool workflows."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("loom.tools.composition_optimizer")

# Tool metadata: execution time (ms), cost (relative), category, dependencies
TOOL_METADATA: dict[str, dict[str, Any]] = {
    "research_search": {"time": 800, "cost": 0.5, "category": "search", "deps": []},
    "research_fetch": {"time": 2000, "cost": 0.3, "category": "fetch", "deps": []},
    "research_spider": {"time": 3500, "cost": 0.8, "category": "fetch", "deps": []},
    "research_deep": {"time": 5000, "cost": 1.2, "category": "search", "deps": ["research_search", "research_fetch"]},
    "research_markdown": {"time": 1500, "cost": 0.4, "category": "fetch", "deps": ["research_fetch"]},
    "research_llm_summarize": {"time": 2500, "cost": 2.0, "category": "llm", "deps": []},
    "research_llm_extract": {"time": 1800, "cost": 1.5, "category": "llm", "deps": []},
    "research_llm_classify": {"time": 1200, "cost": 1.0, "category": "llm", "deps": []},
    "research_github": {"time": 1000, "cost": 0.1, "category": "search", "deps": []},
    "research_cache_stats": {"time": 100, "cost": 0.0, "category": "cache", "deps": []},
}

# Goal-to-tool mapping for common research scenarios
GOAL_PATTERNS: dict[str, list[str]] = {
    "academic": ["research_search", "research_deep", "research_markdown", "research_llm_extract"],
    "technical": ["research_github", "research_search", "research_fetch", "research_llm_classify"],
    "comprehensive": ["research_deep", "research_spider", "research_markdown", "research_llm_summarize"],
    "fast": ["research_search", "research_llm_classify"],
    "cost_efficient": ["research_search", "research_fetch", "research_llm_classify"],
    "multilingual": ["research_search", "research_fetch", "research_markdown", "research_llm_translate"],
}


@dataclass
class WorkflowStep:
    """Single step in optimized workflow."""

    step: int
    tool: str
    reason: str
    estimated_ms: int


@dataclass
class ParallelGroup:
    """Group of tools that can execute in parallel."""

    group_id: int
    tools: list[str]
    estimated_ms: int


def _extract_goal_keywords(goal: str) -> list[str]:
    """Extract keywords from goal to match patterns."""
    return goal.lower().split()


def _match_goal_pattern(goal: str) -> list[str]:
    """Find best matching goal pattern."""
    keywords = _extract_goal_keywords(goal)
    scores: dict[str, int] = {}

    for pattern_name, tools in GOAL_PATTERNS.items():
        pattern_keywords = pattern_name.split("_")
        score = sum(1 for kw in keywords if kw in pattern_keywords)
        if score > 0:
            scores[pattern_name] = score

    if not scores:
        return GOAL_PATTERNS["comprehensive"]

    best_pattern = max(scores.keys(), key=lambda x: scores[x])
    return GOAL_PATTERNS[best_pattern]


def _topological_sort(tools: list[str]) -> list[str]:
    """Sort tools respecting dependencies (topological order)."""
    visited = set()
    result = []

    def visit(tool: str) -> None:
        if tool in visited:
            return
        visited.add(tool)
        meta = TOOL_METADATA.get(tool, {})
        for dep in meta.get("deps", []):
            if dep in tools:
                visit(dep)
        result.append(tool)

    for tool in tools:
        visit(tool)
    return result


def _find_parallel_groups(tools: list[str]) -> list[list[str]]:
    """Partition tools into groups that can run in parallel."""
    sorted_tools = _topological_sort(tools)
    groups: list[list[str]] = []
    completed = set()

    for tool in sorted_tools:
        meta = TOOL_METADATA.get(tool, {})
        deps = set(meta.get("deps", []))

        if deps.issubset(completed):
            groups.append([tool])
            completed.add(tool)

    # Merge independent tools into same group
    merged = []
    for group in groups:
        if not merged:
            merged.append(group)
        else:
            last_group = merged[-1]
            last_deps = set()
            for t in last_group:
                last_deps.update(TOOL_METADATA.get(t, {}).get("deps", []))

            tool = group[0]
            tool_deps = set(TOOL_METADATA.get(tool, {}).get("deps", []))

            if not (tool_deps & set(last_group)) and not (last_deps & {tool}):
                last_group.append(tool)
            else:
                merged.append(group)

    return merged


async def research_optimize_workflow(
    goal: str,
    available_tools: list[str] | None = None,
    optimize_for: str = "speed",
) -> dict[str, Any]:
    """Find optimal tool combination for research goal.

    Args:
        goal: Research goal description (e.g., "find academic papers on AI safety")
        available_tools: Restrict to specific tools, or None for all
        optimize_for: "speed" (minimize ms), "cost" (minimize cost), or "quality" (comprehensive)

    Returns:
        Optimized workflow with steps and metadata
    """
    # Match goal to tool pattern
    matched_tools = _match_goal_pattern(goal)

    # Filter to available tools
    if available_tools:
        matched_tools = [t for t in matched_tools if t in available_tools]

    # Topologically sort by dependencies
    sorted_tools = _topological_sort(matched_tools)

    # Sort by optimization criterion
    if optimize_for == "cost":
        sorted_tools.sort(key=lambda t: TOOL_METADATA.get(t, {}).get("cost", 999))
    elif optimize_for == "speed":
        sorted_tools.sort(key=lambda t: TOOL_METADATA.get(t, {}).get("time", 9999))
    # "quality" keeps all matched tools

    # Build workflow steps with reasons
    steps: list[WorkflowStep] = []
    total_ms = 0
    for idx, tool in enumerate(sorted_tools, 1):
        meta = TOOL_METADATA.get(tool, {})
        time_ms = meta.get("time", 1000)
        reason = f"[{meta.get('category', 'unknown')}] {tool.replace('research_', '')}"
        steps.append(WorkflowStep(step=idx, tool=tool, reason=reason, estimated_ms=time_ms))
        total_ms += time_ms

    return {
        "goal": goal,
        "optimization_strategy": optimize_for,
        "optimized_workflow": [
            {
                "step": s.step,
                "tool": s.tool,
                "reason": s.reason,
                "estimated_ms": s.estimated_ms,
            }
            for s in steps
        ],
        "total_estimated_ms": total_ms,
        "tool_count": len(sorted_tools),
    }


async def research_parallel_plan(tools: list[str]) -> dict[str, Any]:
    """Determine parallel vs sequential execution plan.

    Args:
        tools: List of tools to execute

    Returns:
        Execution plan with parallel groups and speedup factor
    """
    # Find parallel groups
    parallel_groups = _find_parallel_groups(tools)

    # Compute sequential chains (longest path through dependency graph)
    sequential_chains: list[list[str]] = []
    visited = set()

    for tool in tools:
        if tool not in visited:
            chain = [tool]
            meta = TOOL_METADATA.get(tool, {})
            for dep in meta.get("deps", []):
                if dep in tools:
                    chain.insert(0, dep)
            sequential_chains.append(chain)
            visited.update(chain)

    # Estimate speedup: sequential total / parallel critical path
    sequential_total_ms = sum(
        TOOL_METADATA.get(t, {}).get("time", 1000) for t in tools
    )
    parallel_critical_ms = max(
        sum(TOOL_METADATA.get(t, {}).get("time", 1000) for t in group)
        for group in parallel_groups
    )
    speedup = sequential_total_ms / max(parallel_critical_ms, 1)

    return {
        "total_tools": len(tools),
        "parallel_groups": parallel_groups,
        "sequential_chains": sequential_chains,
        "estimated_speedup_factor": round(speedup, 2),
        "execution_plan": {
            "phase": "parallel_then_sequential",
            "group_count": len(parallel_groups),
            "estimated_parallel_ms": parallel_critical_ms,
            "estimated_sequential_ms": sequential_total_ms,
        },
    }
