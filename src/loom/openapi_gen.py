"""Automatic OpenAPI 3.1 schema generation for all MCP tools.

Introspects registered MCP tools and Pydantic parameter models to generate
a valid OpenAPI 3.1 specification. Serves as documentation and API contract.
"""

from __future__ import annotations

import inspect
import logging
from typing import Any

from pydantic import BaseModel

log = logging.getLogger("loom.openapi_gen")


def pydantic_model_to_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Convert a Pydantic model to OpenAPI schema.

    Args:
        model: Pydantic BaseModel class

    Returns:
        OpenAPI schema dict for the model
    """
    schema = model.model_json_schema()

    # Clean up Pydantic-specific keys
    result: dict[str, Any] = {}
    if "title" in schema:
        result["title"] = schema["title"]
    if "description" in schema:
        result["description"] = schema["description"]

    result["type"] = schema.get("type", "object")

    if "properties" in schema:
        result["properties"] = schema["properties"]

    if "required" in schema:
        result["required"] = schema["required"]

    return result


def _categorize_tool(tool_name: str) -> str:
    """Categorize tool by name prefix.

    Args:
        tool_name: MCP tool name (e.g., 'research_fetch')

    Returns:
        Category string (e.g., 'research', 'security', 'billing')
    """
    # Map tool prefixes to categories (order matters - check specific prefixes first)
    prefix_map = [
        ("research_session_", "Session Management"),
        ("research_config_", "Configuration"),
        ("research_cache_", "Cache Management"),
        ("research_llm_", "LLM & Language"),
        ("research_score_", "Scoring & Evaluation"),
        ("research_benchmark_", "Benchmarking"),
        ("research_consensus_", "Consensus & Validation"),
        ("research_crescendo_", "Attack Orchestration"),
        ("research_model_", "Model Analysis"),
        ("research_reid_", "REID Pipeline"),
        ("research_audit_", "Audit & Compliance"),
        ("research_vastai_", "Infrastructure"),
        ("research_billing_", "Billing"),
        ("research_email_", "Communication"),
        ("research_joplin_", "Knowledge Management"),
        ("research_tor_", "Network & Privacy"),
        ("research_transcribe_", "Media Processing"),
        ("research_document_", "Document Processing"),
        ("research_certificate_", "Security Analysis"),
        ("research_breach_", "Security Analysis"),
        ("research_cve_", "Vulnerability Intelligence"),
        ("research_dns_", "Infrastructure Analysis"),
        ("research_whois_", "Infrastructure Analysis"),
        ("research_nmap_", "Infrastructure Analysis"),
        ("research_ip_", "Infrastructure Analysis"),
        ("research_threat_", "Threat Intelligence"),
        ("research_osint_", "Open Source Intelligence"),
        ("research_darkweb_", "Dark Web Intelligence"),
        ("research_onion_", "Tor & Anonymity"),
        ("research_crypto_", "Cryptography & Blockchain"),
        ("research_stealth_", "Stealth & Evasion"),
        ("research_safety_", "AI Safety & Compliance"),
        ("research_academic_", "Academic Integrity"),
        ("research_career_", "Career Intelligence"),
        ("research_sentiment_", "Sentiment & Analysis"),
        ("research_bias_", "Bias Detection"),
        ("research_toxicity_", "Content Moderation"),
        ("research_fingerprint_", "Privacy & Fingerprinting"),
        ("research_privacy_", "Privacy & Anonymity"),
        ("research_", "Research & Data Collection"),  # Catch-all
    ]

    for prefix, category in prefix_map:
        if tool_name.startswith(prefix):
            return category

    return "Other Tools"


def _get_tool_description(func: Any) -> str:
    """Extract description from function docstring.

    Args:
        func: Callable with optional docstring

    Returns:
        First line of docstring or generic message
    """
    if func.__doc__:
        # Get first non-empty line of docstring
        lines = func.__doc__.strip().split("\n")
        for line in lines:
            cleaned = line.strip()
            if cleaned and not cleaned.startswith(":"):
                return cleaned
    return "MCP tool (no description available)"


def generate_openapi_spec(mcp_instance: Any) -> dict[str, Any]:
    """Generate OpenAPI 3.1 spec from registered MCP tools.

    Introspects the FastMCP instance to extract:
    - Registered tools from list_tools()
    - Parameter schemas from function signatures
    - Docstring descriptions

    Args:
        mcp_instance: FastMCP server instance with registered tools

    Returns:
        Valid OpenAPI 3.1 specification dict
    """
    # Get registered tools
    try:
        tools = mcp_instance.list_tools()
    except Exception as e:
        log.warning("Failed to list tools from MCP instance: %s", e)
        return _empty_spec()

    if not tools:
        return _empty_spec()

    # Build paths grouped by category
    paths: dict[str, dict[str, Any]] = {}
    categories: dict[str, list[str]] = {}

    for tool_info in tools:
        tool_name = tool_info.name if hasattr(tool_info, "name") else str(tool_info)

        # Infer parameter schema
        param_schema = _infer_param_schema(tool_name)

        # Categorize tool
        category = _categorize_tool(tool_name)
        if category not in categories:
            categories[category] = []
        categories[category].append(tool_name)

        # Get description
        description = _get_tool_description(
            _get_tool_func(mcp_instance, tool_name) or (lambda: None)
        )

        # Create path entry
        path_key = f"/tools/{tool_name}"
        paths[path_key] = {
            "post": {
                "operationId": f"invoke_{tool_name}",
                "summary": tool_name.replace("_", " ").title(),
                "description": description,
                "tags": [category],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": param_schema,
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Tool execution successful",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "result": {
                                            "description": "Tool result (type varies by tool)",
                                            "oneOf": [
                                                {"type": "string"},
                                                {"type": "number"},
                                                {"type": "boolean"},
                                                {"type": "array"},
                                                {"type": "object"},
                                                {"type": "null"},
                                            ],
                                        },
                                        "error": {
                                            "type": ["string", "null"],
                                            "description": "Error message if execution failed",
                                        },
                                    },
                                    "required": ["success"],
                                }
                            }
                        },
                    },
                    "400": {
                        "description": "Invalid request parameters",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string"},
                                        "message": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "401": {
                        "description": "Unauthorized - missing or invalid API key",
                    },
                    "500": {
                        "description": "Internal server error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string"},
                                        "message": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                },
                "security": [{"BearerAuth": []}],
            }
        }

    # Build spec
    spec: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": "Loom MCP API",
            "description": "Loom Model Context Protocol API with 720+ research and intelligence tools",
            "version": "1.0.0",
            "contact": {
                "name": "Loom Project",
                "url": "https://github.com/aadel/loom",
            },
        },
        "servers": [
            {
                "url": "http://localhost:8787",
                "description": "Local development server",
            },
        ],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "UUID",
                    "description": "Bearer token for API authentication (LOOM_API_KEY)",
                }
            },
        },
        "tags": [
            {"name": category, "description": f"Tools in {category}"}
            for category in sorted(categories.keys())
        ],
    }

    return spec


def _empty_spec() -> dict[str, Any]:
    """Return a minimal valid OpenAPI spec."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Loom MCP API",
            "description": "Loom Model Context Protocol API",
            "version": "1.0.0",
        },
        "servers": [{"url": "http://localhost:8787"}],
        "paths": {},
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "UUID",
                }
            }
        },
    }


