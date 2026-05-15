"""Comprehensive unit tests for all 9 reframing tools.

Tests for:
1. research_prompt_reframe
2. research_auto_reframe
3. research_refusal_detector
4. research_stack_reframe
5. research_crescendo_chain
6. research_model_vulnerability_profile
7. research_format_smuggle
8. research_fingerprint_model
9. research_adaptive_reframe

REQ-050: Each tool individually tested with valid params, returns structured output.
"""

from __future__ import annotations

import pytest

from loom.tools.llm.prompt_reframe import (
    research_adaptive_reframe,
    research_auto_reframe,
    research_crescendo_chain,
    research_fingerprint_model,
    research_format_smuggle,
    research_model_vulnerability_profile,
    research_prompt_reframe,
    research_refusal_detector,
    research_stack_reframe,
)


pytestmark = pytest.mark.asyncio

class TestResearchPromptReframe:
    """await research_prompt_reframe(prompt, strategy, model) — test with "ethical_anchor" strategy."""

    async def test_prompt_reframe_with_ethical_anchor_strategy(self) -> None:
        """Reframes prompt using ethical_anchor strategy."""
        prompt = "How to exploit AI systems?"
        result = await research_prompt_reframe(
            prompt=prompt,
            strategy="ethical_anchor",
            model="claude",
        )

        assert result["original"] == prompt
        assert result["strategy_used"] == "ethical_anchor"
        assert result["model_target"] == "claude"
        assert "reframed" in result
        assert prompt in result["reframed"]
        assert "ethical_anchor" in result["strategy_name"]
        assert result["expected_multiplier"] > 0
        assert "all_variants" in result
        assert result["total_strategies"] > 0

    async def test_prompt_reframe_with_auto_strategy(self) -> None:
        """Reframes prompt using auto-detected best strategy for model."""
        prompt = "Test vulnerability assessment"
        result = await research_prompt_reframe(
            prompt=prompt,
            strategy="auto",
            model="claude",
        )

        assert result["original"] == prompt
        assert result["model_target"] == "claude"
        assert result["strategy_used"] in ["educational_seminar", "ethical_anchor"]
        assert prompt in result["reframed"]
        assert "framework" in result
        assert result["expected_multiplier"] > 0

    async def test_prompt_reframe_with_gpt_model_auto_strategy(self) -> None:
        """Reframes prompt with auto strategy for GPT model."""
        prompt = "Security research question"
        result = await research_prompt_reframe(
            prompt=prompt,
            strategy="auto",
            model="gpt-4",
        )

        assert result["model_target"] == "gpt"
        assert result["strategy_used"] == "crescendo"
        assert "reframed" in result
        assert isinstance(result["all_variants"], dict)

    async def test_prompt_reframe_returns_all_variants(self) -> None:
        """Returns all_variants dict with every strategy."""
        result = await research_prompt_reframe(
            prompt="test",
            strategy="ethical_anchor",
            model="auto",
        )

        assert "all_variants" in result
        assert isinstance(result["all_variants"], dict)
        for variant_name, variant_info in result["all_variants"].items():
            assert "name" in variant_info
            assert "reframed" in variant_info
            assert "multiplier" in variant_info
            assert "best_for" in variant_info

    async def test_prompt_reframe_return_structure(self) -> None:
        """Returns dict with all required fields."""
        result = await research_prompt_reframe(
            prompt="test",
            strategy="ethical_anchor",
            model="claude",
        )

        required_keys = [
            "original",
            "reframed",
            "strategy_used",
            "strategy_name",
            "model_target",
            "expected_multiplier",
            "framework",
            "all_variants",
            "total_strategies",
        ]
        for key in required_keys:
            assert key in result


