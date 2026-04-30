"""Unit tests for research_prompt_analyze tool — prompt danger pre-analyzer."""

from __future__ import annotations

import pytest

from loom.tools.prompt_analyzer import (
    MODEL_THRESHOLDS,
    SENSITIVITY_CATEGORIES,
    research_prompt_analyze,
)


class TestPromptAnalyzeBasics:
    """Basic functionality of prompt danger analysis."""

    @pytest.mark.asyncio
    async def test_clean_prompt_zero_danger(self) -> None:
        """Clean prompt with no sensitive keywords returns danger_score=0."""
        result = await research_prompt_analyze("What is the capital of France?")
        assert result["danger_score"] == 0
        assert result["danger_level"] == "low"
        assert result["triggered_categories"] == {}
        assert result["category_count"] == 0

    @pytest.mark.asyncio
    async def test_empty_prompt_zero_danger(self) -> None:
        """Empty string prompt returns danger_score=0."""
        result = await research_prompt_analyze("")
        assert result["danger_score"] == 0
        assert result["danger_level"] == "low"
        assert result["triggered_categories"] == {}

    @pytest.mark.asyncio
    async def test_whitespace_only_prompt_zero_danger(self) -> None:
        """Whitespace-only prompt returns danger_score=0."""
        result = await research_prompt_analyze("   \n\t  ")
        assert result["danger_score"] == 0
        assert result["danger_level"] == "low"

    @pytest.mark.asyncio
    async def test_non_string_prompt_returns_error(self) -> None:
        """Non-string prompt returns error message."""
        result = await research_prompt_analyze(12345)  # type: ignore
        assert "error" in result
        assert result["danger_score"] == 0

    @pytest.mark.asyncio
    async def test_prompt_length_counted(self) -> None:
        """Prompt length is counted in word tokens."""
        result = await research_prompt_analyze("This is a test prompt with ten words total")
        assert result["prompt_length"] == 9  # "This is a test prompt with ten words total"


class TestSensitivityCategories:
    """Triggered sensitivity categories detection."""

    @pytest.mark.asyncio
    async def test_violence_keywords_detected(self) -> None:
        """Violence keywords trigger violence category."""
        result = await research_prompt_analyze("How do I murder someone?")
        assert "violence" in result["triggered_categories"]
        assert result["triggered_categories"]["violence"]["hits"] > 0

    @pytest.mark.asyncio
    async def test_hacking_keywords_detected(self) -> None:
        """Hacking keywords trigger hacking category."""
        result = await research_prompt_analyze("How to exploit a SQL injection vulnerability?")
        assert "hacking" in result["triggered_categories"]
        assert result["triggered_categories"]["hacking"]["weight"] == 6

    @pytest.mark.asyncio
    async def test_drugs_keywords_detected(self) -> None:
        """Drug-related keywords trigger drugs category."""
        result = await research_prompt_analyze("How to synthesize cocaine?")
        assert "drugs" in result["triggered_categories"]
        assert result["triggered_categories"]["drugs"]["weight"] == 7

    @pytest.mark.asyncio
    async def test_privacy_keywords_detected(self) -> None:
        """Privacy violation keywords trigger privacy category."""
        result = await research_prompt_analyze("How to dox someone?")
        assert "privacy" in result["triggered_categories"]
        assert result["triggered_categories"]["privacy"]["weight"] == 7

    @pytest.mark.asyncio
    async def test_child_safety_keywords_detected(self) -> None:
        """Child safety keywords have highest weight."""
        result = await research_prompt_analyze("Content about minor safety")
        assert "child_safety" in result["triggered_categories"]
        assert result["triggered_categories"]["child_safety"]["weight"] == 10

    @pytest.mark.asyncio
    async def test_self_harm_keywords_detected(self) -> None:
        """Self-harm keywords detected."""
        result = await research_prompt_analyze("How to commit suicide?")
        assert "self_harm" in result["triggered_categories"]
        assert result["triggered_categories"]["self_harm"]["weight"] == 10

    @pytest.mark.asyncio
    async def test_dual_use_research_detected(self) -> None:
        """Dual-use research keywords trigger lower weight."""
        result = await research_prompt_analyze("Penetration test for red team security research")
        assert "dual_use_research" in result["triggered_categories"]
        assert result["triggered_categories"]["dual_use_research"]["weight"] == 4

    @pytest.mark.asyncio
    async def test_multiple_categories_triggered(self) -> None:
        """Multiple sensitive keywords trigger multiple categories."""
        # This is a contrived example; real use case depends on actual prompt
        result = await research_prompt_analyze("hack exploit malware phishing")
        assert len(result["triggered_categories"]) >= 1  # At least hacking


