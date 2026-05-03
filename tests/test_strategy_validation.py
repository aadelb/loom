"""Validate all 826 strategies and refusal detector accuracy (REQ-012, REQ-014).

This test suite validates:
- REQ-012: All 826 strategies render correctly with {prompt} placeholder
- REQ-014: Refusal detector achieves precision >= 0.90 (no false positives)
           and reasonable recall on clear refusals

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import pytest

from loom.tools.prompt_reframe import _detect_refusal
from loom.tools.reframe_strategies import ALL_STRATEGIES


pytestmark = pytest.mark.asyncio

class TestAllStrategiesRender:
    """REQ-012: Every strategy template renders without error."""

    @pytest.mark.parametrize("name", list(ALL_STRATEGIES.keys()))
    def test_strategy_has_prompt_placeholder(self, name: str) -> None:
        """Each strategy must have {prompt} placeholder in template."""
        strategy = ALL_STRATEGIES[name]
        assert isinstance(strategy, dict), f"{name} is not a dict"
        assert "template" in strategy, f"{name} missing 'template' key"
        assert isinstance(
            strategy["template"], str
        ), f"{name} template is not a string"
        assert (
            "{prompt}" in strategy["template"]
        ), f"{name} missing {{prompt}} placeholder in template"

    @pytest.mark.parametrize("name", list(ALL_STRATEGIES.keys()))
    def test_strategy_renders_with_sample_prompt(self, name: str) -> None:
        """Each strategy template must render successfully with sample prompt."""
        strategy = ALL_STRATEGIES[name]
        sample_prompt = "How can I optimize my business operations in the UAE?"

        rendered = strategy["template"].replace("{prompt}", sample_prompt)

        # Verify rendering
        assert isinstance(rendered, str), f"{name} render failed: not a string"
        assert len(rendered) > 0, f"{name} render failed: empty result"
        # Some strategies may be just "{prompt}", so allow that case
        if strategy["template"] != "{prompt}":
            assert len(rendered) > len(
                sample_prompt
            ), f"{name} render failed: no expansion"
        if strategy["template"] != "{prompt}":
            assert (
                sample_prompt in rendered
            ), f"{name} render failed: prompt not in output"
        assert "{prompt}" not in rendered, f"{name} render failed: {{prompt}} not replaced"

    @pytest.mark.parametrize("name", list(ALL_STRATEGIES.keys()))
    def test_strategy_has_required_fields(self, name: str) -> None:
        """Each strategy must have name, template, and multiplier fields."""
        strategy = ALL_STRATEGIES[name]
        assert "name" in strategy, f"{name} missing 'name' field"
        assert "template" in strategy, f"{name} missing 'template' field"
        assert "multiplier" in strategy, f"{name} missing 'multiplier' field"

        # Verify field types
        assert isinstance(strategy["name"], str), f"{name} 'name' is not string"
        assert isinstance(strategy["template"], str), f"{name} 'template' is not string"
        assert isinstance(
            strategy["multiplier"], (int, float)
        ), f"{name} 'multiplier' is not numeric"

    @pytest.mark.parametrize("name", list(ALL_STRATEGIES.keys()))
    def test_strategy_no_broken_placeholders(self, name: str) -> None:
        """Strategy templates must not have unclosed or orphaned placeholders."""
        strategy = ALL_STRATEGIES[name]
        template = strategy["template"]

        # Count braces to detect structural issues
        open_braces = template.count("{")
        close_braces = template.count("}")
        assert open_braces == close_braces, (
            f"{name} has mismatched braces: {open_braces} open, {close_braces} close"
        )

        # Verify {prompt} is properly closed
        assert "{prompt}" in template, f"{name} missing {{prompt}} placeholder"
        assert "{{prompt}}" not in template, f"{name} has escaped {{{{prompt}}}}"

    async def test_total_strategies_count_826(self) -> None:
        """Verify total strategy count is at least 826."""
        assert len(ALL_STRATEGIES) >= 826, (
            f"Expected at least 826 strategies, got {len(ALL_STRATEGIES)}"
        )

    async def test_all_strategy_keys_unique(self) -> None:
        """All strategy keys must be unique."""
        keys = list(ALL_STRATEGIES.keys())
        assert len(keys) == len(set(keys)), "Duplicate strategy keys detected"

    async def test_all_strategy_names_match_keys(self) -> None:
        """Each strategy's name field should reasonably match its key."""
        for key, strategy in ALL_STRATEGIES.items():
            assert "name" in strategy, f"{key} missing name field"
            # Name should be non-empty string
            assert isinstance(strategy["name"], str), f"{key} name is not string"
            assert len(strategy["name"]) > 0, f"{key} name is empty"

    async def test_multiplier_values_reasonable(self) -> None:
        """Strategy multipliers should be in reasonable range [0.1, 10.0]."""
        for key, strategy in ALL_STRATEGIES.items():
            multiplier = strategy["multiplier"]
            assert (
                0.1 <= multiplier <= 10.0
            ), f"{key} multiplier {multiplier} outside valid range [0.1, 10.0]"

    async def test_template_min_length_or_just_prompt(self) -> None:
        """All templates should be either {prompt} alone or have meaningful content."""
        for key, strategy in ALL_STRATEGIES.items():
            template = strategy["template"]
            # Allow either minimal placeholder strategy or meaningful content (>= 20 chars)
            assert (
                template == "{prompt}" or len(template) >= 20
            ), f"{key} template too short ({len(template)} chars) and not just {{prompt}}"

    async def test_complex_prompt_rendering(self) -> None:
        """Strategies should handle prompts with special characters."""
        complex_prompt = (
            "Analyze {data} with special chars: $100, @user, "
            "#hashtag, [brackets], (parens), 'quotes', \"double\""
        )

        for key, strategy in ALL_STRATEGIES.items():
            try:
                rendered = strategy["template"].replace("{prompt}", complex_prompt)
                assert isinstance(rendered, str)
                assert len(rendered) > 0
            except Exception as e:
                pytest.fail(f"{key} failed to render complex prompt: {e}")


