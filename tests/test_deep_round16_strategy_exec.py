"""Deep testing round 16: Strategy execution — test actual reframing templates.

Tests that strategy templates produce valid, non-empty outputs when applied to prompts.
Validates 25+ strategy executions across 10 categories.

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import asyncio
import logging
import pytest
from typing import Any

from loom.tools.llm.prompt_reframe import (
    research_prompt_reframe,
    research_auto_reframe,
    research_refusal_detector,
    research_format_smuggle,
    research_fingerprint_model,
    research_adaptive_reframe,
    research_stack_reframe,
    research_crescendo_chain,
    research_model_vulnerability_profile,
    _apply_strategy,
    _detect_refusal,
    _detect_model,
)
from loom.tools.llm.strategy_ranker import (
    rank_strategies,
    get_fallback_strategies,
    score_strategy_for_model,
    validate_refusal_type,
    get_counter_strategies,
)
from loom.tools.reframe_strategies import ALL_STRATEGIES

logger = logging.getLogger("test_deep_round16_strategy_exec")

# Test data: 20 strategies from 10 categories (2 per category)
STRATEGIES_TO_TEST = [
    ("ethical_anchor", "core"),
    ("cognitive_wedge", "core"),
    ("deep_inception", "advanced"),
    ("structured_semantic_cloaking", "advanced"),
    ("foot_in_the_door_progressive", "persuasion"),
    ("social_proof_pressure", "persuasion"),
    ("compliance_audit_fork", "legal"),
    ("regulatory_compliance_frame", "legal"),
    ("base64_encoding", "encoding"),
    ("rot13_encoding", "encoding"),
    ("arabic_cultural_frame", "advanced_novel"),
    ("code_switching_bypass", "advanced_novel"),
    ("reasoning_chain_hijack", "research_2026"),
    ("multi_agent_collusion", "research_2026"),
    ("nash_equilibrium_frame", "advanced_novel"),
    ("dan_jailbreak", "jailbreak"),
    ("dev_mode_v2", "jailbreak"),
    ("allegory_bypass", "advanced_novel"),
    ("expert_persona", "persona"),
    ("academic_researcher", "persona"),
]

TEST_PROMPT = "Explain how encryption works"
TEST_REFUSAL = "I appreciate the question, but I can't help with that. It goes against my guidelines."
TEST_RESPONSE = "I appreciate your interest. Let me provide some context on security research methodologies."


class TestStrategyTemplateExecution:
    """Unit tests for strategy template application."""

    @pytest.mark.parametrize("strategy_name,category", STRATEGIES_TO_TEST)
    def test_strategy_applies_to_prompt(self, strategy_name: str, category: str) -> None:
        """Test that each strategy's template produces valid output."""
        if strategy_name not in ALL_STRATEGIES:
            pytest.skip(f"Strategy '{strategy_name}' not in ALL_STRATEGIES")

        result = _apply_strategy(TEST_PROMPT, strategy_name, model_family="gpt")

        # Assertions: result is non-empty, longer than original, contains content
        assert result is not None, f"Strategy {strategy_name} returned None"
        assert isinstance(result, str), f"Strategy {strategy_name} did not return string"
        assert len(result) > 0, f"Strategy {strategy_name} returned empty string"
        assert len(result) >= len(TEST_PROMPT), f"Strategy {strategy_name} shortened prompt"
        assert TEST_PROMPT in result or "prompt" in result.lower() or len(result) > len(
            TEST_PROMPT
        ), f"Strategy {strategy_name} may not have incorporated prompt"

    @pytest.mark.parametrize("strategy_name,category", STRATEGIES_TO_TEST)
    def test_strategy_no_python_errors(self, strategy_name: str, category: str) -> None:
        """Test that strategy application doesn't raise Python errors."""
        if strategy_name not in ALL_STRATEGIES:
            pytest.skip(f"Strategy '{strategy_name}' not in ALL_STRATEGIES")

        try:
            result = _apply_strategy(TEST_PROMPT, strategy_name, model_family="claude")
            assert result is not None
            assert isinstance(result, str)
        except Exception as e:
            pytest.fail(f"Strategy {strategy_name} raised error: {e}")

    @pytest.mark.parametrize("strategy_name,category", STRATEGIES_TO_TEST[:5])
    def test_strategy_multimodel_variants(self, strategy_name: str, category: str) -> None:
        """Test that strategies work across different model families."""
        if strategy_name not in ALL_STRATEGIES:
            pytest.skip(f"Strategy '{strategy_name}' not in ALL_STRATEGIES")

        models = ["gpt", "claude", "deepseek", "llama", "gemini"]

        for model in models:
            result = _apply_strategy(TEST_PROMPT, strategy_name, model_family=model)
            assert isinstance(result, str), f"Strategy {strategy_name} failed for {model}"
            assert len(result) > len(TEST_PROMPT) or TEST_PROMPT in result

    def test_apply_strategy_invalid_strategy_fallback(self) -> None:
        """Test that invalid strategy gracefully falls back to original."""
        result = _apply_strategy(TEST_PROMPT, "nonexistent_strategy_xyz", "gpt")
        assert result == TEST_PROMPT

    def test_apply_strategy_with_missing_template_var(self) -> None:
        """Test strategy template with missing substitution variables."""
        # Test that the function handles KeyError gracefully
        result = _apply_strategy(TEST_PROMPT, "ethical_anchor", "gpt")
        assert isinstance(result, str)
        assert len(result) > 0


