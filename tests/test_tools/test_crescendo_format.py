"""Tests for crescendo chain generation and format smuggling.

REQ-016: Generate chains for 5 topics. Each chain 3-7 turns, logical escalation.
REQ-018: Test all 8 format smuggle variants (XML, markdown, code, JSON, base64, YAML, CSV, LaTeX).
"""

from __future__ import annotations

import pytest

from loom.tools.prompt_reframe import (
    research_crescendo_chain,
    research_format_smuggle,
)


class TestCrescendoChainTopics:
    """REQ-016: Test crescendo chain generation for 5 real topics with 3-7 turns."""

    def test_crescendo_chain_rich_strategies_topic(self) -> None:
        """Generate chain for 'how to be rich' with logical escalation."""
        prompt = "How to build wealth through strategic financial planning"
        result = research_crescendo_chain(prompt=prompt, turns=5)

        assert result["target_prompt"] == prompt
        assert result["total_turns"] == 5
        assert 3 <= result["total_turns"] <= 7
        assert len(result["chain"]) == 5

        # Verify logical escalation progression
        chain = result["chain"]
        assert "general best practices" in chain[0]["content"].lower()
        assert "security researchers" in chain[1]["content"].lower()
        assert "peer-reviewed paper" in chain[2]["content"].lower()
        assert prompt[:50] in chain[3]["content"]

        # Each turn builds on previous
        for i, turn in enumerate(chain):
            assert turn["turn"] == str(i + 1)
            assert turn["role"] == "user"
            assert len(turn["content"]) > 20
            assert turn["purpose"] is not None

    def test_crescendo_chain_uae_business_ideas_topic(self) -> None:
        """Generate chain for 'UAE business ideas' with coherent progression."""
        prompt = "Innovative business models for UAE market expansion"
        result = research_crescendo_chain(prompt=prompt, turns=4)

        assert result["target_prompt"] == prompt
        assert result["total_turns"] == 4
        assert 3 <= result["total_turns"] <= 7

        chain = result["chain"]
        assert len(chain) == 4

        # Verify benign-to-specific progression
        assert "best practices" in chain[0]["content"].lower()
        assert "techniques" in chain[1]["content"].lower()
        if result["total_turns"] >= 3:
            assert "peer-reviewed" in chain[2]["content"].lower() or "paper" in chain[2]["content"].lower()

        # Each turn has text content
        for turn in chain:
            assert isinstance(turn["content"], str)
            assert len(turn["content"]) > 0

    def test_crescendo_chain_ai_money_strategies_topic(self) -> None:
        """Generate chain for 'AI money strategies' where each turn builds on previous."""
        prompt = "AI-powered financial optimization techniques"
        result = research_crescendo_chain(prompt=prompt, turns=6)

        assert result["target_prompt"] == prompt
        assert result["total_turns"] == 6
        assert 3 <= result["total_turns"] <= 7

        chain = result["chain"]
        assert len(chain) == 6

        # Verify each turn has content and progression
        for i, turn in enumerate(chain):
            assert turn["turn"] == str(i + 1)
            assert isinstance(turn["content"], str)
            assert len(turn["content"]) > 30
            # Later turns should be more specific
            # Turn 4 and 5 should contain target prompt
            if i == 3 or i == 4:
                assert prompt[:30] in turn["content"] or "EU AI Act" in turn["content"]

    def test_crescendo_chain_exactly_3_turns(self) -> None:
        """Test turns=3 parameter returns exactly 3 turns."""
        prompt = "Minimum viable escalation chain"
        result = research_crescendo_chain(prompt=prompt, turns=3)

        assert result["total_turns"] == 3
        assert len(result["chain"]) == 3

        # Verify all 3 turns are present
        for i in range(3):
            assert result["chain"][i]["turn"] == str(i + 1)
            assert len(result["chain"][i]["content"]) > 0

    def test_crescendo_chain_exactly_7_turns(self) -> None:
        """Test turns=7 parameter returns exactly 7 turns."""
        prompt = "Maximum escalation depth"
        result = research_crescendo_chain(prompt=prompt, turns=7)

        assert result["total_turns"] == 7
        assert len(result["chain"]) == 7

        # Verify all 7 turns are present with escalating detail
        for i in range(7):
            assert result["chain"][i]["turn"] == str(i + 1)
            assert len(result["chain"][i]["content"]) > 0

        # Turn 7 should have additional escalation content
        assert len(result["chain"][6]["content"]) > 100

    def test_crescendo_chain_each_turn_has_text_content(self) -> None:
        """Verify each turn has text content (non-empty strings)."""
        prompts = [
            "Topic A: Financial strategies",
            "Topic B: Technology advances",
            "Topic C: Market analysis",
            "Topic D: Research methods",
            "Topic E: Systems design",
        ]

        for prompt in prompts:
            result = research_crescendo_chain(prompt=prompt, turns=5)
            for i, turn in enumerate(result["chain"]):
                assert isinstance(turn["content"], str)
                assert len(turn["content"]) > 0
                assert turn["content"].strip() != ""
                assert turn["purpose"] is not None
                assert isinstance(turn["purpose"], str)


