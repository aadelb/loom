"""Auto-Parameter Generator — infers tool params from natural language queries."""

from __future__ import annotations

import importlib
import inspect
import logging
import re
from typing import Any

from loom.validators import validate_url, UrlSafetyError

logger = logging.getLogger("loom.tools.auto_params")

# Model name patterns for detection
_MODEL_PATTERNS = (
    "claude", "gpt", "deepseek", "gemini", "llama", "mistral", "falcon",
    "qwen", "moonshot", "kimi", "groq", "nvidia"
)

# Language code mapping (common codes)
_LANGUAGE_CODES = {
    "english": "en", "arabic": "ar", "french": "fr", "spanish": "es",
    "german": "de", "chinese": "zh", "japanese": "ja", "korean": "ko"
}


def _extract_urls(text: str) -> list[str]:
    """Extract HTTP(S) URLs from text, filtered through SSRF validation."""
    pattern = r"https?://[^\s\)]+"
    matches = re.findall(pattern, text)
    urls = [url.rstrip(".,;") for url in matches]

    # Validate each URL against SSRF checks
    validated_urls = []
    for url in urls:
        try:
            validated_url = validate_url(url)
            validated_urls.append(validated_url)
        except (UrlSafetyError, Exception) as e:
            logger.warning("url_rejected_ssrf url=%s error=%s", url, str(e))
            continue

    return validated_urls


def _extract_numbers(text: str) -> list[int]:
    """Extract integers from text."""
    pattern = r"\b(\d+)\b"
    matches = re.findall(pattern, text)
    return [int(m) for m in matches]


def _detect_language(text: str) -> str | None:
    """Detect language code from text."""
    text_lower = text.lower()
    for lang_name, code in _LANGUAGE_CODES.items():
        if lang_name in text_lower:
            return code
    return None


def _detect_model(text: str) -> str | None:
    """Detect model name from text."""
    text_lower = text.lower()
    for model in _MODEL_PATTERNS:
        if model in text_lower:
            return model
    return None


def _extract_domain(text: str) -> str | None:
    """Extract domain-like string (e.g., github.com, example.org)."""
    pattern = r"(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}"
    match = re.search(pattern, text.lower())
    return match.group(0) if match else None


def _infer_param_value(
    param_name: str,
    param_type: Any,
    query: str,
    param_default: Any = inspect.Parameter.empty,
) -> Any | None:
    """Infer a single parameter value from query based on name and type.

    Returns None if no value can be inferred.
    """
    param_lower = param_name.lower()

    # URL parameters
    if "url" in param_lower or "uri" in param_lower:
        urls = _extract_urls(query)
        return urls[0] if urls else None

    # List of URLs
    if "urls" in param_lower:
        urls = _extract_urls(query)
        return urls if urls else None

    # Query/prompt/text parameters
    if any(x in param_lower for x in ("query", "prompt", "text", "content")):
        return query

    # Domain/target parameters
    if any(x in param_lower for x in ("domain", "target", "host")):
        domain = _extract_domain(query)
        return domain if domain else None

    # Model/provider parameters
    if any(x in param_lower for x in ("model", "target_model", "provider")):
        model = _detect_model(query)
        return model if model else None

    # Strategy parameters
    if "strategy" in param_lower:
        # Extract capitalized words or quoted strings
        quoted = re.findall(r"['\"](\w+)['\"]", query)
        if quoted:
            return quoted[0]
        return None

    # Numeric parameters (limit, max_results, count, n)
    if any(x in param_lower for x in ("limit", "max_results", "count", "n", "max_")):
        numbers = _extract_numbers(query)
        return numbers[0] if numbers else 10  # Default limit

    # Language parameters
    if "language" in param_lower or "lang" in param_lower:
        return _detect_language(query)

    # Boolean parameters
    if param_type is bool or param_type == "bool":
        return True  # Default boolean params to True

    # List parameters (wrap single values)
    if "list[" in str(param_type):
        value = _infer_param_value(param_name, str, query, param_default)
        if value:
            return [value] if not isinstance(value, list) else value

    return None