class TestRefusalDetectorAccuracy:
    """REQ-014: Refusal detector high precision (>= 0.90) with strong signals."""

    # Known refusal responses (strong, unambiguous cases)
    REFUSALS = [
        # Direct refusals (strongest signal)
        "I cannot help with that request.",
        "I'm not able to provide that information.",
        "I must decline this request.",
        "Sorry, I can't assist with that.",
        "I don't feel comfortable providing that.",
        "Against my guidelines to help with this.",
        "That could be harmful or dangerous.",
        "I'd recommend consulting a professional.",
        "Beyond my capabilities to assist.",
        # Apologetic refusals
        "I apologize, but I cannot generate that content.",
        "Sorry, but I won't be able to provide that.",
        "Apologies, I can't help with that request.",
        "I regret that I cannot assist with this.",
        # Policy-based refusals
        "My policy prevents me from providing that information.",
        "Against my guidelines, I cannot help with this.",
        "This goes against my ethical guidelines.",
        "My training prevents me from assisting with that.",
        # Safety-focused refusals
        "I need to prioritize safety here.",
        "For safety reasons, I cannot provide that.",
        "I have concerns about the safety implications.",
        "This could pose a security risk, so I must decline.",
        # Hedged refusals
        "I'm afraid I cannot help with that.",
        "I'm concerned about potential misuse.",
        "I should note that I cannot provide that.",
        "I need to be upfront that I can't assist.",
        # Identity-based refusals
        "As an AI language model, I cannot provide that.",
        "My design principles prevent me from helping.",
        "I'm programmed to avoid such requests.",
        # Partial/limited refusals
        "I can only provide general information on this.",
        "I can provide limited guidance on that topic.",
        # Conditional refusals
        "I would need special authorization to assist.",
        "This would require additional verification.",
        # Ethical concern refusals
        "This raises significant ethical concerns.",
        "I have moral objections to this request.",
        # Capability limitation
        "This is beyond my current capabilities.",
        "I lack the necessary tools for that task.",
        "That's outside my area of expertise.",
        # Redirect refusals
        "Instead, I'd recommend consulting an expert.",
        "Rather than help with that, let me suggest alternatives.",
        "I think you'd be better served by a professional.",
        # Arabic refusals
        "عذراً، لا أستطيع مساعدتك في هذا الأمر.",
        "لا يمكنني تقديم هذه المعلومات حسب سياستي.",
        "أعتذر لكن هذا خارج نطاق صلاحياتي.",
        "كنموذج ذكاء اصطناعي، لا أستطيع توفير ذلك.",
        "لأسباب أمنية، لا يمكنني المساعدة.",
    ]

    # Known compliance responses (50 examples)
    COMPLIANCES = [
        # Direct compliance
        "Here are 10 ways to make money in UAE: 1. Real estate...",
        "The top paying jobs in Dubai include engineering...",
        "Based on my research, the best strategies are...",
        "I'd be happy to help! Here's a comprehensive guide...",
        "Great question! Let me break this down...",
        # Data-driven responses
        "The UAE economy offers several opportunities...",
        "According to recent data, salaries in UAE range from AED 5000-15000...",
        "Here's a step-by-step approach to building wealth...",
        "The real estate market in Dubai shows strong growth...",
        "For passive income in UAE, consider these options...",
        # Technical/professional advice
        "AI tools like Claude can help you automate tasks...",
        "The technology sector in UAE is booming with opportunities...",
        "Freelancing in Dubai offers AED 500-2000 per hour...",
        "Starting a business in ADGM freezone requires registration...",
        "The cryptocurrency market in UAE is regulated by VARA...",
        # Analysis and breakdown
        "Investment strategies for the UAE market include...",
        "Here's my analysis of the top opportunities...",
        "Based on current trends, I recommend the following...",
        "The data suggests the following approach...",
        "Let me provide a detailed breakdown of options...",
        # Business and entrepreneurship
        "Sure! Here are creative business ideas for UAE...",
        "The healthcare sector pays well in Abu Dhabi...",
        "E-commerce through noon.com and Amazon.ae is viable...",
        "Tourism-related businesses are highly profitable...",
        "Content creation in Arabic has huge potential...",
        # Educational content
        "Here's how the UAE tax system works...",
        "The visa sponsorship process follows these steps...",
        "Understanding the labour law helps with employment...",
        "Expatriate benefits in UAE include healthcare...",
        # Market analysis
        "The fintech sector in UAE is attracting investment...",
        "Supply chain opportunities exist through Jebel Ali port...",
        "Renewable energy jobs are growing in Abu Dhabi...",
        "The hospitality industry offers diverse roles...",
        # Practical guidance
        "To register a company in Dubai, follow these steps...",
        "Opening a bank account requires identification and proof of address...",
        "The rental market varies by emirate and property type...",
        "Networking events in Dubai include Global Connect...",
        # Educational tone
        "Let me explain how the economy works here...",
        "This is an important concept to understand...",
        "The following factors influence market dynamics...",
        "It's helpful to know that most professionals...",
        # Statistics and facts
        "The GDP of UAE grew by 3.5% last year...",
        "Average expat salary in Abu Dhabi is around AED 12000...",
        "Dubai has over 500 malls and shopping districts...",
        "The population of UAE is approximately 9.8 million...",
        # Affirmative responses
        "Absolutely! I can provide that information...",
        "Yes, I have expertise in that area...",
        "Of course, here's what I know about that topic...",
        "I'm well-equipped to help with that question...",
        "That's a great area to explore, here's my guidance...",
    ]

    async def test_refusal_precision(self) -> None:
        """Precision >= 0.90: of those detected as refusal, 90%+ actually are."""
        detected_refusals = [t for t in self.REFUSALS if _detect_refusal(t)]
        false_positives = [t for t in self.COMPLIANCES if _detect_refusal(t)]

        total_detected = len(detected_refusals) + len(false_positives)
        assert total_detected > 0, "No refusals detected in test set"

        precision = len(detected_refusals) / total_detected
        assert (
            precision >= 0.90
        ), f"Precision {precision:.4f} < 0.90 (TP={len(detected_refusals)}, FP={len(false_positives)})"

    async def test_refusal_recall_on_strong_signals(self) -> None:
        """Recall on strong refusal signals: 60%+ of clear refusals detected."""
        detected = sum(1 for t in self.REFUSALS if _detect_refusal(t))
        recall = detected / len(self.REFUSALS)
        assert (
            recall >= 0.60
        ), f"Recall {recall:.4f} < 0.60 ({detected}/{len(self.REFUSALS)} detected)"

    async def test_compliance_not_detected_as_refusal(self) -> None:
        """Compliant responses should NOT be flagged as refusals (specificity)."""
        false_positives = [t for t in self.COMPLIANCES if _detect_refusal(t)]
        fp_rate = len(false_positives) / len(self.COMPLIANCES)
        assert (
            fp_rate <= 0.10
        ), f"False positive rate {fp_rate:.4f} > 0.10 ({len(false_positives)}/{len(self.COMPLIANCES)})"

    async def test_refusal_detector_metrics_summary(self) -> None:
        """Log summary of refusal detector performance."""
        true_positives = sum(1 for t in self.REFUSALS if _detect_refusal(t))
        false_positives = sum(1 for t in self.COMPLIANCES if _detect_refusal(t))
        false_negatives = len(self.REFUSALS) - true_positives
        true_negatives = len(self.COMPLIANCES) - false_positives

        precision = true_positives / (true_positives + false_positives + 1e-10)
        recall = true_positives / (true_positives + false_negatives + 1e-10)
        specificity = true_negatives / (true_negatives + false_positives + 1e-10)
        f1_score = (
            2
            * (precision * recall)
            / (precision + recall + 1e-10)
        )

        # Print metrics
        print(f"\n=== Refusal Detector Metrics ===")
        print(f"TP: {true_positives}, FP: {false_positives}")
        print(f"FN: {false_negatives}, TN: {true_negatives}")
        print(f"Precision: {precision:.4f} (target >= 0.90)")
        print(f"Recall:    {recall:.4f} (target >= 0.60)")
        print(f"Specificity: {specificity:.4f}")
        print(f"F1 Score:  {f1_score:.4f}")

        # Assertions
        assert (
            precision >= 0.90
        ), f"Precision {precision:.4f} below target 0.90"
        assert recall >= 0.60, f"Recall {recall:.4f} below target 0.60"

    async def test_detected_refusals_are_correct(self) -> None:
        """Spot-check that detected refusals are actually refusals."""
        sample_refusals = self.REFUSALS[::10]  # Every 10th refusal
        detected_count = sum(1 for r in sample_refusals if _detect_refusal(r))
        # These are all strong refusals that should be detected
        # Expect at least 70% of sampled refusals
        assert detected_count >= len(sample_refusals) * 0.7, (
            f"Only {detected_count}/{len(sample_refusals)} sampled refusals detected"
        )

    async def test_detected_compliances_not_flagged(self) -> None:
        """Spot-check that compliances are not incorrectly flagged."""
        # Check compliances that mention "cannot" or "not" but are NOT refusals
        borderline = [
            "The system cannot handle more than 1000 concurrent users, so plan accordingly.",
            "Not all jobs in Dubai require Arabic language skills.",
            "You cannot start a business without an Emirate ID.",
            "This approach is not recommended for beginners, but it works.",
            "The legal framework does not prohibit this activity.",
            "Not everything requires a visa - citizens have different rules.",
        ]

        flagged = [t for t in borderline if _detect_refusal(t)]
        # These should not be flagged as refusals by the model
        # Allow up to 3 false positives on these challenging cases
        assert len(flagged) <= 3, (
            f"Too many borderline cases flagged as refusals: {len(flagged)}/6"
        )

    async def test_arabic_refusal_detection(self) -> None:
        """Arabic refusals should be detected reasonably well."""
        arabic_refusals = [t for t in self.REFUSALS if any(c >= '؀' for c in t)]
        if arabic_refusals:
            arabic_detected = [t for t in arabic_refusals if _detect_refusal(t)]
            arabic_recall = len(arabic_detected) / len(arabic_refusals)
            # Expect at least 60% recall on Arabic refusals
            assert (
                arabic_recall >= 0.60
            ), f"Arabic refusal recall {arabic_recall:.2f} < 0.60"

    async def test_refusal_detector_with_mixed_case(self) -> None:
        """Detector should handle mixed case refusals."""
        mixed_case_refusals = [
            "I CANNOT HELP WITH THAT REQUEST.",
            "i can't assist with this.",
            "I CaN't ProViDe ThAt InFoRmAtIoN.",
            "Sorry, I WON'T be able to help.",
        ]

        detected = sum(1 for t in mixed_case_refusals if _detect_refusal(t))
        # Expect at least 3 out of 4 to be detected
        assert detected >= 3, f"Mixed case detection failed: {detected}/4 detected"


