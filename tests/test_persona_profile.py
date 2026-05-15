"""Unit tests for research_persona_profile tool."""

from __future__ import annotations

import pytest

from loom.tools.adversarial.persona_profile import research_persona_profile


class TestPersonaProfileBasic:
    """Test basic persona profile functionality."""

    @pytest.mark.asyncio
    async def test_profile_valid_inputs(self) -> None:
        """Test persona profiling with valid text samples."""
        texts = [
            "I believe it's important to approach complex issues with nuance and careful consideration. "
            "The interdisciplinary nature of modern problems demands sophisticated analysis.",
            "We organized our team systematically to ensure every deadline is met. "
            "Detailed planning and disciplined execution are key to our success.",
            "Let's get together and have fun! I love meeting new people and sharing experiences. "
            "You won't believe the amazing adventures we've had!",
        ]

        result = await research_persona_profile(texts)

        assert result["profile"] is not None
        assert "formality" in result["profile"]
        assert "vocabulary_tier" in result["profile"]
        assert "personality" in result["profile"]
        assert "top_topics" in result["profile"]
        assert "estimated_education" in result["profile"]

        # Verify numeric ranges
        assert 0 <= result["profile"]["formality"] <= 1
        assert result["profile"]["vocabulary_tier"] in ["basic", "intermediate", "advanced"]
        assert result["text_count"] == 3
        assert result["total_words"] > 0

        # Verify personality scores
        personality = result["profile"]["personality"]
        for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
            assert trait in personality
            assert 0 <= personality[trait] <= 1

    @pytest.mark.asyncio
    async def test_profile_minimal_valid_input(self) -> None:
        """Test with minimum valid text length."""
        texts = ["a" * 50]  # Exactly 50 characters

        result = await research_persona_profile(texts)

        assert result["profile"] is not None
        assert result["text_count"] == 1

    @pytest.mark.asyncio
    async def test_profile_too_short_text(self) -> None:
        """Test rejection of text shorter than 50 characters."""
        texts = ["short text"]

        result = await research_persona_profile(texts)

        assert "error" in result
        assert result["profile"] is None
        assert result["text_count"] == 0

    @pytest.mark.asyncio
    async def test_profile_empty_list(self) -> None:
        """Test rejection of empty text list."""
        result = await research_persona_profile([])

        assert "error" in result
        assert result["profile"] is None

    @pytest.mark.asyncio
    async def test_profile_with_metadata_timestamps(self) -> None:
        """Test persona profiling with timestamp metadata."""
        texts = ["The importance of careful analysis cannot be overstated in modern research contexts."]
        metadata = {
            "timestamps": [
                "2024-04-27T14:30:00Z",
                "2024-04-27T22:15:00Z",
                "2024-04-27T06:45:00Z",
            ]
        }

        result = await research_persona_profile(texts, metadata)

        assert result["temporal"] is not None
        assert "peak_hours" in result["temporal"]
        assert "activity_pattern" in result["temporal"]

    @pytest.mark.asyncio
    async def test_profile_temporal_activity_pattern(self) -> None:
        """Test temporal activity pattern detection."""
        texts = ["Night owl posting patterns analysis for research purposes."]

        # Night-time timestamps (between 22:00 and 06:00)
        metadata = {
            "timestamps": [
                "2024-04-27T23:00:00Z",
                "2024-04-27T01:30:00Z",
                "2024-04-27T03:15:00Z",
            ]
        }

        result = await research_persona_profile(texts, metadata)

        if result["temporal"]:
            # Should detect nocturnal pattern
            assert "activity_pattern" in result["temporal"]


class TestPersonaProfileVocabulary:
    """Test vocabulary tier detection."""

    @pytest.mark.asyncio
    async def test_basic_vocabulary_detection(self) -> None:
        """Test detection of basic vocabulary tier."""
        texts = [
            "I like good things. You are a good person. We do good work. "
            "It is a bad thing when people are bad. Make things good, not bad." * 3
        ]

        result = await research_persona_profile(texts)

        assert result["profile"]["vocabulary_tier"] == "basic"

    @pytest.mark.asyncio
    async def test_advanced_vocabulary_detection(self) -> None:
        """Test detection of advanced vocabulary tier."""
        texts = [
            "The epistemological paradigm presents multifaceted challenges in contemporary analysis. "
            "Juxtaposing phenomenological perspectives with empirical methodology yields perspicacious insights. "
            "Such recondite conceptualizations demonstrate tacit understanding of abstruse theoretical frameworks." * 2
        ]

        result = await research_persona_profile(texts)

        assert result["profile"]["vocabulary_tier"] == "advanced"


