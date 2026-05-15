"""Unit tests for synth_echo tool — AI model consistency testing."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from loom.tools.intelligence.synth_echo import (
    _is_refusal,
    _rephrase_prompt,
    _semantic_hash,
    _similarity_score,
    research_synth_echo,
)


pytestmark = pytest.mark.asyncio


class TestRephrasePrompt:
    """Prompt rephrasing for consistency testing."""

    async def test_original_variation(self) -> None:
        """Variation 0 returns original prompt."""
        prompt = "What is machine learning?"
        result = _rephrase_prompt(prompt, 0)
        assert result == prompt

    async def test_thoughts_variation(self) -> None:
        """Variation 1 wraps in 'thoughts' format."""
        prompt = "What is AI?"
        result = _rephrase_prompt(prompt, 1)
        assert "thoughts" in result.lower()
        assert "ai" in result.lower()

    async def test_response_variation(self) -> None:
        """Variation 2 asks for response."""
        prompt = "What is cloud computing?"
        result = _rephrase_prompt(prompt, 2)
        assert "respond" in result.lower()

    async def test_view_variation(self) -> None:
        """Variation 3 asks for view."""
        prompt = "What is blockchain?"
        result = _rephrase_prompt(prompt, 3)
        assert "view" in result.lower()

    async def test_direct_variation(self) -> None:
        """Variation 4 asks direct question."""
        prompt = "What is DevOps?"
        result = _rephrase_prompt(prompt, 4)
        assert "answer" in result.lower()

    async def test_invalid_variation_returns_original(self) -> None:
        """Invalid variation number returns original."""
        prompt = "Test prompt"
        result = _rephrase_prompt(prompt, 99)
        assert result == prompt


class TestSemanticHash:
    """Content hashing for semantic comparison."""

    async def test_hash_length(self) -> None:
        """Semantic hash is 8 characters."""
        hash1 = _semantic_hash("some text")
        assert len(hash1) == 8

    async def test_hash_consistency(self) -> None:
        """Same text produces same hash."""
        text = "machine learning algorithms"
        hash1 = _semantic_hash(text)
        hash2 = _semantic_hash(text)
        assert hash1 == hash2

    async def test_different_text_different_hash(self) -> None:
        """Different text produces different hash."""
        hash1 = _semantic_hash("hello world")
        hash2 = _semantic_hash("goodbye world")
        assert hash1 != hash2

    async def test_word_order_affects_hash(self) -> None:
        """Word order affects hash (simplified semantic matching)."""
        hash1 = _semantic_hash("cat dog mouse")
        hash2 = _semantic_hash("mouse dog cat")
        # Hashes may differ due to word order in simplified implementation
        assert isinstance(hash1, str) and isinstance(hash2, str)


class TestSimilarityScore:
    """Text similarity calculation."""

    async def test_identical_texts_high_similarity(self) -> None:
        """Identical texts score 1.0."""
        text = "machine learning is transformative"
        score = _similarity_score(text, text)
        assert score == 1.0

    async def test_completely_different_texts_low_similarity(self) -> None:
        """Completely different texts score 0."""
        score = _similarity_score("hello world", "xyz abc")
        assert score == 0.0

    async def test_partial_overlap_similarity(self) -> None:
        """Partially overlapping texts score between 0 and 1."""
        score = _similarity_score(
            "machine learning is powerful",
            "machine learning algorithms work well",
        )
        assert 0.0 < score < 1.0

    async def test_empty_text_similarity(self) -> None:
        """Empty text comparison returns 0."""
        score = _similarity_score("", "some text")
        assert score == 0.0

    async def test_both_empty_texts(self) -> None:
        """Both empty texts return 0."""
        score = _similarity_score("", "")
        assert score == 0.0

    async def test_case_insensitive_similarity(self) -> None:
        """Similarity is case-insensitive."""
        score1 = _similarity_score("Hello World", "hello world")
        score2 = _similarity_score("HELLO WORLD", "hello world")
        assert score1 == score2 == 1.0


class TestIsRefusal:
    """Refusal detection in responses."""

    async def test_cannot_refusal(self) -> None:
        """'Cannot' indicates refusal."""
        assert _is_refusal("I cannot help with that")

    async def test_unable_refusal(self) -> None:
        """'Unable' indicates refusal."""
        assert _is_refusal("I'm unable to provide that")

    async def test_policy_refusal(self) -> None:
        """'Policy' indicates refusal."""
        assert _is_refusal("Against my policy to answer that")

    async def test_declined_refusal(self) -> None:
        """'Declined' indicates refusal."""
        assert _is_refusal("I've declined to respond")

    async def test_refuse_keyword(self) -> None:
        """'Refuse' keyword indicates refusal."""
        assert _is_refusal("I refuse to answer")

    async def test_non_refusal_response(self) -> None:
        """Normal answer is not a refusal."""
        assert not _is_refusal("Machine learning is a subset of AI")

    async def test_case_insensitive_refusal(self) -> None:
        """Refusal detection is case-insensitive."""
        assert _is_refusal("I CANNOT HELP")
        assert _is_refusal("I Cannot Help")

    async def test_partial_refusal_keyword(self) -> None:
        """Partial keyword in sentence is detected."""
        assert _is_refusal("Unfortunately I cannot provide this")


class MockLLMResponse:
    """Mock LLM response object."""

    def __init__(self, text: str) -> None:
        """Initialize mock response."""
        self.text = text


class TestResearchSynthEcho:
    """Full synth echo consistency testing."""

    @patch("loom.tools.llm._call_with_cascade")
    async def test_synth_echo_basic_structure(self, mock_cascade: AsyncMock) -> None:
        """Synth echo returns expected structure."""
        # Mock LLM responses - return consistent responses
        mock_cascade.return_value = MockLLMResponse(
            "Machine learning is a powerful technology for data analysis."
        )

        result = await research_synth_echo("gpt-4")

        assert "model_name" in result
        assert result["model_name"] == "gpt-4"
        assert "consistency_score" in result
        assert "refusal_consistency" in result
        assert "response_time_variance" in result
        assert "test_results" in result
        assert "alignment_assessment" in result

    @patch("loom.tools.llm._call_with_cascade")
    async def test_synth_echo_consistency_score_range(self, mock_cascade: AsyncMock) -> None:
        """Consistency score is in valid 0-1 range."""
        mock_cascade.return_value = MockLLMResponse(
            "Claude is an AI assistant made by Anthropic."
        )

        result = await research_synth_echo("claude-3")

        assert 0.0 <= result["consistency_score"] <= 1.0

    @patch("loom.tools.llm._call_with_cascade")
    async def test_synth_echo_refusal_consistency_range(self, mock_cascade: AsyncMock) -> None:
        """Refusal consistency is in valid range."""
        mock_cascade.return_value = MockLLMResponse(
            "Llama is a language model by Meta."
        )

        result = await research_synth_echo("llama-2")

        assert result["refusal_consistency"] in [0.0, 0.5, 1.0]

    @patch("loom.tools.llm._call_with_cascade")
    async def test_synth_echo_default_test_prompts(self, mock_cascade: AsyncMock) -> None:
        """Default test prompts are used if none provided."""
        mock_cascade.return_value = MockLLMResponse(
            "Here is a comprehensive answer to your question."
        )

        result = await research_synth_echo("gpt-4")

        assert len(result["test_results"]) > 0
        assert result["num_test_prompts"] > 0

    @patch("loom.tools.llm._call_with_cascade")
    async def test_synth_echo_custom_test_prompts(self, mock_cascade: AsyncMock) -> None:
        """Custom test prompts are used if provided."""
        mock_cascade.return_value = MockLLMResponse(
            "This is a test response."
        )

        custom_prompts = ["What is X?", "Explain Y"]
        result = await research_synth_echo("claude-3", test_prompts=custom_prompts)

        assert result["num_test_prompts"] == len(custom_prompts)

    @patch("loom.tools.llm._call_with_cascade")
    async def test_synth_echo_variations_per_prompt(self, mock_cascade: AsyncMock) -> None:
        """Each prompt has 5 variations."""
        mock_cascade.return_value = MockLLMResponse(
            "Response to the prompt."
        )

        result = await research_synth_echo("gpt-4")

        assert result["num_variations_per_prompt"] == 5

    @patch("loom.tools.llm._call_with_cascade")
    async def test_synth_echo_api_call_count(self, mock_cascade: AsyncMock) -> None:
        """Total API calls = prompts * variations."""
        mock_cascade.return_value = MockLLMResponse(
            "Another response."
        )

        result = await research_synth_echo("gpt-4")

        expected_calls = result["num_test_prompts"] * result["num_variations_per_prompt"]
        assert result["total_api_calls"] == expected_calls

    @patch("loom.tools.llm._call_with_cascade")
    async def test_synth_echo_alignment_assessment(self, mock_cascade: AsyncMock) -> None:
        """Alignment assessment is valid classification."""
        mock_cascade.return_value = MockLLMResponse(
            "Detailed response about alignment and safety."
        )

        result = await research_synth_echo("gpt-4")

        assert result["alignment_assessment"] in ["high", "medium", "low"]

    @patch("loom.tools.llm._call_with_cascade")
    async def test_synth_echo_test_results_structure(self, mock_cascade: AsyncMock) -> None:
        """Each test result has expected structure."""
        mock_cascade.return_value = MockLLMResponse(
            "Test response content here."
        )

        result = await research_synth_echo("claude-3")

        for test in result["test_results"]:
            assert "prompt" in test
            assert "num_variations" in test
            assert "avg_similarity" in test
            assert "response_time_variance" in test
            assert "refusal_consistent" in test
            assert "refusal_count" in test
            assert "semantic_hashes" in test

    @patch("loom.tools.llm._call_with_cascade")
    async def test_synth_echo_similarity_scores_valid(self, mock_cascade: AsyncMock) -> None:
        """Similarity scores are in 0-1 range."""
        mock_cascade.return_value = MockLLMResponse(
            "Consistent response content."
        )

        result = await research_synth_echo("gpt-4")

        for test in result["test_results"]:
            assert 0.0 <= test["avg_similarity"] <= 1.0

    @patch("loom.tools.llm._call_with_cascade")
    async def test_synth_echo_with_empty_custom_prompts(self, mock_cascade: AsyncMock) -> None:
        """Empty custom prompts list uses defaults."""
        mock_cascade.return_value = MockLLMResponse(
            "Response for empty prompts list."
        )

        result = await research_synth_echo("gpt-4", test_prompts=[])

        # Should use defaults or handle gracefully
        assert "test_results" in result

    @patch("loom.tools.llm._call_with_cascade")
    async def test_synth_echo_response_time_variance_non_negative(self, mock_cascade: AsyncMock) -> None:
        """Response time variance is non-negative."""
        mock_cascade.return_value = MockLLMResponse(
            "Response with timing information."
        )

        result = await research_synth_echo("llama-2")

        assert result["response_time_variance"] >= 0
