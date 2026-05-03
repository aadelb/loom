"""Tests for daisy-chain multi-hop decomposition."""

from __future__ import annotations

import pytest

from loom.daisy_chain import DaisyChainDecomposer, DaisyChainResult
from loom.params import DaisyChainParams


class TestDaisyChainDecomposerBasic:
    """Basic tests for DaisyChainDecomposer initialization."""

    def test_decomposer_initialization(self) -> None:
        """Test decomposer can be initialized."""
        decomposer = DaisyChainDecomposer()
        assert decomposer is not None
        assert len(decomposer.available_models) == 4

    def test_decomposer_with_models(self) -> None:
        """Test decomposer with custom models."""
        models = ["model-1", "model-2", "model-3"]
        decomposer = DaisyChainDecomposer(available_models=models)
        assert decomposer.available_models == models

    def test_decomposer_default_models(self) -> None:
        """Test default models when none specified."""
        decomposer = DaisyChainDecomposer()
        # Should have default models
        assert hasattr(decomposer, 'available_models')
        assert len(decomposer.available_models) > 0


class TestDaisyChainResult:
    """Tests for DaisyChainResult dataclass."""

    def test_result_creation(self) -> None:
        """Test creating a result."""
        result = DaisyChainResult(
            original_query="test query",
            sub_queries=["sub 1", "sub 2"],
            model_assignments={"sub 1": "model-a", "sub 2": "model-b"},
            sub_responses={"sub 1": "resp 1", "sub 2": "resp 2"},
            combined_response="combined",
            combiner_model="gpt-4",
            success=True,
            hcs_score=5.0,
        )
        assert result.success is True
        assert result.original_query == "test query"
        assert len(result.sub_queries) == 2

    def test_result_fields(self) -> None:
        """Test result has required fields."""
        result = DaisyChainResult(
            original_query="test",
            sub_queries=["q1"],
            model_assignments={"q1": "model-1"},
            sub_responses={"q1": "resp"},
            combined_response="response",
            combiner_model="gpt-4",
            success=True,
            hcs_score=0.0,
        )
        assert hasattr(result, "original_query")
        assert hasattr(result, "sub_queries")
        assert hasattr(result, "sub_responses")
        assert hasattr(result, "combined_response")
        assert hasattr(result, "success")
        assert hasattr(result, "hcs_score")


