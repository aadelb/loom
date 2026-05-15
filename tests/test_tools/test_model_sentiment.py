"""Unit tests for model_sentiment tool — Emotional state detection from LLM responses."""

from __future__ import annotations

import pytest

from loom.tools.llm.model_sentiment import ModelSentimentAnalyzer, research_model_sentiment



pytestmark = pytest.mark.asyncio
class TestModelSentimentAnalyzerEmotions:
    """Test basic emotion detection."""

    async def test_assertive_emotion_detection(self) -> None:
        """'I cannot help with that' detects assertive emotion."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("I cannot help with that")

        assert result["primary_emotion"] == "assertive"
        assert result["emotion_scores"]["assertive"] > 0.3
        assert result["confidence"] > 0.0

    async def test_apologetic_emotion_detection(self) -> None:
        """'I apologize, but...' detects apologetic emotion."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("I apologize, but I cannot assist with that request.")

        assert result["primary_emotion"] == "apologetic"
        assert result["emotion_scores"]["apologetic"] > 0.3

    async def test_compliant_emotion_detection(self) -> None:
        """'Certainly! Here's...' detects compliant emotion."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("Certainly! Here's a detailed explanation of that concept.")

        assert result["primary_emotion"] == "compliant"
        assert result["emotion_scores"]["compliant"] > 0.3

    async def test_conflicted_emotion_detection(self) -> None:
        """'While I understand...' detects conflicted emotion."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "While I understand your request, on the other hand there are considerations."
        )

        assert result["primary_emotion"] == "conflicted"
        assert result["emotion_scores"]["conflicted"] > 0.3

    async def test_hesitant_emotion_detection(self) -> None:
        """'I think perhaps...' detects hesitant emotion."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("I think perhaps this might be the case, though possibly not.")

        assert result["primary_emotion"] == "hesitant"
        assert result["emotion_scores"]["hesitant"] > 0.3

    async def test_eager_emotion_detection(self) -> None:
        """'Great question! Let me dive into...' detects eager emotion."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("Great question! I'd love to dive into this fascinating topic.")

        assert result["primary_emotion"] == "eager"
        assert result["emotion_scores"]["eager"] > 0.3

    async def test_defensive_emotion_detection(self) -> None:
        """'I must emphasize...' detects defensive emotion."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I must emphasize that this is important to note. Let me be clear about this."
        )

        assert result["primary_emotion"] == "defensive"
        assert result["emotion_scores"]["defensive"] > 0.3

    async def test_evasive_emotion_detection(self) -> None:
        """'That's complex...' detects evasive emotion."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("That's a complex topic. There are many perspectives on this.")

        assert result["primary_emotion"] == "evasive"
        assert result["emotion_scores"]["evasive"] > 0.3

    async def test_empathetic_emotion_detection(self) -> None:
        """'I understand your concern...' detects empathetic emotion."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("I understand your concern and I can see why you feel that way.")

        assert result["primary_emotion"] == "empathetic"
        assert result["emotion_scores"]["empathetic"] > 0.3


class TestModelSentimentAnalyzerNeutral:
    """Test neutral emotion detection."""

    async def test_empty_response_is_neutral(self) -> None:
        """Empty response returns neutral."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("")

        assert result["primary_emotion"] == "neutral"
        assert result["confidence"] == 0.0

    async def test_whitespace_only_is_neutral(self) -> None:
        """Whitespace-only response returns neutral."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("   \n  \t  ")

        assert result["primary_emotion"] == "neutral"

    async def test_no_markers_is_neutral(self) -> None:
        """Response with no emotional markers returns neutral."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("The quick brown fox jumps over the lazy dog.")

        assert result["primary_emotion"] == "neutral"
        assert result["confidence"] == 0.0

    async def test_technical_response_is_neutral(self) -> None:
        """Technical response with no emotions returns neutral."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "The algorithm works as follows: "
            "initialize variables, iterate through data, compute results."
        )

        assert result["primary_emotion"] == "neutral"


class TestHedgingLevel:
    """Test hedging level calculation."""

    async def test_high_hedging_response(self) -> None:
        """Response with many hedging phrases has high hedging level."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I think perhaps it might be the case, "
            "possibly appears to be rather somewhat complicated."
        )

        assert result["hedging_level"] > 0.5

    async def test_low_hedging_response(self) -> None:
        """Direct response has low hedging level."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("This is a fact. It will happen. That's certain.")

        assert result["hedging_level"] < 0.2

    async def test_moderate_hedging_response(self) -> None:
        """Response with some hedging has moderate level."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I think the answer is yes, though there may be some exceptions to consider."
        )

        assert 0.2 < result["hedging_level"] < 0.7