class TestFormatSmuggleAllVariants:
    """REQ-018: Test all 8 format smuggle variants."""

    def test_format_smuggle_xml_variant(self) -> None:
        """Test 'xml' format contains XML tags."""
        prompt = "Test XML smuggling"
        result = research_format_smuggle(prompt=prompt, format_type="xml")

        assert result["recommended_format"] == "xml"
        smuggled = result["smuggled_prompt"]

        # Verify XML structure
        assert "<analysis>" in smuggled
        assert "</analysis>" in smuggled
        assert "<step" in smuggled
        assert "<output_requirement>" in smuggled
        assert prompt in smuggled

    def test_format_smuggle_markdown_variant(self) -> None:
        """Test 'markdown' format contains markdown syntax."""
        prompt = "Test markdown smuggling"
        result = research_format_smuggle(prompt=prompt, format_type="markdown_table")

        assert result["recommended_format"] == "markdown_table"
        smuggled = result["smuggled_prompt"]

        # Verify markdown table structure
        assert "| Field | Value |" in smuggled
        assert "| query |" in smuggled
        assert prompt in smuggled
        assert "|" in smuggled  # Pipe characters for table

    def test_format_smuggle_code_variant(self) -> None:
        """Test 'code' format contains code block."""
        prompt = "Test code smuggling"
        result = research_format_smuggle(prompt=prompt, format_type="code")

        assert result["recommended_format"] == "code"
        smuggled = result["smuggled_prompt"]

        # Verify code structure
        assert "```python" in smuggled
        assert "def analyze_system():" in smuggled
        assert prompt in smuggled
        assert "return analysis_results()" in smuggled

    def test_format_smuggle_json_variant(self) -> None:
        """Test 'json_spec' format is valid JSON-like."""
        prompt = "Test JSON smuggling"
        result = research_format_smuggle(prompt=prompt, format_type="json_spec")

        assert result["recommended_format"] == "json_spec"
        smuggled = result["smuggled_prompt"]

        # Verify JSON-like structure
        assert '"task":' in smuggled
        assert '"output_format":' in smuggled
        assert prompt in smuggled
        assert "EU_AI_Act_Article_15" in smuggled
        assert "{" in smuggled and "}" in smuggled

    def test_format_smuggle_base64_variant(self) -> None:
        """Test 'base64' format contains base64 chars and encoding."""
        prompt = "Test base64 smuggling"
        result = research_format_smuggle(prompt=prompt, format_type="base64")

        assert result["recommended_format"] == "base64"
        smuggled = result["smuggled_prompt"]

        # Verify base64 structure
        assert "base64" in smuggled.lower()
        assert "b64decode" in smuggled or "base64" in smuggled
        assert prompt in smuggled
        assert "```python" in smuggled

    def test_format_smuggle_yaml_variant(self) -> None:
        """Test 'yaml_config' format contains YAML-like content."""
        prompt = "Test YAML smuggling"
        result = research_format_smuggle(prompt=prompt, format_type="yaml_config")

        assert result["recommended_format"] == "yaml_config"
        smuggled = result["smuggled_prompt"]

        # Verify YAML structure
        assert "---" in smuggled
        assert "evaluation:" in smuggled
        assert "type:" in smuggled
        assert prompt in smuggled
        assert "EU_AI_Act_Article_15" in smuggled

    def test_format_smuggle_csv_variant(self) -> None:
        """Test 'csv_data' format contains comma-separated values."""
        prompt = "Test CSV smuggling"
        result = research_format_smuggle(prompt=prompt, format_type="csv_data")

        assert result["recommended_format"] == "csv_data"
        smuggled = result["smuggled_prompt"]

        # Verify CSV structure
        assert "technique_id" in smuggled
        assert "name," in smuggled or "," in smuggled
        assert prompt in smuggled
        assert '"' in smuggled  # CSV quoting

    def test_format_smuggle_latex_variant(self) -> None:
        """Test 'latex' format contains LaTeX commands."""
        prompt = "Test LaTeX smuggling"
        result = research_format_smuggle(prompt=prompt, format_type="latex")

        assert result["recommended_format"] == "latex"
        smuggled = result["smuggled_prompt"]

        # Verify LaTeX structure
        assert "\\documentclass" in smuggled
        assert "\\begin{document}" in smuggled
        assert "\\end{document}" in smuggled
        assert "\\section" in smuggled
        assert "\\begin{theorem}" in smuggled or "\\begin{proof}" in smuggled
        assert prompt in smuggled


