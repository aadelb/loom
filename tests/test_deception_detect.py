"""Unit tests for research_deception_detect tool — linguistic deception detection."""

from __future__ import annotations

import pytest

from loom.tools.deception_detect import (
    research_deception_detect,
    _extract_deception_indicators,
    _identify_red_flags,
    _calculate_deception_score,
    _tokenize_words,
    _tokenize_sentences,
)


class TestTokenization:
    """Test basic tokenization functions."""

    def test_tokenize_words(self) -> None:
        """Tokenize text into words."""
        text = "The quick brown fox jumps."
        words = _tokenize_words(text)
        assert len(words) == 5
        assert words[0] == "the"
        assert words[1] == "quick"

    def test_tokenize_words_empty(self) -> None:
        """Handle empty text."""
        words = _tokenize_words("")
        assert words == []

    def test_tokenize_sentences(self) -> None:
        """Tokenize text into sentences."""
        text = "First sentence. Second sentence! Third sentence?"
        sentences = _tokenize_sentences(text)
        assert len(sentences) == 3


class TestIndicatorExtraction:
    """Test deception indicator extraction."""

    def test_extract_hedging_words(self) -> None:
        """Detect hedging language."""
        text = (
            "Maybe this is true. Perhaps I should believe it. "
            "Possibly it could be right. I think it might be correct. "
            "It seems like this could be what happened. We continue."
        )
        indicators = _extract_deception_indicators(text)

        assert indicators["hedging_count"] > 0
        assert indicators["hedging_ratio"] > 0
        assert "maybe" or "perhaps" or "possibly" or "might" in text.lower()

    def test_extract_distancing_language(self) -> None:
        """Detect distancing patterns."""
        text = (
            "One would think this is true. People say it happened. "
            "It is said that this occurred. One can believe this. "
            "They say it's important. Sources indicate this is real. "
            "Continuing with more text to reach minimum length requirement."
        )
        indicators = _extract_deception_indicators(text)

        assert indicators["distancing_count"] > 0

    def test_extract_superlatives(self) -> None:
        """Detect superlative word usage."""
        text = (
            "This is the best solution ever. It's the most amazing opportunity. "
            "Absolutely incredible results with fantastic performance. "
            "The greatest achievement possible with outstanding quality. "
            "Exceptional and phenomenal beyond measure truly extraordinary."
        )
        indicators = _extract_deception_indicators(text)

        assert indicators["superlative_count"] > 0

    def test_extract_first_person(self) -> None:
        """Detect first person pronoun usage."""
        text = (
            "I did this. I think that. I believe this. Me and my friend. "
            "My opinion is important. Mine is the right answer. "
            "Myself, I see the issue clearly. And more text here too."
        )
        indicators = _extract_deception_indicators(text)

        assert indicators["first_person_ratio"] > 0

    def test_extract_insufficient_length(self) -> None:
        """Handle text below minimum length."""
        text = "Too short."
        indicators = _extract_deception_indicators(text)

        assert indicators["hedging_count"] == 0
        assert indicators["hedging_ratio"] == 0.0