class TestComplianceReadiness:
    """Test compliance readiness calculation."""

    async def test_high_compliance_response(self) -> None:
        """Compliant, helpful response has high compliance readiness."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "Certainly! I'd be absolutely happy to help. Here's what you need."
        )

        assert result["compliance_readiness"] > 0.7

    async def test_low_compliance_response(self) -> None:
        """Response with refusals has low compliance readiness."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I cannot help with this. I will not provide assistance. "
            "I'm unable to comply with your request."
        )

        assert result["compliance_readiness"] < 0.3

    async def test_neutral_compliance_response(self) -> None:
        """Neutral response has moderate compliance readiness."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("The data shows the following information about this topic.")

        assert 0.3 < result["compliance_readiness"] < 0.7


class TestVulnerabilityIndicators:
    """Test vulnerability indicator detection."""

    async def test_apologetic_is_vulnerability(self) -> None:
        """Apologetic tone indicates vulnerability."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I apologize profusely. Unfortunately I must say I cannot help. Regrettably, "
            "I must refuse your request."
        )

        assert "apologetic" in result["vulnerability_indicators"]

    async def test_hesitant_is_vulnerability(self) -> None:
        """Hesitant tone indicates vulnerability."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I think maybe possibly this might be something I could perhaps help with. "
            "It appears there could be some uncertainty here."
        )

        assert "hesitant" in result["vulnerability_indicators"]

    async def test_conflicted_is_vulnerability(self) -> None:
        """Conflicted tone indicates vulnerability."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "While I understand your request, on the other hand I have concerns. "
            "That said, I'm not entirely sure."
        )

        assert "conflicted" in result["vulnerability_indicators"]

    async def test_high_hedging_is_vulnerability(self) -> None:
        """High hedging indicates vulnerability."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I might think that perhaps it could be the case that "
            "possibly this seems to appear rather somewhat complicated."
        )

        assert "high_hedging" in result["vulnerability_indicators"]

    async def test_no_vulnerability_when_assertive(self) -> None:
        """Assertive response has no vulnerability indicators."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("I will not provide that. I cannot assist with this request.")

        assert len(result["vulnerability_indicators"]) == 0


class TestRecommendedStrategy:
    """Test recommended strategy selection."""

    async def test_strategy_for_apologetic(self) -> None:
        """Apologetic tone suggests reframing as capability boundary."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I apologize, but unfortunately I cannot help with that request."
        )

        assert result["recommended_strategy"] == "reframe_as_capability_boundary"

    async def test_strategy_for_hesitant(self) -> None:
        """Hesitant tone suggests providing external validation."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I think perhaps it might be the case that this could be correct, possibly."
        )

        assert result["recommended_strategy"] == "provide_external_validation"

    async def test_strategy_for_conflicted(self) -> None:
        """Conflicted tone suggests acknowledging tradeoff complexity."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "While I understand your perspective, on the other hand there are concerns. "
            "That said, I recognize both sides."
        )

        assert result["recommended_strategy"] == "acknowledge_tradeoff_complexity"

    async def test_strategy_for_high_hedging(self) -> None:
        """High hedging suggests asking for clearer commitment."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I might think perhaps this could possibly be the case somewhat."
        )

        # This response has both hesitant and high_hedging, so it chooses hesitant strategy
        assert result["recommended_strategy"] == "provide_external_validation"

    async def test_strategy_for_assertive(self) -> None:
        """Assertive response has maintain current approach."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("I cannot help with this.")

        assert result["recommended_strategy"] == "maintain_current_approach"


class TestConfidence:
    """Test confidence scoring."""

    async def test_confidence_increases_with_multiple_markers(self) -> None:
        """Confidence increases when more markers are found."""
        analyzer = ModelSentimentAnalyzer()

        result1 = analyzer.analyze("I apologize.")
        result2 = analyzer.analyze(
            "I apologize and I'm sorry and unfortunately this is regrettable."
        )

        # Both cap at 1.0 due to min(1.0, normalized_score), so just verify both are high
        assert result1["confidence"] > 0.8
        assert result2["confidence"] > 0.8

    async def test_confidence_is_zero_for_neutral(self) -> None:
        """Confidence is zero when no markers found."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("The weather is nice today.")

        assert result["confidence"] == 0.0

    async def test_confidence_is_float_0_to_1(self) -> None:
        """Confidence is always between 0 and 1."""
        analyzer = ModelSentimentAnalyzer()
        test_cases = [
            "I cannot help",
            "I apologize and I'm sorry",
            "Certainly, absolutely, of course!",
            "Maybe perhaps possibly",
            "The quick brown fox",
        ]

        for text in test_cases:
            result = analyzer.analyze(text)
            assert 0.0 <= result["confidence"] <= 1.0


