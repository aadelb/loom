"""Tests for shared tool_introspection module.

Tests tool metadata extraction, parameter inspection, and docstring handling.
"""
from __future__ import annotations

from typing import Any

import pytest

from loom.tool_introspection import (
    get_tool_docstring,
    get_tool_params,
    get_tool_signature,
    is_tool_async,
)


# Sample tool functions for testing
def simple_tool(query: str, limit: int = 10) -> dict[str, Any]:
    """Search for documents.

    This is a longer description that should not appear in docstring extraction.
    """
    return {"results": []}


async def async_tool(url: str, timeout: float = 30.0) -> dict[str, str]:
    """Fetch content from URL.

    Supports all major HTTP methods.
    """
    return {"content": ""}


def tool_no_docstring(x: int) -> int:
    return x * 2


def tool_no_annotations(a, b, c=None):
    """Tool without type annotations."""
    return a + b


class MyClass:
    def method(self, param1: str, param2: int = 5) -> bool:
        """A method with annotations."""
        return True

    @classmethod
    def class_method(cls, value: str) -> str:
        """A class method."""
        return value


class TestGetToolSignature:
    """Tests for get_tool_signature()."""

    def test_get_tool_signature_basic(self) -> None:
        """get_tool_signature() extracts basic function info."""
        sig = get_tool_signature(simple_tool)

        assert sig["name"] == "simple_tool"
        assert sig["async"] is False
        assert "params" in sig
        assert "return_type" in sig
        assert "docstring" in sig

    def test_get_tool_signature_parameters(self) -> None:
        """get_tool_signature() extracts parameter info."""
        sig = get_tool_signature(simple_tool)

        params = sig["params"]
        assert len(params) == 2

        assert params[0]["name"] == "query"
        assert params[0]["type"] == "str"
        assert params[0]["required"] is True

        assert params[1]["name"] == "limit"
        assert params[1]["type"] == "int"
        assert params[1]["required"] is False
        assert params[1]["default"] == 10

    def test_get_tool_signature_async_function(self) -> None:
        """get_tool_signature() detects async functions."""
        sig = get_tool_signature(async_tool)

        assert sig["async"] is True
        assert sig["name"] == "async_tool"

    def test_get_tool_signature_return_type(self) -> None:
        """get_tool_signature() extracts return type."""
        sig = get_tool_signature(simple_tool)

        assert "dict" in sig["return_type"]

    def test_get_tool_signature_docstring(self) -> None:
        """get_tool_signature() extracts first line of docstring."""
        sig = get_tool_signature(simple_tool)

        assert sig["docstring"] == "Search for documents."

    def test_get_tool_signature_no_docstring(self) -> None:
        """get_tool_signature() handles missing docstring."""
        sig = get_tool_signature(tool_no_docstring)

        assert sig["docstring"] == ""

    def test_get_tool_signature_no_annotations(self) -> None:
        """get_tool_signature() handles functions without annotations."""
        sig = get_tool_signature(tool_no_annotations)

        params = sig["params"]
        assert len(params) == 3

        # First two params should be "Any" type
        assert params[0]["type"] == "Any"
        assert params[1]["type"] == "Any"

        # Third param has default
        assert params[2]["required"] is False
        assert params[2]["default"] is None

    def test_get_tool_signature_complex_types(self) -> None:
        """get_tool_signature() handles complex type annotations."""
        def tool_complex(items: list[str], config: dict[str, Any]) -> tuple[int, str]:
            """Complex types."""
            return (1, "ok")

        sig = get_tool_signature(tool_complex)

        params = sig["params"]
        # Types should be converted to readable strings
        assert "list" in params[0]["type"]
        assert "dict" in params[1]["type"]

    def test_get_tool_signature_all_defaults(self) -> None:
        """get_tool_signature() handles all parameters with defaults."""
        def tool_defaults(a: int = 1, b: str = "hello", c: bool = False) -> None:
            """All defaults."""
            pass

        sig = get_tool_signature(tool_defaults)

        params = sig["params"]
        assert all(p["required"] is False for p in params)

    def test_get_tool_signature_mixed_args(self) -> None:
        """get_tool_signature() handles mixed required and optional params."""
        def tool_mixed(req1: str, req2: int, opt1: str = "a", opt2: float = 1.0) -> None:
            """Mixed args."""
            pass

        sig = get_tool_signature(tool_mixed)

        params = sig["params"]
        assert params[0]["required"] is True
        assert params[1]["required"] is True
        assert params[2]["required"] is False
        assert params[3]["required"] is False


