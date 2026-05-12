"""Tests for text_utils module."""

from __future__ import annotations

import pytest

from loom.text_utils import (
    clean_text,
    count_words,
    estimate_tokens,
    extract_keywords,
    jaccard_similarity,
    split_into_chunks,
    truncate,
)


class TestExtractKeywords:
    """Test keyword extraction."""

    def test_empty_text(self) -> None:
        """Empty text returns no keywords."""
        assert extract_keywords("") == []

    def test_single_word(self) -> None:
        """Single valid word is extracted."""
        assert extract_keywords("research") == ["research"]

    def test_filters_stopwords(self) -> None:
        """Common stopwords are filtered out."""
        text = "the quick brown fox is a fast animal"
        keywords = extract_keywords(text)
        assert "the" not in keywords
        assert "a" not in keywords
        assert "is" not in keywords
        assert "quick" in keywords
        assert "brown" in keywords

    def test_min_length_filter(self) -> None:
        """Words shorter than min_length are filtered."""
        text = "a big brown fox"
        keywords = extract_keywords(text, min_length=4)
        assert "big" not in keywords  # 3 chars
        assert "brown" in keywords  # 5 chars

    def test_respects_max_keywords(self) -> None:
        """Returns at most max_keywords items."""
        text = "cat dog bird fish fish fish cat cat cat"
        keywords = extract_keywords(text, max_keywords=2)
        assert len(keywords) == 2

    def test_frequency_order(self) -> None:
        """Keywords are ordered by frequency."""
        text = "cat cat dog bird bird bird"
        keywords = extract_keywords(text, max_keywords=3)
        # bird appears 3 times, cat 2, dog 1
        assert keywords[0] == "bird"
        assert keywords[1] == "cat"
        assert keywords[2] == "dog"

    def test_case_insensitive(self) -> None:
        """Keyword extraction is case-insensitive."""
        text = "Research RESEARCH ReSeArCh"
        keywords = extract_keywords(text)
        # All three should be counted as same word
        assert keywords.count("research") == 1


class TestTruncate:
    """Test text truncation."""

    def test_short_text_unmodified(self) -> None:
        """Text shorter than max_chars is returned unchanged."""
        text = "hello world"
        assert truncate(text, max_chars=50) == text

    def test_exact_length_unmodified(self) -> None:
        """Text exactly at max_chars is returned unchanged."""
        text = "hello"
        assert truncate(text, max_chars=5) == text

    def test_long_text_truncated(self) -> None:
        """Text longer than max_chars is truncated."""
        text = "hello world this is a test"
        result = truncate(text, max_chars=10)
        assert len(result) <= 10
        assert result.endswith("...")

    def test_custom_suffix(self) -> None:
        """Custom suffix is used when truncating."""
        text = "hello world test"
        result = truncate(text, max_chars=10, suffix="[cut]")
        assert result.endswith("[cut]")
        assert len(result) <= 10

    def test_zero_max_chars(self) -> None:
        """Zero max_chars results in suffix only."""
        text = "hello"
        result = truncate(text, max_chars=3, suffix="...")
        assert result == "..."


class TestCountWords:
    """Test word counting."""

    def test_empty_string(self) -> None:
        """Empty string has zero words."""
        assert count_words("") == 0

    def test_single_word(self) -> None:
        """Single word is counted."""
        assert count_words("hello") == 1

    def test_multiple_words(self) -> None:
        """Multiple words are counted correctly."""
        assert count_words("hello world test") == 3

    def test_extra_whitespace(self) -> None:
        """Extra whitespace is handled correctly."""
        assert count_words("hello    world") == 2

    def test_tabs_and_newlines(self) -> None:
        """Tabs and newlines count as word separators."""
        assert count_words("hello\tworld\ntest") == 3


class TestEstimateTokens:
    """Test token estimation."""

    def test_empty_string(self) -> None:
        """Empty string estimates to 1 token (minimum)."""
        assert estimate_tokens("") == 1

    def test_rough_approximation(self) -> None:
        """Token estimate is roughly text_length / 4."""
        # 8 chars -> ~2 tokens
        assert estimate_tokens("hello wo") == 2
        # 400 chars -> ~100 tokens
        assert estimate_tokens("x" * 400) == 100

    def test_minimum_one_token(self) -> None:
        """Estimate is always at least 1."""
        assert estimate_tokens("a") == 1
        assert estimate_tokens("ab") == 1
        assert estimate_tokens("abc") == 1


