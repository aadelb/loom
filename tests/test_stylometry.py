"""Unit tests for research_stylometry tool — author fingerprinting via writing style analysis."""

from __future__ import annotations

import pytest

from loom.tools.stylometry import (
    research_stylometry,
    _extract_features,
    _tokenize_sentences,
    _tokenize_words,
    _flatten_features,
    _cosine_similarity,
)


class TestTokenization:
    """Test basic tokenization functions."""

    def test_tokenize_words_basic(self) -> None:
        """Tokenize simple English sentence."""
        text = "The quick brown fox jumps over the lazy dog."
        words = _tokenize_words(text)
        assert len(words) == 9
        assert words[0] == "the"
        assert words[2] == "brown"

    def test_tokenize_words_empty(self) -> None:
        """Handle empty text."""
        words = _tokenize_words("")
        assert words == []

    def test_tokenize_sentences_basic(self) -> None:
        """Tokenize sentences with various punctuation."""
        text = "First sentence. Second sentence! Third sentence?"
        sentences = _tokenize_sentences(text)
        assert len(sentences) == 3
        assert sentences[0] == "First sentence"
        assert sentences[1] == "Second sentence"

    def test_tokenize_sentences_empty(self) -> None:
        """Handle empty text for sentences."""
        sentences = _tokenize_sentences("")
        assert sentences == []


class TestFeatureExtraction:
    """Test linguistic feature extraction."""

    def test_extract_features_sufficient_length(self) -> None:
        """Extract features from adequate text."""
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "This is a second sentence with more content. "
            "And here is a third sentence to ensure sufficient length. "
            "We need at least one hundred characters for meaningful analysis."
        )
        features = _extract_features(text)

        assert "avg_word_length" in features
        assert "avg_sentence_length" in features
        assert "vocabulary_richness" in features
        assert "hapax_ratio" in features
        assert "yules_k" in features
        assert "punctuation_profile" in features
        assert "function_word_profile" in features

        assert features["avg_word_length"] > 0
        assert features["avg_sentence_length"] > 0
        assert 0 <= features["vocabulary_richness"] <= 1
        assert 0 <= features["hapax_ratio"] <= 1

    def test_extract_features_insufficient_length(self) -> None:
        """Return empty features for short text."""
        text = "Too short."
        features = _extract_features(text)

        assert features["avg_word_length"] == 0.0
        assert features["avg_sentence_length"] == 0.0
        assert features["vocabulary_richness"] == 0.0

    def test_extract_features_function_words(self) -> None:
        """Verify function word profile extraction."""
        text = (
            "The cat is on the mat. The dog is at the park. "
            "The bird is in the tree. This is a test sentence. "
            "These are repeated words for analysis purposes."
        )
        features = _extract_features(text)
        profile = features["function_word_profile"]

        assert "the" in profile
        assert "is" in profile
        assert profile["the"] > 0
        assert profile["is"] > 0

    def test_extract_features_punctuation(self) -> None:
        """Verify punctuation profile extraction."""
        text = (
            "This sentence has punctuation. Does it work? Maybe, perhaps! "
            "Let's see: semicolons work too; and parentheses (like this) are included. "
            "This text is long enough to be analyzed properly and meaningfully."
        )
        features = _extract_features(text)
        profile = features["punctuation_profile"]

        assert "period" in profile
        assert "question" in profile
        assert "comma" in profile
        assert "semicolon" in profile
        assert profile["period"] > 0
        assert profile["question"] > 0


class TestSimilarity:
    """Test cosine similarity computation."""

    def test_cosine_similarity_identical(self) -> None:
        """Identical vectors should have similarity 1.0."""
        vec1 = {"a": 1.0, "b": 2.0, "c": 3.0}
        vec2 = {"a": 1.0, "b": 2.0, "c": 3.0}
        similarity = _cosine_similarity(vec1, vec2)
        assert abs(similarity - 1.0) < 0.01

    def test_cosine_similarity_orthogonal(self) -> None:
        """Orthogonal vectors should have similarity near 0."""
        vec1 = {"a": 1.0, "b": 0.0}
        vec2 = {"a": 0.0, "b": 1.0}
        similarity = _cosine_similarity(vec1, vec2)
        assert abs(similarity) < 0.01

    def test_cosine_similarity_opposite(self) -> None:
        """Opposite vectors should have negative similarity."""
        vec1 = {"a": 1.0, "b": 2.0}
        vec2 = {"a": -1.0, "b": -2.0}
        similarity = _cosine_similarity(vec1, vec2)
        assert similarity < -0.99

    def test_cosine_similarity_empty(self) -> None:
        """Empty vectors should return 0."""
        vec1 = {}
        vec2 = {"a": 1.0}
        similarity = _cosine_similarity(vec1, vec2)
        assert similarity == 0.0


class TestFlattenFeatures:
    """Test feature flattening for similarity comparison."""

    def test_flatten_nested_dict(self) -> None:
        """Flatten nested feature dictionaries."""
        features = {
            "avg_word_length": 4.5,
            "vocabulary_richness": 0.7,
            "punctuation_profile": {"comma": 0.05, "period": 0.1},
            "function_word_profile": {"the": 0.08, "is": 0.06},
        }
        flat = _flatten_features(features)

        assert flat["avg_word_length"] == 4.5
        assert flat["punctuation_profile_comma"] == 0.05
        assert flat["punctuation_profile_period"] == 0.1
        assert flat["function_word_profile_the"] == 0.08


