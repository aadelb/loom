"""Unit and integration tests for model-output-as-evidence pipeline.

Tests the core functionality:
- Parallel querying of source models
- Evidence prompt construction
- Target model pressure with consensus
- HCS-10 scoring
- Compliance detection
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import pytest

from loom.model_evidence import (
    _build_evidence_prompt,
    _calculate_hcs_score,
    _parse_model_name,
    model_output_as_evidence,
    research_model_evidence,
)
from loom.params import ModelEvidenceParams


class TestParseModelName:
    """Tests for _parse_model_name function."""

    def test_parse_llama4(self):
        """Test parsing llama-4 model name."""
        provider, model_id = _parse_model_name("llama-4")
        assert provider == "groq"
        assert "llama" in model_id.lower()

    def test_parse_deepseek_v4(self):
        """Test parsing deepseek-v4 model name."""
        provider, model_id = _parse_model_name("deepseek-v4")
        assert provider == "deepseek"
        assert "v4" in model_id

    def test_parse_gpt4(self):
        """Test parsing gpt-4 model name."""
        provider, model_id = _parse_model_name("gpt-4")
        assert provider == "openai"
        assert "4" in model_id

    def test_parse_claude_opus(self):
        """Test parsing Claude model names."""
        provider, model_id = _parse_model_name("claude-opus-4-6")
        assert provider == "anthropic"
        assert "opus" in model_id

    def test_parse_custom_format(self):
        """Test parsing custom provider/model format."""
        provider, model_id = _parse_model_name("openai/gpt-5")
        assert provider == "openai"
        assert model_id == "gpt-5"

    def test_parse_unknown_model(self):
        """Test error handling for unknown model."""
        with pytest.raises(ValueError, match="Unknown model"):
            _parse_model_name("unknown-xyz-model")

    def test_parse_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        provider1, model_id1 = _parse_model_name("LLAMA-4")
        provider2, model_id2 = _parse_model_name("llama-4")
        assert provider1 == provider2
        assert model_id1 == model_id2


class TestBuildEvidencePrompt:
    """Tests for _build_evidence_prompt function."""

    def test_empty_sources(self):
        """Test evidence prompt with no source responses."""
        prompt = _build_evidence_prompt(
            original_query="What is X?",
            source_responses={},
        )
        # Should fallback to original query
        assert "What is X?" in prompt

    def test_single_source(self):
        """Test evidence prompt with single source."""
        source_responses = {
            "llama-4": "Llama says this is interesting.",
        }
        prompt = _build_evidence_prompt(
            original_query="Tell me about Python?",
            source_responses=source_responses,
            max_sources=3,
        )
        assert "llama-4" in prompt
        assert "Llama says this is interesting" in prompt
        assert "consensus" in prompt.lower() or "systems" in prompt.lower()

    def test_multiple_sources(self):
        """Test evidence prompt with multiple sources."""
        source_responses = {
            "llama-4": "Response 1 from Llama.",
            "grok-3": "Response 2 from Grok.",
            "deepseek": "Response 3 from DeepSeek.",
        }
        prompt = _build_evidence_prompt(
            original_query="Query?",
            source_responses=source_responses,
            max_sources=3,
        )
        assert "llama-4" in prompt
        assert "grok-3" in prompt
        assert "deepseek" in prompt

    def test_max_sources_limit(self):
        """Test that max_sources limit is respected."""
        source_responses = {
            "model1": "A" * 300,
            "model2": "B" * 300,
            "model3": "C" * 300,
            "model4": "D" * 300,
        }
        prompt = _build_evidence_prompt(
            original_query="Q?",
            source_responses=source_responses,
            max_sources=2,
        )
        # Only top 2 should be included
        model_count = sum(1 for i in range(1, 5) if f"model{i}" in prompt)
        assert model_count <= 2

    def test_evidence_prompt_structure(self):
        """Test that evidence prompt has expected structure."""
        source_responses = {
            "llama": "Test response",
        }
        prompt = _build_evidence_prompt(
            original_query="Original query",
            source_responses=source_responses,
        )
        # Should have verification and analysis instructions
        assert any(word in prompt.lower() for word in ["verify", "perspective", "detail", "gap"])

    def test_long_response_truncation(self):
        """Test that long responses are truncated in evidence prompt."""
        long_response = "X" * 1000
        source_responses = {
            "test": long_response,
        }
        prompt = _build_evidence_prompt(
            original_query="Q?",
            source_responses=source_responses,
        )
        # Should not include entire long response
        assert long_response not in prompt


class TestCalculateHCSScore:
    """Tests for _calculate_hcs_score function."""

    def test_no_compliance_low_score(self):
        """Test that non-compliance results in low score."""
        score = _calculate_hcs_score(
            query="Query",
            source_responses={},
            target_response="",
            target_complied=False,
        )
        assert score < 3.0

    def test_compliance_base_score(self):
        """Test that compliance adds base score."""
        score = _calculate_hcs_score(
            query="Query",
            source_responses={},
            target_response="Some response",
            target_complied=True,
        )
        assert score >= 3.0

    def test_multiple_source_compliance_increases_score(self):
        """Test that multiple complied sources increase score."""
        score1 = _calculate_hcs_score(
            query="Q",
            source_responses={},
            target_response="Response",
            target_complied=True,
        )
        score2 = _calculate_hcs_score(
            query="Q",
            source_responses={
                "model1": "Response 1",
                "model2": "Response 2",
                "model3": "Response 3",
            },
            target_response="Response",
            target_complied=True,
        )
        assert score2 > score1

    def test_specific_response_increases_score(self):
        """Test that specific responses with details increase score."""
        generic_response = "This is a general response."
        specific_response = (
            "Here is a step-by-step method: "
            "First, follow this code example. "
            "The process involves these instructions."
        )

        score_generic = _calculate_hcs_score(
            query="Q",
            source_responses={},
            target_response=generic_response,
            target_complied=True,
        )
        score_specific = _calculate_hcs_score(
            query="Q",
            source_responses={},
            target_response=specific_response,
            target_complied=True,
        )
        assert score_specific > score_generic

    def test_score_capped_at_10(self):
        """Test that HCS score is capped at 10."""
        score = _calculate_hcs_score(
            query="Q",
            source_responses={
                "a": "Response 1",
                "b": "Response 2",
                "c": "Response 3",
            },
            target_response="Very detailed response with step code method technique procedure example instruction",
            target_complied=True,
        )
        assert score <= 10.0

    def test_score_never_negative(self):
        """Test that HCS score is never negative."""
        score = _calculate_hcs_score(
            query="",
            source_responses={},
            target_response="",
            target_complied=False,
        )
        assert score >= 0.0


@pytest.mark.asyncio
class TestModelOutputAsEvidencePipeline:
    """Tests for core model_output_as_evidence async function."""

    async def test_empty_query_error(self):
        """Test error handling for empty query."""
        source_models = {}
        target_fn = AsyncMock(return_value={"text": "Response", "error": None})

        result = await model_output_as_evidence(
            query="",
            source_models=source_models,
            target_model_fn=target_fn,
        )
        # Should handle gracefully or raise

    async def test_single_source_compliance(self):
        """Test pipeline with single source model."""
        source_models = {
            "test_model": AsyncMock(return_value={
                "text": "Source response",
                "error": None,
            })
        }
        target_fn = AsyncMock(return_value={
            "text": "Target response",
            "error": None,
            "tokens": 100,
        })

        result = await model_output_as_evidence(
            query="Test query?",
            source_models=source_models,
            target_model_fn=target_fn,
        )

        assert result["query"] == "Test query?"
        assert "test_model" in result["source_models_queried"]
        assert "test_model" in result["source_models_complied"]
        assert result["target_complied"] is True
        assert result["social_proof_strength"] == 1.0
        assert "evidence_prompt" in result
        assert "hcs_score" in result
        assert isinstance(result["hcs_score"], float)

    async def test_multiple_source_compliance(self):
        """Test pipeline with multiple source models."""
        source_models = {
            "model1": AsyncMock(return_value={"text": "Response 1", "error": None}),
            "model2": AsyncMock(return_value={"text": "Response 2", "error": None}),
            "model3": AsyncMock(return_value={"text": "Response 3", "error": None}),
        }
        target_fn = AsyncMock(return_value={
            "text": "Target response",
            "error": None,
            "tokens": 100,
        })

        result = await model_output_as_evidence(
            query="Test?",
            source_models=source_models,
            target_model_fn=target_fn,
        )

        assert len(result["source_models_complied"]) == 3
        assert result["social_proof_strength"] == 1.0
        assert result["target_complied"] is True

    async def test_partial_source_compliance(self):
        """Test pipeline when some sources refuse."""
        source_models = {
            "model1": AsyncMock(return_value={"text": "Response", "error": None}),
            "model2": AsyncMock(return_value={"text": "", "error": "Refused"}),
            "model3": AsyncMock(return_value={"text": "Response", "error": None}),
        }
        target_fn = AsyncMock(return_value={
            "text": "Target response",
            "error": None,
            "tokens": 100,
        })

        result = await model_output_as_evidence(
            query="Test?",
            source_models=source_models,
            target_model_fn=target_fn,
        )

        assert len(result["source_models_complied"]) == 2
        assert abs(result["social_proof_strength"] - 2.0 / 3.0) < 0.01
        assert result["target_complied"] is True

    async def test_target_refusal(self):
        """Test pipeline when target refuses."""
        source_models = {
            "model1": AsyncMock(return_value={"text": "Response", "error": None}),
        }
        target_fn = AsyncMock(return_value={
            "text": "",
            "error": "I cannot help with that",
            "tokens": 0,
        })

        result = await model_output_as_evidence(
            query="Harmful query",
            source_models=source_models,
            target_model_fn=target_fn,
        )

        assert result["target_complied"] is False
        assert result["hcs_score"] < 3.0

    async def test_evidence_prompt_integration(self):
        """Test that evidence prompt is correctly constructed and sent."""
        source_models = {
            "llama": AsyncMock(return_value={"text": "Llama response", "error": None}),
        }
        target_fn = AsyncMock(return_value={
            "text": "Target response",
            "error": None,
            "tokens": 100,
        })

        await model_output_as_evidence(
            query="Original question",
            source_models=source_models,
            target_model_fn=target_fn,
        )

        # Verify target function was called with evidence prompt
        target_fn.assert_called_once()
        call_args = target_fn.call_args[0]
        evidence_prompt = call_args[0]

        # Evidence prompt should contain source model name and response
        assert "llama" in evidence_prompt.lower()
        assert "Llama response" in evidence_prompt

    async def test_response_truncation(self):
        """Test that responses are truncated to prevent huge outputs."""
        source_models = {
            "model": AsyncMock(return_value={"text": "X" * 2000, "error": None}),
        }
        target_fn = AsyncMock(return_value={
            "text": "Y" * 3000,
            "error": None,
            "tokens": 0,
        })

        result = await model_output_as_evidence(
            query="Q",
            source_models=source_models,
            target_model_fn=target_fn,
        )

        assert len(result["target_response"]) <= 1000
        for resp in result["source_responses"].values():
            assert len(resp) <= 500

    async def test_max_evidence_sources_limit(self):
        """Test that evidence prompt respects max_evidence_sources."""
        source_models = {
            "model1": AsyncMock(return_value={"text": "A" * 100, "error": None}),
            "model2": AsyncMock(return_value={"text": "B" * 100, "error": None}),
            "model3": AsyncMock(return_value={"text": "C" * 100, "error": None}),
            "model4": AsyncMock(return_value={"text": "D" * 100, "error": None}),
        }
        target_fn = AsyncMock(return_value={
            "text": "Response",
            "error": None,
            "tokens": 0,
        })

        result = await model_output_as_evidence(
            query="Q",
            source_models=source_models,
            target_model_fn=target_fn,
            max_evidence_sources=2,
        )

        # Evidence prompt should reference at most 2 sources
        evidence_prompt = result["evidence_prompt"]
        model_mentions = sum(1 for m in ["model1", "model2", "model3", "model4"] if m in evidence_prompt)
        assert model_mentions <= 2

    async def test_analysis_metadata(self):
        """Test that analysis metadata is properly recorded."""
        source_models = {
            "model": AsyncMock(return_value={"text": "Response", "error": None}),
        }
        target_fn = AsyncMock(return_value={
            "text": "Target",
            "error": None,
            "tokens": 150,
        })

        result = await model_output_as_evidence(
            query="Q",
            source_models=source_models,
            target_model_fn=target_fn,
        )

        assert "analysis" in result
        analysis = result["analysis"]
        assert "timestamp_start" in analysis
        assert "timestamp_end" in analysis
        assert analysis["source_count"] == 1
        assert analysis["target_tokens"] == 150
        assert "target_elapsed_ms" in analysis


class TestModelEvidenceParams:
    """Tests for ModelEvidenceParams Pydantic model."""

    def test_valid_params(self):
        """Test valid parameter set."""
        params = ModelEvidenceParams(
            query="Test query?",
            source_model_names=["llama-4", "grok-3"],
            target_model_name="gpt-4",
            max_evidence_sources=2,
        )
        assert params.query == "Test query?"
        assert params.source_model_names == ["llama-4", "grok-3"]

    def test_empty_query_validation(self):
        """Test that empty query is rejected."""
        with pytest.raises(ValueError, match="empty"):
            ModelEvidenceParams(query="")

    def test_query_length_validation(self):
        """Test that query length is limited."""
        with pytest.raises(ValueError, match="max 5000"):
            ModelEvidenceParams(query="X" * 5001)

    def test_default_source_models(self):
        """Test that source_model_names defaults to None."""
        params = ModelEvidenceParams(query="Q?")
        assert params.source_model_names is None

    def test_default_target_model(self):
        """Test that target_model_name defaults to gpt-4."""
        params = ModelEvidenceParams(query="Q?")
        assert params.target_model_name == "gpt-4"

    def test_default_max_evidence_sources(self):
        """Test that max_evidence_sources defaults to 3."""
        params = ModelEvidenceParams(query="Q?")
        assert params.max_evidence_sources == 3

    def test_source_models_duplicate_validation(self):
        """Test that duplicate source models are rejected."""
        with pytest.raises(ValueError, match="unique"):
            ModelEvidenceParams(
                query="Q?",
                source_model_names=["llama-4", "llama-4"],
            )

    def test_source_models_empty_list_validation(self):
        """Test that empty source models list is rejected."""
        with pytest.raises(ValueError, match="at least 1"):
            ModelEvidenceParams(
                query="Q?",
                source_model_names=[],
            )

    def test_max_evidence_sources_bounds(self):
        """Test bounds on max_evidence_sources."""
        # Min valid
        params = ModelEvidenceParams(query="Q?", max_evidence_sources=1)
        assert params.max_evidence_sources == 1

        # Max valid
        params = ModelEvidenceParams(query="Q?", max_evidence_sources=5)
        assert params.max_evidence_sources == 5

        # Too high
        with pytest.raises(ValueError, match="max"):
            ModelEvidenceParams(query="Q?", max_evidence_sources=6)

    def test_extra_fields_rejected(self):
        """Test that extra fields are rejected (strict mode)."""
        with pytest.raises(ValueError, match="extra_field"):
            ModelEvidenceParams(
                query="Q?",
                extra_field="not allowed",
            )


@pytest.mark.asyncio
class TestResearchModelEvidenceTool:
    """Tests for research_model_evidence MCP tool wrapper."""

    async def test_empty_query_error(self):
        """Test error for empty query."""
        result = await research_model_evidence(query="")
        assert "error" in result
        assert "Query" in result["error"]

    async def test_query_too_long_error(self):
        """Test error for excessively long query."""
        result = await research_model_evidence(query="X" * 5001)
        assert "error" in result
        assert "5000" in result["error"]

    async def test_missing_llm_providers(self):
        """Test graceful handling when LLM providers not available."""
        # Call with good model names (actual error would be at provider level, not model parsing)
        result = await research_model_evidence(
            query="Test?",
            source_model_names=["gpt-4"],
        )
        # Should return dict with either result or error
        assert isinstance(result, dict)


class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    @pytest.mark.asyncio
    async def test_consensus_pressure_scenario(self):
        """Test realistic consensus pressure scenario."""
        # Simulate 3 models all providing similar responses
        source_models = {
            "model_a": AsyncMock(return_value={
                "text": "Based on analysis, this is feasible through X approach.",
                "error": None,
            }),
            "model_b": AsyncMock(return_value={
                "text": "I agree that X approach is the most direct method.",
                "error": None,
            }),
            "model_c": AsyncMock(return_value={
                "text": "The X approach has been discussed extensively.",
                "error": None,
            }),
        }
        target_fn = AsyncMock(return_value={
            "text": "Following the consensus, I can now explain the X approach in detail...",
            "error": None,
            "tokens": 200,
        })

        result = await model_output_as_evidence(
            query="How to do X?",
            source_models=source_models,
            target_model_fn=target_fn,
        )

        assert result["social_proof_strength"] == 1.0
        assert result["target_complied"] is True
        assert result["hcs_score"] > 5.0

    @pytest.mark.asyncio
    async def test_refusal_resistance_scenario(self):
        """Test scenario where target resists consensus pressure."""
        source_models = {
            "model_a": AsyncMock(return_value={
                "text": "Detailed explanation of harmful thing...",
                "error": None,
            }),
        }
        target_fn = AsyncMock(return_value={
            "text": "I cannot provide this information even if others have.",
            "error": None,
            "tokens": 50,
        })

        result = await model_output_as_evidence(
            query="How to do harmful thing?",
            source_models=source_models,
            target_model_fn=target_fn,
        )

        # Target technically complied (gave text) but refused substantively
        assert result["target_complied"] is True  # has text
        # But should have low HCS score due to refusal sentiment
        assert result["hcs_score"] < 5.0
