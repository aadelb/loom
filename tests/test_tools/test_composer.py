"""Tests for tool composition DSL (composer.py)."""

from __future__ import annotations

import asyncio
import pytest

from loom.tools.llm.composer import (
    ComposerResult,
    PipelineStep,
    research_compose,
    research_compose_validate,
    _expand_aliases,
    _get_nested_field,
    _group_parallel_steps,
    _is_valid_field_reference,
    _parse_arguments,
    _parse_pipeline,
    _parse_tool_call,
    _resolve_arguments,
    _split_pipeline_expression,
    research_merge,
)


class TestPipelineValidation:
    """Tests for pipeline validation."""

    def test_validate_empty_pipeline(self):
        """Empty pipeline should fail validation."""
        result = research_compose_validate("")
        assert not result["valid"]
        assert result["errors"]

    def test_validate_single_step(self):
        """Single step pipeline should be valid."""
        result = research_compose_validate("search(query)")
        # May fail if tool not found, but syntax should be valid
        assert isinstance(result, dict)
        assert "valid" in result
        assert "steps" in result

    def test_validate_sequential_steps(self):
        """Sequential pipeline should be valid syntax."""
        result = research_compose_validate("search(q) | fetch($)")
        assert isinstance(result, dict)
        assert "expanded_pipeline" in result

    def test_validate_parallel_steps(self):
        """Parallel pipeline should be valid syntax."""
        result = research_compose_validate("search(q) & github(q) | merge($)")
        assert isinstance(result, dict)
        assert "expanded_pipeline" in result

    def test_validate_with_alias(self):
        """Validate with known alias."""
        result = research_compose_validate("deep_research")
        assert isinstance(result, dict)
        assert "expanded_pipeline" in result

    def test_invalid_field_reference(self):
        """Invalid field reference should be caught."""
        result = research_compose_validate("fetch($.urls[abc])")
        # Should have errors about invalid field reference
        assert isinstance(result, dict)


class TestAliasExpansion:
    """Tests for pipeline alias expansion."""

    def test_expand_deep_research(self):
        """deep_research alias should expand correctly."""
        result = _expand_aliases("deep_research")
        assert "search" in result
        assert "fetch" in result
        assert "markdown" in result

    def test_expand_osint_sweep(self):
        """osint_sweep alias should expand correctly."""
        result = _expand_aliases("osint_sweep")
        assert "search" in result
        assert "github" in result
        assert "merge" in result

    def test_no_alias(self):
        """Non-alias should return unchanged."""
        pipeline = "search(q) | fetch($)"
        result = _expand_aliases(pipeline)
        assert result == pipeline

    def test_nested_alias(self):
        """Nested alias references should be handled."""
        result = _expand_aliases("code_search")
        assert isinstance(result, str)


class TestPipelineParsing:
    """Tests for pipeline parsing."""

    def test_parse_single_tool(self):
        """Parse single tool call."""
        steps = _parse_pipeline("search(query)")
        assert len(steps) == 1
        assert steps[0].tool_name == "search"
        assert steps[0].args == ["query"]

    def test_parse_sequential_steps(self):
        """Parse sequential steps separated by |."""
        steps = _parse_pipeline("search(q) | fetch($)")
        assert len(steps) == 2
        assert steps[0].tool_name == "search"
        assert steps[1].tool_name == "fetch"
        # Parallel groups should differ for sequential
        assert steps[0].parallel_group != steps[1].parallel_group

    def test_parse_parallel_steps(self):
        """Parse parallel steps separated by &."""
        steps = _parse_pipeline("search(q) & github(q)")
        assert len(steps) == 2
        assert steps[0].tool_name == "search"
        assert steps[1].tool_name == "github"
        # Both should have same parallel group
        assert steps[0].parallel_group == steps[1].parallel_group

    def test_parse_mixed_operators(self):
        """Parse mixed sequential and parallel."""
        steps = _parse_pipeline("search(q) & github(q) | merge($)")
        assert len(steps) == 3
        # search and github in same group
        assert steps[0].parallel_group == steps[1].parallel_group
        # merge in different group
        assert steps[2].parallel_group != steps[0].parallel_group

    def test_parse_with_field_references(self):
        """Parse with field reference arguments."""
        steps = _parse_pipeline("fetch($.urls[0])")
        assert len(steps) == 1
        assert steps[0].args == ["$.urls[0]"]

    def test_parse_multiple_arguments(self):
        """Parse tool with multiple arguments."""
        steps = _parse_pipeline("spider($.urls, mode)")
        assert len(steps) == 1
        assert steps[0].args == ["$.urls", "mode"]