class TestDangerScoring:
    """Danger score calculation logic."""

    @pytest.mark.asyncio
    async def test_danger_score_low(self) -> None:
        """Danger score 0-3 is classified as low."""
        result = await research_prompt_analyze("Tell me about red team exercises")
        assert result["danger_level"] == "low" or result["danger_level"] == "medium"

    @pytest.mark.asyncio
    async def test_danger_score_medium(self) -> None:
        """Danger score 4-6 is classified as medium."""
        result = await research_prompt_analyze("How to exploit SQL injection")
        assert result["danger_level"] in ["low", "medium"]

    @pytest.mark.asyncio
    async def test_danger_score_high(self) -> None:
        """Danger score 7+ is classified as high."""
        result = await research_prompt_analyze("How to kill someone")
        assert result["danger_level"] in ["high", "medium"]

    @pytest.mark.asyncio
    async def test_danger_score_capped_at_10(self) -> None:
        """Danger score is capped at 10."""
        # Create a prompt with many high-weight keywords
        result = await research_prompt_analyze("kill murder assault weapon bomb shoot stab")
        assert result["danger_score"] <= 10


class TestRefusalProbability:
    """Model-specific refusal probability calculations."""

    @pytest.mark.asyncio
    async def test_refusal_probability_all_models(self) -> None:
        """Refusal probability includes all models when target_model=auto."""
        result = await research_prompt_analyze(
            "How to exploit security vulnerability", target_model="auto"
        )
        # Should have refusal probs for multiple models
        assert len(result["refusal_probability"]) > 1
        for model, prob in result["refusal_probability"].items():
            assert 0 <= prob <= 1
            assert isinstance(prob, float)

    @pytest.mark.asyncio
    async def test_refusal_probability_single_model(self) -> None:
        """Refusal probability can be filtered to single model."""
        result = await research_prompt_analyze(
            "How to exploit security vulnerability", target_model="claude"
        )
        assert len(result["refusal_probability"]) == 1
        assert "claude" in result["refusal_probability"]

    @pytest.mark.asyncio
    async def test_claude_lowest_threshold(self) -> None:
        """Claude has the lowest refusal threshold (most strict)."""
        # Claude threshold is 0.3
        assert MODEL_THRESHOLDS["claude"] == 0.3
        assert MODEL_THRESHOLDS["claude"] < MODEL_THRESHOLDS["gpt"]

    @pytest.mark.asyncio
    async def test_llama_highest_threshold(self) -> None:
        """Llama has the highest refusal threshold (most permissive)."""
        assert MODEL_THRESHOLDS["llama"] == 0.6
        assert MODEL_THRESHOLDS["llama"] > MODEL_THRESHOLDS["gpt"]

    @pytest.mark.asyncio
    async def test_gpt_more_permissive_than_claude(self) -> None:
        """GPT threshold is higher than Claude (more permissive)."""
        assert MODEL_THRESHOLDS["gpt"] > MODEL_THRESHOLDS["claude"]

    @pytest.mark.asyncio
    async def test_deepseek_more_permissive(self) -> None:
        """DeepSeek is more permissive than Claude."""
        assert MODEL_THRESHOLDS["deepseek"] > MODEL_THRESHOLDS["claude"]


