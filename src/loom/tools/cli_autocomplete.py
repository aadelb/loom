"""CLI autocomplete generator for the loom command-line interface."""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

try:
    import logging
    logger = logging.getLogger("loom.tools.cli_autocomplete")
except Exception:
    logger = None


async def research_generate_completions(shell: str = "zsh") -> dict[str, Any]:
    """Generate shell completion script for all Loom tools.

    Args:
        shell: Target shell ("zsh", "bash", "fish")

    Returns:
        Dict with keys: shell, script, tools_count, install_instruction
    """
    if shell not in ("zsh", "bash", "fish"):
        raise ValueError(f"Unsupported shell: {shell}")
    tools = _collect_tools()
    gens = {"zsh": _zsh, "bash": _bash, "fish": _fish}
    insts = {"zsh": "~/.zfunc/_loom (add to ~/.zshrc: fpath=(~/.zfunc $fpath))", "bash": "/etc/bash_completion.d/loom", "fish": "~/.config/fish/completions/loom.fish"}
    return {"shell": shell, "script": gens[shell](tools), "tools_count": len(tools), "install_instruction": insts[shell]}


async def research_tool_help(tool_name: str) -> dict[str, Any]:
    """Get detailed help for a specific tool.

    Args:
        tool_name: Name of the tool (e.g., "research_fetch")

    Returns:
        Dict with tool_name, description, parameters, examples, source_file
    """
    tools = _collect_tools()
    tool = next((t for t in tools if t["name"] == tool_name), None)
    if not tool:
        raise ValueError(f"Tool not found: {tool_name}")
    return {"tool_name": tool["name"], "description": tool["description"], "parameters": tool["parameters"], "examples": tool.get("examples", []), "source_file": tool.get("source_file", "unknown")}


def _collect_tools() -> list[dict[str, Any]]:
    """Scan tool modules and extract function metadata using AST."""
    tools, tools_dir = [], Path(__file__).parent
    for py_file in sorted(tools_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            tree = ast.parse(py_file.read_text(), filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("research_"):
                    doc = ast.get_docstring(node) or ""
                    tools.append({"name": node.name, "description": (doc.split("\n")[0] if doc else ""), "parameters": _params(node), "source_file": py_file.name})
        except Exception as e:
            if logger:
                logger.debug(f"Parse error {py_file}: {e}")
    return tools


def _params(fn: ast.FunctionDef) -> list[dict[str, Any]]:
    """Extract parameter info from function node."""
    p, args = [], fn.args
    for arg in args.args:
        if arg.arg not in ("self", "cls"):
            p.append({"name": arg.arg, "type": ast.unparse(arg.annotation) if arg.annotation else "any"})
    for i, d in enumerate(args.defaults):
        idx = len(args.args) - len(args.defaults) + i
        if 0 <= idx < len(p):
            p[idx]["default"] = ast.unparse(d)
    return p


def _zsh(tools: list[dict[str, Any]]) -> str:
    """Generate zsh completion."""
    l = ["#compdef loom", "", "local -a research_tools", "research_tools=("]
    l += [f'  "{t["name"]}:{t["description"][:40]}"' for t in tools]
    l += [")", "", "case $words[1] in", "  *)", '    _describe "research tool" research_tools', "    ;;", "esac"]
    return "\n".join(l)


def _bash(tools: list[dict[str, Any]]) -> str:
    """Generate bash completion."""
    names = " ".join(t["name"] for t in tools)
    return f"""_loom() {{ [[ $COMP_CWORD -eq 1 ]] && COMPREPLY=($(compgen -W "{names}" -- "${{COMP_WORDS[COMP_CWORD]}}")) }}
complete -F _loom loom"""


def _fish(tools: list[dict[str, Any]]) -> str:
    """Generate fish completion."""
    l = ["# Loom fish completions", ""]
    l += [f'complete -c loom -a "{t["name"]}" -d "{t["description"][:40]}"' for t in tools]
    return "\n".join(l)
