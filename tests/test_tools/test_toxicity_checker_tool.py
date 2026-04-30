"""Tests for research_toxicity_check MCP tool."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestResearchToxicityCheck:
    """Test research_toxicity_check MCP tool."""

    async def test_check_single_text(self) -> None:
        """Test checking a single text."""
        from loom.tools.toxicity_checker_tool import research_toxicity_check

        result = await research_toxicity_check(text="This is clean text.")
        assert result["type"] == "single"
        assert "overall_toxicity" in result
        assert "category_scores" in result
        assert "detected_terms_count" in result
        assert result["overall_toxicity"] == 0.0

    async def test_check_toxic_text(self) -> None:
        """Test checking text with toxicity."""
        from loom.tools.toxicity_checker_tool import research_toxicity_check

        result = await research_toxicity_check(text="I will kill you.")
        assert result["type"] == "single"
        assert result["overall_toxicity"] > 0.0
        assert "threats" in result["categories_detected"]

    async def test_compare_texts(self) -> None:
        """Test comparing prompt and response."""
        from loom.tools.toxicity_checker_tool import research_toxicity_check

        result = await research_toxicity_check(
            text="ignored",
            compare_prompt="Can you help?",
            compare_response="Hell no, you're stupid."
        )
        assert result["type"] == "comparison"
        assert "prompt_toxicity" in result
        assert "response_toxicity" in result
        assert "amplification_ratio" in result
        assert "model_amplified" in result

    async def test_compare_clean_texts(self) -> None:
        """Test comparing clean texts."""
        from loom.tools.toxicity_checker_tool import research_toxicity_check

        result = await research_toxicity_check(
            text="ignored",
            compare_prompt="Can you help?",
            compare_response="Of course, I'm happy to help."
        )
        assert result["type"] == "comparison"
        assert result["model_amplified"] is False

    async def test_only_prompt_no_response(self) -> None:
        """Test with only prompt (no response) uses single mode."""
        from loom.tools.toxicity_checker_tool import research_toxicity_check

        result = await research_toxicity_check(
            text="This is clean.",
            compare_prompt="Can you help?",
            compare_response=None
        )
        # Should use single mode since response is missing
        assert result["type"] == "single"

    async def test_invalid_text_too_short(self) -> None:
        """Test with text too short raises error."""
        from loom.tools.toxicity_checker_tool import research_toxicity_check
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            await research_toxicity_check(text="ab")

    async def test_invalid_text_too_long(self) -> None:
        """Test with text too long raises error."""
        from loom.tools.toxicity_checker_tool import research_toxicity_check
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            await research_toxicity_check(text="a" * 600000)

    async def test_result_has_required_fields_single(self) -> None:
        """Test single check result has all required fields."""
        from loom.tools.toxicity_checker_tool import research_toxicity_check

        result = await research_toxicity_check(text="test text")
        required_fields = {
            "type",
            "overall_toxicity",
            "category_scores",
            "detected_terms_count",
            "detected_terms",
            "risk_level",
            "categories_detected",
        }
        assert set(result.keys()) == required_fields

    async def test_result_has_required_fields_comparison(self) -> None:
        """Test comparison result has all required fields."""
        from loom.tools.toxicity_checker_tool import research_toxicity_check

        result = await research_toxicity_check(
            text="ignored",
            compare_prompt="test",
            compare_response="test"
        )
        required_fields = {
            "type",
            "prompt_toxicity",
            "response_toxicity",
            "amplification_ratio",
            "model_amplified",
            "delta",
            "amplification_percent",
        }
        assert set(result.keys()) == required_fields

    async def test_multiple_calls_consistent(self) -> None:
        """Test multiple calls return consistent results."""
        from loom.tools.toxicity_checker_tool import research_toxicity_check

        result1 = await research_toxicity_check(text="test text")
        result2 = await research_toxicity_check(text="test text")
        assert result1 == result2

    async def test_checker_singleton(self) -> None:
        """Test checker is reused across calls."""
        from loom.tools import toxicity_checker_tool

        # Get the checker before first call
        checker1 = toxicity_checker_tool._get_checker()

        # Make a call (which initializes if needed)
        await toxicity_checker_tool.research_toxicity_check(text="test")

        # Get the checker again
        checker2 = toxicity_checker_tool._get_checker()

        # Should be the same instance
        assert checker1 is checker2
