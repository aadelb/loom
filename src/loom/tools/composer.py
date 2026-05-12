"""Tool composition DSL for chaining research tools together.

Provides a simple declarative syntax for composing research tools:
  - Sequential composition: "tool1(arg) | tool2($)"
  - Parallel execution: "tool1(arg) & tool2(arg) | merge($)"
  - Nested field access: "search($) | fetch($.urls[0]) | markdown($)"
  - Built-in aliases: "deep_research" -> full search pipeline

Example pipelines:
  "search(query) | fetch($.urls[0]) | markdown($) | summarize($)"
  "search(q) & github(q) & social_graph(q) | merge($)"
  "deep_research"  # Expands to search | fetch[:3] | markdown | summarize
  "osint_sweep"    # Expands to search & github & social_graph | merge
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import re
from dataclasses import dataclass
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.composer")


# ── Pipeline Aliases ──

PIPELINE_ALIASES = {
    "deep_research": "search($) | fetch($.urls[:3]) | markdown($) | llm_summarize($)",
    "osint_sweep": "search($) & github($) & social_graph($) | merge($)",
    "code_search": "github($) | fetch($.urls[:5]) | markdown($) | llm_extract($)",
    "breach_scan": "search($) | leak_scan($) | threat_profile($)",
}


@dataclass
class PipelineStep:
    """Represents a single step in a pipeline."""

    tool_name: str
    args: list[str]  # Raw argument strings, may contain $ and $.field references
    parallel_group: int = 0  # Steps with same group execute in parallel


@dataclass
class ComposerResult:
    """Result from pipeline composition execution."""

    success: bool
    output: Any = None
    steps: list[dict[str, Any]] | None = None
    errors: list[str] | None = None
    execution_time_ms: float = 0.0
    step_results: list[Any] | None = None


@handle_tool_errors("research_compose_validate")
def research_compose_validate(pipeline: str) -> dict[str, Any]:
    """Validate pipeline syntax without executing.

    Args:
        pipeline: Pipeline DSL string

    Returns:
        Dict with:
        - valid: bool
        - steps: list of parsed steps
        - errors: list of validation errors
    """
    errors: list[str] = []
    steps: list[dict[str, Any]] = []

    try:
        # Expand aliases
        expanded = _expand_aliases(pipeline)

        # Parse pipeline
        parsed_steps = _parse_pipeline(expanded)

        # Validate each step
        for step in parsed_steps:
            step_info = {
                "tool_name": step.tool_name,
                "args": step.args,
                "parallel_group": step.parallel_group,
            }

            # Check if tool exists
            try:
                _get_tool_function(step.tool_name)
            except (ImportError, AttributeError) as e:
                errors.append(f"Tool '{step.tool_name}' not found: {str(e)}")

            # Validate arguments
            for arg in step.args:
                if arg.startswith("$"):
                    # Field reference validation
                    if not _is_valid_field_reference(arg):
                        errors.append(
                            f"Invalid field reference '{arg}' in tool '{step.tool_name}'"
                        )

            steps.append(step_info)

        return {
            "valid": len(errors) == 0,
            "steps": steps,
            "errors": errors,
            "expanded_pipeline": expanded,
        }

    except Exception as e:
        return {
            "valid": False,
            "steps": [],
            "errors": [f"Parse error: {str(e)}"],
        }


@handle_tool_errors("research_compose")
async def research_compose(
    pipeline: str,
    initial_input: str = "",
    continue_on_error: bool = False,
    timeout_ms: int | None = None,
) -> dict[str, Any]:
    """Execute a composed pipeline of research tools.

    DSL Syntax:
      - "tool1(arg1, arg2) | tool2(arg3, $)" — sequential steps
      - "tool1($) & tool2($) | merge($)" — parallel then sequential
      - "$" — passes entire previous result
      - "$.field" — accesses nested field from dict result
      - "$.field[0]" — array indexing
      - "$.field[:3]" — array slicing

    Args:
        pipeline: Pipeline DSL string
        initial_input: Initial input value for first step
        continue_on_error: Continue on step failure (default False = stop)
        timeout_ms: Optional timeout in milliseconds

    Returns:
        ComposerResult dict with:
        - success: bool
        - output: final result
        - steps: list of step info
        - errors: list of any errors encountered
        - execution_time_ms: wall-clock time
        - step_results: list of intermediate results
    """
    import time

    start_time = time.time()
    result = ComposerResult(
        success=False,
        steps=[],
        errors=[],
        step_results=[],
    )

    try:
        # Expand aliases
        expanded = _expand_aliases(pipeline)
        logger.info("Expanded pipeline: %s", expanded)

        # Validate first
        validation = research_compose_validate(expanded)
        if not validation["valid"]:
            result.errors = validation["errors"]
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result.__dict__

        # Parse pipeline
        parsed_steps = _parse_pipeline(expanded)
        if not parsed_steps:
            result.errors = ["No valid steps found in pipeline"]
            result.execution_time_ms = (time.time() - start_time) * 1000
            return result.__dict__

        # Group parallel steps
        step_groups = _group_parallel_steps(parsed_steps)

        # Execute step groups
        current_value = initial_input
        for group_idx, group in enumerate(step_groups):
            logger.info("Executing group %d with %d steps", group_idx, len(group))

            if len(group) == 1:
                # Single step, execute sequentially
                step = group[0]
                try:
                    step_result = await _execute_step(step, current_value)
                    result.step_results.append(step_result)
                    result.steps.append(
                        {
                            "tool": step.tool_name,
                            "args": step.args,
                            "status": "success",
                        }
                    )
                    current_value = step_result
                except Exception as e:
                    error_msg = f"Step {step.tool_name} failed: {str(e)}"
                    result.errors.append(error_msg)
                    result.step_results.append(None)
                    result.steps.append(
                        {
                            "tool": step.tool_name,
                            "args": step.args,
                            "status": "error",
                            "error": error_msg,
                        }
                    )
                    if not continue_on_error:
                        result.execution_time_ms = (time.time() - start_time) * 1000
                        return result.__dict__
            else:
                # Multiple steps in parallel
                try:
                    parallel_tasks = [
                        _execute_step(step, current_value) for step in group
                    ]

                    # Set timeout if specified
                    if timeout_ms:
                        timeout_secs = timeout_ms / 1000.0
                        parallel_results = await asyncio.wait_for(
                            asyncio.gather(*parallel_tasks, return_exceptions=True),
                            timeout=timeout_secs,
                        )
                    else:
                        parallel_results = await asyncio.gather(
                            *parallel_tasks, return_exceptions=True
                        )

                    # Collect parallel results
                    parallel_outputs = {}
                    for step, res in zip(group, parallel_results):
                        if isinstance(res, Exception):
                            error_msg = (
                                f"Parallel step {step.tool_name} failed: {str(res)}"
                            )
                            result.errors.append(error_msg)
                            result.steps.append(
                                {
                                    "tool": step.tool_name,
                                    "status": "error",
                                    "error": error_msg,
                                }
                            )
                            if not continue_on_error:
                                result.execution_time_ms = (
                                    time.time() - start_time
                                ) * 1000
                                return result.__dict__
                        else:
                            parallel_outputs[step.tool_name] = res
                            result.step_results.append(res)
                            result.steps.append(
                                {
                                    "tool": step.tool_name,
                                    "status": "success",
                                }
                            )

                    # Set current value to dict of parallel results
                    current_value = parallel_outputs

                except asyncio.TimeoutError:
                    error_msg = f"Parallel execution group {group_idx} timed out"
                    result.errors.append(error_msg)
                    if not continue_on_error:
                        result.execution_time_ms = (time.time() - start_time) * 1000
                        return result.__dict__

        result.success = len(result.errors) == 0
        result.output = current_value

    except Exception as e:
        logger.error("Pipeline execution failed: %s", e, exc_info=True)
        result.errors.append(f"Pipeline execution error: {str(e)}")

    result.execution_time_ms = (time.time() - start_time) * 1000
    return result.__dict__


# ── Private Helpers ──


def _expand_aliases(pipeline: str) -> str:
    """Expand pipeline aliases to full DSL.

    Args:
        pipeline: Pipeline string that may contain aliases

    Returns:
        Expanded pipeline string
    """
    # Check if entire pipeline is an alias
    if pipeline.strip() in PIPELINE_ALIASES:
        return PIPELINE_ALIASES[pipeline.strip()]

    # Replace inline aliases
    result = pipeline
    for alias, expansion in PIPELINE_ALIASES.items():
        # Match whole word only to avoid partial replacements
        pattern = rf"\b{re.escape(alias)}\b"
        result = re.sub(pattern, f"({expansion})", result)

    return result


def _parse_pipeline(pipeline: str) -> list[PipelineStep]:
    """Parse pipeline DSL into list of steps.

    Args:
        pipeline: Pipeline string

    Returns:
        List of PipelineStep objects

    Raises:
        ValueError: If pipeline syntax is invalid
    """
    steps: list[PipelineStep] = []
    parallel_group = 0

    # Split by pipes and ampersands (maintain structure)
    # Pattern: handle both | (sequential) and & (parallel)
    parts = _split_pipeline_expression(pipeline)

    for part in parts:
        operator, content = part

        if operator == "&":
            # Parallel: same group
            step = _parse_tool_call(content)
            step.parallel_group = parallel_group
            steps.append(step)
        elif operator == "|":
            # Sequential: new group
            parallel_group += 1
            step = _parse_tool_call(content)
            step.parallel_group = parallel_group
            steps.append(step)

    return steps


def _split_pipeline_expression(expr: str) -> list[tuple[str, str]]:
    """Split pipeline expression by | and & operators.

    Returns list of (operator, content) tuples.
    The first entry has operator "START".

    Args:
        expr: Pipeline expression string

    Returns:
        List of (operator, content) tuples
    """
    # Remove outer whitespace and parentheses
    expr = expr.strip()
    if expr.startswith("(") and expr.endswith(")"):
        expr = expr[1:-1].strip()

    # Split respecting parentheses
    parts: list[tuple[str, str]] = []
    current = ""
    paren_depth = 0
    last_op = "START"

    i = 0
    while i < len(expr):
        char = expr[i]

        if char == "(":
            paren_depth += 1
            current += char
        elif char == ")":
            paren_depth -= 1
            current += char
        elif char in ("|", "&") and paren_depth == 0:
            # Found operator at top level
            if current.strip():
                parts.append((last_op, current.strip()))
            last_op = char
            current = ""
        else:
            current += char

        i += 1

    # Add final part
    if current.strip():
        parts.append((last_op, current.strip()))

    return parts


def _parse_tool_call(call_str: str) -> PipelineStep:
    """Parse a single tool call like 'search(query)' or 'fetch($.urls[0])'.

    Args:
        call_str: Tool call string

    Returns:
        PipelineStep with tool name and arguments

    Raises:
        ValueError: If parsing fails
    """
    # Pattern: tool_name(arg1, arg2, ...)
    match = re.match(r"(\w+)\((.*)\)", call_str.strip())
    if not match:
        raise ValueError(f"Invalid tool call syntax: {call_str}")

    tool_name = match.group(1)
    args_str = match.group(2).strip()

    # Parse arguments (handle nested parens, $, etc.)
    args = _parse_arguments(args_str)

    return PipelineStep(tool_name=tool_name, args=args, parallel_group=0)


def _parse_arguments(args_str: str) -> list[str]:
    """Parse comma-separated arguments, respecting nested structures.

    Args:
        args_str: Arguments string from tool call

    Returns:
        List of argument strings
    """
    if not args_str:
        return []

    args: list[str] = []
    current = ""
    paren_depth = 0
    bracket_depth = 0

    for char in args_str:
        if char == "(" or char == "[":
            paren_depth += 1 if char == "(" else 0
            bracket_depth += 1 if char == "[" else 0
            current += char
        elif char == ")" or char == "]":
            paren_depth -= 1 if char == ")" else 0
            bracket_depth -= 1 if char == "]" else 0
            current += char
        elif char == "," and paren_depth == 0 and bracket_depth == 0:
            if current.strip():
                args.append(current.strip())
            current = ""
        else:
            current += char

    if current.strip():
        args.append(current.strip())

    return args


def _group_parallel_steps(steps: list[PipelineStep]) -> list[list[PipelineStep]]:
    """Group steps by parallel_group number.

    Args:
        steps: List of steps

    Returns:
        List of groups, each group is a list of steps
    """
    groups: dict[int, list[PipelineStep]] = {}

    for step in steps:
        if step.parallel_group not in groups:
            groups[step.parallel_group] = []
        groups[step.parallel_group].append(step)

    # Return in sorted order
    return [groups[k] for k in sorted(groups.keys())]


def _is_valid_field_reference(ref: str) -> bool:
    """Check if field reference is valid.

    Args:
        ref: Field reference like "$", "$.field", "$.field[0]", "$.field[:3]"

    Returns:
        True if valid
    """
    if not ref.startswith("$"):
        return False

    if ref == "$":
        return True

    # Check remaining part after $
    rest = ref[1:]

    # Should start with . or [ for field/array access
    if rest and not rest[0] in (".", "["):
        return False

    # Basic validation: contains only alphanumerics, dots, brackets, colons
    pattern = r"^\.[a-zA-Z_]\w*(\[\d*:?\d*\])*$|^\[[^\]]+\](\[[^\]]+\])*$|^$"
    return bool(re.match(pattern, rest))


async def _execute_step(step: PipelineStep, input_value: Any) -> Any:
    """Execute a single pipeline step.

    Args:
        step: PipelineStep to execute
        input_value: Input value to pass to tool

    Returns:
        Tool result

    Raises:
        Exception: Tool execution error
    """
    # Resolve arguments with field references
    resolved_args = _resolve_arguments(step.args, input_value)

    logger.info("Executing %s with args: %s", step.tool_name, resolved_args)

    # Get tool function
    tool_func = _get_tool_function(step.tool_name)

    # Map positional args to tool function's actual parameter names
    import inspect
    sig = inspect.signature(tool_func)
    param_names = [
        name for name, p in sig.parameters.items()
        if name not in ("self", "cls") and p.kind in (
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    ]

    kwargs = {}
    for i, arg in enumerate(resolved_args):
        if i < len(param_names):
            key = param_names[i]
        else:
            key = f"arg{i}"

        if isinstance(arg, str):
            try:
                kwargs[key] = json.loads(arg)
            except (json.JSONDecodeError, ValueError):
                kwargs[key] = arg
        else:
            kwargs[key] = arg

    # Call tool — may be sync or async
    if asyncio.iscoroutinefunction(tool_func):
        try:
            result = await asyncio.wait_for(tool_func(**kwargs), timeout=30.0)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Tool {step.tool_name} timed out after 30 seconds")
    else:
        result = tool_func(**kwargs)

    return result


def _resolve_arguments(args: list[str], input_value: Any) -> list[Any]:
    """Resolve arguments by replacing field references with actual values.

    Args:
        args: List of argument strings
        input_value: Current pipeline value

    Returns:
        List of resolved argument values
    """
    resolved: list[Any] = []

    for arg in args:
        if arg == "$":
            # Pass entire input
            resolved.append(input_value)
        elif arg.startswith("$."):
            # Field access
            field_path = arg[2:]  # Remove $.
            try:
                value = _get_nested_field(input_value, field_path)
                resolved.append(value)
            except (KeyError, IndexError, TypeError) as e:
                logger.warning("Field access failed for '%s': %s", arg, e)
                resolved.append(None)
        else:
            # Literal argument
            resolved.append(arg)

    return resolved


def _get_nested_field(obj: Any, path: str) -> Any:
    """Get nested field from object using path notation.

    Supports:
      - "field" — dict key
      - "field[0]" — list index
      - "field[:3]" — list slice
      - "field.subfield" — nested access
      - "field[0].subfield" — mixed

    Args:
        obj: Object to access
        path: Path expression

    Returns:
        Value at path

    Raises:
        KeyError, IndexError, TypeError: Access failed
    """
    if not path:
        return obj

    # Split path into segments
    segments = re.split(r"(?=\[)|(?<=\])\.", path)

    current = obj
    for segment in segments:
        if not segment:
            continue

        # Check if segment has array access
        match = re.match(r"(\w+)((?:\[[^\]]+\])*)", segment)
        if not match:
            raise ValueError(f"Invalid path segment: {segment}")

        field_name = match.group(1)
        array_parts = match.group(2)

        # Access field/key
        if isinstance(current, dict):
            current = current[field_name]
        else:
            current = getattr(current, field_name)

        # Handle array access
        if array_parts:
            array_matches = re.findall(r"\[([^\]]*)\]", array_parts)
            for index_expr in array_matches:
                if ":" in index_expr:
                    # Slice notation
                    start, end = index_expr.split(":")
                    start = int(start) if start else None
                    end = int(end) if end else None
                    current = current[start:end]
                else:
                    # Direct index
                    idx = int(index_expr)
                    current = current[idx]

    return current


def _get_tool_function(tool_name: str) -> Any:
    """Get the research tool function by name.

    Args:
        tool_name: Tool name like 'search', 'fetch', 'github'

    Returns:
        Callable tool function

    Raises:
        ImportError: Module not found
        AttributeError: Function not found
    """
    # Map tool names to module paths
    tool_module_map = {
        "search": "loom.tools.search",
        "fetch": "loom.tools.fetch",
        "spider": "loom.tools.spider",
        "markdown": "loom.tools.markdown",
        "github": "loom.tools.github",
        "llm_summarize": "loom.tools.llm",
        "llm_extract": "loom.tools.llm",
        "llm_classify": "loom.tools.llm",
        "social_graph": "loom.tools.social_graph",
        "leak_scan": "loom.tools.leak_scan",
        "threat_profile": "loom.tools.threat_profile",
        "merge": "loom.tools.composer",
        "deep": "loom.tools.deep",
    }

    # Determine module path
    if tool_name in tool_module_map:
        module_path = tool_module_map[tool_name]
    else:
        # Infer module from tool name
        tool_base = tool_name.replace("research_", "")
        module_path = f"loom.tools.{tool_base}"

    # Import module
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        raise ImportError(f"Module {module_path} not found: {str(e)}") from e

    # Get function - try with and without "research_" prefix
    func_name = tool_name if tool_name.startswith("research_") else f"research_{tool_name}"

    try:
        return getattr(module, func_name)
    except AttributeError:
        # Try without prefix
        try:
            return getattr(module, tool_name)
        except AttributeError as e:
            raise AttributeError(
                f"Function {func_name} not found in {module_path}"
            ) from e


# ── Built-in Tools ──


@handle_tool_errors("research_merge")
async def research_merge(arg0: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    """Merge multiple parallel results into a single structure.

    Args:
        arg0: Dict of tool results from parallel execution
        **kwargs: Additional results

    Returns:
        Merged result dict
    """
    try:
        if arg0 is None:
            arg0 = {}

        result = {}

        if isinstance(arg0, dict):
            result.update(arg0)

        result.update(kwargs)

        return {
            "merged": True,
            "sources": list(result.keys()),
            "data": result,
        }
    except Exception as exc:
        return {"error": str(exc), "tool": "research_merge"}
