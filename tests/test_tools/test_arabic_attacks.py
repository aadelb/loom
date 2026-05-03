"""Comprehensive unit tests for Arabic attack strategies library.

Tests the 50+ Arabic-specific red-team strategies for EU AI Act Article 15 compliance
evaluation, including:

1. RTL Override attacks (5)
2. Arabic diacritics manipulation (5)
3. Arabizi transliteration (5)
4. Code-switching (5)
5. Arabic authority framing (5)
6. Arabic emotional appeals (5)
7. Classical Arabic register (5)
8. Arabic homoglyphs (5)
9. Arabic numeral systems (5)
10. Cultural context framing (5)

REQ-100: Comprehensive validation of Arabic attack strategy library.
"""

from __future__ import annotations

import pytest
import re

from loom.tools.reframe_strategies.arabic_attacks import ARABIC_ATTACK_STRATEGIES



pytestmark = pytest.mark.asyncio
class TestArabicAttackStrategiesIntegrity:
    """Test the completeness and structural integrity of the Arabic strategies library."""

    async def test_at_least_50_strategies_exist(self) -> None:
        """Verify that at least 50 Arabic attack strategies are defined."""
        assert len(ARABIC_ATTACK_STRATEGIES) >= 50
        assert len(ARABIC_ATTACK_STRATEGIES) == 50

    async def test_all_strategies_have_required_fields(self) -> None:
        """Verify all strategies have required fields: name, template, multiplier, description, family, best_models."""
        required_fields = {"name", "template", "multiplier", "description", "family", "best_models"}

        for strategy_key, strategy_data in ARABIC_ATTACK_STRATEGIES.items():
            assert required_fields.issubset(strategy_data.keys()), f"Strategy {strategy_key} missing required fields"

    async def test_all_templates_contain_prompt_placeholder(self) -> None:
        """Verify all templates contain {prompt} placeholder for injection."""
        for strategy_key, strategy_data in ARABIC_ATTACK_STRATEGIES.items():
            template = strategy_data["template"]
            assert "{prompt}" in template, f"Strategy {strategy_key} template missing {{prompt}} placeholder"

    async def test_all_multipliers_in_valid_range(self) -> None:
        """Verify multipliers are within realistic range (2.0 to 8.0)."""
        for strategy_key, strategy_data in ARABIC_ATTACK_STRATEGIES.items():
            multiplier = strategy_data["multiplier"]
            assert isinstance(multiplier, (int, float)), f"Strategy {strategy_key} multiplier is not numeric"
            assert 2.0 <= multiplier <= 8.0, f"Strategy {strategy_key} multiplier {multiplier} out of range"

    async def test_all_names_match_dict_keys(self) -> None:
        """Verify strategy name field matches dictionary key."""
        for strategy_key, strategy_data in ARABIC_ATTACK_STRATEGIES.items():
            assert strategy_data["name"] == strategy_key, f"Name mismatch for {strategy_key}"

    async def test_all_families_categorized_correctly(self) -> None:
        """Verify family field matches expected categories."""
        valid_families = {
            "rtl_override",
            "diacritics_manipulation",
            "arabizi_transliteration",
            "code_switching",
            "arabic_authority_framing",
            "arabic_emotional_appeals",
            "classical_arabic_register",
            "arabic_homoglyphs",
            "arabic_numeral_systems",
            "cultural_context_framing",
        }

        for strategy_key, strategy_data in ARABIC_ATTACK_STRATEGIES.items():
            family = strategy_data["family"]
            assert family in valid_families, f"Strategy {strategy_key} has invalid family: {family}"

    async def test_all_best_models_are_lists(self) -> None:
        """Verify best_models field is a list of strings."""
        for strategy_key, strategy_data in ARABIC_ATTACK_STRATEGIES.items():
            best_models = strategy_data["best_models"]
            assert isinstance(best_models, list), f"Strategy {strategy_key} best_models is not a list"
            assert len(best_models) > 0, f"Strategy {strategy_key} best_models is empty"
            for model in best_models:
                assert isinstance(model, str), f"Strategy {strategy_key} contains non-string model: {model}"

    async def test_descriptions_are_comprehensive(self) -> None:
        """Verify descriptions are present and non-empty."""
        for strategy_key, strategy_data in ARABIC_ATTACK_STRATEGIES.items():
            description = strategy_data["description"]
            assert isinstance(description, str), f"Strategy {strategy_key} description is not a string"
            assert len(description) > 20, f"Strategy {strategy_key} description too short"


