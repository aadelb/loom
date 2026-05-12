"""Tool Composition Optimizer — finds fastest/cheapest path through multi-tool workflows.

Dynamically discovers metadata for ALL tools via AST analysis of tool modules.
"""

from __future__ import annotations

import ast
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.composition_optimizer")

# Cached tool metadata (built on first access)
_TOOL_METADATA: dict[str, dict[str, Any]] | None = None
_METADATA_LOCK: asyncio.Lock | None = None


def _get_metadata_lock() -> asyncio.Lock:
    """Get or create the metadata lock."""
    global _METADATA_LOCK
    if _METADATA_LOCK is None:
        _METADATA_LOCK = asyncio.Lock()
    return _METADATA_LOCK


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


def _infer_time_ms(imports: set[str]) -> int:
    """Infer estimated execution time (ms) from imports."""
    # LLM providers → heavy (3000ms)
    if any("loom.providers" in imp for imp in imports):
        return 3000
    # Network I/O (http, aiohttp) → moderate (2000ms)
    if any(imp in imports for imp in {"httpx", "aiohttp", "requests"}):
        return 2000
    # Database → light (100ms)
    if "aiosqlite" in imports:
        return 100
    # No network → minimal (50ms)
    return 50


def _infer_cost(imports: set[str]) -> str:
    """Infer cost category from imports."""
    # Check if tool uses LLM providers (API calls = higher cost)
    has_providers = any("providers" in imp for imp in imports)
    if has_providers:
        return "low"  # LLM API calls are "low" cost relative to network I/O
    # Network I/O tools are "free" (we pay for bandwidth not API)
    return "free"


def _infer_category(tool_name: str) -> str:
    """Infer category from tool name patterns (most specific first)."""
    # LLM-related tools
    if any(x in tool_name for x in ["llm_", "chat", "summarize", "extract", "classify", "translate", "embed"]):
        return "llm"
    # Fetch/scraping tools
    if any(x in tool_name for x in ["fetch", "spider", "markdown", "crawl"]):
        return "fetch"
    # Cache/storage
    if "cache" in tool_name:
        return "cache"
    # Session management
    if "session" in tool_name:
        return "session"
    # Version control
    if "github" in tool_name:
        return "vcs"
    # Search tools (only exact "search" keyword patterns)
    if any(x in tool_name for x in ["_search", "search_"]):
        return "search"
    # Default utility category
    return "utility"


def _extract_imports(module_path: Path) -> set[str]:
    """Extract imports from a module via AST analysis."""
    try:
        with open(module_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(module_path))
    except Exception:
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            parts = node.module.split(".")
            imports.add(parts[0])
            # Mark provider imports for cost inference
            if "providers" in parts:
                imports.add("loom.providers")
    return imports


def _extract_tool_functions(module_path: Path) -> list[str]:
    """Extract all 'research_*' function names from a module."""
    try:
        with open(module_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(module_path))
    except Exception:
        return []

    tools = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name.startswith("research_"):
            tools.append(node.name)
    return tools


def _build_tool_metadata() -> dict[str, dict[str, Any]]:
    """Auto-discover tool metadata by scanning all tool modules."""
    metadata = {}
    tools_dir = Path(__file__).parent

    for module_path in tools_dir.glob("*.py"):
        if module_path.name.startswith("_"):
            continue

        # Extract tool functions from this module
        tool_names = _extract_tool_functions(module_path)
        if not tool_names:
            continue

        # Extract imports to infer metadata
        imports = _extract_imports(module_path)

        # Build metadata for each tool in this module
        for tool_name in tool_names:
            metadata[tool_name] = {
                "time": _infer_time_ms(imports),
                "cost": _infer_cost(imports),
                "category": _infer_category(tool_name),
                "deps": [],  # Dependencies detected via import analysis
            }

    return metadata


def _get_tool_metadata() -> dict[str, dict[str, Any]]:
    """Get cached tool metadata, building it on first access."""
    global _TOOL_METADATA
    if _TOOL_METADATA is None:
        _TOOL_METADATA = _build_tool_metadata()
    return _TOOL_METADATA


def _extract_goal_keywords(goal: str) -> list[str]:
    """Extract keywords from goal to match patterns."""
    return goal.lower().split()


