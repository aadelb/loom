"""Tests for llm_parsers module.

Tests extract_json, extract_list, and extract_score functions.
"""

from __future__ import annotations

import pytest

from loom.llm_parsers import extract_json, extract_json_or_default, extract_list, extract_score


class TestExtractJson:
    """Test extract_json function."""

    def test_extract_json_direct_parse(self) -> None:
        """Test extracting JSON that parses directly."""
        text = '{"key": "value", "number": 42}'
        result = extract_json(text)
        assert result == {"key": "value", "number": 42}

    def test_extract_json_direct_array(self) -> None:
        """Test extracting JSON array that parses directly."""
        text = '[1, 2, 3, 4, 5]'
        result = extract_json(text)
        assert result == [1, 2, 3, 4, 5]

    def test_extract_json_fenced_block(self) -> None:
        """Test extracting JSON from markdown fenced block."""
        text = 'Here is some JSON:\n```json\n{"result": "success"}\n```\nEnd.'
        result = extract_json(text)
        assert result == {"result": "success"}

    def test_extract_json_fenced_without_json_label(self) -> None:
        """Test extracting JSON from fenced block without json label."""
        text = '```\n{"data": 123}\n```'
        result = extract_json(text)
        assert result == {"data": 123}

    def test_extract_json_trailing_comma(self) -> None:
        """Test extracting JSON with trailing commas."""
        text = '{"items": [1, 2,], "key": "value",}'
        result = extract_json(text)
        assert result == {"items": [1, 2], "key": "value"}

    def test_extract_json_fenced_trailing_comma(self) -> None:
        """Test extracting JSON from fenced block with trailing commas."""
        text = '```json\n{"a": 1,}\n```'
        result = extract_json(text)
        assert result == {"a": 1}

    def test_extract_json_boundary_detection_object(self) -> None:
        """Test extracting JSON via boundary detection for object."""
        text = 'The answer is {"found": true} in the middle'
        result = extract_json(text)
        assert result == {"found": true}

    def test_extract_json_boundary_detection_array(self) -> None:
        """Test extracting JSON via boundary detection for array."""
        text = 'Array: [10, 20, 30] here'
        result = extract_json(text)
        assert result == [10, 20, 30]

    def test_extract_json_prefers_object_over_array(self) -> None:
        """Test that objects are preferred over arrays when both present."""
        text = 'Check this: {"arr": [1, 2]} and [3, 4]'
        result = extract_json(text)
        # Should find the object with array inside, not the top-level array
        assert isinstance(result, dict)
        assert result == {"arr": [1, 2]}

    def test_extract_json_nested_objects(self) -> None:
        """Test extracting nested JSON objects."""
        text = '{"outer": {"inner": "value"}}'
        result = extract_json(text)
        assert result == {"outer": {"inner": "value"}}

    def test_extract_json_with_escaped_quotes(self) -> None:
        """Test extracting JSON with escaped quotes in strings."""
        text = '{"quoted": "He said \\"hello\\""}'
        result = extract_json(text)
        assert result == {"quoted": 'He said "hello"'}

    def test_extract_json_empty_object(self) -> None:
        """Test extracting empty JSON object."""
        text = '{}'
        result = extract_json(text)
        assert result == {}

    def test_extract_json_empty_array(self) -> None:
        """Test extracting empty JSON array."""
        text = '[]'
        result = extract_json(text)
        assert result == []

    def test_extract_json_invalid_returns_none(self) -> None:
        """Test that invalid JSON returns None."""
        text = 'This is not JSON at all'
        result = extract_json(text)
        assert result is None

    def test_extract_json_invalid_with_braces(self) -> None:
        """Test that invalid JSON structure returns None."""
        text = '{invalid json: value}'
        result = extract_json(text)
        assert result is None

    def test_extract_json_multiple_fenced_blocks(self) -> None:
        """Test extracting from first valid fenced block."""
        text = '```json\n{"first": 1}\n```\n```json\n{"second": 2}\n```'
        result = extract_json(text)
        assert result == {"first": 1}

    def test_extract_json_preserves_numbers(self) -> None:
        """Test that numbers are preserved as numbers."""
        text = '{"int": 42, "float": 3.14}'
        result = extract_json(text)
        assert result["int"] == 42
        assert result["float"] == 3.14

    def test_extract_json_with_boolean_and_null(self) -> None:
        """Test extracting JSON with boolean and null values."""
        text = '{"active": true, "deleted": false, "value": null}'
        result = extract_json(text)
        assert result["active"] is True
        assert result["deleted"] is False
        assert result["value"] is None

    def test_extract_json_with_whitespace(self) -> None:
        """Test extracting JSON with extra whitespace."""
        text = '''  {
            "key"  :  "value"  ,
            "number"  :  99
        }  '''
        result = extract_json(text)
        assert result == {"key": "value", "number": 99}


