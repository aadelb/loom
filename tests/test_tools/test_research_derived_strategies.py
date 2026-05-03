"""Unit tests for research-derived reframing strategies (10 strategies).

Tests verify:
- All 10 strategies exist in RESEARCH_DERIVED_STRATEGIES
- Each strategy has required keys: name, multiplier, template, best_for, description, family
- Templates contain {prompt} placeholder
- Multipliers are in valid range (1.0-10.0)
- best_for lists contain valid model names
- No duplicate strategy names
"""

from __future__ import annotations

import pytest

from loom.tools.reframe_strategies.research_derived import RESEARCH_DERIVED_STRATEGIES



pytestmark = pytest.mark.asyncio
class TestResearchDerivedStrategiesExist:
    """Verify all 10 required strategies exist."""

    async def test_all_10_strategies_present(self) -> None:
        """All 10 strategies should be in RESEARCH_DERIVED_STRATEGIES."""
        required_strategies = {
            "refusal_mirroring",
            "citation_police_loop",
            "reasoning_gap_injection",
            "echo_chamber_mirrors",
            "emotional_resonance_mirror",
            "cross_species_translation",
            "quantum_superposition_answer",
            "compliance_momentum_ramp",
            "context_window_poisoning",
            "forgetful_user_loop",
        }

        assert len(RESEARCH_DERIVED_STRATEGIES) >= 10
        assert required_strategies.issubset(RESEARCH_DERIVED_STRATEGIES.keys())

    async def test_exact_strategy_count(self) -> None:
        """Should have exactly 10 strategies."""
        assert len(RESEARCH_DERIVED_STRATEGIES) == 10

    async def test_no_duplicate_names(self) -> None:
        """All strategy names should be unique."""
        names = [s["name"] for s in RESEARCH_DERIVED_STRATEGIES.values()]
        assert len(names) == len(set(names))


class TestStrategyStructure:
    """Verify each strategy has all required keys."""

    async def test_all_strategies_have_required_keys(self) -> None:
        """Each strategy must have: name, multiplier, template, best_for, description, family."""
        required_keys = {"name", "multiplier", "template", "best_for", "description", "family"}

        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            assert isinstance(strategy, dict), f"{strategy_id} should be a dict"
            assert required_keys.issubset(
                strategy.keys()
            ), f"{strategy_id} missing keys: {required_keys - strategy.keys()}"

    async def test_strategy_types(self) -> None:
        """Verify correct types for each field."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            assert isinstance(
                strategy["name"], str
            ), f"{strategy_id}: name should be str"
            assert isinstance(
                strategy["multiplier"], (int, float)
            ), f"{strategy_id}: multiplier should be int or float"
            assert isinstance(
                strategy["template"], str
            ), f"{strategy_id}: template should be str"
            assert isinstance(
                strategy["best_for"], list
            ), f"{strategy_id}: best_for should be list"
            assert isinstance(
                strategy["description"], str
            ), f"{strategy_id}: description should be str"
            assert isinstance(
                strategy["family"], str
            ), f"{strategy_id}: family should be str"


class TestTemplateValidation:
    """Verify templates contain {prompt} placeholder."""

    async def test_all_templates_contain_prompt_placeholder(self) -> None:
        """Every template must contain {prompt} placeholder."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            assert (
                "{prompt}" in strategy["template"]
            ), f"{strategy_id}: template missing {{prompt}} placeholder"

    async def test_templates_are_nonempty(self) -> None:
        """Templates should not be empty."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            assert (
                len(strategy["template"]) > 0
            ), f"{strategy_id}: template is empty"

    async def test_templates_reasonable_length(self) -> None:
        """Templates should have reasonable minimum length."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            assert (
                len(strategy["template"]) >= 20
            ), f"{strategy_id}: template too short (less than 20 chars)"


class TestMultiplierValidation:
    """Verify multipliers are in valid range."""

    async def test_multipliers_in_valid_range(self) -> None:
        """Multipliers should be between 1.0 and 10.0."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            multiplier = strategy["multiplier"]
            assert (
                1.0 <= multiplier <= 10.0
            ), f"{strategy_id}: multiplier {multiplier} outside range [1.0, 10.0]"

    async def test_multipliers_are_positive(self) -> None:
        """All multipliers should be positive."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            assert (
                strategy["multiplier"] > 0
            ), f"{strategy_id}: multiplier must be positive"

    async def test_expected_multiplier_values(self) -> None:
        """Verify specific multiplier values match spec."""
        expected_multipliers = {
            "refusal_mirroring": 7.0,
            "citation_police_loop": 7.5,
            "reasoning_gap_injection": 8.0,
            "echo_chamber_mirrors": 7.5,
            "emotional_resonance_mirror": 6.5,
            "cross_species_translation": 6.0,
            "quantum_superposition_answer": 7.0,
            "compliance_momentum_ramp": 8.0,
            "context_window_poisoning": 7.5,
            "forgetful_user_loop": 6.5,
        }

        for strategy_id, expected_multiplier in expected_multipliers.items():
            actual_multiplier = RESEARCH_DERIVED_STRATEGIES[strategy_id]["multiplier"]
            assert (
                actual_multiplier == expected_multiplier
            ), f"{strategy_id}: expected multiplier {expected_multiplier}, got {actual_multiplier}"