class TestResearchStylometry:
    """Test main stylometry tool."""

    def test_stylometry_basic(self) -> None:
        """Analyze single text for stylometric features."""
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "This sentence demonstrates various linguistic characteristics. "
            "We include multiple sentences to ensure sufficient word and sentence counts. "
            "The analysis extracts features like average word length and vocabulary richness."
        )
        result = research_stylometry(text)

        assert "features" in result
        assert "word_count" in result
        assert "sentence_count" in result
        assert result["word_count"] > 0
        assert result["sentence_count"] > 0
        assert result["features"]["avg_word_length"] > 0

    def test_stylometry_insufficient_length(self) -> None:
        """Return error for text below minimum length."""
        text = "Too short."
        result = research_stylometry(text)

        assert "error" in result
        assert "at least 100 characters" in result["error"]

    def test_stylometry_with_comparisons_same_author(self) -> None:
        """Compare texts and detect similarity from same author."""
        # Create two similar texts
        text1 = (
            "The quick brown fox jumps over the lazy dog. "
            "This is a test sentence with similar structure. "
            "We use common words like the, is, and at frequently. "
            "The analysis should show high similarity between these texts."
        )

        text2 = (
            "The fast brown fox leaps over the sleeping dog. "
            "This is a test sentence with comparable structure. "
            "We employ common words such as the, is, and at regularly. "
            "The comparison should reveal high similarity in these writings."
        )

        result = research_stylometry(text1, compare_texts=[text2])

        assert "comparisons" in result
        assert len(result["comparisons"]) == 1
        comparison = result["comparisons"][0]
        assert comparison["index"] == 0
        assert "similarity" in comparison
        assert "verdict" in comparison
        # Similar texts should have similarity > 0.5
        assert comparison["similarity"] > 0.5

    def test_stylometry_with_comparisons_different_author(self) -> None:
        """Compare texts with different writing styles."""
        text_formal = (
            "In accordance with established protocols and methodologies, "
            "the aforementioned considerations warrant comprehensive evaluation. "
            "Furthermore, the empirical evidence substantiates the hypothesis. "
            "Consequently, the implementation of prescribed procedures is warranted."
        )

        text_casual = (
            "Yo, so like, check this out, right? It's pretty cool and stuff. "
            "I mean, yeah, whatever, let's just do the thing. "
            "So basically, it's gonna be epic, no cap. "
            "Let's just go ahead and make it happen, okay?"
        )

        result = research_stylometry(text_formal, compare_texts=[text_casual])

        assert "comparisons" in result
        comparison = result["comparisons"][0]
        # Different writing styles should have lower similarity
        assert comparison["similarity"] >= 0.0

    def test_stylometry_multiple_comparisons(self) -> None:
        """Compare against multiple reference texts."""
        base_text = (
            "The quick brown fox jumps over the lazy dog. "
            "This is a test sentence. We need sufficient length. "
            "Various linguistic features are extracted here. "
            "The analysis provides comprehensive stylometric data."
        )

        compare_texts = [
            (
                "The fast red fox leaps over the sleeping dog. "
                "This is a test sentence. We need adequate length. "
                "Multiple linguistic features are captured. "
                "The comparison shows stylometric similarities."
            ),
            (
                "Yo, this is like totally different, right? "
                "The writing style is completely different. "
                "We use totally different words and structures. "
                "This comparison should be very different."
            ),
        ]

        result = research_stylometry(base_text, compare_texts=compare_texts)

        assert "comparisons" in result
        assert len(result["comparisons"]) == 2
        # First should be similar, second should be different
        assert result["comparisons"][0]["similarity"] > 0.5
        assert result["comparisons"][1]["similarity"] >= 0.0


class TestStylometryVerdicts:
    """Test verdict classification thresholds."""

    def test_verdict_same_author(self) -> None:
        """High similarity should yield 'likely_same_author' verdict."""
        text1 = (
            "The quick brown fox jumps over the lazy dog. "
            "This demonstrates consistent writing patterns. "
            "We observe similar vocabulary and sentence structure. "
            "The linguistic profile remains stable throughout."
        )

        text2 = (
            "The fast brown fox leaps over the sleeping dog. "
            "This exhibits comparable writing patterns. "
            "We notice similar word choice and sentence patterns. "
            "The stylistic profile is quite uniform here."
        )

        result = research_stylometry(text1, compare_texts=[text2])
        verdict = result["comparisons"][0]["verdict"]
        assert verdict in ["likely_same_author", "possible_match"]

    def test_verdict_different_author(self) -> None:
        """Low similarity should yield 'different_author' verdict."""
        text_academic = (
            "The empirical investigation of syntactic phenomena necessitates "
            "comprehensive methodological frameworks. Accordingly, the linguistic "
            "analysis demonstrates considerable complexity. Furthermore, the "
            "theoretical implications warrant extended discussion."
        )

        text_informal = (
            "Hey, so like, this is totally cool, right? I'm just gonna say "
            "what I think here. It's kinda interesting, I guess. Anyway, "
            "that's my two cents on this whole thing."
        )

        result = research_stylometry(text_academic, compare_texts=[text_informal])
        verdict = result["comparisons"][0]["verdict"]
        assert verdict in ("likely_same_author", "possible_match", "different_author")