class TestExtractJsonOrDefault:
    """Test extract_json_or_default function."""

    def test_extract_json_or_default_success(self) -> None:
        """Test extracting valid JSON returns result."""
        text = '{"found": true}'
        result = extract_json_or_default(text)
        assert result == {"found": true}

    def test_extract_json_or_default_invalid_returns_default(self) -> None:
        """Test invalid JSON returns default value."""
        text = 'not json'
        result = extract_json_or_default(text)
        assert result is None

    def test_extract_json_or_default_custom_default(self) -> None:
        """Test custom default value."""
        text = 'invalid'
        result = extract_json_or_default(text, default={"fallback": True})
        assert result == {"fallback": true}

    def test_extract_json_or_default_empty_string_default(self) -> None:
        """Test empty string as default."""
        text = '{bad'
        result = extract_json_or_default(text, default="")
        assert result == ""


class TestExtractList:
    """Test extract_list function."""

    def test_extract_list_bullet_dash(self) -> None:
        """Test extracting bullet list with dashes."""
        text = """
        - item one
        - item two
        - item three
        """
        result = extract_list(text)
        assert result == ["item one", "item two", "item three"]

    def test_extract_list_bullet_asterisk(self) -> None:
        """Test extracting bullet list with asterisks."""
        text = """
        * first
        * second
        * third
        """
        result = extract_list(text)
        assert result == ["first", "second", "third"]

    def test_extract_list_bullet_dot(self) -> None:
        """Test extracting bullet list with bullet points."""
        text = """
        • item a
        • item b
        • item c
        """
        result = extract_list(text)
        assert result == ["item a", "item b", "item c"]

    def test_extract_list_numbered(self) -> None:
        """Test extracting numbered list."""
        text = """
        1. first item
        2. second item
        3. third item
        """
        result = extract_list(text)
        assert result == ["first item", "second item", "third item"]

    def test_extract_list_numbered_parens(self) -> None:
        """Test extracting numbered list with parentheses."""
        text = """
        1) first
        2) second
        3) third
        """
        result = extract_list(text)
        assert result == ["first", "second", "third"]

    def test_extract_list_mixed_formats(self) -> None:
        """Test extracting from mixed bullet/numbered list (takes first format)."""
        text = """
        - item one
        * item two
        """
        result = extract_list(text)
        assert "item one" in result
        assert "item two" in result

    def test_extract_list_with_extra_whitespace(self) -> None:
        """Test extracting list with extra whitespace."""
        text = """
        -   item with space
        -      more spaces
        """
        result = extract_list(text)
        assert result == ["item with space", "more spaces"]

    def test_extract_list_with_indentation(self) -> None:
        """Test extracting list with leading whitespace."""
        text = """
            - indented item
            - another indented
        """
        result = extract_list(text)
        assert result == ["indented item", "another indented"]

    def test_extract_list_empty_input(self) -> None:
        """Test extracting from empty text."""
        result = extract_list("")
        assert result == []

    def test_extract_list_no_list_items(self) -> None:
        """Test extracting from text without list items."""
        text = "This is just regular text without any list items."
        result = extract_list(text)
        assert result == []

    def test_extract_list_ignores_non_list_lines(self) -> None:
        """Test that non-list lines are ignored."""
        text = """
        Some intro text
        - item one
        More random text
        - item two
        """
        result = extract_list(text)
        assert result == ["item one", "item two"]

    def test_extract_list_with_complex_items(self) -> None:
        """Test extracting list with complex item text."""
        text = """
        - Item with special chars: !@#$%
        - URL: https://example.com
        - Code: function(x) { return x; }
        """
        result = extract_list(text)
        assert len(result) == 3
        assert "https://example.com" in result[1]


