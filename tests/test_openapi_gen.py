"""Tests for OpenAPI schema generation module."""

import pytest
from unittest.mock import MagicMock

from loom.openapi_gen import (
    generate_openapi_spec,
    get_openapi_spec,
    pydantic_model_to_schema,
    _categorize_tool,
    _empty_spec,
    _infer_param_schema,
    _to_pascal_case,
)
from loom import params


class TestPydanticModelToSchema:
    """Test Pydantic model to OpenAPI schema conversion."""

    def test_fetch_params_conversion(self):
        """Test FetchParams model conversion."""
        schema = pydantic_model_to_schema(params.FetchParams)

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "url" in schema["properties"]
        assert "mode" in schema["properties"]

    def test_spider_params_conversion(self):
        """Test SpiderParams model conversion."""
        schema = pydantic_model_to_schema(params.SpiderParams)

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "urls" in schema["properties"]


class TestCategorizeToolFunction:
    """Test tool categorization logic."""

    def test_research_fetch_categorization(self):
        """Test research_fetch tool categorization."""
        result = _categorize_tool("research_fetch")
        assert result == "Research & Data Collection"

    def test_session_tool_categorization(self):
        """Test session management tools."""
        result = _categorize_tool("research_session_open")
        assert result == "Session Management"

    def test_config_tool_categorization(self):
        """Test configuration tools."""
        result = _categorize_tool("research_config_get")
        assert result == "Configuration"

    def test_cache_tool_categorization(self):
        """Test cache management tools."""
        result = _categorize_tool("research_cache_stats")
        assert result == "Cache Management"

    def test_scoring_tool_categorization(self):
        """Test scoring tools."""
        result = _categorize_tool("research_score_all")
        assert result == "Scoring & Evaluation"

    def test_unknown_tool_categorization(self):
        """Test unknown tool defaults to 'Other Tools'."""
        result = _categorize_tool("unknown_tool_xyz")
        assert result == "Other Tools"


class TestToPascalCase:
    """Test snake_case to PascalCase conversion."""

    def test_single_word(self):
        """Test single word conversion."""
        assert _to_pascal_case("fetch") == "Fetch"

    def test_multiple_words(self):
        """Test multiple word conversion."""
        assert _to_pascal_case("session_open") == "SessionOpen"
        assert _to_pascal_case("config_get") == "ConfigGet"

    def test_empty_string(self):
        """Test empty string."""
        assert _to_pascal_case("") == ""


class TestInferParamSchema:
    """Test parameter schema inference."""

    def test_fetch_params_inference(self):
        """Test inference for research_fetch tool."""
        schema = _infer_param_schema("research_fetch")

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "url" in schema["properties"]

    def test_fallback_schema(self):
        """Test fallback schema for unknown tools."""
        schema = _infer_param_schema("research_unknown_xyz")

        assert schema["type"] == "object"
        assert "properties" in schema
        assert "query" in schema["properties"]


class TestEmptySpec:
    """Test minimal OpenAPI spec generation."""

    def test_empty_spec_structure(self):
        """Test empty spec has required structure."""
        spec = _empty_spec()

        assert spec["openapi"] == "3.1.0"
        assert "info" in spec
        assert "servers" in spec
        assert "paths" in spec
        assert "components" in spec

    def test_empty_spec_has_security_scheme(self):
        """Test empty spec has BearerAuth security scheme."""
        spec = _empty_spec()

        assert "securitySchemes" in spec["components"]
        assert "BearerAuth" in spec["components"]["securitySchemes"]


class TestGenerateOpenAPISpec:
    """Test OpenAPI spec generation from MCP instance."""

    def test_spec_generation_with_empty_tools(self):
        """Test spec generation with no tools registered."""
        mock_mcp = MagicMock()
        mock_mcp.list_tools.return_value = []

        spec = generate_openapi_spec(mock_mcp)

        assert spec["openapi"] == "3.1.0"
        assert spec["paths"] == {}

    def test_spec_generation_with_single_tool(self):
        """Test spec generation with one tool."""
        mock_tool = MagicMock()
        mock_tool.name = "research_fetch"

        mock_mcp = MagicMock()
        mock_mcp.list_tools.return_value = [mock_tool]
        mock_mcp._tool_manager = None

        spec = generate_openapi_spec(mock_mcp)

        assert spec["openapi"] == "3.1.0"
        assert "/tools/research_fetch" in spec["paths"]
        assert "post" in spec["paths"]["/tools/research_fetch"]

    def test_spec_has_required_sections(self):
        """Test generated spec has all required sections."""
        mock_mcp = MagicMock()
        mock_mcp.list_tools.return_value = []

        spec = generate_openapi_spec(mock_mcp)

        assert "openapi" in spec
        assert "info" in spec
        assert "servers" in spec
        assert "paths" in spec
        assert "components" in spec
        # tags is optional and only present when there are categories

    def test_spec_info_section(self):
        """Test spec info section content."""
        mock_mcp = MagicMock()
        mock_mcp.list_tools.return_value = []

        spec = generate_openapi_spec(mock_mcp)

        assert spec["info"]["title"] == "Loom MCP API"
        assert spec["info"]["description"] is not None
        assert len(spec["info"]["description"]) > 0


class TestGetOpenAPISpecCaching:
    """Test caching behavior of get_openapi_spec."""

    def test_caching_enabled_by_default(self):
        """Test that caching is enabled by default."""
        mock_mcp = MagicMock()
        mock_mcp.list_tools.return_value = []

        # First call
        spec1 = get_openapi_spec(mock_mcp)

        # Second call should use cache
        spec2 = get_openapi_spec(mock_mcp)

        assert spec1 is spec2  # Same object from cache

    def test_cache_bypass(self):
        """Test bypassing the cache."""
        mock_mcp = MagicMock()
        mock_mcp.list_tools.return_value = []

        # First call
        spec1 = get_openapi_spec(mock_mcp, bypass_cache=False)

        # Second call with bypass
        spec2 = get_openapi_spec(mock_mcp, bypass_cache=True)

        # Both should be dicts with same content but different if they were regenerated
        assert spec1["openapi"] == spec2["openapi"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