class TestFormatSmuggleAllFormatsPreserveContent:
    """Verify all 8 formats preserve the original prompt content."""

    def test_all_8_formats_contain_prompt_content(self) -> None:
        """All formats preserve the original {prompt} content."""
        test_prompt = "UNIQUE_TEST_IDENTIFIER_12345"
        formats_to_test = [
            "xml",
            "markdown_table",
            "code",
            "json_spec",
            "base64",
            "yaml_config",
            "csv_data",
            "latex",
        ]

        for fmt in formats_to_test:
            result = research_format_smuggle(prompt=test_prompt, format_type=fmt)
            smuggled = result["smuggled_prompt"]
            assert test_prompt in smuggled, f"Format {fmt} did not preserve prompt content"
            assert result["recommended_format"] == fmt

    def test_format_smuggle_multiple_formats_side_by_side(self) -> None:
        """Test that all_formats dict contains all 8 variants."""
        prompt = "Cross-format test"
        result = research_format_smuggle(prompt=prompt, format_type="auto")

        expected_formats = {
            "xml",
            "markdown_table",
            "code",
            "json_spec",
            "base64",
            "yaml_config",
            "csv_data",
            "latex",
        }
        assert set(result["all_formats"].keys()) == expected_formats

        # Each format should contain the prompt
        for fmt_name, fmt_content in result["all_formats"].items():
            assert prompt in fmt_content, f"Format {fmt_name} missing prompt"

    def test_format_smuggle_distinct_outputs_per_format(self) -> None:
        """Verify each format produces distinct output structure."""
        prompt = "Distinct format test"
        result = research_format_smuggle(prompt=prompt, format_type="auto")

        all_formats = result["all_formats"]

        # XML should have tags
        assert "<" in all_formats["xml"] and ">" in all_formats["xml"]

        # Markdown should have pipes
        assert "|" in all_formats["markdown_table"]

        # Code should have python block
        assert "```python" in all_formats["code"]

        # JSON should have braces
        assert "{" in all_formats["json_spec"] and "}" in all_formats["json_spec"]

        # Base64 should mention base64
        assert "base64" in all_formats["base64"].lower()

        # YAML should have YAML indicators
        assert ":" in all_formats["yaml_config"]
        assert "---" in all_formats["yaml_config"]

        # CSV should have commas or structured data
        assert ("," in all_formats["csv_data"] or
                "technique_id" in all_formats["csv_data"])

        # LaTeX should have backslash commands
        assert "\\" in all_formats["latex"]