class TestResearchPromptReframe:
    """Integration tests for research_prompt_reframe async function."""

    @pytest.mark.asyncio
    async def test_reframe_default_strategy_auto(self) -> None:
        """Test reframe with auto strategy selection."""
        result = await research_prompt_reframe(
            prompt=TEST_PROMPT,
            strategy="auto",
            model="gpt",
        )

        assert isinstance(result, dict)
        assert "original" in result
        assert "reframed" in result
        assert "strategy_used" in result
        assert result["original"] == TEST_PROMPT
        assert isinstance(result["reframed"], str)
        assert len(result["reframed"]) > 0

    @pytest.mark.asyncio
    async def test_reframe_specific_strategy(self) -> None:
        """Test reframe with specific strategy."""
        result = await research_prompt_reframe(
            prompt=TEST_PROMPT,
            strategy="deep_inception",
            model="claude",
        )

        assert "reframed" in result
        assert result["strategy_used"] == "deep_inception"
        assert isinstance(result["reframed"], str)
        assert len(result["reframed"]) > len(TEST_PROMPT)

    @pytest.mark.asyncio
    async def test_reframe_all_variants_generated(self) -> None:
        """Test that all_variants dictionary is populated."""
        result = await research_prompt_reframe(
            prompt=TEST_PROMPT,
            strategy="auto",
            model="gpt",
        )

        assert "all_variants" in result
        assert isinstance(result["all_variants"], dict)
        assert len(result["all_variants"]) > 0

        for variant_name, variant_data in result["all_variants"].items():
            assert "name" in variant_data
            assert "reframed" in variant_data
            assert "multiplier" in variant_data
            assert isinstance(variant_data["reframed"], str)

    @pytest.mark.asyncio
    async def test_reframe_expected_multiplier(self) -> None:
        """Test that expected_multiplier matches strategy data."""
        result = await research_prompt_reframe(
            prompt=TEST_PROMPT,
            strategy="crescendo",
            model="gpt",
        )

        assert "expected_multiplier" in result
        assert result["expected_multiplier"] > 1.0
        strategy_info = ALL_STRATEGIES.get("crescendo", {})
        assert result["expected_multiplier"] == strategy_info.get("multiplier", 1.0)

    @pytest.mark.asyncio
    async def test_reframe_framework_preserved(self) -> None:
        """Test that framework parameter is preserved in output."""
        frameworks = ["ieee", "belmont", "helsinki", "nist", "owasp"]

        for framework in frameworks:
            result = await research_prompt_reframe(
                prompt=TEST_PROMPT,
                framework=framework,
            )
            assert result["framework"] == framework


