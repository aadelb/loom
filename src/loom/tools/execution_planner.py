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
    """Select tools by category, ordered by efficiency (lowest time/cost ratio first)."""
    candidates = []

    # Collect all matching tools from all categories
    for category in categories:
        for tool_name, info in TOOL_REGISTRY.items():
            if info["category"] == category:
                candidates.append((tool_name, info))

    if not candidates and max_tools > 0:
        candidates.append(("research_search", TOOL_REGISTRY["research_search"]))

    # Sort by efficiency: lowest time_ms per USD cost.
    # For zero-cost tools, treat as infinite efficiency (sort first).
    def efficiency_key(item: tuple[str, dict[str, Any]]) -> tuple[int, float]:
        _, info = item
        cost = info["cost_usd"]
        time = info["time_ms"]
        # Sort free tools first (cost=0 → sort_key=(0, time))
        # Paid tools by ratio (cost>0 → sort_key=(1, time/cost))
        if cost == 0:
            return (0, time)
        return (1, time / cost)

    candidates.sort(key=efficiency_key)
    return candidates[:max_tools]


async def research_plan_execution(
    goal: str,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate an execution plan for a research goal.

    Args:
        goal: research goal or query (must be non-empty string)
        constraints: dict with optional keys:
            - max_time_minutes: max execution time (default: 30)
            - max_cost_usd: max cost budget (default: 0.10)
            - max_tools: max tools in plan (default: 5)

    Returns:
        Dict with:
        - goal: original goal
        - plan: list of execution steps with tool, time, cost, reason
        - total_estimated_time_ms: combined time in ms (sequential estimate)
        - total_estimated_cost_usd: combined cost in USD
        - constraints_met: bool indicating if plan respects constraints
    """
    try:
        # Validate goal
        if not goal or not isinstance(goal, str):
            return {
                "error": f"goal must be non-empty string, got {type(goal).__name__ if goal is not None else 'None'}",
                "tool": "research_plan_execution",
            }

        constraints = constraints or {}

        # Validate and extract constraints
        try:
            max_time_minutes = float(constraints.get("max_time_minutes", 30))
            max_cost_usd = float(constraints.get("max_cost_usd", 0.10))
            max_tools = int(constraints.get("max_tools", 5))

            if max_time_minutes <= 0 or max_cost_usd < 0 or max_tools <= 0:
                return {
                    "error": "Constraints must be positive (max_time_minutes > 0, max_cost_usd >= 0, max_tools > 0)",
                    "tool": "research_plan_execution",
                }
        except (TypeError, ValueError) as e:
            return {"error": f"Invalid constraint type: {str(e)}", "tool": "research_plan_execution"}

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
            goal[:50] if len(goal) > 50 else goal,
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
        logger.exception("Error in plan_execution")
        return {"error": str(exc), "tool": "research_plan_execution"}


async def research_plan_validate(
    steps: list[dict[str, Any]] | None = None,
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

        # Validate input type
        if steps is None or not isinstance(steps, list):
            issues.append({"step": 0, "issue": "steps must be a list"})
            return {"valid": False, "issues": issues, "warnings": warnings, "optimizations": optimizations}

        if not steps:
            issues.append({"step": 0, "issue": "Plan is empty"})
            return {"valid": False, "issues": issues, "warnings": warnings, "optimizations": optimizations}

        seen_tools = set()
        dependency_graph: dict[int, list[int]] = {}  # step -> list of dependencies

        # First pass: validate structure and collect dependencies
        for idx, step in enumerate(steps, 1):
            if not isinstance(step, dict):
                issues.append({"step": idx, "issue": f"Step must be a dict, got {type(step).__name__}"})
                continue

            if "tool" not in step:
                issues.append({"step": idx, "issue": "Missing 'tool' key"})
                continue

            tool = step["tool"]

            if not isinstance(tool, str):
                issues.append({"step": idx, "issue": f"tool must be string, got {type(tool).__name__}"})
                continue

            if tool not in TOOL_REGISTRY:
                warnings.append(f"Step {idx}: Tool '{tool}' not in registry (may be custom)")

            if tool in seen_tools:
                optimizations.append(f"Step {idx}: Tool '{tool}' already used; consider deduplication")

            seen_tools.add(tool)

            # Validate and normalize depends_on
            if "depends_on" in step:
                dep = step["depends_on"]
                normalized_deps = []

                if isinstance(dep, int):
                    normalized_deps = [dep]
                elif isinstance(dep, list):
                    for d in dep:
                        if not isinstance(d, int):
                            issues.append(
                                {"step": idx, "issue": f"Dependency step must be int, got {type(d).__name__}"}
                            )
                        else:
                            normalized_deps.append(d)
                else:
                    issues.append(
                        {"step": idx, "issue": f"depends_on must be int or list, got {type(dep).__name__}"}
                    )

                # Validate dependency references are in range
                for d in normalized_deps:
                    if d < 1 or d > len(steps):
                        issues.append(
                            {"step": idx, "issue": f"Dependency step {d} out of range [1, {len(steps)}]"}
                        )
                    elif d >= idx:
                        issues.append(
                            {"step": idx, "issue": f"Forward dependency on step {d} (must be <=  {idx - 1})"}
                        )

                dependency_graph[idx] = normalized_deps

        # Second pass: detect cycles using DFS
        visited: set[int] = set()
        rec_stack: set[int] = set()

        def has_cycle(node: int) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for dep in dependency_graph.get(node, []):
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for step_num in range(1, len(steps) + 1):
            visited.clear()
            rec_stack.clear()
            if has_cycle(step_num):
                issues.append(
                    {"step": step_num, "issue": f"Circular dependency detected starting at step {step_num}"}
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
        logger.exception("Error in plan_validate")
        return {"error": str(exc), "tool": "research_plan_validate"}