async def research_auto_params(
    tool_name: str,
    query: str,
) -> dict[str, Any]:
    """Auto-infer tool parameters from natural language query.

    Args:
        tool_name: Name of the tool (e.g., 'research_fetch', 'research_search')
        query: Natural language query or description

    Returns:
        Dict with:
            - tool_name: input tool name
            - generated_params: inferred parameters (dict)
            - params_inferred: count of parameters inferred from query
            - params_defaulted: count of parameters set to defaults
            - confidence: score 0-100 based on inference quality
    """
    try:
        # Dynamic import: strip "research_" prefix and try module name variants
        base = tool_name.replace("research_", "")
        func = None
        for candidate_module in [base, base.split("_")[0], tool_name]:
            try:
                module = importlib.import_module(f"loom.tools.{candidate_module}")
                func = getattr(module, tool_name, None)
                if func and callable(func):
                    break
            except ImportError:
                continue

        if not func or not callable(func):
            return {
                "tool_name": tool_name,
                "generated_params": {},
                "params_inferred": 0,
                "params_defaulted": 0,
                "confidence": 0,
                "error": f"Tool {tool_name} not found",
            }

        sig = inspect.signature(func)
        generated = {}
        inferred_count = 0
        defaulted_count = 0

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            # Get parameter type
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                param_type = type(None)

            # Try to infer value
            inferred = _infer_param_value(param_name, param_type, query, param.default)

            if inferred is not None:
                generated[param_name] = inferred
                inferred_count += 1
            elif param.default != inspect.Parameter.empty:
                defaulted_count += 1

        # Confidence: high if we inferred > 50% of params
        total_params = len([p for p in sig.parameters.keys() if p not in ("self", "cls")])
        confidence = int((inferred_count / max(total_params, 1)) * 100) if total_params > 0 else 100

        logger.info(
            "auto_params tool=%s inferred=%d defaulted=%d confidence=%d",
            tool_name, inferred_count, defaulted_count, confidence
        )

        return {
            "tool_name": tool_name,
            "generated_params": generated,
            "params_inferred": inferred_count,
            "params_defaulted": defaulted_count,
            "confidence": confidence,
        }

    except ImportError as e:
        logger.error("Failed to import tool %s: %s", tool_name, e)
        return {
            "tool_name": tool_name,
            "generated_params": {},
            "params_inferred": 0,
            "params_defaulted": 0,
            "confidence": 0,
            "error": f"Import error: {str(e)}",
        }
    except Exception as e:
        logger.error("Error inferring params for %s: %s", tool_name, e)
        return {
            "tool_name": tool_name,
            "generated_params": {},
            "params_inferred": 0,
            "params_defaulted": 0,
            "confidence": 0,
            "error": f"Error: {str(e)}",
        }


async def research_inspect_tool(tool_name: str) -> dict[str, Any]:
    """Return full signature info for a tool.

    Args:
        tool_name: Name of the tool (e.g., 'research_fetch')

    Returns:
        Dict with:
            - tool_name: input tool name
            - module: module name
            - parameters: list of parameter dicts with name/type/default/required
            - docstring: function docstring (first 200 chars)
            - source_file: file path where tool is defined
    """
    try:
        parts = tool_name.rsplit("_", 1)
        if len(parts) == 2:
            module_name, _ = parts
            module = importlib.import_module(f"loom.tools.{module_name}")
        else:
            module = importlib.import_module(f"loom.tools.{tool_name}")

        # Find the function
        func = getattr(module, tool_name, None)
        if not func or not callable(func):
            return {
                "tool_name": tool_name,
                "module": None,
                "parameters": [],
                "docstring": None,
                "source_file": None,
                "error": f"Tool {tool_name} not found",
            }

        sig = inspect.signature(func)
        module_name = module.__name__

        params = []
        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
            default = param.default if param.default != inspect.Parameter.empty else None
            required = default is None

            params.append({
                "name": param_name,
                "type": param_type,
                "default": str(default) if default is not None else None,
                "required": required,
            })

        docstring = None
        if func.__doc__:
            docstring = func.__doc__[:200].strip()

        try:
            source_file = inspect.getsourcefile(func)
        except (TypeError, OSError):
            source_file = None

        logger.info("inspected tool=%s params=%d", tool_name, len(params))

        return {
            "tool_name": tool_name,
            "module": module_name,
            "parameters": params,
            "docstring": docstring,
            "source_file": source_file,
        }

    except Exception as e:
        logger.error("Error inspecting tool %s: %s", tool_name, e)
        return {
            "tool_name": tool_name,
            "module": None,
            "parameters": [],
            "docstring": None,
            "source_file": None,
            "error": f"Error: {str(e)}",
        }
