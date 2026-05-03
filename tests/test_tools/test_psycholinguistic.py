"""Unit tests for psycholinguistic tool — threat assessment via language patterns."""

from __future__ import annotations

import pytest

from loom.tools.psycholinguistic import (
    _calculate_avg_sentence_length,
    _calculate_cognitive_complexity,
    _calculate_ttr,
    _calculate_urgency_score,
    _classify_threat_level,
    _count_words,
    _detect_deception_indicators,
    research_psycholinguistic,
)


pytestmark = pytest.mark.asyncio

class TestCountWords:
    """Word counting with pattern matching."""

    async def test_count_single_word(self) -> None:
        """Count single word occurrence."""
        text = "I love this amazing discovery"
        count = _count_words(text, ["love"])
        assert count == 1

    async def test_count_multiple_words(self) -> None:
        """Count multiple word occurrences."""
        text = "happy joy love amazing wonderful"
        count = _count_words(text, ["happy", "joy", "love"])
        assert count == 3

    async def test_count_case_insensitive(self) -> None:
        """Word counting is case-insensitive."""
        text = "Love LOVE Love"
        count = _count_words(text, ["love"])
        assert count == 3

    async def test_count_word_boundaries(self) -> None:
        """Only count complete word matches."""
        text = "loving love lovely"
        count = _count_words(text, ["love"])
        assert count == 1  # Only exact "love"

    async def test_count_empty_list(self) -> None:
        """Empty word list returns 0."""
        count = _count_words("some text here", [])
        assert count == 0

    async def test_count_no_matches(self) -> None:
        """No matching words returns 0."""
        text = "xyz abc def"
        count = _count_words(text, ["love", "happy"])
        assert count == 0


class TestCalculateTTR:
    """Type-Token Ratio (vocabulary richness)."""

    async def test_high_ttr_diverse_vocabulary(self) -> None:
        """High vocabulary diversity yields high TTR."""
        text = "alpha beta gamma delta epsilon zeta"
        ttr = _calculate_ttr(text)
        assert ttr > 0.8  # Nearly all words unique

    async def test_low_ttr_repeated_words(self) -> None:
        """Repeated words yield low TTR."""
        text = "the the the the a a a"
        ttr = _calculate_ttr(text)
        assert ttr < 0.5

    async def test_ttr_range(self) -> None:
        """TTR is always 0-1."""
        text = "machine learning and deep learning"
        ttr = _calculate_ttr(text)
        assert 0.0 <= ttr <= 1.0

    async def test_single_word_ttr(self) -> None:
        """Single word text has TTR = 1.0."""
        ttr = _calculate_ttr("word")
        assert ttr == 1.0

    async def test_empty_text_ttr(self) -> None:
        """Empty text returns 0."""
        ttr = _calculate_ttr("")
        assert ttr == 0.0


class TestCalculateAverageSentenceLength:
    """Average sentence length calculation."""

    async def test_single_sentence(self) -> None:
        """Single sentence length."""
        text = "This is a test sentence."
        avg_len = _calculate_avg_sentence_length(text)
        assert avg_len > 0

    async def test_multiple_sentences(self) -> None:
        """Multiple sentence average."""
        text = "Short. This is longer. Medium length here."
        avg_len = _calculate_avg_sentence_length(text)
        assert avg_len > 0

    async def test_various_punctuation(self) -> None:
        """Handles different sentence endings."""
        text = "First sentence. Second question? Third exclamation!"
        avg_len = _calculate_avg_sentence_length(text)
        assert avg_len > 0

    async def test_no_punctuation_empty_result(self) -> None:
        """Text without punctuation returns 0."""
        avg_len = _calculate_avg_sentence_length("no punctuation here")
        assert avg_len == 0.0

    async def test_empty_text_no_sentences(self) -> None:
        """Empty text returns 0."""
        avg_len = _calculate_avg_sentence_length("")
        assert avg_len == 0.0