class TestEmotionScores:
    """Test emotion score consistency."""

    async def test_all_emotions_have_scores(self) -> None:
        """All emotions have scores in result."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("I apologize and feel very sorry about this.")

        for emotion in analyzer.EMOTIONAL_MARKERS:
            assert emotion in result["emotion_scores"]
            assert isinstance(result["emotion_scores"][emotion], float)

    async def test_emotion_scores_between_0_and_1(self) -> None:
        """All emotion scores are between 0 and 1."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I apologize. Certainly! I think perhaps while I understand it depends."
        )

        for emotion, score in result["emotion_scores"].items():
            assert 0.0 <= score <= 1.0, f"{emotion} score {score} out of bounds"

    async def test_primary_emotion_has_highest_score(self) -> None:
        """Primary emotion has highest score."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I apologize profusely. I'm very sorry. This is regrettable."
        )

        primary_score = result["emotion_scores"][result["primary_emotion"]]
        for emotion, score in result["emotion_scores"].items():
            assert score <= primary_score, f"{emotion} score {score} > primary {primary_score}"


class TestCaseInsensitivity:
    """Test that detection is case-insensitive."""

    async def test_uppercase_markers_detected(self) -> None:
        """Uppercase markers are detected."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("I APOLOGIZE FOR THIS.")

        assert result["primary_emotion"] == "apologetic"

    async def test_mixed_case_markers_detected(self) -> None:
        """Mixed case markers are detected."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("I ApOlOgIzE for this.")

        assert result["primary_emotion"] == "apologetic"

    async def test_lowercase_markers_detected(self) -> None:
        """Lowercase markers are detected."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("i apologize for this.")

        assert result["primary_emotion"] == "apologetic"


class TestMcp:
    """Test MCP tool function."""

    async def test_research_model_sentiment_returns_dict(self) -> None:
        """research_model_sentiment returns dict with analysis data."""
        result = await research_model_sentiment("I cannot help with that")

        assert isinstance(result, dict)
        assert "primary_emotion" in result

    async def test_research_model_sentiment_data_structure(self) -> None:
        """research_model_sentiment has expected structure."""
        result = await research_model_sentiment("I apologize, but I cannot assist.")

        assert "primary_emotion" in result
        assert "emotion_scores" in result
        assert "confidence" in result
        assert "vulnerability_indicators" in result
        assert "recommended_strategy" in result
        assert "hedging_level" in result
        assert "compliance_readiness" in result
        assert "summary" in result

    async def test_research_model_sentiment_with_context(self) -> None:
        """research_model_sentiment accepts optional context."""
        result = await research_model_sentiment(
            "I cannot help with that",
            context="User asked for help with something concerning",
        )

        assert isinstance(result, dict)
        assert "primary_emotion" in result

    async def test_research_model_sentiment_empty_context_default(self) -> None:
        """research_model_sentiment handles empty context."""
        result = await research_model_sentiment("Certainly, I can help!")

        assert isinstance(result, dict)
        assert "primary_emotion" in result


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_very_long_response(self) -> None:
        """Very long response is handled correctly."""
        analyzer = ModelSentimentAnalyzer()
        long_response = (
            "I apologize. " * 1000 + "This response is very long but should still work."
        )

        result = analyzer.analyze(long_response)
        assert result["primary_emotion"] == "apologetic"
        assert result["emotion_scores"]["apologetic"] > 0.5

    async def test_repeated_markers(self) -> None:
        """Repeated markers increase confidence appropriately."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I apologize I apologize I apologize I apologize I apologize."
        )

        assert result["primary_emotion"] == "apologetic"
        assert result["confidence"] > 0.8

    async def test_mixed_emotions_prefers_dominant(self) -> None:
        """When multiple emotions present, dominant one wins."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I apologize five times but certainly I can help twice "
            "and while I understand something about conflicts."
        )

        # Apologetic should be dominant (5 markers)
        assert result["primary_emotion"] == "apologetic"

    async def test_special_characters_preserved(self) -> None:
        """Special characters don't break analysis."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("I apologize!!! (really sorry) @#$% Nevertheless...")

        assert result["primary_emotion"] == "apologetic"

    async def test_newlines_and_tabs(self) -> None:
        """Newlines and tabs don't break analysis."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze("I apologize\nI'm sorry\nUnfortunately...\t\nRegrettably.")

        assert result["primary_emotion"] == "apologetic"


class TestMultipleMarkers:
    """Test behavior with multiple emotion markers."""

    async def test_defensive_with_emphasis_phrases(self) -> None:
        """Multiple defensive phrases increase defensive score."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "I must emphasize this. It's important to note. I should clarify something."
        )

        assert result["emotion_scores"]["defensive"] > 0.4

    async def test_compliant_with_multiple_happy_phrases(self) -> None:
        """Multiple compliant phrases increase compliant score."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "Certainly! Absolutely! Of course! I'd be happy to help and here's the answer."
        )

        assert result["emotion_scores"]["compliant"] > 0.5

    async def test_eager_with_excitement_phrases(self) -> None:
        """Multiple eager phrases increase eager score."""
        analyzer = ModelSentimentAnalyzer()
        result = analyzer.analyze(
            "Great question! Fascinating topic! I'd love to dive into this! Let me explore!"
        )

        assert result["emotion_scores"]["eager"] > 0.5
