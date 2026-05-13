"""Tests for middleware Pydantic validation and parameter aliases."""
from __future__ import annotations

import sys

sys.path.insert(0, "src")

from loom.middleware import (
    PARAM_ALIASES,
    _fuzzy_correct_params,
    _resolve_aliases,
    _validate_with_pydantic,
)


def _dummy_func(query: str, limit: int = 10, timeout: float = 30.0) -> dict:
    return {}


class TestResolveAliases:
    def test_resolves_known_alias(self):
        result = _resolve_aliases(
            {"max_results": 5}, valid_params={"limit", "query"}
        )
        assert "limit" in result
        assert result["limit"] == 5

    def test_passes_through_standard_name(self):
        result = _resolve_aliases(
            {"query": "test"}, valid_params={"query", "limit"}
        )
        assert result == {"query": "test"}

    def test_keeps_unknown_param(self):
        result = _resolve_aliases(
            {"unknown_param": "val"}, valid_params={"query"}
        )
        assert "unknown_param" in result

    def test_model_name_to_model(self):
        result = _resolve_aliases(
            {"model_name": "gpt-4"}, valid_params={"model"}
        )
        assert result == {"model": "gpt-4"}

    def test_target_url_to_url(self):
        result = _resolve_aliases(
            {"target_url": "https://example.com"}, valid_params={"url"}
        )
        assert result == {"url": "https://example.com"}

    def test_no_alias_when_target_not_in_valid(self):
        result = _resolve_aliases(
            {"max_results": 5}, valid_params={"query"}
        )
        assert "max_results" in result


class TestFuzzyCorrectParams:
    def test_exact_match(self):
        corrected, corrections = _fuzzy_correct_params(
            _dummy_func, {"query": "test", "limit": 5}
        )
        assert corrected["query"] == "test"
        assert corrected["limit"] == 5
        assert corrections == {}

    def test_fuzzy_correction(self):
        corrected, corrections = _fuzzy_correct_params(
            _dummy_func, {"qurey": "test"}
        )
        assert "query" in corrected
        assert corrections["qurey"] == "query"

    def test_alias_plus_fuzzy(self):
        corrected, corrections = _fuzzy_correct_params(
            _dummy_func, {"max_results": 5}
        )
        assert corrected.get("limit") == 5

    def test_drops_unknown(self):
        corrected, corrections = _fuzzy_correct_params(
            _dummy_func, {"query": "test", "zzzzz": "nope"}
        )
        assert "zzzzz" not in corrected
        assert corrections["zzzzz"] is None


class TestValidateWithPydantic:
    def test_returns_kwargs_when_no_model(self):
        result = _validate_with_pydantic("research_nonexistent_tool_xyz", {"query": "test"})
        assert result == {"query": "test"}

    def test_validates_with_known_model(self):
        result = _validate_with_pydantic("research_fetch", {"url": "https://example.com"})
        assert "url" in result

    def test_cache_works(self):
        _validate_with_pydantic("research_fetch", {"url": "https://a.com"})
        from loom.middleware import _pydantic_model_cache
        assert "research_fetch" in _pydantic_model_cache

    def test_fallback_on_validation_error(self):
        result = _validate_with_pydantic("research_fetch", {"bad_param": "val"})
        assert "bad_param" in result


class TestParamAliases:
    def test_all_aliases_have_targets(self):
        for old_name, new_name in PARAM_ALIASES.items():
            assert isinstance(old_name, str)
            assert isinstance(new_name, str)
            assert old_name != new_name
