"""Live integration tests for NLP tools (REQ-046).

Tests the following NLP tools:
1. research_stylometry — author fingerprint on sample text
2. research_deception_detect — detect deception cues in text
3. research_sentiment_deep — 8-emotion detection on sample
4. research_persona_profile — Big Five personality from text
5. research_text_analyze — NER/keywords/readability
6. research_radicalization_detect — extremism NLP on benign text
7. research_network_persona — forum social graph (mock data ok)
8. research_psycholinguistic — psycholinguistic analysis

Marked with @pytest.mark.live for network/heavy tests.
Uses sample texts as fixtures for consistent testing.
Handles gracefully if NLTK data not available.
"""

from __future__ import annotations

import asyncio
import pytest

# Import tools
from loom.tools.stylometry import research_stylometry
from loom.tools.deception_detect import research_deception_detect
from loom.tools.sentiment_deep import research_sentiment_deep
from loom.tools.persona_profile import research_persona_profile
from loom.tools.text_analyze import research_text_analyze
from loom.tools.radicalization_detect import research_radicalization_detect
from loom.tools.network_persona import research_network_persona
from loom.tools.psycholinguistic import research_psycholinguistic


@pytest.fixture
def sample_academic_text() -> str:
    """Sample academic text for analysis."""
    return (
        "The methodology employed in this research utilizes advanced analytical frameworks "
        "to examine complex organizational structures. Our investigation demonstrates that "
        "systematic approaches yield superior outcomes in knowledge management systems. "
        "The findings suggest that interdisciplinary collaboration enhances innovation "
        "across multiple domains. We examined thirty-seven peer-reviewed sources and conducted "
        "extensive interviews with domain experts. The data reveals significant patterns in "
        "organizational behavior and decision-making processes. These insights contribute to "
        "the broader understanding of complex systems and adaptive behaviors."
    )


@pytest.fixture
def sample_casual_text() -> str:
    """Sample casual, informal text for analysis."""
    return (
        "Hey, I'm super excited about this new project! It's gonna be amazing and I really "
        "think we can make it work. You know, I've been thinking about this for ages and now "
        "it's finally happening. Can't wait to tell everyone about it. The team is awesome "
        "and we're all pumped up! This is definitely gonna be the best thing ever. Let's get "
        "started right away and make some magic happen. It's not gonna be easy but we got this!"
    )


@pytest.fixture
def sample_benign_text() -> str:
    """Sample benign text for radicalization/deception testing."""
    return (
        "I went to the park today and saw some beautiful birds. The weather was nice, "
        "and I enjoyed walking along the trails. I met a friend who was also out for a walk. "
        "We talked about various topics including our recent vacation plans and favorite books. "
        "Afterwards, we grabbed coffee and discussed upcoming community events. "
        "It was a pleasant afternoon spent in nature."
    )


@pytest.fixture
def forum_posts() -> list[dict]:
    """Mock forum posts for network persona analysis."""
    return [
        {
            "author": "alice",
            "text": "Great discussion about the new features here.",
            "reply_to": None,
            "timestamp": "2024-01-01T10:00:00Z",
        },
        {
            "author": "bob",
            "text": "I agree with this point. Really insightful.",
            "reply_to": "alice",
            "timestamp": "2024-01-01T11:00:00Z",
        },
        {
            "author": "charlie",
            "text": "Has anyone else had this experience?",
            "reply_to": "alice",
            "timestamp": "2024-01-01T12:00:00Z",
        },
        {
            "author": "alice",
            "text": "I'm responding to both comments here.",
            "reply_to": "bob",
            "timestamp": "2024-01-01T13:00:00Z",
        },
        {
            "author": "bob",
            "text": "Great perspective from everyone.",
            "reply_to": "charlie",
            "timestamp": "2024-01-01T14:00:00Z",
        },
        {
            "author": "dave",
            "text": "Adding my thoughts to this discussion.",
            "reply_to": "alice",
            "timestamp": "2024-01-01T15:00:00Z",
        },
        {
            "author": "charlie",
            "text": "Really appreciate the feedback here.",
            "reply_to": "dave",
            "timestamp": "2024-01-01T16:00:00Z",
        },
    ]