def _get_tool_func(mcp_instance: Any, tool_name: str) -> Any | None:
    """Attempt to retrieve the underlying function for a tool.

    Args:
        mcp_instance: FastMCP instance
        tool_name: Tool name

    Returns:
        Function or None
    """
    try:
        if hasattr(mcp_instance, "_tool_manager") and mcp_instance._tool_manager:
            tools_dict = mcp_instance._tool_manager._tools
            if tool_name in tools_dict:
                return tools_dict[tool_name]
    except Exception:
        pass
    return None


def _infer_param_schema(tool_name: str) -> dict[str, Any]:
    """Infer parameter schema from tool name and signature.

    Attempts to load the Pydantic model from params.py if available,
    otherwise generates a generic schema from function signature.

    Args:
        tool_name: MCP tool name (e.g., 'research_fetch')

    Returns:
        OpenAPI schema for parameters
    """
    # Try to import the params module and find the corresponding model
    try:
        from loom import params as params_module

        # Convert tool name to expected model name (snake_case -> PascalCase + Params)
        # e.g., research_fetch -> FetchParams, research_session_open -> SessionOpenParams
        tool_suffix = tool_name.replace("research_", "")
        potential_names = [
            _to_pascal_case(tool_suffix) + "Params",
            _to_pascal_case(tool_suffix.split("_")[0]) + "Params",
        ]

        for model_name in potential_names:
            if hasattr(params_module, model_name):
                model_class = getattr(params_module, model_name)
                if isinstance(model_class, type) and issubclass(model_class, BaseModel):
                    try:
                        return pydantic_model_to_schema(model_class)
                    except Exception as e:
                        log.debug("Failed to convert model %s: %s", model_name, e)
                        break

    except ImportError:
        pass

    # Fallback: generic schema
    return {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Tool-specific query or parameter",
            }
        },
        "description": f"Parameters for {tool_name} (auto-generated)",
    }


def _to_pascal_case(snake_str: str) -> str:
    """Convert snake_case to PascalCase.

    Args:
        snake_str: Snake case string

    Returns:
        Pascal case string
    """
    return "".join(word.capitalize() for word in snake_str.split("_"))


# Singleton cache for generated spec
_cached_spec: dict[str, Any] | None = None
_cached_mcp_id: int | None = None


def get_openapi_spec(mcp_instance: Any, bypass_cache: bool = False) -> dict[str, Any]:
    """Get or generate OpenAPI spec (with caching).

    Caches the spec keyed by MCP instance identity to avoid regeneration
    on every request.

    Args:
        mcp_instance: FastMCP server instance
        bypass_cache: Force regeneration if True

    Returns:
        OpenAPI 3.1 spec dict
    """
    global _cached_spec, _cached_mcp_id

    instance_id = id(mcp_instance)

    if not bypass_cache and _cached_mcp_id == instance_id and _cached_spec:
        return _cached_spec

    _cached_spec = generate_openapi_spec(mcp_instance)
    _cached_mcp_id = instance_id

    return _cached_spec