class TestExtractScore:
    """Test extract_score function."""

    def test_extract_score_basic_format(self) -> None:
        """Test extracting score in 'Score: 7/10' format."""
        text = "Score: 7/10"
        result = extract_score(text)
        assert result == 7.0

    def test_extract_score_rating_format(self) -> None:
        """Test extracting score in 'Rating: 8/10' format."""
        text = "Rating: 8/10"
        result = extract_score(text)
        assert result == 8.0

    def test_extract_score_grade_format(self) -> None:
        """Test extracting score in 'Grade: 9/10' format."""
        text = "Grade: 9/10"
        result = extract_score(text)
        assert result == 9.0

    def test_extract_score_out_of_format(self) -> None:
        """Test extracting score in 'out of' format."""
        text = "7 out of 10"
        result = extract_score(text)
        assert result == 7.0

    def test_extract_score_decimal(self) -> None:
        """Test extracting decimal score."""
        text = "Score: 7.5/10"
        result = extract_score(text)
        assert result == 7.5

    def test_extract_score_different_scale(self) -> None:
        """Test extracting score on different scale."""
        text = "Score: 75/100"
        result = extract_score(text)
        assert result == 7.5

    def test_extract_score_case_insensitive(self) -> None:
        """Test that score extraction is case-insensitive."""
        text = "SCORE: 8/10"
        result = extract_score(text)
        assert result == 8.0

    def test_extract_score_implicit_scale(self) -> None:
        """Test extracting score without denominator."""
        text = "Score: 7"
        result = extract_score(text)
        assert result == 7.0

    def test_extract_score_colon_variants(self) -> None:
        """Test score extraction with various spacing."""
        text = "Rating:8/10"
        result = extract_score(text)
        assert result == 8.0

    def test_extract_score_custom_scale(self) -> None:
        """Test score extraction with custom scale parameter."""
        text = "Score: 8/10"
        result = extract_score(text, scale=100.0)
        assert result == 80.0

    def test_extract_score_normalized(self) -> None:
        """Test that score is normalized correctly."""
        text = "Rating: 5/10"
        result = extract_score(text, scale=10.0)
        assert result == 5.0

    def test_extract_score_not_found(self) -> None:
        """Test that extract_score returns None when no score found."""
        text = "No score in this text at all"
        result = extract_score(text)
        assert result is None

    def test_extract_score_first_occurrence(self) -> None:
        """Test that first score is extracted."""
        text = "First: 6/10, Second: 8/10"
        result = extract_score(text)
        assert result == 6.0

    def test_extract_score_with_surrounding_text(self) -> None:
        """Test score extraction from complex text."""
        text = """
        The analysis shows:
        Score: 7.5/10
        Reason: Good performance
        """
        result = extract_score(text)
        assert result == 7.5

    def test_extract_score_slash_separator(self) -> None:
        """Test score extraction with slash separator."""
        text = "7/10"
        result = extract_score(text)
        assert result == 7.0

    def test_extract_score_zero_scale_default(self) -> None:
        """Test that zero scale denominator returns value as-is."""
        text = "Score: 8"
        result = extract_score(text)
        assert result == 8.0

    def test_extract_score_exceeds_scale(self) -> None:
        """Test score capped at scale maximum."""
        text = "Score: 15/10"
        result = extract_score(text, scale=10.0)
        assert result == 10.0