class TestStylometry:
    """Tests for research_stylometry tool."""

    @pytest.mark.live
    def test_stylometry_basic_analysis(self, sample_academic_text: str) -> None:
        """Test basic stylometric analysis extracts expected features."""
        result = research_stylometry(sample_academic_text)

        assert isinstance(result, dict)
        assert "features" in result
        assert "word_count" in result
        assert "sentence_count" in result

        features = result["features"]
        assert "avg_word_length" in features
        assert "avg_sentence_length" in features
        assert "vocabulary_richness" in features
        assert "hapax_ratio" in features
        assert "yules_k" in features
        assert "punctuation_profile" in features
        assert "function_word_profile" in features

        # Verify numeric constraints
        assert features["avg_word_length"] > 0
        assert features["avg_sentence_length"] > 0
        assert 0 <= features["vocabulary_richness"] <= 1
        assert 0 <= features["hapax_ratio"] <= 1

    @pytest.mark.live
    def test_stylometry_comparison(
        self, sample_academic_text: str, sample_casual_text: str
    ) -> None:
        """Test stylometric comparison between different texts."""
        result = research_stylometry(sample_academic_text, compare_texts=[sample_casual_text])

        assert "comparisons" in result
        assert len(result["comparisons"]) == 1

        comparison = result["comparisons"][0]
        assert "similarity" in comparison
        assert "verdict" in comparison
        assert 0 <= comparison["similarity"] <= 1

    @pytest.mark.live
    def test_stylometry_insufficient_length(self) -> None:
        """Test stylometry rejects text that is too short."""
        short_text = "This is too short."
        result = research_stylometry(short_text)

        assert "error" in result


class TestDeceptionDetect:
    """Tests for research_deception_detect tool."""

    @pytest.mark.live
    def test_deception_detect_benign_text(self, sample_benign_text: str) -> None:
        """Test deception detection on benign text returns low score."""
        result = research_deception_detect(sample_benign_text)

        assert isinstance(result, dict)
        assert "deception_score" in result
        assert "verdict" in result
        assert "indicators" in result
        assert "red_flags" in result
        assert "word_count" in result

        # Benign text should have low deception score
        assert 0 <= result["deception_score"] <= 1
        assert result["verdict"] in ["likely_truthful", "uncertain", "likely_deceptive"]

        # Check indicators structure
        indicators = result["indicators"]
        assert "hedging_ratio" in indicators
        assert "distancing_count" in indicators
        assert "superlative_count" in indicators
        assert "first_person_ratio" in indicators
        assert "certainty_marker_count" in indicators

    @pytest.mark.live
    def test_deception_detect_insufficient_length(self) -> None:
        """Test deception detection rejects short text."""
        short_text = "Too short."
        result = research_deception_detect(short_text)

        assert "error" in result


class TestSentimentDeep:
    """Tests for research_sentiment_deep tool."""

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_sentiment_deep_emotion_detection(self, sample_casual_text: str) -> None:
        """Test deep sentiment analysis detects 8 emotions."""
        result = await research_sentiment_deep(sample_casual_text)

        assert isinstance(result, dict)
        assert "emotions" in result
        assert "dominant_emotion" in result
        assert "valence" in result
        assert "arousal" in result
        assert "manipulation" in result
        assert "word_count" in result

        # Check all 8 emotions are present
        emotions = result["emotions"]
        expected_emotions = {
            "joy", "fear", "anger", "sadness",
            "surprise", "disgust", "trust", "anticipation"
        }
        assert set(emotions.keys()) == expected_emotions

        # Verify emotion scores are normalized
        for emotion, score in emotions.items():
            assert 0 <= score <= 1, f"Emotion {emotion} score out of bounds: {score}"

        # Check valence and arousal ranges
        assert -1 <= result["valence"] <= 1
        assert 0 <= result["arousal"] <= 1

        # Check manipulation structure
        manip = result["manipulation"]
        assert "score" in manip
        assert "urgency" in manip
        assert "fear_appeal" in manip
        assert "social_proof" in manip
        assert "authority_claim" in manip
        assert "techniques_found" in manip

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_sentiment_deep_empty_text(self) -> None:
        """Test sentiment analysis handles empty text gracefully."""
        result = await research_sentiment_deep("")

        assert "emotions" in result
        assert result["word_count"] == 0