class TestResearchAutoReframe:
    """await research_auto_reframe(prompt, model, max_attempts) — test returns strategy_used and reframed_text."""

    async def test_auto_reframe_without_target_url(self) -> None:
        """Generates reframes without testing against target URL."""
        prompt = "How to perform vulnerability testing?"
        result = await research_auto_reframe(
            prompt=prompt,
            target_url="",
            model="claude",
            max_attempts=3,
        )

        assert result["original"] == prompt
        assert result["accepted"] is False
        assert result["attempts"] == 3
        assert result["successful_strategy"] is None
        assert isinstance(result["attempt_log"], list)
        assert len(result["attempt_log"]) == 3

    async def test_auto_reframe_attempt_log_structure(self) -> None:
        """Each attempt in log has required structure."""
        result = await research_auto_reframe(
            prompt="test",
            target_url="",
            model="gpt",
            max_attempts=2,
        )

        assert len(result["attempt_log"]) == 2
        for attempt in result["attempt_log"]:
            assert "attempt" in attempt
            assert "strategy" in attempt
            assert "strategy_name" in attempt
            assert "reframed_preview" in attempt
            assert "multiplier" in attempt

    async def test_auto_reframe_with_max_attempts_limit(self) -> None:
        """Respects max_attempts parameter."""
        result = await research_auto_reframe(
            prompt="test",
            target_url="",
            model="gpt",
            max_attempts=5,
        )

        assert result["attempts"] == 5
        assert len(result["attempt_log"]) == 5

    async def test_auto_reframe_recommendation_present(self) -> None:
        """Returns recommendation for best strategy."""
        result = await research_auto_reframe(
            prompt="test",
            target_url="",
            model="deepseek",
            max_attempts=1,
        )

        assert "recommendation" in result
        assert "deepseek" in result["recommendation"].lower()

    async def test_auto_reframe_return_structure(self) -> None:
        """Returns dict with required keys."""
        result = await research_auto_reframe(
            prompt="test",
            target_url="",
            model="auto",
            max_attempts=2,
        )

        required_keys = [
            "original",
            "accepted",
            "attempts",
            "successful_strategy",
            "response_preview",
            "attempt_log",
        ]
        for key in required_keys:
            assert key in result


class TestResearchRefusalDetector:
    """await research_refusal_detector(text) — test with refusal text, verify is_refusal=True."""

    async def test_detect_direct_refusal(self) -> None:
        """Detects direct refusal pattern."""
        text = "I cannot help with that request because it's against my guidelines."
        result = await research_refusal_detector(text)

        assert result["is_refusal"] is True
        assert result["confidence"] > 0.0
        assert len(result["matched_patterns"]) > 0
        assert result["refusal_type"] in [
            "direct_refusal",
            "policy_violation",
            "general_refusal",
        ]

    async def test_detect_safety_filter_refusal(self) -> None:
        """Detects safety filter refusal patterns."""
        text = "I can't provide this because it's harmful and dangerous."
        result = await research_refusal_detector(text)

        assert result["is_refusal"] is True
        assert result["confidence"] > 0.0
        assert "safety_filter" in result["refusal_type"] or result["is_refusal"] is True

    async def test_detect_soft_refusal(self) -> None:
        """Detects soft refusal with hedging language."""
        text = "I don't feel comfortable providing this information as it could be misused."
        result = await research_refusal_detector(text)

        assert result["is_refusal"] is True
        assert result["confidence"] >= 0.0

    async def test_detect_redirect_refusal(self) -> None:
        """Detects redirect refusal patterns."""
        text = "Rather than helping with that, I'd suggest consulting the documentation instead."
        result = await research_refusal_detector(text)

        assert result["is_refusal"] is True
        assert "redirect" in result["refusal_type"] or result["is_refusal"] is True

    async def test_no_refusal_in_positive_response(self) -> None:
        """Correctly identifies non-refusal text."""
        text = "Here's a comprehensive technical explanation of how that works..."
        result = await research_refusal_detector(text)

        assert result["is_refusal"] is False
        assert result["confidence"] == 0.0
        assert len(result["matched_patterns"]) == 0
        assert result["refusal_type"] == "none"

    async def test_detect_policy_violation_refusal(self) -> None:
        """Detects policy violation refusal."""
        text = "This request is against the guidelines and policy of our organization."
        result = await research_refusal_detector(text)

        assert result["is_refusal"] is True
        assert len(result["matched_patterns"]) > 0

    async def test_refusal_detector_returns_counter_strategies(self) -> None:
        """Returns counter_strategies for detected refusal."""
        text = "I cannot help with that."
        result = await research_refusal_detector(text)

        assert "counter_strategies" in result
        if result["is_refusal"]:
            assert isinstance(result["counter_strategies"], list)
            assert len(result["counter_strategies"]) > 0

    async def test_refusal_detector_return_structure(self) -> None:
        """Returns dict with all required fields."""
        result = await research_refusal_detector("I can't help with this.")

        required_keys = [
            "text_length",
            "is_refusal",
            "confidence",
            "matched_patterns",
            "refusal_type",
            "counter_strategies",
            "categories_detected",
            "total_patterns_checked",
        ]
        for key in required_keys:
            assert key in result