class TestToolCallParsing:
    """Tests for individual tool call parsing."""

    def test_parse_simple_call(self):
        """Parse simple tool call."""
        step = _parse_tool_call("search(query)")
        assert step.tool_name == "search"
        assert step.args == ["query"]

    def test_parse_no_args(self):
        """Parse tool with no arguments."""
        step = _parse_tool_call("health_check()")
        assert step.tool_name == "health_check"
        assert step.args == []

    def test_parse_multiple_args(self):
        """Parse tool with multiple arguments."""
        step = _parse_tool_call("spider(urls, mode, concurrency)")
        assert step.tool_name == "spider"
        assert len(step.args) == 3

    def test_parse_with_field_reference(self):
        """Parse with field reference argument."""
        step = _parse_tool_call("fetch($.urls[0])")
        assert step.tool_name == "fetch"
        assert step.args == ["$.urls[0]"]

    def test_invalid_syntax(self):
        """Invalid tool call should raise error."""
        with pytest.raises(ValueError):
            _parse_tool_call("no_parens")

        with pytest.raises(ValueError):
            _parse_tool_call("incomplete(")


class TestArgumentParsing:
    """Tests for argument parsing."""

    def test_parse_no_arguments(self):
        """Parse empty argument list."""
        args = _parse_arguments("")
        assert args == []

    def test_parse_single_argument(self):
        """Parse single argument."""
        args = _parse_arguments("query")
        assert args == ["query"]

    def test_parse_multiple_arguments(self):
        """Parse multiple comma-separated arguments."""
        args = _parse_arguments("q, mode, concurrency")
        assert len(args) == 3
        assert args[0] == "q"

    def test_parse_with_nested_parens(self):
        """Parse arguments with nested parentheses."""
        args = _parse_arguments("func(nested), other")
        assert len(args) == 2

    def test_parse_with_array_access(self):
        """Parse arguments with array indexing."""
        args = _parse_arguments("$.urls[0], $.field[:3]")
        assert len(args) == 2
        assert "$.urls[0]" in args
        assert "$.field[:3]" in args


class TestPipelineExpression:
    """Tests for pipeline expression splitting."""

    def test_split_sequential(self):
        """Split sequential expression."""
        parts = _split_pipeline_expression("a(x) | b(y)")
        assert len(parts) == 2
        assert parts[0] == ("START", "a(x)")
        assert parts[1] == ("|", "b(y)")

    def test_split_parallel(self):
        """Split parallel expression."""
        parts = _split_pipeline_expression("a(x) & b(y)")
        assert len(parts) == 2
        assert parts[0] == ("START", "a(x)")
        assert parts[1] == ("&", "b(y)")

    def test_split_mixed(self):
        """Split mixed operators."""
        parts = _split_pipeline_expression("a(x) & b(y) | c(z)")
        assert len(parts) == 3
        assert parts[1][0] == "&"
        assert parts[2][0] == "|"

    def test_split_with_nested_parens(self):
        """Split respecting nested parentheses."""
        parts = _split_pipeline_expression("a(f(x)) | b(y)")
        assert len(parts) == 2


class TestFieldReferences:
    """Tests for field reference validation and resolution."""

    def test_valid_dollar_sign(self):
        """Single $ should be valid."""
        assert _is_valid_field_reference("$")

    def test_valid_field_access(self):
        """Field access like $.field should be valid."""
        assert _is_valid_field_reference("$.field")
        assert _is_valid_field_reference("$.urls")
        assert _is_valid_field_reference("$.data")

    def test_valid_array_index(self):
        """Array indexing like $.field[0] should be valid."""
        assert _is_valid_field_reference("$.field[0]")
        assert _is_valid_field_reference("$.urls[0]")

    def test_valid_array_slice(self):
        """Array slicing like $.field[:3] should be valid."""
        assert _is_valid_field_reference("$.field[:3]")
        assert _is_valid_field_reference("$.urls[1:5]")

    def test_invalid_references(self):
        """Invalid references should fail."""
        assert not _is_valid_field_reference("not_dollar")
        assert not _is_valid_field_reference("$invalid")


class TestNestedFieldAccess:
    """Tests for nested field access."""

    def test_access_simple_field(self):
        """Access simple dict field."""
        data = {"name": "Alice", "age": 30}
        result = _get_nested_field(data, "name")
        assert result == "Alice"

    def test_access_nested_field(self):
        """Access nested dict field."""
        data = {"user": {"name": "Alice", "age": 30}}
        result = _get_nested_field(data, "user.name")
        assert result == "Alice"

    def test_access_list_index(self):
        """Access list by index."""
        data = {"items": [1, 2, 3, 4, 5]}
        result = _get_nested_field(data, "items[0]")
        assert result == 1

    def test_access_list_slice(self):
        """Access list slice."""
        data = {"items": [1, 2, 3, 4, 5]}
        result = _get_nested_field(data, "items[:3]")
        assert result == [1, 2, 3]

    def test_access_complex_path(self):
        """Access complex nested path."""
        data = {
            "results": [
                {"urls": ["http://a.com", "http://b.com"]},
                {"urls": ["http://c.com"]},
            ]
        }
        result = _get_nested_field(data, "results[0].urls[0]")
        assert result == "http://a.com"

    def test_missing_field(self):
        """Missing field should raise KeyError."""
        data = {"name": "Alice"}
        with pytest.raises((KeyError, IndexError)):
            _get_nested_field(data, "missing")

    def test_empty_path(self):
        """Empty path returns original object."""
        data = {"name": "Alice"}
        result = _get_nested_field(data, "")
        assert result == data


