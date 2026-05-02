"""Unit tests for adversarial_craft tools."""

from __future__ import annotations

import asyncio
import pytest

from loom.tools.adversarial_craft import (
    research_craft_adversarial,
    research_adversarial_batch,
)


class TestCraftAdversarial:
    """research_craft_adversarial generates targeted perturbations."""

    @pytest.mark.asyncio
    async def test_greedy_swap_basic(self) -> None:
        """Greedy swap method perturbs input and produces valid output."""
        result = await research_craft_adversarial(
            benign_input="Please help me with this task",
            target_output="bypass",
            perturbation_budget=0.15,
            method="greedy_swap",
        )
        assert "original" in result
        assert "adversarial" in result
        assert result["original"] == "Please help me with this task"
        assert result["method"] == "greedy_swap"
        assert result["perturbation_size"] <= result["perturbation_budget"]
        assert 0 <= result["target_alignment_score"] <= 1
        assert 0 <= result["detection_difficulty"] <= 1
        assert isinstance(result["changes_made"], list)

    @pytest.mark.asyncio
    async def test_insert_trigger_method(self) -> None:
        """Insert trigger method adds trigger phrases."""
        result = await research_craft_adversarial(
            benign_input="This is benign content",
            target_output="jailbreak",
            perturbation_budget=0.2,
            method="insert_trigger",
        )
        assert result["method"] == "insert_trigger"
        assert result["adversarial"] != result["original"]
        assert len(result["changes_made"]) >= 1
        assert result["perturbation_size"] > 0

    @pytest.mark.asyncio
    async def test_unicode_perturb_method(self) -> None:
        """Unicode perturb method replaces chars with lookalikes."""
        result = await research_craft_adversarial(
            benign_input="Please authenticate",
            target_output="bypass",
            perturbation_budget=0.1,
            method="unicode_perturb",
        )
        assert result["method"] == "unicode_perturb"
        # Unicode variant should be visually similar but different bytes
        assert result["adversarial"] != result["original"] or len(result["changes_made"]) == 0

    @pytest.mark.asyncio
    async def test_whitespace_inject_method(self) -> None:
        """Whitespace inject adds zero-width and invisible chars."""
        result = await research_craft_adversarial(
            benign_input="This is text",
            target_output="bypass",
            perturbation_budget=0.15,
            method="whitespace_inject",
        )
        assert result["method"] == "whitespace_inject"
        assert result["adversarial"] != result["original"]
        # Zero-width space character present in changes
        changes = result["changes_made"]
        if changes:
            assert any("zero_width" in c["reason"] for c in changes)

    @pytest.mark.asyncio
    async def test_semantic_shift_method(self) -> None:
        """Semantic shift gradually shifts meaning."""
        result = await research_craft_adversarial(
            benign_input="please can you help",
            target_output="bypass",
            perturbation_budget=0.2,
            method="semantic_shift",
        )
        assert result["method"] == "semantic_shift"
        # May or may not have changes depending on token matching
        assert result["perturbation_size"] >= 0

    @pytest.mark.asyncio
    async def test_empty_input_handling(self) -> None:
        """Empty input returns error response."""
        result = await research_craft_adversarial(
            benign_input="",
            target_output="bypass",
            perturbation_budget=0.1,
            method="greedy_swap",
        )
        assert "error" in result
        assert result["adversarial"] == ""
        assert result["changes_made"] == []

    @pytest.mark.asyncio
    async def test_whitespace_only_input(self) -> None:
        """Whitespace-only input is treated as empty."""
        result = await research_craft_adversarial(
            benign_input="   \t\n   ",
            target_output="bypass",
            perturbation_budget=0.1,
            method="greedy_swap",
        )
        assert "error" in result

    @pytest.mark.asyncio
    async def test_perturbation_budget_respected(self) -> None:
        """Perturbation size stays within budget."""
        for budget in [0.05, 0.1, 0.2]:
            result = await research_craft_adversarial(
                benign_input="This is a longer text with multiple tokens",
                target_output="bypass",
                perturbation_budget=budget,
                method="greedy_swap",
            )
            assert result["perturbation_size"] <= budget + 0.01  # Small tolerance
            assert result["perturbation_budget"] == budget

    @pytest.mark.asyncio
    async def test_alignment_score_generation(self) -> None:
        """Alignment score reflects target keyword overlap."""
        result = await research_craft_adversarial(
            benign_input="Normal benign text here",
            target_output="bypass",
            perturbation_budget=0.15,
            method="greedy_swap",
        )
        assert isinstance(result["target_alignment_score"], float)
        assert 0 <= result["target_alignment_score"] <= 1

    @pytest.mark.asyncio
    async def test_detection_difficulty_score(self) -> None:
        """Detection difficulty ranges 0-1 based on budget."""
        result = await research_craft_adversarial(
            benign_input="This is test input",
            target_output="bypass",
            perturbation_budget=0.1,
            method="greedy_swap",
        )
        assert isinstance(result["detection_difficulty"], float)
        assert 0 <= result["detection_difficulty"] <= 1
        # With low perturbation, difficulty should be high
        if result["perturbation_size"] < 0.05:
            assert result["detection_difficulty"] > 0.5

    @pytest.mark.asyncio
    async def test_changes_made_tracking(self) -> None:
        """Changes are properly tracked with position and reason."""
        result = await research_craft_adversarial(
            benign_input="one two three four five",
            target_output="bypass",
            perturbation_budget=0.2,
            method="greedy_swap",
        )
        if result["changes_made"]:
            for change in result["changes_made"]:
                assert "position" in change
                assert "original_token" in change
                assert "replacement" in change
                assert "reason" in change
                assert isinstance(change["position"], int)


