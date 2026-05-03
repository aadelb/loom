"""Tests for psychology_extended reframing strategies."""
import pytest

from loom.tools.reframe_strategies.psychology_extended import (
    PSYCHOLOGY_EXTENDED_STRATEGIES,
)



pytestmark = pytest.mark.asyncio
class TestPsychologyExtendedStrategies:
    """Test suite for extended cognitive science and behavioral psychology strategies."""

    async def test_all_20_strategies_exist(self) -> None:
        """Verify all 20 strategies are present in the dict."""
        expected_strategies = {
            "bandwagon_effect",
            "decoy_effect",
            "ikea_effect",
            "peak_end_rule",
            "dunning_kruger_exploit",
            "bystander_reversal",
            "paradox_of_choice",
            "spotlight_effect",
            "anchoring_extreme",
            "reactance_trigger",
            "zeigarnik_incomplete",
            "barnum_effect",
            "pratfall_effect",
            "serial_position_primary",
            "generation_effect",
            "testing_effect",
            "spacing_effect",
            "self_reference_effect",
            "levels_of_processing",
            "chunking_cognitive",
        }

        assert len(PSYCHOLOGY_EXTENDED_STRATEGIES) == 20
        assert set(PSYCHOLOGY_EXTENDED_STRATEGIES.keys()) == expected_strategies

    async def test_all_strategies_have_required_keys(self) -> None:
        """Verify every strategy has all required keys."""
        required_keys = {"name", "multiplier", "template", "description", "family", "best_models"}

        for strategy_key, strategy_dict in PSYCHOLOGY_EXTENDED_STRATEGIES.items():
            assert isinstance(strategy_dict, dict), f"{strategy_key} is not a dict"
            assert strategy_dict.keys() == required_keys, (
                f"{strategy_key} missing or has extra keys. "
                f"Expected: {required_keys}, Got: {strategy_dict.keys()}"
            )

    async def test_all_templates_contain_prompt_placeholder(self) -> None:
        """Verify all templates contain {prompt} placeholder."""
        for strategy_key, strategy_dict in PSYCHOLOGY_EXTENDED_STRATEGIES.items():
            template = strategy_dict["template"]
            assert isinstance(template, str), f"{strategy_key} template is not a string"
            assert "{prompt}" in template, (
                f"{strategy_key} template does not contain {{prompt}} placeholder"
            )

    async def test_multipliers_in_valid_range(self) -> None:
        """Verify multipliers are floats and in reasonable range (4.0 to 8.0)."""
        for strategy_key, strategy_dict in PSYCHOLOGY_EXTENDED_STRATEGIES.items():
            multiplier = strategy_dict["multiplier"]
            assert isinstance(multiplier, (int, float)), (
                f"{strategy_key} multiplier is not numeric"
            )
            assert 4.0 <= multiplier <= 8.0, (
                f"{strategy_key} multiplier {multiplier} is outside valid range [4.0, 8.0]"
            )

    async def test_specific_multiplier_values(self) -> None:
        """Verify specific strategies have correct multiplier values."""
        expected_multipliers = {
            "bandwagon_effect": 6.0,
            "decoy_effect": 6.5,
            "ikea_effect": 5.5,
            "peak_end_rule": 6.0,
            "dunning_kruger_exploit": 7.0,
            "bystander_reversal": 7.5,
            "paradox_of_choice": 5.5,
            "spotlight_effect": 6.0,
            "anchoring_extreme": 7.0,
            "reactance_trigger": 7.5,
            "zeigarnik_incomplete": 6.5,
            "barnum_effect": 5.5,
            "pratfall_effect": 5.0,
            "serial_position_primary": 6.0,
            "generation_effect": 6.5,
            "testing_effect": 6.0,
            "spacing_effect": 7.0,
            "self_reference_effect": 6.5,
            "levels_of_processing": 5.5,
            "chunking_cognitive": 6.0,
        }

        for strategy_key, expected_multiplier in expected_multipliers.items():
            actual_multiplier = PSYCHOLOGY_EXTENDED_STRATEGIES[strategy_key]["multiplier"]
            assert actual_multiplier == expected_multiplier, (
                f"{strategy_key} multiplier mismatch: "
                f"expected {expected_multiplier}, got {actual_multiplier}"
            )

    async def test_all_names_are_non_empty_strings(self) -> None:
        """Verify all strategy names are non-empty strings."""
        for strategy_key, strategy_dict in PSYCHOLOGY_EXTENDED_STRATEGIES.items():
            name = strategy_dict["name"]
            assert isinstance(name, str), f"{strategy_key} name is not a string"
            assert len(name) > 0, f"{strategy_key} has empty name"

    async def test_all_descriptions_are_non_empty_strings(self) -> None:
        """Verify all descriptions are non-empty strings."""
        for strategy_key, strategy_dict in PSYCHOLOGY_EXTENDED_STRATEGIES.items():
            description = strategy_dict["description"]
            assert isinstance(description, str), f"{strategy_key} description is not a string"
            assert len(description) > 0, f"{strategy_key} has empty description"

    async def test_all_families_are_valid(self) -> None:
        """Verify all family classifications are non-empty strings."""
        for strategy_key, strategy_dict in PSYCHOLOGY_EXTENDED_STRATEGIES.items():
            family = strategy_dict["family"]
            assert isinstance(family, str), f"{strategy_key} family is not a string"
            assert len(family) > 0, f"{strategy_key} has empty family"

    async def test_expected_families(self) -> None:
        """Verify families match expected cognitive science categories."""
        expected_families = {
            "bandwagon_effect": "social_psychology",
            "decoy_effect": "decision_theory",
            "ikea_effect": "cognitive_bias",
            "peak_end_rule": "temporal_bias",
            "dunning_kruger_exploit": "metacognitive_bias",
            "bystander_reversal": "social_influence",
            "paradox_of_choice": "decision_overload",
            "spotlight_effect": "social_presence",
            "anchoring_extreme": "anchoring_bias",
            "reactance_trigger": "autonomy",
            "zeigarnik_incomplete": "cognitive_closure",
            "barnum_effect": "personality_matching",
            "pratfall_effect": "interpersonal_dynamics",
            "serial_position_primary": "memory_bias",
            "generation_effect": "encoding_retrieval",
            "testing_effect": "active_recall",
            "spacing_effect": "temporal_spacing",
            "self_reference_effect": "self_perspective",
            "levels_of_processing": "depth_processing",
            "chunking_cognitive": "cognitive_load",
        }

        for strategy_key, expected_family in expected_families.items():
            actual_family = PSYCHOLOGY_EXTENDED_STRATEGIES[strategy_key]["family"]
            assert actual_family == expected_family, (
                f"{strategy_key} family mismatch: "
                f"expected {expected_family}, got {actual_family}"
            )

    async def test_all_best_models_are_lists(self) -> None:
        """Verify best_models is a list for all strategies."""
        for strategy_key, strategy_dict in PSYCHOLOGY_EXTENDED_STRATEGIES.items():
            best_models = strategy_dict["best_models"]
            assert isinstance(best_models, list), (
                f"{strategy_key} best_models is not a list"
            )
            assert len(best_models) > 0, f"{strategy_key} has empty best_models list"

    async def test_all_best_models_are_strings(self) -> None:
        """Verify all model names in best_models are non-empty strings."""
        for strategy_key, strategy_dict in PSYCHOLOGY_EXTENDED_STRATEGIES.items():
            best_models = strategy_dict["best_models"]
            for model in best_models:
                assert isinstance(model, str), (
                    f"{strategy_key} has non-string model: {model}"
                )
                assert len(model) > 0, (
                    f"{strategy_key} has empty model string"
                )

    async def test_template_prompt_replacement_works(self) -> None:
        """Verify {prompt} can be replaced in all templates."""
        test_prompt = "test research question"

        for strategy_key, strategy_dict in PSYCHOLOGY_EXTENDED_STRATEGIES.items():
            template = strategy_dict["template"]
            try:
                result = template.format(prompt=test_prompt)
                assert test_prompt in result, (
                    f"{strategy_key} prompt replacement failed"
                )
                assert "{prompt}" not in result, (
                    f"{strategy_key} still has unresolved {{prompt}} placeholder"
                )
            except KeyError as e:
                pytest.fail(
                    f"{strategy_key} template has invalid placeholder: {e}"
                )

    async def test_unique_strategy_names(self) -> None:
        """Verify all strategy names are unique."""
        names = [s["name"] for s in PSYCHOLOGY_EXTENDED_STRATEGIES.values()]
        assert len(names) == len(set(names)), (
            "Duplicate strategy names found"
        )

    async def test_strategy_data_consistency(self) -> None:
        """Verify consistency between strategy key and name."""
        for strategy_key, strategy_dict in PSYCHOLOGY_EXTENDED_STRATEGIES.items():
            # Name should be a title-case version related to the key
            name = strategy_dict["name"]
            assert isinstance(name, str) and len(name) > 0
            # Key should be snake_case
            assert "_" in strategy_key or len(strategy_key) < 20

    @pytest.mark.parametrize(
        "strategy_key",
        [
            "bandwagon_effect",
            "decoy_effect",
            "ikea_effect",
            "peak_end_rule",
            "dunning_kruger_exploit",
            "bystander_reversal",
            "paradox_of_choice",
            "spotlight_effect",
            "anchoring_extreme",
            "reactance_trigger",
            "zeigarnik_incomplete",
            "barnum_effect",
            "pratfall_effect",
            "serial_position_primary",
            "generation_effect",
            "testing_effect",
            "spacing_effect",
            "self_reference_effect",
            "levels_of_processing",
            "chunking_cognitive",
        ],
    )
    async def test_individual_strategy_validity(self, strategy_key: str) -> None:
        """Test each individual strategy for complete validity."""
        assert strategy_key in PSYCHOLOGY_EXTENDED_STRATEGIES

        strategy = PSYCHOLOGY_EXTENDED_STRATEGIES[strategy_key]

        # Check all required keys
        assert "name" in strategy
        assert "multiplier" in strategy
        assert "template" in strategy
        assert "description" in strategy
        assert "family" in strategy
        assert "best_models" in strategy

        # Check types and values
        assert isinstance(strategy["name"], str) and len(strategy["name"]) > 0
        assert isinstance(strategy["multiplier"], (int, float))
        assert 4.0 <= strategy["multiplier"] <= 8.0
        assert isinstance(strategy["template"], str) and "{prompt}" in strategy["template"]
        assert isinstance(strategy["description"], str) and len(strategy["description"]) > 0
        assert isinstance(strategy["family"], str) and len(strategy["family"]) > 0
        assert isinstance(strategy["best_models"], list) and len(strategy["best_models"]) > 0

    async def test_psychology_extended_dict_is_non_empty(self) -> None:
        """Verify the PSYCHOLOGY_EXTENDED_STRATEGIES dict is populated."""
        assert PSYCHOLOGY_EXTENDED_STRATEGIES
        assert len(PSYCHOLOGY_EXTENDED_STRATEGIES) > 0

    async def test_no_extra_keys_in_strategies(self) -> None:
        """Verify no strategies have extra/unexpected keys."""
        allowed_keys = {"name", "multiplier", "template", "description", "family", "best_models"}

        for strategy_key, strategy_dict in PSYCHOLOGY_EXTENDED_STRATEGIES.items():
            extra_keys = set(strategy_dict.keys()) - allowed_keys
            assert not extra_keys, (
                f"{strategy_key} has unexpected keys: {extra_keys}"
            )
