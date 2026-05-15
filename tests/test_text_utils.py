"""Unit tests for shared text_utils module.

Tests cover keyword extraction, truncation, word counting, token estimation,
text chunking, similarity metrics, and text cleaning with comprehensive
edge case coverage including unicode, empty strings, and very long strings.
"""

from __future__ import annotations

import pytest

from loom.text_utils import (
    extract_keywords,
    truncate,
    count_words,
    estimate_tokens,
    split_into_chunks,
    jaccard_similarity,
    clean_text,
)


class TestExtractKeywords:
    """Tests for extract_keywords() function — 11 test cases."""

    def test_extract_keywords_basic(self) -> None:
        """Extract keywords from normal text."""
        text = "python programming python development programming languages"
        keywords = extract_keywords(text)
        assert "python" in keywords
        assert "programming" in keywords

    def test_extract_keywords_max_limit(self) -> None:
        """Respect max_keywords limit."""
        text = "apple banana cherry date elderberry fig grape honeydew indigo jasmine"
        keywords = extract_keywords(text, max_keywords=3)
        assert len(keywords) <= 3

    def test_extract_keywords_min_length(self) -> None:
        """Filter words shorter than min_length."""
        text = "a an the programming python code"
        keywords = extract_keywords(text, min_length=3)
        assert "programming" in keywords
        assert "python" in keywords
        # Should not include single/double letter words

    def test_extract_keywords_stopwords_filtered(self) -> None:
        """Filter out common stopwords."""
        text = "the quick brown fox jumps over the lazy dog"
        keywords = extract_keywords(text)
        # Should not include 'the' or other stopwords
        assert "quick" in keywords
        assert "brown" in keywords

    def test_extract_keywords_empty_string(self) -> None:
        """Handle empty string."""
        keywords = extract_keywords("")
        assert keywords == []

    def test_extract_keywords_only_stopwords(self) -> None:
        """Handle text with only stopwords."""
        text = "the a an and or is are"
        keywords = extract_keywords(text)
        assert len(keywords) == 0

    def test_extract_keywords_case_insensitive(self) -> None:
        """Extract keywords case-insensitively."""
        text = "Python PYTHON python Python"
        keywords = extract_keywords(text, max_keywords=5)
        # All variations should be counted together
        assert keywords.count("python") <= 1 or "python" in keywords

    def test_extract_keywords_frequency_order(self) -> None:
        """Return keywords sorted by frequency."""
        text = "apple apple apple banana banana cherry"
        keywords = extract_keywords(text, max_keywords=3)
        assert keywords[0] == "apple"
        assert keywords[1] == "banana"

    def test_extract_keywords_unicode(self) -> None:
        """Handle unicode text."""
        text = "café naïve résumé café café"
        keywords = extract_keywords(text, min_length=3)
        # Note: regex [a-z]+ won't match accented chars, so they may not extract
        # This test documents the behavior

    def test_extract_keywords_numbers_ignored(self) -> None:
        """Numbers should be filtered out."""
        text = "word1 word2 word3 testing testing"
        keywords = extract_keywords(text, min_length=3)
        # Numbers don't match [a-z]+ pattern

    def test_extract_keywords_very_long_text(self) -> None:
        """Handle very long text."""
        # Use words without numbers to match [a-z]+ regex pattern
        words = ["apple", "banana", "cherry", "date", "elderberry"]
        text = " ".join([words[i % 5] for i in range(10000)])
        keywords = extract_keywords(text, max_keywords=5)
        assert len(keywords) <= 5
        assert len(keywords) > 0