class TestSplitIntoChunks:
    """Test text chunking."""

    def test_short_text_single_chunk(self) -> None:
        """Text shorter than chunk_size returns single chunk."""
        text = "hello world"
        chunks = split_into_chunks(text, chunk_size=100, overlap=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self) -> None:
        """Long text is split into multiple chunks."""
        text = "a" * 1000
        chunks = split_into_chunks(text, chunk_size=200, overlap=50)
        assert len(chunks) > 1
        # Each chunk should be at most chunk_size
        for chunk in chunks:
            assert len(chunk) <= 200

    def test_overlap_preservation(self) -> None:
        """Overlapping chunks share boundary content."""
        text = "0123456789" * 10  # 100 chars
        chunks = split_into_chunks(text, chunk_size=30, overlap=10)
        assert len(chunks) > 1
        # Check that consecutive chunks overlap
        chunk1 = chunks[0]
        chunk2 = chunks[1]
        # Last 10 chars of chunk1 should appear near start of chunk2
        overlap_text = chunk1[-10:]
        assert overlap_text in chunk2[:15]

    def test_empty_text_single_chunk(self) -> None:
        """Empty text returns single empty chunk (after strip)."""
        text = ""
        chunks = split_into_chunks(text, chunk_size=100, overlap=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_whitespace_chunks_skipped(self) -> None:
        """Chunks that are only whitespace are skipped."""
        text = "hello" + " " * 100 + "world"
        chunks = split_into_chunks(text, chunk_size=30, overlap=5)
        # Should have content chunks, not whitespace-only chunks
        for chunk in chunks:
            assert chunk.strip()  # Should have non-whitespace content


class TestJaccardSimilarity:
    """Test Jaccard similarity calculation."""

    def test_identical_strings(self) -> None:
        """Identical strings have similarity 1.0."""
        assert jaccard_similarity("hello world", "hello world") == 1.0

    def test_completely_different_strings(self) -> None:
        """Completely different strings have similarity 0.0."""
        assert jaccard_similarity("aaa bbb", "xxx yyy") == 0.0

    def test_partial_overlap(self) -> None:
        """Partially overlapping strings have 0 < similarity < 1."""
        sim = jaccard_similarity("hello world test", "hello world foo")
        assert 0.0 < sim < 1.0
        # Both share "hello world" (2 words)
        # Union is "hello world test foo" (4 words)
        # Similarity = 2/4 = 0.5
        assert sim == pytest.approx(0.5)

    def test_both_empty_sets(self) -> None:
        """Both empty sets have similarity 1.0."""
        assert jaccard_similarity(set(), set()) == 1.0
        assert jaccard_similarity("", "") == 1.0

    def test_one_empty_set(self) -> None:
        """One empty, one non-empty set have similarity 0.0."""
        assert jaccard_similarity(set(), {"a", "b"}) == 0.0
        assert jaccard_similarity("", "hello world") == 0.0

    def test_with_sets_directly(self) -> None:
        """Can pass sets directly instead of strings."""
        set1 = {"apple", "banana", "cherry"}
        set2 = {"apple", "banana", "date"}
        # Intersection: {apple, banana} = 2
        # Union: {apple, banana, cherry, date} = 4
        # Similarity = 2/4 = 0.5
        assert jaccard_similarity(set1, set2) == pytest.approx(0.5)

    def test_case_insensitive(self) -> None:
        """String similarity is case-insensitive."""
        sim1 = jaccard_similarity("Hello World", "hello world")
        sim2 = jaccard_similarity("HELLO WORLD", "hello world")
        assert sim1 == 1.0
        assert sim2 == 1.0


class TestCleanText:
    """Test text cleaning."""

    def test_removes_control_chars(self) -> None:
        """Control characters are removed."""
        text = "hello\x00world\x01test"
        result = clean_text(text)
        assert "\x00" not in result
        assert "\x01" not in result
        assert "hello" in result
        assert "world" in result

    def test_normalizes_line_endings(self) -> None:
        """CRLF line endings are converted to LF."""
        text = "hello\r\nworld\r\ntest"
        result = clean_text(text)
        assert "\r" not in result
        assert "hello\nworld\ntest" in result

    def test_condenses_spaces(self) -> None:
        """Multiple spaces are condensed to single space."""
        text = "hello    world   test"
        result = clean_text(text)
        assert result == "hello world test"

    def test_condenses_tabs(self) -> None:
        """Multiple tabs are condensed to single space."""
        text = "hello\t\t\tworld"
        result = clean_text(text)
        assert result == "hello world"

    def test_condenses_newlines(self) -> None:
        """Multiple newlines (3+) are condensed to double newline."""
        text = "hello\n\n\n\nworld"
        result = clean_text(text)
        assert result == "hello\n\nworld"

    def test_preserves_single_newlines(self) -> None:
        """Single newlines are preserved."""
        text = "hello\nworld"
        result = clean_text(text)
        assert result == "hello\nworld"

    def test_preserves_double_newlines(self) -> None:
        """Double newlines are preserved."""
        text = "hello\n\nworld"
        result = clean_text(text)
        assert result == "hello\n\nworld"

    def test_trims_whitespace(self) -> None:
        """Leading and trailing whitespace is trimmed."""
        text = "   hello world   "
        result = clean_text(text)
        assert result == "hello world"

    def test_full_example(self) -> None:
        """Complex example with all transformations."""
        text = "  hello\r\n\n\n\nworld  \x00test\t\t\ttab  "
        result = clean_text(text)
        # Should have:
        # - No leading/trailing whitespace
        # - No control chars
        # - LF instead of CRLF
        # - Condensed newlines (3+ -> 2)
        # - Condensed spaces/tabs
        assert result == "hello\n\nworld test tab"


@pytest.mark.parametrize("text,expected", [
    ("", []),
    ("hello", ["hello"]),
    ("the quick brown fox", ["quick", "brown", "fox"]),
])
def test_extract_keywords_parametrized(text: str, expected: list[str]) -> None:
    """Parametrized tests for keyword extraction."""
    result = extract_keywords(text)
    for keyword in expected:
        assert keyword in result


@pytest.mark.parametrize("text,max_chars,expected_len", [
    ("hello", 10, 5),  # Shorter than max_chars
    ("hello world", 5, 5),  # Truncated to max_chars
    ("test", 4, 4),  # Exact match
])
def test_truncate_parametrized(text: str, max_chars: int, expected_len: int) -> None:
    """Parametrized tests for truncation."""
    result = truncate(text, max_chars)
    assert len(result) <= max_chars
