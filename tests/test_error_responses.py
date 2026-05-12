"""Tests for error_responses module.

Tests success_response, error_response, and handle_tool_errors decorator
for both sync and async functions.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from loom.error_responses import error_response, handle_tool_errors, success_response


class TestSuccessResponse:
    """Test success_response function."""

    def test_basic_success_response(self) -> None:
        """Test basic success response with minimal data."""
        data = {"results": [1, 2, 3]}
        result = success_response(data)
        assert result == {"results": [1, 2, 3]}
        assert isinstance(result, dict)

    def test_success_response_with_tool_name(self) -> None:
        """Test success response includes tool name."""
        data = {"items": []}
        result = success_response(data, tool="research_test")
        assert result["tool"] == "research_test"
        assert result["items"] == []

    def test_success_response_with_source(self) -> None:
        """Test success response includes source."""
        data = {"content": "text"}
        result = success_response(data, source="cache")
        assert result["source"] == "cache"
        assert result["content"] == "text"

    def test_success_response_with_cached_flag(self) -> None:
        """Test success response includes cached flag."""
        data = {"value": 42}
        result = success_response(data, cached=True)
        assert result["cached"] is True
        assert result["value"] == 42

    def test_success_response_with_elapsed_time(self) -> None:
        """Test success response includes elapsed milliseconds."""
        data = {"status": "ok"}
        result = success_response(data, elapsed_ms=150)
        assert result["elapsed_ms"] == 150
        assert result["status"] == "ok"

    def test_success_response_all_fields(self) -> None:
        """Test success response with all optional fields."""
        data = {"count": 5}
        result = success_response(
            data,
            tool="research_multi",
            source="api",
            cached=True,
            elapsed_ms=200,
        )
        assert result["count"] == 5
        assert result["tool"] == "research_multi"
        assert result["source"] == "api"
        assert result["cached"] is True
        assert result["elapsed_ms"] == 200

    def test_success_response_does_not_mutate_original(self) -> None:
        """Test that success_response does not mutate the original dict."""
        original = {"data": "value"}
        result = success_response(original, tool="test")
        assert "tool" not in original
        assert "tool" in result
        assert original == {"data": "value"}

    def test_success_response_with_empty_dict(self) -> None:
        """Test success response with empty data dict."""
        result = success_response({})
        assert result == {}

    def test_success_response_omits_zero_elapsed(self) -> None:
        """Test that elapsed_ms=0 is omitted from response."""
        result = success_response({"x": 1}, elapsed_ms=0)
        assert "elapsed_ms" not in result


class TestErrorResponse:
    """Test error_response function."""

    def test_basic_error_response_with_string(self) -> None:
        """Test basic error response with string message."""
        result = error_response("Something went wrong")
        assert result["error"] == "Something went wrong"
        assert "error_type" not in result

    def test_error_response_with_exception(self) -> None:
        """Test error response with exception instance."""
        exc = ValueError("Invalid input")
        result = error_response(exc)
        assert result["error"] == "Invalid input"
        assert result["error_type"] == "ValueError"

    def test_error_response_with_tool_name(self) -> None:
        """Test error response includes tool name."""
        result = error_response("failed", tool="research_test")
        assert result["tool"] == "research_test"
        assert result["error"] == "failed"

    def test_error_response_with_explicit_error_type(self) -> None:
        """Test error response with explicit error_type."""
        result = error_response("problem", error_type="CustomError")
        assert result["error_type"] == "CustomError"
        assert result["error"] == "problem"

    def test_error_response_with_exception_overrides_error_type(self) -> None:
        """Test that explicit error_type doesn't override exception class name."""
        exc = RuntimeError("oops")
        result = error_response(exc, error_type="Explicit")
        assert result["error_type"] == "Explicit"

    def test_error_response_with_extra_fields(self) -> None:
        """Test error response includes extra fields."""
        result = error_response(
            "failed",
            tool="test",
            detail="extra info",
            code=500,
        )
        assert result["error"] == "failed"
        assert result["tool"] == "test"
        assert result["detail"] == "extra info"
        assert result["code"] == 500

    def test_error_response_converts_exception_to_string(self) -> None:
        """Test that exception message is converted to string."""
        exc = TypeError("wrong type")
        result = error_response(exc)
        assert isinstance(result["error"], str)
        assert result["error"] == "wrong type"

    def test_error_response_with_multi_word_exception(self) -> None:
        """Test error response with multi-word exception class."""
        exc = ConnectionError("Connection failed")
        result = error_response(exc)
        assert result["error_type"] == "ConnectionError"

    def test_error_response_empty_string_error(self) -> None:
        """Test error response with empty string message."""
        result = error_response("")
        assert result["error"] == ""


