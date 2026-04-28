"""Unit tests for research_text_analyze — NLP text analysis using NLTK."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from loom.tools.text_analyze import (
    research_text_analyze,
    _count_syllables,
    _extract_entities,
    _extract_keywords,
    _compute_readability,
    _compute_language_stats,
)


class TestTextAnalyze:
    """research_text_analyze performs NLP analysis on text."""

    @pytest.mark.asyncio
    async def test_text_analyze_nltk_not_available(self) -> None:
        """Tool returns error when NLTK not installed."""
        with patch("loom.tools.text_analyze._HAS_NLTK", False):
            result = await research_text_analyze(text="Some text here")

            assert "error" in result
            assert "not installed" in result["error"]
            assert result["word_count"] == 0

    @pytest.mark.asyncio
    async def test_text_analyze_empty_text(self) -> None:
        """Tool rejects empty text."""
        result = await research_text_analyze(text="")

        assert "error" in result
        assert "must be at least" in result["error"]

    @pytest.mark.asyncio
    async def test_text_analyze_text_too_long(self) -> None:
        """Tool rejects text exceeding 100,000 characters."""
        long_text = "x" * 100001
        result = await research_text_analyze(text=long_text)

        assert "error" in result
        assert "exceeds" in result["error"]

    @pytest.mark.asyncio
    async def test_text_analyze_all_analyses(self) -> None:
        """Tool runs all analyses when none specified."""
        text = "The quick brown fox jumps over the lazy dog. This is a test sentence."

        with patch("loom.tools.text_analyze._HAS_NLTK", True):
            with patch("loom.tools.text_analyze.word_tokenize") as mock_tokenize:
                mock_tokenize.return_value = text.split()

                with patch("loom.tools.text_analyze._extract_entities") as mock_entities:
                    mock_entities.return_value = []

                    with patch(
                        "loom.tools.text_analyze._extract_keywords"
                    ) as mock_keywords:
                        mock_keywords.return_value = [
                            {"term": "quick", "frequency": 1, "tfidf": 0.1}
                        ]

                        with patch(
                            "loom.tools.text_analyze._compute_readability"
                        ) as mock_readability:
                            mock_readability.return_value = {
                                "flesch_kincaid_grade": 8.5,
                                "ari": 7.2,
                                "avg_syllables": 1.5,
                                "vocabulary_level": "high",
                            }

                            with patch(
                                "loom.tools.text_analyze._compute_language_stats"
                            ) as mock_stats:
                                mock_stats.return_value = {
                                    "words": 14,
                                    "sentences": 2,
                                    "paragraphs": 1,
                                    "avg_words_per_sentence": 7.0,
                                    "lexical_density": 0.85,
                                    "unique_words": 13,
                                    "most_common_words": [],
                                }

                                result = await research_text_analyze(text=text)

                                assert "entities" in result
                                assert "keywords" in result
                                assert "readability" in result
                                assert "language_stats" in result
                                assert result["word_count"] > 0

    @pytest.mark.asyncio
    async def test_text_analyze_selective_analyses(self) -> None:
        """Tool runs only requested analyses."""
        text = "Test text for analysis purposes"

        with patch("loom.tools.text_analyze._HAS_NLTK", True):
            with patch("loom.tools.text_analyze.word_tokenize") as mock_tokenize:
                mock_tokenize.return_value = text.split()

                with patch(
                    "loom.tools.text_analyze._extract_keywords"
                ) as mock_keywords:
                    mock_keywords.return_value = [
                        {"term": "test", "frequency": 1, "tfidf": 0.1}
                    ]

                    result = await research_text_analyze(
                        text=text, analyses=["keywords"]
                    )

                    assert "keywords" in result
                    assert "entities" not in result
                    assert "readability" not in result

    def test_syllable_count_simple(self) -> None:
        """Syllable counter works for simple words."""
        assert _count_syllables("cat") == 1
        assert _count_syllables("hello") == 2
        assert _count_syllables("beautiful") == 3
        assert _count_syllables("science") == 2

    def test_syllable_count_silent_e(self) -> None:
        """Syllable counter adjusts for silent e."""
        assert _count_syllables("make") == 1
        assert _count_syllables("take") == 1

    def test_syllable_count_minimum_one(self) -> None:
        """Syllable counter returns minimum 1."""
        assert _count_syllables("a") >= 1
        assert _count_syllables("b") >= 1

    @pytest.mark.skipif(
        True, reason="Requires NLTK data which may not be available in test env"
    )
    def test_extract_entities_sample_text(self) -> None:
        """Entity extraction identifies named entities."""
        text = "John Smith works at Google in California."
        entities = _extract_entities(text)

        assert isinstance(entities, list)
        if entities:
            assert "text" in entities[0]
            assert "type" in entities[0]
            assert "count" in entities[0]

    @pytest.mark.skipif(
        True, reason="Requires NLTK data which may not be available in test env"
    )
    def test_extract_keywords_sample_text(self) -> None:
        """Keyword extraction identifies frequent meaningful terms."""
        text = "Machine learning is a subset of artificial intelligence. ML is powerful."
        keywords = _extract_keywords(text)

        assert isinstance(keywords, list)
        if keywords:
            assert "term" in keywords[0]
            assert "frequency" in keywords[0]
            assert "tfidf" in keywords[0]

    def test_compute_readability_simple_text(self) -> None:
        """Readability computes grade level metrics."""
        # Use simple mock to avoid NLTK dependency
        with patch("loom.tools.text_analyze._count_syllables") as mock_syllables:
            mock_syllables.return_value = 1

            with patch("loom.tools.text_analyze.sent_tokenize") as mock_sent:
                mock_sent.return_value = [
                    "This is a test.",
                    "It has two sentences.",
                ]

                with patch("loom.tools.text_analyze.word_tokenize") as mock_word:
                    mock_word.return_value = [
                        "this",
                        "is",
                        "a",
                        "test",
                        "it",
                        "has",
                        "two",
                        "sentences",
                    ]

                    result = _compute_readability(
                        "This is a test. It has two sentences."
                    )

                    assert "flesch_kincaid_grade" in result
                    assert "ari" in result
                    assert "vocabulary_level" in result
                    assert result["vocabulary_level"] in [
                        "elementary",
                        "middle",
                        "high",
                        "advanced",
                    ]

    def test_compute_readability_empty_text(self) -> None:
        """Readability handles empty text."""
        with patch("loom.tools.text_analyze.sent_tokenize") as mock_sent:
            mock_sent.return_value = []

            with patch("loom.tools.text_analyze.word_tokenize") as mock_word:
                mock_word.return_value = []

                result = _compute_readability("")

                assert result["flesch_kincaid_grade"] == 0
                assert result["ari"] == 0
                assert result["vocabulary_level"] == "unknown"

    def test_compute_language_stats_basic(self) -> None:
        """Language stats counts words, sentences, paragraphs."""
        with patch("loom.tools.text_analyze.sent_tokenize") as mock_sent:
            mock_sent.return_value = ["First sentence.", "Second sentence."]

            with patch("loom.tools.text_analyze.word_tokenize") as mock_word:
                mock_word.return_value = [
                    "first",
                    "sentence",
                    "second",
                    "sentence",
                ]

                result = _compute_language_stats(
                    "First sentence.\nSecond sentence."
                )

                assert result["words"] == 4
                assert result["sentences"] == 2
                assert result["paragraphs"] == 2
                assert result["avg_words_per_sentence"] > 0
                assert "lexical_density" in result
                assert "most_common_words" in result

    def test_compute_language_stats_empty(self) -> None:
        """Language stats handles empty text."""
        with patch("loom.tools.text_analyze.sent_tokenize") as mock_sent:
            mock_sent.return_value = []

            with patch("loom.tools.text_analyze.word_tokenize") as mock_word:
                mock_word.return_value = []

                result = _compute_language_stats("")

                assert result["words"] == 0
                assert result["sentences"] == 0
                assert result["lexical_density"] == 0
                assert result["most_common_words"] == []

    @pytest.mark.asyncio
    async def test_text_analyze_error_handling(self) -> None:
        """Tool handles analysis errors gracefully."""
        text = "Valid text for testing"

        with patch("loom.tools.text_analyze._HAS_NLTK", True):
            with patch("loom.tools.text_analyze.word_tokenize") as mock_tokenize:
                mock_tokenize.side_effect = Exception("NLTK error")

                result = await research_text_analyze(text=text)

                assert "error" in result
                # But should still have word_count field
                assert "word_count" in result

    @pytest.mark.asyncio
    async def test_text_analyze_invalid_analysis_type(self) -> None:
        """Tool ignores invalid analysis type names."""
        text = "Test text"

        with patch("loom.tools.text_analyze._HAS_NLTK", True):
            with patch("loom.tools.text_analyze.word_tokenize") as mock_tokenize:
                mock_tokenize.return_value = text.split()

                result = await research_text_analyze(
                    text=text, analyses=["invalid_type", "keywords"]
                )

                # Should run keywords but skip invalid_type
                assert "keywords" in result
                assert "invalid_type" not in result
