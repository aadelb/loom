"""Instructor integration for guaranteed structured outputs from LLMs.

Provides research_structured_extract tool that wraps instructor library to
ensure validated Pydantic outputs with automatic retry on validation failure.

Falls back to research_llm_extract if instructor is not installed.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from loom.providers.base import LLMResponse
    from loom.tools.llm import (
        _call_with_cascade,
        _safe_error_str,
        _sanitize_error,
        _wrap_untrusted_content,
    )
    _INSTRUCTOR_DEPS = True
except ImportError:
    _INSTRUCTOR_DEPS = False

logger = logging.getLogger("loom.instructor")

# Global flag: has instructor been imported successfully?
_INSTRUCTOR_AVAILABLE = False
_INSTRUCTOR_IMPORT_ERROR: str | None = None

try:
    import instructor
    from pydantic import BaseModel, create_model
    _INSTRUCTOR_AVAILABLE = True
except ImportError as e:
    _INSTRUCTOR_IMPORT_ERROR = str(e)
    logger.debug("instructor not installed, fallback to research_llm_extract: %s", e)


def _create_pydantic_model(
    output_schema: dict[str, str],
) -> type[BaseModel]:
    """Dynamically create a Pydantic model from a schema dict.

    Args:
        output_schema: Dict mapping field names to type strings
                      (e.g., {"name": "str", "age": "int", "items": "list"})

    Returns:
        Pydantic BaseModel class

    Raises:
        ValueError: if schema is empty or contains invalid type names
    """
    if not output_schema:
        raise ValueError("output_schema cannot be empty")

    # Map type strings to Python types
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

    # Build field definitions for create_model
    fields: dict[str, tuple[type, Any]] = {}
    for field_name, field_type_str in output_schema.items():
        if field_type_str.lower() not in type_map:
            raise ValueError(
                f"invalid type '{field_type_str}' for field '{field_name}'. "
                f"Valid types: {', '.join(type_map.keys())}"
            )
        py_type = type_map[field_type_str.lower()]
        # All fields are required by default; use str | None for optional
        fields[field_name] = (py_type, ...)

    # Dynamically create the Pydantic model
    DynamicModel = create_model("ExtractedData", **fields)  # type: ignore
    return DynamicModel


async def _patch_and_call_instructor(
    client: Any,
    model: str,
    messages: list[dict[str, str]],
    output_schema: dict[str, str],
    max_retries: int = 3,
) -> dict[str, Any]:
    """Patch a provider client with instructor and call it.

    Args:
        client: OpenAI/Anthropic/etc. async client instance
        model: Model identifier to use
        messages: Chat messages
        output_schema: Schema dict for extraction
        max_retries: Max validation retries

    Returns:
        Dict with extracted_data, retries_used, validation_passed

    Raises:
        ValueError: if schema is invalid
        RuntimeError: if all retries exhausted
    """
    # Create the Pydantic model from schema
    OutputModel = _create_pydantic_model(output_schema)

    # Patch the client with instructor
    patched_client = instructor.from_openai(client)

    # Call with retries
    retry_count = 0
    last_error: Exception | None = None

    while retry_count < max_retries:
        try:
            # Call the patched client with response_model
            response = await patched_client.messages.create(
                model=model,
                messages=messages,
                response_model=OutputModel,
                max_retries=1,  # Let instructor handle 1 retry internally
            )

            # Convert Pydantic model to dict
            extracted_data = response.model_dump()

            return {
                "extracted_data": extracted_data,
                "retries_used": retry_count,
                "validation_passed": True,
            }

        except Exception as e:
            last_error = e
            retry_count += 1
            logger.debug(
                "instructor_validation_failed attempt=%d/%d error=%s",
                retry_count,
                max_retries,
                _sanitize_error(_safe_error_str(e)),
            )

    # All retries exhausted
    error_msg = (
        f"structured extraction failed after {max_retries} retries: "
        f"{_sanitize_error(_safe_error_str(last_error))}"
    )
    raise RuntimeError(error_msg)


async def research_structured_extract(
    text: str,
    output_schema: dict[str, str] | str,
    model: str = "auto",
    max_retries: int = 3,
    provider_override: str | None = None,
) -> dict[str, Any]:
    """Extract structured data from text with guaranteed schema compliance.

    Uses instructor library to get validated Pydantic outputs from LLMs.
    Automatically retries on validation failure. Falls back to
    research_llm_extract if instructor is not installed.

    Args:
        text: Input text to extract from (user-supplied, untrusted)
        output_schema: Dict mapping field names to types
                      (e.g., {"name": "str", "age": "int", "items": "list"})
        model: LLM model to use ('auto' for cascade)
        max_retries: Max validation retries before giving up
        provider_override: Force a specific provider (nvidia, openai, anthropic, etc.)

    Returns:
        Dict with keys:
            - extracted_data: the validated extracted dict
            - model: model identifier used
            - provider: provider name used
            - cost_usd: estimated USD cost
            - retries_needed: number of validation retries performed
            - validation_passed: always True if successful
            - instructor_used: True if instructor was used, False if fallback

    Raises:
        ValueError: if output_schema is invalid
        RuntimeError: if all retries exhausted or all providers fail
    """
    # Coerce string to dict before validation
    if isinstance(output_schema, str):
        output_schema = {"extract": output_schema}

    # If instructor not available, fall back to research_llm_extract
    if not _INSTRUCTOR_AVAILABLE:
        logger.info(
            "instructor not available, falling back to research_llm_extract: %s",
            _INSTRUCTOR_IMPORT_ERROR,
        )
        # Import and call the fallback
        try:
            from loom.tools.llm import research_llm_extract
            fallback_result = await research_llm_extract(
                text=text,
                schema=output_schema,
                model=model,
                provider_override=provider_override,
            )
            # Normalize the fallback result
            fallback_result["instructor_used"] = False
            if "data" in fallback_result and "error" not in fallback_result:
                fallback_result["extracted_data"] = fallback_result.pop("data")
                fallback_result["retries_needed"] = 0
                fallback_result["validation_passed"] = True
            return fallback_result
        except Exception as e:
            logger.error("fallback_extract_failed: %s", _sanitize_error(_safe_error_str(e)))
            raise

    # Validate schema early
    try:
        _create_pydantic_model(output_schema)
    except ValueError as e:
        logger.error("invalid_schema: %s", e)
        raise

    # Wrap untrusted content
    wrapped_text = _wrap_untrusted_content(text, max_chars=20000)

    # Build schema description
    schema_desc = "\n".join(f"  - {k}: {v}" for k, v in output_schema.items())

    system_prompt = (
        "You are a data extraction expert. Extract structured data from the "
        "following text and return ONLY valid JSON (no markdown, no extra text).\n\n"
        "Schema:\n" + schema_desc
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": wrapped_text},
    ]

    try:
        # Call LLM with cascade
        response: LLMResponse = await _call_with_cascade(
            messages,
            model=model,
            provider_override=provider_override,
            max_tokens=1000,
            temperature=0.0,
        )

        # Now use instructor to validate/extract
        # We need the actual provider client to patch it
        if provider_override:
            from loom.tools.llm import _get_provider
            provider_instance = _get_provider(provider_override)
        else:
            # Use the provider from the cascade response
            from loom.tools.llm import _get_provider
            provider_name = response.provider.lower()
            provider_instance = _get_provider(provider_name)

        # Get the underlying client
        if hasattr(provider_instance, "_get_client"):
            client = provider_instance._get_client()
        elif hasattr(provider_instance, "client"):
            if provider_instance.client is None:
                # Some providers lazy-initialize; try to get it
                if hasattr(provider_instance, "_get_client"):
                    client = provider_instance._get_client()
                else:
                    raise RuntimeError(f"cannot access client for provider {response.provider}")
            client = provider_instance.client
        else:
            raise RuntimeError(f"cannot access client for provider {response.provider}")

        # Call with instructor patching
        extraction_result = await _patch_and_call_instructor(
            client=client,
            model=response.model,
            messages=messages,
            output_schema=output_schema,
            max_retries=max_retries,
        )

        # Build final result
        result = {
            "extracted_data": extraction_result["extracted_data"],
            "model": response.model,
            "provider": response.provider,
            "cost_usd": response.cost_usd,
            "retries_needed": extraction_result["retries_used"],
            "validation_passed": extraction_result["validation_passed"],
            "instructor_used": True,
        }
        return result

    except Exception as e:
        error_msg = _sanitize_error(_safe_error_str(e))
        logger.error("structured_extract_failed: %s", error_msg)
        return {
            "error": error_msg,
            "instructor_used": True,
            "extracted_data": None,
            "validation_passed": False,
            "retries_needed": 0,
        }