class TestHandleToolErrorsDecorator:
    """Test handle_tool_errors decorator for sync and async functions."""

    def test_sync_function_success(self) -> None:
        """Test decorator on successful sync function."""
        @handle_tool_errors("test_tool")
        def sync_func() -> dict[str, Any]:
            return {"result": "success"}

        result = sync_func()
        assert result["result"] == "success"
        assert "elapsed_ms" in result

    def test_sync_function_exception(self) -> None:
        """Test decorator catches sync function exception."""
        @handle_tool_errors("failing_tool")
        def sync_func() -> dict[str, Any]:
            raise ValueError("test error")

        result = sync_func()
        assert "error" in result
        assert "test error" in result["error"]
        assert result["error_type"] == "ValueError"
        assert result["tool"] == "failing_tool"
        assert "elapsed_ms" in result

    def test_sync_function_adds_elapsed_time(self) -> None:
        """Test decorator adds elapsed_ms to result."""
        @handle_tool_errors("timed_tool")
        def sync_func() -> dict[str, Any]:
            return {"status": "ok"}

        result = sync_func()
        assert "elapsed_ms" in result
        assert isinstance(result["elapsed_ms"], int)
        assert result["elapsed_ms"] >= 0

    def test_sync_function_preserves_existing_elapsed(self) -> None:
        """Test decorator doesn't overwrite existing elapsed_ms."""
        @handle_tool_errors("test")
        def sync_func() -> dict[str, Any]:
            return {"elapsed_ms": 100}

        result = sync_func()
        assert result["elapsed_ms"] == 100

    @pytest.mark.asyncio
    async def test_async_function_success(self) -> None:
        """Test decorator on successful async function."""
        @handle_tool_errors("async_tool")
        async def async_func() -> dict[str, Any]:
            await asyncio.sleep(0.001)
            return {"result": "success"}

        result = await async_func()
        assert result["result"] == "success"
        assert "elapsed_ms" in result

    @pytest.mark.asyncio
    async def test_async_function_exception(self) -> None:
        """Test decorator catches async function exception."""
        @handle_tool_errors("async_failing")
        async def async_func() -> dict[str, Any]:
            raise RuntimeError("async error")

        result = await async_func()
        assert "error" in result
        assert "async error" in result["error"]
        assert result["error_type"] == "RuntimeError"
        assert result["tool"] == "async_failing"

    @pytest.mark.asyncio
    async def test_async_function_adds_elapsed_time(self) -> None:
        """Test decorator adds elapsed_ms to async result."""
        @handle_tool_errors("async_timed")
        async def async_func() -> dict[str, Any]:
            return {"status": "ok"}

        result = await async_func()
        assert "elapsed_ms" in result
        assert isinstance(result["elapsed_ms"], int)

    def test_decorator_preserves_function_metadata(self) -> None:
        """Test decorator preserves function name and docstring."""
        @handle_tool_errors("test")
        def my_func() -> dict[str, Any]:
            """My function docstring."""
            return {"x": 1}

        assert my_func.__name__ == "my_func"
        assert "My function docstring" in my_func.__doc__

    def test_sync_function_with_arguments(self) -> None:
        """Test decorator works with function arguments."""
        @handle_tool_errors("test")
        def func_with_args(a: int, b: str = "default") -> dict[str, Any]:
            return {"a": a, "b": b}

        result = func_with_args(42, b="custom")
        assert result["a"] == 42
        assert result["b"] == "custom"

    @pytest.mark.asyncio
    async def test_async_function_with_arguments(self) -> None:
        """Test async decorator works with function arguments."""
        @handle_tool_errors("test")
        async def async_func_args(x: int, y: str) -> dict[str, Any]:
            return {"x": x, "y": y}

        result = await async_func_args(99, "test")
        assert result["x"] == 99
        assert result["y"] == "test"

    def test_sync_function_non_dict_return(self) -> None:
        """Test decorator on sync function returning non-dict."""
        @handle_tool_errors("test")
        def func_returns_string() -> str:  # type: ignore
            return "not a dict"

        result = func_returns_string()
        assert result == "not a dict"
