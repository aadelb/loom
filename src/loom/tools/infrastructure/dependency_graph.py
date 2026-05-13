"""Tool dependency graph analysis — maps inter-tool dependencies."""
from __future__ import annotations

import ast
import logging
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.dependency_graph")


def _extract_tool_imports(source_code: str) -> set[str]:
    """Extract loom.tools.* imports from Python source code."""
    imports = set()
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("loom.tools."):
                    module_name = node.module.split("loom.tools.")[-1]
                    imports.add(module_name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("loom.tools."):
                        module_name = alias.name.split("loom.tools.")[-1]
                        imports.add(module_name)
    except (SyntaxError, ValueError):
        logger.warning("Failed to parse source code for tool imports")
    return imports


@handle_tool_errors("research_dependency_graph")
async def research_dependency_graph() -> dict[str, Any]:
    """Analyze tool modules to find inter-tool dependencies.

    Scans src/loom/tools/*.py for imports of other tool modules,
    builds adjacency list, and computes statistics.

    Returns:
        Dict with keys:
        - nodes: int (total tool modules found)
        - edges: int (total dependencies)
        - dependencies: dict[str, list[str]] (adjacency list)
        - most_depended_on: list[dict] (tools with highest dependent count)
        - isolated_tools: list[str] (tools with no dependencies)
    """
    tools_dir = Path(__file__).parent
    graph: dict[str, set[str]] = defaultdict(set)

    # Scan all .py files in tools directory
    for tool_file in sorted(tools_dir.glob("*.py")):
        if tool_file.name == "__init__.py":
            continue

        module_name = tool_file.stem
        try:
            source = tool_file.read_text(encoding="utf-8")
            imports = _extract_tool_imports(source)
            graph[module_name] = imports
        except Exception as e:
            logger.warning("Failed to analyze %s: %s", module_name, e)

    # Convert to adjacency list and compute reverse dependency graph
    dependencies = {k: sorted(v) for k, v in graph.items()}
    reverse_graph: dict[str, set[str]] = defaultdict(set)

    for module, deps in dependencies.items():
        for dep in deps:
            if dep in dependencies:  # Only count valid tool modules
                reverse_graph[dep].add(module)

    # Find most depended-on tools
    dependents_count = [
        {"module": mod, "dependents_count": len(reverse_graph[mod])}
        for mod in reverse_graph
        if reverse_graph[mod]
    ]
    most_depended_on = sorted(dependents_count, key=lambda x: x["dependents_count"], reverse=True)[:10]

    # Find isolated tools (no dependencies)
    isolated = [mod for mod in dependencies if not dependencies[mod]]

    return {
        "nodes": len(dependencies),
        "edges": sum(len(deps) for deps in dependencies.values()),
        "dependencies": dependencies,
        "most_depended_on": most_depended_on,
        "isolated_tools": sorted(isolated),
    }


@handle_tool_errors("research_tool_impact")
async def research_tool_impact(tool_name: str) -> dict[str, Any]:
    """Show what would break if a tool failed.

    Given a tool module name, traverses the dependency graph to find
    all downstream dependents (direct and transitive).

    Args:
        tool_name: Tool module name (e.g., 'fetch', 'search')

    Returns:
        Dict with keys:
        - tool: str (input tool name)
        - direct_dependents: list[str] (tools that directly depend on this)
        - transitive_dependents: list[str] (all tools transitively dependent)
        - impact_score: float (0-10 scale based on dependent count)
        - safe_to_modify: bool (True if safe to modify without breaking others)
    """
    tools_dir = Path(__file__).parent
    graph: dict[str, set[str]] = defaultdict(set)

    # Build dependency graph
    for tool_file in sorted(tools_dir.glob("*.py")):
        if tool_file.name == "__init__.py":
            continue

        module_name = tool_file.stem
        try:
            source = tool_file.read_text(encoding="utf-8")
            imports = _extract_tool_imports(source)
            graph[module_name] = imports
        except Exception:
            pass

    # Build reverse graph (who depends on whom)
    reverse_graph: dict[str, set[str]] = defaultdict(set)
    for module, deps in graph.items():
        for dep in deps:
            if dep in graph:
                reverse_graph[dep].add(module)

    # BFS to find all transitive dependents
    direct = sorted(reverse_graph.get(tool_name, set()))
    visited = set(direct)
    queue = deque(direct)
    transitive = set()

    while queue:
        current = queue.popleft()
        for dependent in reverse_graph.get(current, set()):
            if dependent not in visited:
                visited.add(dependent)
                transitive.add(dependent)
                queue.append(dependent)

    total_dependents = len(visited)
    impact_score = min(10.0, total_dependents / 2.0)
    safe_to_modify = total_dependents == 0

    return {
        "tool": tool_name,
        "direct_dependents": direct,
        "transitive_dependents": sorted(transitive),
        "impact_score": round(impact_score, 2),
        "safe_to_modify": safe_to_modify,
    }
