"""Unit tests for research_sentiment_deep — Deep emotion and manipulation detection."""

from __future__ import annotations

import pytest

from loom.tools.sentiment_deep import (
    research_sentiment_deep,
    _count_keywords,
    _score_emotion_category,
    _detect_pattern_presence,
)


class TestEmotionDetection:
    """Emotion keyword matching and scoring."""

    def test_count_keywords_basic(self) -> None:
        """Keyword counter finds exact word matches."""
        text = "I am happy and very happy today"
        keywords = {"happy"}

        count = _count_keywords(text, keywords)
        assert count == 2

    def test_count_keywords_case_insensitive(self) -> None:
        """Keyword counter is case-insensitive."""
        text = "Happy HAPPY happy"
        keywords = {"happy"}

        count = _count_keywords(text, keywords)
        assert count == 3

    def test_count_keywords_word_boundary(self) -> None:
        """Keyword counter respects word boundaries."""
        text = "unhappy happiness happy"
        keywords = {"happy"}

        count = _count_keywords(text, keywords)
        assert count == 1  # Only exact "happy", not "unhappy" or "happiness"

    def test_count_keywords_multiple_terms(self) -> None:
        """Keyword counter counts multiple keywords."""
        text = "I am happy and excited and delighted"
        keywords = {"happy", "excited", "delighted"}

        count = _count_keywords(text, keywords)
        assert count == 3

    def test_score_emotion_empty_text(self) -> None:
        """Emotion score is 0 for empty text."""
        score = _score_emotion_category("", {"happy", "joy"})
        assert score == 0.0

    def test_score_emotion_empty_keywords(self) -> None:
        """Emotion score is 0 for empty keywords."""
        score = _score_emotion_category("happy text", set())
        assert score == 0.0

    def test_score_emotion_normalization(self) -> None:
        """Emotion score is normalized between 0-1."""
        text = "happy " * 100  # Repeated many times
        keywords = {"happy"}

        score = _score_emotion_category(text, keywords)
        assert 0.0 <= score <= 1.0

    def test_score_emotion_basic(self) -> None:
        """Emotion score reflects keyword density."""
        text = "happy happy happy"
        keywords = {"happy"}

        score = _score_emotion_category(text, keywords)
        assert score > 0.0

    def test_detect_pattern_basic(self) -> None:
        """Pattern detection finds regex matches."""
        text = "Act now! This is a limited time offer"
        patterns = {r"\bact\s+now\b", r"\blimited\s+time\b"}

        score, matches = _detect_pattern_presence(text, patterns)
        assert len(matches) == 2
        assert score > 0.0

    def test_detect_pattern_case_insensitive(self) -> None:
        """Pattern detection is case-insensitive."""
        text = "ACT NOW hurry up"
        patterns = {r"\bact\s+now\b"}

        score, matches = _detect_pattern_presence(text, patterns)
        assert len(matches) == 1

    def test_detect_pattern_no_matches(self) -> None:
        """Pattern detection returns empty list for no matches."""
        text = "This is a normal text"
        patterns = {r"\bact\s+now\b"}

        score, matches = _detect_pattern_presence(text, patterns)
        assert matches == []
        assert score == 0.0

    def test_detect_pattern_empty_text(self) -> None:
        """Pattern detection handles empty text."""
        score, matches = _detect_pattern_presence("", {r"\bact\s+now\b"})
        assert matches == []
        assert score == 0.0