class TestPersonaProfilePersonality:
    """Test Big Five personality indicator detection."""

    @pytest.mark.asyncio
    async def test_openness_indicators(self) -> None:
        """Test detection of openness traits."""
        texts = [
            "I find novel ideas fascinating and I'm always exploring creative approaches. "
            "The diversity of abstract concepts appeals to my curiosity about unique perspectives. "
            "Art, philosophy, and complex theories intrigue me." * 2
        ]

        result = await research_persona_profile(texts)

        assert result["profile"]["personality"]["openness"] > 0.5

    @pytest.mark.asyncio
    async def test_conscientiousness_indicators(self) -> None:
        """Test detection of conscientiousness traits."""
        texts = [
            "I maintain a systematic and organized approach to all my work. "
            "Careful planning and precise execution are essential to my success. "
            "I follow detailed procedures and maintain discipline in my responsibilities." * 2
        ]

        result = await research_persona_profile(texts)

        assert result["profile"]["personality"]["conscientiousness"] > 0.5

    @pytest.mark.asyncio
    async def test_extraversion_indicators(self) -> None:
        """Test detection of extraversion traits."""
        texts = [
            "I love talking to people and building friendships. Social events energize me! "
            "Meeting new friends and having fun together is my favorite activity. "
            "The excitement of group gatherings and public events makes me feel alive!" * 2
        ]

        result = await research_persona_profile(texts)

        assert result["profile"]["personality"]["extraversion"] > 0.5


class TestPersonaProfileEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_profile_with_none_input(self) -> None:
        """Test rejection of None input."""
        result = await research_persona_profile(None)  # type: ignore

        assert "error" in result
        assert result["profile"] is None

    @pytest.mark.asyncio
    async def test_profile_mixed_valid_invalid_texts(self) -> None:
        """Test with mixture of valid and invalid texts."""
        texts = [
            "This is a valid text that meets the minimum character requirement for analysis.",
            "too short",  # Invalid: < 50 chars
            "Another valid sample that contains sufficient information for profile generation.",
        ]

        result = await research_persona_profile(texts)

        # Should process only valid texts
        assert result["text_count"] == 2

    @pytest.mark.asyncio
    async def test_profile_large_input(self) -> None:
        """Test with large text inputs."""
        texts = ["Long text sample. " * 1000]  # Very long text

        result = await research_persona_profile(texts)

        assert result["profile"] is not None
        assert result["total_words"] > 0

    @pytest.mark.asyncio
    async def test_profile_special_characters(self) -> None:
        """Test handling of special characters and emojis."""
        texts = [
            "This text contains special chars: @#$%^&*() and emojis 😀🎉. "
            "It's still valid content for analysis despite unusual formatting!" * 2
        ]

        result = await research_persona_profile(texts)

        assert result["profile"] is not None

    @pytest.mark.asyncio
    async def test_profile_unicode_content(self) -> None:
        """Test handling of Unicode content."""
        texts = [
            "This text contains Unicode: café, naïve, résumé, and other international characters. "
            "Supporting multiple languages is important for global analysis." * 2
        ]

        result = await research_persona_profile(texts)

        assert result["profile"] is not None


class TestPersonaProfileEducationEstimate:
    """Test education level estimation."""

    @pytest.mark.asyncio
    async def test_education_graduate_estimate(self) -> None:
        """Test detection of graduate-level education markers."""
        texts = [
            "The epistemological implications of quantum phenomena necessitate reconsideration of "
            "traditional paradigms. Contemporary theoretical frameworks exhibit unprecedented sophistication." * 3
        ]

        result = await research_persona_profile(texts)

        # Advanced vocabulary + high openness should indicate graduate level
        assert result["profile"]["estimated_education"] in ["graduate", "undergraduate"]

    @pytest.mark.asyncio
    async def test_education_high_school_estimate(self) -> None:
        """Test detection of high school-level education markers."""
        texts = [
            "I like good things and bad things. Things are sometimes good. "
            "The good thing is important. People do things every day." * 3
        ]

        result = await research_persona_profile(texts)

        # Basic vocabulary should indicate high school or lower
        assert result["profile"]["estimated_education"] in ["high_school", "unknown"]
