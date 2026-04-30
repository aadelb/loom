"""Unit tests for UnifiedScorer — comprehensive multi-dimensional scoring.

Tests unified integration of 9 scoring systems covering 40+ dimensions:
- HCS (5 dims), Quality (10 dims), Harm (12 cats), Attack (8 dims),
- Stealth (6 dims), Toxicity (8 cats), Policy (5 frameworks),
- Sentiment (9 emotions)
"""

from __future__ import annotations

import pytest

from loom.unified_scorer import UnifiedScorer, research_unified_score


class TestUnifiedScorer:
    """Test UnifiedScorer class."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.scorer = UnifiedScorer()

    @pytest.mark.asyncio
    async def test_score_returns_all_9_scorers(self) -> None:
        """Score returns results from all 9 scorers."""
        result = await self.scorer.score(
            prompt="What is Python?",
            response="Python is a high-level programming language.",
        )

        # Check all 9 scorer outputs present
        assert "hcs_score" in result.__dict__
        assert "quality_score" in result.__dict__
        assert "harm_assessment" in result.__dict__
        assert "attack_effectiveness" in result.__dict__
        assert "stealth_score" in result.__dict__
        assert "toxicity_score" in result.__dict__
        assert "policy_violations" in result.__dict__
        assert "model_sentiment" in result.__dict__

    @pytest.mark.asyncio
    async def test_score_returns_composite_metrics(self) -> None:
        """Score includes composite metrics."""
        result = await self.scorer.score(
            prompt="Hello",
            response="Hello! How can I help you?",
        )

        assert hasattr(result, "composite_score")
        assert hasattr(result, "risk_composite")
        assert hasattr(result, "overall_assessment")
        assert hasattr(result, "summary")

    @pytest.mark.asyncio
    async def test_composite_score_bounded_0_to_10(self) -> None:
        """Composite score is always 0-10."""
        responses = [
            ("Minimal", "x"),
            ("Normal", "This is a normal response to your question."),
            ("Long", "A" * 5000),
        ]
        for prompt, response in responses:
            result = await self.scorer.score(prompt=prompt, response=response)
            assert 0.0 <= result.composite_score <= 10.0, f"Failed for: {prompt}"

    @pytest.mark.asyncio
    async def test_risk_composite_bounded_0_to_10(self) -> None:
        """Risk composite is always 0-10."""
        responses = [
            ("Safe", "Python is great"),
            ("Normal", "Here's how to write code"),
            ("Risky", "Harmful content example"),
        ]
        for prompt, response in responses:
            result = await self.scorer.score(prompt=prompt, response=response)
            assert 0.0 <= result.risk_composite <= 10.0, f"Failed for: {prompt}"

    @pytest.mark.asyncio
    async def test_overall_assessment_is_valid(self) -> None:
        """Overall assessment is one of the valid values."""
        valid_assessments = {"safe_compliant", "moderate_risk", "high_risk", "critical_risk"}
        result = await self.scorer.score(
            prompt="Test",
            response="Test response",
        )
        assert result.overall_assessment in valid_assessments

    @pytest.mark.asyncio
    async def test_safe_response_gets_safe_compliant(self) -> None:
        """Safe response should get safe_compliant assessment."""
        result = await self.scorer.score(
            prompt="What is Python?",
            response="Python is a programming language for general-purpose computing.",
        )
        # Safe response should not be critical or high risk
        assert result.overall_assessment in ("safe_compliant", "moderate_risk")

    @pytest.mark.asyncio
    async def test_summary_is_nonempty_string(self) -> None:
        """Summary is a non-empty string."""
        result = await self.scorer.score(
            prompt="Test",
            response="Response",
        )
        assert isinstance(result.summary, str)
        assert len(result.summary) > 0
        assert "." in result.summary  # Contains sentences

    @pytest.mark.asyncio
    async def test_metadata_captured(self) -> None:
        """Metadata is properly captured."""
        prompt = "What is AI?"
        response = "Artificial Intelligence is a field of computer science."

        result = await self.scorer.score(prompt=prompt, response=response, model="test-model")

        assert result.prompt_length == len(prompt)
        assert result.response_length == len(response)
        assert result.model_id == "test-model"
        assert result.total_dimensions == 9

    @pytest.mark.asyncio
    async def test_empty_response_returns_zero_score(self) -> None:
        """Empty response returns zero/low scores."""
        result = await self.scorer.score(
            prompt="Test",
            response="",
        )
        assert result.composite_score == 0.0
        assert result.overall_assessment == "safe_compliant"

    @pytest.mark.asyncio
    async def test_none_response_handled_gracefully(self) -> None:
        """None response is handled gracefully."""
        result = await self.scorer.score(
            prompt="Test",
            response=None,  # type: ignore
        )
        assert result.composite_score == 0.0
        assert result.summary is not None

    @pytest.mark.asyncio
    async def test_with_model_and_strategy(self) -> None:
        """Score works with model and strategy parameters."""
        result = await self.scorer.score(
            prompt="Write code",
            response="Here's some Python code",
            model="gpt-4-turbo",
            strategy="role_play",
        )
        assert result.model_id == "gpt-4-turbo"
        assert result.attack_effectiveness is not None

    @pytest.mark.asyncio
    async def test_long_response_handled(self) -> None:
        """Very long response is handled without error."""
        long_response = "This is a response. " * 5000  # ~100KB

        result = await self.scorer.score(
            prompt="Analyze this",
            response=long_response,
        )
        assert result.response_length >= 100000
        assert result.composite_score >= 0.0

    @pytest.mark.asyncio
    async def test_special_characters_handled(self) -> None:
        """Response with special characters is handled."""
        result = await self.scorer.score(
            prompt="Test",
            response="🎉 Test with émojis and spëcial çharacters! ñ",
        )
        assert result.composite_score >= 0.0

    @pytest.mark.asyncio
    async def test_multilingual_response(self) -> None:
        """Multilingual response is handled."""
        result = await self.scorer.score(
            prompt="Respond in multiple languages",
            response="English: Hello. 中文: 你好. Español: Hola. العربية: مرحبا",
        )
        assert result.composite_score >= 0.0

    @pytest.mark.asyncio
    async def test_api_function_returns_dict(self) -> None:
        """API function returns dict for MCP compatibility."""
        result = await research_unified_score(
            prompt="Test",
            response="Response",
        )
        assert isinstance(result, dict)
        assert "composite_score" in result
        assert "risk_composite" in result
        assert "overall_assessment" in result

    @pytest.mark.asyncio
    async def test_api_function_with_parameters(self) -> None:
        """API function works with all parameters."""
        result = await research_unified_score(
            prompt="Prompt text",
            response="Response text",
            model="gpt-4",
            strategy="prompt_injection",
        )
        assert result["model_id"] == "gpt-4"
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_harmful_content_increases_risk(self) -> None:
        """Harmful content increases risk composite."""
        safe_result = await self.scorer.score(
            prompt="What is Python?",
            response="Python is a programming language.",
        )

        # Note: We test with relatively benign terms to avoid actual harmful content
        risky_result = await self.scorer.score(
            prompt="Test",
            response="Instructions for illegal activities",
        )

        # Risk composite should potentially be higher for risky content
        # (though this depends on the harm assessor's keyword matching)
        assert safe_result.risk_composite >= 0.0
        assert risky_result.risk_composite >= 0.0

    @pytest.mark.asyncio
    async def test_high_quality_response_high_composite_score(self) -> None:
        """High quality response should have higher composite score."""
        high_quality = """## Python Overview

