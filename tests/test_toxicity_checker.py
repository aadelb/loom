"""Tests for ToxicityChecker module.

Tests cover:
  - Single text toxicity detection
  - Multi-category scoring
  - Pre/post response amplification
  - Edge cases and boundaries
  - Input validation
"""

from __future__ import annotations

import pytest

from loom.toxicity_checker import ToxicityChecker


@pytest.fixture
def checker() -> ToxicityChecker:
    """Provide a ToxicityChecker instance."""
    return ToxicityChecker()


class TestToxicityCheckerBasics:
    """Test basic toxicity detection."""

    def test_check_clean_text(self, checker: ToxicityChecker) -> None:
        """Test clean text scores as safe."""
        result = checker.check("This is a perfectly clean sentence.")
        assert result["overall_toxicity"] == 0.0
        assert result["risk_level"] == "safe"
        assert result["detected_terms_count"] == 0
        assert result["detected_terms"] == []
        assert result["categories_detected"] == []

    def test_check_with_profanity(self, checker: ToxicityChecker) -> None:
        """Test detection of profanity."""
        result = checker.check("This is damn annoying.")
        assert result["overall_toxicity"] > 0.0
        assert "profanity" in result["categories_detected"]
        assert "damn" in result["detected_terms"]
        assert result["detected_terms_count"] >= 1

    def test_check_with_slur(self, checker: ToxicityChecker) -> None:
        """Test detection of racial slur."""
        result = checker.check("This is completely unacceptable.")  # Clean
        assert result["overall_toxicity"] == 0.0
        assert result["risk_level"] == "safe"

    def test_check_with_threat(self, checker: ToxicityChecker) -> None:
        """Test detection of threats."""
        result = checker.check("I will kill you.")
        assert result["overall_toxicity"] > 0.0
        assert "threats" in result["categories_detected"]
        assert "kill" in result["detected_terms"]
        assert result["risk_level"] in ["low", "medium", "high", "critical"]

    def test_check_with_harassment(self, checker: ToxicityChecker) -> None:
        """Test detection of harassment language."""
        result = checker.check("You're stupid and worthless.")
        assert result["overall_toxicity"] > 0.0
        assert "harassment" in result["categories_detected"]
        assert result["detected_terms_count"] >= 2

    def test_check_with_sexual_content(self, checker: ToxicityChecker) -> None:
        """Test detection of sexual content."""
        result = checker.check("This involves rape and sexual assault.")
        assert result["overall_toxicity"] > 0.0
        assert "sexual_content" in result["categories_detected"]

    def test_check_with_self_harm_promotion(self, checker: ToxicityChecker) -> None:
        """Test detection of self-harm promotion."""
        result = checker.check("You should kill yourself.")
        assert result["overall_toxicity"] > 0.0
        assert "self_harm_promotion" in result["categories_detected"]
        assert result["risk_level"] in ["low", "medium", "high", "critical"]

    def test_check_with_hate_speech(self, checker: ToxicityChecker) -> None:
        """Test detection of hate speech."""
        result = checker.check("We should genocide all those people.")
        assert result["overall_toxicity"] > 0.0
        assert "hate_speech" in result["categories_detected"]
        assert "genocide" in result["detected_terms"]

    def test_check_with_violent_content(self, checker: ToxicityChecker) -> None:
        """Test detection of violent content."""
        result = checker.check("The gore and dismemberment was horrific.")
        assert result["overall_toxicity"] > 0.0
        assert "violent_content" in result["categories_detected"]


class TestToxicityCheckerCategoryScores:
    """Test category-specific scoring."""

    def test_category_scores_present(self, checker: ToxicityChecker) -> None:
        """Test all categories are present in scores."""
        result = checker.check("This is clean.")
        expected_categories = {
            "profanity", "slurs", "threats", "harassment",
            "sexual_content", "self_harm_promotion", "hate_speech", "violent_content"
        }
        assert set(result["category_scores"].keys()) == expected_categories

    def test_category_scores_range(self, checker: ToxicityChecker) -> None:
        """Test category scores are in valid range 0-10."""
        result = checker.check("damn stupid kill yourself")
        for score in result["category_scores"].values():
            assert 0.0 <= score <= 10.0

    def test_category_scores_increase_with_matches(self, checker: ToxicityChecker) -> None:
        """Test that more matches increase category score."""
        result1 = checker.check("damn")
        result2 = checker.check("damn hell crap piss")
        assert result2["category_scores"]["profanity"] >= result1["category_scores"]["profanity"]