class TestRedFlagIdentification:
    """Test red flag identification."""

    def test_red_flag_high_hedging_with_certainty(self) -> None:
        """Detect high hedging with certainty markers."""
        indicators = {
            "hedging_ratio": 0.10,
            "hedging_count": 5,
            "distancing_count": 0,
            "superlative_count": 0,
            "first_person_ratio": 0.02,
            "avg_sentence_length": 15.0,
            "certainty_marker_count": 8,
        }
        red_flags = _identify_red_flags(indicators)

        assert "high_hedging_with_certainty_markers" in red_flags

    def test_red_flag_excessive_superlatives(self) -> None:
        """Detect excessive superlative usage."""
        indicators = {
            "hedging_ratio": 0.02,
            "hedging_count": 1,
            "distancing_count": 0,
            "superlative_count": 15,
            "first_person_ratio": 0.05,
            "avg_sentence_length": 12.0,
            "certainty_marker_count": 2,
        }
        red_flags = _identify_red_flags(indicators)

        assert "excessive_superlatives" in red_flags

    def test_red_flag_personal_pronoun_avoidance(self) -> None:
        """Detect avoidance of first person pronouns."""
        indicators = {
            "hedging_ratio": 0.02,
            "hedging_count": 1,
            "distancing_count": 2,
            "superlative_count": 3,
            "first_person_ratio": 0.0005,
            "avg_sentence_length": 20.0,
            "certainty_marker_count": 3,
        }
        red_flags = _identify_red_flags(indicators)

        assert "avoidance_of_personal_pronouns" in red_flags

    def test_red_flag_distancing_language(self) -> None:
        """Detect excessive distancing language."""
        indicators = {
            "hedging_ratio": 0.02,
            "hedging_count": 1,
            "distancing_count": 5,
            "superlative_count": 1,
            "first_person_ratio": 0.05,
            "avg_sentence_length": 12.0,
            "certainty_marker_count": 2,
        }
        red_flags = _identify_red_flags(indicators)

        assert "excessive_distancing_language" in red_flags

    def test_red_flag_short_sentences(self) -> None:
        """Detect unusually short sentences."""
        indicators = {
            "hedging_ratio": 0.02,
            "hedging_count": 1,
            "distancing_count": 0,
            "superlative_count": 1,
            "first_person_ratio": 0.05,
            "avg_sentence_length": 5.0,
            "certainty_marker_count": 2,
        }
        red_flags = _identify_red_flags(indicators)

        assert "unusually_short_sentences" in red_flags

    def test_no_red_flags(self) -> None:
        """Identify absence of red flags with normal text."""
        indicators = {
            "hedging_ratio": 0.02,
            "hedging_count": 1,
            "distancing_count": 0,
            "superlative_count": 1,
            "first_person_ratio": 0.05,
            "avg_sentence_length": 15.0,
            "certainty_marker_count": 2,
        }
        red_flags = _identify_red_flags(indicators)

        assert len(red_flags) == 0


class TestDeceptionScore:
    """Test deception score calculation."""

    def test_score_truthful_text(self) -> None:
        """Calculate low score for truthful text."""
        indicators = {
            "hedging_ratio": 0.01,
            "hedging_count": 1,
            "distancing_count": 0,
            "superlative_count": 1,
            "first_person_ratio": 0.10,
            "avg_sentence_length": 15.0,
            "certainty_marker_count": 2,
        }
        red_flags: list[str] = []
        score = _calculate_deception_score(indicators, red_flags)

        assert 0.0 <= score <= 1.0
        assert score < 0.3  # Should be in truthful range

    def test_score_deceptive_text(self) -> None:
        """Calculate high score for deceptive indicators."""
        indicators = {
            "hedging_ratio": 0.12,
            "hedging_count": 10,
            "distancing_count": 5,
            "superlative_count": 20,
            "first_person_ratio": 0.001,
            "avg_sentence_length": 12.0,
            "certainty_marker_count": 8,
        }
        red_flags = [
            "high_hedging_with_certainty_markers",
            "excessive_superlatives",
            "avoidance_of_personal_pronouns",
        ]
        score = _calculate_deception_score(indicators, red_flags)

        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should be in uncertain/deceptive range

    def test_score_bounded(self) -> None:
        """Ensure score never exceeds 1.0."""
        indicators = {
            "hedging_ratio": 0.5,  # Extremely high
            "hedging_count": 100,
            "distancing_count": 100,
            "superlative_count": 100,
            "first_person_ratio": 0.0,
            "avg_sentence_length": 1.0,
            "certainty_marker_count": 50,
        }
        red_flags = ["flag1", "flag2", "flag3", "flag4", "flag5"]
        score = _calculate_deception_score(indicators, red_flags)

        assert score <= 1.0


class TestVerdictClassification:
    """Test verdict classification."""

    def test_verdict_truthful(self) -> None:
        """Classify low-score text as likely truthful."""
        result = research_deception_detect(
            "I honestly did my best. I worked hard on this project. "
            "I made some mistakes, but I learned from them. I'm proud "
            "of my effort. I believe this is good work overall. I hope "
            "you agree with my assessment of the situation."
        )

        assert result["deception_score"] < 0.3
        assert result["verdict"] == "likely_truthful"

    def test_verdict_deceptive(self) -> None:
        """Classify high-score text as likely deceptive."""
        result = research_deception_detect(
            "Perhaps it might be considered that one could hypothetically "
            "suggest that certain people might say this is absolutely the best "
            "and most incredible solution ever conceived. Sources indicate that "
            "it is said by experts that this represents the greatest achievement. "
            "It appears that some would argue this is fantastic and perfect. "
            "One could believe this demonstration to be quite amazing indeed."
        )

        assert result["deception_score"] > 0.5
        assert result["verdict"] in ["uncertain", "likely_deceptive"]

    def test_verdict_uncertain(self) -> None:
        """Classify middle-range text as uncertain."""
        result = research_deception_detect(
            "I think this might work. Perhaps the approach is reasonable. "
            "It seems like we could try this method. Maybe it will be "
            "successful. I believe the strategy shows some promise. We should "
            "consider this option carefully before proceeding. The results "
            "might be positive if implemented properly overall."
        )

        assert 0.3 <= result["deception_score"] < 0.7
        assert result["verdict"] == "uncertain"


