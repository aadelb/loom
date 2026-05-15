"""Tests for pydantic_ai_backend integration.

Tests structured LLM output with pydantic-ai schema validation.
Falls back to standard LLM tools when pydantic-ai is unavailable.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom.tools.backends.pydantic_ai_backend import (
    _build_pydantic_model,
    research_pydantic_agent,
    research_structured_llm,
    _PYDANTIC_AI_AVAILABLE,
)


class TestBuildPydanticModel:
    """Test Pydantic model generation from schema dict."""

    def test_build_model_simple_types(self):
        """Build model with simple type fields."""
        schema = {
            "name": "str",
            "age": "int",
            "active": "bool",
            "score": "float",
        }
        model = _build_pydantic_model(schema)

        # Create instance and validate
        instance = model(name="Alice", age=30, active=True, score=95.5)
        assert instance.name == "Alice"
        assert instance.age == 30
        assert instance.active is True
        assert instance.score == 95.5

    def test_build_model_complex_types(self):
        """Build model with list and dict fields."""
        schema = {
            "items": "list",
            "metadata": "dict",
            "title": "string",
        }
        model = _build_pydantic_model(schema)

        instance = model(items=[1, 2, 3], metadata={"key": "value"}, title="Test")
        assert instance.items == [1, 2, 3]
        assert instance.metadata == {"key": "value"}

    def test_build_model_type_aliases(self):
        """Test type aliases (string -> str, integer -> int, etc.)."""
        schema = {
            "name": "string",
            "count": "integer",
            "enabled": "boolean",
        }
        model = _build_pydantic_model(schema)
        instance = model(name="test", count=42, enabled=False)
        assert instance.name == "test"
        assert instance.count == 42

    def test_build_model_empty_schema_fails(self):
        """Empty schema should raise ValueError."""
        with pytest.raises(ValueError, match="output_schema cannot be empty"):
            _build_pydantic_model({})

    def test_build_model_invalid_type_fails(self):
        """Invalid type string should raise ValueError."""
        schema = {"field": "invalid_type"}
        with pytest.raises(ValueError, match="invalid type 'invalid_type'"):
            _build_pydantic_model(schema)

    def test_build_model_invalid_field_name_in_error(self):
        """Error message should include problematic field name."""
        schema = {"my_field": "badtype"}
        with pytest.raises(ValueError, match="my_field"):
            _build_pydantic_model(schema)


@pytest.mark.unit
class TestPydanticAgent:
    """Test research_pydantic_agent function."""

    @pytest.mark.skipif(not _PYDANTIC_AI_AVAILABLE, reason="pydantic-ai not installed")
    @pytest.mark.asyncio
    async def test_pydantic_agent_success(self):
        """Agent should return response on success."""
        with patch("loom.tools.backends.pydantic_ai_backend._call_with_cascade") as mock_cascade:
            mock_response = MagicMock()
            mock_response.content = "Agent response text"
            mock_response.model = "nvidia-llama2"
            mock_response.input_tokens = 10
            mock_response.output_tokens = 50
            mock_cascade.return_value = mock_response

            result = await research_pydantic_agent(
                prompt="What is 2+2?",
                model="nvidia_nim",
                system_prompt="You are a math tutor.",
            )

            assert result["success"] is True
            assert result["response"] == "Agent response text"
            assert result["model_used"] == "nvidia-llama2"
            assert result["tokens_used"] == 60

    @pytest.mark.asyncio
    async def test_pydantic_agent_fallback_to_llm(self):
        """Should fallback to research_llm_answer when pydantic-ai unavailable."""
        with patch("loom.tools.backends.pydantic_ai_backend._PYDANTIC_AI_AVAILABLE", False):
            with patch(
                "loom.tools.backends.pydantic_ai_backend.research_llm_answer"
            ) as mock_llm:
                mock_llm.return_value = {
                    "answer": "2+2 equals 4",
                    "model": "gpt-4",
                }

                result = await research_pydantic_agent(
                    prompt="What is 2+2?",
                )

                assert result["success"] is True
                mock_llm.assert_called_once()

    @pytest.mark.skipif(not _PYDANTIC_AI_AVAILABLE, reason="pydantic-ai not installed")
    @pytest.mark.asyncio
    async def test_pydantic_agent_error_handling(self):
        """Agent should handle errors gracefully."""
        with patch("loom.tools.backends.pydantic_ai_backend._call_with_cascade") as mock_cascade:
            mock_cascade.side_effect = ValueError("Test error")

            result = await research_pydantic_agent(
                prompt="Test prompt",
            )

            assert result["success"] is False
            assert "error" in result


@pytest.mark.unit
class TestStructuredLLM:
    """Test research_structured_llm function."""

    @pytest.mark.skipif(not _PYDANTIC_AI_AVAILABLE, reason="pydantic-ai not installed")
    @pytest.mark.asyncio
    async def test_structured_llm_success(self):
        """Should extract and validate structured data."""
        import json

        schema = {"name": "str", "age": "int"}

        with patch("loom.tools.backends.pydantic_ai_backend._call_with_cascade") as mock_cascade:
            mock_response = MagicMock()
            mock_response.content = json.dumps({"name": "Alice", "age": 30})
            mock_response.model = "nvidia-llama2"
            mock_response.cost_usd = 0.001
            mock_cascade.return_value = mock_response

            result = await research_structured_llm(
                prompt="Extract person info",
                output_schema=schema,
            )

            assert result["success"] is True
            assert result["data"]["name"] == "Alice"
            assert result["data"]["age"] == 30
            assert result["model_used"] == "nvidia-llama2"

    @pytest.mark.skipif(not _PYDANTIC_AI_AVAILABLE, reason="pydantic-ai not installed")
    @pytest.mark.asyncio
    async def test_structured_llm_markdown_json(self):
        """Should handle JSON wrapped in markdown code blocks."""
        schema = {"title": "str"}

        with patch("loom.tools.backends.pydantic_ai_backend._call_with_cascade") as mock_cascade:
            mock_response = MagicMock()
            mock_response.content = '```json\n{"title": "Test"}\n```'
            mock_response.model = "gpt-4"
            mock_response.cost_usd = 0.002
            mock_cascade.return_value = mock_response

            result = await research_structured_llm(
                prompt="Extract title",
                output_schema=schema,
            )

            assert result["success"] is True
            assert result["data"]["title"] == "Test"

    @pytest.mark.skipif(not _PYDANTIC_AI_AVAILABLE, reason="pydantic-ai not installed")
    @pytest.mark.asyncio
    async def test_structured_llm_invalid_json(self):
        """Should fail gracefully on invalid JSON."""
        schema = {"name": "str"}

        with patch("loom.tools.backends.pydantic_ai_backend._call_with_cascade") as mock_cascade:
            mock_response = MagicMock()
            mock_response.content = "not valid json at all"
            mock_cascade.return_value = mock_response

            result = await research_structured_llm(
                prompt="Extract data",
                output_schema=schema,
            )

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.skipif(not _PYDANTIC_AI_AVAILABLE, reason="pydantic-ai not installed")
    @pytest.mark.asyncio
    async def test_structured_llm_schema_validation_fails(self):
        """Should fail when response doesn't match schema."""
        schema = {"name": "str", "age": "int"}

        with patch("loom.tools.backends.pydantic_ai_backend._call_with_cascade") as mock_cascade:
            import json
            mock_response = MagicMock()
            # Missing required 'age' field
            mock_response.content = json.dumps({"name": "Bob"})
            mock_cascade.return_value = mock_response

            result = await research_structured_llm(
                prompt="Extract person info",
                output_schema=schema,
            )

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_structured_llm_fallback(self):
        """Should fallback to research_llm_extract when pydantic-ai unavailable."""
        with patch("loom.tools.backends.pydantic_ai_backend._PYDANTIC_AI_AVAILABLE", False):
            with patch(
                "loom.tools.backends.pydantic_ai_backend.research_llm_extract"
            ) as mock_extract:
                mock_extract.return_value = {
                    "data": {"name": "Charlie"},
                }

                result = await research_structured_llm(
                    prompt="Extract name",
                    output_schema={"name": "str"},
                )

                assert result["success"] is True
                mock_extract.assert_called_once()

    @pytest.mark.skipif(not _PYDANTIC_AI_AVAILABLE, reason="pydantic-ai not installed")
    @pytest.mark.asyncio
    async def test_structured_llm_with_provider_override(self):
        """Should pass provider_override to cascade."""
        schema = {"data": "str"}

        with patch("loom.tools.backends.pydantic_ai_backend._call_with_cascade") as mock_cascade:
            import json
            mock_response = MagicMock()
            mock_response.content = json.dumps({"data": "test"})
            mock_response.model = "gpt-4"
            mock_response.cost_usd = 0.001
            mock_cascade.return_value = mock_response

            await research_structured_llm(
                prompt="Test",
                output_schema=schema,
                provider_override="openai",
            )

            # Verify provider_override was passed
            mock_cascade.assert_called_once()
            call_kwargs = mock_cascade.call_args[1]
            assert call_kwargs.get("provider_override") == "openai"


@pytest.mark.unit
class TestIntegration:
    """Integration tests for pydantic-ai backend."""

    def test_import_availability(self):
        """Check if pydantic-ai availability flag is set correctly."""
        # If pydantic-ai is installed, the flag should be True
        # If not, it should be False with an error message
        import loom.tools.backends.pydantic_ai_backend

        if pydantic_ai_backend._PYDANTIC_AI_AVAILABLE:
            assert pydantic_ai_backend._PYDANTIC_AI_IMPORT_ERROR is None
        else:
            assert pydantic_ai_backend._PYDANTIC_AI_IMPORT_ERROR is not None
            assert isinstance(pydantic_ai_backend._PYDANTIC_AI_IMPORT_ERROR, str)

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Tools should work even if pydantic-ai is not installed."""
        # Both tools should return valid responses or fallbacks
        import loom.tools.backends.pydantic_ai_backend

        with patch.object(pydantic_ai_backend, "_PYDANTIC_AI_AVAILABLE", False):
            with patch("loom.tools.backends.pydantic_ai_backend.research_llm_answer") as mock_llm:
                mock_llm.return_value = {"answer": "response"}

                result = await research_pydantic_agent(prompt="test")
                assert isinstance(result, dict)
                assert "success" in result or "answer" in result
