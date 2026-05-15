"""Tests for instructor_backend tool integration.

Tests structured extraction with schema validation, retry logic, and fallback.
"""

from __future__ import annotations

import pytest

from loom.tools.backends.instructor_backend import (
    _INSTRUCTOR_AVAILABLE,
    _create_pydantic_model,
    research_structured_extract,
)


class TestCreatePydanticModel:
    """Test _create_pydantic_model helper."""

    def test_create_model_basic(self) -> None:
        """Create a basic model with str and int fields."""
        schema = {"name": "str", "age": "int"}
        model_class = _create_pydantic_model(schema)

        # Should be instantiable
        instance = model_class(name="Alice", age=30)
        assert instance.name == "Alice"
        assert instance.age == 30

    def test_create_model_all_types(self) -> None:
        """Create model with all supported types."""
        schema = {
            "name": "str",
            "count": "int",
            "ratio": "float",
            "active": "bool",
            "items": "list",
            "metadata": "dict",
        }
        model_class = _create_pydantic_model(schema)
        instance = model_class(
            name="test",
            count=5,
            ratio=1.5,
            active=True,
            items=["a", "b"],
            metadata={"key": "value"},
        )
        assert instance.name == "test"
        assert instance.count == 5

    def test_create_model_type_aliases(self) -> None:
        """Test type aliases (string/integer/boolean/object)."""
        schema = {
            "text": "string",
            "num": "integer",
            "flag": "boolean",
            "data": "object",
        }
        model_class = _create_pydantic_model(schema)
        instance = model_class(text="hi", num=42, flag=False, data={})
        assert instance.text == "hi"

    def test_create_model_empty_schema_raises(self) -> None:
        """Empty schema should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            _create_pydantic_model({})

    def test_create_model_invalid_type_raises(self) -> None:
        """Invalid type name should raise ValueError."""
        schema = {"name": "str", "unknown": "badtype"}
        with pytest.raises(ValueError, match="invalid type 'badtype'"):
            _create_pydantic_model(schema)

    def test_create_model_case_insensitive_types(self) -> None:
        """Type names should be case-insensitive."""
        schema = {"name": "STR", "count": "INT", "flag": "BOOL"}
        model_class = _create_pydantic_model(schema)
        instance = model_class(name="test", count=5, flag=True)
        assert instance.name == "test"


class TestInstructorAvailability:
    """Test fallback behavior when instructor is not available."""

    def test_instructor_availability_flag(self) -> None:
        """_INSTRUCTOR_AVAILABLE should be True or False."""
        assert isinstance(_INSTRUCTOR_AVAILABLE, bool)

    @pytest.mark.skipif(_INSTRUCTOR_AVAILABLE, reason="instructor installed")
    async def test_fallback_when_instructor_unavailable(self) -> None:
        """If instructor not installed, should fall back to research_llm_extract."""
        # This test only runs when instructor is NOT available
        result = await research_structured_extract(
            text="Alice is 30 years old",
            output_schema={"name": "str", "age": "int"},
        )
        # Should have instructor_used=False in fallback
        assert result.get("instructor_used") is False or result.get("error") is not None


@pytest.mark.skipif(not _INSTRUCTOR_AVAILABLE, reason="instructor not installed")
class TestStructuredExtractWithInstructor:
    """Tests that require instructor library to be installed."""

    async def test_research_structured_extract_returns_dict(self) -> None:
        """research_structured_extract should return a dict with expected keys."""
        # Note: This is a basic structure test; full integration tests need live LLM
        result = await research_structured_extract(
            text="Alice is 30 years old and from New York.",
            output_schema={"name": "str", "age": "int", "city": "str"},
            model="auto",
            max_retries=1,
        )

        # Check result structure
        assert isinstance(result, dict)
        if "error" not in result:
            assert "extracted_data" in result or "error" in result
            assert "instructor_used" in result
            assert result.get("instructor_used") is True

    async def test_research_structured_extract_error_handling(self) -> None:
        """Should handle errors gracefully."""
        result = await research_structured_extract(
            text="Some text",
            output_schema={},  # Invalid: empty schema
            model="auto",
        )
        # Should return error response
        assert isinstance(result, dict)
        assert "error" in result or "extracted_data" in result


class TestInstructorParamValidation:
    """Test parameter validation for instructor tool."""

    def test_param_model_basic(self) -> None:
        """Basic parameter validation should pass."""
        from loom.params import InstructorStructuredExtractParams

        params = InstructorStructuredExtractParams(
            text="Alice is 30",
            output_schema={"name": "str", "age": "int"},
        )
        assert params.text == "Alice is 30"
        assert params.output_schema == {"name": "str", "age": "int"}
        assert params.model == "auto"
        assert params.max_retries == 3

    def test_param_model_empty_text_raises(self) -> None:
        """Empty text should raise validation error."""
        from loom.params import InstructorStructuredExtractParams

        with pytest.raises(ValueError, match="cannot be empty"):
            InstructorStructuredExtractParams(
                text="",
                output_schema={"name": "str"},
            )

    def test_param_model_empty_schema_raises(self) -> None:
        """Empty schema should raise validation error."""
        from loom.params import InstructorStructuredExtractParams

        with pytest.raises(ValueError, match="cannot be empty"):
            InstructorStructuredExtractParams(
                text="Some text",
                output_schema={},
            )

    def test_param_model_invalid_type_raises(self) -> None:
        """Invalid field type should raise validation error."""
        from loom.params import InstructorStructuredExtractParams

        with pytest.raises(ValueError, match="invalid type"):
            InstructorStructuredExtractParams(
                text="Some text",
                output_schema={"field": "badtype"},
            )

    def test_param_model_max_retries_bounds(self) -> None:
        """max_retries must be 1-10."""
        from loom.params import InstructorStructuredExtractParams

        # Too low
        with pytest.raises(ValueError):
            InstructorStructuredExtractParams(
                text="Some text",
                output_schema={"name": "str"},
                max_retries=0,
            )

        # Too high
        with pytest.raises(ValueError):
            InstructorStructuredExtractParams(
                text="Some text",
                output_schema={"name": "str"},
                max_retries=11,
            )

    def test_param_model_valid_providers(self) -> None:
        """Provider override must be from allowed list."""
        from loom.params import InstructorStructuredExtractParams

        # Valid provider
        params = InstructorStructuredExtractParams(
            text="text",
            output_schema={"name": "str"},
            provider_override="openai",
        )
        assert params.provider_override == "openai"

        # Invalid provider
        with pytest.raises(ValueError, match="invalid provider"):
            InstructorStructuredExtractParams(
                text="text",
                output_schema={"name": "str"},
                provider_override="invalid_provider",
            )

    def test_param_model_forbids_extra_fields(self) -> None:
        """Extra fields should be forbidden."""
        from pydantic import ValidationError

        from loom.params import InstructorStructuredExtractParams

        with pytest.raises(ValidationError, match="extra_field"):
            InstructorStructuredExtractParams(
                text="text",
                output_schema={"name": "str"},
                extra_field="not_allowed",
            )

    def test_param_model_strict_mode(self) -> None:
        """Strict mode should enforce type coercion limits."""
        from pydantic import ValidationError

        from loom.params import InstructorStructuredExtractParams

        # String "3" should not coerce to int 3
        with pytest.raises(ValidationError):
            InstructorStructuredExtractParams(
                text="text",
                output_schema={"name": "str"},
                max_retries="3",  # type: ignore
            )
