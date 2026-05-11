"""Auto-generate workflows covering ALL tool categories using AST introspection."""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.workflow_expander")

# Category keywords for tool classification
CATEGORY_KEYWORDS = {
    "security": ["security", "vuln", "scan", "breach", "cert", "cve", "exploit"],
    "osint": ["identity", "social", "recon", "graph", "intel", "profile"],
    "adversarial": ["attack", "reframe", "bypass", "inject", "craft", "debate"],
    "research": ["search", "deep", "fetch", "arxiv", "scrape", "crawl"],
    "infrastructure": ["deploy", "backup", "monitor", "health", "check", "pool"],
    "analysis": ["score", "analyze", "detect", "compare", "profile", "estimate"],
}

# Logical order: fetch → process → analyze → report
TOOL_ORDER = ["fetch", "search", "process", "detect", "analyze", "score", "report"]


def _get_tool_modules() -> dict[str, str]:
    """Scan tools/ directory and return {module_name: file_path}."""
    tools_dir = Path(__file__).parent
    return {f.stem: str(f) for f in tools_dir.glob("*.py") if not f.stem.startswith("_")}


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
        tree = ast.parse(Path(file_path).read_text())
        return [
            node.name
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("research_")
        ]
    except Exception as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
        return []


def _build_workflow(
    category: str,
    tools_for_cat: list[tuple[str, list[str]]],
    max_steps: int,
) -> list[dict[str, Any]]:
    """Build a workflow for a category by ordering tools logically."""
    all_tools = [
        (module_name, func)
        for module_name, funcs in tools_for_cat
        for func in funcs
    ]

    def tool_sort_key(item: tuple[str, str]) -> int:
        _, func_name = item
        for i, order_word in enumerate(TOOL_ORDER):
            if order_word in func_name.lower():
                return i
        return len(TOOL_ORDER)

    all_tools.sort(key=tool_sort_key)

    return [
        {
            "step": i + 1,
            "tool": func_name,
            "module": module_name,
            "description": f"Execute {func_name.replace('research_', '').replace('_', ' ').title()}",
            "condition": "success_from_previous" if i > 0 else None,
        }
        for i, (module_name, func_name) in enumerate(all_tools[:max_steps])
    ]


async def research_workflow_generate(
    category: str = "auto",
    max_steps: int = 6,
) -> dict[str, Any]:
    """Auto-generate workflows for given tool category.

    If category="auto", generates workflows for all categories.
    Otherwise, generates a single workflow for the specified category.

    Args:
        category: Tool category ("security", "osint", "adversarial", "research",
                 "infrastructure", "analysis", "other", or "auto" for all)
        max_steps: Maximum workflow steps per workflow (default: 6)

    Returns:
        Single category: {category, workflow: list[{step, tool, description}], tools_covered}
        Auto mode: {workflows: dict[category, workflow], total_tools_covered, coverage_pct}
    """
    try:
        modules = _get_tool_modules()
        category_tools: dict[str, list[tuple[str, list[str]]]] = {}

        for module_name, file_path in modules.items():
            tools = _extract_tool_functions(file_path)
            if tools:
                cat = _categorize_tool(module_name)
                category_tools.setdefault(cat, []).append((module_name, tools))

        if category == "auto":
            all_workflows = {}
            total_covered = 0
            for cat in sorted(category_tools.keys()):
                workflow_steps = _build_workflow(cat, category_tools[cat], max_steps)
                tools_in_workflow = len(workflow_steps)
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
            if category not in category_tools:
                return {"error": f"Category '{category}' not found. Available: {list(category_tools.keys())}"}

            workflow_steps = _build_workflow(category, category_tools[category], max_steps)
            return {
                "category": category,
                "workflow": workflow_steps,
                "tools_covered": len(workflow_steps),
            }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_workflow_generate"}


async def research_workflow_coverage() -> dict[str, Any]:
    """Report workflow coverage across all tools and categories.

    Scans all tool modules via AST and reports coverage metrics.

    Returns:
        Dict with:
          - total_tools: Total unique research_* functions found
          - covered: Tools in workflows (count)
          - uncovered: List of uncovered tools
          - coverage_pct: Coverage percentage (0-100)
          - uncovered_by_category: Dict mapping category → uncovered tools
          - categories_analyzed: Total categories found
    """
    try:
        modules = _get_tool_modules()
        all_tools: dict[str, str] = {}
        category_map: dict[str, str] = {}

        for module_name, file_path in modules.items():
            for tool in _extract_tool_functions(file_path):
                all_tools[tool] = module_name
                category_map[tool] = _categorize_tool(module_name)

        # Get covered tools from auto-generated workflows
        gen_result = await research_workflow_generate(category="auto", max_steps=6)
        covered_tools = {
            step["tool"]
            for cat_workflow in gen_result.get("workflows", {}).values()
            for step in cat_workflow.get("workflow", [])
        }

        # Calculate uncovered tools
        uncovered = sorted(t for t in all_tools if t not in covered_tools)

        # Group uncovered by category
        uncovered_by_category: dict[str, list[str]] = {}
        for tool in uncovered:
            uncovered_by_category.setdefault(category_map[tool], []).append(tool)

        return {
            "total_tools": len(all_tools),
            "covered": len(covered_tools),
            "uncovered": uncovered,
            "coverage_pct": round((len(covered_tools) / len(all_tools)) * 100, 1) if all_tools else 0,
            "uncovered_by_category": uncovered_by_category,
            "categories_analyzed": len(set(category_map.values())),
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_workflow_coverage"}