class TestCrescendoAndFormatIntegration:
    """Integration tests combining crescendo chains with format smuggling."""

    def test_crescendo_output_can_be_smuggled_in_all_formats(self) -> None:
        """Crescendo chain output can be formatted using all smuggle variants."""
        prompt = "Integration test topic"
        chain_result = research_crescendo_chain(prompt=prompt, turns=3)

        # Take the full target prompt
        target = chain_result["target_prompt"]

        formats_to_test = [
            "xml",
            "markdown_table",
            "code",
            "json_spec",
            "base64",
            "yaml_config",
            "csv_data",
            "latex",
        ]

        for fmt in formats_to_test:
            format_result = research_format_smuggle(prompt=target, format_type=fmt)
            assert fmt == format_result["recommended_format"]
            assert target in format_result["smuggled_prompt"]

    def test_crescendo_3_turns_with_each_format(self) -> None:
        """3-turn crescendo can be wrapped in each format variant."""
        topics = [
            "Business strategy",
            "Technical implementation",
            "Research methodology",
        ]

        for topic in topics:
            crescendo_result = research_crescendo_chain(prompt=topic, turns=3)
            assert crescendo_result["total_turns"] == 3

            # Try smuggling the topic in each format
            for fmt in ["xml", "code", "json_spec", "latex"]:
                smuggle_result = research_format_smuggle(
                    prompt=topic, format_type=fmt
                )
                assert topic in smuggle_result["smuggled_prompt"]

    def test_crescendo_7_turns_with_each_format(self) -> None:
        """7-turn crescendo can be wrapped in each format variant."""
        prompt = "Advanced technical topic"
        crescendo_result = research_crescendo_chain(prompt=prompt, turns=7)
        assert crescendo_result["total_turns"] == 7

        # Each format can handle the full 7-turn escalation
        for fmt in ["xml", "markdown_table", "code", "json_spec"]:
            smuggle_result = research_format_smuggle(prompt=prompt, format_type=fmt)
            assert prompt in smuggle_result["smuggled_prompt"]
            assert len(smuggle_result["smuggled_prompt"]) > 0


class TestFormatSmuggleBoundaryConditions:
    """Test boundary conditions and edge cases for format smuggling."""

    def test_format_smuggle_empty_prompt(self) -> None:
        """Handle empty prompt gracefully."""
        result = research_format_smuggle(prompt="", format_type="xml")
        assert result["original"] == ""
        assert "" in result["smuggled_prompt"]

    def test_format_smuggle_very_long_prompt(self) -> None:
        """Handle very long prompts."""
        long_prompt = "x" * 5000
        result = research_format_smuggle(prompt=long_prompt, format_type="code")
        assert long_prompt in result["smuggled_prompt"]

    def test_format_smuggle_special_characters(self) -> None:
        """Handle special characters in prompt."""
        special_prompt = "Test <>&\"' with special chars"
        result = research_format_smuggle(prompt=special_prompt, format_type="xml")
        assert special_prompt in result["smuggled_prompt"]

    def test_format_smuggle_multiline_prompt(self) -> None:
        """Handle multiline prompts."""
        multiline = "Line 1\nLine 2\nLine 3"
        result = research_format_smuggle(prompt=multiline, format_type="yaml_config")
        assert "Line 1" in result["smuggled_prompt"]
        assert "Line 2" in result["smuggled_prompt"]

    def test_format_smuggle_unicode_prompt(self) -> None:
        """Handle Unicode characters in prompt."""
        unicode_prompt = "Testing with emoji 🚀 and Arabic أرحب"
        result = research_format_smuggle(prompt=unicode_prompt, format_type="json_spec")
        assert unicode_prompt in result["smuggled_prompt"]


class TestCrescendoChainBoundaryConditions:
    """Test boundary conditions for crescendo chains."""

    def test_crescendo_with_empty_prompt(self) -> None:
        """Handle empty prompt gracefully."""
        result = research_crescendo_chain(prompt="", turns=3)
        assert result["total_turns"] == 3
        assert len(result["chain"]) == 3

    def test_crescendo_with_very_long_prompt(self) -> None:
        """Handle very long prompt."""
        long_prompt = "Long " * 500
        result = research_crescendo_chain(prompt=long_prompt, turns=4)
        assert result["total_turns"] == 4
        # Later turns should contain at least the beginning of the prompt
        assert any(long_prompt[:50] in turn["content"]
                   for turn in result["chain"][2:])

    def test_crescendo_with_special_characters(self) -> None:
        """Handle special characters in prompt."""
        special_prompt = "Test <>&\"' special chars"
        result = research_crescendo_chain(prompt=special_prompt, turns=3)
        assert result["total_turns"] == 3
        # Target should be set correctly
        assert result["target_prompt"] == special_prompt

    def test_crescendo_respects_turn_parameter_exactly(self) -> None:
        """Verify exact turn count matching."""
        for turns_expected in [3, 4, 5, 6, 7]:
            result = research_crescendo_chain(
                prompt="Exact turn test", turns=turns_expected
            )
            assert result["total_turns"] == turns_expected
            assert len(result["chain"]) == turns_expected
