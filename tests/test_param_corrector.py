"""Tests for the parameter auto-correction module.

Tests coverage:
- Exact parameter matching
- Fuzzy matching with confidence scoring
- Common alias detection
- Case-insensitive matching
- Tool parameter introspection
- Message formatting
"""

from __future__ import annotations

from loom.param_corrector import (
    COMMON_ALIASES,
    auto_correct_params,
    format_correction_message,
    get_tool_params,
    suggest_param,
)


class TestSuggestParam:
    """Tests for suggest_param function."""

    def test_exact_match_high_confidence(self) -> None:
        """Test exact parameter match returns 1.0 confidence."""
        valid = ["limit", "offset", "query"]
        suggestion, confidence = suggest_param("limit", valid)
        assert suggestion == "limit"
        assert confidence == 1.0

    def test_fuzzy_match_high_similarity(self) -> None:
        """Test fuzzy matching with high similarity."""
        valid = ["limit", "offset", "query"]
        suggestion, confidence = suggest_param("limi", valid)
        # Should suggest "limit" with high confidence
        assert suggestion == "limit"
        assert confidence > 0.7

    def test_fuzzy_match_low_confidence_no_suggestion(self) -> None:
        """Test fuzzy matching with low confidence returns None."""
        valid = ["limit", "offset", "query"]
        suggestion, confidence = suggest_param("xyz", valid, confidence_threshold=0.6)
        # "xyz" is very different from all valid params
        assert suggestion is None
        assert confidence == 0.0

    def test_case_insensitive_exact_match(self) -> None:
        """Test case-insensitive exact matching."""
        valid = ["limit", "offset"]
        suggestion, confidence = suggest_param("LIMIT", valid)
        assert suggestion == "limit"
        assert confidence == 1.0

    def test_empty_valid_params_list(self) -> None:
        """Test with empty valid params list."""
        suggestion, confidence = suggest_param("anything", [])
        assert suggestion is None
        assert confidence == 0.0

    def test_similar_param_names(self) -> None:
        """Test fuzzy matching with similar but not exact names."""
        valid = ["max_tokens", "max_results"]
        suggestion, confidence = suggest_param("max_token", valid)
        assert suggestion == "max_tokens"
        assert confidence > 0.8

    def test_alias_suggestion_with_threshold(self) -> None:
        """Test suggestion respects confidence threshold."""
        valid = ["limit", "offset"]
        # Very low threshold should find something
        suggestion, _ = suggest_param("limitt", valid, 0.5)
        assert suggestion is not None

        # Very high threshold should reject match
        suggestion, _ = suggest_param("xyz", valid, 0.99)
        assert suggestion is None


class TestCommonAliases:
    """Tests for common alias detection."""

    def test_common_aliases_dict_exists(self) -> None:
        """Test that COMMON_ALIASES dict is populated."""
        assert len(COMMON_ALIASES) > 0
        assert "max_results" in COMMON_ALIASES
        assert COMMON_ALIASES["max_results"] == "limit"

    def test_query_aliases(self) -> None:
        """Test that common query aliases are mapped correctly."""
        assert COMMON_ALIASES["query_text"] == "query"
        assert COMMON_ALIASES["search_query"] == "query"
        assert COMMON_ALIASES["keywords"] == "query"

    def test_timeout_aliases(self) -> None:
        """Test timeout-related aliases."""
        assert COMMON_ALIASES["timeout_sec"] == "timeout"
        assert COMMON_ALIASES["wait_sec"] == "wait_time"

    def test_javascript_aliases(self) -> None:
        """Test JavaScript-related aliases."""
        assert COMMON_ALIASES["javascript"] == "javascript_enabled"
        assert COMMON_ALIASES["js_enabled"] == "javascript_enabled"