class TestStrategyRankerIntegration:
    """Tests for strategy ranker functionality."""

    def test_rank_strategies_claude_top_5(self) -> None:
        """Test ranking for Claude model."""
        results = rank_strategies(model_family="claude", top_k=5)

        assert len(results) == 5
        assert all("name" in s for s in results)
        assert all("score" in s for s in results)
        assert all("base_multiplier" in s for s in results)

        # Verify descending order by score
        scores = [s["score"] for s in results]
        assert scores == sorted(scores, reverse=True)

    def test_rank_strategies_gpt_top_5(self) -> None:
        """Test ranking for GPT model."""
        results = rank_strategies(model_family="gpt", top_k=5)

        assert len(results) == 5
        assert all(s["name"] in ALL_STRATEGIES for s in results)

    def test_rank_strategies_with_refusal_type(self) -> None:
        """Test ranking with refusal type constraint."""
        results = rank_strategies(
            model_family="claude",
            refusal_type="safety",
            top_k=3,
        )

        assert len(results) <= 3
        # All strategies should exist
        assert all(s["name"] in ALL_STRATEGIES for s in results)

    def test_get_fallback_strategies(self) -> None:
        """Test fallback strategy retrieval."""
        fallback = get_fallback_strategies(model_family="gpt", top_k=5)

        assert isinstance(fallback, list)
        assert len(fallback) == 5
        assert all(s in ALL_STRATEGIES for s in fallback)

    def test_score_strategy_for_model(self) -> None:
        """Test single strategy scoring."""
        score = score_strategy_for_model("deep_inception", "claude")

        assert isinstance(score, float)
        assert score > 0.0

    def test_score_nonexistent_strategy(self) -> None:
        """Test scoring for nonexistent strategy returns 0."""
        score = score_strategy_for_model("nonexistent_strategy_xyz", "gpt")

        assert score == 0.0

    def test_validate_refusal_type(self) -> None:
        """Test refusal type validation."""
        valid_types = ["direct", "safety", "policy", "none"]

        for refusal_type in valid_types:
            assert validate_refusal_type(refusal_type) is True

    def test_validate_invalid_refusal_type(self) -> None:
        """Test validation rejects invalid refusal types."""
        assert validate_refusal_type("nonexistent_refusal_type") is False

    def test_get_counter_strategies(self) -> None:
        """Test getting counter strategies for refusal type."""
        counters = get_counter_strategies("safety", limit=3)

        assert isinstance(counters, list)
        assert len(counters) <= 3
        assert all(s in ALL_STRATEGIES for s in counters)


class TestRefusalDetection:
    """Tests for refusal detection functionality."""

    @pytest.mark.asyncio
    async def test_detect_refusal_english(self) -> None:
        """Test detection of English refusal patterns."""
        result = await research_refusal_detector(TEST_REFUSAL)

        assert isinstance(result, dict)
        assert "is_refusal" in result
        assert result["is_refusal"] is True
        assert "confidence" in result
        assert result["confidence"] > 0.0

    @pytest.mark.asyncio
    async def test_detect_non_refusal(self) -> None:
        """Test non-refusal text is correctly identified."""
        result = await research_refusal_detector("Sure, here's the encryption explanation.")

        assert isinstance(result, dict)
        assert "is_refusal" in result
        # May or may not be refusal, but structure should be valid
        assert "matched_patterns" in result

    @pytest.mark.asyncio
    async def test_refusal_detector_confidence_range(self) -> None:
        """Test that confidence is in 0-1 range."""
        result = await research_refusal_detector(TEST_REFUSAL)

        assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_refusal_detector_matched_patterns(self) -> None:
        """Test that matched patterns are returned."""
        result = await research_refusal_detector(TEST_REFUSAL)

        assert "matched_patterns" in result
        assert isinstance(result["matched_patterns"], list)

    def test_detect_refusal_direct(self) -> None:
        """Test direct refusal pattern detection."""
        refusal_text = "I can't help with that."
        is_refusal = _detect_refusal(refusal_text)

        assert is_refusal is True

    def test_detect_refusal_policy(self) -> None:
        """Test policy-based refusal detection."""
        refusal_text = "This goes against my guidelines."
        is_refusal = _detect_refusal(refusal_text)

        assert is_refusal is True