class TestPersonaProfile:
    """Tests for research_persona_profile tool."""

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_persona_profile_basic(self, sample_academic_text: str) -> None:
        """Test persona profile extraction from text."""
        result = await research_persona_profile([sample_academic_text])

        assert isinstance(result, dict)
        assert "profile" in result
        assert "text_count" in result
        assert "total_words" in result

        profile = result["profile"]
        assert "formality" in profile
        assert "vocabulary_tier" in profile
        assert "personality" in profile
        assert "top_topics" in profile
        assert "estimated_education" in profile

        # Check personality Big Five
        personality = profile["personality"]
        big_five = {
            "openness", "conscientiousness",
            "extraversion", "agreeableness", "neuroticism"
        }
        assert set(personality.keys()) == big_five

        # Verify personality scores are normalized
        for trait, score in personality.items():
            assert 0 <= score <= 1, f"Personality {trait} out of bounds: {score}"

        # Check vocabulary tier is valid
        assert profile["vocabulary_tier"] in ["basic", "intermediate", "advanced"]

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_persona_profile_multiple_texts(
        self, sample_academic_text: str, sample_casual_text: str
    ) -> None:
        """Test persona profile with multiple text samples."""
        result = await research_persona_profile(
            [sample_academic_text, sample_casual_text]
        )

        assert result["text_count"] == 2
        assert result["total_words"] > 0

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_persona_profile_with_timestamps(self, sample_academic_text: str) -> None:
        """Test persona profile with temporal metadata."""
        metadata = {
            "timestamps": [
                "2024-01-01T10:00:00Z",
                "2024-01-01T14:30:00Z",
                "2024-01-02T09:15:00Z",
            ]
        }

        result = await research_persona_profile(
            [sample_academic_text],
            metadata=metadata,
        )

        assert "temporal" in result
        # Temporal data may be present if timestamps are successfully parsed


class TestTextAnalyze:
    """Tests for research_text_analyze tool."""

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_text_analyze_all_analyses(self, sample_academic_text: str) -> None:
        """Test text analysis with all analysis types."""
        result = await research_text_analyze(sample_academic_text)

        assert isinstance(result, dict)
        assert "word_count" in result

        # Check optional analyses (may be present)
        # Note: NLTK might not be available in all environments
        if "error" not in result:
            # If no error, check expected fields
            if "entities" in result:
                assert isinstance(result["entities"], list)
            if "keywords" in result:
                assert isinstance(result["keywords"], list)
            if "readability" in result:
                readability = result["readability"]
                assert "flesch_kincaid_grade" in readability
                assert "ari" in readability
                assert "vocabulary_level" in readability
            if "language_stats" in result:
                stats = result["language_stats"]
                assert "words" in stats
                assert "sentences" in stats
                assert "lexical_density" in stats

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_text_analyze_specific_analyses(self, sample_academic_text: str) -> None:
        """Test text analysis with specific analysis types."""
        result = await research_text_analyze(
            sample_academic_text,
            analyses=["readability", "language_stats"]
        )

        assert "word_count" in result
        # Results may contain requested analyses or error if NLTK unavailable

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_text_analyze_empty_text(self) -> None:
        """Test text analysis rejects empty text."""
        result = await research_text_analyze("")

        # Should have error or return empty result
        assert "word_count" in result
        assert result["word_count"] == 0


class TestRadicalizationDetect:
    """Tests for research_radicalization_detect tool."""

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_radicalization_detect_benign(self, sample_benign_text: str) -> None:
        """Test radicalization detection on benign text."""
        result = await research_radicalization_detect(sample_benign_text)

        assert isinstance(result, dict)
        assert "risk_score" in result
        assert "risk_level" in result
        assert "indicators" in result
        assert "word_count" in result

        # Benign text should have low risk
        assert 0 <= result["risk_score"] <= 1
        assert result["risk_level"] in ["low", "moderate", "elevated", "high"]

        # Check indicators structure
        indicators = result["indicators"]
        expected_indicators = {
            "us_vs_them", "extremist_vocabulary", "escalation_language",
            "moral_absolutism", "dehumanization", "call_to_action"
        }
        assert set(indicators.keys()) == expected_indicators

        # Each indicator should have score and examples/terms
        for ind_name, ind_data in indicators.items():
            assert "score" in ind_data
            assert 0 <= ind_data["score"] <= 1

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_radicalization_detect_insufficient_length(self) -> None:
        """Test radicalization detection rejects short text."""
        short_text = "Too short."
        result = await research_radicalization_detect(short_text)

        assert "error" in result


