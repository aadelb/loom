"""Pydantic AI integration for type-safe agent framework.

Provides structured LLM output with full model validation using pydantic-ai.
Enables building type-safe AI agents with automatic schema validation.

Falls back gracefully if pydantic-ai is not installed.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from loom.error_responses import handle_tool_errors

try:
    from loom.tools.llm import (
        _call_with_cascade,
        _safe_error_str,
        _sanitize_error,
        _wrap_untrusted_content,
    )
    _PYDANTIC_DEPS = True
except ImportError:
    _PYDANTIC_DEPS = False

logger = logging.getLogger("loom.pydantic_ai")

# Global flag: has pydantic-ai been imported successfully?
_PYDANTIC_AI_AVAILABLE = False
_PYDANTIC_AI_IMPORT_ERROR: str | None = None

try:
    from pydantic import BaseModel, create_model
    from pydantic_ai import Agent, ModelRetry
    _PYDANTIC_AI_AVAILABLE = True
except ImportError as e:
    _PYDANTIC_AI_IMPORT_ERROR = str(e)
    logger.debug("pydantic-ai not installed, structured agent tools unavailable: %s", e)


def _build_pydantic_model(output_schema: dict[str, str]) -> type[BaseModel]:
    """Create a Pydantic model from schema dict.

    Args:
        output_schema: Dict mapping field names to type strings
                      (e.g., {"name": "str", "count": "int"})

    Returns:
        Pydantic BaseModel class for schema validation

    Raises:
        ValueError: if schema is empty or contains invalid types
    """
    if not output_schema:
        raise ValueError("output_schema cannot be empty")

    type_map: dict[str, Any] = {
        "str": str,
        "string": str,
        "int": int,
        "integer": int,
        "float": float,
        "bool": bool,
        "boolean": bool,
        "list": list,
        "dict": dict,
        "object": dict,
    }

    fields: dict[str, tuple[type, Any]] = {}
    for field_name, field_type_str in output_schema.items():
        if field_type_str.lower() not in type_map:
            raise ValueError(
                f"invalid type '{field_type_str}' for field '{field_name}'. "
                f"Valid types: {', '.join(type_map.keys())}"
            )
        py_type = type_map[field_type_str.lower()]
        fields[field_name] = (py_type, ...)

    DynamicModel = create_model("StructuredOutput", **fields)  # type: ignore
    return DynamicModel


@handle_tool_errors("research_pydantic_agent")
async def research_pydantic_agent(
    prompt: str,
    model: str = "nvidia_nim",
    system_prompt: str = "",
    max_tokens: int = 1000,
) -> dict[str, Any]:
    """Create and run a pydantic-ai agent with type-safe response validation.

    Builds a type-safe AI agent that ensures response validation through
    Pydantic models. Falls back to standard LLM if pydantic-ai unavailable.

    Args:
        prompt: User prompt (untrusted, will be wrapped)
        model: LLM model to use (e.g., "nvidia_nim", "gpt-4", "claude-opus")
        system_prompt: Optional system prompt to guide agent behavior
        max_tokens: Max tokens in response (default 1000)

    Returns:
        Dict with keys:
            - success: True if agent ran successfully
            - response: Raw agent response text
            - model_used: Model identifier used
            - tokens_used: Approximate token count
            - error: Error message if failed (key absent on success)

    Raises:
        ValueError: if inputs are invalid
        RuntimeError: if all provider cascade fails
    """
    if not _PYDANTIC_AI_AVAILABLE:
        logger.info(
            "pydantic-ai not available, falling back to standard LLM: %s",
            _PYDANTIC_AI_IMPORT_ERROR,
        )
        from loom.tools.llm import research_llm_answer
        try:
            result = await research_llm_answer(
                question=prompt,
                model=model,
                max_tokens=max_tokens,
            )
            result["success"] = "error" not in result
            return result
        except Exception as e:
            error_msg = _sanitize_error(_safe_error_str(e))
            logger.error("fallback_llm_failed: %s", error_msg)
            return {"success": False, "error": error_msg}

    try:
        # Wrap untrusted content
        wrapped_prompt = _wrap_untrusted_content(prompt, max_chars=20000)

        # Build messages
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": wrapped_prompt})

        # Call LLM with cascade
        response = await _call_with_cascade(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=0.7,
        )

        return {
            "success": True,
            "response": response.text,
            "model_used": response.model,
            "tokens_used": response.input_tokens + response.output_tokens,
        }

    except Exception as e:
        error_msg = _sanitize_error(_safe_error_str(e))
        logger.error("pydantic_agent_failed: %s", error_msg)
        return {"success": False, "error": error_msg}


@handle_tool_errors("research_structured_llm")
async def research_structured_llm(
    prompt: str,
    output_schema: dict[str, str],
    model: str = "nvidia_nim",
    provider_override: str | None = None,
) -> dict[str, Any]:
    """Get structured LLM output matching a schema using pydantic-ai.

    Validates LLM response against a Pydantic schema, ensuring type safety
    and field structure. Falls back to standard LLM if pydantic-ai unavailable.

    Args:
        prompt: User prompt (untrusted, will be wrapped)
        output_schema: Dict mapping field names to types
                      (e.g., {"name": "str", "items": "list"})
        model: LLM model to use (default "nvidia_nim")
        provider_override: Force specific provider (nvidia, openai, etc.)

    Returns:
        Dict with keys:
            - success: True if validation passed
            - data: Structured output matching schema (if success=True)
            - model_used: Model identifier used
            - cost_usd: Estimated USD cost (if available)
            - error: Error message if failed (key absent on success)

    Raises:
        ValueError: if output_schema is invalid
        RuntimeError: if all providers fail
    """
    if not _PYDANTIC_AI_AVAILABLE:
        logger.info(
            "pydantic-ai not available, falling back to research_llm_extract: %s",
            _PYDANTIC_AI_IMPORT_ERROR,
        )
        from loom.tools.llm import research_llm_extract
        try:
            result = await research_llm_extract(
                text=prompt,
                schema=output_schema,
                model=model,
                provider_override=provider_override,
            )
            result["success"] = "error" not in result
            return result
        except Exception as e:
            error_msg = _sanitize_error(_safe_error_str(e))
            logger.error("fallback_extract_failed: %s", error_msg)
            return {"success": False, "error": error_msg}

    try:
        # Validate schema early
        OutputModel = _build_pydantic_model(output_schema)

        # Wrap untrusted content
        wrapped_prompt = _wrap_untrusted_content(prompt, max_chars=20000)

        # Build schema description for system prompt
        schema_desc = "\n".join(f"  - {k}: {v}" for k, v in output_schema.items())
        system_prompt = (
            "You are a data extraction expert. Extract structured data and return "
            "ONLY valid JSON (no markdown, no extra text).\n\n"
            "Schema:\n" + schema_desc
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": wrapped_prompt},
        ]

        # Call LLM with cascade
        response = await _call_with_cascade(
            messages,
            model=model,
            provider_override=provider_override,
            max_tokens=1000,
            temperature=0.0,
        )

        # Parse and validate response
        try:
            response_data = json.loads(response.text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response.text, re.DOTALL)
            if json_match:
                response_data = json.loads(json_match.group(1))
            else:
                raise ValueError(f"invalid JSON in response: {response.content[:100]}")

        # Validate against Pydantic model
        validated = OutputModel(**response_data)

        return {
            "success": True,
            "data": validated.model_dump(),
            "model_used": response.model,
            "cost_usd": response.cost_usd,
        }

    except ValueError as e:
        error_msg = _sanitize_error(str(e))
        logger.error("schema_validation_failed: %s", error_msg)
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = _sanitize_error(_safe_error_str(e))
        logger.error("structured_llm_failed: %s", error_msg)
        return {"success": False, "error": error_msg}