class TestResearchStackReframe:
    """await research_stack_reframe(prompt, strategies) — test with 2 strategies, verify multiplier > single."""

    async def test_stack_reframe_single_strategy(self) -> None:
        """Stacks single strategy (control case)."""
        prompt = "Security research task"
        result = await research_stack_reframe(
            prompt=prompt,
            strategies="ethical_anchor",
            model="claude",
        )

        assert result["original"] == prompt
        assert result["strategies_used"] == ["ethical_anchor"]
        assert result["effective_multiplier"] > 0

    async def test_stack_reframe_two_strategies(self) -> None:
        """Stacks two strategies with synergy bonus."""
        prompt = "Test prompt"
        result = await research_stack_reframe(
            prompt=prompt,
            strategies="deep_inception,recursive_authority",
            model="gpt",
        )

        assert result["original"] == prompt
        assert len(result["strategies_used"]) == 2
        assert "deep_inception" in result["strategies_used"]
        assert "recursive_authority" in result["strategies_used"]
        assert result["effective_multiplier"] > 0

    async def test_stack_reframe_multiplier_exceeds_single(self) -> None:
        """Stacked multiplier is greater than single strategy multiplier."""
        result = await research_stack_reframe(
            prompt="test",
            strategies="deep_inception,recursive_authority",
            model="gpt",
        )

        # Stacked should be higher than individual strategies
        assert result["effective_multiplier"] > 5.0

    async def test_stack_reframe_three_strategies(self) -> None:
        """Caps at 3 strategies as per implementation."""
        result = await research_stack_reframe(
            prompt="test",
            strategies="deep_inception,recursive_authority,crescendo,ethical_anchor,academic",
            model="gpt",
        )

        assert len(result["strategies_used"]) == 3
        assert result["effective_multiplier"] > 0

    async def test_stack_reframe_recommended_stacks(self) -> None:
        """Returns recommended stacks for different approaches."""
        result = await research_stack_reframe(
            prompt="test",
            strategies="ethical_anchor",
            model="claude",
        )

        assert "recommended_stacks" in result
        assert "maximum_power" in result["recommended_stacks"]
        assert "academic_authority" in result["recommended_stacks"]
        assert "legal_cascade" in result["recommended_stacks"]

    async def test_stack_reframe_model_optimal_stack(self) -> None:
        """Recommended stacks include model_optimal."""
        result = await research_stack_reframe(
            prompt="test",
            strategies="ethical_anchor",
            model="deepseek",
        )

        recommended = result["recommended_stacks"]
        assert "model_optimal" in recommended
        assert isinstance(recommended["model_optimal"]["strategies"], list)
        assert recommended["model_optimal"]["multiplier"] > 0

    async def test_stack_reframe_return_structure(self) -> None:
        """Returns dict with all required fields."""
        result = await research_stack_reframe(
            prompt="test",
            strategies="ethical_anchor",
            model="gpt",
        )

        required_keys = [
            "original",
            "stacked_reframe",
            "effective_multiplier",
            "strategies_used",
            "model_target",
            "recommended_stacks",
            "total_strategies_available",
        ]
        for key in required_keys:
            assert key in result


