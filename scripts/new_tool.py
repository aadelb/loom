#!/usr/bin/env python3
"""CLI scaffold generator for new MCP tools in Loom.

Generates all required files for a new tool in ~2 minutes:
  1. src/loom/tools/{tool_name}.py — implementation with boilerplate
  2. Pydantic model in src/loom/params.py
  3. tests/test_tools/test_{tool_name}.py — pytest boilerplate

Usage:
  python scripts/new_tool.py \
    --name fetch_rss \
    --params "url:str,limit:int=10" \
    --category intelligence \
    --description "Fetch and parse RSS feeds"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def validate_tool_name(name: str) -> str:
    """Validate tool name is valid Python identifier."""
    if not name.isidentifier():
        raise ValueError(f"Tool name '{name}' is not a valid Python identifier")
    if name.startswith("_"):
        raise ValueError("Tool name cannot start with underscore")
    return name


def parse_params(params_str: str) -> list[dict[str, str]]:
    """Parse parameter string into list of param dicts.

    Format: "name:type=default,name2:type=default2"
    Examples:
      - "url:str" → [{"name": "url", "type": "str"}]
      - "limit:int=10" → [{"name": "limit", "type": "int", "default": "10"}]
      - "url:str,limit:int=10" → [{"name": "url", "type": "str"}, {"name": "limit", "type": "int", "default": "10"}]
    """
    if not params_str.strip():
        return []

    params: list[dict[str, str]] = []
    for param in params_str.split(","):
        param = param.strip()
        if not param:
            continue

        # Split by '=' to extract default value
        if "=" in param:
            name_type, default = param.split("=", 1)
            name, param_type = name_type.split(":", 1)
            params.append({
                "name": name.strip(),
                "type": param_type.strip(),
                "default": default.strip(),
            })
        else:
            # No default value
            name, param_type = param.split(":", 1)
            params.append({
                "name": name.strip(),
                "type": param_type.strip(),
            })

    return params


def _format_default(default: str, param_type: str) -> str:
    """Format default value with appropriate quotes for the parameter type."""
    if param_type == "str":
        # String defaults need quotes
        return f'"{default}"'
    elif param_type == "bool":
        # Boolean defaults should be True/False
        return default if default in ("True", "False") else default
    else:
        # int, float, etc. - use as-is
        return default


def generate_tool_impl(tool_name: str, params: list[dict[str, str]], description: str) -> str:
    """Generate tool implementation file content."""
    # Function name is research_{tool_name}
    func_name = f"research_{tool_name}"

    # Build parameter list for function signature
    param_lines = []
    for p in params:
        name = p["name"]
        param_type = p["type"]
        if "default" in p:
            default_val = _format_default(p["default"], param_type)
            param_lines.append(f"    {name}: {param_type} = {default_val},")
        else:
            param_lines.append(f"    {name}: {param_type},")

    param_signature = "\n".join(param_lines) if param_lines else ""
    if param_signature:
        param_signature = "\n" + param_signature + "\n"

    # Build parameter validation block with proper indentation
    validation_lines = []
    for p in params:
        name = p["name"]
        if p["type"] == "str":
            # Common case: validate URLs or strings
            if "url" in name.lower():
                validation_lines.append(f"        # TODO: validate {name} — may require URL validation")
            else:
                validation_lines.append(f"        # TODO: validate {name}")

    if validation_lines:
        validation_block = "\n".join(validation_lines)
    else:
        validation_block = "        pass"

    # Build return type hint
    return_type = "dict[str, Any]"

    # Use explicit string formatting to avoid f-string issues with nested braces
    tool_impl = f'''"""research_{tool_name} — {description}."""

from __future__ import annotations

import logging
from typing import Any

from loom.params import {_pascal_case(tool_name)}Params
from loom.validators import validate_url

logger = logging.getLogger("loom.tools.{tool_name}")


async def {func_name}({param_signature}) -> {return_type}:
    """{description}.

    Args:
{_generate_arg_docs(params)}

    Returns:
        dict with keys: result, tool, error (if failed)
    """
    try:
        # Input validation
{validation_block}

        # TODO: Implement core logic here
        logger.info(f"Executing {func_name}")

        return {{
            "result": "TODO: implement",
            "tool": "{func_name}",
            "error": None,
        }}

    except Exception as e:
        logger.error(f"Error in {func_name}: {{str(e)}}")
        return {{
            "result": None,
            "tool": "{func_name}",
            "error": str(e),
        }}
'''

    return tool_impl


def _pascal_case(snake_str: str) -> str:
    """Convert snake_case to PascalCase."""
    return "".join(word.capitalize() for word in snake_str.split("_"))


def _generate_arg_docs(params: list[dict[str, str]]) -> str:
    """Generate docstring argument documentation."""
    if not params:
        return "        None"
    lines = []
    for p in params:
        name = p["name"]
        param_type = p["type"]
        if "default" in p:
            lines.append(f"        {name}: {param_type}, default={p['default']}")
        else:
            lines.append(f"        {name}: {param_type} (required)")
    return "\n".join(lines)


def generate_params_model(tool_name: str, params: list[dict[str, str]]) -> str:
    """Generate Pydantic parameter model for params.py."""
    model_name = f"{_pascal_case(tool_name)}Params"

    # Build field definitions
    field_lines = []
    for p in params:
        name = p["name"]
        param_type = p["type"]
        if "default" in p:
            default_val = _format_default(p["default"], param_type)
            field_lines.append(f"    {name}: {param_type} = {default_val}")
        else:
            field_lines.append(f"    {name}: {param_type}")

    if field_lines:
        fields_block = "\n".join(field_lines)
        model_code = f'''
class {model_name}(BaseModel):
    """{tool_name.replace('_', ' ').title()} parameters."""

{fields_block}

    model_config = {{"extra": "forbid", "strict": True}}
'''
    else:
        # No parameters case
        model_code = f'''
class {model_name}(BaseModel):
    """{tool_name.replace('_', ' ').title()} parameters."""

    model_config = {{"extra": "forbid", "strict": True}}
'''

    return model_code


def generate_test_file(tool_name: str, params: list[dict[str, str]]) -> str:
    """Generate pytest test file boilerplate."""
    func_name = f"research_{tool_name}"

    # Build simple test with mocked implementation
    param_examples = []
    for p in params:
        name = p["name"]
        param_type = p["type"]
        if param_type == "str":
            param_examples.append(f'{name}="test_value"')
        elif param_type == "int":
            param_examples.append(f'{name}=42')
        elif param_type == "bool":
            param_examples.append(f'{name}=True')
        elif param_type == "float":
            param_examples.append(f'{name}=3.14')
        else:
            param_examples.append(f'{name}=None')

    param_call = ", ".join(param_examples) if param_examples else ""

    test_code = f'''"""Tests for {func_name} tool."""

import pytest
from unittest.mock import AsyncMock, patch

from loom.tools import {tool_name}


@pytest.mark.asyncio
async def test_{func_name}_signature():
    """Verify function signature."""
    import inspect

    sig = inspect.signature({tool_name}.{func_name})
    params = list(sig.parameters.keys())

{_generate_param_checks(params)}

    assert sig.return_annotation != inspect.Signature.empty


@pytest.mark.asyncio
async def test_{func_name}_basic():
    """Test basic execution."""
    result = await {tool_name}.{func_name}({param_call})

    assert isinstance(result, dict)
    assert "tool" in result
    assert "error" in result
    assert result["tool"] == "{func_name}"


@pytest.mark.asyncio
async def test_{func_name}_error_handling():
    """Test error handling."""
    # Call with invalid input or mock an exception
    with patch("loom.tools.{tool_name}.logger") as mock_logger:
        # Mock an error condition
        result = await {tool_name}.{func_name}({param_call})

        # Should gracefully return error dict
        assert isinstance(result, dict)
        assert "error" in result


@pytest.mark.asyncio
async def test_{func_name}_logging():
    """Test logging is called."""
    with patch("loom.tools.{tool_name}.logger") as mock_logger:
        await {tool_name}.{func_name}({param_call})

        # Verify logging was called
        assert mock_logger.info.called or mock_logger.error.called
'''

    return test_code


def _generate_param_checks(params: list[dict[str, str]]) -> str:
    """Generate assertion lines for parameter checks."""
    if not params:
        return '    assert len(params) == 0'

    checks = []
    for p in params:
        checks.append(f'    assert "{p["name"]}" in params')

    return "\n".join(checks)


def append_to_params_file(params_model: str, project_root: Path) -> None:
    """Append Pydantic model to params.py file."""
    params_file = project_root / "src" / "loom" / "params.py"

    if not params_file.exists():
        raise FileNotFoundError(f"params.py not found at {params_file}")

    # Read existing content
    content = params_file.read_text()

    # Append the new model
    with open(params_file, "a") as f:
        f.write("\n")
        f.write(params_model)
        f.write("\n")

    print(f"✓ Appended Pydantic model to {params_file}")


def main() -> None:
    """Parse arguments and generate tool files."""
    parser = argparse.ArgumentParser(
        description="Generate scaffold files for a new MCP tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/new_tool.py \\
    --name fetch_rss \\
    --params "url:str,limit:int=10" \\
    --category intelligence \\
    --description "Fetch and parse RSS feeds"

  python scripts/new_tool.py \\
    --name analyze_sentiment \\
    --params "text:str" \\
    --category analysis \\
    --description "Analyze sentiment of text"
""",
    )

    parser.add_argument(
        "--name",
        required=True,
        help="Tool name (snake_case, e.g. 'fetch_rss')",
    )
    parser.add_argument(
        "--params",
        default="",
        help="Parameter spec (e.g. 'url:str,limit:int=10')",
    )
    parser.add_argument(
        "--category",
        default="research",
        help="Tool category (e.g. 'intelligence', 'analysis')",
    )
    parser.add_argument(
        "--description",
        default="Research tool",
        help="Tool description for docstring",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Project root directory (default: inferred from cwd)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated files without creating them",
    )

    args = parser.parse_args()

    try:
        # Validate inputs
        tool_name = validate_tool_name(args.name)
        params = parse_params(args.params)

        # Infer project root
        if args.output_dir:
            project_root = args.output_dir
        else:
            # Look for src/loom directory
            cwd = Path.cwd()
            if (cwd / "src" / "loom").exists():
                project_root = cwd
            elif (cwd.parent / "src" / "loom").exists():
                project_root = cwd.parent
            else:
                raise FileNotFoundError(
                    "Could not find src/loom directory. "
                    "Run from project root or use --output-dir"
                )

        # Generate content
        tool_impl = generate_tool_impl(tool_name, params, args.description)
        params_model = generate_params_model(tool_name, params)
        test_file_content = generate_test_file(tool_name, params)

        if args.dry_run:
            print("\n" + "=" * 80)
            print(f"TOOL IMPLEMENTATION: src/loom/tools/{tool_name}.py")
            print("=" * 80)
            print(tool_impl)

            print("\n" + "=" * 80)
            print(f"PARAMS MODEL (append to src/loom/params.py)")
            print("=" * 80)
            print(params_model)

            print("\n" + "=" * 80)
            print(f"TEST FILE: tests/test_tools/test_{tool_name}.py")
            print("=" * 80)
            print(test_file_content)
            return

        # Create tool implementation
        tools_dir = project_root / "src" / "loom" / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        tool_file_path = tools_dir / f"{tool_name}.py"

        if tool_file_path.exists():
            print(f"Error: {tool_file_path} already exists", file=sys.stderr)
            sys.exit(1)

        tool_file_path.write_text(tool_impl)
        print(f"✓ Created tool implementation: {tool_file_path}")

        # Append to params.py
        append_to_params_file(params_model, project_root)

        # Create test file
        tests_dir = project_root / "tests" / "test_tools"
        tests_dir.mkdir(parents=True, exist_ok=True)
        test_file_path = tests_dir / f"test_{tool_name}.py"

        if test_file_path.exists():
            print(f"Warning: {test_file_path} already exists, skipping", file=sys.stderr)
        else:
            test_file_path.write_text(test_file_content)
            print(f"✓ Created test file: {test_file_path}")

        # Print manual next steps
        print("\n" + "=" * 80)
        print("NEXT STEPS — MANUAL ACTIONS REQUIRED")
        print("=" * 80)
        func_name = f"research_{tool_name}"
        print(f"""
1. EDIT TOOL IMPLEMENTATION
   File: {tool_file_path}
   - Replace TODO comments with actual logic
   - Add error handling
   - Add proper logging

2. REGISTER TOOL IN SERVER
   File: {project_root / 'src' / 'loom' / 'server.py'}
   Add to _register_tools():

   mcp.tool()(
       _wrap_tool(
           {tool_name}.{func_name},
           "{tool_name}",
       )
   )

3. UPDATE DOCUMENTATION
   - docs/tools-reference.md: Add tool reference with examples
   - docs/help.md: Add troubleshooting section (if applicable)

4. RUN TESTS
   pytest tests/test_tools/test_{tool_name}.py -v

5. LINT & FORMAT
   ruff check --fix src/loom/tools/{tool_name}.py
   ruff format src/loom/tools/{tool_name}.py
   mypy src/loom/tools/{tool_name}.py

6. VERIFY COMPLETENESS
   scripts/verify_completeness.py (to check for doc drift)
""")

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
