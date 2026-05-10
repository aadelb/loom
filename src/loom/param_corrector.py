"""Parameter auto-correction module for Loom's 829+ tools.

Provides automatic detection and correction of common parameter name mistakes,
enabling users to call tools with slightly misspelled or aliased parameter names.

Features:
- Fuzzy matching with confidence scoring
- Common alias detection
- Dynamic tool parameter introspection
- User-friendly correction messages
"""

from __future__ import annotations

import difflib
import importlib
import inspect
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Known common aliases that users frequently use
COMMON_ALIASES: dict[str, str] = {
    "max_results": "limit",
    "num_results": "n",
    "target_language": "target_lang",
    "target_model": "model_name",
    "query_text": "query",
    "search_query": "query",
    "url_list": "urls",
    "max_tokens_output": "max_tokens",
    "darkness": "darkness_level",
    "text_input": "text",
    "content": "text",
    "keywords": "query",
    "search_term": "query",
    "timeout_sec": "timeout",
    "wait_sec": "wait_time",
    "javascript": "javascript_enabled",
    "js_enabled": "javascript_enabled",
    "output_format": "format",
    "return_type": "format",
    "include_metadata": "metadata",
    "show_metadata": "metadata",
    "num_workers": "workers",
    "thread_count": "workers",
    "batch_size": "batch",
}


def suggest_param(
    user_param: str,
    valid_params: list[str],
    confidence_threshold: float = 0.6,
) -> tuple[str | None, float]:
    """Suggest the closest valid parameter name using fuzzy matching.

    Args:
        user_param: The parameter name provided by the user
        valid_params: List of valid parameter names for a tool
        confidence_threshold: Minimum confidence score (0.0-1.0) to suggest

    Returns:
        Tuple of (suggested_param, confidence_score) or (None, 0.0) if no match
    """
    if not valid_params:
        return None, 0.0

    # First check for exact case-insensitive match
    lower_user = user_param.lower()
    for param in valid_params:
        if param.lower() == lower_user:
            return param, 1.0

    # Use difflib for fuzzy matching
    matches = difflib.get_close_matches(
        user_param, valid_params, n=1, cutoff=confidence_threshold
    )

    if matches:
        suggestion = matches[0]
        # Calculate confidence score
        ratio = difflib.SequenceMatcher(None, user_param, suggestion).ratio()
        return suggestion, ratio

    return None, 0.0


def get_tool_params(tool_name: str) -> list[str]:
    """Introspect a tool function to extract valid parameter names.

    Dynamically imports the tool from loom.tools and inspects its signature
    to extract parameter names, excluding 'self' and special params.

    Args:
        tool_name: The name of the tool (e.g., 'fetch', 'spider', 'search')

    Returns:
        List of valid parameter names for the tool, or empty list if not found
    """
    try:
        # Map tool names to module paths (most common patterns)
        tool_modules: dict[str, str] = {
            "fetch": "loom.tools.fetch",
            "spider": "loom.tools.spider",
            "search": "loom.tools.search",
            "markdown": "loom.tools.markdown",
            "deep": "loom.tools.deep",
            "github": "loom.tools.github",
            "llm": "loom.tools.llm",
            "llm_summarize": "loom.tools.llm",
        }

        # Try explicit module mapping first
        module_name = tool_modules.get(tool_name)

        if not module_name:
            # Fallback: try loom.tools.{tool_name}
            module_name = f"loom.tools.{tool_name}"

        module = importlib.import_module(module_name)

        # Find the tool function (usually named research_{tool_name})
        func_name = f"research_{tool_name}"
        if not hasattr(module, func_name):
            # Fallback: look for the tool name without prefix
            func_name = tool_name

        if not hasattr(module, func_name):
            logger.warning(f"Tool function {func_name} not found in {module_name}")
            return []

        func = getattr(module, func_name)

        # Extract parameter names from function signature
        sig = inspect.signature(func)
        params = [
            p.name
            for p in sig.parameters.values()
            if p.name not in ("self", "cls", "kwargs", "args")
            and not p.name.startswith("_")
        ]

        return params

    except (ImportError, AttributeError) as e:
        logger.debug(f"Could not introspect tool {tool_name}: {e}")
        return []


def auto_correct_params(
    tool_name: str,
    user_params: dict[str, Any],
    valid_params: list[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Auto-correct parameter names in a tool call.

    Attempts to correct misspelled or aliased parameter names using:
    1. Common aliases lookup
    2. Fuzzy matching with confidence scoring
    3. Case-insensitive exact matching

    Args:
        tool_name: The name of the tool being called
        user_params: Dictionary of parameters provided by user
        valid_params: Optional pre-computed list of valid params. If None,
                     introspects the tool automatically.

    Returns:
        Tuple of (corrected_params_dict, list_of_correction_messages)
    """
    corrections: list[str] = []
    corrected: dict[str, Any] = {}

    # Get valid params if not provided
    if valid_params is None:
        valid_params = get_tool_params(tool_name)

    # If we couldn't determine valid params, return original
    if not valid_params:
        logger.warning(f"Could not determine valid params for tool {tool_name}")
        return user_params, corrections

    valid_params_set = set(valid_params)

    for user_param, value in user_params.items():
        # Check if param is already valid
        if user_param in valid_params_set:
            corrected[user_param] = value
            continue

        # Try common aliases first
        if user_param in COMMON_ALIASES:
            corrected_name = COMMON_ALIASES[user_param]
            if corrected_name in valid_params_set:
                corrections.append(
                    f"'{user_param}' → '{corrected_name}' (common alias)"
                )
                corrected[corrected_name] = value
                continue

        # Try fuzzy matching
        suggestion, confidence = suggest_param(user_param, valid_params, 0.6)
        if suggestion:
            corrections.append(
                f"'{user_param}' → '{suggestion}' (similarity: {confidence:.0%})"
            )
            corrected[suggestion] = value
            continue

        # No correction found, keep original (may fail validation later)
        logger.debug(f"No correction found for param '{user_param}' in tool {tool_name}")
        corrected[user_param] = value

    return corrected, corrections


def format_correction_message(corrections: list[str]) -> str:
    """Format a user-friendly message summarizing parameter corrections.

    Args:
        corrections: List of correction messages from auto_correct_params

    Returns:
        A formatted string suitable for user display
    """
    if not corrections:
        return ""

    if len(corrections) == 1:
        return f"Auto-corrected parameter: {corrections[0]}"

    message_parts = ["Auto-corrected parameters:"]
    for i, correction in enumerate(corrections, 1):
        message_parts.append(f"  {i}. {correction}")

    return "\n".join(message_parts)
