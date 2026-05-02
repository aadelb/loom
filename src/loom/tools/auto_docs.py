"""Auto-documentation generator for research tools.

Introspects tool signatures and docstrings to generate markdown documentation
and coverage reports for all registered tools.
"""

from __future__ import annotations

import ast
import inspect
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.auto_docs")


def _extract_tool_metadata(file_path: Path) -> list[dict[str, Any]]:
    """Extract metadata for all research_* functions from a Python file.

    Returns list of dicts with keys:
    - name: function name (str)
    - docstring: first line of docstring (str or None)
    - parameters: list of (param_name, type_hint, default) tuples
    - return_type: return type annotation string (str or None)
    """
    try:
        with open(file_path) as f:
            tree = ast.parse(f.read())
    except Exception as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
        return []

    tools = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        if not node.name.startswith("research_"):
            continue

        # Extract docstring
        docstring = ast.get_docstring(node)
        first_line = (docstring.split("\n")[0] if docstring else None) or "No description"

        # Extract parameters with type hints
        params = []
        for arg in node.args.args:
            param_name = arg.arg
            type_hint = ast.unparse(arg.annotation) if arg.annotation else "Any"
            params.append(param_name)

        # Extract return type
        return_type = ast.unparse(node.returns) if node.returns else "dict"

        tools.append(
            {
                "name": node.name,
                "docstring": first_line,
                "parameters": params,
                "return_type": return_type,
                "file": file_path.name,
            }
        )

    return tools


async def research_generate_docs(
    output_format: str = "markdown",
    include_params: bool = True,
) -> dict:
    """Generate auto-documentation for all registered tools.

    Scans src/loom/tools/*.py, introspects async function signatures starting
    with "research_", and generates formatted documentation.

    Args:
        output_format: "markdown" (default) or "json"
        include_params: Include parameter list in output (default: True)

    Returns:
        {
            "format": str,
            "total_tools": int,
            "documentation": str (markdown) or dict (json),
            "grouped_by_file": dict[filename -> list[tool_dicts]],
        }
    """
    tools_dir = Path(__file__).parent
    all_tools = {}
    file_groups = {}

    # Scan all .py files in tools directory
    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue

        metadata = _extract_tool_metadata(py_file)
        for tool in metadata:
            all_tools[tool["name"]] = tool
            file_groups.setdefault(tool["file"], []).append(tool)

    # Generate documentation
    if output_format == "json":
        return {
            "format": "json",
            "total_tools": len(all_tools),
            "tools": all_tools,
            "grouped_by_file": file_groups,
        }

    # Generate markdown
    lines = ["# Loom Tools Reference\n", f"Auto-generated documentation for {len(all_tools)} tools.\n"]

    for filename in sorted(file_groups.keys()):
        lines.append(f"## {filename}\n")
        lines.append("| Tool | Description | Parameters |\n")
        lines.append("|------|-------------|------------|\n")

        for tool in file_groups[filename]:
            tool_name = tool["name"]
            description = tool["docstring"][:80]
            params = ", ".join(tool["parameters"][:3]) if include_params else "—"

            lines.append(f"| `{tool_name}` | {description} | {params} |\n")

        lines.append("")

    return {
        "format": "markdown",
        "total_tools": len(all_tools),
        "documentation": "".join(lines),
        "grouped_by_file": {k: len(v) for k, v in file_groups.items()},
    }


async def research_docs_coverage() -> dict:
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
            # Tool is documented if docstring exists and is not the default message
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

    files_with_no_docs = [
        f for f, counts in file_doc_counts.items() if counts["documented"] == 0 and counts["total"] > 0
    ]

    return {
        "total_tools": len(all_tools),
        "documented": documented,
        "undocumented": undocumented,
        "coverage_pct": round(coverage_pct, 1),
        "files_with_no_docs": files_with_no_docs,
    }