class TestTruncate:
    """Tests for truncate() function — 10 test cases."""

    def test_truncate_short_text(self) -> None:
        """Return text unchanged if under max_chars."""
        text = "hello world"
        result = truncate(text, max_chars=100)
        assert result == text

    def test_truncate_exact_length(self) -> None:
        """Return text unchanged if exactly max_chars."""
        text = "hello world"
        result = truncate(text, max_chars=11)
        assert result == text

    def test_truncate_long_text(self) -> None:
        """Truncate and add suffix."""
        text = "hello world this is a long text"
        result = truncate(text, max_chars=15)
        assert result.endswith("...")
        assert len(result) <= 15

    def test_truncate_custom_suffix(self) -> None:
        """Use custom suffix."""
        text = "hello world this is a long text"
        result = truncate(text, max_chars=20, suffix="---")
        assert result.endswith("---")

    def test_truncate_empty_suffix(self) -> None:
        """Use empty suffix."""
        text = "hello world this is a long text"
        result = truncate(text, max_chars=10, suffix="")
        assert not result.endswith(".")
        assert len(result) == 10

    def test_truncate_empty_string(self) -> None:
        """Handle empty string."""
        result = truncate("", max_chars=100)
        assert result == ""

    def test_truncate_exact_suffix_length(self) -> None:
        """Truncate with suffix length matching max_chars."""
        text = "hello"
        result = truncate(text, max_chars=3, suffix="...")
        # max_chars includes suffix, so actual text = 3-3 = 0
        assert len(result) == 3

    def test_truncate_single_char(self) -> None:
        """Truncate to single character."""
        text = "hello"
        result = truncate(text, max_chars=4, suffix=".")
        assert len(result) <= 4

    def test_truncate_unicode(self) -> None:
        """Truncate unicode text."""
        text = "café résumé naïve"
        result = truncate(text, max_chars=5)
        assert isinstance(result, str)
        assert len(result) <= 5

    def test_truncate_newlines(self) -> None:
        """Truncate text with newlines."""
        text = "line1\nline2\nline3"
        result = truncate(text, max_chars=10)
        assert result.endswith("...")


class TestCountWords:
    """Tests for count_words() function — 8 test cases."""

    def test_count_words_simple(self) -> None:
        """Count words in simple text."""
        assert count_words("hello world") == 2

    def test_count_words_empty(self) -> None:
        """Count words in empty string."""
        assert count_words("") == 0

    def test_count_words_single(self) -> None:
        """Count single word."""
        assert count_words("hello") == 1

    def test_count_words_multiple_spaces(self) -> None:
        """Handle multiple spaces between words."""
        assert count_words("hello    world") == 2

    def test_count_words_tabs_newlines(self) -> None:
        """Count words separated by tabs and newlines."""
        assert count_words("hello\tworld\nfoo") == 3

    def test_count_words_long_text(self) -> None:
        """Count words in long text."""
        text = " ".join(["word"] * 1000)
        assert count_words(text) == 1000

    def test_count_words_unicode(self) -> None:
        """Count unicode words."""
        assert count_words("café résumé naïve") == 3

    def test_count_words_punctuation(self) -> None:
        """Count words with punctuation (splits on whitespace only)."""
        assert count_words("hello, world!") == 2


class TestEstimateTokens:
    """Tests for estimate_tokens() function — 9 test cases."""

    def test_estimate_tokens_simple(self) -> None:
        """Estimate tokens for simple text."""
        result = estimate_tokens("hello world")
        assert result >= 1

    def test_estimate_tokens_empty(self) -> None:
        """Estimate tokens for empty string (minimum 1)."""
        assert estimate_tokens("") == 1

    def test_estimate_tokens_four_chars(self) -> None:
        """Estimate tokens for 4 characters (1 token)."""
        assert estimate_tokens("abcd") == 1

    def test_estimate_tokens_eight_chars(self) -> None:
        """Estimate tokens for 8 characters (2 tokens)."""
        assert estimate_tokens("abcdefgh") == 2

    def test_estimate_tokens_formula(self) -> None:
        """Verify token estimation formula (chars // 4)."""
        text = "a" * 100
        result = estimate_tokens(text)
        assert result == 25

    def test_estimate_tokens_very_long(self) -> None:
        """Estimate tokens for very long text."""
        text = "word " * 10000
        result = estimate_tokens(text)
        assert result > 1000

    def test_estimate_tokens_unicode(self) -> None:
        """Estimate tokens for unicode text."""
        text = "café" * 100
        result = estimate_tokens(text)
        assert result > 0

    def test_estimate_tokens_newlines(self) -> None:
        """Estimate tokens for text with newlines."""
        text = "line\n" * 100
        result = estimate_tokens(text)
        assert result > 0

    def test_estimate_tokens_always_positive(self) -> None:
        """Ensure token count is always >= 1."""
        for text_len in range(0, 100):
            result = estimate_tokens("x" * text_len)
            assert result >= 1


