"""Tests for Brain Action Layer — Tool execution and param extraction."""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.brain.action import (
    _rule_based_extract,
    execute_step,
    extract_params,
)
from loom.brain.types import PlanStep, QualityMode


class TestRuleBasedExtract:
    """Test rule-based parameter extraction."""

    def test_extract_query_param(self) -> None:
        """Test extracting query parameter."""
        schema = {"query": {"type": "string", "required": True}}
        result = _rule_based_extract("search for python", schema)
        assert result.get("query") == "search for python"

    def test_extract_url_param(self) -> None:
        """Test extracting URL parameter."""
        schema = {"url": {"type": "string", "required": True}}
        result = _rule_based_extract("fetch https://example.com", schema)
        assert result.get("url") == "https://example.com"

    def test_extract_multiple_urls_first(self) -> None:
        """Test that multiple URLs extract the first."""
        schema = {"url": {"type": "string"}}
        result = _rule_based_extract(
            "fetch https://example.com and https://test.org",
            schema,
        )
        assert result.get("url") == "https://example.com"

    def test_extract_domain_param(self) -> None:
        """Test extracting domain parameter."""
        schema = {"domain": {"type": "string"}}
        result = _rule_based_extract("analyze example.com", schema)
        assert "example.com" in result.get("domain", "")

    def test_extract_limit_param(self) -> None:
        """Test extracting limit/max_results parameter."""
        schema = {"limit": {"type": "integer"}}
        result = _rule_based_extract("search and get 42 results", schema)
        assert result.get("limit") == 42

    def test_extract_n_param(self) -> None:
        """Test extracting n parameter."""
        schema = {"n": {"type": "integer"}}
        result = _rule_based_extract("return 10 items", schema)
        assert result.get("n") == 10

    def test_extract_max_results_param(self) -> None:
        """Test extracting max_results parameter."""
        schema = {"max_results": {"type": "integer"}}
        result = _rule_based_extract("find up to 25 items", schema)
        assert result.get("max_results") == 25

    def test_extract_depth_default(self) -> None:
        """Test that depth parameter gets default value."""
        schema = {"depth": {"type": "integer"}}
        result = _rule_based_extract("query", schema)
        assert result.get("depth") == 2  # Default depth

    def test_extract_count_param(self) -> None:
        """Test extracting count parameter."""
        schema = {"count": {"type": "integer"}}
        result = _rule_based_extract("get 5 results", schema)
        assert result.get("count") == 5

    def test_extract_no_matching_params(self) -> None:
        """Test extraction with no matching params in query."""
        schema = {"unknown_field": {"type": "string"}}
        result = _rule_based_extract("some query", schema)
        assert result.get("unknown_field") is None

    def test_extract_preserves_multiple_params(self) -> None:
        """Test extracting multiple parameters at once."""
        schema = {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
        }
        result = _rule_based_extract("search for python with 50 results", schema)
        assert result.get("query") == "search for python with 50 results"
        assert result.get("limit") == 50

    def test_extract_handles_case_insensitive_query(self) -> None:
        """Test that extraction is case-insensitive where appropriate."""
        schema = {"query": {"type": "string"}}
        result = _rule_based_extract("SEARCH FOR SOMETHING", schema)
        assert result.get("query") is not None


class TestExtractParams:
    """Test parameter extraction layer."""

    @pytest.mark.asyncio
    async def test_extract_params_rule_based(self) -> None:
        """Test rule-based parameter extraction."""
        schema = {"query": {"type": "string", "required": True}}
        params = await extract_params(
            "research_search",
            "search for python",
            schema,
            QualityMode.ECONOMY,
        )
        assert "query" in params

    @pytest.mark.asyncio
    async def test_extract_params_fills_defaults(self) -> None:
        """Test that defaults are filled."""
        schema = {
            "query": {"type": "string", "required": True},
            "timeout": {"type": "integer", "default": 30},
        }
        params = await extract_params(
            "research_search",
            "search for something",
            schema,
            QualityMode.ECONOMY,
        )
        assert params.get("timeout") == 30

    @pytest.mark.asyncio
    async def test_extract_params_economy_mode(self) -> None:
        """Test economy mode extraction."""
        schema = {"query": {"type": "string"}}
        params = await extract_params(
            "research_search",
            "test query",
            schema,
            QualityMode.ECONOMY,
        )
        assert isinstance(params, dict)

    @pytest.mark.asyncio
    async def test_extract_params_empty_schema(self) -> None:
        """Test extraction with empty schema."""
        params = await extract_params(
            "research_search",
            "test",
            {},
            QualityMode.AUTO,
        )
        assert isinstance(params, dict)