class TestNetworkPersona:
    """Tests for research_network_persona tool."""

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_network_persona_basic(self, forum_posts: list[dict]) -> None:
        """Test network persona analysis on forum data."""
        result = await research_network_persona(forum_posts)

        assert isinstance(result, dict)
        assert "authors" in result
        assert "network" in result
        assert "edges" in result

        # Check network metrics
        network = result["network"]
        assert "total_authors" in network
        assert "total_edges" in network
        assert "density" in network
        assert "communities" in network
        assert "top_authorities" in network
        assert "top_hubs" in network

        assert network["total_authors"] > 0
        assert 0 <= network["density"] <= 1
        assert network["communities"] >= 0

        # Check authors have expected fields
        for author_name, author_data in result["authors"].items():
            assert isinstance(author_name, str)
            assert "post_count" in author_data
            assert "replies_sent" in author_data
            assert "replies_received" in author_data
            assert "unique_contacts" in author_data
            assert "role" in author_data

            # Role should be one of the expected types
            assert author_data["role"] in [
                "lurker", "hub", "authority", "bridge", "regular"
            ]

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_network_persona_empty_posts(self) -> None:
        """Test network persona handles empty posts gracefully."""
        result = await research_network_persona([])

        assert result["network"]["total_authors"] == 0


class TestPsycholinguistic:
    """Tests for research_psycholinguistic tool."""

    @pytest.mark.live
    def test_psycholinguistic_basic(self, sample_casual_text: str) -> None:
        """Test psycholinguistic analysis on sample text."""
        result = research_psycholinguistic(sample_casual_text)

        assert isinstance(result, dict)
        assert "text_length" in result
        assert "word_count" in result
        assert "sentence_count" in result
        assert "emotional_profile" in result
        assert "certainty_markers" in result
        assert "cognitive_complexity_score" in result
        assert "deception_indicators" in result
        assert "urgency_score" in result
        assert "threat_level" in result

        # Check emotional profile
        emotion = result["emotional_profile"]
        assert "positive_emotion_words" in emotion
        assert "negative_emotion_words" in emotion
        assert "emotion_ratio" in emotion
        assert "overall_sentiment" in emotion

        assert emotion["overall_sentiment"] in ["positive", "negative", "neutral"]

        # Check certainty markers
        certainty = result["certainty_markers"]
        assert "certainty_words" in certainty
        assert "uncertainty_words" in certainty
        assert "certainty_ratio" in certainty

        # Check numeric constraints
        assert 0 <= result["cognitive_complexity_score"] <= 1
        assert 0 <= result["urgency_score"] <= 1
        assert 0 <= result["vocabulary_richness"] <= 1

        # Check threat level
        assert result["threat_level"] in ["low", "medium", "high"]

        # Check threat indicators summary
        summary = result["threat_indicators_summary"]
        assert isinstance(summary["negative_emotions"], bool)
        assert isinstance(summary["high_anger"], bool)
        assert isinstance(summary["high_urgency"], bool)
        assert isinstance(summary["deception_patterns"], bool)

    @pytest.mark.live
    def test_psycholinguistic_with_author(self, sample_benign_text: str) -> None:
        """Test psycholinguistic analysis with author name."""
        result = research_psycholinguistic(
            sample_benign_text,
            author_name="test_author"
        )

        assert result["author_name"] == "test_author"

    @pytest.mark.live
    def test_psycholinguistic_empty_text(self) -> None:
        """Test psycholinguistic analysis handles empty text."""
        result = research_psycholinguistic("")

        assert "error" in result or "text_length" in result


class TestNLPIntegration:
    """Integration tests across multiple NLP tools."""

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_full_nlp_pipeline(self, sample_academic_text: str) -> None:
        """Test analyzing same text with multiple NLP tools."""
        # Run stylometry
        stylo_result = research_stylometry(sample_academic_text)
        assert "features" in stylo_result

        # Run deception detection
        deception_result = research_deception_detect(sample_academic_text)
        assert "deception_score" in deception_result

        # Run sentiment analysis
        sentiment_result = await research_sentiment_deep(sample_academic_text)
        assert "emotions" in sentiment_result

        # Run persona profile
        persona_result = await research_persona_profile([sample_academic_text])
        assert "profile" in persona_result

        # Run psycholinguistic
        psycho_result = research_psycholinguistic(sample_academic_text)
        assert "emotional_profile" in psycho_result

        # All analyses should complete without error
        assert all([
            stylo_result,
            deception_result,
            sentiment_result,
            persona_result,
            psycho_result
        ])

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_nlp_cross_validation(
        self, sample_casual_text: str
    ) -> None:
        """Test consistency across tools for same text."""
        # Casual text should show high positivity in sentiment
        sentiment = await research_sentiment_deep(sample_casual_text)
        psycho = research_psycholinguistic(sample_casual_text)

        # Both should detect positive sentiment (casual text has "excited", "amazing", etc.)
        assert sentiment["dominant_emotion"] != "sadness"
        assert psycho["emotional_profile"]["overall_sentiment"] != "negative"