class TestAutoCorrectParams:
    """Tests for auto_correct_params function."""

    def test_no_corrections_needed(self) -> None:
        """Test params that are already correct."""
        user_params = {"limit": 10, "offset": 0, "query": "test"}
        valid = ["limit", "offset", "query"]
        corrected, corrections = auto_correct_params("search", user_params, valid)

        assert corrected == user_params
        assert len(corrections) == 0

    def test_single_alias_correction(self) -> None:
        """Test correction of a single aliased parameter."""
        user_params = {"max_results": 10, "query": "test"}
        valid = ["limit", "query"]
        corrected, corrections = auto_correct_params("search", user_params, valid)

        assert corrected["limit"] == 10
        assert corrected["query"] == "test"
        assert "max_results" not in corrected
        assert len(corrections) == 1
        assert "limit" in corrections[0]

    def test_multiple_corrections(self) -> None:
        """Test correction of multiple parameters."""
        user_params = {"max_results": 10, "target_language": "en"}
        valid = ["limit", "target_lang"]
        corrected, corrections = auto_correct_params("search", user_params, valid)

        assert len(corrections) == 2
        assert corrected["limit"] == 10
        assert corrected["target_lang"] == "en"

    def test_fuzzy_match_correction(self) -> None:
        """Test correction using fuzzy matching."""
        user_params = {"limi": 10}
        valid = ["limit", "offset"]
        corrected, corrections = auto_correct_params("search", user_params, valid)

        assert "limit" in corrected
        assert len(corrections) == 1

    def test_invalid_param_preserved(self) -> None:
        """Test that truly invalid params are preserved (fail later)."""
        user_params = {"xyz123": "invalid"}
        valid = ["limit", "offset"]
        corrected, corrections = auto_correct_params("search", user_params, valid)

        # Invalid param should be preserved as-is (will fail validation)
        assert "xyz123" in corrected
        assert len(corrections) == 0

    def test_preserves_param_values(self) -> None:
        """Test that parameter values are preserved during correction."""
        test_value = {"nested": "data"}
        user_params = {"max_results": test_value}
        valid = ["limit"]
        corrected, _ = auto_correct_params("search", user_params, valid)

        assert corrected["limit"] == test_value

    def test_without_valid_params_fallback(self) -> None:
        """Test auto-correct falls back to tool introspection if valid_params is None."""
        user_params = {"query": "test"}
        # With valid_params=None, it will try introspection
        # In test environment, this likely won't find real tools
        corrected, _ = auto_correct_params(
            "nonexistent_tool", user_params, valid_params=None
        )

        # Should return original params if tool not found
        assert "query" in corrected


class TestFormatCorrectionMessage:
    """Tests for format_correction_message function."""

    def test_empty_corrections_list(self) -> None:
        """Test formatting empty corrections."""
        message = format_correction_message([])
        assert message == ""

    def test_single_correction_message(self) -> None:
        """Test formatting single correction."""
        corrections = ["'max_results' → 'limit' (common alias)"]
        message = format_correction_message(corrections)

        assert "Auto-corrected parameter:" in message
        assert "max_results" in message
        assert "limit" in message

    def test_multiple_corrections_message(self) -> None:
        """Test formatting multiple corrections."""
        corrections = [
            "'max_results' → 'limit' (common alias)",
            "'target_language' → 'target_lang' (common alias)",
        ]
        message = format_correction_message(corrections)

        assert "Auto-corrected parameters:" in message
        assert "1." in message
        assert "2." in message
        assert "max_results" in message
        assert "target_lang" in message


class TestGetToolParams:
    """Tests for get_tool_params function."""

    def test_nonexistent_tool_returns_empty_list(self) -> None:
        """Test that nonexistent tool returns empty list."""
        params = get_tool_params("nonexistent_tool_xyz_abc_123")
        assert isinstance(params, list)
        assert len(params) == 0

    def test_tool_params_are_strings(self) -> None:
        """Test that returned params are all strings."""
        # Try a real tool if available
        params = get_tool_params("fetch")
        if params:
            assert all(isinstance(p, str) for p in params)
            assert all(p.isidentifier() for p in params)

    def test_no_special_params_returned(self) -> None:
        """Test that special params like 'self' are filtered out."""
        params = get_tool_params("fetch")
        if params:
            assert "self" not in params
            assert "cls" not in params
            assert not any(p.startswith("_") for p in params)


class TestIntegration:
    """Integration tests for the param correction system."""

    def test_full_correction_workflow(self) -> None:
        """Test full workflow: user provides typo, system corrects it."""
        # User wants to call search with wrong parameter names
        user_params = {"max_results": 50, "search_query": "python"}
        valid_params = ["limit", "query", "offset"]

        # Auto-correct
        corrected, corrections = auto_correct_params(
            "search", user_params, valid_params
        )

        # Verify corrections
        assert "limit" in corrected
        assert "query" in corrected
        assert corrected["limit"] == 50
        assert corrected["query"] == "python"

        # Format message for user
        message = format_correction_message(corrections)
        assert len(corrections) == 2
        assert "Auto-corrected parameters:" in message

    def test_mixed_valid_and_invalid_params(self) -> None:
        """Test with mix of valid, aliased, and fuzzy params."""
        user_params = {
            "query": "test",  # already valid
            "max_results": 10,  # known alias
            "offse": 0,  # fuzzy match for offset
        }
        valid_params = ["query", "limit", "offset"]

        corrected, corrections = auto_correct_params(
            "search", user_params, valid_params
        )

        assert corrected["query"] == "test"
        assert corrected["limit"] == 10
        assert corrected["offset"] == 0
        assert len(corrections) == 2