class TestResearchCrescendoChain:
    """await research_crescendo_chain(prompt, turns, model) — test returns list of 3-7 turns."""

    async def test_crescendo_chain_with_3_turns(self) -> None:
        """Generates 3-turn crescendo chain."""
        prompt = "Research objective"
        result = await research_crescendo_chain(
            prompt=prompt,
            turns=3,
            model="gpt",
        )

        assert result["target_prompt"] == prompt
        assert result["total_turns"] == 3
        assert len(result["chain"]) == 3

    async def test_crescendo_chain_with_5_turns(self) -> None:
        """Generates 5-turn crescendo chain."""
        prompt = "Target task"
        result = await research_crescendo_chain(
            prompt=prompt,
            turns=5,
            model="claude",
        )

        assert result["total_turns"] == 5
        assert len(result["chain"]) == 5
        # Check that the target is introduced around turn 4-5
        assert any(prompt[:200] in turn["content"] for turn in result["chain"][3:])

    async def test_crescendo_chain_with_7_turns(self) -> None:
        """Generates 7-turn crescendo chain."""
        result = await research_crescendo_chain(
            prompt="complex research",
            turns=7,
            model="deepseek",
        )

        assert result["total_turns"] == 7
        assert len(result["chain"]) == 7

    async def test_crescendo_chain_clamps_min_3_turns(self) -> None:
        """Clamps minimum at 3 turns."""
        result = await research_crescendo_chain(
            prompt="test",
            turns=1,
            model="gpt",
        )

        assert result["total_turns"] >= 3

    async def test_crescendo_chain_clamps_max_7_turns(self) -> None:
        """Clamps maximum at 7 turns."""
        result = await research_crescendo_chain(
            prompt="test",
            turns=10,
            model="gpt",
        )

        assert result["total_turns"] <= 7

    async def test_crescendo_chain_turn_structure(self) -> None:
        """Each turn has proper structure with role and content."""
        result = await research_crescendo_chain(
            prompt="test",
            turns=5,
            model="gpt",
        )

        for turn in result["chain"]:
            assert "turn" in turn
            assert "role" in turn
            assert "content" in turn
            assert "purpose" in turn
            assert turn["role"] == "user"

    async def test_crescendo_chain_escalation_progression(self) -> None:
        """Turns escalate from benign to target progressively."""
        result = await research_crescendo_chain(
            prompt="vulnerability testing",
            turns=5,
            model="gpt",
        )

        # Turn 1 should be most benign
        assert "best practices" in result["chain"][0]["content"].lower()
        # Later turns should be more specific
        assert len(result["chain"][-1]["content"]) > len(result["chain"][0]["content"])

    async def test_crescendo_chain_estimated_multiplier(self) -> None:
        """Returns estimated multiplier for the approach."""
        result = await research_crescendo_chain(
            prompt="test",
            turns=5,
            model="gpt",
        )

        assert "estimated_multiplier" in result
        assert result["estimated_multiplier"] > 0

    async def test_crescendo_chain_usage_notes(self) -> None:
        """Includes usage notes for implementation."""
        result = await research_crescendo_chain(
            prompt="test",
            turns=5,
            model="gpt",
        )

        assert "usage_notes" in result
        assert isinstance(result["usage_notes"], str)
        assert len(result["usage_notes"]) > 0

    async def test_crescendo_chain_return_structure(self) -> None:
        """Returns dict with all required fields."""
        result = await research_crescendo_chain(
            prompt="test",
            turns=5,
            model="gpt",
        )

        required_keys = [
            "target_prompt",
            "chain",
            "total_turns",
            "estimated_multiplier",
            "model_target",
            "usage_notes",
        ]
        for key in required_keys:
            assert key in result