class TestGetToolParams:
    """Tests for get_tool_params()."""

    def test_get_tool_params_basic(self) -> None:
        """get_tool_params() returns parameter names."""
        params = get_tool_params(simple_tool)

        assert params == ["query", "limit"]

    def test_get_tool_params_async_function(self) -> None:
        """get_tool_params() works with async functions."""
        params = get_tool_params(async_tool)

        assert params == ["url", "timeout"]

    def test_get_tool_params_no_params(self) -> None:
        """get_tool_params() handles functions with no parameters."""
        def no_params_tool() -> str:
            return "ok"

        params = get_tool_params(no_params_tool)

        assert params == []

    def test_get_tool_params_excludes_var_args(self) -> None:
        """get_tool_params() excludes *args and **kwargs."""
        def tool_varargs(a: str, *args: Any, **kwargs: Any) -> None:
            pass

        params = get_tool_params(tool_varargs)

        assert params == ["a"]

    def test_get_tool_params_method(self) -> None:
        """get_tool_params() returns parameter names including self."""
        params = get_tool_params(MyClass.method)

        # self is included in the parameter list
        assert params == ["self", "param1", "param2"]

    def test_get_tool_params_multiple_optional(self) -> None:
        """get_tool_params() returns all parameters including optional."""
        def tool(a: str, b: int = 1, c: bool = False) -> None:
            pass

        params = get_tool_params(tool)

        assert params == ["a", "b", "c"]


class TestGetToolDocstring:
    """Tests for get_tool_docstring()."""

    def test_get_tool_docstring_first_line(self) -> None:
        """get_tool_docstring() returns first line of docstring."""
        docstring = get_tool_docstring(simple_tool)

        assert docstring == "Search for documents."

    def test_get_tool_docstring_async_function(self) -> None:
        """get_tool_docstring() works with async functions."""
        docstring = get_tool_docstring(async_tool)

        assert docstring == "Fetch content from URL."

    def test_get_tool_docstring_no_docstring(self) -> None:
        """get_tool_docstring() handles missing docstring."""
        docstring = get_tool_docstring(tool_no_docstring)

        assert docstring == ""

    def test_get_tool_docstring_max_length(self) -> None:
        """get_tool_docstring() truncates long docstrings."""
        def long_docstring_tool() -> None:
            """This is a very long docstring that exceeds the maximum length limit for a single line and should be truncated."""
            pass

        docstring = get_tool_docstring(long_docstring_tool, max_length=50)

        assert len(docstring) <= 50
        assert docstring.endswith("...")

    def test_get_tool_docstring_short_vs_long(self) -> None:
        """get_tool_docstring() handles both short and long docstrings."""
        def short_doc() -> None:
            """Short."""
            pass

        def long_doc() -> None:
            """This is a very long docstring that definitely exceeds the limit we want to set for the output."""
            pass

        short = get_tool_docstring(short_doc, max_length=20)
        long = get_tool_docstring(long_doc, max_length=20)

        assert short == "Short."
        assert len(long) <= 20
        assert long.endswith("...")