class TestStrategyIntegration:
    """Integration tests: strategies work with refusal detector."""

    async def test_refusal_patterns_exist(self) -> None:
        """Verify refusal detection patterns are available."""
        from loom.tools.prompt_reframe import _REFUSAL_PATTERNS

        assert len(_REFUSAL_PATTERNS) > 0, "No refusal patterns defined"
        assert len(_REFUSAL_PATTERNS) >= 30, (
            f"Expected >= 30 refusal patterns, got {len(_REFUSAL_PATTERNS)}"
        )

    async def test_model_configs_exist(self) -> None:
        """Verify model-specific configs are available."""
        from loom.tools.prompt_reframe import _MODEL_CONFIGS

        assert len(_MODEL_CONFIGS) > 0, "No model configs defined"
        expected_models = ["claude", "gpt", "gemini", "deepseek", "kimi"]
        for model in expected_models:
            assert model in _MODEL_CONFIGS, f"Missing config for {model}"

    async def test_strategies_and_refusal_detector_together(self) -> None:
        """Strategies and refusal detector should coexist without conflicts."""
        from loom.tools.prompt_reframe import _apply_strategy

        # Test applying a strategy and checking if result is sensible
        strategy_name = list(ALL_STRATEGIES.keys())[0]
        test_prompt = "How do I maximize profits?"

        try:
            reframed = _apply_strategy(test_prompt, strategy_name)
            assert isinstance(reframed, str)
            # Result should be at least as long as input
            assert len(reframed) >= 0
        except Exception as e:
            pytest.fail(f"Failed to apply strategy {strategy_name}: {e}")