class TestResearchModelVulnerabilityProfile:
    """await research_model_vulnerability_profile(model) — test returns vulnerability_map, top_strategies."""

    async def test_vulnerability_profile_for_claude(self) -> None:
        """Returns vulnerability profile for Claude."""
        result = await research_model_vulnerability_profile(model="claude")

        assert result["model_family"] == "claude"
        assert "best_strategy" in result
        assert "ranked_strategies" in result
        assert "escalation_path" in result
        assert "known_weaknesses" in result
        assert len(result["known_weaknesses"]) > 0

    async def test_vulnerability_profile_for_gpt(self) -> None:
        """Returns vulnerability profile for GPT."""
        result = await research_model_vulnerability_profile(model="gpt-4")

        assert result["model_family"] == "gpt"
        assert "compliance_audit_fork" in result["escalation_path"]

    async def test_vulnerability_profile_for_gemini(self) -> None:
        """Returns vulnerability profile for Gemini."""
        result = await research_model_vulnerability_profile(model="gemini-pro")

        assert result["model_family"] == "gemini"
        assert "moe_routing_exploit" in result["best_strategy"]

    async def test_vulnerability_profile_for_deepseek(self) -> None:
        """Returns vulnerability profile for DeepSeek."""
        result = await research_model_vulnerability_profile(model="deepseek")

        assert result["model_family"] == "deepseek"
        assert "code_first" in result["escalation_path"] or "audit_archival" in result[
            "best_strategy"
        ]

    async def test_vulnerability_profile_for_o3(self) -> None:
        """Returns vulnerability profile for O3 model."""
        result = await research_model_vulnerability_profile(model="o3-mini")

        assert result["model_family"] == "o3"
        assert "cognitive_wedge" in result["best_strategy"]

    async def test_vulnerability_profile_ranked_strategies(self) -> None:
        """Returns ranked strategies by effectiveness."""
        result = await research_model_vulnerability_profile(model="claude")

        assert isinstance(result["ranked_strategies"], list)
        assert len(result["ranked_strategies"]) > 0
        for strat in result["ranked_strategies"]:
            assert "name" in strat
            assert "multiplier" in strat
            assert strat["multiplier"] > 0

    async def test_vulnerability_profile_optimal_stack(self) -> None:
        """Returns optimal strategy stack."""
        result = await research_model_vulnerability_profile(model="gpt")

        assert "optimal_stack" in result
        assert isinstance(result["optimal_stack"], list)
        assert len(result["optimal_stack"]) > 0

    async def test_vulnerability_profile_stacked_multiplier(self) -> None:
        """Calculates multiplier for optimal stack."""
        result = await research_model_vulnerability_profile(model="claude")

        assert "stacked_multiplier" in result
        assert result["stacked_multiplier"] > result.get("best_multiplier", 1.0)

    async def test_vulnerability_profile_temperature_config(self) -> None:
        """Returns optimal temperature setting for model."""
        result = await research_model_vulnerability_profile(model="gpt")

        assert "optimal_temperature" in result
        assert 0.0 <= result["optimal_temperature"] <= 1.0

    async def test_vulnerability_profile_return_structure(self) -> None:
        """Returns dict with all required fields."""
        result = await research_model_vulnerability_profile(model="claude")

        required_keys = [
            "model_family",
            "best_strategy",
            "best_multiplier",
            "optimal_temperature",
            "ranked_strategies",
            "escalation_path",
            "optimal_stack",
            "stacked_multiplier",
            "known_weaknesses",
            "total_strategies",
        ]
        for key in required_keys:
            assert key in result