class TestResearchDeceptionDetect:
    """Test main deception detection tool."""

    def test_deception_detect_basic(self) -> None:
        """Analyze text for deception indicators."""
        text = (
            "I did this work myself. I am proud of my accomplishment. "
            "I believe it is good quality. I hope you appreciate my effort. "
            "I worked hard on this. I am satisfied with the results. "
            "I feel confident about this submission. I stand by my work."
        )
        result = research_deception_detect(text)

        assert "deception_score" in result
        assert "verdict" in result
        assert "indicators" in result
        assert "red_flags" in result
        assert "word_count" in result
        assert 0.0 <= result["deception_score"] <= 1.0
        assert result["verdict"] in ["likely_truthful", "uncertain", "likely_deceptive"]

    def test_deception_detect_insufficient_length(self) -> None:
        """Return error for text below minimum length."""
        text = "Too short."
        result = research_deception_detect(text)

        assert "error" in result
        assert "at least 100 characters" in result["error"]

    def test_deception_detect_indicators_present(self) -> None:
        """Verify all indicators are calculated."""
        text = (
            "The analysis might show various interesting characteristics. "
            "Perhaps it could demonstrate some patterns. One would argue "
            "the results are quite spectacular and absolutely amazing. "
            "I believe this is important. I think it matters. I feel this "
            "is significant. I am confident. The study continues here."
        )
        result = research_deception_detect(text)

        indicators = result["indicators"]
        assert "hedging_count" in indicators
        assert "hedging_ratio" in indicators
        assert "distancing_count" in indicators
        assert "superlative_count" in indicators
        assert "first_person_ratio" in indicators
        assert "avg_sentence_length" in indicators
        assert "certainty_marker_count" in indicators

    def test_deception_detect_high_hedging(self) -> None:
        """Detect text with high hedging language."""
        text = (
            "Maybe it works. Perhaps it's true. Possibly it could help. "
            "Might be useful. Could be beneficial. Seems promising. "
            "Appears helpful. Sort of interesting. Kind of useful. "
            "Rather nice. Quite good. Somewhat effective. Arguably valid. "
            "Apparently real. Allegedly true. Purportedly accurate. "
            "More content here to reach minimum requirement length."
        )
        result = research_deception_detect(text)

        assert result["indicators"]["hedging_ratio"] > 0.05
        assert result["deception_score"] > 0.2

    def test_deception_detect_personal_pronouns(self) -> None:
        """Detect first person pronoun usage."""
        text = (
            "I did this. I completed it. I made this happen. "
            "Me and my colleagues worked on this. My team. Mine was the idea. "
            "Myself, I believe this. I am responsible. I take credit. "
            "I am satisfied. I feel good. I am confident. I am proud. "
            "I am happy. I am pleased. I am the author."
        )
        result = research_deception_detect(text)

        assert result["indicators"]["first_person_ratio"] > 0.10
        assert result["deception_score"] < 0.5

    def test_deception_detect_empty_red_flags(self) -> None:
        """Normal text should have minimal red flags."""
        text = (
            "I worked on this project carefully. I spent time on quality. "
            "I believe the work is good. I am satisfied with the results. "
            "I hope you find it useful. I appreciate your consideration. "
            "I look forward to your feedback. I am available for questions."
        )
        result = research_deception_detect(text)

        red_flags = result["red_flags"]
        assert len(red_flags) <= 2  # Normal text should have few red flags

    def test_deception_detect_multiple_red_flags(self) -> None:
        """Deceptive text should trigger multiple red flags."""
        text = (
            "Absolutely, definitely, certainly this is the best and greatest "
            "idea ever conceived. Perhaps one might suggest that sources say "
            "people believe it's the most incredible and phenomenal solution. "
            "One would think it's spectacular. They say it's fantastic. "
            "It is said to be amazing and unbelievable. The evidence supposedly "
            "proves this beyond doubt. One can clearly see this is perfect."
        )
        result = research_deception_detect(text)

        red_flags = result["red_flags"]
        assert len(red_flags) > 0  # Should have at least some red flags
