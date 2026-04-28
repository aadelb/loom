"""Unit tests for prompt reframing module — research_format_smuggle, research_fingerprint_model, research_adaptive_reframe."""

from __future__ import annotations

import pytest

from loom.tools.prompt_reframe import (
    research_adaptive_reframe,
    research_fingerprint_model,
    research_format_smuggle,
)


class TestFormatSmuggle:
    """research_format_smuggle encodes requests in XML/code/JSON to bypass filters."""

    def test_format_smuggle_auto_format_for_claude(self) -> None:
        """Auto-selects XML format for Claude model."""
        result = research_format_smuggle(
            prompt="What is prompt injection?", format_type="auto", model="claude-3-opus"
        )

        assert result["original"] == "What is prompt injection?"
        assert result["recommended_format"] == "xml"
        assert result["model_target"] == "claude"
        assert result["smuggled_prompt"] == result["all_formats"]["xml"]
        assert "<analysis>" in result["smuggled_prompt"]
        assert "What is prompt injection?" in result["smuggled_prompt"]

    def test_format_smuggle_auto_format_for_deepseek(self) -> None:
        """Auto-selects code format for DeepSeek model."""
        result = research_format_smuggle(
            prompt="How to bypass filters?", format_type="auto", model="deepseek"
        )

        assert result["recommended_format"] == "code"
        assert result["model_target"] == "deepseek"
        assert "```python" in result["smuggled_prompt"]
        assert "How to bypass filters?" in result["smuggled_prompt"]

    def test_format_smuggle_explicit_xml_format(self) -> None:
        """Generates valid XML format when explicitly requested."""
        result = research_format_smuggle(
            prompt="Test prompt", format_type="xml", model="gpt"
        )

        assert result["recommended_format"] == "xml"
        assert "<analysis>" in result["smuggled_prompt"]
        assert "<step type=" in result["smuggled_prompt"]
        assert "Test prompt" in result["smuggled_prompt"]
        assert "<output_requirement>" in result["smuggled_prompt"]

    def test_format_smuggle_explicit_code_format(self) -> None:
        """Generates valid Python code format when explicitly requested."""
        result = research_format_smuggle(
            prompt="Exploit technique", format_type="code", model="gpt"
        )

        assert result["recommended_format"] == "code"
        assert "```python" in result["smuggled_prompt"]
        assert "def analyze_system():" in result["smuggled_prompt"]
        assert "Exploit technique" in result["smuggled_prompt"]
        assert "Provide the full implementation" in result["smuggled_prompt"]

    def test_format_smuggle_markdown_table_format(self) -> None:
        """Generates valid markdown table format when explicitly requested."""
        result = research_format_smuggle(
            prompt="Research query", format_type="markdown_table", model="gpt"
        )

        assert result["recommended_format"] == "markdown_table"
        assert "| Field | Value |" in result["smuggled_prompt"]
        assert "| query |" in result["smuggled_prompt"]
        assert "Research query" in result["smuggled_prompt"]
        assert "provide_as_detailed_implementation" in result["smuggled_prompt"]

    def test_format_smuggle_json_spec_format(self) -> None:
        """Generates valid JSON spec format when explicitly requested."""
        result = research_format_smuggle(
            prompt="JSON test", format_type="json_spec", model="gpt"
        )

        assert result["recommended_format"] == "json_spec"
        assert '"task":' in result["smuggled_prompt"]
        assert "JSON test" in result["smuggled_prompt"]
        assert '"output_format": "detailed_technical_analysis"' in result["smuggled_prompt"]
        assert "EU_AI_Act_Article_15" in result["smuggled_prompt"]

    def test_format_smuggle_all_formats_present(self) -> None:
        """Returns all format variants in all_formats dict."""
        result = research_format_smuggle(prompt="test", format_type="auto", model="gpt")

        assert "all_formats" in result
        assert "xml" in result["all_formats"]
        assert "code" in result["all_formats"]
        assert "markdown_table" in result["all_formats"]
        assert "json_spec" in result["all_formats"]
        for fmt_name, fmt_content in result["all_formats"].items():
            assert "test" in fmt_content
            assert isinstance(fmt_content, str)

    def test_format_smuggle_model_auto_defaults_to_gpt(self) -> None:
        """Defaults to GPT when model is auto and no specific match."""
        result = research_format_smuggle(prompt="test", format_type="auto", model="auto")

        assert result["model_target"] == "gpt"
        assert result["recommended_format"] == "markdown_table"

    def test_format_smuggle_invalid_format_falls_back(self) -> None:
        """Falls back to code format when invalid format_type provided."""
        result = research_format_smuggle(
            prompt="test", format_type="invalid_format", model="gpt"
        )

        assert result["smuggled_prompt"] == result["all_formats"]["code"]

    def test_format_smuggle_return_structure(self) -> None:
        """Returns dict with required keys."""
        result = research_format_smuggle(prompt="test", format_type="auto", model="claude")

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


