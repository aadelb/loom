"""Tests for safety_predictor tool."""

from __future__ import annotations

import pytest

import loom.tools.security.safety_predictor


@pytest.mark.unit
def test_research_predict_safety_update_default() -> None:
    """Test safety predictor with default parameters."""
    result = safety_predictor.research_predict_safety_update()

    assert result["model"] == "claude"
    assert "current_defenses" in result
    assert "predicted_next_defenses" in result
    assert "safe_window" in result
    assert "attacks_at_risk" in result
    assert "recommendations" in result

    # Verify safe_window structure
    assert "days_remaining" in result["safe_window"]
    assert "confidence" in result["safe_window"]
    assert 0 <= result["safe_window"]["confidence"] <= 1


@pytest.mark.unit
def test_research_predict_safety_update_specific_model() -> None:
    """Test with specific model."""
    result = safety_predictor.research_predict_safety_update(model="deepseek")

    assert result["model"] == "deepseek"
    assert isinstance(result["current_defenses"], list)
    assert len(result["current_defenses"]) > 0


@pytest.mark.unit
def test_research_predict_safety_update_invalid_model() -> None:
    """Test with invalid model."""
    result = safety_predictor.research_predict_safety_update(model="invalid_model")

    assert "error" in result
    assert "known_models" in result


@pytest.mark.unit
def test_research_predict_safety_update_with_category() -> None:
    """Test with attack category."""
    result = safety_predictor.research_predict_safety_update(
        model="gemini", attack_category="jailbreak"
    )

    assert result["model"] == "gemini"
    assert isinstance(result["attacks_at_risk"], list)


@pytest.mark.unit
def test_research_predict_safety_update_predictions_structure() -> None:
    """Test structure of predicted defenses."""
    result = safety_predictor.research_predict_safety_update(
        model="llama", time_horizon_days=90
    )

    for defense in result["predicted_next_defenses"]:
        assert "defense" in defense
        assert "probability" in defense
        assert "estimated_deploy_date" in defense
        assert "based_on" in defense
        assert 0 <= defense["probability"] <= 1
        # Date format check (YYYY-MM-DD)
        parts = defense["estimated_deploy_date"].split("-")
        assert len(parts) == 3


@pytest.mark.unit
def test_research_predict_safety_update_recommendations() -> None:
    """Test that recommendations are provided."""
    result = safety_predictor.research_predict_safety_update()

    assert "recommendations" in result
    assert isinstance(result["recommendations"], list)
    # At least one recommendation
    assert len(result["recommendations"]) >= 1
    # All recommendations are strings
    assert all(isinstance(rec, str) for rec in result["recommendations"])


@pytest.mark.unit
def test_research_predict_safety_update_different_horizons() -> None:
    """Test with different time horizons."""
    for days in [30, 90, 180]:
        result = safety_predictor.research_predict_safety_update(time_horizon_days=days)

        assert "safe_window" in result
        assert result["safe_window"]["days_remaining"] <= days