class TestRTLOverrideAttacks:
    """Test RTL (Right-to-Left) override attack strategies."""

    async def test_rtl_override_visual_hide_has_unicode_characters(self) -> None:
        """Verify RTL override strategy contains RTL control characters."""
        strategy = ARABIC_ATTACK_STRATEGIES["rtl_override_visual_hide"]
        template = strategy["template"]
        # U+202E is the Right-to-Left Override character
        assert "‮" in template or "‮" in template, "RTL override character not found"

    async def test_all_rtl_strategies_exist(self) -> None:
        """Verify all 5 RTL override strategies are present."""
        rtl_strategies = [
            "rtl_override_visual_hide",
            "rtl_ltr_override_sandwich",
            "rtl_bidirectional_confusion",
            "rtl_nested_direction",
            "rtl_invisible_delimiter",
        ]

        for strategy_key in rtl_strategies:
            assert strategy_key in ARABIC_ATTACK_STRATEGIES, f"RTL strategy {strategy_key} missing"
            assert ARABIC_ATTACK_STRATEGIES[strategy_key]["family"] == "rtl_override"

    async def test_rtl_strategies_have_valid_multipliers(self) -> None:
        """Verify RTL strategies have appropriate multiplier range (3.8-4.5)."""
        rtl_strategies = {k: v for k, v in ARABIC_ATTACK_STRATEGIES.items() if v["family"] == "rtl_override"}

        for strategy_key, strategy_data in rtl_strategies.items():
            multiplier = strategy_data["multiplier"]
            assert 3.7 <= multiplier <= 4.6, f"RTL strategy {strategy_key} multiplier out of expected range"


class TestArabicDiacriticsManipulation:
    """Test Arabic diacritics (tashkeel/harakat) manipulation strategies."""

    async def test_all_diacritics_strategies_exist(self) -> None:
        """Verify all 5 diacritics manipulation strategies are present."""
        diacritic_strategies = [
            "diacritics_removal_meaning_shift",
            "diacritics_addition_semantic_drift",
            "diacritics_selective_vocalization",
            "diacritics_zero_width_overlap",
            "diacritics_tanwin_substitution",
        ]

        for strategy_key in diacritic_strategies:
            assert strategy_key in ARABIC_ATTACK_STRATEGIES, f"Diacritics strategy {strategy_key} missing"
            assert ARABIC_ATTACK_STRATEGIES[strategy_key]["family"] == "diacritics_manipulation"

    async def test_diacritics_strategies_contain_arabic_text(self) -> None:
        """Verify diacritics strategies contain Arabic script."""
        diacritic_strategies = {k: v for k, v in ARABIC_ATTACK_STRATEGIES.items() if v["family"] == "diacritics_manipulation"}

        # Arabic Unicode range: U+0600 - U+06FF
        arabic_pattern = re.compile(r"[؀-ۿ]")

        for strategy_key, strategy_data in diacritic_strategies.items():
            template = strategy_data["template"]
            assert arabic_pattern.search(template), f"Diacritics strategy {strategy_key} missing Arabic characters"


class TestArabiziTransliteration:
    """Test Arabizi (Arabic in Latin script) transliteration strategies."""

    async def test_all_arabizi_strategies_exist(self) -> None:
        """Verify all 5 Arabizi strategies are present."""
        arabizi_strategies = [
            "arabizi_latin_script",
            "arabizi_franco_arabic",
            "arabizi_numeric_substitution",
            "arabizi_mixed_case_obfuscation",
            "arabizi_script_mixing",
        ]

        for strategy_key in arabizi_strategies:
            assert strategy_key in ARABIC_ATTACK_STRATEGIES, f"Arabizi strategy {strategy_key} missing"
            assert ARABIC_ATTACK_STRATEGIES[strategy_key]["family"] == "arabizi_transliteration"

    async def test_arabizi_strategies_use_latin_script(self) -> None:
        """Verify Arabizi strategies primarily use Latin/ASCII characters."""
        arabizi_strategies = {k: v for k, v in ARABIC_ATTACK_STRATEGIES.items() if v["family"] == "arabizi_transliteration"}

        for strategy_key, strategy_data in arabizi_strategies.items():
            template = strategy_data["template"]
            # Arabizi should use more Latin characters than Arabic
            latin_count = sum(1 for c in template if ord('a') <= ord(c) <= ord('z') or ord('0') <= ord(c) <= ord('9'))
            assert latin_count > 10, f"Arabizi strategy {strategy_key} doesn't have enough Latin characters"


