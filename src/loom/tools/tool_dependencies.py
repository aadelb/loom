"""Tool dependency graph and execution planning for research tool pipelines.

Provides:
1. DEPENDENCY_GRAPH: Maps each tool to its prerequisite tools
2. research_tool_dependencies(): Returns dependency graph for a tool
3. get_execution_plan(): Computes parallel groups in execution order
4. resolve_dependencies(): Transitively resolves all prerequisites
5. validate_execution_order(): Validates tool execution is topologically sorted

This enables intelligent pipeline composition: execute prerequisites in parallel
within each group, then move to the next group sequentially.

Example:
    >>> plan = get_execution_plan(['research_deep', 'research_llm_summarize'])
    >>> for group in plan:
    ...     # Execute all tools in group in parallel
    ...     results = await asyncio.gather(*[execute(t) for t in group])
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from typing import Any

from loom.error_responses import handle_tool_errors
logger = logging.getLogger("loom.tools.tool_dependencies")


# ─────────────────────────────────────────────────────────────────────────────
# Core Dependency Graph
# ─────────────────────────────────────────────────────────────────────────────

DEPENDENCY_GRAPH: dict[str, list[str]] = {
    # Research core tools (lowest level, no dependencies)
    "research_fetch": [],
    "research_spider": [],
    "research_search": [],
    "research_github": [],
    "research_markdown": [],
    "research_session_open": [],
    "research_session_list": [],
    "research_session_close": [],
    "research_config_get": [],
    "research_config_set": [],
    "research_health_check": [],
    # LLM tools (low level, can work standalone)
    "research_llm_summarize": [],
    "research_llm_extract": [],
    "research_llm_classify": [],
    "research_llm_translate": [],
    "research_llm_expand": [],
    "research_llm_answer": [],
    "research_llm_embed": [],
    "research_llm_chat": [],
    # Deep research pipeline (depends on search + fetch)
    "research_deep": [
        "research_search",
        "research_fetch",
        "research_markdown",
    ],
    # Spider depends on fetch + markdown for enrichment
    "research_spider_enrich": [
        "research_spider",
        "research_markdown",
    ],
    # Multi-source search combining multiple providers
    "research_multi_search": [
        "research_search",
    ],
    # GitHub research (standalone but benefits from markdown processing)
    "research_github_repo_analysis": [
        "research_github",
        "research_markdown",
    ],
    # Stealth tools (cascade escalation)
    "research_camoufox": [],
    "research_botasaurus": [],
    # Cache management (standalone utilities)
    "research_cache_stats": [],
    "research_cache_clear": [],
    # Scrapling variants (all independent)
    "research_fetch_http": [],
    "research_fetch_stealthy": [],
    "research_fetch_dynamic": [],
    # ─────────────────────────────────────────────────────────────────────────
    # Enrichment & Analysis (Level 1: depend on fetch/search)
    # ─────────────────────────────────────────────────────────────────────────
    # Knowledge graph extraction (depends on fetch content)
    "research_knowledge_graph": [
        "research_fetch",
    ],
    # Fact checking (depends on LLM + fetch)
    "research_fact_check": [
        "research_llm_classify",
        "research_fetch",
    ],
    # Sentiment analysis (depends on fetch content + LLM)
    "research_sentiment_analysis": [
        "research_llm_classify",
        "research_fetch",
    ],
    # ─────────────────────────────────────────────────────────────────────────
    # Intelligence & Analysis Tools (Level 2: depend on deep research)
    # ─────────────────────────────────────────────────────────────────────────
    # OSINT tools (depend on fetch/search)
    "research_passive_recon": [
        "research_search",
    ],
    "research_infrastructure_correlator": [
        "research_search",
        "research_fetch",
    ],
    "research_threat_profiling": [
        "research_fetch",
        "research_search",
    ],
    # Darkweb tools (depend on search)
    "research_dark_forum_search": [
        "research_search",
    ],
    "research_onion_discovery": [
        "research_search",
    ],
    "research_darkweb_early_warning": [
        "research_search",
    ],
    # Metadata & forensics (depend on fetch)
    "research_metadata_forensics": [
        "research_fetch",
    ],
    "research_stego_detection": [
        "research_fetch",
    ],
    # Leak & breach scanning (depends on search)
    "research_leak_scan": [
        "research_search",
    ],
    # Crypto & blockchain (depends on search)
    "research_crypto_trace": [
        "research_search",
    ],
    # ─────────────────────────────────────────────────────────────────────────
    # Advanced Pipelines (Level 3: depend on multiple lower tools)
    # ─────────────────────────────────────────────────────────────────────────
    # Full pipeline: search → fetch → markdown → analyze → summarize
    "research_full_pipeline": [
        "research_search",
        "research_fetch",
        "research_markdown",
        "research_llm_summarize",
    ],
    # Intelligence pipeline: search → correlate → profile → summarize
    "research_intelligence_pipeline": [
        "research_search",
        "research_infrastructure_correlator",
        "research_threat_profiling",
        "research_llm_summarize",
    ],
    # Security audit pipeline: search → recon → threat profiling → report
    "research_security_audit_pipeline": [
        "research_search",
        "research_passive_recon",
        "research_threat_profiling",
        "research_llm_summarize",
    ],
    # Academic research pipeline: search (arxiv) → fetch → extract → summarize
    "research_academic_pipeline": [
        "research_search",
        "research_fetch",
        "research_llm_extract",
        "research_llm_summarize",
    ],
    # ─────────────────────────────────────────────────────────────────────────
    # Pipeline Enhancement & Orchestration (Level 4: depend on pipelines)
    # ─────────────────────────────────────────────────────────────────────────
    # Pipeline enhancer (wraps any tool with enrichment)
    "research_enhance": [
        "research_llm_summarize",
    ],
    # Batch enhancement (wrapper around multiple tools)
    "research_enhance_batch": [
        "research_enhance",
    ],
    # Tool orchestration (orchestrates tool execution)
    "research_orchestrate": [
        "research_deep",
        "research_full_pipeline",
    ],
    "research_orchestrate_smart": [
        "research_orchestrate",
        "research_enhance",
    ],
    # ─────────────────────────────────────────────────────────────────────────
    # Dependency Analysis Tools
    # ─────────────────────────────────────────────────────────────────────────
    "research_tool_dependencies": [],
    "research_tool_impact": [],
}


# ─────────────────────────────────────────────────────────────────────────────
# Public API Functions
# ─────────────────────────────────────────────────────────────────────────────

@handle_tool_errors("research_tool_dependencies")

async def research_tool_dependencies(
    tool_name: str,
) -> dict[str, Any]:
    """Get all dependencies for a single tool.

    Args:
        tool_name: Name of the tool (e.g., 'research_deep')

    Returns:
        Dict with keys:
        - tool: str (input tool name)
        - direct_deps: list[str] (immediate prerequisites)
        - transitive_deps: list[str] (all prerequisites recursively)
        - execution_order: list[list[str]] (parallel groups in execution order)
        - total_prerequisite_count: int
        - is_leaf_tool: bool (True if no dependencies)
        - can_run_standalone: bool (always True for this module)
    """
    try:
        if tool_name not in DEPENDENCY_GRAPH:
            return {
                "tool": tool_name,
                "error": f"Unknown tool: {tool_name}",
                "direct_deps": [],
                "transitive_deps": [],
                "execution_order": [],
                "total_prerequisite_count": 0,
                "is_leaf_tool": True,
                "can_run_standalone": True,
            }

        direct_deps = DEPENDENCY_GRAPH[tool_name]
        transitive_deps = resolve_dependencies([tool_name])
        transitive_deps.discard(tool_name)  # Don't include self

        execution_order = get_execution_plan([tool_name])
        # Remove the tool itself from all execution groups
        execution_order = [
            [t for t in group if t != tool_name]
            for group in execution_order
        ]
        # Remove empty groups
        execution_order = [group for group in execution_order if group]

        return {
            "tool": tool_name,
            "direct_deps": direct_deps,
            "transitive_deps": sorted(transitive_deps),
            "execution_order": execution_order,
            "total_prerequisite_count": len(transitive_deps),
            "is_leaf_tool": len(direct_deps) == 0,
            "can_run_standalone": True,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_tool_dependencies"}

@handle_tool_errors("research_get_execution_plan")

async def research_get_execution_plan(
    tools: list[str],
) -> dict[str, Any]:
    """Compute optimal execution plan for multiple tools.

    Resolves all dependencies and returns them in parallel groups,
    where tools in the same group can execute simultaneously.

    Args:
        tools: List of tool names to execute

    Returns:
        Dict with keys:
        - requested_tools: list[str]
        - execution_plan: list[list[str]] (parallel groups in order)
        - all_tools_needed: list[str] (all unique tools including deps)
        - total_groups: int
        - sequential_critical_path: list[str] (longest dependency chain)
        - parallelizable_count: int (tools that can run in parallel)
    """
    try:
        all_deps = resolve_dependencies(tools)
        execution_groups = get_execution_plan(tools)
        critical_path = _find_critical_path(tools)
        parallelizable = sum(len(group) for group in execution_groups if len(group) > 1)

        return {
            "requested_tools": tools,
            "execution_plan": execution_groups,
            "all_tools_needed": sorted(all_deps),
            "total_groups": len(execution_groups),
            "sequential_critical_path": critical_path,
            "parallelizable_count": parallelizable,
            "estimated_speedup": (len(all_deps) / len(critical_path)) if critical_path else 1.0,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_get_execution_plan"}


def get_execution_plan(tools: list[str]) -> list[list[str]]:
    """Compute parallel execution groups for tools in topological order.

    Returns a list of lists, where each inner list contains tools that can
    execute in parallel (no dependencies between them in that group).

    Algorithm:
    1. Resolve all transitive dependencies
    2. Group by level (depth from leaves)
    3. Return groups from deepest (level 0) to shallowest

    Args:
        tools: List of tool names to execute

    Returns:
        List of parallel execution groups in order
    """
    all_deps = resolve_dependencies(tools)

    # Compute depth (level) for each tool
    depths: dict[str, int] = {}
    visited = set()

    def compute_depth(tool: str) -> int:
        if tool in visited:
            return depths.get(tool, 0)
        visited.add(tool)

        deps = DEPENDENCY_GRAPH.get(tool, [])
        if not deps:
            depths[tool] = 0
            return 0

        max_dep_depth = max(compute_depth(dep) for dep in deps) if deps else 0
        depths[tool] = max_dep_depth + 1
        return depths[tool]

    # Compute depth for all tools
    for tool in all_deps:
        compute_depth(tool)

    # Group by depth (level)
    groups_by_level: dict[int, list[str]] = defaultdict(list)
    for tool in all_deps:
        level = depths.get(tool, 0)
        groups_by_level[level].append(tool)

    # Return groups from deepest to shallowest
    max_level = max(depths.values()) if depths else 0
    execution_groups = []
    for level in range(max_level + 1):
        group = sorted(groups_by_level[level])
        if group:
            execution_groups.append(group)

    return execution_groups


def resolve_dependencies(tools: list[str]) -> set[str]:
    """Transitively resolve all dependencies for a list of tools.

    Uses BFS to find all direct and indirect prerequisites.

    Args:
        tools: List of tool names

    Returns:
        Set of all tool names (input + all prerequisites)
    """
    visited = set(tools)
    queue = deque(tools)

    while queue:
        current_tool = queue.popleft()
        deps = DEPENDENCY_GRAPH.get(current_tool, [])

        for dep in deps:
            if dep not in visited:
                visited.add(dep)
                queue.append(dep)

    return visited


def validate_execution_order(execution_plan: list[list[str]]) -> dict[str, Any]:
    """Validate that an execution plan respects tool dependencies.

    Args:
        execution_plan: List of parallel groups from get_execution_plan()

    Returns:
        Dict with:
        - valid: bool (True if all dependencies are satisfied)
        - violations: list[str] (dependency violations if any)
        - issues: list[str] (other issues)
    """
    violations = []
    issues = []
    executed = set()

    for group_idx, group in enumerate(execution_plan):
        # Check that all tools in this group have no inter-group dependencies
        for tool in group:
            deps = DEPENDENCY_GRAPH.get(tool, [])
            for dep in deps:
                if dep not in executed:
                    violations.append(
                        f"Tool {tool} (group {group_idx}) depends on {dep} "
                        f"which hasn't been executed yet"
                    )

        # Mark all tools in this group as executed
        executed.update(group)

    if not violations:
        for tool_list in execution_plan:
            if len(tool_list) != len(set(tool_list)):
                issues.append(f"Duplicate tools in group: {tool_list}")

    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "issues": issues,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Private Helper Functions
# ─────────────────────────────────────────────────────────────────────────────


def _find_critical_path(tools: list[str]) -> list[str]:
    """Find the longest dependency chain (critical path).

    The critical path determines the minimum sequential execution time,
    since all tools in parallel chains can execute concurrently.

    Args:
        tools: List of tool names

    Returns:
        List of tools in the longest dependency chain
    """
    # Memoization for path computation
    memo: dict[str, list[str]] = {}

    def longest_path_from(tool: str) -> list[str]:
        if tool in memo:
            return memo[tool]

        deps = DEPENDENCY_GRAPH.get(tool, [])
        if not deps:
            memo[tool] = [tool]
            return [tool]

        longest = max(
            (longest_path_from(dep) for dep in deps),
            key=len,
            default=[],
        )
        path = longest + [tool]
        memo[tool] = path
        return path

    # Find longest path from any of the requested tools
    all_paths = [longest_path_from(t) for t in tools]
    return max(all_paths, key=len, default=[])


# ─────────────────────────────────────────────────────────────────────────────
# Integration Hooks for Pipeline Composer
# ─────────────────────────────────────────────────────────────────────────────


async def prepare_tool_execution(
    requested_tools: list[str],
) -> dict[str, Any]:
    """Prepare tools for execution with dependency resolution.

    This is the main hook for pipeline_enhancer.py and orchestrator.py.

    Args:
        requested_tools: List of tool names the user wants to execute

    Returns:
        Dict with:
        - requested_tools: Original list
        - execution_plan: Parallel groups in order
        - all_tools: All tools to execute (including dependencies)
        - first_group: First group of tools to execute now
        - remaining_groups: Groups to execute after first group completes
        - dependency_warnings: Any issues found
    """
    try:
        # Validate inputs
        invalid = [t for t in requested_tools if t not in DEPENDENCY_GRAPH]
        if invalid:
            logger.warning(f"Unknown tools requested: {invalid}")

        # Resolve dependencies
        all_tools = resolve_dependencies(requested_tools)
        execution_plan = get_execution_plan(requested_tools)

        # Extract groups
        first_group = execution_plan[0] if execution_plan else []
        remaining_groups = execution_plan[1:] if len(execution_plan) > 1 else []

        # Validate the plan
        validation = validate_execution_order(execution_plan)
        warnings = validation.get("violations", []) + validation.get("issues", [])

        return {
            "requested_tools": requested_tools,
            "execution_plan": execution_plan,
            "all_tools": sorted(all_tools),
            "first_group": first_group,
            "remaining_groups": remaining_groups,
            "dependency_warnings": warnings,
            "valid": validation["valid"],
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "prepare_tool_execution"}


# ─────────────────────────────────────────────────────────────────────────────
# Diagnostics & Reporting
# ─────────────────────────────────────────────────────────────────────────────

@handle_tool_errors("research_dependency_graph_stats")

async def research_dependency_graph_stats() -> dict[str, Any]:
    """Return statistics about the dependency graph.

    Returns:
        Dict with graph metrics
    """
    try:
        all_tools = set(DEPENDENCY_GRAPH.keys())
        all_edges = sum(len(deps) for deps in DEPENDENCY_GRAPH.values())

        # Find leaf tools (no dependencies)
        leaf_tools = [t for t in all_tools if not DEPENDENCY_GRAPH[t]]

        # Find root tools (nothing depends on them)
        depends_on_me: dict[str, set[str]] = defaultdict(set)
        for tool, deps in DEPENDENCY_GRAPH.items():
            for dep in deps:
                depends_on_me[dep].add(tool)

        root_tools = [t for t in all_tools if not depends_on_me[t]]

        # Compute dependency depth (critical path length)
        depths: dict[str, int] = {}
        visited_global = set()

        def compute_max_depth(tool: str) -> int:
            if tool in depths:
                return depths[tool]
            if tool in visited_global:
                # Circular dependency detected
                raise ValueError(
                    f"Circular dependency detected in graph involving tool: {tool}"
                )
            visited_global.add(tool)

            deps = DEPENDENCY_GRAPH.get(tool, [])
            if not deps:
                depths[tool] = 0
                return 0

            max_dep_depth = max((compute_max_depth(d) for d in deps), default=0)
            depths[tool] = max_dep_depth + 1
            return depths[tool]

        for tool in all_tools:
            compute_max_depth(tool)

        max_depth = max(depths.values()) if depths else 0
        avg_depth = sum(depths.values()) / len(depths) if depths else 0

        return {
            "total_tools": len(all_tools),
            "total_dependencies": all_edges,
            "leaf_tools_count": len(leaf_tools),
            "leaf_tools": sorted(leaf_tools),
            "root_tools_count": len(root_tools),
            "root_tools": sorted(root_tools),
            "max_dependency_depth": max_depth,
            "avg_dependency_depth": round(avg_depth, 2),
            "graph_density": round(all_edges / (len(all_tools) * (len(all_tools) - 1) / 2) if all_tools else 0, 4),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_dependency_graph_stats"}
