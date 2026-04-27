"""Tests for sentiment_deep research tool."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestSentimentDeep:
    """Test suite for research_sentiment_deep tool."""

    async def test_sentiment_deep_joy_emotion(self):
        """Test detection of joy/positive emotion."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "I am so happy and delighted with this wonderful experience. "
            "I absolutely love it! This is excellent and fantastic!"
        )

        result = await research_sentiment_deep(text)

        assert "emotions" in result
        assert "dominant_emotion" in result
        assert result["emotions"]["joy"] > 0.5
        assert result["dominant_emotion"] == "joy"
        assert result["valence"] > 0.3

    async def test_sentiment_deep_fear_emotion(self):
        """Test detection of fear emotion."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "I am terrified and afraid of what might happen. "
            "This is terrifying and causes panic. I am extremely anxious."
        )

        result = await research_sentiment_deep(text)

        assert result["emotions"]["fear"] > 0.5
        assert result["dominant_emotion"] == "fear"
        assert result["arousal"] > 0.4

    async def test_sentiment_deep_anger_emotion(self):
        """Test detection of anger emotion."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "I am absolutely furious and enraged by this behavior. "
            "This is disgusting and infuriating! I hate it!"
        )

        result = await research_sentiment_deep(text)

        assert result["emotions"]["anger"] > 0.5
        assert result["dominant_emotion"] == "anger"

    async def test_sentiment_deep_sadness_emotion(self):
        """Test detection of sadness emotion."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "I feel so sad and depressed. This is heartbreaking and "
            "I feel lonely and miserable. I have such sorrow."
        )

        result = await research_sentiment_deep(text)

        assert result["emotions"]["sadness"] > 0.5
        assert result["dominant_emotion"] == "sadness"
        assert result["valence"] < -0.3

    async def test_sentiment_deep_surprise_emotion(self):
        """Test detection of surprise emotion."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "I was shocked and amazed by what I saw. This is incredible "
            "and astonishing. I was completely taken aback!"
        )

        result = await research_sentiment_deep(text)

        assert result["emotions"]["surprise"] > 0.4

    async def test_sentiment_deep_disgust_emotion(self):
        """Test detection of disgust emotion."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "This is revolting and disgusting. It's repulsive and vile. "
            "This is absolutely appalling and nasty."
        )

        result = await research_sentiment_deep(text)

        assert result["emotions"]["disgust"] > 0.5

    async def test_sentiment_deep_trust_emotion(self):
        """Test detection of trust emotion."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "I trust this source completely. They are reliable, honest, "
            "and loyal. This is genuine and authentic information."
        )

        result = await research_sentiment_deep(text)

        assert result["emotions"]["trust"] > 0.4

    async def test_sentiment_deep_anticipation_emotion(self):
        """Test detection of anticipation emotion."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "I expect great things to come. I hope for the best and am "
            "eager for upcoming events. I am prepared and ready."
        )

        result = await research_sentiment_deep(text)

        assert result["emotions"]["anticipation"] > 0.4

    async def test_sentiment_deep_urgency_manipulation(self):
        """Test detection of urgency manipulation patterns."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "Act now! This is a limited time offer. Don't miss out! "
            "Hurry, this is your last chance. The offer expires today!"
        )

        result = await research_sentiment_deep(text)

        assert result["manipulation"]["score"] > 0.3
        assert result["manipulation"]["urgency"] > 0.3
        assert len(result["manipulation"]["techniques_found"]) > 0

    async def test_sentiment_deep_fear_appeal(self):
        """Test detection of fear appeal manipulation."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "Failure to act will have devastating consequences. "
            "This poses a serious threat and danger to you. "
            "The risk is catastrophic."
        )

        result = await research_sentiment_deep(text)

        assert result["manipulation"]["fear_appeal"] > 0.2

    async def test_sentiment_deep_social_proof(self):
        """Test detection of social proof manipulation."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "Everyone knows this is true. Most people agree with this. "
            "Millions of people have joined our movement. "
            "This is widely accepted by the consensus."
        )

        result = await research_sentiment_deep(text)

        assert result["manipulation"]["social_proof"] > 0.2

    async def test_sentiment_deep_authority_claim(self):
        """Test detection of false authority claims."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "Experts say this works. Studies show results. "
            "This has been scientifically proven. According to experts, "
            "research shows this is effective."
        )

        result = await research_sentiment_deep(text)

        assert result["manipulation"]["authority_claim"] > 0.2

    async def test_sentiment_deep_valence_calculation(self):
        """Test valence score calculation (positive vs negative)."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        positive_text = "I am happy, joyful, and grateful. I trust this completely."
        result = await research_sentiment_deep(positive_text)
        assert result["valence"] > 0.0

        negative_text = "I am sad, angry, and fearful. This is disgusting."
        result = await research_sentiment_deep(negative_text)
        assert result["valence"] < 0.0

    async def test_sentiment_deep_arousal_calculation(self):
        """Test arousal score calculation (calm vs intense)."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        intense_text = (
            "I am furious, terrified, and shocked. This is amazing!"
        )
        result = await research_sentiment_deep(intense_text)
        assert result["arousal"] > 0.5

        calm_text = "Everything is okay. I trust the process."
        result = await research_sentiment_deep(calm_text)
        assert result["arousal"] < 0.5

    async def test_sentiment_deep_empty_text(self):
        """Test handling of empty text."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        result = await research_sentiment_deep("")

        assert result["emotions"]["joy"] == 0.0
        assert result["dominant_emotion"] == "neutral"
        assert result["word_count"] == 0

    async def test_sentiment_deep_none_text(self):
        """Test handling of None text."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        result = await research_sentiment_deep(None)

        assert result["emotions"]["joy"] == 0.0
        assert result["dominant_emotion"] == "neutral"

    async def test_sentiment_deep_language_parameter(self):
        """Test language parameter is preserved in output."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        result = await research_sentiment_deep("I am happy", language="ar")

        assert result["language"] == "ar"

    async def test_sentiment_deep_word_count(self):
        """Test accurate word count."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = "The quick brown fox jumps over the lazy dog"
        result = await research_sentiment_deep(text)

        assert result["word_count"] == 9

    async def test_sentiment_deep_neutral_text(self):
        """Test neutral text with no strong emotions."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = "The cat is on the mat. The dog is in the yard."

        result = await research_sentiment_deep(text)

        # All emotions should be low
        for emotion_score in result["emotions"].values():
            assert emotion_score < 0.2
        assert result["dominant_emotion"] == "neutral"
        assert abs(result["valence"]) < 0.2

    async def test_sentiment_deep_mixed_emotions(self):
        """Test text with mixed emotions."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "I am happy about the good news but sad about the loss. "
            "I trust the outcome but fear the process."
        )

        result = await research_sentiment_deep(text)

        assert result["emotions"]["joy"] > 0.0
        assert result["emotions"]["sadness"] > 0.0
        assert result["emotions"]["trust"] > 0.0
        assert result["emotions"]["fear"] > 0.0

    async def test_sentiment_deep_returns_dict(self):
        """Test that result is a proper dictionary."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        result = await research_sentiment_deep("I am very happy")

        assert isinstance(result, dict)
        assert "emotions" in result
        assert "dominant_emotion" in result
        assert "valence" in result
        assert "arousal" in result
        assert "manipulation" in result
        assert "word_count" in result
        assert "language" in result

    async def test_sentiment_deep_emotions_in_0_1_range(self):
        """Test that all emotion scores are between 0 and 1."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = "Very happy! Extremely sad! Absolutely furious! Totally afraid!"
        result = await research_sentiment_deep(text)

        for emotion_name, score in result["emotions"].items():
            assert 0.0 <= score <= 1.0, f"{emotion_name} score {score} out of range"

    async def test_sentiment_deep_manipulation_scores_in_range(self):
        """Test that manipulation scores are in 0-1 range."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = (
            "Act now! Limited time! Everyone knows this! Experts say! "
            "Threatening consequences! Act quickly!"
        )
        result = await research_sentiment_deep(text)

        assert 0.0 <= result["manipulation"]["score"] <= 1.0
        assert 0.0 <= result["manipulation"]["urgency"] <= 1.0
        assert 0.0 <= result["manipulation"]["fear_appeal"] <= 1.0
        assert 0.0 <= result["manipulation"]["social_proof"] <= 1.0
        assert 0.0 <= result["manipulation"]["authority_claim"] <= 1.0

    async def test_sentiment_deep_valence_in_range(self):
        """Test that valence is between -1 and 1."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = "Testing valence range with various emotions"
        result = await research_sentiment_deep(text)

        assert -1.0 <= result["valence"] <= 1.0

    async def test_sentiment_deep_arousal_in_range(self):
        """Test that arousal is between 0 and 1."""
        from loom.tools.sentiment_deep import research_sentiment_deep

        text = "Testing arousal range"
        result = await research_sentiment_deep(text)

        assert 0.0 <= result["arousal"] <= 1.0
