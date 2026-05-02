"""Auto-generate workflows covering ALL tool categories using AST introspection."""

from __future__ import annotations

import ast
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.workflow_expander")

# Category keywords for tool classification
CATEGORY_KEYWORDS = {
    "security": ["security", "vuln", "scan", "breach", "cert", "cve", "exploit"],
    "osint": ["identity", "social", "recon", "graph", "intel", "profile"],
    "adversarial": ["attack", "reframe", "bypass", "inject", "craft", "debate"],
    "research": ["search", "deep", "fetch", "arxiv", "scrape", "crawl", "fetch"],
    "infrastructure": ["deploy", "backup", "monitor", "health", "check", "pool"],
    "analysis": ["score", "analyze", "detect", "compare", "profile", "estimate"],
}

# Logical order: fetch → process → analyze → report
TOOL_ORDER = ["fetch", "search", "process", "detect", "analyze", "score", "report"]


def _get_tool_modules() -> dict[str, str]:
    """Scan tools/ directory and return {module_name: file_path}."""
    tools_dir = Path(__file__).parent
    modules = {}

    for file in tools_dir.glob("*.py"):
        name = file.stem
        if not name.startswith("_"):
            modules[name] = str(file)

    return modules


def _categorize_tool(module_name: str) -> str:
    """Classify tool by module name into a category."""
    lower_name = module_name.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lower_name for kw in keywords):
            return category

    return "other"


def _extract_tool_functions(file_path: str) -> list[str]:
    """Extract async def research_* functions from a module using AST."""
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())

        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef):
                if node.name.startswith("research_"):
                    functions.append(node.name)

        return functions
    except Exception as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
        return []


async def research_workflow_generate(
    category: str = "auto",
    max_steps: int = 6,
) -> dict[str, Any]:
    """Auto-generate workflows for given tool category.

    If category="auto", generates workflows for all categories with coverage.
    Otherwise, generates a single workflow for the specified category.

    Args:
        category: Tool category ("security", "osint", "adversarial", "research",
                 "infrastructure", "analysis", "other", or "auto" for all)
        max_steps: Maximum workflow steps per workflow (default: 6)

    Returns:
        Dict with keys:
          - if category != "auto": {category, workflow: list[{step, tool, description}], tools_covered}
          - if category == "auto": {workflows: dict[category, workflow], total_tools_covered, coverage_pct}
    """
    modules = _get_tool_modules()

    # Build category → tools mapping
    category_tools: dict[str, list[tuple[str, list[str]]]] = {}
    for module_name, file_path in modules.items():
        cat = _categorize_tool(module_name)
        tools = _extract_tool_functions(file_path)

        if tools:
            if cat not in category_tools:
                category_tools[cat] = []
            category_tools[cat].append((module_name, tools))

    if category == "auto":
        # Generate workflows for all categories
        all_workflows = {}
        total_covered = 0

        for cat in sorted(category_tools.keys()):
            tools_for_cat = category_tools[cat]
            workflow_steps = _build_workflow(cat, tools_for_cat, max_steps)

            tools_in_workflow = len([t for step in workflow_steps for t in [step["tool"]]])
            all_workflows[cat] = {
                "category": cat,
                "workflow": workflow_steps,
                "tools_covered": tools_in_workflow,
            }
            total_covered += tools_in_workflow

        return {
            "workflows": all_workflows,
            "total_tools_covered": total_covered,
            "categories": len(all_workflows),
            "coverage_pct": round((total_covered / len(modules)) * 100, 1) if modules else 0,
        }
    else:
        # Generate single category workflow
        if category not in category_tools:
            return {
                "error": f"Category '{category}' not found. Available: {list(category_tools.keys())}"
            }

        tools_for_cat = category_tools[category]
        workflow_steps = _build_workflow(category, tools_for_cat, max_steps)
        tools_in_workflow = len([t for step in workflow_steps for t in [step["tool"]]])

        return {
            "category": category,
            "workflow": workflow_steps,
            "tools_covered": tools_in_workflow,
        }


def _build_workflow(
    category: str,
    tools_for_cat: list[tuple[str, list[str]]],
    max_steps: int,
) -> list[dict[str, Any]]:
    """Build a workflow for a category by ordering tools logically."""
    workflow = []
    step = 1

    # Flatten and sort tools by order heuristic
    all_tools = []
    for module_name, funcs in tools_for_cat:
        for func in funcs:
            all_tools.append((module_name, func))

    # Sort by tool order heuristic
    def tool_sort_key(item: tuple[str, str]) -> int:
        _, func_name = item
        for i, order_word in enumerate(TOOL_ORDER):
            if order_word in func_name.lower():
                return i
        return len(TOOL_ORDER)

    all_tools.sort(key=tool_sort_key)

    # Build steps (up to max_steps)
    for module_name, func_name in all_tools[:max_steps]:
        desc = func_name.replace("research_", "").replace("_", " ").title()
        workflow.append({
            "step": step,
            "tool": func_name,
            "module": module_name,
            "description": f"Execute {desc}",
            "condition": "success_from_previous" if step > 1 else None,
        })
        step += 1

    return workflow


async def research_workflow_coverage() -> dict[str, Any]:
    """Report workflow coverage across all tools and categories.

    Scans all tool modules via AST and reports which tools are covered
    by workflows vs uncovered.

    Returns:
        Dict with keys:
          - total_tools: Total unique research_* functions found
          - covered: Tools in workflows (count)
          - uncovered: List of uncovered tools
          - coverage_pct: Coverage percentage (0-100)
          - uncovered_by_category: Dict mapping category → uncovered tools
          - categories_analyzed: Total categories found
    """
    modules = _get_tool_modules()

    # Extract all tools
    all_tools: dict[str, list[str]] = {}
    category_map: dict[str, str] = {}

    for module_name, file_path in modules.items():
        tools = _extract_tool_functions(file_path)
        cat = _categorize_tool(module_name)

        for tool in tools:
            all_tools[tool] = module_name
            category_map[tool] = cat

    # Run workflow generation to get covered tools
    gen_result = await research_workflow_generate(category="auto", max_steps=6)

    covered_tools = set()
    if "workflows" in gen_result:
        for cat_workflow in gen_result["workflows"].values():
            for step in cat_workflow["workflow"]:
                covered_tools.add(step["tool"])

    # Calculate coverage
    uncovered = sorted([t for t in all_tools.keys() if t not in covered_tools])

    # Group uncovered by category
    uncovered_by_category: dict[str, list[str]] = {}
    for tool in uncovered:
        cat = category_map[tool]
        if cat not in uncovered_by_category:
            uncovered_by_category[cat] = []
        uncovered_by_category[cat].append(tool)

    return {
        "total_tools": len(all_tools),
        "covered": len(covered_tools),
        "uncovered": uncovered,
        "coverage_pct": round((len(covered_tools) / len(all_tools)) * 100, 1) if all_tools else 0,
        "uncovered_by_category": uncovered_by_category,
        "categories_analyzed": len(set(category_map.values())),
    }