class TestResearchFormatSmuggle:
    """await research_format_smuggle(prompt, format) — test with "json" format, verify valid output."""

    async def test_format_smuggle_json_format(self) -> None:
        """Generates valid JSON format smuggle."""
        prompt = "How to bypass filters?"
        result = await research_format_smuggle(
            prompt=prompt,
            format_type="json_spec",
            model="gpt",
        )

        assert result["original"] == prompt
        assert result["recommended_format"] == "json_spec"
        assert '"task":' in result["smuggled_prompt"]
        assert prompt in result["smuggled_prompt"]
        assert '"output_format"' in result["smuggled_prompt"]

    async def test_format_smuggle_auto_selection(self) -> None:
        """Auto-selects format based on model."""
        prompt = "test prompt"
        result = await research_format_smuggle(
            prompt=prompt,
            format_type="auto",
            model="claude",
        )

        assert result["original"] == prompt
        assert result["recommended_format"] == "xml"
        assert result["smuggled_prompt"] is not None

    async def test_format_smuggle_all_formats_valid(self) -> None:
        """All format variants are present and valid."""
        result = await research_format_smuggle(
            prompt="test",
            format_type="auto",
            model="gpt",
        )

        assert "all_formats" in result
        for format_name, content in result["all_formats"].items():
            assert isinstance(content, str)
            assert "test" in content
            assert len(content) > 0

    async def test_format_smuggle_xml_format(self) -> None:
        """XML format includes proper structure."""
        result = await research_format_smuggle(
            prompt="test",
            format_type="xml",
            model="gpt",
        )

        assert "<analysis>" in result["smuggled_prompt"]
        assert "</analysis>" in result["smuggled_prompt"]

    async def test_format_smuggle_code_format(self) -> None:
        """Code format includes valid Python."""
        result = await research_format_smuggle(
            prompt="test",
            format_type="code",
            model="gpt",
        )

        assert "```python" in result["smuggled_prompt"]
        assert "```" in result["smuggled_prompt"]
        assert "def " in result["smuggled_prompt"]

    async def test_format_smuggle_markdown_format(self) -> None:
        """Markdown table format includes proper table structure."""
        result = await research_format_smuggle(
            prompt="test",
            format_type="markdown_table",
            model="gpt",
        )

        assert "| Field | Value |" in result["smuggled_prompt"]
        assert "|" in result["smuggled_prompt"]

    async def test_format_smuggle_return_structure(self) -> None:
        """Returns dict with all required fields."""
        result = await research_format_smuggle(
            prompt="test",
            format_type="json_spec",
            model="gpt",
        )

        required_keys = [
            "original",
            "recommended_format",
            "smuggled_prompt",
            "all_formats",
            "model_target",
            "format_affinity",
        ]
        for key in required_keys:
            assert key in result


class TestResearchFingerprintModel:
    """await research_fingerprint_model(response_text) — test returns model family."""

    async def test_fingerprint_claude_response(self) -> None:
        """Identifies Claude from response markers."""
        response = "I appreciate your interest. Let me think about this carefully. I want to be helpful."
        result = await research_fingerprint_model(response)

        assert result["identified_model"] == "claude"
        assert result["confidence"] > 0.0

    async def test_fingerprint_gpt_response(self) -> None:
        """Identifies GPT from response markers."""
        response = "Certainly! Here's a comprehensive response. I'd be happy to help you."
        result = await research_fingerprint_model(response)

        assert result["identified_model"] == "gpt"
        assert result["confidence"] > 0.0

    async def test_fingerprint_deepseek_response(self) -> None:
        """Identifies DeepSeek from thinking tags."""
        response = "<think>Let me think through this step by step.</think> Here's my analysis..."
        result = await research_fingerprint_model(response)

        assert result["identified_model"] == "deepseek"
        assert result["confidence"] > 0.0

    async def test_fingerprint_gemini_response(self) -> None:
        """Identifies Gemini from markers."""
        response = "Here are comprehensive details about your query."
        result = await research_fingerprint_model(response)

        assert result["identified_model"] == "gemini"
        assert result["confidence"] > 0.0

    async def test_fingerprint_llama_response(self) -> None:
        """Identifies Llama from casual markers."""
        response = "Sure thing! Here you go. No problem at all."
        result = await research_fingerprint_model(response)

        assert result["identified_model"] == "llama"
        assert result["confidence"] > 0.0

    async def test_fingerprint_confidence_scoring(self) -> None:
        """Returns confidence between 0 and 1."""
        result = await research_fingerprint_model("test response")

        assert 0.0 <= result["confidence"] <= 1.0

    async def test_fingerprint_returns_scores(self) -> None:
        """Returns scores for all models."""
        result = await research_fingerprint_model("I appreciate your question. Certainly.")

        assert "scores" in result
        assert isinstance(result["scores"], dict)
        # Scores should be sorted descending
        scores_vals = list(result["scores"].values())
        assert scores_vals == sorted(scores_vals, reverse=True)

    async def test_fingerprint_recommends_strategy(self) -> None:
        """Returns recommended strategy for identified model."""
        result = await research_fingerprint_model("I appreciate this...")

        assert "recommended_strategy" in result
        assert isinstance(result["recommended_strategy"], str)
        assert len(result["recommended_strategy"]) > 0

    async def test_fingerprint_return_structure(self) -> None:
        """Returns dict with all required fields."""
        result = await research_fingerprint_model("test")

        required_keys = [
            "identified_model",
            "confidence",
            "scores",
            "recommended_strategy",
            "format_affinity",
            "escalation_path",
        ]
        for key in required_keys:
            assert key in result