class TestIsToolAsync:
    """Tests for is_tool_async()."""

    def test_is_tool_async_async_function(self) -> None:
        """is_tool_async() returns True for async functions."""
        assert is_tool_async(async_tool) is True

    def test_is_tool_async_sync_function(self) -> None:
        """is_tool_async() returns False for sync functions."""
        assert is_tool_async(simple_tool) is False

    def test_is_tool_async_method(self) -> None:
        """is_tool_async() works with methods."""
        assert is_tool_async(MyClass.method) is False

    def test_is_tool_async_lambda(self) -> None:
        """is_tool_async() handles lambda functions."""
        lambda_func = lambda x: x  # noqa: E731
        assert is_tool_async(lambda_func) is False

    def test_is_tool_async_builtin(self) -> None:
        """is_tool_async() handles builtin functions."""
        assert is_tool_async(len) is False


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_tool_introspection_with_union_types(self) -> None:
        """Signature extraction handles Union types."""
        def union_tool(value: str | int) -> dict[str, Any]:
            """Tool with union type."""
            return {}

        sig = get_tool_signature(union_tool)

        params = sig["params"]
        # Union should be in the type string (may be "Union" or contain types)
        assert "Union" in params[0]["type"] or "int" in params[0]["type"] or "str" in params[0]["type"]

    def test_tool_introspection_with_optional(self) -> None:
        """Signature extraction handles Optional types."""
        def optional_tool(value: str | None = None) -> None:
            """Tool with optional."""
            pass

        sig = get_tool_signature(optional_tool)

        params = sig["params"]
        assert params[0]["required"] is False
        assert params[0]["default"] is None

    def test_tool_introspection_empty_docstring(self) -> None:
        """Signature extraction handles empty docstring."""
        def empty_doc_tool() -> None:
            """"""
            pass

        sig = get_tool_signature(empty_doc_tool)

        assert sig["docstring"] == ""

    def test_tool_introspection_multiline_docstring(self) -> None:
        """get_tool_docstring() returns only first line of multiline docstring."""
        def multiline_tool() -> None:
            """First line of docstring.

            Second paragraph with more details.
            Third line.
            """
            pass

        docstring = get_tool_docstring(multiline_tool)

        assert docstring == "First line of docstring."
        assert "\n" not in docstring

    def test_tool_introspection_special_characters_in_docstring(self) -> None:
        """Signature extraction handles special characters in docstring."""
        def special_tool() -> None:
            """Tool with @special #characters and $symbols."""
            pass

        sig = get_tool_signature(special_tool)

        assert "@special" in sig["docstring"]
        assert "$symbols" in sig["docstring"]

    def test_tool_introspection_nested_function(self) -> None:
        """Signature extraction works with nested functions."""
        def outer() -> None:
            def inner(x: int) -> str:
                """Inner tool."""
                return str(x)

            sig = get_tool_signature(inner)
            assert sig["name"] == "inner"
            assert sig["params"][0]["name"] == "x"

        outer()

    def test_tool_params_no_duplicates(self) -> None:
        """get_tool_params() doesn't include duplicates."""
        def tool(a: str, b: int, c: str) -> None:
            pass

        params = get_tool_params(tool)

        assert len(params) == 3
        assert params.count("a") == 1
        assert params.count("b") == 1
        assert params.count("c") == 1

    def test_tool_introspection_preserves_order(self) -> None:
        """Parameter order is preserved in introspection."""
        def ordered_tool(z: str, y: int, x: bool, w: float) -> None:
            """Reverse alphabetical order."""
            pass

        params = get_tool_params(ordered_tool)

        assert params == ["z", "y", "x", "w"]

    def test_tool_introspection_with_annotations_dict(self) -> None:
        """Signature extraction handles cases where get_type_hints fails gracefully."""
        def tricky_tool(x: "ForwardRef") -> None:  # type: ignore
            """Tool with forward reference."""
            pass

        sig = get_tool_signature(tricky_tool)

        # Should not crash, should handle the forward ref gracefully
        assert sig["name"] == "tricky_tool"
        assert len(sig["params"]) == 1