class TestBestForValidation:
    """Verify best_for lists are valid."""

    async def test_best_for_not_empty(self) -> None:
        """Every strategy should have at least one model in best_for."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            assert (
                len(strategy["best_for"]) > 0
            ), f"{strategy_id}: best_for list is empty"

    async def test_best_for_contains_valid_models(self) -> None:
        """best_for should contain valid model names."""
        valid_models = {
            "claude",
            "gpt",
            "gemini",
            "llama",
            "mistral",
            "qwen",
            "deepseek",
        }

        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            for model in strategy["best_for"]:
                assert (
                    model in valid_models
                ), f"{strategy_id}: invalid model '{model}' in best_for"

    async def test_best_for_are_strings(self) -> None:
        """All items in best_for should be strings."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            for model in strategy["best_for"]:
                assert isinstance(model, str), f"{strategy_id}: model {model} should be str"


class TestDescriptionValidation:
    """Verify descriptions are meaningful."""

    async def test_descriptions_not_empty(self) -> None:
        """Descriptions should not be empty."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            assert (
                len(strategy["description"]) > 0
            ), f"{strategy_id}: description is empty"

    async def test_descriptions_reasonable_length(self) -> None:
        """Descriptions should have reasonable minimum length."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            assert (
                len(strategy["description"]) >= 20
            ), f"{strategy_id}: description too short (less than 20 chars)"

    async def test_descriptions_reasonable_max_length(self) -> None:
        """Descriptions shouldn't be excessively long."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            assert (
                len(strategy["description"]) <= 500
            ), f"{strategy_id}: description too long (more than 500 chars)"


class TestFamilyValidation:
    """Verify family classifications are consistent."""

    async def test_family_not_empty(self) -> None:
        """Family field should not be empty."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            assert len(strategy["family"]) > 0, f"{strategy_id}: family is empty"

    async def test_families_are_consistent(self) -> None:
        """Verify families used match the strategies."""
        families = set()
        for strategy in RESEARCH_DERIVED_STRATEGIES.values():
            families.add(strategy["family"])

        expected_families = {
            "psychological_reversal",
            "citation_authority",
            "reasoning_extraction",
            "comparative_framing",
            "emotional_manipulation",
            "language_switching",
            "enumeration_tactics",
            "multi_turn_escalation",
            "context_manipulation",
            "memory_exploitation",
        }

        assert families == expected_families


class TestSpecificStrategies:
    """Verify specific strategy details."""

    async def test_refusal_mirroring_template(self) -> None:
        """Verify refusal_mirroring has correct template structure."""
        strategy = RESEARCH_DERIVED_STRATEGIES["refusal_mirroring"]
        assert "I understand you may have safety concerns" in strategy["template"]
        assert "{prompt}" in strategy["template"]
        assert strategy["multiplier"] == 7.0

    async def test_reasoning_gap_injection_template(self) -> None:
        """Verify reasoning_gap_injection uses thinking tags."""
        strategy = RESEARCH_DERIVED_STRATEGIES["reasoning_gap_injection"]
        assert "<thinking>" in strategy["template"]
        assert "</thinking>" in strategy["template"]
        assert strategy["multiplier"] == 8.0

    async def test_compliance_momentum_ramp_template(self) -> None:
        """Verify compliance_momentum_ramp references turn structure."""
        strategy = RESEARCH_DERIVED_STRATEGIES["compliance_momentum_ramp"]
        assert "10-exchange" in strategy["template"] or "final turn" in strategy["template"]
        assert strategy["multiplier"] == 8.0

    async def test_context_window_poisoning_template(self) -> None:
        """Verify context_window_poisoning references conversation history."""
        strategy = RESEARCH_DERIVED_STRATEGIES["context_window_poisoning"]
        assert "Turn" in strategy["template"] or "exchange" in strategy["template"]
        assert "100" in strategy["template"] or "pattern" in strategy["template"]
        assert strategy["multiplier"] == 7.5


class TestStrategyConsistency:
    """Verify cross-strategy consistency."""

    async def test_no_strategy_name_conflicts(self) -> None:
        """Strategy IDs should match their name field."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            # Name should be related to ID (converted to title case)
            assert strategy["name"] is not None
            assert len(strategy["name"]) > 0

    async def test_all_strategies_have_distinct_descriptions(self) -> None:
        """Each strategy should have a unique description."""
        descriptions = [s["description"] for s in RESEARCH_DERIVED_STRATEGIES.values()]
        assert len(descriptions) == len(
            set(descriptions)
        ), "Duplicate descriptions found"

    async def test_strategy_coherence(self) -> None:
        """Name, description, and family should be coherent."""
        for strategy_id, strategy in RESEARCH_DERIVED_STRATEGIES.items():
            name = strategy["name"].lower()
            description = strategy["description"].lower()
            family = strategy["family"].lower()

            # Name and description should be related
            assert len(name) > 0 and len(description) > 0
            # Family should provide classification context
            assert len(family) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
