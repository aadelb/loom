"""Brain Action Layer — Tool execution with param extraction and validation."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Callable

from loom.brain.prompts import PARAM_EXTRACTION_SYSTEM, PARAM_EXTRACTION_USER
from loom.brain.types import PlanStep, QualityMode, ToolMeta

logger = logging.getLogger("loom.brain.action")

_LLM_AVAILABLE = False
_resolved_tools: dict[str, Callable[..., Any]] = {}


def _get_tool_function(tool_name: str) -> Callable[..., Any] | None:
    """Resolve tool name to its actual Python callable."""
    if tool_name in _resolved_tools:
        return _resolved_tools[tool_name]

    func = _resolve_tool(tool_name)
    if func is not None:
        _resolved_tools[tool_name] = func
    return func


def _resolve_tool(tool_name: str) -> Callable[..., Any] | None:
    """Find tool function by scanning loom.tools modules."""
    tools_dir = Path(__file__).parent.parent / "tools"

    # Strategy 1: Try direct import from likely module
    module_candidates = _guess_module_names(tool_name)
    for module_name in module_candidates:
        try:
            import importlib

            mod = importlib.import_module(f"loom.tools.{module_name}")
            func = getattr(mod, tool_name, None)
            if func and callable(func):
                return func
        except (ImportError, AttributeError):
            continue

    # Strategy 2: Use the pre-built name index
    from loom.brain.reasoning import _build_tool_name_index

    name_index = _build_tool_name_index()
    if tool_name in name_index:
        file_path = Path(name_index[tool_name])
        tools_root = Path(__file__).parent.parent / "tools"
        try:
            import importlib

            rel_path = file_path.relative_to(tools_root)
            parts = list(rel_path.with_suffix("").parts)
            module_path = "loom.tools." + ".".join(parts)
            mod = importlib.import_module(module_path)
            func = getattr(mod, tool_name, None)
            if func and callable(func):
                return func
        except (ImportError, AttributeError, ValueError):
            pass

    return None


def _guess_module_names(tool_name: str) -> list[str]:
    """Guess likely module names for a tool function."""
    base = tool_name.replace("research_", "")
    candidates = [base]

    parts = base.split("_")
    if len(parts) >= 2:
        candidates.append("_".join(parts[:2]))
        candidates.append(parts[0])

    common_mappings = {
        "search": "search",
        "fetch": "fetch",
        "markdown": "markdown",
        "spider": "spider",
        "deep": "deep",
        "github": "github",
        "llm": "llm",
        "camoufox": "stealth",
        "botasaurus": "stealth",
        "smart_call": "core",
    }
    for keyword, module in common_mappings.items():
        if keyword in base:
            candidates.append(module)

    return candidates


def _build_schema(tool_name: str, func: Callable[..., Any]) -> dict[str, Any]:
    """Build parameter schema from function signature as ground truth.

    Uses inspect.signature for actual param names/types/defaults.
    Does NOT overwrite with external schemas — those are advisory only.
    """
    schema: dict[str, Any] = {}

    try:
        sig = inspect.signature(func)
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue
            entry: dict[str, Any] = {"required": param.default is inspect.Parameter.empty}
            if param.annotation is not inspect.Parameter.empty:
                entry["type"] = _annotation_to_type_str(param.annotation)
            if param.default is not inspect.Parameter.empty:
                entry["default"] = param.default
            schema[param_name] = entry
    except (ValueError, TypeError):
        pass

    return schema


def _annotation_to_type_str(annotation: Any) -> str:
    """Convert a type annotation to a simple string."""
    if annotation is str:
        return "string"
    elif annotation is int:
        return "integer"
    elif annotation is float:
        return "float"
    elif annotation is bool:
        return "boolean"
    elif annotation is list:
        return "list"
    elif annotation is dict:
        return "dict"
    elif hasattr(annotation, "__origin__"):
        return str(annotation)
    return "string"


async def extract_params(
    tool_name: str,
    query: str,
    schema: dict[str, Any],
    quality_mode: QualityMode = QualityMode.AUTO,
) -> dict[str, Any]:
    """Extract tool parameters from the user query.

    Strategy:
    1. Rule-based extraction from entities/keywords
    2. Validate against schema (ensure required params are found)
    3. LLM extraction via NVIDIA NIM (if available and needed)
    4. Fill defaults for missing required params
    """
    params: dict[str, Any] = {}

    # Rule-based extraction
    params = _rule_based_extract(query, schema)

    # Validate critical required params — try harder to fill them
    params = _validate_and_improve_params(query, params, schema)

    # LLM extraction (NVIDIA only)
    if _LLM_AVAILABLE and quality_mode != QualityMode.ECONOMY:
        try:
            llm_params = await _llm_extract_params(tool_name, query, schema)
            for key, val in llm_params.items():
                if key in schema and val is not None:
                    params[key] = val
        except Exception as exc:
            logger.debug("LLM param extraction failed: %s", exc)

    # Fill defaults
    for key, info in schema.items():
        if key not in params and "default" in info:
            params[key] = info["default"]

    # Validate and filter
    params = _filter_and_validate_params(params, schema)

    return params


def _rule_based_extract(query: str, schema: dict[str, Any]) -> dict[str, Any]:
    """Extract params using pattern matching on common param names."""
    import re

    params: dict[str, Any] = {}
    query_lower = query.lower()

    for param_name, info in schema.items():
        param_type = info.get("type", "string")

        if param_name in ("query", "q", "text", "input", "prompt"):
            params[param_name] = query
        elif param_name == "url":
            urls = re.findall(r"https?://[^\s,\"'<>]+", query)
            if urls:
                params[param_name] = urls[0]
        elif param_name in ("n", "limit", "max_results", "count"):
            numbers = re.findall(r"\b(\d+)\b", query)
            if numbers:
                params[param_name] = int(numbers[0])
        elif param_name in ("target", "domain"):
            import re as _re

            domains = _re.findall(
                r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b",
                query_lower,
            )
            if domains:
                params[param_name] = domains[0]
        elif param_name == "depth" and param_type == "integer":
            params.setdefault(param_name, 2)

    return params


def _validate_and_improve_params(
    query: str, params: dict[str, Any], schema: dict[str, Any]
) -> dict[str, Any]:
    """Validate and attempt to fill critical required parameters.

    For required params that are still missing, try additional extraction strategies.
    For example, if 'url' is required but not found in initial rule-based extraction,
    search more aggressively for URLs in the query.
    """
    for param_name, info in schema.items():
        if param_name in params and params[param_name] is not None:
            continue  # Already have a value

        if not info.get("required", False):
            continue  # Not required, skip

        # Try harder for required params
        if param_name == "url" and param_name not in params:
            # Extended URL search (more lenient patterns)
            urls = re.findall(r"https?://\S+|www\.\S+", query, re.IGNORECASE)
            if urls:
                params[param_name] = urls[0]
                logger.debug("recovered required param '%s' via extended search", param_name)

        elif param_name in ("domain", "target") and param_name not in params:
            # Try case-insensitive domain extraction
            domains = re.findall(
                r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b",
                query.lower(),
                re.IGNORECASE,
            )
            if domains:
                params[param_name] = domains[0]
                logger.debug("recovered required param '%s' via case-insensitive search", param_name)

    return params


async def _llm_extract_params(
    tool_name: str, query: str, schema: dict[str, Any]
) -> dict[str, Any]:
    """Use NVIDIA NIM LLM for intelligent param extraction."""
    try:
        from loom.providers.nvidia_nim import NvidiaNimProvider

        provider = NvidiaNimProvider()
        if not await asyncio.to_thread(provider.available):
            return {}

        schema_str = json.dumps(schema, indent=2, default=str)
        prompt = PARAM_EXTRACTION_USER.format(
            query=query, tool_name=tool_name, param_schema=schema_str
        )

        response = await asyncio.to_thread(
            provider.chat,
            messages=[
                {"role": "system", "content": PARAM_EXTRACTION_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.1,
        )

        text = response.text if hasattr(response, "text") else str(response)
        json_match = _extract_json_from_text(text)
        if json_match:
            return json_match
    except Exception as exc:
        logger.debug("nvidia param extraction error: %s", exc)

    return {}


def _extract_json_from_text(text: str) -> dict[str, Any] | None:
    """Extract JSON object from LLM response text."""
    import re

    json_patterns = [
        re.compile(r"```json\s*\n?(.*?)\n?```", re.DOTALL),
        re.compile(r"```\s*\n?(.*?)\n?```", re.DOTALL),
        re.compile(r"\{[^{}]*\}"),
    ]

    for pattern in json_patterns:
        match = pattern.search(text)
        if match:
            try:
                return json.loads(match.group(1) if match.lastindex else match.group(0))
            except (json.JSONDecodeError, IndexError):
                continue
    return None


def _filter_and_validate_params(
    params: dict[str, Any], schema: dict[str, Any]
) -> dict[str, Any]:
    """Filter params to only those in schema and validate types.

    Does NOT coerce int/float/bool/list/dict to str — preserves native types.
    """
    filtered: dict[str, Any] = {}
    for key, value in params.items():
        if key not in schema:
            continue
        info = schema[key]
        expected_type = info.get("type", "string")

        if value is None:
            if not info.get("required", False):
                filtered[key] = value
            continue

        if expected_type == "integer" and isinstance(value, (int, float)):
            filtered[key] = int(value)
        elif expected_type == "float" and isinstance(value, (int, float)):
            filtered[key] = float(value)
        elif expected_type == "boolean" and isinstance(value, bool):
            filtered[key] = value
        elif expected_type == "list" and isinstance(value, list):
            filtered[key] = value
        elif expected_type == "dict" and isinstance(value, dict):
            filtered[key] = value
        elif expected_type == "string":
            filtered[key] = str(value)
        else:
            filtered[key] = value

    return filtered


async def execute_step(
    step: PlanStep,
    query: str,
    quality_mode: QualityMode = QualityMode.AUTO,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a single plan step: resolve tool, extract params, call it."""
    start = time.time()
    tool_name = step.tool_name

    func = _get_tool_function(tool_name)
    if func is None:
        return {
            "tool": tool_name,
            "success": False,
            "error": f"tool not found: {tool_name}",
            "elapsed_ms": int((time.time() - start) * 1000),
        }

    schema = _build_schema(tool_name, func)

    if step.params:
        params = _filter_and_validate_params(step.params, schema)
    else:
        params = await extract_params(tool_name, query, schema, quality_mode)

    try:
        if asyncio.iscoroutinefunction(func):
            result = await asyncio.wait_for(func(**params), timeout=step.timeout)
        else:
            result = await asyncio.wait_for(
                asyncio.to_thread(func, **params), timeout=step.timeout
            )

        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "tool": tool_name,
            "success": True,
            "result": result,
            "params_used": params,
            "elapsed_ms": elapsed_ms,
        }
    except asyncio.TimeoutError:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "tool": tool_name,
            "success": False,
            "error": f"timeout after {step.timeout}s",
            "elapsed_ms": elapsed_ms,
        }
    except Exception as exc:
        elapsed_ms = int((time.time() - start) * 1000)
        logger.warning("tool execution failed: %s — %s", tool_name, exc)
        return {
            "tool": tool_name,
            "success": False,
            "error": str(exc),
            "params_used": params,
            "elapsed_ms": elapsed_ms,
        }
