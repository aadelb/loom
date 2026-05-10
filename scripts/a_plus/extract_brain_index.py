"""Extract tool metadata for Brain index using NVIDIA NIM (free tier).

Usage:
    python scripts/a_plus/extract_brain_index.py --output src/loom/tools/brain_index.json
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import call_model

_SRC = Path(__file__).resolve().parent.parent.parent / "src" / "loom" / "tools"


def extract_functions(file_path: Path) -> list[dict]:
    """Extract research_* function signatures from a file using AST."""
    content = file_path.read_text()
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("research_") or node.name.startswith("tool_"):
                docstring = ast.get_docstring(node) or ""
                params = []
                for arg in node.args.args:
                    if arg.arg != "self":
                        annotation = ast.unparse(arg.annotation) if arg.annotation else "Any"
                        params.append({"name": arg.arg, "type": annotation})
                functions.append({
                    "name": node.name,
                    "file": file_path.name,
                    "docstring": docstring[:200],
                    "params": params,
                    "is_async": isinstance(node, ast.AsyncFunctionDef),
                })
    return functions


async def enrich_with_llm(func: dict, semaphore: asyncio.Semaphore) -> dict:
    """Use NVIDIA NIM to extract keywords and category from docstring."""
    async with semaphore:
        prompt = f"""Extract metadata for this tool function:
Name: {func['name']}
Docstring: {func['docstring']}
Params: {json.dumps(func['params'])}

Return JSON with:
- description: one sentence
- category: one of [core, search, llm, osint, security, career, creative, academic, privacy, infrastructure, reframe, adversarial]
- keywords: list of 5-10 words for matching user queries to this tool
"""
        try:
            response = await call_model("nvidia", "", prompt, max_tokens=300)
            # Try to parse JSON from response
            if "{" in response:
                json_str = response[response.index("{"):response.rindex("}") + 1]
                metadata = json.loads(json_str)
                func["description"] = metadata.get("description", func["docstring"][:100])
                func["category"] = metadata.get("category", "unknown")
                func["keywords"] = metadata.get("keywords", [])
            else:
                func["description"] = func["docstring"][:100]
                func["category"] = "unknown"
                func["keywords"] = []
        except Exception:
            func["description"] = func["docstring"][:100]
            func["category"] = "unknown"
            func["keywords"] = []
        return func


async def build_index(output_path: Path, parallel: int) -> None:
    """Build the brain index from all tool files."""
    all_functions = []
    tool_files = sorted(_SRC.glob("*.py"))
    print(f"Scanning {len(tool_files)} tool files...")

    for f in tool_files:
        funcs = extract_functions(f)
        all_functions.extend(funcs)

    print(f"Found {len(all_functions)} tool functions. Enriching with NVIDIA NIM...")

    semaphore = asyncio.Semaphore(parallel)
    enriched = await asyncio.gather(*[enrich_with_llm(f, semaphore) for f in all_functions])

    # Build index keyed by function name
    index = {}
    for func in enriched:
        index[func["name"]] = {
            "file": func["file"],
            "description": func.get("description", ""),
            "category": func.get("category", "unknown"),
            "params": func["params"],
            "keywords": func.get("keywords", []),
            "is_async": func["is_async"],
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2))
    print(f"Brain index written: {output_path} ({len(index)} tools)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Brain index from tool files")
    parser.add_argument("--output", default="src/loom/tools/brain_index.json")
    parser.add_argument("--parallel", type=int, default=5)
    args = parser.parse_args()

    asyncio.run(build_index(Path(args.output), args.parallel))


if __name__ == "__main__":
    main()
