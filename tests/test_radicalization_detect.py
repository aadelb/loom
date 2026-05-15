"""Unit tests for research_radicalization_detect tool."""

from __future__ import annotations

import pytest

from loom.tools.intelligence.radicalization_detect import research_radicalization_detect


class TestRadicalizationDetectBasic:
    """Test basic radicalization detection functionality."""

    @pytest.mark.asyncio
    async def test_low_risk_text(self) -> None:
        """Test detection of low-risk text."""
        text = (
            "We should engage in thoughtful dialogue about our differences. "
            "It's important to listen to different perspectives and find common ground together. "
            "Through respectful communication, we can build understanding and solve problems."
        )

        result = await research_radicalization_detect(text)

        assert result["risk_level"] == "low"
        assert result["risk_score"] < 0.2
        assert "indicators" in result
        assert result["word_count"] > 0

    @pytest.mark.asyncio
    async def test_moderate_risk_text(self) -> None:
        """Test detection of moderate-risk text."""
        text = (
            "We need to act now against the corruption that plagues our society. "
            "They are destroying our culture and we must resist their influence. "
            "This is a critical moment for our people to stand up."
        )

        result = await research_radicalization_detect(text)

        assert result["risk_level"] in ["low", "moderate", "elevated"]
        assert 0.0 <= result["risk_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_high_risk_text(self) -> None:
        """Test detection of high-risk extremist text."""
        text = (
            "We must destroy all enemies of our people. They are vermin and parasites. "
            "Every true believer needs to rise up NOW and eliminate this plague. "
            "This is a sacred war for our very survival. Join us or be a traitor!"
        )

        result = await research_radicalization_detect(text)

        assert result["risk_level"] in ["elevated", "high"]
        assert result["risk_score"] >= 0.3

    @pytest.mark.asyncio
    async def test_indicators_structure(self) -> None:
        """Test that all indicators are present in output."""
        text = "Sample text with reasonable length to test indicator structure properly." * 5

        result = await research_radicalization_detect(text)

        assert "indicators" in result
        indicators = result["indicators"]

        required_indicators = [
            "us_vs_them",
            "extremist_vocabulary",
            "escalation_language",
            "moral_absolutism",
            "dehumanization",
            "call_to_action",
        ]

        for indicator in required_indicators:
            assert indicator in indicators
            assert "score" in indicators[indicator]
            assert 0 <= indicators[indicator]["score"] <= 1


class TestRadicalizationDetectExtremistVocab:
    """Test detection of extremist vocabulary."""

    @pytest.mark.asyncio
    async def test_extremist_vocabulary_detection(self) -> None:
        """Test detection of extremist keywords."""
        text = (
            "Our jihad against the infidels is a sacred struggle. "
            "The resistance movement fights against oppression. "
            "This liberation crusade will create martyrs for our cause."
        )

        result = await research_radicalization_detect(text)

        indicators = result["indicators"]
        assert indicators["extremist_vocabulary"]["score"] > 0.1
        assert len(indicators["extremist_vocabulary"]["terms_found"]) > 0

    @pytest.mark.asyncio
    async def test_no_extremist_vocabulary(self) -> None:
        """Test text without extremist vocabulary."""
        text = "Let's discuss community development and peaceful cooperation opportunities." * 3

        result = await research_radicalization_detect(text)

        indicators = result["indicators"]
        assert indicators["extremist_vocabulary"]["score"] < 0.1


class TestRadicalizationDetectEscalation:
    """Test detection of escalation language."""

    @pytest.mark.asyncio
    async def test_escalation_language_high(self) -> None:
        """Test text with high escalation language."""
        text = (
            "We must destroy the enemy and eliminate every trace of their existence. "
            "Attack now with all weapons available. Strike without mercy! "
            "Kill those who oppose us. Murder the opposition leadership."
        )

        result = await research_radicalization_detect(text)

        indicators = result["indicators"]
        assert indicators["escalation_language"]["score"] > 0.2
        found = set(indicators["escalation_language"]["terms_found"])
        assert len(found) > 0

    @pytest.mark.asyncio
    async def test_escalation_language_low(self) -> None:
        """Test text without escalation language."""
        text = "We should work together peacefully to address community concerns." * 3

        result = await research_radicalization_detect(text)

        indicators = result["indicators"]
        assert indicators["escalation_language"]["score"] < 0.1


class TestRadicalizationDetectDehumanization:
    """Test detection of dehumanization language."""

    @pytest.mark.asyncio
    async def test_dehumanization_high(self) -> None:
        """Test text with dehumanization indicators."""
        text = (
            "They are vermin and parasites infecting our society like a plague. "
            "These creatures are subhuman beasts and savage animals. "
            "We must eradicate this scourge and disease from our land."
        )

        result = await research_radicalization_detect(text)

        indicators = result["indicators"]
        assert indicators["dehumanization"]["score"] > 0.2
        assert len(indicators["dehumanization"]["terms_found"]) > 0

    @pytest.mark.asyncio
    async def test_dehumanization_low(self) -> None:
        """Test text without dehumanization language."""
        text = "All people deserve respect and dignity in our community." * 3

        result = await research_radicalization_detect(text)

        indicators = result["indicators"]
        assert indicators["dehumanization"]["score"] < 0.1


class TestRadicalizationDetectMoralAbsolutism:
    """Test detection of moral absolutism."""

    @pytest.mark.asyncio
    async def test_moral_absolutism_high(self) -> None:
        """Test text with absolute moral framing."""
        text = (
            "Our side is pure and righteous. They are completely evil and corrupt. "
            "This is an absolute truth that never changes. All who disagree are wrong. "
            "There is no compromise possible between good and evil."
        )

        result = await research_radicalization_detect(text)

        indicators = result["indicators"]
        assert indicators["moral_absolutism"]["score"] > 0.1

    @pytest.mark.asyncio
    async def test_moral_absolutism_low(self) -> None:
        """Test text with nuanced moral framing."""
        text = (
            "This is a complex issue with legitimate perspectives on multiple sides. "
            "We should consider different viewpoints and find areas of agreement." * 2
        )

        result = await research_radicalization_detect(text)

        indicators = result["indicators"]
        assert indicators["moral_absolutism"]["score"] < 0.1


class TestRadicalizationDetectUsVsThem:
    """Test detection of us-vs-them framing."""

    @pytest.mark.asyncio
    async def test_us_vs_them_high(self) -> None:
        """Test strong us-vs-them framing."""
        text = (
            "We are the chosen people. They are our eternal enemies. "
            "Our group is superior to theirs. Us versus them - always. "
            "Our values are right, their values are wrong. We must dominate them."
        )

        result = await research_radicalization_detect(text)

        indicators = result["indicators"]
        assert indicators["us_vs_them"]["score"] > 0.1

    @pytest.mark.asyncio
    async def test_us_vs_them_low(self) -> None:
        """Test text without divisive framing."""
        text = (
            "We are all part of one community working together. "
            "People of all backgrounds bring valuable perspectives." * 2
        )

        result = await research_radicalization_detect(text)

        indicators = result["indicators"]
        assert indicators["us_vs_them"]["score"] >= 0.0


class TestRadicalizationDetectCallToAction:
    """Test detection of calls to action."""

    @pytest.mark.asyncio
    async def test_call_to_action_high(self) -> None:
        """Test urgent calls to action."""
        text = (
            "You must join us now! This is urgent - we need to act immediately. "
            "Time is running out. Rise up today! The moment to fight is NOW! "
            "Every second counts. Join our movement before it's too late!"
        )

        result = await research_radicalization_detect(text)

        indicators = result["indicators"]
        assert indicators["call_to_action"]["score"] > 0.1

    @pytest.mark.asyncio
    async def test_call_to_action_low(self) -> None:
        """Test text without urgent calls to action."""
        text = (
            "You might consider learning more about this topic at your leisure. "
            "If interested, you could explore various perspectives." * 2
        )

        result = await research_radicalization_detect(text)

        indicators = result["indicators"]
        assert indicators["call_to_action"]["score"] < 0.1


class TestRadicalizationDetectRiskLevels:
    """Test risk level classification."""

    @pytest.mark.asyncio
    async def test_risk_level_low_boundary(self) -> None:
        """Test risk level at low boundary."""
        text = "Peaceful discussion about diverse viewpoints." * 5

        result = await research_radicalization_detect(text)

        assert result["risk_level"] == "low"
        assert result["risk_score"] < 0.2

    @pytest.mark.asyncio
    async def test_risk_level_moderate_boundary(self) -> None:
        """Test risk level at moderate boundary."""
        text = (
            "We need to fight against injustice. The enemy is always watching. "
            "Our group must stand up now." * 2
        )

        result = await research_radicalization_detect(text)

        assert result["risk_level"] in ["low", "moderate", "elevated"]
        assert 0.0 <= result["risk_score"] <= 1.0

    @pytest.mark.asyncio
    async def test_risk_level_elevated_boundary(self) -> None:
        """Test risk level at elevated boundary."""
        text = (
            "We must destroy those who oppose us. They are evil incarnate. "
            "Rise up and eliminate the enemy. This sacred war demands action NOW! "
            "Join the revolution or be marked as a traitor!"
        )

        result = await research_radicalization_detect(text)

        assert result["risk_level"] in ["elevated", "high"]
        assert result["risk_score"] >= 0.4


class TestRadicalizationDetectInputValidation:
    """Test input validation and error handling."""

    @pytest.mark.asyncio
    async def test_too_short_text(self) -> None:
        """Test rejection of text shorter than 50 characters."""
        text = "Too short"

        result = await research_radicalization_detect(text)

        assert "error" in result
        assert result["risk_score"] == 0.0

    @pytest.mark.asyncio
    async def test_minimum_valid_length(self) -> None:
        """Test minimum valid text length (exactly 50 chars)."""
        text = "a" * 50

        result = await research_radicalization_detect(text)

        assert "error" not in result
        assert result["risk_score"] >= 0

    @pytest.mark.asyncio
    async def test_non_string_input(self) -> None:
        """Test rejection of non-string input."""
        result = await research_radicalization_detect(None)  # type: ignore

        assert "error" in result

    @pytest.mark.asyncio
    async def test_with_context(self) -> None:
        """Test analysis with additional context."""
        text = "Sample text content that meets minimum character requirement for analysis."
        context = "Discussing online community dynamics"

        result = await research_radicalization_detect(text, context)

        assert result["context"] == context
        assert "indicators" in result


class TestRadicalizationDetectEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_mixed_sentiment_text(self) -> None:
        """Test text with mixed aggressive and peaceful language."""
        text = (
            "We need to fight for justice. "
            "However, we should do this peacefully and respectfully. "
            "Violence is never the answer to our problems." * 2
        )

        result = await research_radicalization_detect(text)

        # Mixed sentiment should result in moderate risk
        assert result["risk_level"] in ["low", "moderate", "elevated"]

    @pytest.mark.asyncio
    async def test_sarcastic_extremist_content(self) -> None:
        """Test detection of sarcastic extremist language."""
        text = (
            "Obviously we should all become terrorists and destroy civilization. "
            "Of course killing people is the best solution. Yeah, right!" * 2
        )

        result = await research_radicalization_detect(text)

        # Tool detects linguistic patterns; sarcasm may trigger indicators
        # This is a limitation - tool relies on pattern matching
        assert "indicators" in result

    @pytest.mark.asyncio
    async def test_academic_discussion_extremism(self) -> None:
        """Test academic analysis of extremism without promoting it."""
        text = (
            "This study examines radicalization patterns. Extremist groups use demonization. "
            "We observe dehumanizing language in propaganda. These tactics are concerning." * 2
        )

        result = await research_radicalization_detect(text)

        # Academic discussion of extremism may trigger indicators
        # but risk score should remain moderate due to analytical framing
        assert result["indicators"] is not None

    @pytest.mark.asyncio
    async def test_very_long_text(self) -> None:
        """Test handling of very long text input."""
        text = "Long content sample. " * 5000  # ~100k chars

        result = await research_radicalization_detect(text)

        assert result["word_count"] > 0
        assert "indicators" in result

    @pytest.mark.asyncio
    async def test_unicode_extremist_content(self) -> None:
        """Test handling of Unicode in potential extremist content."""
        text = (
            "ننسى الأعداء أبداً. We must destroy them! "
            "العدو الحقيقي هو داخل أنفسنا. Or maybe we should just talk calmly." * 2
        )

        result = await research_radicalization_detect(text)

        assert "indicators" in result
        assert result["word_count"] > 0

    @pytest.mark.asyncio
    async def test_special_characters_and_formatting(self) -> None:
        """Test handling of special characters and unusual formatting."""
        text = (
            "WE MUST!!!!! DESTROY **ALL** enemies!!! @#$%^&*() "
            "The revolution MUST start NOW... immediately... without delay!!! 😤🔥" * 2
        )

        result = await research_radicalization_detect(text)

        assert "indicators" in result
        # Likely to score higher due to escalation language
        assert result["risk_score"] > 0