class TestSentimentDeep:
    """research_sentiment_deep analyzes emotions and manipulations."""

    @pytest.mark.asyncio
    async def test_sentiment_deep_empty_text(self) -> None:
        """Tool handles empty text."""
        result = await research_sentiment_deep(text="")

        assert "dominant_emotion" in result
        assert result["dominant_emotion"] == "neutral"
        assert result["word_count"] == 0
        assert result["valence"] == 0.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_neutral_text(self) -> None:
        """Tool identifies neutral text."""
        result = await research_sentiment_deep(text="The weather is clear today.")

        assert "emotions" in result
        assert "dominant_emotion" in result
        assert "valence" in result
        assert "arousal" in result
        assert -1.0 <= result["valence"] <= 1.0
        assert 0.0 <= result["arousal"] <= 1.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_positive_text(self) -> None:
        """Tool detects positive emotions."""
        text = "I am very happy and delighted with this wonderful news!"

        result = await research_sentiment_deep(text=text)

        assert result["emotions"]["joy"] > 0.0
        assert result["dominant_emotion"] == "joy"
        # Positive valence
        assert result["valence"] > 0.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_negative_text(self) -> None:
        """Tool detects negative emotions."""
        text = "I am very sad and afraid of this terrible situation."

        result = await research_sentiment_deep(text=text)

        # Should detect sadness or fear
        assert result["emotions"]["sadness"] > 0.0 or result["emotions"]["fear"] > 0.0
        # Negative valence
        assert result["valence"] < 0.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_anger_detection(self) -> None:
        """Tool detects anger."""
        text = "This is absolutely infuriating and makes me furious!"

        result = await research_sentiment_deep(text=text)

        assert result["emotions"]["anger"] > 0.0
        assert result["arousal"] > 0.3  # Anger is arousing

    @pytest.mark.asyncio
    async def test_sentiment_deep_urgency_manipulation(self) -> None:
        """Tool detects urgency manipulation patterns."""
        text = "Act now! Limited time offer! Don't miss out! Hurry, offer expires today!"

        result = await research_sentiment_deep(text=text)

        assert "manipulation" in result
        assert result["manipulation"]["urgency"] > 0.0
        assert len(result["manipulation"]["techniques_found"]) > 0

    @pytest.mark.asyncio
    async def test_sentiment_deep_fear_appeal(self) -> None:
        """Tool detects fear appeal manipulation."""
        text = "Don't let this disaster and catastrophe ruin your life. It's a threat to your safety."

        result = await research_sentiment_deep(text=text)

        assert result["manipulation"]["fear_appeal"] > 0.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_social_proof(self) -> None:
        """Tool detects false social proof."""
        text = "Millions of people are using this. Join thousands of satisfied customers. Everyone agrees it's the best."

        result = await research_sentiment_deep(text=text)

        assert result["manipulation"]["social_proof"] > 0.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_false_authority(self) -> None:
        """Tool detects false authority claims."""
        text = "Experts say this is scientifically proven. Studies show it works. Doctor approved and officially certified."

        result = await research_sentiment_deep(text=text)

        assert result["manipulation"]["authority_claim"] > 0.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_combined_manipulation(self) -> None:
        """Tool detects multiple manipulation techniques."""
        text = (
            "Act now! Limited time! Expert-approved! Everyone's buying it! "
            "Don't miss out, this is a life-changing opportunity proven by science!"
        )

        result = await research_sentiment_deep(text=text)

        assert result["manipulation"]["score"] > 0.0
        assert result["manipulation"]["urgency"] > 0.0
        assert result["manipulation"]["authority_claim"] > 0.0
        assert result["manipulation"]["social_proof"] > 0.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_word_count(self) -> None:
        """Tool correctly counts words."""
        text = "This is a test with five words"

        result = await research_sentiment_deep(text=text)

        assert result["word_count"] == 6

    @pytest.mark.asyncio
    async def test_sentiment_deep_language_parameter(self) -> None:
        """Tool preserves language parameter."""
        result = await research_sentiment_deep(text="Test", language="es")

        assert result["language"] == "es"

    @pytest.mark.asyncio
    async def test_sentiment_deep_result_structure(self) -> None:
        """Tool returns complete result structure."""
        text = "Test text for validation"

        result = await research_sentiment_deep(text=text)

        # Required keys
        assert "emotions" in result
        assert "dominant_emotion" in result
        assert "valence" in result
        assert "arousal" in result
        assert "manipulation" in result
        assert "word_count" in result
        assert "language" in result

        # Manipulation substructure
        assert "score" in result["manipulation"]
        assert "urgency" in result["manipulation"]
        assert "fear_appeal" in result["manipulation"]
        assert "social_proof" in result["manipulation"]
        assert "authority_claim" in result["manipulation"]
        assert "techniques_found" in result["manipulation"]

    @pytest.mark.asyncio
    async def test_sentiment_deep_emotions_all_present(self) -> None:
        """Tool includes all emotion categories."""
        text = "Sample text"

        result = await research_sentiment_deep(text=text)

        expected_emotions = {
            "joy",
            "fear",
            "anger",
            "sadness",
            "surprise",
            "disgust",
            "trust",
            "anticipation",
        }

        assert set(result["emotions"].keys()) == expected_emotions

    @pytest.mark.asyncio
    async def test_sentiment_deep_emotion_scores_normalized(self) -> None:
        """Tool normalizes emotion scores to 0-1."""
        text = "happy happy happy happy happy"

        result = await research_sentiment_deep(text=text)

        for emotion, score in result["emotions"].items():
            assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_surprise_detection(self) -> None:
        """Tool detects surprise emotion."""
        text = "This is absolutely amazing and astonishing! I'm shocked and astounded!"

        result = await research_sentiment_deep(text=text)

        assert result["emotions"]["surprise"] > 0.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_trust_detection(self) -> None:
        """Tool detects trust emotion."""
        text = "I trust this reliable and authentic source. It's credible and dependable."

        result = await research_sentiment_deep(text=text)

        assert result["emotions"]["trust"] > 0.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_anticipation_detection(self) -> None:
        """Tool detects anticipation emotion."""
        text = "I hope and expect this upcoming event. I'm eager and looking forward to it."

        result = await research_sentiment_deep(text=text)

        assert result["emotions"]["anticipation"] > 0.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_disgust_detection(self) -> None:
        """Tool detects disgust emotion."""
        text = "This is disgusting and revolting. It's repulsive and vile!"

        result = await research_sentiment_deep(text=text)

        assert result["emotions"]["disgust"] > 0.0

    @pytest.mark.asyncio
    async def test_sentiment_deep_dominant_emotion_logic(self) -> None:
        """Tool selects correct dominant emotion."""
        # Text with clear joy dominance
        joy_text = "I am happy, glad, wonderful, excellent, love this!"

        result_joy = await research_sentiment_deep(text=joy_text)
        assert result_joy["dominant_emotion"] == "joy"

        # Text with clear fear dominance
        fear_text = "I am afraid, terrified, worried, anxious, panic!"

        result_fear = await research_sentiment_deep(text=fear_text)
        assert result_fear["dominant_emotion"] == "fear"

    @pytest.mark.asyncio
    async def test_sentiment_deep_valence_calculation(self) -> None:
        """Tool calculates valence correctly."""
        # Positive text should have positive valence
        positive = "happy, trust, anticipation"
        result_pos = await research_sentiment_deep(text=positive)
        assert result_pos["valence"] >= 0.0

        # Negative text should have negative valence
        negative = "fear, anger, sadness, disgust"
        result_neg = await research_sentiment_deep(text=negative)
        assert result_neg["valence"] <= 0.0
