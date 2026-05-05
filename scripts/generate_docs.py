#!/usr/bin/env python3
"""Generate complete tool documentation from source code.

This script introspects all tools in src/loom/tools/ and generates:
1. Auto-generated markdown documentation (docs/COMPLETE_TOOL_GUIDE.md)
2. Tool count statistics per category
3. Parameter extraction for each tool
4. Async status detection

Usage:
    python3 scripts/generate_docs.py
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

# Add src to path for relative imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def extract_tools_from_file(file_path: Path) -> list[dict[str, Any]]:
    """Extract all research_* tools from a Python file."""
    tools = []
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("research_"):
                    doc = ast.get_docstring(node) or "No description available"
                    doc_first_line = doc.split("\n")[0]

                    # Extract parameters
                    params = []
                    for arg in node.args.args:
                        if arg.arg not in ("self", "cls"):
                            type_hint = "Any"
                            if arg.annotation:
                                type_hint = ast.unparse(arg.annotation)
                            params.append(
                                {
                                    "name": arg.arg,
                                    "type": type_hint,
                                }
                            )

                    # Extract defaults
                    defaults_count = len(node.args.defaults)
                    required_count = len(params) - defaults_count

                    tools.append(
                        {
                            "name": node.name,
                            "file": file_path.name,
                            "doc": doc_first_line,
                            "full_doc": doc,
                            "params": params,
                            "required_params": required_count,
                            "async": isinstance(node, ast.AsyncFunctionDef),
                            "lineno": node.lineno,
                        }
                    )
    except Exception as e:
        print(f"Warning: Failed to parse {file_path}: {e}", file=sys.stderr)

    return tools


def generate_markdown_docs(all_tools: dict[str, list[dict]]) -> str:
    """Generate markdown documentation for all tools."""
    lines = []

    # Header
    lines.append("# Loom Complete Tool Guide")
    lines.append("")
    lines.append("**Auto-Generated Documentation**")
    lines.append("")

    total_tools = sum(len(tools) for tools in all_tools.values())
    lines.append(f"## Summary: {total_tools} Tools Across {len(all_tools)} Categories")
    lines.append("")

    # Category table of contents
    lines.append("### Categories")
    lines.append("")
    lines.append("| Category | Tools | Examples |")
    lines.append("|----------|-------|----------|")

    for category in sorted(all_tools.keys()):
        tools = all_tools[category]
        count = len(tools)
        examples = ", ".join(f"`{t['name']}`" for t in tools[:3])
        cat_display = category.replace("_", " ").title()
        lines.append(f"| {cat_display} | {count} | {examples} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Detailed category sections
    for category in sorted(all_tools.keys()):
        tools = all_tools[category]
        cat_display = category.replace("_", " ").title()

        lines.append(f"## {cat_display} ({len(tools)} tools)")
        lines.append("")

        for tool in sorted(tools, key=lambda t: t["name"]):
            lines.append(f"### `{tool['name']}`")
            lines.append("")
            lines.append(f"**File:** `src/loom/tools/{tool['file']}`")
            lines.append("")
            lines.append(f"**Description:** {tool['doc']}")
            lines.append("")

            if tool["params"]:
                lines.append("**Parameters:**")
                lines.append("")
                for param in tool["params"]:
                    req = (
                        "required"
                        if tool["params"].index(param)
                        < tool["required_params"]
                        else "optional"
                    )
                    lines.append(f"- `{param['name']}` ({param['type']}) — {req}")
                lines.append("")
            else:
                lines.append("**Parameters:** None")
                lines.append("")

            if tool["async"]:
                lines.append("**Type:** Async")
            else:
                lines.append("**Type:** Sync")
            lines.append("")

            # Full docstring
            if tool["full_doc"] and len(tool["full_doc"]) > len(tool["doc"]):
                lines.append("**Full Documentation:**")
                lines.append("")
                lines.append("```")
                lines.append(tool["full_doc"])
                lines.append("```")
                lines.append("")

    return "\n".join(lines)


def generate_statistics(all_tools: dict[str, list[dict]]) -> str:
    """Generate statistics summary."""
    lines = []

    total_tools = sum(len(tools) for tools in all_tools.values())
    async_tools = sum(
        1 for tools in all_tools.values() for t in tools if t["async"]
    )
    sync_tools = total_tools - async_tools

    lines.append("# Loom Tool Statistics")
    lines.append("")
    lines.append(f"- **Total Tools:** {total_tools}")
    lines.append(f"- **Async Tools:** {async_tools}")
    lines.append(f"- **Sync Tools:** {sync_tools}")
    lines.append(f"- **Categories:** {len(all_tools)}")
    lines.append("")
    lines.append("## Tools Per Category")
    lines.append("")

    for category in sorted(all_tools.keys(), key=lambda c: len(all_tools[c]), reverse=True):
        tools = all_tools[category]
        async_count = sum(1 for t in tools if t["async"])
        lines.append(f"- **{category}**: {len(tools)} ({async_count} async, {len(tools) - async_count} sync)")

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    tools_dir = Path(__file__).parent.parent / "src" / "loom" / "tools"

    if not tools_dir.exists():
        print(f"Error: Tools directory not found at {tools_dir}", file=sys.stderr)
        sys.exit(1)

    all_tools: dict[str, list[dict]] = defaultdict(list)

    # Discover and parse all tool files
    for file_path in sorted(tools_dir.glob("*.py")):
        if file_path.name.startswith("_"):
            continue

        tools = extract_tools_from_file(file_path)
        if tools:
            category = file_path.stem
            all_tools[category] = tools

    # Generate outputs
    docs_root = Path(__file__).parent.parent / "docs"
    docs_root.mkdir(exist_ok=True)

    # 1. Complete tool guide
    markdown_docs = generate_markdown_docs(all_tools)
    guide_path = docs_root / "COMPLETE_TOOL_GUIDE.md"
    guide_path.write_text(markdown_docs, encoding="utf-8")
    print(f"Generated: {guide_path}")

    # 2. Statistics summary
    stats = generate_statistics(all_tools)
    stats_path = docs_root / "TOOL_STATISTICS.md"
    stats_path.write_text(stats, encoding="utf-8")
    print(f"Generated: {stats_path}")

    # Summary output
    total_tools = sum(len(tools) for tools in all_tools.values())
    print(f"\nSummary:")
    print(f"  Tools discovered: {total_tools}")
    print(f"  Categories: {len(all_tools)}")
    print(f"  Files processed: {sum(1 for _ in tools_dir.glob('*.py') if not _.name.startswith('_'))}")


if __name__ == "__main__":
    main()
