"""Contract tests: Verify API schema matches implementation.

Tests cover:
  - OpenAPI schema generation from code
  - Documented parameters exist in function signatures
  - Return types match documentation
  - Parameter types are correctly specified
  - All required fields are marked as required
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any, get_type_hints

import pytest


pytestmark = pytest.mark.unit


class TestOpenAPIGeneration:
    """Test OpenAPI schema generation from function signatures."""

    def test_openapi_gen_imports(self) -> None:
        """OpenAPI generator module imports successfully."""
        try:
            from loom.openapi_gen import pydantic_model_to_schema
            assert pydantic_model_to_schema is not None
        except ImportError as e:
            pytest.fail(f"Failed to import openapi_gen: {e}")

    def test_pydantic_to_schema_conversion(self) -> None:
        """Pydantic models convert to OpenAPI schema correctly."""
        from loom.openapi_gen import pydantic_model_to_schema
        from pydantic import BaseModel, Field

        class TestModel(BaseModel):
            name: str = Field(description="User name")
            age: int = Field(default=0, ge=0, le=150)

        schema = pydantic_model_to_schema(TestModel)
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]

    def test_openapi_categorization(self) -> None:
        """Tool categorization from names works correctly."""
        from loom.openapi_gen import _categorize_tool

        test_cases = [
            ("research_fetch", "Research & Data Collection"),
            ("research_session_open", "Session Management"),
            ("research_config_get", "Configuration"),
            ("research_cache_stats", "Cache Management"),
            ("research_llm_chat", "LLM & Language"),
        ]
        for tool_name, expected_category in test_cases:
            result = _categorize_tool(tool_name)
            assert result == expected_category, (
                f"Tool {tool_name} categorized as '{result}', "
                f"expected '{expected_category}'"
            )


class TestParameterDocumentation:
    """Test that documented parameters match function signatures."""

    def test_fetch_params_match_function(self) -> None:
        """research_fetch documented params match function signature."""
        from loom.tools.fetch import research_fetch
        from loom.params import FetchParams

        sig = inspect.signature(research_fetch)
        params_model = FetchParams.model_json_schema()

        # All required params in model should be in function signature
        required_model_params = params_model.get("required", [])
        func_param_names = set(sig.parameters.keys())

        for param_name in required_model_params:
            assert param_name in func_param_names, (
                f"Required param '{param_name}' from FetchParams model "
                f"not found in research_fetch signature"
            )

    def test_spider_params_match_function(self) -> None:
        """research_spider documented params match function signature."""
        from loom.tools.spider import research_spider
        from loom.params import SpiderParams

        sig = inspect.signature(research_spider)
        params_model = SpiderParams.model_json_schema()

        func_param_names = set(sig.parameters.keys())
        schema_properties = set(params_model.get("properties", {}).keys())

        # Schema properties should be subset of function params
        for param_name in schema_properties:
            assert param_name in func_param_names, (
                f"Schema param '{param_name}' not in research_spider signature"
            )

    def test_markdown_params_match_function(self) -> None:
        """research_markdown documented params match function signature."""
        from loom.tools.markdown import research_markdown
        from loom.params import MarkdownParams

        sig = inspect.signature(research_markdown)
        params_model = MarkdownParams.model_json_schema()

        func_param_names = set(sig.parameters.keys())
        schema_properties = set(params_model.get("properties", {}).keys())

        for param_name in schema_properties:
            assert param_name in func_param_names, (
                f"Schema param '{param_name}' not in research_markdown signature"
            )

    def test_core_tools_have_param_models(self) -> None:
        """All core tools have corresponding Pydantic parameter models."""
        from loom.params import (
            FetchParams,
            SpiderParams,
            MarkdownParams,
            SearchParams,
        )

        models = [FetchParams, SpiderParams, MarkdownParams, SearchParams]

        for model in models:
            assert hasattr(model, "model_json_schema"), (
                f"{model.__name__} missing model_json_schema method"
            )
            schema = model.model_json_schema()
            assert "properties" in schema, (
                f"{model.__name__} schema has no properties"
            )


class TestReturnTypeContracts:
    """Test that actual return types match documented contracts."""

    def test_fetch_returns_dict(self) -> None:
        """research_fetch return type annotation is dict."""
        from loom.tools.fetch import research_fetch

        hints = get_type_hints(research_fetch)
        return_type = hints.get("return")
        assert return_type is not None, "research_fetch missing return type hint"
        # Accept dict or Dict
        type_str = str(return_type).lower()
        assert "dict" in type_str, (
            f"research_fetch return type {return_type} is not dict-like"
        )

    def test_spider_returns_list(self) -> None:
        """research_spider return type annotation is list."""
        from loom.tools.spider import research_spider

        hints = get_type_hints(research_spider)
        return_type = hints.get("return")
        assert return_type is not None, "research_spider missing return type hint"
        type_str = str(return_type).lower()
        assert "list" in type_str, (
            f"research_spider return type {return_type} is not list-like"
        )

    def test_all_tools_have_return_type_hints(self) -> None:
        """Sample of tools have return type hints."""
        from loom.tools.fetch import research_fetch
        from loom.tools.spider import research_spider
        from loom.tools.markdown import research_markdown

        tools = [research_fetch, research_spider, research_markdown]

        for tool in tools:
            hints = get_type_hints(tool)
            assert "return" in hints, (
                f"{tool.__name__} missing return type hint"
            )


class TestParameterTypeConsistency:
    """Test parameter types are consistent between model and function."""

    def test_fetch_url_is_required_string(self) -> None:
        """FetchParams.url is required string matching function signature."""
        from loom.params import FetchParams
        from loom.tools.fetch import research_fetch

        # Check model
        schema = FetchParams.model_json_schema()
        assert "url" in schema["required"], "url not marked required in model"
        url_prop = schema["properties"]["url"]
        assert url_prop["type"] == "string", "url not string type in model"

        # Check function
        sig = inspect.signature(research_fetch)
        url_param = sig.parameters["url"]
        assert url_param.default == inspect.Parameter.empty, (
            "url parameter should have no default (required)"
        )

    def test_fetch_mode_is_literal_string(self) -> None:
        """FetchParams.mode is Literal string with valid options."""
        from loom.params import FetchParams

        schema = FetchParams.model_json_schema()
        mode_prop = schema["properties"]["mode"]

        # Check it has enum constraint
        assert "enum" in mode_prop or "anyOf" in mode_prop, (
            "mode should have enum constraint"
        )

    def test_fetch_max_chars_is_positive_integer(self) -> None:
        """FetchParams.max_chars validates as positive integer."""
        from loom.params import FetchParams

        schema = FetchParams.model_json_schema()
        max_chars_prop = schema["properties"]["max_chars"]

        assert max_chars_prop["type"] == "integer", (
            "max_chars not integer type"
        )
        assert max_chars_prop.get("default", 0) > 0, (
            "max_chars default should be positive"
        )


class TestParameterValidation:
    """Test that parameter models validate correctly."""

    def test_fetch_params_validates_url(self) -> None:
        """FetchParams validates URL format."""
        from loom.params import FetchParams

        # Valid URL
        try:
            params = FetchParams(url="https://example.com")
            assert params.url == "https://example.com"
        except ValueError as e:
            pytest.fail(f"Valid URL rejected: {e}")

        # Invalid URL (missing scheme)
        with pytest.raises(ValueError):
            FetchParams(url="example.com")

    def test_fetch_params_validates_mode(self) -> None:
        """FetchParams validates mode enum."""
        from loom.params import FetchParams

        # Valid modes
        for mode in ["http", "stealthy", "dynamic"]:
            params = FetchParams(url="https://example.com", mode=mode)
            assert params.mode == mode

        # Invalid mode
        with pytest.raises(ValueError):
            FetchParams(url="https://example.com", mode="invalid")

    def test_fetch_params_accepts_reasonable_max_chars(self) -> None:
        """FetchParams accepts reasonable max_chars values."""
        from loom.params import FetchParams

        # Test a range of reasonable values
        test_values = [1000, 5000, 20000, 50000, 100000]
        for value in test_values:
            params = FetchParams(url="https://example.com", max_chars=value)
            assert params.max_chars == value

    def test_fetch_params_proxy_validation(self) -> None:
        """FetchParams validates proxy URL format."""
        from loom.params import FetchParams

        # Valid proxy
        params = FetchParams(
            url="https://example.com",
            proxy="socks5://localhost:9050"
        )
        assert params.proxy == "socks5://localhost:9050"

        # Invalid proxy (bad scheme)
        with pytest.raises(ValueError):
            FetchParams(url="https://example.com", proxy="ftp://invalid")


class TestDocumentationContractIntegrity:
    """Test that documentation reflects actual API contract."""

    def test_tools_reference_md_exists(self) -> None:
        """docs/tools-reference.md exists."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        assert doc_path.exists(), f"Documentation file not found at {doc_path}"

    def test_core_tools_documented(self) -> None:
        """Core tools are documented in tools-reference.md."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        content = doc_path.read_text(encoding="utf-8")

        core_tools = ["research_fetch", "research_spider", "research_markdown"]
        for tool_name in core_tools:
            assert tool_name in content, (
                f"Tool {tool_name} not found in tools-reference.md"
            )

    def test_fetch_documentation_has_return_section(self) -> None:
        """research_fetch documentation includes return type specification."""
        doc_path = Path(__file__).parent.parent.parent / "docs" / "tools-reference.md"
        content = doc_path.read_text(encoding="utf-8")

        # Find research_fetch section
        fetch_idx = content.find("### research_fetch")
        assert fetch_idx != -1, "research_fetch section not found"

        # Look for Returns section after it
        section_end = content.find("###", fetch_idx + 1)
        fetch_section = content[fetch_idx:section_end]

        assert "Returns:" in fetch_section or "**Returns**" in fetch_section, (
            "research_fetch missing Returns documentation"
        )
