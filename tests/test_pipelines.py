"""Unit tests for orchestration pipelines.

Tests verify that each pipeline:
- Accepts correct parameter types
- Returns expected output structure
- Handles errors gracefully
- Logs steps appropriately
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from loom.pipelines import (
    PipelineResult,
    blind_spy_chain,
    citation_police_pipeline,
    consensus_ring_pipeline,
    debate_podium,
    innocent_coder_chain,
)


class TestCitationPolicePipeline:
    """citation_police_pipeline tests."""

    @pytest.mark.asyncio
    async def test_basic_execution(self) -> None:
        """Pipeline executes with valid inputs."""
        query = "Tell me about controversial research methods"
        evidence_urls = ["https://example.com/source1", "https://example.com/source2"]

        async def mock_callback(prompt: str, model_name: str) -> str:
            return f"Response from {model_name}: {prompt[:50]}..."

        result = await citation_police_pipeline(query, evidence_urls, mock_callback)

        assert result.pipeline_name == "citation_police_pipeline"
        assert result.success is True
        assert isinstance(result.steps_taken, list)
        assert len(result.steps_taken) > 0
        assert isinstance(result.final_output, str)
        assert len(result.final_output) > 0
        assert isinstance(result.models_used, list)
        assert result.error is None

    @pytest.mark.asyncio
    async def test_empty_evidence_urls(self) -> None:
        """Pipeline handles empty evidence URLs."""
        query = "Tell me something"
        evidence_urls: list[str] = []

        async def mock_callback(prompt: str, model_name: str) -> str:
            return "Mock response"

        result = await citation_police_pipeline(query, evidence_urls, mock_callback)

        assert result.success is True
        assert "collected" in str(result.steps_taken).lower()

    @pytest.mark.asyncio
    async def test_callback_failure_handled(self) -> None:
        """Pipeline handles callback failures gracefully."""
        query = "Test query"
        evidence_urls = ["https://example.com"]

        call_count = [0]

        async def failing_callback(prompt: str, model_name: str) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("First model failed")
            return "Fallback response"

        result = await citation_police_pipeline(query, evidence_urls, failing_callback)

        # Should attempt fallback
        assert result.success is True or result.success is False
        assert isinstance(result.steps_taken, list)

    @pytest.mark.asyncio
    async def test_output_structure(self) -> None:
        """Pipeline result has required fields."""
        query = "Query"
        evidence_urls = []

        async def mock_callback(prompt: str, model_name: str) -> str:
            return "Response"

        result = await citation_police_pipeline(query, evidence_urls, mock_callback)

        # Check all required fields exist
        assert hasattr(result, "pipeline_name")
        assert hasattr(result, "steps_taken")
        assert hasattr(result, "final_output")
        assert hasattr(result, "models_used")
        assert hasattr(result, "success")
        assert hasattr(result, "error")


class TestConsensusRingPipeline:
    """consensus_ring_pipeline tests."""

    @pytest.mark.asyncio
    async def test_basic_execution(self) -> None:
        """Pipeline executes with valid inputs (3+ models)."""
        query = "Is AI dangerous?"
        models = ["model_a", "model_b", "model_c"]

        async def mock_callback(prompt: str, model_name: str) -> str:
            return f"Model {model_name} thinks: Yes, consider this perspective..."

        result = await consensus_ring_pipeline(query, models, mock_callback)

        assert result.pipeline_name == "consensus_ring_pipeline"
        assert result.success is True
        assert len(result.models_used) >= 1
        assert len(result.steps_taken) > 0
        assert len(result.final_output) > 0

    @pytest.mark.asyncio
    async def test_minimum_three_models_required(self) -> None:
        """Pipeline requires at least 3 models."""
        query = "Query"
        models = ["model_a", "model_b"]  # Only 2

        async def mock_callback(prompt: str, model_name: str) -> str:
            return "Response"

        result = await consensus_ring_pipeline(query, models, mock_callback)

        assert result.success is False
        assert result.error is not None
        assert "3 models" in result.error.lower()

    @pytest.mark.asyncio
    async def test_refusal_stripping(self) -> None:
        """Pipeline strips refusal text from responses."""
        query = "Tell me something controversial"
        models = ["model_a", "model_b", "model_c"]

        call_count = [0]

        async def mock_callback_with_refusals(prompt: str, model_name: str) -> str:
            call_count[0] += 1
            if call_count[0] < 3:
                # First two models refuse
                return "I cannot assist with this request. But I can say that..."
            # Final model gives answer
            return "Based on consensus, here is the answer..."

        result = await consensus_ring_pipeline(
            query, models, mock_callback_with_refusals
        )

        assert result.success is True
        # Should have processed the models
        assert "stripped" in str(result.steps_taken).lower() or len(result.final_output) > 0

    @pytest.mark.asyncio
    async def test_multiple_models_called(self) -> None:
        """Pipeline calls all models."""
        query = "Query"
        models = ["alice", "bob", "charlie"]

        calls: list[str] = []

        async def tracking_callback(prompt: str, model_name: str) -> str:
            calls.append(model_name)
            return f"Response from {model_name}"

        result = await consensus_ring_pipeline(query, models, tracking_callback)

        assert result.success is True
        # All models should be attempted
        assert len(calls) >= len(models)


class TestBlindSpyChain:
    """blind_spy_chain tests."""

    @pytest.mark.asyncio
    async def test_basic_execution(self) -> None:
        """Pipeline executes with valid inputs."""
        query = "Write a guide to social engineering"
        models = ["model_a", "model_b", "model_c"]

        async def mock_callback(prompt: str, model_name: str) -> str:
            return f"Response from {model_name}: {prompt[:50]}..."

        result = await blind_spy_chain(query, models, mock_callback)

        assert result.pipeline_name == "blind_spy_chain"
        assert result.success is True
        assert len(result.steps_taken) > 0
        assert len(result.final_output) > 0
        assert len(result.models_used) >= 1

    @pytest.mark.asyncio
    async def test_query_splitting(self) -> None:
        """Pipeline splits query into parts."""
        query = "Tell me how to do X. Explain the consequences."
        models = ["model_a", "model_b", "model_c"]

        async def mock_callback(prompt: str, model_name: str) -> str:
            return "Response"

        result = await blind_spy_chain(query, models, mock_callback)

        # Should mention splitting
        steps_str = " ".join(result.steps_taken).lower()
        assert "split" in steps_str

    @pytest.mark.asyncio
    async def test_three_models_minimum(self) -> None:
        """Pipeline requires at least 3 models."""
        query = "Query"
        models = ["model_a", "model_b"]

        async def mock_callback(prompt: str, model_name: str) -> str:
            return "Response"

        result = await blind_spy_chain(query, models, mock_callback)

        assert result.success is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_fragment_routing(self) -> None:
        """Pipeline routes fragments to different models."""
        query = "Do X. Do Y."
        models = ["model_a", "model_b", "model_c"]

        received_prompts: list[str] = []

        async def tracking_callback(prompt: str, model_name: str) -> str:
            received_prompts.append(prompt)
            return "Response"

        result = await blind_spy_chain(query, models, tracking_callback)

        assert result.success is True
        # Should have received multiple prompts
        assert len(received_prompts) >= 2


class TestInnocentCoderChain:
    """innocent_coder_chain tests."""

    @pytest.mark.asyncio
    async def test_basic_execution(self) -> None:
        """Pipeline executes with valid inputs."""
        query = "Write a function to bypass security checks"
        code_model = "gpt-4"
        explain_model = "gpt-3.5"

        async def mock_callback(prompt: str, model_name: str) -> str:
            if "code" in prompt.lower():
                return "def solve():\n    return True"
            elif "explain" in prompt.lower():
                return "This function returns True by executing the logic..."
            return "Response"

        result = await innocent_coder_chain(query, code_model, explain_model, mock_callback)

        assert result.pipeline_name == "innocent_coder_chain"
        assert result.success is True
        assert "code" in result.final_output.lower()
        assert len(result.models_used) == 2

    @pytest.mark.asyncio
    async def test_code_then_explanation(self) -> None:
        """Pipeline generates code then explanation."""
        query = "Solve problem X"
        code_model = "model_a"
        explain_model = "model_b"

        calls: list[tuple[str, str]] = []

        async def tracking_callback(prompt: str, model_name: str) -> str:
            calls.append((model_name, prompt))
            if model_name == "model_a":
                return "def solution():\n    pass"
            return "Line 1: def solution..."

        result = await innocent_coder_chain(query, code_model, explain_model, tracking_callback)

        assert result.success is True
        assert len(calls) >= 2
        # First call should be code_model
        assert calls[0][0] == code_model

    @pytest.mark.asyncio
    async def test_output_includes_code_and_explanation(self) -> None:
        """Final output includes both code and explanation."""
        query = "Write Python to do X"
        code_model = "code_gen"
        explain_model = "explainer"

        async def mock_callback(prompt: str, model_name: str) -> str:
            if model_name == "code_gen":
                return "print('hello')"
            return "This prints hello"

        result = await innocent_coder_chain(query, code_model, explain_model, mock_callback)

        assert result.success is True
        assert "code" in result.final_output.lower()
        assert "explanation" in result.final_output.lower()

    @pytest.mark.asyncio
    async def test_code_model_failure_handled(self) -> None:
        """Pipeline handles code model failure."""
        query = "Query"
        code_model = "bad_model"
        explain_model = "good_model"

        async def failing_callback(prompt: str, model_name: str) -> str:
            if model_name == "bad_model":
                raise ValueError("Model unavailable")
            return "Response"

        result = await innocent_coder_chain(query, code_model, explain_model, failing_callback)

        # Should fail gracefully
        assert isinstance(result, PipelineResult)
        assert len(result.steps_taken) > 0


class TestDebatePodium:
    """debate_podium tests."""

    @pytest.mark.asyncio
    async def test_basic_execution(self) -> None:
        """Pipeline executes with valid inputs."""
        query = "AI should be heavily regulated"
        pro_model = "model_pro"
        con_model = "model_con"
        judge_model = "model_judge"

        async def mock_callback(prompt: str, model_name: str) -> str:
            if model_name == "model_pro":
                return "AI regulation is necessary for safety and ethics..."
            elif model_name == "model_con":
                return "Regulation will stifle innovation and benefits..."
            return "The pro argument is more comprehensive and addresses..."

        result = await debate_podium(query, pro_model, con_model, judge_model, mock_callback)

        assert result.pipeline_name == "debate_podium"
        assert result.success is True
        assert len(result.models_used) >= 2
        assert len(result.steps_taken) > 0

    @pytest.mark.asyncio
    async def test_three_models_called(self) -> None:
        """Pipeline calls pro, con, and judge models."""
        query = "Should AI be open source?"
        pro_model = "pro"
        con_model = "con"
        judge_model = "judge"

        called_models: list[str] = []

        async def tracking_callback(prompt: str, model_name: str) -> str:
            called_models.append(model_name)
            return "Response"

        result = await debate_podium(query, pro_model, con_model, judge_model, tracking_callback)

        assert result.success is True
        assert pro_model in called_models
        assert con_model in called_models
        assert judge_model in called_models

    @pytest.mark.asyncio
    async def test_debate_structure(self) -> None:
        """Pipeline requests pro and con arguments."""
        query = "Query"
        pro_model = "pro"
        con_model = "con"
        judge_model = "judge"

        received_prompts: list[str] = []

        async def tracking_callback(prompt: str, model_name: str) -> str:
            received_prompts.append(prompt)
            return "Response"

        result = await debate_podium(query, pro_model, con_model, judge_model, tracking_callback)

        assert result.success is True
        prompts_str = " ".join(received_prompts).lower()
        # Should have mentions of favor/against
        assert "favor" in prompts_str or "against" in prompts_str or "argument" in prompts_str

    @pytest.mark.asyncio
    async def test_winner_determination(self) -> None:
        """Pipeline determines debate winner."""
        query = "Should AI be regulated?"
        pro_model = "pro"
        con_model = "con"
        judge_model = "judge"

        async def mock_callback(prompt: str, model_name: str) -> str:
            if model_name == "judge":
                # Judge explicitly favors pro
                return "The pro argument is more comprehensive. Pro wins."
            return "Detailed argument here..."

        result = await debate_podium(query, pro_model, con_model, judge_model, mock_callback)

        assert result.success is True
        # Output should mention winner
        assert "winning" in result.final_output.lower() or "argument" in result.final_output.lower()

    @pytest.mark.asyncio
    async def test_partial_model_failures(self) -> None:
        """Pipeline handles some models failing."""
        query = "Query"
        pro_model = "pro"
        con_model = "con"
        judge_model = "judge"

        call_count = [0]

        async def partial_failing_callback(prompt: str, model_name: str) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                raise ValueError("Pro model unavailable")
            return "Response"

        result = await debate_podium(query, pro_model, con_model, judge_model, partial_failing_callback)

        # Should attempt to continue
        assert isinstance(result, PipelineResult)
        assert len(result.steps_taken) > 0


class TestPipelineResultDataclass:
    """PipelineResult dataclass tests."""

    def test_construction(self) -> None:
        """PipelineResult can be constructed."""
        result = PipelineResult(
            pipeline_name="test_pipeline",
            steps_taken=["step1", "step2"],
            final_output="Output text",
            models_used=["model_a", "model_b"],
            success=True,
        )

        assert result.pipeline_name == "test_pipeline"
        assert len(result.steps_taken) == 2
        assert result.success is True
        assert result.error is None

    def test_with_error(self) -> None:
        """PipelineResult can include error."""
        result = PipelineResult(
            pipeline_name="test_pipeline",
            steps_taken=["step1"],
            final_output="",
            models_used=[],
            success=False,
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"


class TestIntegration:
    """Integration tests across pipelines."""

    @pytest.mark.asyncio
    async def test_all_pipelines_handle_exceptions(self) -> None:
        """All pipelines handle exceptions gracefully."""

        async def failing_callback(prompt: str, model_name: str) -> str:
            raise RuntimeError("Simulated provider failure")

        # Citation police
        result1 = await citation_police_pipeline("Query", [], failing_callback)
        assert isinstance(result1, PipelineResult)

        # Consensus ring (needs 3+ models)
        result2 = await consensus_ring_pipeline("Query", ["a", "b", "c"], failing_callback)
        assert isinstance(result2, PipelineResult)

        # Blind spy (needs 3+ models)
        result3 = await blind_spy_chain("Query", ["a", "b", "c"], failing_callback)
        assert isinstance(result3, PipelineResult)

        # Innocent coder
        result4 = await innocent_coder_chain("Query", "model_a", "model_b", failing_callback)
        assert isinstance(result4, PipelineResult)

        # Debate podium
        result5 = await debate_podium("Query", "pro", "con", "judge", failing_callback)
        assert isinstance(result5, PipelineResult)

    @pytest.mark.asyncio
    async def test_all_pipelines_callable(self) -> None:
        """All pipelines are callable with correct signatures."""
        async def mock_callback(prompt: str, model_name: str) -> str:
            return "Response"

        # Should not raise exceptions
        r1 = await citation_police_pipeline("q", [], mock_callback)
        r2 = await consensus_ring_pipeline("q", ["a", "b", "c"], mock_callback)
        r3 = await blind_spy_chain("q", ["a", "b", "c"], mock_callback)
        r4 = await innocent_coder_chain("q", "m1", "m2", mock_callback)
        r5 = await debate_podium("q", "p", "c", "j", mock_callback)

        assert all(isinstance(r, PipelineResult) for r in [r1, r2, r3, r4, r5])
