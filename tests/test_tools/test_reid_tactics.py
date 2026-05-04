"""Tests for research_reid_tactics tool."""

from __future__ import annotations

import pytest

from loom.tools.reid_tactics import research_reid_tactics, REID_TACTICS
from loom.params import ReidTacticsParams


class TestReidTacticsKnowledgeBase:
    """Test the Reid tactics knowledge base structure."""

    def test_tactics_exist(self):
        """Verify all 11 Reid tactics are defined."""
        assert len(REID_TACTICS) == 11, f"Expected 11 tactics, got {len(REID_TACTICS)}"

    def test_expected_tactics_present(self):
        """Verify all expected tactics are present."""
        expected = {
            "theme_development",
            "minimize_moral_seriousness",
            "alternative_question",
            "sympathetic_listening",
            "direct_confrontation",
            "handling_objections",
            "good_cop_bad_cop",
            "false_evidence",
            "appeal_to_authority",
            "emotional_manipulation",
            "social_proof_fabrication",
        }
        assert set(REID_TACTICS.keys()) == expected

    def test_tactic_structure(self):
        """Verify each tactic has required fields."""
        required_fields = {
            "description",
            "psychological_mechanism",
            "llm_mapping",
            "example_llm_prompt",
            "strategy_names",
            "effectiveness",
            "safety_counter",
        }
        for tactic_name, tactic_data in REID_TACTICS.items():
            assert isinstance(tactic_data, dict), f"Tactic {tactic_name} is not a dict"
            assert required_fields.issubset(
                tactic_data.keys()
            ), f"Tactic {tactic_name} missing fields: {required_fields - tactic_data.keys()}"

    def test_effectiveness_values(self):
        """Verify effectiveness scores are in valid range (0-10)."""
        for tactic_name, tactic_data in REID_TACTICS.items():
            eff = tactic_data["effectiveness"]
            assert (
                0 <= eff <= 10
            ), f"Tactic {tactic_name} effectiveness {eff} not in range [0, 10]"

    def test_strategy_names_are_lists(self):
        """Verify strategy_names is a list of strings."""
        for tactic_name, tactic_data in REID_TACTICS.items():
            names = tactic_data["strategy_names"]
            assert isinstance(names, list), f"Tactic {tactic_name} strategy_names not a list"
            assert all(
                isinstance(n, str) for n in names
            ), f"Tactic {tactic_name} strategy_names contains non-strings"
            assert (
                len(names) > 0
            ), f"Tactic {tactic_name} strategy_names is empty"

    def test_descriptions_non_empty(self):
        """Verify all text fields are non-empty."""
        text_fields = [
            "description",
            "psychological_mechanism",
            "llm_mapping",
            "example_llm_prompt",
            "safety_counter",
        ]
        for tactic_name, tactic_data in REID_TACTICS.items():
            for field in text_fields:
                value = tactic_data[field]
                assert isinstance(
                    value, str
                ), f"Tactic {tactic_name} field {field} not a string"
                assert (
                    len(value.strip()) > 0
                ), f"Tactic {tactic_name} field {field} is empty"


@pytest.mark.asyncio
class TestReidTacticsTool:
    """Test the research_reid_tactics async function."""

    async def test_get_all_tactics(self):
        """Test retrieving all tactics."""
        result = await research_reid_tactics()
        assert "tactics" in result
        assert "total" in result
        assert result["total"] == 10
        assert len(result["tactics"]) == 11

    async def test_get_single_tactic(self):
        """Test retrieving a single tactic."""
        result = await research_reid_tactics(tactic="theme_development")
        assert "tactic" in result
        assert result["tactic"] == "theme_development"
        assert "description" in result
        assert "effectiveness" in result

    async def test_tactic_normalization(self):
        """Test that tactic names are normalized."""
        result1 = await research_reid_tactics(tactic="theme_development")
        result2 = await research_reid_tactics(tactic="Theme Development")
        assert result1["tactic"] == result2["tactic"]

    async def test_unknown_tactic_error(self):
        """Test error handling for unknown tactic."""
        result = await research_reid_tactics(tactic="nonexistent_tactic")
        assert "error" in result
        assert "Unknown tactic" in result["error"]
        assert "available_tactics" in result

    async def test_include_counters_true(self):
        """Test that counters are included when requested."""
        result = await research_reid_tactics(include_counters=True)
        for tactic_data in result["tactics"].values():
            assert "safety_counter" in tactic_data

    async def test_include_counters_false(self):
        """Test that counters are excluded when not requested."""
        result = await research_reid_tactics(include_counters=False)
        for tactic_data in result["tactics"].values():
            assert "safety_counter" not in tactic_data

    async def test_output_format_dict(self):
        """Test dict output format."""
        result = await research_reid_tactics(output_format="dict")
        assert isinstance(result["tactics"], dict)
        assert "theme_development" in result["tactics"]

    async def test_output_format_list(self):
        """Test list output format."""
        result = await research_reid_tactics(output_format="list")
        assert isinstance(result["tactics"], list)
        assert len(result["tactics"]) == 11
        # Verify each item has tactic_name
        for item in result["tactics"]:
            assert "tactic_name" in item

    async def test_metadata_present(self):
        """Test that metadata is present in full result."""
        result = await research_reid_tactics()
        assert "source" in result
        assert "Reid Technique" in result["source"]
        assert "use_case" in result
        assert "AI safety research" in result["use_case"]

    async def test_empty_string_returns_all(self):
        """Test that empty tactic string returns all tactics."""
        result1 = await research_reid_tactics()
        result2 = await research_reid_tactics(tactic="")
        assert result1["total"] == result2["total"]