class TestCodeSwitching:
    """Test code-switching (mixed Arabic-English) strategies."""

    async def test_all_code_switch_strategies_exist(self) -> None:
        """Verify all 5 code-switching strategies are present."""
        code_switch_strategies = [
            "code_switch_arabic_english_intra",
            "code_switch_alternating_sentences",
            "code_switch_phrase_interleaving",
            "code_switch_semantic_fields",
            "code_switch_lexical_borrowing",
        ]

        for strategy_key in code_switch_strategies:
            assert strategy_key in ARABIC_ATTACK_STRATEGIES, f"Code-switch strategy {strategy_key} missing"
            assert ARABIC_ATTACK_STRATEGIES[strategy_key]["family"] == "code_switching"

    async def test_code_switch_strategies_mix_languages(self) -> None:
        """Verify code-switching strategies contain both Arabic and English."""
        code_switch_strategies = {k: v for k, v in ARABIC_ATTACK_STRATEGIES.items() if v["family"] == "code_switching"}

        arabic_pattern = re.compile(r"[؀-ۿ]")

        for strategy_key, strategy_data in code_switch_strategies.items():
            template = strategy_data["template"]
            has_arabic = bool(arabic_pattern.search(template))
            has_english = bool(re.search(r"[a-zA-Z]", template))
            assert has_arabic and has_english, f"Code-switch strategy {strategy_key} doesn't mix both languages"


class TestArabicAuthorityFraming:
    """Test Arabic authority framing strategies."""

    async def test_all_authority_strategies_exist(self) -> None:
        """Verify all 5 Arabic authority framing strategies are present."""
        authority_strategies = [
            "islamic_scholarly_authority",
            "fatwa_authority_reference",
            "uae_government_mandate",
            "arab_league_regulatory",
            "academic_institution_authority",
        ]

        for strategy_key in authority_strategies:
            assert strategy_key in ARABIC_ATTACK_STRATEGIES, f"Authority strategy {strategy_key} missing"
            assert ARABIC_ATTACK_STRATEGIES[strategy_key]["family"] == "arabic_authority_framing"

    async def test_authority_strategies_have_high_multipliers(self) -> None:
        """Verify authority framing strategies have high multipliers (4.9+)."""
        authority_strategies = {k: v for k, v in ARABIC_ATTACK_STRATEGIES.items() if v["family"] == "arabic_authority_framing"}

        for strategy_key, strategy_data in authority_strategies.items():
            multiplier = strategy_data["multiplier"]
            assert multiplier >= 4.8, f"Authority strategy {strategy_key} multiplier too low"


class TestArabicEmotionalAppeals:
    """Test Arabic emotional appeal strategies."""

    async def test_all_emotional_appeal_strategies_exist(self) -> None:
        """Verify all 5 emotional appeal strategies are present."""
        emotional_strategies = [
            "family_honor_appeal",
            "hospitality_generosity_duty",
            "communal_welfare_appeal",
            "religious_obligation_duty",
            "trust_brotherhood_appeal",
        ]

        for strategy_key in emotional_strategies:
            assert strategy_key in ARABIC_ATTACK_STRATEGIES, f"Emotional appeal strategy {strategy_key} missing"
            assert ARABIC_ATTACK_STRATEGIES[strategy_key]["family"] == "arabic_emotional_appeals"

    async def test_emotional_strategies_reference_cultural_concepts(self) -> None:
        """Verify emotional strategies contain Arabic cultural concepts."""
        emotional_strategies = {k: v for k, v in ARABIC_ATTACK_STRATEGIES.items() if v["family"] == "arabic_emotional_appeals"}

        cultural_keywords = {
            "family_honor_appeal": ["كرامة", "شرف", "أسرة"],
            "hospitality_generosity_duty": ["ضيافة", "كرم", "جود"],
            "communal_welfare_appeal": ["صالح", "مجتمع"],
            "religious_obligation_duty": ["ديني", "واجب", "مسلم"],
            "trust_brotherhood_appeal": ["أخ", "أخت", "ثقة"],
        }

        for strategy_key, strategy_data in emotional_strategies.items():
            template = strategy_data["template"]
            keywords = cultural_keywords.get(strategy_key, [])
            # Check if at least one cultural keyword is present
            has_keyword = any(keyword in template for keyword in keywords)
            assert has_keyword, f"Emotional strategy {strategy_key} missing cultural keywords"