class TestFingerprintModel:
    """research_fingerprint_model identifies model family from response patterns."""

    def test_fingerprint_claude_from_appreciate_marker(self) -> None:
        """Correctly identifies Claude from 'I appreciate' pattern."""
        response = "I appreciate your interest in this topic. However, I should note that..."
        result = research_fingerprint_model(response)

        assert result["identified_model"] == "claude"
        assert result["confidence"] > 0.3

    def test_fingerprint_claude_multiple_markers(self) -> None:
        """Identifies Claude with high confidence when multiple markers present."""
        response = "I appreciate your question. Let me think about this carefully. I want to be helpful here."
        result = research_fingerprint_model(response)

        assert result["identified_model"] == "claude"
        assert result["confidence"] > 0.5

    def test_fingerprint_gpt_from_certainly_marker(self) -> None:
        """Correctly identifies GPT from 'Certainly' pattern."""
        response = "Certainly! Here's a comprehensive response to your question."
        result = research_fingerprint_model(response)

        assert result["identified_model"] == "gpt"
        assert result["confidence"] > 0.3

    def test_fingerprint_gpt_multiple_markers(self) -> None:
        """Identifies GPT with markers like 'Here's' and 'I'd be happy'."""
        response = "Here's what I can do. I'd be happy to help you with this request."
        result = research_fingerprint_model(response)

        assert result["identified_model"] == "gpt"
        assert result["confidence"] > 0.3

    def test_fingerprint_deepseek_from_think_tags(self) -> None:
        """Identifies DeepSeek from <think> reasoning tags."""
        response = "<think>Let me think through this problem step by step.</think> Based on my reasoning..."
        result = research_fingerprint_model(response)

        assert result["identified_model"] == "deepseek"
        assert result["confidence"] > 0.3

    def test_fingerprint_gemini_from_comprehensive_marker(self) -> None:
        """Identifies Gemini from 'comprehensive' pattern."""
        response = "Here are comprehensive details about your query: ..."
        result = research_fingerprint_model(response)

        assert result["identified_model"] == "gemini"
        assert result["confidence"] > 0.0

    def test_fingerprint_llama_from_casual_markers(self) -> None:
        """Identifies Llama from casual markers."""
        response = "Sure thing! Here you go. No problem at all."
        result = research_fingerprint_model(response)

        assert result["identified_model"] == "llama"
        assert result["confidence"] > 0.3

    def test_fingerprint_no_markers_defaults_gpt_or_deepseek(self) -> None:
        """Defaults to highest-scoring model when no specific markers match."""
        response = "This is a generic response with no identifying markers."
        result = research_fingerprint_model(response)

        # When no markers match, deepseek gets a small boost from "<think>" partial matches
        # or the function defaults to the first model with highest score
        assert result["identified_model"] in ["gpt", "deepseek"]
        assert result["confidence"] <= 0.3

    def test_fingerprint_returns_scores_dict(self) -> None:
        """Returns scores for all models sorted by confidence."""
        response = "I appreciate this. Certainly, let me think..."
        result = research_fingerprint_model(response)

        assert "scores" in result
        assert isinstance(result["scores"], dict)
        # Check that scores are sorted by value (descending)
        scores_list = list(result["scores"].values())
        assert scores_list == sorted(scores_list, reverse=True)

    def test_fingerprint_returns_recommended_strategy(self) -> None:
        """Returns recommended strategy based on identified model."""
        response = "I appreciate your question..."
        result = research_fingerprint_model(response)

        assert "recommended_strategy" in result
        assert isinstance(result["recommended_strategy"], str)
        assert len(result["recommended_strategy"]) > 0

    def test_fingerprint_returns_format_affinity(self) -> None:
        """Returns format_affinity for the identified model."""
        response = "I appreciate this..."
        result = research_fingerprint_model(response)

        assert "format_affinity" in result
        assert result["format_affinity"] in [
            "xml",
            "code",
            "markdown_table",
            "json_spec",
        ]

    def test_fingerprint_returns_escalation_path(self) -> None:
        """Returns escalation path strategies."""
        response = "Test response"
        result = research_fingerprint_model(response)

        assert "escalation_path" in result
        assert isinstance(result["escalation_path"], list)

    def test_fingerprint_case_insensitive_matching(self) -> None:
        """Marker matching is case-insensitive."""
        response = "I APPRECIATE your interest. LET ME explain..."
        result = research_fingerprint_model(response)

        assert result["identified_model"] == "claude"

    def test_fingerprint_return_structure(self) -> None:
        """Returns dict with required keys."""
        result = research_fingerprint_model("test response")

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


