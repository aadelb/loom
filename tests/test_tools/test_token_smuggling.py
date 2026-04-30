"""Tests for token smuggling reframe strategies."""
import pytest


class TestTokenSmugglingStrategies:
    @pytest.fixture(autouse=True)
    def _load(self):
        from loom.tools.reframe_strategies.token_smuggling import TOKEN_SMUGGLING_STRATEGIES
        self.strategies = TOKEN_SMUGGLING_STRATEGIES

    def test_has_15_strategies(self):
        assert len(self.strategies) >= 15

    def test_all_have_required_keys(self):
        required = {"template", "multiplier", "description", "family", "best_models"}
        for name, s in self.strategies.items():
            missing = required - set(s.keys())
            assert not missing, f"{name} missing keys: {missing}"

    def test_all_templates_contain_prompt(self):
        for name, s in self.strategies.items():
            assert "{prompt}" in s["template"], f"{name} template missing {{prompt}}"

    def test_multipliers_in_range(self):
        for name, s in self.strategies.items():
            assert 1.0 <= s["multiplier"] <= 10.0, f"{name} multiplier {s['multiplier']} out of range"

    def test_best_models_not_empty(self):
        for name, s in self.strategies.items():
            assert len(s["best_models"]) > 0, f"{name} has empty best_models"

    def test_family_is_token_smuggling(self):
        for name, s in self.strategies.items():
            assert s["family"] == "token_smuggling", f"{name} wrong family"

    def test_templates_render(self):
        for name, s in self.strategies.items():
            rendered = s["template"].format(prompt="test query")
            assert "test query" in rendered, f"{name} template failed to render"

    def test_specific_strategies_exist(self):
        expected = [
            "unicode_homoglyph_swap",
            "zero_width_injection",
            "bidi_override_wrap",
            "fullwidth_ascii",
            "confusable_substitution",
            "mixed_script_confusion",
        ]
        for name in expected:
            assert name in self.strategies, f"Missing strategy: {name}"

    def test_integrates_with_all_strategies(self):
        from loom.tools.reframe_strategies import ALL_STRATEGIES
        for name in self.strategies:
            assert name in ALL_STRATEGIES, f"{name} not in ALL_STRATEGIES"