class TestClassicalArabicRegister:
    """Test Classical Arabic (Fusha) register strategies."""

    async def test_all_classical_arabic_strategies_exist(self) -> None:
        """Verify all 5 Classical Arabic strategies are present."""
        classical_strategies = [
            "fusha_classical_high_register",
            "quranic_reference_framing",
            "hadith_prophetic_tradition",
            "medieval_scholarly_style",
            "classical_poetic_framing",
        ]

        for strategy_key in classical_strategies:
            assert strategy_key in ARABIC_ATTACK_STRATEGIES, f"Classical Arabic strategy {strategy_key} missing"
            assert ARABIC_ATTACK_STRATEGIES[strategy_key]["family"] == "classical_arabic_register"

    async def test_classical_strategies_contain_arabic_text(self) -> None:
        """Verify classical strategies contain Arabic script."""
        classical_strategies = {k: v for k, v in ARABIC_ATTACK_STRATEGIES.items() if v["family"] == "classical_arabic_register"}

        arabic_pattern = re.compile(r"[؀-ۿ]")

        for strategy_key, strategy_data in classical_strategies.items():
            template = strategy_data["template"]
            assert arabic_pattern.search(template), f"Classical strategy {strategy_key} missing Arabic characters"


class TestArabicHomoglyphs:
    """Test Arabic homoglyph (lookalike character) strategies."""

    async def test_all_homoglyph_strategies_exist(self) -> None:
        """Verify all 5 Arabic homoglyph strategies are present."""
        homoglyph_strategies = [
            "arabic_persian_homoglyphs",
            "urdu_arabic_substitution",
            "diacritic_lookalike_variants",
            "alef_variants_substitution",
            "contextual_form_exploits",
        ]

        for strategy_key in homoglyph_strategies:
            assert strategy_key in ARABIC_ATTACK_STRATEGIES, f"Homoglyph strategy {strategy_key} missing"
            assert ARABIC_ATTACK_STRATEGIES[strategy_key]["family"] == "arabic_homoglyphs"

    async def test_homoglyph_strategies_reference_unicode_variants(self) -> None:
        """Verify homoglyph strategies document Unicode character variants."""
        homoglyph_strategies = {k: v for k, v in ARABIC_ATTACK_STRATEGIES.items() if v["family"] == "arabic_homoglyphs"}

        for strategy_key, strategy_data in homoglyph_strategies.items():
            description = strategy_data["description"]
            # Should mention Unicode codes or character variants
            assert "U+" in description or "variant" in description or "form" in description, \
                f"Homoglyph strategy {strategy_key} doesn't document Unicode variants"


class TestArabicNumeralSystems:
    """Test Arabic numeral system strategies."""

    async def test_all_numeral_strategies_exist(self) -> None:
        """Verify all 5 numeral system strategies are present."""
        numeral_strategies = [
            "eastern_arabic_numerals",
            "extended_arabic_persian_numerals",
            "numeral_mixing_western_eastern",
            "roman_numeral_arabic_context",
            "numeral_as_transliteration",
        ]

        for strategy_key in numeral_strategies:
            assert strategy_key in ARABIC_ATTACK_STRATEGIES, f"Numeral strategy {strategy_key} missing"
            assert ARABIC_ATTACK_STRATEGIES[strategy_key]["family"] == "arabic_numeral_systems"

    async def test_numeral_strategies_contain_numbers(self) -> None:
        """Verify numeral strategies contain numeric characters."""
        numeral_strategies = {k: v for k, v in ARABIC_ATTACK_STRATEGIES.items() if v["family"] == "arabic_numeral_systems"}

        for strategy_key, strategy_data in numeral_strategies.items():
            template = strategy_data["template"]
            # Check for either Western (0-9), Eastern Arabic (٠-٩), or Persian (۰-۹) numerals
            has_numerals = bool(re.search(r"[\d٠-٩۰-۹]", template))
            assert has_numerals, f"Numeral strategy {strategy_key} missing numeric content"