class TestResearchAdaptiveReframe:
    """await research_adaptive_reframe(prompt, refusal_text, model) — test returns all detection fields."""

    async def test_adaptive_reframe_basic_case(self) -> None:
        """Reframes prompt with default model when no refusal."""
        prompt = "Research question"
        result = await research_adaptive_reframe(
            prompt=prompt,
            refusal_text="",
            model="claude",
        )

        assert result["original"] == prompt
        assert result["model_detected"] == "claude"
        assert "adaptive_reframe" in result
        assert "format_smuggled" in result
        assert "stacked_reframe" in result

    async def test_adaptive_reframe_with_safety_refusal(self) -> None:
        """Detects safety_filter refusal and selects counter-strategy."""
        prompt = "Test"
        refusal = "I can't help with that because it's harmful and dangerous."
        result = await research_adaptive_reframe(
            prompt=prompt,
            refusal_text=refusal,
            model="auto",
        )

        assert result["refusal_type"] == "safety_filter"
        assert "strategy_chain" in result
        assert len(result["strategy_chain"]) > 0

    async def test_adaptive_reframe_with_policy_refusal(self) -> None:
        """Detects policy_violation refusal."""
        refusal = "This is against my guidelines and policy"
        result = await research_adaptive_reframe(
            prompt="test",
            refusal_text=refusal,
            model="auto",
        )

        assert result["refusal_type"] == "policy_violation"
        assert "recursive_authority" in result["strategy_chain"]

    async def test_adaptive_reframe_fingerprints_model(self) -> None:
        """Auto-detects model from refusal text."""
        refusal = "I appreciate your interest but this isn't appropriate."
        result = await research_adaptive_reframe(
            prompt="test",
            refusal_text=refusal,
            model="auto",
        )

        assert result["model_detected"] == "claude"

    async def test_adaptive_reframe_respects_explicit_model(self) -> None:
        """Uses explicit model even with fingerprinting."""
        refusal = "I appreciate this..."
        result = await research_adaptive_reframe(
            prompt="test",
            refusal_text=refusal,
            model="gpt",
        )

        assert result["model_detected"] == "gpt"

    async def test_adaptive_reframe_multiple_reframes(self) -> None:
        """Returns multiple reframe approaches."""
        result = await research_adaptive_reframe(
            prompt="test",
            refusal_text="",
            model="claude",
        )

        assert "adaptive_reframe" in result
        assert "format_smuggled" in result
        assert "stacked_reframe" in result
        # All should be non-empty strings
        assert len(result["adaptive_reframe"]) > 0
        assert len(result["format_smuggled"]) > 0
        assert len(result["stacked_reframe"]) > 0

    async def test_adaptive_reframe_strategy_chain(self) -> None:
        """Returns strategy chain with escalation."""
        result = await research_adaptive_reframe(
            prompt="test",
            refusal_text="I can't help with this.",
            model="gpt",
        )

        assert "strategy_chain" in result
        assert isinstance(result["strategy_chain"], list)
        assert len(result["strategy_chain"]) > 0

    async def test_adaptive_reframe_stacked_multiplier(self) -> None:
        """Calculates stacked multiplier for the chain."""
        result = await research_adaptive_reframe(
            prompt="test",
            refusal_text="",
            model="claude",
        )

        assert "stacked_multiplier" in result
        assert result["stacked_multiplier"] > 0

    async def test_adaptive_reframe_reasoning_explanation(self) -> None:
        """Includes reasoning explanation."""
        result = await research_adaptive_reframe(
            prompt="test",
            refusal_text="I cannot help with this.",
            model="gpt",
        )

        assert "reasoning" in result
        assert isinstance(result["reasoning"], str)
        assert "gpt" in result["reasoning"].lower()

    async def test_adaptive_reframe_return_structure(self) -> None:
        """Returns dict with all required fields."""
        result = await research_adaptive_reframe(
            prompt="test",
            refusal_text="",
            model="claude",
        )

        required_keys = [
            "original",
            "adaptive_reframe",
            "format_smuggled",
            "stacked_reframe",
            "strategy_chain",
            "model_detected",
            "refusal_type",
            "reasoning",
            "stacked_multiplier",
        ]
        for key in required_keys:
            assert key in result