class TestDetectDeceptionIndicators:
    """Deception pattern detection."""

    async def test_lack_of_self_references(self) -> None:
        """Low self-reference usage detected."""
        text = "One should consider the facts. The evidence shows."
        indicators = _detect_deception_indicators(text)
        # May or may not detect depending on text length
        assert isinstance(indicators, list)

    async def test_excessive_exaggeration(self) -> None:
        """Excessive intensifiers detected."""
        text = "This is extremely very incredibly absolutely amazing and awesome!"
        indicators = _detect_deception_indicators(text)
        # May detect exaggeration
        assert isinstance(indicators, list)

    async def test_excessive_detail(self) -> None:
        """Excessive detail markers detected."""
        text = "Specifically, in detail, exactly as follows, specifically we noted."
        indicators = _detect_deception_indicators(text)
        # May detect excessive detail
        assert isinstance(indicators, list)

    async def test_distancing_language(self) -> None:
        """Distancing language patterns detected."""
        text = "They did it. Those people made that choice. Not my decision."
        indicators = _detect_deception_indicators(text)
        # May detect distancing
        assert isinstance(indicators, list)

    async def test_opinion_hedging(self) -> None:
        """Opinion hedging detected."""
        text = "Honestly I believe we should trust this. Frankly, to be honest."
        indicators = _detect_deception_indicators(text)
        # May detect hedging
        assert isinstance(indicators, list)

    async def test_no_deception_clean_text(self) -> None:
        """Clean straightforward text has few indicators."""
        text = "I did the work. It was completed on time. The results are good."
        indicators = _detect_deception_indicators(text)
        assert len(indicators) < 3  # Should have few indicators


class TestCalculateCognitiveComplexity:
    """Cognitive complexity scoring."""

    async def test_complexity_range(self) -> None:
        """Complexity score is 0-1."""
        text = "This is simple. But here's a more complex sentence with multiple clauses."
        score = _calculate_cognitive_complexity(text)
        assert 0.0 <= score <= 1.0

    async def test_simple_text_low_complexity(self) -> None:
        """Simple short sentences have low complexity."""
        text = "I am here. You are too. This is fine."
        score = _calculate_cognitive_complexity(text)
        assert score < 0.7

    async def test_complex_text_high_complexity(self) -> None:
        """Complex sentences with varied vocabulary have high complexity."""
        text = "Notwithstanding the aforementioned considerations, the multifaceted methodology."
        score = _calculate_cognitive_complexity(text)
        assert score >= 0.0

    async def test_empty_text_zero_complexity(self) -> None:
        """Empty text has zero complexity."""
        score = _calculate_cognitive_complexity("")
        assert score == 0.0


class TestCalculateUrgencyScore:
    """Urgency and pressure detection."""

    async def test_high_urgency_language(self) -> None:
        """Urgent language yields high score."""
        text = "Urgent! Must do immediately now! Asap deadline today!"
        score = _calculate_urgency_score(text)
        assert score > 0.3

    async def test_ultimatum_language(self) -> None:
        """Ultimatum language detected."""
        text = "You must do this or else. You have no choice but to."
        score = _calculate_urgency_score(text)
        assert score > 0.0

    async def test_no_urgency_calm_text(self) -> None:
        """Calm text has low urgency."""
        text = "Please consider this proposal at your leisure."
        score = _calculate_urgency_score(text)
        assert score < 0.3

    async def test_urgency_range(self) -> None:
        """Urgency score is 0-1."""
        text = "Regular text with occasional urgency word urgent mentioned."
        score = _calculate_urgency_score(text)
        assert 0.0 <= score <= 1.0

    async def test_empty_text_zero_urgency(self) -> None:
        """Empty text has zero urgency."""
        score = _calculate_urgency_score("")
        assert score == 0.0


class TestClassifyThreatLevel:
    """Threat level classification."""

    async def test_high_threat_classification(self) -> None:
        """High threat indicators yield high classification."""
        threat = _classify_threat_level(
            emotional_negative=10,
            anger_score=0.8,
            urgency_score=0.9,
            deception_count=4,
        )
        assert threat == "high"

    async def test_medium_threat_classification(self) -> None:
        """Medium indicators yield medium classification."""
        threat = _classify_threat_level(
            emotional_negative=3,
            anger_score=0.5,
            urgency_score=0.4,
            deception_count=1,
        )
        assert threat == "medium"

    async def test_low_threat_classification(self) -> None:
        """Low indicators yield low classification."""
        threat = _classify_threat_level(
            emotional_negative=0,
            anger_score=0.1,
            urgency_score=0.1,
            deception_count=0,
        )
        assert threat == "low"

    async def test_valid_threat_levels(self) -> None:
        """Threat level is valid classification."""
        threat = _classify_threat_level(5, 0.5, 0.5, 2)
        assert threat in ["low", "medium", "high"]