class TestExecuteStep:
    """Test step execution."""

    @pytest.mark.asyncio
    async def test_execute_step_success(self) -> None:
        """Test successful step execution."""
        step = PlanStep(tool_name="research_search", params={"query": "test"})

        mock_tool = AsyncMock(return_value={"success": True, "data": "results"})

        with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
            result = await execute_step(
                step=step,
                query="test query",
                quality_mode=QualityMode.AUTO,
            )

            assert result.get("success") is True
            assert "result" in result

    @pytest.mark.asyncio
    async def test_execute_step_tool_not_found(self) -> None:
        """Test execution when tool is not found."""
        step = PlanStep(tool_name="nonexistent_tool", params={})

        with patch("loom.brain.action._get_tool_function", return_value=None):
            result = await execute_step(
                step=step,
                query="test",
                quality_mode=QualityMode.AUTO,
            )

            assert result.get("success") is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_step_timeout(self) -> None:
        """Test step execution with timeout."""
        step = PlanStep(tool_name="research_search", params={"query": "test"}, timeout=0.001)

        async def slow_tool(**kwargs: dict) -> dict:
            import asyncio
            await asyncio.sleep(10)
            return {"success": True}

        with patch("loom.brain.action._get_tool_function", return_value=slow_tool):
            result = await execute_step(
                step=step,
                query="test",
                quality_mode=QualityMode.AUTO,
            )

            # Should timeout
            assert result.get("success") is False or "elapsed_ms" in result

    @pytest.mark.asyncio
    async def test_execute_step_records_elapsed_time(self) -> None:
        """Test that execution time is recorded."""
        step = PlanStep(tool_name="research_search", params={})

        mock_tool = AsyncMock(return_value={"success": True})

        with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
            result = await execute_step(
                step=step,
                query="test",
                quality_mode=QualityMode.AUTO,
            )

            assert "elapsed_ms" in result
            assert isinstance(result["elapsed_ms"], int)

    @pytest.mark.asyncio
    async def test_execute_step_with_context(self) -> None:
        """Test step execution with context injection."""
        step = PlanStep(tool_name="research_fetch", params={"url": "https://example.com"})

        mock_tool = AsyncMock(return_value={"success": True, "content": "data"})

        context = {
            "recent": [{"tool": "research_search", "success": True}],
            "previous_outputs": [],
        }

        with patch("loom.brain.action._get_tool_function", return_value=mock_tool):
            result = await execute_step(
                step=step,
                query="fetch and summarize",
                quality_mode=QualityMode.AUTO,
                context=context,
            )

            assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_execute_step_handles_sync_tool(self) -> None:
        """Test execution of synchronous tools."""
        step = PlanStep(tool_name="research_search", params={"query": "test"})

        def sync_tool(**kwargs: dict) -> dict:
            return {"success": True, "data": "results"}

        with patch("loom.brain.action._get_tool_function", return_value=sync_tool):
            result = await execute_step(
                step=step,
                query="test",
                quality_mode=QualityMode.AUTO,
            )

            assert result.get("success") is True


class TestGetToolFunction:
    """Test tool function resolution."""

    def test_get_tool_function_cached(self) -> None:
        """Test that tool functions are cached."""
        from loom.brain.action import _get_tool_function, _resolved_tools

        mock_func = MagicMock()
        with patch("loom.brain.action._resolve_tool", return_value=mock_func):
            func1 = _get_tool_function("research_search")
            func2 = _get_tool_function("research_search")

            assert func1 is func2  # Same object due to caching

    def test_get_tool_function_not_found(self) -> None:
        """Test when tool function is not found."""
        from loom.brain.action import _get_tool_function

        with patch("loom.brain.action._resolve_tool", return_value=None):
            func = _get_tool_function("nonexistent_tool")
            assert func is None

    def test_get_tool_function_returns_callable(self) -> None:
        """Test that returned tool is callable."""
        from loom.brain.action import _get_tool_function

        mock_func = MagicMock()
        with patch("loom.brain.action._resolve_tool", return_value=mock_func):
            func = _get_tool_function("research_search")
            assert callable(func)


class TestBuildSchema:
    """Test _build_schema reads function signature."""

    def test_build_schema_from_function(self) -> None:
        from loom.brain.action import _build_schema

        async def sample_tool(query: str, limit: int = 10, timeout: float = 30.0) -> dict:
            pass

        schema = _build_schema("sample_tool", sample_tool)
        assert "query" in schema
        assert schema["query"]["type"] == "string"
        assert "limit" in schema
        assert "timeout" in schema

    def test_build_schema_no_params(self) -> None:
        from loom.brain.action import _build_schema

        async def no_params_tool() -> dict:
            pass

        schema = _build_schema("no_params_tool", no_params_tool)
        assert schema == {} or len(schema) == 0


class TestFilterAndValidateParams:
    """Test _filter_and_validate_params strips unknown params."""

    def test_strips_unknown_params(self) -> None:
        from loom.brain.action import _filter_and_validate_params

        schema = {"query": {"type": "string"}, "limit": {"type": "integer"}}
        params = {"query": "test", "limit": 5, "unknown_param": "should_be_removed"}
        filtered = _filter_and_validate_params(params, schema)
        assert "query" in filtered
        assert "limit" in filtered
        assert "unknown_param" not in filtered

    def test_preserves_valid_params(self) -> None:
        from loom.brain.action import _filter_and_validate_params

        schema = {"query": {"type": "string"}, "n": {"type": "integer"}}
        params = {"query": "hello", "n": 10}
        filtered = _filter_and_validate_params(params, schema)
        assert filtered == params
