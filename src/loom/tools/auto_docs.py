"""Auto-documentation generator for research tools.

Introspects tool signatures to generate markdown documentation and coverage reports.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.auto_docs")


def _extract_tool_metadata(file_path: Path) -> list[dict[str, Any]]:
    """Extract metadata for all research_* functions from a Python file."""
    try:
        tree = ast.parse(file_path.read_text())
    except Exception as e:
        logger.warning("Failed to parse %s: %s", file_path, e)
        return []

    tools = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) or not node.name.startswith("research_"):
            continue

        docstring = ast.get_docstring(node)
        first_line = (docstring.split("\n")[0] if docstring else None) or "No description"
        params = [arg.arg for arg in node.args.args]
        return_type = ast.unparse(node.returns) if node.returns else "dict"

        tools.append({
            "name": node.name,
            "docstring": first_line,
            "parameters": params,
            "return_type": return_type,
            "file": file_path.name,
        })

    return tools


async def research_generate_docs(
    output_format: str = "markdown",
    include_params: bool = True,
) -> dict[str, Any]:
    """Generate auto-documentation for all registered tools.

    Scans src/loom/tools/*.py and generates markdown or JSON documentation
    by introspecting async function signatures starting with "research_".

    Args:
        output_format: "markdown" (default) or "json"
        include_params: Include parameter list (default: True)

    Returns:
        {
            "format": str,
            "total_tools": int,
            "documentation": str | dict,
            "grouped_by_file": dict[filename -> list|int],
        }
    """
    try:
        tools_dir = Path(__file__).parent
        all_tools = {}
        file_groups = {}

        for py_file in sorted(tools_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            metadata = _extract_tool_metadata(py_file)
            for tool in metadata:
                all_tools[tool["name"]] = tool
                file_groups.setdefault(tool["file"], []).append(tool)

        if output_format == "json":
            return {
                "format": "json",
                "total_tools": len(all_tools),
                "tools": all_tools,
                "grouped_by_file": file_groups,
            }

        # Generate markdown
        lines = ["# Loom Tools Reference\n", f"Auto-generated for {len(all_tools)} tools.\n"]
        for filename in sorted(file_groups.keys()):
            lines.append(f"## {filename}\n")
            lines.append("| Tool | Description | Parameters |\n")
            lines.append("|------|-------------|------------|\n")
            for tool in file_groups[filename]:
                desc = tool["docstring"][:75]
                params = ", ".join(tool["parameters"][:3]) if include_params else "—"
                lines.append(f"| `{tool['name']}` | {desc} | {params} |\n")
            lines.append("")

        return {
            "format": "markdown",
            "total_tools": len(all_tools),
            "documentation": "".join(lines),
            "grouped_by_file": {k: len(v) for k, v in file_groups.items()},
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_generate_docs"}


async def research_docs_coverage() -> dict[str, Any]:
    """Report documentation coverage for all tools.

    Returns:
        {
            "total_tools": int,
            "documented": int,
            "undocumented": list[str],
            "coverage_pct": float,
            "files_with_no_docs": list[str],
        }
    """
    try:
        tools_dir = Path(__file__).parent
        all_tools = []
        undocumented = []
        file_doc_counts = {}

        for py_file in sorted(tools_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            metadata = _extract_tool_metadata(py_file)
            file_doc_counts[py_file.name] = {"total": len(metadata), "documented": 0}

            for tool in metadata:
                all_tools.append(tool["name"])
                is_documented = (
                    tool["docstring"]
                    and tool["docstring"] != "No description"
                    and len(tool["docstring"]) > 10
                )
                if is_documented:
                    file_doc_counts[py_file.name]["documented"] += 1
                else:
                    undocumented.append(tool["name"])

        documented = len(all_tools) - len(undocumented)
        coverage_pct = (documented / len(all_tools) * 100) if all_tools else 0.0
        files_no_docs = [f for f, c in file_doc_counts.items() if c["documented"] == 0 and c["total"] > 0]

        return {
            "total_tools": len(all_tools),
            "documented": documented,
            "undocumented": undocumented,
            "coverage_pct": round(coverage_pct, 1),
            "files_with_no_docs": files_no_docs,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_docs_coverage"}
