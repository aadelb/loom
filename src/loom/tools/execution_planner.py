"""Tool Execution Planner — generates and validates optimal execution plans for complex queries."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("loom.tools.execution_planner")


# Tool registry with categories and estimated metrics
TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "research_fetch": {"category": "fetch", "time_ms": 3000, "cost_usd": 0.001},
    "research_spider": {"category": "fetch", "time_ms": 5000, "cost_usd": 0.002},
    "research_markdown": {"category": "fetch", "time_ms": 2000, "cost_usd": 0.001},
    "research_search": {"category": "search", "time_ms": 1500, "cost_usd": 0.002},
    "research_deep": {"category": "deep", "time_ms": 8000, "cost_usd": 0.005},
    "research_github": {"category": "search", "time_ms": 1000, "cost_usd": 0.0},
    "research_ask_all_llms": {"category": "llm", "time_ms": 4000, "cost_usd": 0.01},
    "research_llm_summarize": {"category": "llm", "time_ms": 2000, "cost_usd": 0.005},
    "research_camoufox": {"category": "fetch", "time_ms": 6000, "cost_usd": 0.003},
    "research_botasaurus": {"category": "fetch", "time_ms": 7000, "cost_usd": 0.004},
}

KEYWORD_MAPPING: dict[str, list[str]] = {
    "search": ["search", "find", "discover", "locate"],
    "fetch": ["fetch", "scrape", "get", "retrieve", "extract"],
    "deep": ["deep", "research", "comprehensive", "thorough"],
    "llm": ["summarize", "analyze", "classify", "generate", "ask"],
    "github": ["github", "repo", "code", "commit"],
}


def _categorize_goal(goal: str) -> list[str]:
    """Match goal keywords to tool categories."""
    goal_lower = goal.lower()
    matched = set()

    for category, keywords in KEYWORD_MAPPING.items():
        if any(kw in goal_lower for kw in keywords):
            matched.add(category)

    return list(matched) if matched else ["search"]


def _select_tools(
    categories: list[str],
    max_tools: int,
) -> list[tuple[str, dict[str, Any]]]:
    """Select tools by category, ordered by efficiency."""
    selected = []

    for category in categories:
        for tool_name, info in TOOL_REGISTRY.items():
            if info["category"] == category and len(selected) < max_tools:
                selected.append((tool_name, info))

    if not selected and max_tools > 0:
        selected.append(("research_search", TOOL_REGISTRY["research_search"]))

    selected.sort(key=lambda x: x[1]["time_ms"] / (x[1]["cost_usd"] + 0.001))
    return selected[:max_tools]


async def research_plan_execution(
    goal: str,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate an execution plan for a research goal.

    Args:
        goal: research goal or query
        constraints: dict with optional keys:
            - max_time_minutes: max execution time (default: 30)
            - max_cost_usd: max cost budget (default: 0.10)
            - max_tools: max tools in plan (default: 5)

    Returns:
        Dict with:
        - goal: original goal
        - plan: list of execution steps with tool, time, cost, reason
        - total_estimated_time: combined time in ms
        - total_estimated_cost: combined cost in USD
        - constraints_met: bool indicating if plan respects constraints
    """
    try:
        constraints = constraints or {}
        max_time_minutes = constraints.get("max_time_minutes", 30)
        max_cost_usd = constraints.get("max_cost_usd", 0.10)
        max_tools = constraints.get("max_tools", 5)

        categories = _categorize_goal(goal)
        tools = _select_tools(categories, max_tools)

        plan = []
        total_time = 0
        total_cost = 0.0

        for step_num, (tool_name, info) in enumerate(tools, 1):
            step_time = info["time_ms"]
            step_cost = info["cost_usd"]
            total_time += step_time
            total_cost += step_cost

            plan.append(
                {
                    "step": step_num,
                    "tool": tool_name,
                    "estimated_time_ms": step_time,
                    "estimated_cost": step_cost,
                    "reason": f"Matched category '{info['category']}' from goal keywords",
                }
            )

        max_time_ms = max_time_minutes * 60 * 1000
        constraints_met = total_time <= max_time_ms and total_cost <= max_cost_usd

        logger.info(
            "plan_execution goal=%s tools=%d time=%dms cost=$%.4f constraints_met=%s",
            goal[:50],
            len(plan),
            total_time,
            total_cost,
            constraints_met,
        )

        return {
            "goal": goal,
            "plan": plan,
            "total_estimated_time_ms": total_time,
            "total_estimated_cost_usd": total_cost,
            "constraints_met": constraints_met,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_plan_execution"}


async def research_plan_validate(
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate an execution plan for issues.

    Args:
        steps: list of plan step dicts with 'tool' and optional 'depends_on'

    Returns:
        Dict with:
        - valid: bool indicating if plan is valid
        - issues: list of dicts with 'step' and 'issue' description
        - warnings: list of warning strings
        - optimizations: list of suggested improvements
    """
    try:
        issues = []
        warnings = []
        optimizations = []

        if not steps:
            issues.append({"step": 0, "issue": "Plan is empty"})
            return {"valid": False, "issues": issues, "warnings": warnings, "optimizations": optimizations}

        seen_tools = set()
        for idx, step in enumerate(steps, 1):
            if "tool" not in step:
                issues.append({"step": idx, "issue": "Missing 'tool' key"})
                continue

            tool = step["tool"]

            if tool not in TOOL_REGISTRY:
                warnings.append(f"Step {idx}: Tool '{tool}' not in registry (may be custom)")

            if tool in seen_tools:
                optimizations.append(f"Step {idx}: Tool '{tool}' already used; consider deduplication")

            seen_tools.add(tool)

            if "depends_on" in step:
                dep = step["depends_on"]
                if isinstance(dep, list):
                    for d in dep:
                        if d > idx:
                            issues.append(
                                {"step": idx, "issue": f"Circular/forward dependency on step {d}"}
                            )

        valid = len(issues) == 0
        logger.info(
            "plan_validate steps=%d valid=%s issues=%d warnings=%d",
            len(steps),
            valid,
            len(issues),
            len(warnings),
        )

        return {
            "valid": valid,
            "issues": issues,
            "warnings": warnings,
            "optimizations": optimizations,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_plan_validate"}