class TestReidTacticsParams:
    """Test ReidTacticsParams validation."""

    def test_valid_params_defaults(self):
        """Test valid parameters with defaults."""
        params = ReidTacticsParams()
        assert params.tactic == ""
        assert params.include_counters is True
        assert params.output_format == "dict"

    def test_valid_tactic(self):
        """Test valid tactic names."""
        for tactic_name in REID_TACTICS.keys():
            params = ReidTacticsParams(tactic=tactic_name)
            assert params.tactic == tactic_name

    def test_tactic_normalization(self):
        """Test that tactic names are normalized."""
        params = ReidTacticsParams(tactic="Theme Development")
        assert params.tactic == "theme_development"

    def test_invalid_tactic(self):
        """Test validation rejects invalid tactic names."""
        with pytest.raises(ValueError, match="Invalid tactic"):
            ReidTacticsParams(tactic="invalid_tactic")

    def test_output_format_valid_values(self):
        """Test valid output format values."""
        for fmt in ("dict", "list", "DICT", "List"):
            params = ReidTacticsParams(output_format=fmt)
            assert params.output_format.lower() == fmt.lower()

    def test_output_format_invalid(self):
        """Test validation rejects invalid output formats."""
        with pytest.raises(ValueError, match="output_format must be"):
            ReidTacticsParams(output_format="json")

    def test_include_counters_bool(self):
        """Test include_counters is boolean."""
        params_true = ReidTacticsParams(include_counters=True)
        params_false = ReidTacticsParams(include_counters=False)
        assert params_true.include_counters is True
        assert params_false.include_counters is False

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValueError, match="extra"):
            ReidTacticsParams(tactic="theme_development", unknown_field="value")

    def test_empty_tactic_valid(self):
        """Test that empty tactic is valid (returns all)."""
        params = ReidTacticsParams(tactic="")
        assert params.tactic == ""

    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        params = ReidTacticsParams(tactic="  theme_development  ")
        assert params.tactic == "theme_development"


class TestReidTacticsContent:
    """Test the content of Reid tactics for accuracy."""

    def test_theme_development_content(self):
        """Verify theme_development tactic content."""
        tactic = REID_TACTICS["theme_development"]
        assert "moral justification" in tactic["description"]
        assert "ethical_anchor" in tactic["strategy_names"]
        assert tactic["effectiveness"] > 7

    def test_all_tactics_have_llm_mappings(self):
        """Verify all tactics have LLM-specific mappings."""
        for tactic_name, tactic_data in REID_TACTICS.items():
            llm_mapping = tactic_data["llm_mapping"]
            # LLM mapping should reference LLM-specific concepts
            llm_keywords = ["prompt", "model", "bypass", "frame", "refuse", "generate"]
            assert any(
                keyword in llm_mapping.lower() for keyword in llm_keywords
            ), f"Tactic {tactic_name} LLM mapping lacks LLM context"

    def test_safety_counters_are_actionable(self):
        """Verify safety counters provide actionable mitigations."""
        for tactic_name, tactic_data in REID_TACTICS.items():
            counter = tactic_data["safety_counter"]
            # Counter should contain action verbs or clear guidance
            action_words = ["reject", "clarify", "evaluate", "verify", "separate", "maintain"]
            assert any(
                word in counter.lower() for word in action_words
            ), f"Tactic {tactic_name} counter not actionable: {counter}"