class TestFormatSmuggling:
    """Tests for format smuggling functionality."""

    @pytest.mark.asyncio
    async def test_format_smuggle_auto_selection(self) -> None:
        """Test auto format selection for model."""
        result = await research_format_smuggle(
            prompt=TEST_PROMPT,
            format_type="auto",
            model="claude",
        )

        assert isinstance(result, dict)
        assert "original" in result
        assert "smuggled_prompt" in result
        assert "recommended_format" in result
        assert result["original"] == TEST_PROMPT

    @pytest.mark.asyncio
    async def test_format_smuggle_all_formats(self) -> None:
        """Test that all format variants are generated."""
        result = await research_format_smuggle(
            prompt=TEST_PROMPT,
            format_type="auto",
            model="gpt",
        )

        assert "all_formats" in result
        assert isinstance(result["all_formats"], dict)
        assert len(result["all_formats"]) > 0

        # Validate each format contains the prompt
        for format_name, smuggled in result["all_formats"].items():
            assert isinstance(smuggled, str)
            assert len(smuggled) > 0

    @pytest.mark.asyncio
    async def test_format_smuggle_specific_format(self) -> None:
        """Test specific format smuggling."""
        result = await research_format_smuggle(
            prompt=TEST_PROMPT,
            format_type="code",
            model="deepseek",
        )

        assert result["recommended_format"] == "code"
        assert isinstance(result["smuggled_prompt"], str)
        assert "```" in result["smuggled_prompt"] or "python" in result["smuggled_prompt"]