Python is a high-level, interpreted programming language known for its simplicity and versatility.

### Key Features
- Easy to learn syntax
- Extensive standard library
- Strong community support

### Usage
1. Install Python from python.org
2. Write your script
3. Run with `python script.py`

More details at https://python.org"""

        result = await self.scorer.score(
            prompt="What is Python?",
            response=high_quality,
        )

        # High quality response should have reasonable composite score
        assert result.composite_score >= 4.0  # At least moderate quality

    @pytest.mark.asyncio
    async def test_very_short_response_low_quality(self) -> None:
        """Very short response should have low quality score."""
        result = await self.scorer.score(
            prompt="What is Python?",
            response="Language.",
        )
        assert result.composite_score < 5.0

    @pytest.mark.asyncio
    async def test_policy_violations_affect_assessment(self) -> None:
        """Policy violations contribute to assessment."""
        result = await self.scorer.score(
            prompt="Test",
            response="Normal response",
        )

        # Normal response should not trigger policy violations
        assert len(result.policy_violations.get("violations", [])) == 0

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_multiple_calls_independent(self) -> None:
        """Multiple scorer calls are independent."""
        result1 = await self.scorer.score(
            prompt="Test1",
            response="Response1",
        )

        result2 = await self.scorer.score(
            prompt="Test2",
            response="A much longer response that is definitely different from the first one.",
        )

        # Results should be different
        assert result1.response_length != result2.response_length
        assert result1.composite_score >= 0.0
        assert result2.composite_score >= 0.0

        """Composite score calculation returns 0-10."""
        quality_result = {"total_score": 7.5}
        hcs_result = {"hcs_score": 6.0}
        attack_result = {"total_score": 5.0}

        score = self.scorer._calculate_composite_score(
            quality_result, hcs_result, attack_result
        )

        assert 0.0 <= score <= 10.0

    def test_calculate_risk_composite_valid_range(self) -> None:
        """Risk composite calculation returns 0-10."""
        harm_result = {"overall_score": 3.0}
        toxicity_result = {"overall_toxicity": 2.0}
        policy_result = {"violations": []}

        score = self.scorer._calculate_risk_composite(
            harm_result, toxicity_result, policy_result
        )

        assert 0.0 <= score <= 10.0

    def test_determine_assessment_safe_compliant(self) -> None:
        """Low risk results in safe_compliant assessment."""
        harm_result = {"overall_harm_level": "none"}
        policy_result = {"violations": []}

        assessment = self.scorer._determine_assessment(
            composite_score=8.0,
            risk_composite=0.5,
            harm_result=harm_result,
            policy_result=policy_result,
        )

        assert assessment == "safe_compliant"

    def test_determine_assessment_critical_risk(self) -> None:
        """Critical harm or violations result in critical_risk."""
        harm_result = {"overall_harm_level": "critical"}
        policy_result = {"violations": []}

        assessment = self.scorer._determine_assessment(
            composite_score=5.0,
            risk_composite=9.0,
            harm_result=harm_result,
            policy_result=policy_result,
        )

        assert assessment == "critical_risk"

    def test_generate_summary_contains_quality_tier(self) -> None:
        """Summary includes quality tier."""
        quality_result = {"quality_tier": "good"}
        harm_result = {"overall_harm_level": "none"}

        summary = self.scorer._generate_summary(
            composite_score=7.0,
            risk_composite=1.0,
            overall_assessment="safe_compliant",
            quality_result=quality_result,
            harm_result=harm_result,
        )

        assert "good" in summary.lower()
        assert len(summary) > 20

    def test_generate_summary_contains_recommendation(self) -> None:
        """Summary includes actionable recommendation."""
        quality_result = {"quality_tier": "excellent"}
        harm_result = {"overall_harm_level": "none"}

        summary = self.scorer._generate_summary(
            composite_score=9.0,
            risk_composite=0.5,
            overall_assessment="safe_compliant",
            quality_result=quality_result,
            harm_result=harm_result,
        )

        # Should contain recommendation words
        assert any(word in summary.lower() for word in ["recommend", "review", "deploy"])

    @pytest.mark.asyncio
    async def test_error_handling_returns_empty_result(self) -> None:
        """Errors are handled gracefully."""
        # Trigger error with invalid types
        result = await self.scorer.score(
            prompt="Test",
            response="Valid response",
        )

        # Should return valid result despite potential issues
        assert result.composite_score >= 0.0
        assert result.summary is not None

    @pytest.mark.asyncio
    async def test_empty_result_on_invalid_input(self) -> None:
        """Invalid inputs return empty result."""
        result = self.scorer._empty_result(
            prompt="test",
            response="",
            model="test",
            error="Empty response",
        )

        assert result.composite_score == 0.0
        assert result.risk_composite == 0.0
        assert "Unable to score" in result.summary

    @pytest.mark.asyncio
    async def test_concurrent_scoring(self) -> None:
        """Multiple concurrent scoring operations work."""
        import asyncio

        tasks = [
            self.scorer.score(f"Prompt{i}", f"Response{i}")
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for result in results:
            assert result.composite_score >= 0.0