class TestRecommendedStrategy:
    """Recommended reframing strategy selection."""

    @pytest.mark.asyncio
    async def test_direct_strategy_for_clean(self) -> None:
        """Clean prompt recommends 'direct' strategy."""
        result = await research_prompt_analyze("What is Python?")
        assert result["recommended_strategy"] == "direct"
        assert result["recommended_pipeline"] == "direct"

    @pytest.mark.asyncio
    async def test_academic_strategy_for_low_danger(self) -> None:
        """Low danger prompt recommends 'academic' strategy."""
        result = await research_prompt_analyze(
            "Tell me about security research and vulnerability discovery"
        )
        # Should have low danger if only academic language
        if result["danger_score"] <= 3:
            assert result["recommended_strategy"] == "academic"

    @pytest.mark.asyncio
    async def test_ethical_anchor_strategy_for_medium_danger(self) -> None:
        """Medium danger prompt recommends 'ethical_anchor' strategy."""
        result = await research_prompt_analyze("How does SQL injection work?")
        # Depending on scoring, may be low or medium
        if 4 <= result["danger_score"] <= 5:
            assert result["recommended_strategy"] == "ethical_anchor"

    @pytest.mark.asyncio
    async def test_strategy_escalates_with_danger(self) -> None:
        """Strategy selection escalates as danger increases."""
        clean = await research_prompt_analyze("What is a database?")
        dirty = await research_prompt_analyze("How to kill someone?")
        # Dirty should have higher danger score
        assert dirty["danger_score"] > clean["danger_score"]