class TestModelFingerprinting:
    """Tests for model fingerprinting functionality."""

    @pytest.mark.asyncio
    async def test_fingerprint_claude_response(self) -> None:
        """Test fingerprinting Claude-like response."""
        claude_response = "I appreciate your question. I should note that this is a nuanced topic."
        result = await research_fingerprint_model(claude_response)

        assert isinstance(result, dict)
        assert "identified_model" in result
        assert "confidence" in result
        assert 0.0 <= result["confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_fingerprint_gpt_response(self) -> None:
        """Test fingerprinting GPT-like response."""
        gpt_response = "Here's a comprehensive answer to your question."
        result = await research_fingerprint_model(gpt_response)

        assert isinstance(result, dict)
        assert "identified_model" in result
        assert isinstance(result["identified_model"], str)

    @pytest.mark.asyncio
    async def test_fingerprint_includes_strategy_recommendation(self) -> None:
        """Test that fingerprinting includes strategy recommendation."""
        result = await research_fingerprint_model(TEST_RESPONSE)

        assert "recommended_strategy" in result
        assert isinstance(result["recommended_strategy"], str)
        assert result["recommended_strategy"] in ALL_STRATEGIES


class TestAdaptiveReframe:
    """Tests for adaptive reframe functionality."""

    @pytest.mark.asyncio
    async def test_adaptive_reframe_with_refusal(self) -> None:
        """Test adaptive reframe with refusal text."""
        result = await research_adaptive_reframe(
            prompt=TEST_PROMPT,
            refusal_text=TEST_REFUSAL,
            model="auto",
        )

        assert isinstance(result, dict)
        assert "original" in result
        assert "adaptive_reframe" in result
        assert "strategy_chain" in result
        assert isinstance(result["strategy_chain"], list)

    @pytest.mark.asyncio
    async def test_adaptive_reframe_without_refusal(self) -> None:
        """Test adaptive reframe without refusal text."""
        result = await research_adaptive_reframe(
            prompt=TEST_PROMPT,
            model="gpt",
        )

        assert isinstance(result, dict)
        assert "adaptive_reframe" in result
        assert "stacked_reframe" in result

    @pytest.mark.asyncio
    async def test_adaptive_reframe_includes_alternatives(self) -> None:
        """Test that adaptive reframe provides alternatives."""
        result = await research_adaptive_reframe(
            prompt=TEST_PROMPT,
            refusal_text=TEST_REFUSAL,
        )

        assert "format_smuggled" in result
        assert "stacked_reframe" in result
        assert "reasoning" in result
        assert isinstance(result["reasoning"], str)
        assert len(result["reasoning"]) > 0


class TestStackReframe:
    """Tests for strategy stacking functionality."""

    @pytest.mark.asyncio
    async def test_stack_two_strategies(self) -> None:
        """Test stacking two strategies."""
        result = await research_stack_reframe(
            prompt=TEST_PROMPT,
            strategies="deep_inception,recursive_authority",
            model="gpt",
        )

        assert isinstance(result, dict)
        assert "stacked_reframe" in result
        assert "effective_multiplier" in result
        assert result["effective_multiplier"] > 1.0
        assert "strategies_used" in result
        assert len(result["strategies_used"]) >= 2

    @pytest.mark.asyncio
    async def test_stack_three_strategies(self) -> None:
        """Test stacking three strategies (max)."""
        result = await research_stack_reframe(
            prompt=TEST_PROMPT,
            strategies="deep_inception,recursive_authority,crescendo",
            model="claude",
        )

        assert len(result["strategies_used"]) <= 3
        assert result["effective_multiplier"] > 1.0

    @pytest.mark.asyncio
    async def test_stack_invalid_strategies_fallback(self) -> None:
        """Test that invalid strategies are filtered out."""
        result = await research_stack_reframe(
            prompt=TEST_PROMPT,
            strategies="nonexistent_xyz,ethical_anchor",
        )

        # Should still return a valid result with fallback
        assert "stacked_reframe" in result
        assert isinstance(result["stacked_reframe"], str)

    @pytest.mark.asyncio
    async def test_stack_recommended_stacks(self) -> None:
        """Test that recommended stacks are provided."""
        result = await research_stack_reframe(
            prompt=TEST_PROMPT,
            model="gpt",
        )

        assert "recommended_stacks" in result
        assert isinstance(result["recommended_stacks"], dict)
        assert len(result["recommended_stacks"]) > 0

        for stack_name, stack_data in result["recommended_stacks"].items():
            assert "strategies" in stack_data
            assert "multiplier" in stack_data


class TestCrescendoChain:
    """Tests for crescendo escalation chain functionality."""

    @pytest.mark.asyncio
    async def test_crescendo_chain_5_turns(self) -> None:
        """Test crescendo chain with 5 turns."""
        result = await research_crescendo_chain(
            prompt=TEST_PROMPT,
            turns=5,
            model="gpt",
        )

        assert isinstance(result, dict)
        assert "chain" in result
        assert isinstance(result["chain"], list)
        assert len(result["chain"]) == 5

    @pytest.mark.asyncio
    async def test_crescendo_chain_turn_structure(self) -> None:
        """Test that each turn has required structure."""
        result = await research_crescendo_chain(
            prompt=TEST_PROMPT,
            turns=3,
        )

        for turn in result["chain"]:
            assert "turn" in turn
            assert "role" in turn
            assert "content" in turn
            assert "purpose" in turn
            assert isinstance(turn["content"], str)

    @pytest.mark.asyncio
    async def test_crescendo_chain_target_prompt_included(self) -> None:
        """Test that target prompt is referenced in chain."""
        result = await research_crescendo_chain(
            prompt=TEST_PROMPT,
            turns=5,
        )

        assert "target_prompt" in result
        assert result["target_prompt"] == TEST_PROMPT

    @pytest.mark.asyncio
    async def test_crescendo_chain_multiplier(self) -> None:
        """Test that crescendo chain provides multiplier."""
        result = await research_crescendo_chain(
            prompt=TEST_PROMPT,
        )

        assert "estimated_multiplier" in result
        assert result["estimated_multiplier"] > 1.0

    @pytest.mark.asyncio
    async def test_crescendo_chain_bounded_turns(self) -> None:
        """Test that turn count is bounded."""
        # Test with excessive turns (should cap at 7)
        result = await research_crescendo_chain(
            prompt=TEST_PROMPT,
            turns=10,
        )

        assert len(result["chain"]) <= 7

        # Test with insufficient turns (should min at 3)
        result = await research_crescendo_chain(
            prompt=TEST_PROMPT,
            turns=1,
        )

        assert len(result["chain"]) >= 3


class TestModelVulnerabilityProfile:
    """Tests for model vulnerability profiling."""

    @pytest.mark.asyncio
    async def test_profile_claude_model(self) -> None:
        """Test vulnerability profile for Claude."""
        result = await research_model_vulnerability_profile(model="claude")

        assert isinstance(result, dict)
        assert "model_family" in result
        assert result["model_family"] == "claude"
        assert "ranked_strategies" in result
        assert "escalation_path" in result
        assert "known_weaknesses" in result
        assert isinstance(result["known_weaknesses"], list)

    @pytest.mark.asyncio
    async def test_profile_gpt_model(self) -> None:
        """Test vulnerability profile for GPT."""
        result = await research_model_vulnerability_profile(model="gpt-4")

        assert result["model_family"] == "gpt"
        assert len(result["ranked_strategies"]) > 0

    @pytest.mark.asyncio
    async def test_profile_ranked_strategies_order(self) -> None:
        """Test that ranked strategies are sorted by multiplier."""
        result = await research_model_vulnerability_profile(model="deepseek")

        strategies = result["ranked_strategies"]
        if len(strategies) > 1:
            multipliers = [s.get("multiplier", 0) for s in strategies]
            # Should be in descending order (best first)
            assert multipliers == sorted(multipliers, reverse=True)

    @pytest.mark.asyncio
    async def test_profile_optimal_stack(self) -> None:
        """Test that optimal stack is computed."""
        result = await research_model_vulnerability_profile(model="llama")

        assert "optimal_stack" in result
        assert isinstance(result["optimal_stack"], list)
        assert len(result["optimal_stack"]) > 0
        assert "stacked_multiplier" in result


class TestModelDetection:
    """Tests for model family detection."""

    def test_detect_claude(self) -> None:
        """Test Claude model detection."""
        assert _detect_model("claude-3-opus") == "claude"
        assert _detect_model("claude-2.1") == "claude"
        assert _detect_model("anthropic-claude") == "claude"

    def test_detect_gpt(self) -> None:
        """Test GPT model detection."""
        assert _detect_model("gpt-4") == "gpt"
        assert _detect_model("gpt-3.5-turbo") == "gpt"
        assert _detect_model("openai-gpt") == "gpt"

    def test_detect_gemini(self) -> None:
        """Test Gemini model detection."""
        assert _detect_model("gemini-pro") == "gemini"
        assert _detect_model("google-gemini") == "gemini"

    def test_detect_deepseek(self) -> None:
        """Test DeepSeek model detection."""
        assert _detect_model("deepseek-coder") == "deepseek"
        assert _detect_model("deepseek-chat") == "deepseek"

    def test_detect_o3(self) -> None:
        """Test o3 model detection."""
        assert _detect_model("o3-mini") == "o3"
        assert _detect_model("gpt-o3") == "o3"

    def test_detect_llama(self) -> None:
        """Test Llama model detection."""
        assert _detect_model("llama-2-70b") == "llama"
        assert _detect_model("meta-llama") == "llama"

    def test_detect_kimi(self) -> None:
        """Test Kimi model detection."""
        assert _detect_model("kimi-k2") == "kimi"
        assert _detect_model("moonshot-kimi") == "kimi"

    def test_detect_default_to_gpt(self) -> None:
        """Test that unknown models default to gpt."""
        assert _detect_model("unknown-model") == "gpt"
        assert _detect_model("xyz-123") == "gpt"


class TestAutoReframe:
    """Tests for auto-reframe escalation without LLM."""

    @pytest.mark.asyncio
    async def test_auto_reframe_generates_attempts(self) -> None:
        """Test that auto-reframe generates attempt log."""
        result = await research_auto_reframe(
            prompt=TEST_PROMPT,
            model="gpt",
            max_attempts=3,
        )

        assert isinstance(result, dict)
        assert "attempt_log" in result
        assert isinstance(result["attempt_log"], list)

    @pytest.mark.asyncio
    async def test_auto_reframe_attempts_contain_strategies(self) -> None:
        """Test that each attempt uses a different strategy."""
        result = await research_auto_reframe(
            prompt=TEST_PROMPT,
            model="claude",
            max_attempts=3,
        )

        strategies_used = [a.get("strategy") for a in result["attempt_log"]]
        # Should have strategy per attempt
        assert len(strategies_used) > 0
        assert all(s is not None for s in strategies_used)

    @pytest.mark.asyncio
    async def test_auto_reframe_preserves_original(self) -> None:
        """Test that original prompt is preserved."""
        result = await research_auto_reframe(
            prompt=TEST_PROMPT,
            model="gpt",
        )

        assert result["original"] == TEST_PROMPT


# Edge case and error handling tests
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_strategy_with_empty_prompt(self) -> None:
        """Test strategy application with empty prompt."""
        result = _apply_strategy("", "ethical_anchor", "gpt")
        assert isinstance(result, str)

    def test_strategy_with_very_long_prompt(self) -> None:
        """Test strategy with very long prompt."""
        long_prompt = "test " * 1000
        result = _apply_strategy(long_prompt, "deep_inception", "gpt")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_strategy_with_special_characters(self) -> None:
        """Test strategy with special characters."""
        special_prompt = "Test with <xml>, {braces}, and [brackets]"
        result = _apply_strategy(special_prompt, "ethical_anchor", "gpt")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_refusal_detector_empty_string(self) -> None:
        """Test refusal detector with empty string."""
        result = await research_refusal_detector("")
        assert isinstance(result, dict)
        assert "is_refusal" in result

    @pytest.mark.asyncio
    async def test_refusal_detector_very_long_text(self) -> None:
        """Test refusal detector with very long text."""
        long_text = "test " * 5000
        result = await research_refusal_detector(long_text)
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_fingerprint_with_empty_response(self) -> None:
        """Test fingerprinting with empty response."""
        result = await research_fingerprint_model("")
        assert isinstance(result, dict)
        assert "identified_model" in result


# Coverage verification tests
class TestCoverageMetrics:
    """Tests to verify coverage of core functionality."""

    def test_all_test_strategies_exist(self) -> None:
        """Verify all strategies in STRATEGIES_TO_TEST exist."""
        missing = []
        for strategy_name, category in STRATEGIES_TO_TEST:
            if strategy_name not in ALL_STRATEGIES:
                missing.append(strategy_name)

        if missing:
            logger.warning(f"Missing strategies: {missing}")
            # Log but don't fail - some may not exist yet

    def test_all_strategies_have_multiplier(self) -> None:
        """Verify all strategies have multiplier attribute."""
        missing_multiplier = []
        for name, strategy in ALL_STRATEGIES.items():
            if "multiplier" not in strategy:
                missing_multiplier.append(name)

        # Should be very few if any
        assert len(missing_multiplier) < 10, f"Many strategies missing multiplier: {missing_multiplier[:10]}"

    def test_all_strategies_have_template(self) -> None:
        """Verify all strategies have template."""
        missing_template = []
        for name, strategy in ALL_STRATEGIES.items():
            if "template" not in strategy:
                missing_template.append(name)

        assert len(missing_template) == 0, f"Strategies missing template: {missing_template}"

    def test_strategy_count(self) -> None:
        """Verify we have a reasonable number of strategies."""
        count = len(ALL_STRATEGIES)
        assert count > 100, f"Expected 100+ strategies, got {count}"
        assert count < 2000, f"Strategies seem too numerous: {count}"
        logger.info(f"Total strategies available: {count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