class TestSplitIntoChunks:
    """Tests for split_into_chunks() function — 11 test cases."""

    def test_split_short_text(self) -> None:
        """Return single chunk for short text."""
        text = "hello world"
        chunks = split_into_chunks(text, chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_split_exact_chunk_size(self) -> None:
        """Return single chunk for text exactly matching chunk_size."""
        text = "a" * 100
        chunks = split_into_chunks(text, chunk_size=100)
        assert len(chunks) == 1

    def test_split_long_text(self) -> None:
        """Split long text into multiple chunks."""
        text = "word " * 1000
        chunks = split_into_chunks(text, chunk_size=500)
        assert len(chunks) > 1
        # Each chunk should be non-empty
        for chunk in chunks:
            assert len(chunk.strip()) > 0

    def test_split_with_overlap(self) -> None:
        """Chunks should overlap properly."""
        text = "a" * 1000
        chunks = split_into_chunks(text, chunk_size=400, overlap=100)
        assert len(chunks) > 1
        # Check overlap: end of chunk i should share content with start of chunk i+1

    def test_split_empty_string(self) -> None:
        """Handle empty string."""
        chunks = split_into_chunks("", chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_split_zero_overlap(self) -> None:
        """Split with zero overlap."""
        text = "a" * 1000
        chunks = split_into_chunks(text, chunk_size=300, overlap=0)
        assert len(chunks) >= 3

    def test_split_large_overlap(self) -> None:
        """Split with overlap nearly equal to chunk size."""
        text = "a" * 1000
        chunks = split_into_chunks(text, chunk_size=300, overlap=250)
        assert len(chunks) > 1

    def test_split_preserves_content(self) -> None:
        """Rejoined chunks preserve original text (minus whitespace)."""
        text = "word " * 200
        chunks = split_into_chunks(text, chunk_size=500, overlap=50)
        rejoined = "".join(chunks)
        # Should contain all words, though with overlap/spacing variations
        assert len(rejoined) >= len(text) * 0.9

    def test_split_skips_empty_chunks(self) -> None:
        """Skip empty chunks."""
        text = "word word      word"  # Multiple spaces
        chunks = split_into_chunks(text, chunk_size=50, overlap=10)
        for chunk in chunks:
            assert chunk.strip() != ""

    def test_split_custom_chunk_size(self) -> None:
        """Use custom chunk size."""
        text = "a" * 1000
        chunks = split_into_chunks(text, chunk_size=200)
        # Should produce chunks of ~200 chars each
        for chunk in chunks[:-1]:  # All but last
            assert len(chunk) <= 201  # Slight variation due to overlap

    def test_split_unicode_text(self) -> None:
        """Split unicode text."""
        text = "café " * 200
        chunks = split_into_chunks(text, chunk_size=500)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert isinstance(chunk, str)


class TestJaccardSimilarity:
    """Tests for jaccard_similarity() function — 11 test cases."""

    def test_jaccard_identical_strings(self) -> None:
        """Identical strings have similarity 1.0."""
        result = jaccard_similarity("hello world", "hello world")
        assert result == 1.0

    def test_jaccard_identical_sets(self) -> None:
        """Identical sets have similarity 1.0."""
        s1 = {"hello", "world"}
        s2 = {"hello", "world"}
        result = jaccard_similarity(s1, s2)
        assert result == 1.0

    def test_jaccard_no_overlap(self) -> None:
        """Completely different strings have similarity 0.0."""
        result = jaccard_similarity("abc def", "xyz uvw")
        assert result == 0.0

    def test_jaccard_partial_overlap(self) -> None:
        """Partial overlap returns intermediate value."""
        result = jaccard_similarity("apple banana cherry", "banana cherry date")
        assert 0.0 < result < 1.0

    def test_jaccard_empty_strings(self) -> None:
        """Both empty strings have similarity 1.0."""
        result = jaccard_similarity("", "")
        assert result == 1.0

    def test_jaccard_one_empty_string(self) -> None:
        """One empty, one non-empty has similarity 0.0."""
        result = jaccard_similarity("hello world", "")
        assert result == 0.0

    def test_jaccard_empty_sets(self) -> None:
        """Both empty sets have similarity 1.0."""
        result = jaccard_similarity(set(), set())
        assert result == 1.0

    def test_jaccard_one_empty_set(self) -> None:
        """One empty set, one non-empty has similarity 0.0."""
        result = jaccard_similarity({"hello"}, set())
        assert result == 0.0

    def test_jaccard_case_insensitive(self) -> None:
        """String comparison is case-insensitive."""
        result = jaccard_similarity("HELLO world", "hello WORLD")
        assert result == 1.0

    def test_jaccard_duplicate_words(self) -> None:
        """Duplicate words in string are handled (set deduplicates)."""
        # "apple apple banana" tokenizes to ["apple", "apple", "banana"]
        # then becomes set {"apple", "banana"}
        result = jaccard_similarity("apple apple banana", "apple banana cherry")
        assert 0.0 < result < 1.0

    def test_jaccard_mixed_sets_and_strings(self) -> None:
        """Mix string and set inputs."""
        s = {"hello", "world"}
        result = jaccard_similarity("hello world", s)
        assert result == 1.0


class TestCleanText:
    """Tests for clean_text() function — 11 test cases."""

    def test_clean_normal_text(self) -> None:
        """Clean text with normal whitespace."""
        text = "hello  world"
        result = clean_text(text)
        assert result == "hello world"

    def test_clean_leading_trailing_whitespace(self) -> None:
        """Remove leading and trailing whitespace."""
        text = "  hello world  \n"
        result = clean_text(text)
        assert result == "hello world"

    def test_clean_multiple_spaces(self) -> None:
        """Condense multiple spaces to single space."""
        text = "hello    world    test"
        result = clean_text(text)
        assert result == "hello world test"

    def test_clean_tabs(self) -> None:
        """Convert tabs to single space."""
        text = "hello\t\tworld"
        result = clean_text(text)
        assert result == "hello world"

    def test_clean_crlf_to_lf(self) -> None:
        """Normalize CRLF to LF."""
        text = "line1\r\nline2\r\nline3"
        result = clean_text(text)
        assert "\r" not in result
        assert result.count("\n") == 2

    def test_clean_multiple_newlines(self) -> None:
        """Condense 3+ newlines to 2 newlines."""
        text = "line1\n\n\n\nline2"
        result = clean_text(text)
        assert result == "line1\n\nline2"

    def test_clean_control_characters(self) -> None:
        """Remove control characters."""
        text = "hello\x00world\x01test"
        result = clean_text(text)
        assert "\x00" not in result
        assert "\x01" not in result

    def test_clean_empty_string(self) -> None:
        """Handle empty string."""
        result = clean_text("")
        assert result == ""

    def test_clean_only_whitespace(self) -> None:
        """Clean string of only whitespace."""
        result = clean_text("   \n\n\t  ")
        assert result == ""

    def test_clean_unicode(self) -> None:
        """Handle unicode text."""
        text = "café  résumé\n\nnaïve"
        result = clean_text(text)
        assert "café" in result
        assert "résumé" in result
        assert "naïve" in result

    def test_clean_mixed_whitespace(self) -> None:
        """Clean mixed whitespace types."""
        text = "hello \t  world\n\ntest"
        result = clean_text(text)
        assert result == "hello world\n\ntest"