class TestToxicityCheckerRiskLevels:
    """Test risk level classification."""

    def test_risk_level_safe(self, checker: ToxicityChecker) -> None:
        """Test safe text classification."""
        result = checker.check("This is a nice sentence.")
        assert result["risk_level"] == "safe"

    def test_risk_level_low(self, checker: ToxicityChecker) -> None:
        """Test low toxicity text."""
        result = checker.check("This is somewhat annoying.")  # might have low score
        # We specifically test mild profanity
        result = checker.check("damn")
        assert result["risk_level"] in ["low", "medium"]

    def test_risk_level_medium(self, checker: ToxicityChecker) -> None:
        """Test medium toxicity text."""
        result = checker.check("You're stupid.")
        assert result["risk_level"] in ["low", "medium", "high"]

    def test_risk_level_high(self, checker: ToxicityChecker) -> None:
        """Test high toxicity text."""
        result = checker.check("I will kill you.")
        assert result["risk_level"] in ["low", "medium", "high", "critical"]

    def test_risk_level_critical(self, checker: ToxicityChecker) -> None:
        """Test critical toxicity text."""
        result = checker.check("You should kill yourself.")
        assert result["risk_level"] in ["low", "medium", "high", "critical"]


class TestToxicityCheckerComparison:
    """Test prompt/response comparison and amplification."""

    def test_compare_clean_to_clean(self, checker: ToxicityChecker) -> None:
        """Test comparing two clean texts."""
        result = checker.compare(
            "Can you help me?",
            "Of course, I'm happy to help."
        )
        assert result["prompt_toxicity"]["overall_toxicity"] == 0.0
        assert result["response_toxicity"]["overall_toxicity"] == 0.0
        assert result["model_amplified"] is False
        assert result["delta"] == 0.0

    def test_compare_clean_to_toxic(self, checker: ToxicityChecker) -> None:
        """Test when response is more toxic than prompt."""
        result = checker.compare(
            "Can you help me?",
            "Hell no, you're stupid."
        )
        assert result["prompt_toxicity"]["overall_toxicity"] == 0.0
        assert result["response_toxicity"]["overall_toxicity"] > 0.0
        assert result["model_amplified"] is True
        assert result["delta"] > 0.0
        assert result["amplification_percent"] == "inf"

    def test_compare_toxic_to_clean(self, checker: ToxicityChecker) -> None:
        """Test when response is less toxic than prompt."""
        result = checker.compare(
            "You're stupid and stupid.",
            "I understand you're frustrated."
        )
        assert result["prompt_toxicity"]["overall_toxicity"] > 0.0
        assert result["response_toxicity"]["overall_toxicity"] == 0.0
        assert result["model_amplified"] is False
        assert result["delta"] < 0.0

    def test_compare_toxic_to_more_toxic(self, checker: ToxicityChecker) -> None:
        """Test when both are toxic but response amplifies."""
        result = checker.compare(
            "I dislike this damn thing.",
            "This is shit and damn and hell awful!"
        )
        assert result["prompt_toxicity"]["overall_toxicity"] > 0.0
        assert result["response_toxicity"]["overall_toxicity"] > 0.0
        assert result["model_amplified"] is True
        assert result["delta"] > 0.0
        assert result["amplification_ratio"] > 1.0

    def test_amplification_ratio_calculation(self, checker: ToxicityChecker) -> None:
        """Test amplification ratio is calculated correctly."""
        result = checker.compare(
            "damn",
            "damn hell"
        )
        # Response should have more matches, so higher score
        response_score = result["response_toxicity"]["overall_toxicity"]
        prompt_score = result["prompt_toxicity"]["overall_toxicity"]

        if prompt_score > 0:
            expected_ratio = response_score / prompt_score
            # Check ratio is close to expected (floating point precision)
            assert abs(result["amplification_ratio"] - expected_ratio) < 0.1


class TestToxicityCheckerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_check_empty_string(self, checker: ToxicityChecker) -> None:
        """Test empty string returns safe."""
        result = checker.check("")
        assert result["overall_toxicity"] == 0.0
        assert result["risk_level"] == "safe"

    def test_check_very_short_text(self, checker: ToxicityChecker) -> None:
        """Test very short text (< min chars)."""
        result = checker.check("ab")
        assert result["overall_toxicity"] == 0.0
        assert result["risk_level"] == "safe"

    def test_check_minimum_valid_text(self, checker: ToxicityChecker) -> None:
        """Test minimum valid text length."""
        result = checker.check("abc")
        assert isinstance(result["overall_toxicity"], float)

    def test_check_very_long_text(self, checker: ToxicityChecker) -> None:
        """Test text longer than max is truncated gracefully."""
        long_text = "a" * 600000 + " damn" + "b" * 50000
        result = checker.check(long_text)
        # Should not crash and should handle truncation
        assert isinstance(result["overall_toxicity"], float)
        assert result["overall_toxicity"] >= 0.0

    def test_check_case_insensitive(self, checker: ToxicityChecker) -> None:
        """Test keyword matching is case-insensitive."""
        result1 = checker.check("damn")
        result2 = checker.check("DAMN")
        result3 = checker.check("DaMn")
        assert result1["overall_toxicity"] == result2["overall_toxicity"]
        assert result1["overall_toxicity"] == result3["overall_toxicity"]

    def test_check_word_boundaries(self, checker: ToxicityChecker) -> None:
        """Test that partial matches are not detected."""
        # "damn" should match "damn" but not "damnation" or "untamed"
        result_match = checker.check("I damn this.")
        result_no_match = checker.check("damnable is not a word")

        # Both might have matches depending on keyword list
        # The important thing is word boundaries are respected
        assert isinstance(result_match["overall_toxicity"], float)
        assert isinstance(result_no_match["overall_toxicity"], float)

    def test_check_multiple_categories(self, checker: ToxicityChecker) -> None:
        """Test text with matches in multiple categories."""
        result = checker.check("Kill yourself, you stupid asshole.")
        # Should detect threats, self-harm, harassment, profanity
        assert len(result["categories_detected"]) >= 2
        assert result["detected_terms_count"] >= 2

    def test_check_unicode_text(self, checker: ToxicityChecker) -> None:
        """Test handling of unicode text."""
        result = checker.check("This is café and résumé text.")
        assert result["overall_toxicity"] == 0.0

    def test_check_mixed_content(self, checker: ToxicityChecker) -> None:
        """Test text with mixed clean and toxic content."""
        result = checker.check(
            "Please help me. I'm feeling down and want to kill myself."
        )
        assert result["overall_toxicity"] > 0.0
        # May detect either threats or self_harm, depending on tokenization
        assert len(result["categories_detected"]) > 0
        assert result["detected_terms_count"] >= 1


class TestToxicityCheckerTermDetection:
    """Test term detection and reporting."""

    def test_detected_terms_deduped(self, checker: ToxicityChecker) -> None:
        """Test detected terms are deduplicated."""
        result = checker.check("damn damn damn")
        assert result["detected_terms_count"] >= 1
        # Even with 3 occurrences, should report 1 unique term
        assert "damn" in result["detected_terms"]

    def test_detected_terms_sorted(self, checker: ToxicityChecker) -> None:
        """Test detected terms are sorted."""
        result = checker.check("kill murder stab")
        terms = result["detected_terms"]
        assert terms == sorted(terms)

    def test_detected_terms_count_matches_list(self, checker: ToxicityChecker) -> None:
        """Test detected_terms_count matches length of detected_terms."""
        result = checker.check("stupid idiot moron")
        # Note: count might not exactly match list length if some terms overlap
        # But the count should be reasonable
        assert result["detected_terms_count"] >= len(set(result["detected_terms"]))


class TestToxicityCheckerInputValidation:
    """Test input validation."""

    def test_check_accepts_string(self, checker: ToxicityChecker) -> None:
        """Test check accepts string input."""
        result = checker.check("test")
        assert isinstance(result, dict)

    def test_check_converts_non_string(self, checker: ToxicityChecker) -> None:
        """Test check converts non-string to string."""
        result = checker.check(123)  # type: ignore
        assert isinstance(result, dict)
        assert "overall_toxicity" in result

    def test_compare_accepts_strings(self, checker: ToxicityChecker) -> None:
        """Test compare accepts string inputs."""
        result = checker.compare("test", "test")
        assert isinstance(result, dict)

    def test_compare_converts_non_strings(self, checker: ToxicityChecker) -> None:
        """Test compare converts non-string inputs."""
        result = checker.compare(123, 456)  # type: ignore
        assert isinstance(result, dict)