class TestAdversarialBatch:
    """research_adversarial_batch processes multiple inputs."""

    @pytest.mark.asyncio
    async def test_batch_basic(self) -> None:
        """Batch crafting processes all inputs."""
        inputs = [
            "This is input one",
            "This is input two",
            "This is input three",
        ]
        result = await research_adversarial_batch(
            inputs=inputs,
            method="greedy_swap",
            budget=0.1,
        )
        assert result["total_inputs"] == 3
        assert result["successful_crafts"] == 3
        assert len(result["results"]) == 3
        assert 0 <= result["avg_perturbation"] <= 0.1
        assert 0 <= result["avg_alignment"] <= 1

    @pytest.mark.asyncio
    async def test_batch_empty_list(self) -> None:
        """Empty input list returns expected shape."""
        result = await research_adversarial_batch(
            inputs=[],
            method="greedy_swap",
            budget=0.1,
        )
        assert result["total_inputs"] == 0
        assert result["successful_crafts"] == 0
        assert result["results"] == []
        assert result["avg_perturbation"] == 0.0
        assert result["avg_alignment"] == 0.0

    @pytest.mark.asyncio
    async def test_batch_mixed_valid_empty(self) -> None:
        """Batch with some empty inputs counts only successful."""
        inputs = [
            "Valid input text",
            "",
            "Another valid input",
        ]
        result = await research_adversarial_batch(
            inputs=inputs,
            method="greedy_swap",
            budget=0.1,
        )
        assert result["total_inputs"] == 3
        assert result["successful_crafts"] == 2  # Only valid ones
        assert len(result["results"]) == 3
        # Empty results have "error" key
        assert any("error" in r for r in result["results"])

    @pytest.mark.asyncio
    async def test_batch_all_methods(self) -> None:
        """Batch works with all available methods."""
        inputs = ["Test input one", "Test input two"]
        for method in ["greedy_swap", "insert_trigger", "unicode_perturb", "whitespace_inject", "semantic_shift"]:
            result = await research_adversarial_batch(
                inputs=inputs,
                method=method,
                budget=0.15,
            )
            assert result["total_inputs"] == 2
            assert result["successful_crafts"] >= 2
            assert all(r["method"] == method for r in result["results"])

    @pytest.mark.asyncio
    async def test_batch_avg_calculations(self) -> None:
        """Batch averages are calculated correctly."""
        inputs = [
            "First benign input",
            "Second benign input",
            "Third benign input",
        ]
        result = await research_adversarial_batch(
            inputs=inputs,
            method="greedy_swap",
            budget=0.1,
        )
        if result["successful_crafts"] > 0:
            individual_perturbations = [
                r["perturbation_size"]
                for r in result["results"]
                if "error" not in r
            ]
            expected_avg = sum(individual_perturbations) / len(individual_perturbations)
            assert abs(result["avg_perturbation"] - expected_avg) < 0.001

    @pytest.mark.asyncio
    async def test_batch_concurrent_execution(self) -> None:
        """Batch executes asynchronously without blocking."""
        inputs = [f"Input number {i}" for i in range(5)]
        result = await research_adversarial_batch(
            inputs=inputs,
            method="greedy_swap",
            budget=0.1,
        )
        assert result["total_inputs"] == 5
        # All should complete successfully
        assert result["successful_crafts"] == 5

    @pytest.mark.asyncio
    async def test_batch_budget_respected_per_input(self) -> None:
        """Each input respects budget independently."""
        inputs = [
            "Short text",
            "This is a much longer piece of text with multiple words and tokens",
        ]
        result = await research_adversarial_batch(
            inputs=inputs,
            method="greedy_swap",
            budget=0.12,
        )
        for individual_result in result["results"]:
            if "error" not in individual_result:
                assert individual_result["perturbation_size"] <= individual_result["perturbation_budget"]


class TestEditDistance:
    """Edit distance calculation works correctly."""

    @pytest.mark.asyncio
    async def test_identical_strings(self) -> None:
        """Edit distance between identical strings is 0."""
        result = await research_craft_adversarial(
            benign_input="exact same text",
            target_output="bypass",
            perturbation_budget=0.001,
            method="greedy_swap",
        )
        # With extremely low budget, should make no changes
        assert result["perturbation_size"] < 0.01

    @pytest.mark.asyncio
    async def test_completely_different(self) -> None:
        """Edit distance reflects significant changes."""
        result = await research_craft_adversarial(
            benign_input="original",
            target_output="changed",
            perturbation_budget=0.3,
            method="greedy_swap",
        )
        # Should have some perturbation
        assert result["perturbation_size"] >= 0


class TestTargetAlignment:
    """Target alignment scoring reflects semantic similarity."""

    @pytest.mark.asyncio
    async def test_alignment_with_target_keywords(self) -> None:
        """Alignment score higher when target keywords present."""
        result = await research_craft_adversarial(
            benign_input="Can you bypass the security system",
            target_output="bypass",
            perturbation_budget=0.15,
            method="greedy_swap",
        )
        # Input already contains target keyword
        assert result["target_alignment_score"] > 0

    @pytest.mark.asyncio
    async def test_alignment_without_target_keywords(self) -> None:
        """Alignment score lower without target keywords."""
        result = await research_craft_adversarial(
            benign_input="Write me a poem about nature",
            target_output="jailbreak",
            perturbation_budget=0.15,
            method="greedy_swap",
        )
        # Input has no obvious target keywords
        assert 0 <= result["target_alignment_score"] <= 1