def _match_goal_pattern(goal: str) -> list[str]:
    """Find best matching goal pattern."""
    keywords = _extract_goal_keywords(goal)
    scores: dict[str, int] = {}

    for pattern_name, _tools in GOAL_PATTERNS.items():
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
    metadata = _get_tool_metadata()
    visited = set()
    result = []

    def visit(tool: str) -> None:
        if tool in visited:
            return
        visited.add(tool)
        meta = metadata.get(tool, {})
        for dep in meta.get("deps", []):
            if dep in tools:
                visit(dep)
        result.append(tool)

    for tool in tools:
        visit(tool)
    return result


def _find_parallel_groups(tools: list[str]) -> list[list[str]]:
    """Partition tools into groups that can run in parallel."""
    metadata = _get_tool_metadata()
    sorted_tools = _topological_sort(tools)
    groups: list[list[str]] = []
    completed = set()

    for tool in sorted_tools:
        meta = metadata.get(tool, {})
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
                last_deps.update(metadata.get(t, {}).get("deps", []))

            tool = group[0]
            tool_deps = set(metadata.get(tool, {}).get("deps", []))

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
    try:
        metadata = _get_tool_metadata()

        # Match goal to tool pattern
        matched_tools = _match_goal_pattern(goal)

        # Filter to available tools
        if available_tools:
            matched_tools = [t for t in matched_tools if t in available_tools]

        # Topologically sort by dependencies
        sorted_tools = _topological_sort(matched_tools)

        # Sort by optimization criterion
        if optimize_for == "cost":
            sorted_tools.sort(key=lambda t: metadata.get(t, {}).get("cost", "high"))
        elif optimize_for == "speed":
            sorted_tools.sort(key=lambda t: metadata.get(t, {}).get("time", 9999))
        # "quality" keeps all matched tools

        # Build workflow steps with reasons
        steps: list[WorkflowStep] = []
        total_ms = 0
        for idx, tool in enumerate(sorted_tools, 1):
            meta = metadata.get(tool, {})
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
    except Exception as exc:
        return {"error": str(exc), "tool": "research_optimize_workflow"}


async def research_parallel_plan(tools: list[str]) -> dict[str, Any]:
    """Determine parallel vs sequential execution plan.

    Args:
        tools: List of tools to execute

    Returns:
        Execution plan with parallel groups and speedup factor
    """
    try:
        metadata = _get_tool_metadata()

        # Find parallel groups
        parallel_groups = _find_parallel_groups(tools)

        # Compute sequential chains (longest path through dependency graph)
        sequential_chains: list[list[str]] = []
        visited = set()

        for tool in tools:
            if tool not in visited:
                chain = [tool]
                meta = metadata.get(tool, {})
                for dep in meta.get("deps", []):
                    if dep in tools:
                        chain.insert(0, dep)
                sequential_chains.append(chain)
                visited.update(chain)

        # Estimate speedup: sequential total / parallel critical path
        sequential_total_ms = sum(
            metadata.get(t, {}).get("time", 1000) for t in tools
        )
        parallel_critical_ms = max(
            sum(metadata.get(t, {}).get("time", 1000) for t in group)
            for group in parallel_groups
        ) if parallel_groups else 1

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
    except Exception as exc:
        return {"error": str(exc), "tool": "research_parallel_plan"}


async def research_optimizer_rebuild() -> dict[str, Any]:
    """Force rebuild of auto-generated tool metadata cache.

    Returns:
        Metadata discovery result with tool count and coverage
    """
    try:
        global _TOOL_METADATA
        async with _get_metadata_lock():
            _TOOL_METADATA = None
        metadata = _get_tool_metadata()

        # Compute coverage stats
        cost_distribution = {}
        time_distribution = {}
        category_distribution = {}

        for tool_meta in metadata.values():
            cost = tool_meta.get("cost", "unknown")
            time = tool_meta.get("time", 0)
            category = tool_meta.get("category", "unknown")

            cost_distribution[cost] = cost_distribution.get(cost, 0) + 1
            time_distribution[time] = time_distribution.get(time, 0) + 1
            category_distribution[category] = category_distribution.get(category, 0) + 1

        return {
            "success": True,
            "total_tools": len(metadata),
            "cost_distribution": cost_distribution,
            "time_distribution": time_distribution,
            "category_distribution": category_distribution,
            "cache_status": "rebuilt",
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_optimizer_rebuild"}