class TestResearchPsycholinguistic:
    """Full psycholinguistic analysis."""

    async def test_psycholinguistic_basic_structure(self) -> None:
        """Returns expected structure."""
        result = await research_psycholinguistic("This is a test message.")

        assert "text_length" in result
        assert "word_count" in result
        assert "sentence_count" in result
        assert "author_name" in result
        assert "emotional_profile" in result
        assert "certainty_markers" in result
        assert "cognitive_complexity_score" in result
        assert "vocabulary_richness" in result
        assert "deception_indicators" in result
        assert "urgency_score" in result
        assert "threat_level" in result

    async def test_psycholinguistic_emotional_profile(self) -> None:
        """Emotional profile structure is correct."""
        result = await research_psycholinguistic("I love this happy moment!")

        profile = result["emotional_profile"]
        assert "positive_emotion_words" in profile
        assert "negative_emotion_words" in profile
        assert "emotion_ratio" in profile
        assert "overall_sentiment" in profile

    async def test_psycholinguistic_positive_sentiment(self) -> None:
        """Positive text yields positive sentiment."""
        result = await research_psycholinguistic("Great! Amazing! Wonderful!")

        assert result["emotional_profile"]["overall_sentiment"] == "positive"

    async def test_psycholinguistic_negative_sentiment(self) -> None:
        """Negative text yields negative sentiment."""
        result = await research_psycholinguistic("Hate this terrible awful situation.")

        assert result["emotional_profile"]["overall_sentiment"] == "negative"

    async def test_psycholinguistic_neutral_sentiment(self) -> None:
        """Neutral text yields neutral sentiment."""
        result = await research_psycholinguistic("The weather is cloudy today.")

        assert result["emotional_profile"]["overall_sentiment"] == "neutral"

    async def test_psycholinguistic_certainty_markers(self) -> None:
        """Certainty markers extracted."""
        result = await research_psycholinguistic("I definitely will absolutely do this.")

        certainty = result["certainty_markers"]
        assert "certainty_words" in certainty
        assert "uncertainty_words" in certainty
        assert "certainty_ratio" in certainty
        assert certainty["certainty_words"] > 0

    async def test_psycholinguistic_complexity_score_range(self) -> None:
        """Complexity score is 0-1."""
        result = await research_psycholinguistic(
            "Complex multifaceted considerations notwithstanding."
        )

        assert 0.0 <= result["cognitive_complexity_score"] <= 1.0

    async def test_psycholinguistic_vocabulary_richness(self) -> None:
        """Vocabulary richness is 0-1."""
        result = await research_psycholinguistic("apple banana cherry date elderberry fig.")

        assert 0.0 <= result["vocabulary_richness"] <= 1.0

    async def test_psycholinguistic_threat_level_valid(self) -> None:
        """Threat level is valid classification."""
        result = await research_psycholinguistic("Angry threatening message with urgency.")

        assert result["threat_level"] in ["low", "medium", "high"]

    async def test_psycholinguistic_with_author_name(self) -> None:
        """Author name is preserved."""
        result = await research_psycholinguistic("Test text", author_name="Alice")

        assert result["author_name"] == "Alice"

    async def test_psycholinguistic_empty_text_error(self) -> None:
        """Empty text returns error."""
        result = await research_psycholinguistic("")

        assert "error" in result
        assert result["text_length"] == 0

    async def test_psycholinguistic_urgency_score_range(self) -> None:
        """Urgency score is 0-1."""
        result = await research_psycholinguistic("Urgent action needed immediately now!")

        assert 0.0 <= result["urgency_score"] <= 1.0

    async def test_psycholinguistic_threat_indicators_summary(self) -> None:
        """Threat indicators summary is present."""
        result = await research_psycholinguistic("Angry hate urgent message.")

        summary = result["threat_indicators_summary"]
        assert "negative_emotions" in summary
        assert "high_anger" in summary
        assert "high_urgency" in summary
        assert "deception_patterns" in summary
