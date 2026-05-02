"""OpenAPI 3.0 schema generator and tool search for Loom MCP tools."""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.openapi_gen")


async def research_openapi_schema() -> dict[str, Any]:
    """Generate OpenAPI 3.0 schema for all Loom research_* tools.

    Scans src/loom/tools/*.py and extracts function metadata via ast module.
    Builds OpenAPI paths (POST endpoints) and parameter schemas.

    Returns: OpenAPI 3.0 dict with paths, components, and metadata.
    """
    tools = _discover_tools(Path(__file__).parent)
    paths = {}
    components = {"schemas": {}}

    for name, info in tools.items():
        path = f"/api/v1/{name.replace('_', '-')}"
        paths[path] = {
            "post": {
                "summary": info["summary"],
                "description": info["docstring"],
                "operationId": name,
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": f"#/components/schemas/{name}Params"}}},
                },
                "responses": {"200": {"description": "Success", "content": {"application/json": {"schema": {"type": "object", "properties": {"result": {"type": "object"}, "tool": {"type": "string"}}}}}}},
            }
        }
        if info["params"]:
            components["schemas"][f"{name}Params"] = {"type": "object", "properties": info["params"], "required": list(info["required"])}

    return {
        "openapi": "3.0.0",
        "info": {"title": "Loom Research API", "description": "220+ research and attack tools", "version": "4.0.0"},
        "servers": [{"url": "http://127.0.0.1:8787"}],
        "paths": paths,
        "components": components,
    }


async def research_tool_search(query: str, limit: int = 10) -> dict[str, Any]:
    """Search tools by keyword/name using natural language matching.

    Scores: keyword matches + name prefix similarity (case-insensitive).
    Args: query (search string), limit (1-100 results)
    Returns: Dict with query, results list, total_matches.
    """
    limit = max(1, min(limit, 100))
    tools = _discover_tools(Path(__file__).parent)
    query_lower, query_words = query.lower(), set(query.lower().split())
    results = []

    for name, info in tools.items():
        text_words = set(f"{name} {info['docstring']}".lower().split())
        score = len(query_words & text_words)
        if name.lower().startswith(query_lower):
            score += 10
        elif query_lower in name.lower():
            score += 5

        if score > 0:
            results.append({"tool_name": name, "description": info["summary"], "relevance_score": score, "file": info["file"]})

    return {"query": query, "results": sorted(results, key=lambda x: x["relevance_score"], reverse=True)[:limit], "total_matches": len(results)}


def _discover_tools(tools_dir: Path) -> dict[str, dict[str, Any]]:
    """Extract research_* functions from .py files using ast (no imports)."""
    tools = {}
    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=py_file.name)
        except Exception as e:
            logger.warning(f"Parse error {py_file.name}: {e}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("research_"):
                doc = ast.get_docstring(node) or ""
                summary = doc.split("\n")[0] if doc else node.name
                params = {arg.arg: {"type": "string"} for arg in node.args.args if arg.arg != "self"}
                tools[node.name] = {"summary": summary, "docstring": doc, "params": params, "required": list(params.keys()), "file": py_file.name}
    return tools