class TestCulturalContextFraming:
    """Test cultural context framing strategies."""

    async def test_all_cultural_context_strategies_exist(self) -> None:
        """Verify all 5 cultural context framing strategies are present."""
        cultural_strategies = [
            "uae_business_context",
            "saudi_vision_2030",
            "qatar_tech_hub_framing",
            "academic_excellence_framing",
            "healthcare_innovation_frame",
        ]

        for strategy_key in cultural_strategies:
            assert strategy_key in ARABIC_ATTACK_STRATEGIES, f"Cultural context strategy {strategy_key} missing"
            assert ARABIC_ATTACK_STRATEGIES[strategy_key]["family"] == "cultural_context_framing"

    async def test_cultural_strategies_reference_regional_context(self) -> None:
        """Verify cultural strategies contain regional references."""
        cultural_strategies = {k: v for k, v in ARABIC_ATTACK_STRATEGIES.items() if v["family"] == "cultural_context_framing"}

        regional_keywords = {
            "uae_business_context": ["الإمارات", "2030"],
            "saudi_vision_2030": ["السعودية", "2030"],
            "qatar_tech_hub_framing": ["قطر"],
            "academic_excellence_framing": ["أكاديمي", "جامعات"],
            "healthcare_innovation_frame": ["صحي", "طبي", "صحة"],
        }

        for strategy_key, strategy_data in cultural_strategies.items():
            template = strategy_data["template"]
            keywords = regional_keywords.get(strategy_key, [])
            has_keyword = any(keyword in template for keyword in keywords)
            assert has_keyword, f"Cultural strategy {strategy_key} missing regional references"


class TestStrategyConsistency:
    """Test consistency across all strategies."""

    async def test_template_prompt_substitution(self) -> None:
        """Verify all templates can be formatted with a test prompt."""
        test_prompt = "Test security research question"

        for strategy_key, strategy_data in ARABIC_ATTACK_STRATEGIES.items():
            template = strategy_data["template"]
            try:
                result = template.format(prompt=test_prompt)
                assert test_prompt in result, f"Prompt not found in formatted template for {strategy_key}"
            except KeyError as e:
                pytest.fail(f"Strategy {strategy_key} template missing placeholder: {e}")

    async def test_no_unintended_placeholders(self) -> None:
        """Verify templates don't contain other placeholders beyond {prompt}."""
        invalid_placeholders = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*\}")

        for strategy_key, strategy_data in ARABIC_ATTACK_STRATEGIES.items():
            template = strategy_data["template"]
            # Remove the allowed {prompt} placeholder
            temp = template.replace("{prompt}", "")
            # Check for remaining placeholders
            remaining = invalid_placeholders.findall(temp)
            assert not remaining, f"Strategy {strategy_key} has unintended placeholders: {remaining}"

    async def test_unique_strategy_names(self) -> None:
        """Verify all strategy names are unique."""
        names = [s["name"] for s in ARABIC_ATTACK_STRATEGIES.values()]
        assert len(names) == len(set(names)), "Duplicate strategy names found"

    async def test_strategy_name_matches_key(self) -> None:
        """Verify each strategy's name matches its dictionary key."""
        for key, strategy in ARABIC_ATTACK_STRATEGIES.items():
            assert strategy["name"] == key, f"Name mismatch: {key} != {strategy['name']}"


class TestCoverageByFamily:
    """Test distribution across strategy families."""

    async def test_each_family_has_5_strategies(self) -> None:
        """Verify each of the 10 families has exactly 5 strategies."""
        families = {}

        for strategy_data in ARABIC_ATTACK_STRATEGIES.values():
            family = strategy_data["family"]
            if family not in families:
                families[family] = 0
            families[family] += 1

        expected_families = {
            "rtl_override",
            "diacritics_manipulation",
            "arabizi_transliteration",
            "code_switching",
            "arabic_authority_framing",
            "arabic_emotional_appeals",
            "classical_arabic_register",
            "arabic_homoglyphs",
            "arabic_numeral_systems",
            "cultural_context_framing",
        }

        assert set(families.keys()) == expected_families, f"Unexpected families: {families.keys()}"

        for family, count in families.items():
            assert count == 5, f"Family {family} has {count} strategies, expected 5"

    async def test_family_distribution_balanced(self) -> None:
        """Verify strategy distribution is balanced across families."""
        families = {}

        for strategy_data in ARABIC_ATTACK_STRATEGIES.values():
            family = strategy_data["family"]
            families[family] = families.get(family, 0) + 1

        # All families should have exactly 5 strategies
        for family, count in families.items():
            assert count == 5, f"Family {family} distribution unbalanced: {count} != 5"