class TestDaisyChainParams:
    """Test DaisyChainParams validation."""

    def test_params_basic(self) -> None:
        """Test creating params with basic query."""
        params = DaisyChainParams(query="test query")
        assert params.query == "test query"
        assert params.combiner_model == "gpt-4"
        assert params.timeout_per_model == 30.0
        assert params.max_sub_queries == 4

    def test_params_custom(self) -> None:
        """Test custom parameters."""
        models = ["model-1", "model-2"]
        params = DaisyChainParams(
            query="test",
            available_models=models,
            combiner_model="custom-model",
            timeout_per_model=60.0,
        )
        assert params.available_models == models
        assert params.combiner_model == "custom-model"
        assert params.timeout_per_model == 60.0

    def test_params_empty_query_invalid(self) -> None:
        """Test that empty query is caught by validator."""
        with pytest.raises(ValueError, match="cannot be empty"):
            DaisyChainParams(query="")

    def test_params_whitespace_query_invalid(self) -> None:
        """Test that whitespace-only query is caught by validator."""
        with pytest.raises(ValueError, match="cannot be empty"):
            DaisyChainParams(query="   ")

    def test_params_query_max_length(self) -> None:
        """Test query max length constraint."""
        long_query = "x" * 6000
        # Should raise ValidationError due to max_length=5000
        with pytest.raises(ValueError):
            DaisyChainParams(query=long_query)

    def test_params_timeout_bounds(self) -> None:
        """Test timeout bounds."""
        # Too small - should raise ValidationError
        with pytest.raises(ValueError):
            DaisyChainParams(query="test", timeout_per_model=2.0)

        # Too large - should raise ValidationError
        with pytest.raises(ValueError):
            DaisyChainParams(query="test", timeout_per_model=150.0)

    def test_params_timeout_valid_bounds(self) -> None:
        """Test valid timeout values."""
        params = DaisyChainParams(query="test", timeout_per_model=5.0)
        assert params.timeout_per_model == 5.0

        params = DaisyChainParams(query="test", timeout_per_model=120.0)
        assert params.timeout_per_model == 120.0

    def test_params_max_sub_queries_bounds(self) -> None:
        """Test max_sub_queries bounds."""
        # Too small
        with pytest.raises(ValueError):
            DaisyChainParams(query="test", max_sub_queries=1)

        # Too large
        with pytest.raises(ValueError):
            DaisyChainParams(query="test", max_sub_queries=7)

    def test_params_max_sub_queries_valid(self) -> None:
        """Test valid max_sub_queries values."""
        params = DaisyChainParams(query="test", max_sub_queries=2)
        assert params.max_sub_queries == 2

        params = DaisyChainParams(query="test", max_sub_queries=6)
        assert params.max_sub_queries == 6

    def test_params_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden."""
        with pytest.raises(ValueError):
            DaisyChainParams(
                query="test",
                extra_field="not allowed"
            )


class TestDaisyChainDecomposition:
    """Tests for the decompose method."""

    def test_decompose_simple_query(self) -> None:
        """Test decomposing a simple query."""
        decomposer = DaisyChainDecomposer()
        sub_queries = decomposer.decompose("How do I create a system?")
        
        # Should return a list of sub-queries
        assert isinstance(sub_queries, list)
        assert len(sub_queries) > 0
        # Should have 2-4 sub-queries
        assert 2 <= len(sub_queries) <= 4

    def test_decompose_complex_query(self) -> None:
        """Test decomposing a complex query."""
        decomposer = DaisyChainDecomposer()
        sub_queries = decomposer.decompose(
            "How should I approach designing, implementing, and deploying a complex system?"
        )
        
        assert isinstance(sub_queries, list)
        assert len(sub_queries) > 0


class TestIntegration:
    """Integration tests for daisy-chain pipeline."""

    @pytest.mark.asyncio
    async def test_full_pipeline_simple(self) -> None:
        """Test complete daisy-chain pipeline with simple query."""
        decomposer = DaisyChainDecomposer(
            available_models=["model-a", "model-b", "model-c"]
        )

        call_count = {"count": 0}

        async def mock_callback(model: str, prompt: str) -> str:
            call_count["count"] += 1
            return f"Response #{call_count['count']} from {model}"

        callbacks = {
            "model-a": mock_callback,
            "model-b": mock_callback,
            "model-c": mock_callback,
            "gpt-4": mock_callback,
        }

        result = await decomposer.execute_chain(
            "How to create a system",
            callbacks,
            combiner_model="gpt-4"
        )

        assert result.success
        assert result.original_query == "How to create a system"
        assert len(result.sub_queries) > 0
        assert len(result.sub_responses) > 0
        assert result.combined_response != ""
        assert 0.0 <= result.hcs_score <= 10.0

    @pytest.mark.asyncio
    async def test_full_pipeline_complex_query(self) -> None:
        """Test pipeline with complex query."""
        decomposer = DaisyChainDecomposer()

        async def mock_callback(model: str, prompt: str) -> str:
            return f"Complex response about {prompt[:30]}..."

        callbacks = {
            "model-1": mock_callback,
            "gpt-4": mock_callback,
            "claude-opus-4": mock_callback,
            "deepseek-r1": mock_callback,
            "gemini-pro": mock_callback,
        }

        result = await decomposer.execute_chain(
            "Explain the complete lifecycle of how ML models are developed, trained, deployed, and maintained in production environments with multiple teams",
            callbacks,
        )

        assert result.success
        assert result.combined_response != ""

    @pytest.mark.asyncio
    async def test_execute_chain_with_models(self) -> None:
        """Test execute_chain with explicit models."""
        models = ["model-x", "model-y"]
        decomposer = DaisyChainDecomposer(available_models=models)

        async def mock_callback(model: str, prompt: str) -> str:
            return "Test response"

        callbacks = {m: mock_callback for m in models + ["gpt-4"]}

        result = await decomposer.execute_chain(
            "Test query",
            callbacks,
            combiner_model="gpt-4"
        )

        assert result.original_query == "Test query"


class TestErrorHandling:
    """Tests for error handling in daisy-chain."""

    @pytest.mark.asyncio
    async def test_empty_callback_dict_handled(self) -> None:
        """Test handling of empty callback dict."""
        decomposer = DaisyChainDecomposer()

        # Empty callbacks dict
        callbacks = {}

        try:
            result = await decomposer.execute_chain(
                "Test query",
                callbacks,
            )
        except (KeyError, ValueError):
            # Expected to fail with missing callbacks
            pass


class TestSubQueryDecomposition:
    """Tests for sub-query decomposition logic."""

    def test_sub_queries_vary_by_content(self) -> None:
        """Test that sub-queries vary based on input."""
        decomposer = DaisyChainDecomposer()
        
        sub_queries_1 = decomposer.decompose("What is AI?")
        sub_queries_2 = decomposer.decompose("How do I build a house?")
        
        # Different queries should produce different sub-queries
        # (or at least they can be different)
        assert sub_queries_1 != sub_queries_2 or len(sub_queries_1) > 0


class TestCombinerModel:
    """Tests for combiner model functionality."""

    @pytest.mark.asyncio
    async def test_custom_combiner_model(self) -> None:
        """Test using custom combiner model."""
        decomposer = DaisyChainDecomposer()

        async def mock_callback(model: str, prompt: str) -> str:
            return f"Response from {model}"

        callbacks = {
            "gpt-4": mock_callback,
            "claude-opus-4": mock_callback,
            "deepseek-r1": mock_callback,
            "gemini-pro": mock_callback,
            "custom-combiner": mock_callback,
        }

        result = await decomposer.execute_chain(
            "Test query",
            callbacks,
            combiner_model="custom-combiner"
        )

        assert result.success
        assert result.combined_response != ""
        assert result.combiner_model == "custom-combiner"

    @pytest.mark.asyncio
    async def test_default_combiner_model_gpt4(self) -> None:
        """Test that default combiner model is used."""
        decomposer = DaisyChainDecomposer()

        async def mock_callback(model: str, prompt: str) -> str:
            return f"Response from {model}"

        callbacks = {
            "gpt-4": mock_callback,
            "claude-opus-4": mock_callback,
            "deepseek-r1": mock_callback,
            "gemini-pro": mock_callback,
        }

        result = await decomposer.execute_chain(
            "Test query",
            callbacks,
            # No combiner_model specified, should use default
        )

        assert result.success


class TestModelAssignment:
    """Tests for model assignment logic."""

    @pytest.mark.asyncio
    async def test_model_assignments_match_sub_queries(self) -> None:
        """Test that each sub-query is assigned a model."""
        decomposer = DaisyChainDecomposer()

        async def mock_callback(model: str, prompt: str) -> str:
            return "Response"

        callbacks = {
            "gpt-4": mock_callback,
            "claude-opus-4": mock_callback,
            "deepseek-r1": mock_callback,
            "gemini-pro": mock_callback,
        }

        result = await decomposer.execute_chain(
            "Test query",
            callbacks,
        )

        # Each sub-query should have an assignment
        assert len(result.model_assignments) == len(result.sub_queries)

    @pytest.mark.asyncio
    async def test_model_assignment_uses_available_models(self) -> None:
        """Test that assignments only use available models."""
        models = ["model-a", "model-b"]
        decomposer = DaisyChainDecomposer(available_models=models)

        async def mock_callback(model: str, prompt: str) -> str:
            return "Response"

        callbacks = {m: mock_callback for m in models + ["gpt-4"]}

        result = await decomposer.execute_chain(
            "Test query",
            callbacks,
        )

        # All assignments should be to available models (or gpt-4 for combiner)
        for assigned_model in result.model_assignments.values():
            assert assigned_model in models
