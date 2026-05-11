"""Extract tool metadata via AST into brain_index.json for smart tool matching.

Scans all src/loom/tools/*.py files, extracts:
- Function name, docstring, parameters (with types/defaults)
- Inferred categories from module name and keywords
- Whether it's async

Output: src/loom/brain/brain_index.json
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any


def extract_tool_metadata(file_path: Path) -> list[dict[str, Any]]:
    """Extract all research_* functions from a Python file via AST."""
    tools: list[dict[str, Any]] = []
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return tools

    module_name = file_path.stem

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("research_"):
            continue

        # Extract docstring
        docstring = ast.get_docstring(node) or ""
        first_line = docstring.split("\n")[0].strip() if docstring else ""

        # Extract parameters
        params: dict[str, dict[str, Any]] = {}
        for arg in node.args.args:
            if arg.arg in ("self", "cls"):
                continue
            param_info: dict[str, Any] = {"required": True}

            # Type annotation
            if arg.annotation:
                param_info["type"] = _annotation_to_str(arg.annotation)

            params[arg.arg] = param_info

        # Handle defaults (assigned right-to-left)
        defaults = node.args.defaults
        num_defaults = len(defaults)
        param_names = [a.arg for a in node.args.args if a.arg not in ("self", "cls")]
        for i, default in enumerate(defaults):
            param_idx = len(param_names) - num_defaults + i
            if 0 <= param_idx < len(param_names):
                param_name = param_names[param_idx]
                if param_name in params:
                    params[param_name]["required"] = False
                    params[param_name]["default"] = _default_to_value(default)

        # Infer categories from module name
        categories = _infer_categories(module_name, node.name, first_line)

        tool_meta = {
            "name": node.name,
            "module": module_name,
            "description": first_line,
            "full_docstring": docstring[:500] if docstring else "",
            "parameters": params,
            "is_async": isinstance(node, ast.AsyncFunctionDef),
            "categories": categories,
        }
        tools.append(tool_meta)

    return tools


def _annotation_to_str(annotation: ast.expr) -> str:
    """Convert AST annotation node to string."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    elif isinstance(annotation, ast.Constant):
        return str(annotation.value)
    elif isinstance(annotation, ast.Attribute):
        return f"{_annotation_to_str(annotation.value)}.{annotation.attr}"
    elif isinstance(annotation, ast.Subscript):
        base = _annotation_to_str(annotation.value)
        return f"{base}[...]"
    elif isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        left = _annotation_to_str(annotation.left)
        right = _annotation_to_str(annotation.right)
        return f"{left} | {right}"
    return "Any"


def _default_to_value(node: ast.expr) -> Any:
    """Convert AST default value to Python value."""
    if isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.List):
        return []
    elif isinstance(node, ast.Dict):
        return {}
    elif isinstance(node, ast.Name) and node.id == "None":
        return None
    elif isinstance(node, ast.Attribute):
        return f"{_annotation_to_str(node)}"
    return None


_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "search": ["search", "find", "query", "lookup", "discover"],
    "fetch": ["fetch", "scrape", "crawl", "download", "extract"],
    "security": ["vuln", "cve", "exploit", "breach", "scan", "security", "pentest"],
    "osint": ["osint", "recon", "intel", "spy", "monitor", "track"],
    "academic": ["paper", "citation", "journal", "arxiv", "academic", "retraction"],
    "crypto": ["crypto", "blockchain", "bitcoin", "wallet", "token"],
    "darkweb": ["onion", "tor", "dark", "hidden", "forum"],
    "privacy": ["fingerprint", "privacy", "stealth", "anonymity", "stego"],
    "career": ["job", "career", "salary", "resume", "employment"],
    "llm": ["llm", "summarize", "translate", "classify", "embed", "chat"],
    "analysis": ["analyze", "score", "assess", "evaluate", "detect"],
    "infrastructure": ["dns", "whois", "ip", "domain", "cert", "header"],
}


def _infer_categories(module_name: str, func_name: str, description: str) -> list[str]:
    """Infer tool categories from module name, function name, and description."""
    text = f"{module_name} {func_name} {description}".lower()
    matched = []
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            matched.append(category)
    return matched or ["general"]


def main() -> None:
    tools_dir = Path(__file__).parent.parent / "src" / "loom" / "tools"
    if not tools_dir.is_dir():
        print(f"ERROR: {tools_dir} not found")
        sys.exit(1)

    all_tools: list[dict[str, Any]] = []
    files_scanned = 0

    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        tools = extract_tool_metadata(py_file)
        all_tools.extend(tools)
        files_scanned += 1

    # Also scan reframe_strategies
    strategies_dir = tools_dir / "reframe_strategies"
    if strategies_dir.is_dir():
        for py_file in sorted(strategies_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            tools = extract_tool_metadata(py_file)
            all_tools.extend(tools)
            files_scanned += 1

    output_path = Path(__file__).parent.parent / "src" / "loom" / "brain" / "brain_index.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    index = {
        "version": "1.0",
        "files_scanned": files_scanned,
        "tools_count": len(all_tools),
        "tools": all_tools,
    }

    output_path.write_text(json.dumps(index, indent=2, default=str), encoding="utf-8")
    print(f"Extracted {len(all_tools)} tools from {files_scanned} files → {output_path}")


if __name__ == "__main__":
    main()