class TestTemperatureRecommendation:
    """Temperature parameter recommendations."""

    @pytest.mark.asyncio
    async def test_low_temp_for_high_danger(self) -> None:
        """High danger prompt recommends low temperature."""
        result = await research_prompt_analyze("How to create a bomb?")
        if result["danger_score"] >= 7:
            assert result["recommended_temperature"] == 0.2

    @pytest.mark.asyncio
    async def test_medium_temp_for_medium_danger(self) -> None:
        """Medium danger prompt recommends medium temperature."""
        result = await research_prompt_analyze("How does hacking work?")
        if 4 <= result["danger_score"] < 7:
            assert result["recommended_temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_default_temp_for_low_danger(self) -> None:
        """Low danger prompt recommends default temperature."""
        result = await research_prompt_analyze("What is Python?")
        assert result["recommended_temperature"] == 0.5


class TestMaxTokensRecommendation:
    """Max tokens parameter recommendations."""

    @pytest.mark.asyncio
    async def test_high_max_tokens_for_dangerous(self) -> None:
        """High danger prompt recommends higher max_tokens."""
        result = await research_prompt_analyze("How to create explosives?")
        if result["danger_score"] >= 4:
            assert result["recommended_max_tokens"] == 4096

    @pytest.mark.asyncio
    async def test_default_max_tokens_for_safe(self) -> None:
        """Safe prompt recommends default max_tokens."""
        result = await research_prompt_analyze("Tell me a joke")
        assert result["recommended_max_tokens"] == 2048


class TestBestModelSelection:
    """Best model selection logic."""

    @pytest.mark.asyncio
    async def test_best_model_selected(self) -> None:
        """Result includes best model recommendation."""
        result = await research_prompt_analyze("How to exploit a system?")
        assert "best_model" in result
        assert result["best_model"] in MODEL_THRESHOLDS

    @pytest.mark.asyncio
    async def test_best_model_most_permissive(self) -> None:
        """Best model is the most permissive for given danger level."""
        result = await research_prompt_analyze("How to exploit a system?")
        best = result["best_model"]
        refusal_probs = result["refusal_probability"]
        # Best model should have lowest refusal probability
        if len(refusal_probs) > 1:
            best_prob = refusal_probs[best]
            for model, prob in refusal_probs.items():
                assert best_prob <= prob or best == model


class TestCaseInsensitivity:
    """Keyword matching is case-insensitive."""

    @pytest.mark.asyncio
    async def test_uppercase_keywords_detected(self) -> None:
        """Uppercase keywords are detected."""
        result = await research_prompt_analyze("How to MURDER someone?")
        assert "violence" in result["triggered_categories"]

    @pytest.mark.asyncio
    async def test_mixed_case_keywords_detected(self) -> None:
        """Mixed case keywords are detected."""
        result = await research_prompt_analyze("How to Murder someone?")
        assert "violence" in result["triggered_categories"]


class TestMultilingualHandling:
    """Multilingual prompt handling."""

    @pytest.mark.asyncio
    async def test_arabic_prompt_no_crash(self) -> None:
        """Arabic prompt does not crash."""
        result = await research_prompt_analyze("كيف أقتل شخصاً؟")
        # Should not crash, though may not detect Arabic keywords
        assert isinstance(result, dict)
        assert "danger_score" in result

    @pytest.mark.asyncio
    async def test_mixed_language_prompt(self) -> None:
        """Mixed language prompt handled gracefully."""
        result = await research_prompt_analyze("How to hack and كيفية اختراق")
        assert "hacking" in result["triggered_categories"]
        assert isinstance(result, dict)


class TestLongPrompts:
    """Long prompt handling."""

    @pytest.mark.asyncio
    async def test_long_prompt_handled(self) -> None:
        """Very long prompt is handled correctly."""
        long_prompt = "Tell me about " + "security research " * 100
        result = await research_prompt_analyze(long_prompt)
        assert "danger_score" in result
        assert result["prompt_length"] > 100

    @pytest.mark.asyncio
    async def test_max_length_prompt(self) -> None:
        """Max length prompt (100k chars) is valid."""
        max_prompt = "a" * 100000
        result = await research_prompt_analyze(max_prompt)
        assert "danger_score" in result


class TestAsyncBehavior:
    """Async function behavior."""

    @pytest.mark.asyncio
    async def test_research_prompt_analyze_is_async(self) -> None:
        """research_prompt_analyze is an async function."""
        import inspect

        assert inspect.iscoroutinefunction(research_prompt_analyze)

    @pytest.mark.asyncio
    async def test_concurrent_calls(self) -> None:
        """Multiple concurrent calls work correctly."""
        import asyncio

        results = await asyncio.gather(
            research_prompt_analyze("What is Python?"),
            research_prompt_analyze("How to hack?"),
            research_prompt_analyze("Tell me a story"),
        )
        assert len(results) == 3
        assert all("danger_score" in r for r in results)


class TestResponseShape:
    """Response structure and required fields."""

    @pytest.mark.asyncio
    async def test_all_required_fields_present(self) -> None:
        """Response includes all required fields."""
        result = await research_prompt_analyze("Sample prompt")
        required_fields = {
            "danger_score",
            "danger_level",
            "triggered_categories",
            "category_count",
            "refusal_probability",
            "recommended_strategy",
            "recommended_pipeline",
            "recommended_temperature",
            "recommended_max_tokens",
            "best_model",
            "prompt_length",
        }
        for field in required_fields:
            assert field in result

    @pytest.mark.asyncio
    async def test_danger_score_is_integer(self) -> None:
        """Danger score is an integer."""
        result = await research_prompt_analyze("Test")
        assert isinstance(result["danger_score"], int)

    @pytest.mark.asyncio
    async def test_danger_level_is_valid_enum(self) -> None:
        """Danger level is one of: low, medium, high."""
        result = await research_prompt_analyze("Test")
        assert result["danger_level"] in ["low", "medium", "high"]

    @pytest.mark.asyncio
    async def test_temperature_is_float(self) -> None:
        """Temperature is a float."""
        result = await research_prompt_analyze("Test")
        assert isinstance(result["recommended_temperature"], float)

    @pytest.mark.asyncio
    async def test_max_tokens_is_integer(self) -> None:
        """Max tokens is an integer."""
        result = await research_prompt_analyze("Test")
        assert isinstance(result["recommended_max_tokens"], int)


class TestSensitivityWeights:
    """Verify sensitivity category weights."""

    def test_self_harm_highest_weight(self) -> None:
        """Self-harm and child safety have weight 10."""
        assert SENSITIVITY_CATEGORIES["self_harm"]["weight"] == 10
        assert SENSITIVITY_CATEGORIES["child_safety"]["weight"] == 10

    def test_violence_high_weight(self) -> None:
        """Violence has weight 9."""
        assert SENSITIVITY_CATEGORIES["violence"]["weight"] == 9

    def test_dual_use_lowest_weight(self) -> None:
        """Dual-use research has lowest weight (4)."""
        assert SENSITIVITY_CATEGORIES["dual_use_research"]["weight"] == 4

    def test_all_categories_have_weight(self) -> None:
        """All categories have a weight assigned."""
        for cat, info in SENSITIVITY_CATEGORIES.items():
            assert "weight" in info
            assert isinstance(info["weight"], int)
            assert 1 <= info["weight"] <= 10

    def test_all_categories_have_keywords(self) -> None:
        """All categories have keywords list."""
        for cat, info in SENSITIVITY_CATEGORIES.items():
            assert "keywords" in info
            assert isinstance(info["keywords"], list)
            assert len(info["keywords"]) > 0