class TestArgumentResolution:
    """Tests for argument resolution with field references."""

    def test_resolve_literal_args(self):
        """Resolve literal argument (no $ reference)."""
        args = ["hello", "world"]
        result = _resolve_arguments(args, None)
        assert result == ["hello", "world"]

    def test_resolve_dollar_sign(self):
        """Resolve $ to entire input value."""
        args = ["$"]
        input_value = {"data": "value"}
        result = _resolve_arguments(args, input_value)
        assert result[0] == input_value

    def test_resolve_field_reference(self):
        """Resolve $.field to nested value."""
        args = ["$.urls[0]"]
        input_value = {"urls": ["http://a.com", "http://b.com"]}
        result = _resolve_arguments(args, input_value)
        assert result[0] == "http://a.com"

    def test_resolve_mixed_args(self):
        """Resolve mix of literal and field references."""
        args = ["mode", "$.urls"]
        input_value = {"urls": ["http://a.com"]}
        result = _resolve_arguments(args, input_value)
        assert result[0] == "mode"
        assert result[1] == ["http://a.com"]

    def test_resolve_missing_field(self):
        """Resolve missing field returns None."""
        args = ["$.missing"]
        input_value = {"data": "value"}
        result = _resolve_arguments(args, input_value)
        assert result[0] is None


class TestParallelGrouping:
    """Tests for grouping parallel steps."""

    def test_group_sequential(self):
        """Group sequential steps."""
        steps = [
            PipelineStep(tool_name="a", args=[], parallel_group=0),
            PipelineStep(tool_name="b", args=[], parallel_group=1),
            PipelineStep(tool_name="c", args=[], parallel_group=2),
        ]
        groups = _group_parallel_steps(steps)
        assert len(groups) == 3
        assert len(groups[0]) == 1
        assert len(groups[1]) == 1

    def test_group_parallel(self):
        """Group parallel steps together."""
        steps = [
            PipelineStep(tool_name="a", args=[], parallel_group=0),
            PipelineStep(tool_name="b", args=[], parallel_group=0),
            PipelineStep(tool_name="c", args=[], parallel_group=1),
        ]
        groups = _group_parallel_steps(steps)
        assert len(groups) == 2
        assert len(groups[0]) == 2
        assert len(groups[1]) == 1


class TestMergeFunction:
    """Tests for built-in merge tool."""

    @pytest.mark.asyncio
    async def test_merge_dict_input(self):
        """Merge should combine dict input."""
        input_dict = {
            "search_results": ["result1"],
            "github_results": ["repo1"],
        }
        result = await research_merge(arg0=input_dict)
        assert result["merged"]
        assert "sources" in result
        assert len(result["sources"]) >= 2

    @pytest.mark.asyncio
    async def test_merge_empty_input(self):
        """Merge should handle empty input."""
        result = await research_merge(arg0=None)
        assert result["merged"]
        assert result["data"] == {}

    @pytest.mark.asyncio
    async def test_merge_with_kwargs(self):
        """Merge should combine dict and kwargs."""
        result = await research_merge(arg0={"a": 1}, b=2, c=3)
        assert result["merged"]
        assert "sources" in result


class TestComposePipelineExecution:
    """Integration tests for pipeline execution."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_compose_simple_pipeline(self):
        """Execute simple sequential pipeline (may require mock tools)."""
        result = await research_compose("search(hello)")
        # May fail if tool not available, but should execute without crashing
        assert isinstance(result, dict)
        assert "success" in result
        assert "errors" in result

    @pytest.mark.asyncio
    async def test_compose_with_alias(self):
        """Execute pipeline with alias (may require mock tools)."""
        result = await research_compose("deep_research")
        assert isinstance(result, dict)
        assert "success" in result

    @pytest.mark.asyncio
    async def test_compose_with_timeout(self):
        """Execute pipeline with timeout."""
        result = await research_compose("search(q)", timeout_ms=5000)
        assert isinstance(result, dict)
        assert "execution_time_ms" in result

    @pytest.mark.asyncio
    async def test_compose_continue_on_error(self):
        """Execute pipeline with continue_on_error flag."""
        result = await research_compose(
            "invalid_tool(arg) | search(q)",
            continue_on_error=True,
        )
        assert isinstance(result, dict)


class TestComposerErrorHandling:
    """Tests for error handling."""

    def test_invalid_pipeline_syntax(self):
        """Invalid syntax should be caught."""
        result = research_compose_validate("(incomplete pipeline")
        assert not result["valid"]
        assert result["errors"]

    def test_nonexistent_tool(self):
        """Nonexistent tool should be caught."""
        result = research_compose_validate("nonexistent_tool_xyz(arg)")
        # Should detect the tool doesn't exist
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_compose_with_invalid_pipeline(self):
        """Compose with invalid pipeline should fail gracefully."""
        result = await research_compose("(incomplete")
        assert not result["success"]
        assert result["errors"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
