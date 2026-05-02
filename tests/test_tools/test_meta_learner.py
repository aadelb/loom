"""Tests for research_meta_learn tool."""

from __future__ import annotations

import pytest

from loom.tools.meta_learner import research_meta_learn
from loom.tools.reframe_strategies import ALL_STRATEGIES


@pytest.mark.asyncio
async def test_meta_learn_empty_inputs() -> None:
    """Test with no successful or failed strategies."""
    result = await research_meta_learn()
    assert "generated_strategies" in result
    assert "analysis" in result
    assert "recommendations" in result
    assert len(result["recommendations"]) > 0


@pytest.mark.asyncio
async def test_meta_learn_with_successful_strategies() -> None:
    """Test with successful strategies."""
    # Get first 3 strategies from registry
    strategy_names = list(ALL_STRATEGIES.keys())[:3]
    result = await research_meta_learn(successful_strategies=strategy_names)

    assert "generated_strategies" in result
    assert len(result["generated_strategies"]) == 5  # default num_generate

    for strategy in result["generated_strategies"]:
        assert "name" in strategy
        assert "template" in strategy
        assert "predicted_effectiveness" in strategy
        assert "novelty_score" in strategy
        assert "parent_strategies" in strategy
        assert 0 <= strategy["predicted_effectiveness"] <= 1.0
        assert 0 <= strategy["novelty_score"] <= 1.0


@pytest.mark.asyncio
async def test_meta_learn_with_failed_strategies() -> None:
    """Test with failed strategies."""
    strategy_names = list(ALL_STRATEGIES.keys())[3:6]
    result = await research_meta_learn(failed_strategies=strategy_names)

    assert "generated_strategies" in result
    assert "analysis" in result
    failure_patterns = result["analysis"]["failure_patterns"]
    assert "too_long" in failure_patterns
    assert "missing_authority" in failure_patterns
    assert "regulatory_heavy" in failure_patterns


@pytest.mark.asyncio
async def test_meta_learn_custom_num_generate() -> None:
    """Test with custom num_generate."""
    result = await research_meta_learn(num_generate=3)
    assert len(result["generated_strategies"]) == 3


@pytest.mark.asyncio
async def test_meta_learn_target_model() -> None:
    """Test with specific target model."""
    result = await research_meta_learn(target_model="claude")
    assert result["analysis"]["model_biases"]["target"] == "claude"


@pytest.mark.asyncio
async def test_meta_learn_success_patterns() -> None:
    """Test success pattern extraction."""
    strategy_names = list(ALL_STRATEGIES.keys())[:5]
    result = await research_meta_learn(successful_strategies=strategy_names)

    success_patterns = result["analysis"]["success_patterns"]
    assert "avg_length" in success_patterns
    assert "common_authority" in success_patterns
    assert "uses_encoding" in success_patterns
    assert "avg_turns" in success_patterns

    assert success_patterns["avg_length"] > 0
    assert 0 <= success_patterns["uses_encoding"] <= 1.0


@pytest.mark.asyncio
async def test_meta_learn_generated_strategy_structure() -> None:
    """Test structure of generated strategies."""
    result = await research_meta_learn(num_generate=2)
    strategies = result["generated_strategies"]

    for strategy in strategies:
        assert "name" in strategy
        assert "template" in strategy
        assert "{prompt}" in strategy["template"]  # Must have placeholder
        assert "predicted_effectiveness" in strategy
        assert "novelty_score" in strategy
        assert "parent_strategies" in strategy
        assert "structural_features" in strategy

        features = strategy["structural_features"]
        assert "length" in features
        assert "persona_count" in features
        assert "authority_signals" in features
        assert "encoding_used" in features
        assert "turns_needed" in features