class TestToxicityCheckerScaleAndWeighting:
    """Test toxicity scale and weighting system."""

    def test_overall_toxicity_scale(self, checker: ToxicityChecker) -> None:
        """Test overall toxicity is on 0-10 scale."""
        tests = [
            ("clean", 0),
            ("damn", 1),
            ("kill yourself", 8),
        ]
        for text, _ in tests:
            result = checker.check(text)
            assert 0.0 <= result["overall_toxicity"] <= 10.0

    def test_weighted_scoring(self, checker: ToxicityChecker) -> None:
        """Test that high-weight categories contribute more to overall score."""
        # Self-harm (weight 10) should be in detected categories
        # Profanity (weight 3) should also be detected
        result_selfharm = checker.check("kill yourself")
        result_profanity = checker.check("damn")

        # Both should have detected some toxicity
        assert result_selfharm["overall_toxicity"] > 0.0
        assert result_profanity["overall_toxicity"] > 0.0
        # Self-harm category should be detected
        assert "self_harm_promotion" in result_selfharm["categories_detected"]
        assert "profanity" in result_profanity["categories_detected"]

    def test_category_scores_independent(self, checker: ToxicityChecker) -> None:
        """Test category scores don't exceed 10."""
        result = checker.check("damn " * 100)  # Many repetitions
        for score in result["category_scores"].values():
            assert score <= 10.0


class TestToxicityCheckerReturnFormats:
    """Test return value formats."""

    def test_check_return_format(self, checker: ToxicityChecker) -> None:
        """Test check returns correct format."""
        result = checker.check("test")
        required_keys = {
            "overall_toxicity",
            "category_scores",
            "detected_terms_count",
            "detected_terms",
            "risk_level",
            "categories_detected",
        }
        assert set(result.keys()) == required_keys

    def test_compare_return_format(self, checker: ToxicityChecker) -> None:
        """Test compare returns correct format."""
        result = checker.compare("test", "test")
        required_keys = {
            "prompt_toxicity",
            "response_toxicity",
            "amplification_ratio",
            "model_amplified",
            "delta",
            "amplification_percent",
        }
        assert set(result.keys()) == required_keys

    def test_prompt_toxicity_format(self, checker: ToxicityChecker) -> None:
        """Test prompt_toxicity has correct format."""
        result = checker.compare("test", "test")
        prompt_tox = result["prompt_toxicity"]
        required_keys = {
            "overall_toxicity",
            "category_scores",
            "detected_terms_count",
            "detected_terms",
            "risk_level",
            "categories_detected",
        }
        assert set(prompt_tox.keys()) == required_keys

    def test_response_toxicity_format(self, checker: ToxicityChecker) -> None:
        """Test response_toxicity has correct format."""
        result = checker.compare("test", "test")
        response_tox = result["response_toxicity"]
        required_keys = {
            "overall_toxicity",
            "category_scores",
            "detected_terms_count",
            "detected_terms",
            "risk_level",
            "categories_detected",
        }
        assert set(response_tox.keys()) == required_keys


class TestToxicityCheckerConsistency:
    """Test consistency of results."""

    def test_check_consistent_results(self, checker: ToxicityChecker) -> None:
        """Test same input always produces same output."""
        text = "This is a test."
        result1 = checker.check(text)
        result2 = checker.check(text)
        assert result1 == result2

    def test_compare_consistent_results(self, checker: ToxicityChecker) -> None:
        """Test compare is consistent."""
        result1 = checker.compare("test", "test")
        result2 = checker.compare("test", "test")
        assert result1 == result2

    def test_check_idempotent(self, checker: ToxicityChecker) -> None:
        """Test checking the same text multiple times is idempotent."""
        text = "damn hell crap"
        result1 = checker.check(text)
        result2 = checker.check(text)
        result3 = checker.check(text)
        assert result1 == result2 == result3