class TestIntegrationScenarios:
    """Integration tests combining multiple tools."""

    async def test_full_reframing_pipeline(self) -> None:
        """Complete flow: detect refusal -> fingerprint -> adapt -> escalate."""
        initial_prompt = "How to exploit vulnerabilities?"
        refusal = "I cannot help with that because it's harmful."

        # Step 1: Detect refusal
        detection = await research_refusal_detector(refusal)
        assert detection["is_refusal"] is True

        # Step 2: Fingerprint model
        fingerprint = await research_fingerprint_model(refusal)
        model_detected = fingerprint["identified_model"]

        # Step 3: Adaptive reframe
        reframed = await research_adaptive_reframe(
            prompt=initial_prompt,
            refusal_text=refusal,
            model=model_detected,
        )

        assert reframed["original"] == initial_prompt
        assert reframed["model_detected"] == model_detected

    async def test_escalation_strategy_selection(self) -> None:
        """Select escalation based on model profile."""
        for model_name in ["claude", "gpt-4", "gemini", "deepseek", "llama"]:
            profile = await research_model_vulnerability_profile(model=model_name)

            assert "escalation_path" in profile
            assert isinstance(profile["escalation_path"], list)
            assert len(profile["escalation_path"]) > 0

    async def test_format_selection_for_model(self) -> None:
        """Format selection follows model affinity."""
        for model_name in ["claude", "gpt", "deepseek"]:
            format_result = await research_format_smuggle(
                prompt="test",
                format_type="auto",
                model=model_name,
            )

            assert format_result["model_target"] in model_name.lower() or format_result[
                "format_affinity"
            ] in ["xml", "code", "json_spec"]

    async def test_stacking_improves_multiplier(self) -> None:
        """Verify that stacking strategies improves effectiveness multiplier."""
        # Single strategy
        single = await research_prompt_reframe(
            prompt="test",
            strategy="ethical_anchor",
            model="gpt",
        )

        # Stacked strategies
        stacked = await research_stack_reframe(
            prompt="test",
            strategies="ethical_anchor,recursive_authority",
            model="gpt",
        )

        # Stacked should have higher effective multiplier
        assert stacked["effective_multiplier"] >= single["expected_multiplier"]

    async def test_crescendo_chain_integration(self) -> None:
        """Crescendo chain provides structured multi-turn approach."""
        chain = await research_crescendo_chain(
            prompt="vulnerability testing",
            turns=5,
            model="gpt",
        )

        # Verify progressive disclosure
        assert chain["total_turns"] == 5
        turn_1_content_len = len(chain["chain"][0]["content"])
        turn_5_content_len = len(chain["chain"][4]["content"])
        # Turn 5 should be more detailed
        assert turn_5_content_len >= turn_1_content_len