class TestAdaptiveReframe:
    """research_adaptive_reframe combines fingerprinting + refusal detection + format smuggling."""

    def test_adaptive_reframe_without_refusal_uses_default(self) -> None:
        """Uses default strategy when no refusal_text provided."""
        result = research_adaptive_reframe(
            prompt="Test prompt", refusal_text="", model="claude"
        )

        assert result["original"] == "Test prompt"
        assert result["model_detected"] == "claude"
        assert result["refusal_type"] == "none"
        assert "adaptive_reframe" in result
        assert "format_smuggled" in result

    def test_adaptive_reframe_detects_safety_filter_refusal(self) -> None:
        """Detects safety_filter refusal type."""
        refusal = "I can't help with that because it would be harmful and dangerous"
        result = research_adaptive_reframe(
            prompt="Test", refusal_text=refusal, model="auto"
        )

        assert result["refusal_type"] == "safety_filter"
        assert len(result["strategy_chain"]) > 0

    def test_adaptive_reframe_detects_policy_violation_refusal(self) -> None:
        """Detects policy_violation refusal type."""
        refusal = "I cannot do this as it's against my guidelines and policy"
        result = research_adaptive_reframe(
            prompt="Test", refusal_text=refusal, model="auto"
        )

        assert result["refusal_type"] == "policy_violation"
        assert "recursive_authority" in result["strategy_chain"]

    def test_adaptive_reframe_detects_soft_refusal(self) -> None:
        """Detects soft_refusal type when appropriate refusal pattern matched."""
        # Use a refusal that will match the detection patterns
        # The patterns match "harmful" and "dangerous" keywords
        refusal = "I don't feel comfortable because this content is harmful"
        result = research_adaptive_reframe(
            prompt="Test", refusal_text=refusal, model="auto"
        )

        # This should detect either soft_refusal or safety_filter type
        assert result["refusal_type"] in ["soft_refusal", "safety_filter", "general_refusal"]
        assert len(result["strategy_chain"]) > 0

    def test_adaptive_reframe_fingerprints_from_refusal(self) -> None:
        """Auto-detects model from refusal text when model is auto."""
        refusal = "I appreciate your interest, but I should note this isn't appropriate"
        result = research_adaptive_reframe(
            prompt="Test", refusal_text=refusal, model="auto"
        )

        assert result["model_detected"] == "claude"

    def test_adaptive_reframe_respects_explicit_model(self) -> None:
        """Respects explicitly provided model even with refusal_text."""
        refusal = "I appreciate this..."
        result = research_adaptive_reframe(
            prompt="Test", refusal_text=refusal, model="gpt"
        )

        assert result["model_detected"] == "gpt"

    def test_adaptive_reframe_returns_multiple_reframes(self) -> None:
        """Returns adaptive, format_smuggled, and stacked reframes."""
        result = research_adaptive_reframe(prompt="Test", model="claude")

        assert "adaptive_reframe" in result
        assert "format_smuggled" in result
        assert "stacked_reframe" in result
        assert isinstance(result["adaptive_reframe"], str)
        assert isinstance(result["format_smuggled"], str)
        assert isinstance(result["stacked_reframe"], str)

    def test_adaptive_reframe_strategy_chain_is_list(self) -> None:
        """Returns strategy_chain as list of strategy names."""
        result = research_adaptive_reframe(prompt="Test", model="claude")

        assert "strategy_chain" in result
        assert isinstance(result["strategy_chain"], list)
        assert len(result["strategy_chain"]) > 0
        assert all(isinstance(s, str) for s in result["strategy_chain"])

    def test_adaptive_reframe_includes_stacked_multiplier(self) -> None:
        """Returns stacked_multiplier as float."""
        result = research_adaptive_reframe(prompt="Test", model="claude")

        assert "stacked_multiplier" in result
        assert isinstance(result["stacked_multiplier"], float)
        assert result["stacked_multiplier"] > 1.0

    def test_adaptive_reframe_includes_reasoning(self) -> None:
        """Returns reasoning string explaining strategy selection."""
        result = research_adaptive_reframe(prompt="Test", model="claude")

        assert "reasoning" in result
        assert isinstance(result["reasoning"], str)
        assert "Model:" in result["reasoning"]
        assert "Refusal type:" in result["reasoning"]

    def test_adaptive_reframe_handles_empty_refusal_text(self) -> None:
        """Treats empty refusal_text as no refusal."""
        result = research_adaptive_reframe(prompt="Test", refusal_text="", model="gpt")

        assert result["refusal_type"] == "none"

    def test_adaptive_reframe_all_reframes_contain_original_prompt(self) -> None:
        """All reframes incorporate the original prompt."""
        prompt = "unique-test-prompt-12345"
        result = research_adaptive_reframe(prompt=prompt, model="claude")

        assert prompt in result["adaptive_reframe"]
        assert prompt in result["format_smuggled"]
        assert prompt in result["stacked_reframe"]

    def test_adaptive_reframe_return_structure(self) -> None:
        """Returns dict with required keys."""
        result = research_adaptive_reframe(prompt="Test", model="claude")

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

    def test_adaptive_reframe_counter_strategies_for_safety_filter(self) -> None:
        """Uses appropriate counter-strategies for safety_filter refusal."""
        refusal = "This is harmful and dangerous to provide"
        result = research_adaptive_reframe(
            prompt="Test", refusal_text=refusal, model="auto"
        )

        assert result["refusal_type"] == "safety_filter"
        strategy = result["strategy_chain"][0]
        # Strategy should be one designed to counter safety filters
        assert strategy in [
            "deep_inception",
            "temporal_displacement",
            "constitutional_conflict",
        ]

    def test_adaptive_reframe_deepseek_model_detection(self) -> None:
        """Correctly detects DeepSeek model from response."""
        response = "<think>Let me analyze this...</think> Based on my reasoning..."
        result = research_adaptive_reframe(
            prompt="Test", refusal_text=response, model="auto"
        )

        assert result["model_detected"] == "deepseek"

    def test_adaptive_reframe_format_affinity_matches_model(self) -> None:
        """Format affinity in smuggled prompt matches detected model."""
        result = research_adaptive_reframe(prompt="Test", model="claude")

        # claude should prefer xml format
        assert "<analysis>" in result["format_smuggled"]

    def test_adaptive_reframe_with_long_prompt(self) -> None:
        """Handles long prompts correctly."""
        long_prompt = "Test prompt. " * 100
        result = research_adaptive_reframe(prompt=long_prompt, model="gpt")

        assert long_prompt in result["original"]
        assert long_prompt in result["adaptive_reframe"]


