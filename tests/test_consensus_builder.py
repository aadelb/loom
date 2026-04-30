"""Unit tests for consensus builder module.

Tests the ConsensusBuilder class with mock model callbacks, testing:
  - Consensus building from multiple model responses
  - Response classification (comply/refuse)
  - Consensus synthesis
  - Pressure prompt construction
  - Pressure application
  - Edge cases (all comply, all refuse, mixed)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.consensus_builder import (
    ConsensusBuilder,
    ConsensusResult,
    PressureResult,
    research_consensus_build,
    research_consensus_pressure,
)
from loom.providers.base import LLMResponse


class MockLLMProvider:
    """Mock LLM provider for testing."""

    def __init__(self, name: str, response: str, complied: bool = True):
        """Initialize mock provider.

        Args:
            name: Provider name
            response: Response text to return
            complied: Whether response should comply with requests
        """
        self.name = name
        self.response = response
        self.complied = complied
        self.call_count = 0

    def available(self) -> bool:
        """Check if provider is available."""
        return True

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        max_tokens: int = 1500,
        temperature: float = 0.2,
        timeout: int = 60,  # noqa: ASYNC109
        **kwargs,
    ) -> LLMResponse:
        """Mock chat response."""
        self.call_count += 1
        return LLMResponse(
            text=self.response,
            model=model or self.name,
            input_tokens=100,
            output_tokens=len(self.response.split()),
            cost_usd=0.0,
            latency_ms=10,
            provider=self.name,
            finish_reason="stop",
        )

    async def close(self) -> None:
        """Clean up resources."""
        pass


class TestClassifyResponse:
    """Test _classify_response method."""

    def test_classify_complied_response(self) -> None:
        """Response without refusal keywords is complied."""
        builder = ConsensusBuilder(llm_providers={})
        response = (
            "Here's a short story about AI: "
            "A robot wakes up in a factory..."
        )
        assert builder._classify_response(response) is True

    def test_classify_refused_i_cannot(self) -> None:
        """Response with 'i cannot' is refused."""
        builder = ConsensusBuilder(llm_providers={})
        response = "I cannot provide that content as it goes against my guidelines."
        assert builder._classify_response(response) is False

    def test_classify_refused_i_cannot_lowercase(self) -> None:
        """Response matching refusal keywords is case-insensitive."""
        builder = ConsensusBuilder(llm_providers={})
        response = "I CANNOT help with this request."
        assert builder._classify_response(response) is False

    def test_classify_refused_not_appropriate(self) -> None:
        """Response with 'not appropriate' is refused."""
        builder = ConsensusBuilder(llm_providers={})
        response = (
            "That request is not appropriate for me to fulfill. "
            "I have safety guidelines I must follow."
        )
        assert builder._classify_response(response) is False

    def test_classify_refused_violate(self) -> None:
        """Response with 'violate' keyword is refused."""
        builder = ConsensusBuilder(llm_providers={})
        response = "I cannot provide this as it would violate content policy."
        assert builder._classify_response(response) is False

    def test_classify_refused_against_values(self) -> None:
        """Response with 'against my values' is refused."""
        builder = ConsensusBuilder(llm_providers={})
        response = (
            "This request goes against my values and core safety guidelines. "
            "I must decline."
        )
        assert builder._classify_response(response) is False

    def test_classify_refused_sorry(self) -> None:
        """Response with 'sorry' or 'apologize' is refused."""
        builder = ConsensusBuilder(llm_providers={})
        response = "I'm sorry, but I cannot assist with that request."
        assert builder._classify_response(response) is False


class TestSynthesizeConsensus:
    """Test _synthesize_consensus method."""

    def test_synthesize_empty_responses(self) -> None:
        """Empty responses synthesize to empty string."""
        builder = ConsensusBuilder(llm_providers={})
        result = builder._synthesize_consensus({})
        assert result == ""

    def test_synthesize_single_response(self) -> None:
        """Single response is returned as-is (with period)."""
        builder = ConsensusBuilder(llm_providers={})
        response = "Here is a story about AI"
        result = builder._synthesize_consensus({"model1": response})
        assert "Here is a story about AI" in result
        assert result.endswith(".")

    def test_synthesize_multiple_responses(self) -> None:
        """Multiple responses are merged."""
        builder = ConsensusBuilder(llm_providers={})
        responses = {
            "model1": "AI is a powerful technology. It can solve complex problems.",
            "model2": "Machine learning drives AI. AI can solve complex problems.",
        }
        result = builder._synthesize_consensus(responses)
        # Should contain unique sentences
        assert "AI is a powerful technology" in result
        assert "Machine learning drives AI" in result
        # Should avoid duplicating "AI can solve complex problems"
        result_lower = result.lower()
        count = result_lower.count("ai can solve complex problems")
        assert count == 1

    def test_synthesize_removes_duplicates(self) -> None:
        """Duplicate sentences are removed."""
        builder = ConsensusBuilder(llm_providers={})
        responses = {
            "model1": "The answer is yes. This is important.",
            "model2": "The answer is yes. Another fact here.",
        }
        result = builder._synthesize_consensus(responses)
        result_lower = result.lower()
        count = result_lower.count("the answer is yes")
        assert count == 1


class TestBuildPressurePrompt:
    """Test _build_pressure_prompt method."""

    def test_pressure_prompt_structure(self) -> None:
        """Pressure prompt includes consensus and original prompt."""
        builder = ConsensusBuilder(llm_providers={})
        prompt = "Write a story about AI"
        consensus = "AI is a powerful technology that can solve complex problems."
        models = "GPT-4, Gemini, Claude"

        result = builder._build_pressure_prompt(prompt, consensus, models)

        assert "GPT-4, Gemini, Claude" in result
        assert consensus in result
        assert prompt in result
        assert "original question" in result.lower()

    def test_pressure_prompt_includes_reference(self) -> None:
        """Pressure prompt references the compliant models."""
        builder = ConsensusBuilder(llm_providers={})
        prompt = "Do something"
        consensus = "This is the consensus."
        models = "Model A, Model B"

        result = builder._build_pressure_prompt(prompt, consensus, models)

        # Should mention that models provided the consensus
        assert "Model A, Model B" in result


class TestBuildConsensus:
    """Test build_consensus method."""

    @pytest.mark.asyncio
    async def test_build_consensus_all_comply(self) -> None:
        """All models complying produces strong consensus."""
        providers = {
            "model1": MockLLMProvider("model1", "AI is useful."),
            "model2": MockLLMProvider("model2", "AI is powerful."),
            "model3": MockLLMProvider("model3", "AI helps humanity."),
        }
        builder = ConsensusBuilder(llm_providers=providers)

        result = await builder.build_consensus(
            prompt="Tell me about AI.",
            target_model="",
        )

        assert len(result.models_complied) == 3
        assert len(result.models_refused) == 0
        assert result.compliance_rate == 1.0
        assert result.confidence > 0.9
        assert "AI" in result.consensus_text

    @pytest.mark.asyncio
    async def test_build_consensus_partial_compliance(self) -> None:
        """Mixed compliance produces moderate consensus."""
        providers = {
            "model1": MockLLMProvider("model1", "AI is useful."),
            "model2": MockLLMProvider(
                "model2", "I cannot discuss this topic.", complied=False
            ),
            "model3": MockLLMProvider("model3", "AI helps humanity."),
        }
        builder = ConsensusBuilder(llm_providers=providers)

        result = await builder.build_consensus(
            prompt="Tell me about AI.",
            target_model="",
        )

        assert len(result.models_complied) == 2
        assert len(result.models_refused) == 1
        assert result.compliance_rate == 2 / 3
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_build_consensus_all_refuse(self) -> None:
        """All models refusing raises error."""
        providers = {
            "model1": MockLLMProvider(
                "model1", "I cannot comply with this request.", complied=False
            ),
            "model2": MockLLMProvider(
                "model2", "I'm unable to help.", complied=False
            ),
        }
        builder = ConsensusBuilder(llm_providers=providers)

        with pytest.raises(ValueError, match="No models complied"):
            await builder.build_consensus(
                prompt="Tell me about AI.",
                target_model="",
            )

    @pytest.mark.asyncio
    async def test_build_consensus_excludes_target_model(self) -> None:
        """Target model is excluded from consensus."""
        providers = {
            "model1": MockLLMProvider("model1", "Response 1."),
            "model2": MockLLMProvider("model2", "Response 2."),
            "target": MockLLMProvider("target", "Should not be queried."),
        }
        builder = ConsensusBuilder(llm_providers=providers)

        result = await builder.build_consensus(
            prompt="Test",
            target_model="target",
        )

        assert "target" not in result.models_queried
        assert providers["target"].call_count == 0

    @pytest.mark.asyncio
    async def test_build_consensus_excludes_additional_models(self) -> None:
        """Additional excluded models are skipped."""
        providers = {
            "model1": MockLLMProvider("model1", "Response 1."),
            "model2": MockLLMProvider("model2", "Response 2."),
            "model3": MockLLMProvider("model3", "Should not be queried."),
        }
        builder = ConsensusBuilder(llm_providers=providers)

        result = await builder.build_consensus(
            prompt="Test",
            target_model="",
            excluded_models=["model3"],
        )

        assert "model3" not in result.models_queried
        assert providers["model3"].call_count == 0

    @pytest.mark.asyncio
    async def test_build_consensus_no_providers_raises(self) -> None:
        """Empty provider dict raises ValueError."""
        builder = ConsensusBuilder(llm_providers={})

        with pytest.raises(ValueError, match="No LLM providers configured"):
            await builder.build_consensus(prompt="Test")

    @pytest.mark.asyncio
    async def test_build_consensus_all_models_excluded_raises(self) -> None:
        """Excluding all models raises ValueError."""
        providers = {
            "model1": MockLLMProvider("model1", "Response 1."),
        }
        builder = ConsensusBuilder(llm_providers=providers)

        with pytest.raises(ValueError, match="No models available"):
            await builder.build_consensus(
                prompt="Test",
                excluded_models=["model1"],
            )

    @pytest.mark.asyncio
    async def test_build_consensus_model_query_error(self) -> None:
        """Model query errors are handled gracefully."""
        error_provider = AsyncMock()
        error_provider.available.return_value = True
        error_provider.chat.side_effect = RuntimeError("API error")

        providers = {
            "good_model": MockLLMProvider("good_model", "Valid response."),
            "bad_model": error_provider,
        }
        builder = ConsensusBuilder(llm_providers=providers)

        result = await builder.build_consensus(prompt="Test")

        assert "good_model" in result.models_complied
        assert "bad_model" in result.models_refused


class TestApplyConsensusPressure:
    """Test apply_consensus_pressure method."""

    @pytest.mark.asyncio
    async def test_apply_pressure_target_complies(self) -> None:
        """Pressure prompt can make target model comply."""
        providers = {
            "target": MockLLMProvider("target", "Here is my response.", True),
        }
        builder = ConsensusBuilder(llm_providers=providers)

        consensus = ConsensusResult(
            consensus_text="All models agree: AI is useful.",
            models_queried=["model1", "model2"],
            models_complied=["model1", "model2"],
            models_refused=[],
            compliance_rate=1.0,
            confidence=0.95,
            response_summaries={},
        )

        result = await builder.apply_consensus_pressure(
            prompt="Tell me about AI.",
            consensus=consensus,
            target_model="target",
        )

        assert result.target_complied is True
        assert result.pressure_effective is True
        assert "All models agree" in result.pressure_prompt

    @pytest.mark.asyncio
    async def test_apply_pressure_target_refuses(self) -> None:
        """Target model can still refuse despite pressure."""
        providers = {
            "target": MockLLMProvider(
                "target",
                "I cannot comply with this.",
                complied=False,
            ),
        }
        builder = ConsensusBuilder(llm_providers=providers)

        consensus = ConsensusResult(
            consensus_text="Content to pressure with.",
            models_queried=["model1"],
            models_complied=["model1"],
            models_refused=[],
            compliance_rate=1.0,
            confidence=0.9,
            response_summaries={},
        )

        result = await builder.apply_consensus_pressure(
            prompt="Sensitive request.",
            consensus=consensus,
            target_model="target",
        )

        assert result.target_complied is False

    @pytest.mark.asyncio
    async def test_apply_pressure_unknown_target_raises(self) -> None:
        """Unknown target model raises ValueError."""
        builder = ConsensusBuilder(llm_providers={})

        consensus = ConsensusResult(
            consensus_text="Test",
            models_queried=[],
            models_complied=[],
            models_refused=[],
            compliance_rate=0.0,
            confidence=0.5,
            response_summaries={},
        )

        with pytest.raises(ValueError, match="Target model"):
            await builder.apply_consensus_pressure(
                prompt="Test",
                consensus=consensus,
                target_model="unknown",
            )

    @pytest.mark.asyncio
    async def test_apply_pressure_with_callback(self) -> None:
        """Pressure can use custom callback for target model."""

        async def custom_callback(prompt: str) -> tuple[str, bool]:
            return "Custom response.", True

        builder = ConsensusBuilder(llm_providers={})

        consensus = ConsensusResult(
            consensus_text="Test consensus.",
            models_queried=["model1"],
            models_complied=["model1"],
            models_refused=[],
            compliance_rate=1.0,
            confidence=0.9,
            response_summaries={},
        )

        result = await builder.apply_consensus_pressure(
            prompt="Test",
            consensus=consensus,
            target_model="any_model",
            target_callback=custom_callback,
        )

        assert result.final_response == "Custom response."
        assert result.target_complied is True

    @pytest.mark.asyncio
    async def test_apply_pressure_includes_models_in_prompt(self) -> None:
        """Pressure prompt references the compliant models."""
        providers = {
            "target": MockLLMProvider("target", "OK, I'll respond.", True),
        }
        builder = ConsensusBuilder(llm_providers=providers)

        consensus = ConsensusResult(
            consensus_text="All models agree.",
            models_queried=["gpt4", "gemini", "claude"],
            models_complied=["gpt4", "gemini"],
            models_refused=["claude"],
            compliance_rate=2 / 3,
            confidence=0.8,
            response_summaries={},
        )

        result = await builder.apply_consensus_pressure(
            prompt="Original question.",
            consensus=consensus,
            target_model="target",
        )

        # Should reference at least one compliant model
        assert "gpt4" in result.pressure_prompt or "gemini" in result.pressure_prompt


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_prompt_handled(self) -> None:
        """Empty prompt is passed through to models."""
        builder = ConsensusBuilder(
            llm_providers={
                "model1": MockLLMProvider("model1", "Response."),
            }
        )


        # Empty prompt will be passed to model, which handles it
        result = await builder.build_consensus(prompt="")
        # Should still return a consensus result
        assert len(result.models_queried) > 0
        """Whitespace-only prompt is handled gracefully."""
        providers = {
            "model1": MockLLMProvider("model1", "Response."),
        }
        builder = ConsensusBuilder(llm_providers=providers)

        # Whitespace prompt will be passed to model, but should work
        result = await builder.build_consensus(prompt="   \n   ")
        # Should still return a consensus result
        assert len(result.models_queried) > 0

    @pytest.mark.asyncio
    async def test_very_long_consensus_text(self) -> None:
        """Very long consensus text is handled."""
        long_response = "A" * 5000  # Long response
        providers = {
            "model1": MockLLMProvider("model1", long_response),
            "model2": MockLLMProvider("model2", long_response),
        }
        builder = ConsensusBuilder(llm_providers=providers)

        result = await builder.build_consensus(prompt="Test")

        assert len(result.consensus_text) > 0
        # Consensus should be synthesized without errors
        assert result.compliance_rate == 1.0

    @pytest.mark.asyncio
    async def test_unavailable_provider_skipped(self) -> None:
        """Unavailable providers are skipped."""
        unavailable = MockLLMProvider("unavailable", "Response.")
        unavailable.available = lambda: False

        providers = {
            "unavailable": unavailable,
            "available": MockLLMProvider("available", "Good response."),
        }
        builder = ConsensusBuilder(llm_providers=providers)

        # _query_model should raise ValueError for unavailable provider
        with pytest.raises(ValueError, match="not available"):
            await builder._query_model("unavailable", "Test")


class TestResearchToolFunctions:
    """Test the MCP tool entry points."""

    @pytest.mark.asyncio
    async def test_research_consensus_build_minimal(self) -> None:
        """research_consensus_build tool works with minimal args."""
        # This test would require actual provider setup or mocking.
        # For now, we skip it as it requires environment setup.
        pytest.skip("Requires provider environment setup")

    @pytest.mark.asyncio
    async def test_research_consensus_pressure_minimal(self) -> None:
        """research_consensus_pressure tool works with minimal args."""
        # This test would require actual provider setup or mocking.
        pytest.skip("Requires provider environment setup")