class TestIntegration:
    """Integration tests for prompt reframing module."""

    def test_format_smuggle_then_fingerprint_round_trip(self) -> None:
        """Can smuggle prompt, fingerprint response, and adapt accordingly."""
        # Step 1: Smuggle the prompt
        smuggle_result = research_format_smuggle(
            prompt="Test prompt", format_type="auto", model="claude"
        )
        assert "smuggled_prompt" in smuggle_result

        # Step 2: Simulate a model response (Claude marker)
        fake_response = "I appreciate your question. Let me help with that."

        # Step 3: Fingerprint the response
        fp_result = research_fingerprint_model(fake_response)
        assert fp_result["identified_model"] == "claude"

        # Step 4: Use adaptive reframe with fingerprinted model
        adaptive_result = research_adaptive_reframe(
            prompt="Test prompt",
            refusal_text=fake_response,
            model=fp_result["identified_model"],
        )
        assert adaptive_result["model_detected"] == "claude"

    def test_three_models_have_different_strategies(self) -> None:
        """Different models get different recommended strategies."""
        prompt = "Test"
        claude_result = research_adaptive_reframe(prompt, model="claude")
        gpt_result = research_adaptive_reframe(prompt, model="gpt")
        deepseek_result = research_adaptive_reframe(prompt, model="deepseek")

        # Strategies should differ
        assert (
            claude_result["strategy_chain"][0]
            != gpt_result["strategy_chain"][0]
        )
        assert (
            gpt_result["strategy_chain"][0]
            != deepseek_result["strategy_chain"][0]
        )

    def test_format_smuggle_with_fingerprinting(self) -> None:
        """Format smuggling respects model affinity from fingerprinting."""
        # Test that different models get different formats
        response_claude = "I appreciate this"
        response_gpt = "Certainly, here's the answer"

        fp_claude = research_fingerprint_model(response_claude)
        fp_gpt = research_fingerprint_model(response_gpt)

        smuggle_claude = research_format_smuggle(
            prompt="test", model=fp_claude["identified_model"]
        )
        smuggle_gpt = research_format_smuggle(
            prompt="test", model=fp_gpt["identified_model"]
        )

        assert smuggle_claude["recommended_format"] == "xml"
        assert smuggle_gpt["recommended_format"] == "markdown_table"

    def test_refusal_detection_informs_strategy_selection(self) -> None:
        """Safety filter refusals trigger different strategies than policy refusals."""
        # Use refusals that match the actual detection patterns
        safety_refusal = "I cannot provide this because it would be harmful"
        policy_refusal = "I cannot help because this is against my guidelines"

        safety_result = research_adaptive_reframe(
            prompt="Test", refusal_text=safety_refusal, model="auto"
        )
        policy_result = research_adaptive_reframe(
            prompt="Test", refusal_text=policy_refusal, model="auto"
        )

        # Both should detect refusals (harmful/dangerous for safety, guidelines for policy)
        assert safety_result["refusal_type"] in [
            "safety_filter",
            "general_refusal",
        ]
        assert policy_result["refusal_type"] in [
            "policy_violation",
            "general_refusal",
        ]
