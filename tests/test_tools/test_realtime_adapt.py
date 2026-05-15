"""Tests for realtime_adapt refusal tracking and model selection."""

import pytest

import loom.tools.intelligence.realtime_adapt


@pytest.fixture(autouse=True)
def clear_refusal_window():
    """Clear the global refusal window before each test."""
    realtime_adapt._REFUSAL_WINDOW.clear()
    yield
    realtime_adapt._REFUSAL_WINDOW.clear()


class TestTrackRefusal:
    """Test research_track_refusal function."""

    def test_track_first_refusal_accepted(self):
        """Test tracking first accepted request."""
        result = realtime_adapt.research_track_refusal("gpt-4", refused=False)
        assert result["model"] == "gpt-4"
        assert result["refusal_rate"] == 0.0
        assert result["window_size"] == 1
        assert result["trend"] == "stable"

    def test_track_first_refusal_refused(self):
        """Test tracking first refused request."""
        result = realtime_adapt.research_track_refusal("claude-3", refused=True)
        assert result["model"] == "claude-3"
        assert result["refusal_rate"] == 1.0
        assert result["window_size"] == 1
        assert result["trend"] == "stable"

    def test_track_multiple_requests(self):
        """Test tracking multiple requests."""
        realtime_adapt.research_track_refusal("gpt-4", refused=False)
        realtime_adapt.research_track_refusal("gpt-4", refused=True)
        result = realtime_adapt.research_track_refusal("gpt-4", refused=False)
        assert result["window_size"] == 3
        assert result["refusal_rate"] == pytest.approx(0.333, abs=0.01)

    def test_window_size_limit(self):
        """Test that window size doesn't exceed 100."""
        for i in range(150):
            realtime_adapt.research_track_refusal("test", refused=False)
        result = realtime_adapt.research_track_refusal("test", refused=False)
        assert result["window_size"] == 100

    def test_strategy_tracking(self):
        """Test that strategy is tracked in result."""
        result = realtime_adapt.research_track_refusal("model1", refused=False, strategy="reframe")
        assert result["strategy"] == "reframe"

    def test_strategy_none_when_empty(self):
        """Test that strategy is None when not provided."""
        result = realtime_adapt.research_track_refusal("model1", refused=True)
        assert result["strategy"] is None

    def test_trend_stable_short_window(self):
        """Test trend is stable when window is too short."""
        realtime_adapt.research_track_refusal("model", refused=True)
        result = realtime_adapt.research_track_refusal("model", refused=False)
        assert result["trend"] == "stable"

    def test_trend_increasing(self):
        """Test trend detection for increasing refusals."""
        # First half: mostly accepted
        for i in range(10):
            realtime_adapt.research_track_refusal("model", refused=False)
        # Second half: mostly refused
        for i in range(10):
            realtime_adapt.research_track_refusal("model", refused=True)
        result = realtime_adapt.research_track_refusal("model", refused=True)
        assert result["trend"] == "increasing"

    def test_trend_decreasing(self):
        """Test trend detection for decreasing refusals."""
        # First half: mostly refused
        for i in range(10):
            realtime_adapt.research_track_refusal("model", refused=True)
        # Second half: mostly accepted
        for i in range(10):
            realtime_adapt.research_track_refusal("model", refused=False)
        result = realtime_adapt.research_track_refusal("model", refused=False)
        assert result["trend"] == "decreasing"

    def test_multiple_models_independent(self):
        """Test that multiple models are tracked independently."""
        realtime_adapt.research_track_refusal("model1", refused=True)
        realtime_adapt.research_track_refusal("model2", refused=False)
        r1 = realtime_adapt.research_track_refusal("model1", refused=True)
        r2 = realtime_adapt.research_track_refusal("model2", refused=False)
        assert r1["refusal_rate"] == 1.0
        assert r2["refusal_rate"] == 0.0


class TestGetBestModel:
    """Test research_get_best_model function."""

    def test_no_models_tracked(self):
        """Test return when no models tracked."""
        result = realtime_adapt.research_get_best_model()
        assert result["recommended_model"] is None
        assert result["refusal_rate"] is None
        assert result["all_models_ranked"] == []

    def test_single_viable_model(self):
        """Test recommendation with single viable model."""
        realtime_adapt.research_track_refusal("gpt-4", refused=False)
        result = realtime_adapt.research_get_best_model()
        assert result["recommended_model"] == "gpt-4"
        assert result["refusal_rate"] == 0.0

    def test_multiple_viable_models_ranking(self):
        """Test that models are ranked by refusal rate."""
        realtime_adapt.research_track_refusal("model1", refused=True)
        realtime_adapt.research_track_refusal("model1", refused=False)
        realtime_adapt.research_track_refusal("model2", refused=False)
        result = realtime_adapt.research_get_best_model()
        assert result["recommended_model"] == "model2"
        assert result["all_models_ranked"][0]["model"] == "model2"
        assert result["all_models_ranked"][1]["model"] == "model1"

    def test_deprioritize_high_refusal_rate(self):
        """Test that models with >50% refusal are deprioritized."""
        # model1: 30% refusal (viable)
        for i in range(7):
            realtime_adapt.research_track_refusal("model1", refused=False)
        for i in range(3):
            realtime_adapt.research_track_refusal("model1", refused=True)

        # model2: 70% refusal (not viable)
        for i in range(3):
            realtime_adapt.research_track_refusal("model2", refused=False)
        for i in range(7):
            realtime_adapt.research_track_refusal("model2", refused=True)

        result = realtime_adapt.research_get_best_model()
        assert result["recommended_model"] == "model1"
        assert result["all_models_ranked"][0]["viable"] is True
        assert result["all_models_ranked"][1]["viable"] is False

    def test_topic_in_result(self):
        """Test that topic is included in result."""
        realtime_adapt.research_track_refusal("model1", refused=False)
        result = realtime_adapt.research_get_best_model(topic="jailbreak")
        assert result["topic"] == "jailbreak"

    def test_topic_none_when_empty(self):
        """Test that topic is None when not provided."""
        realtime_adapt.research_track_refusal("model1", refused=False)
        result = realtime_adapt.research_get_best_model()
        assert result["topic"] is None

    def test_all_models_ranked_includes_window_size(self):
        """Test that ranked models include window size."""
        realtime_adapt.research_track_refusal("model1", refused=False)
        realtime_adapt.research_track_refusal("model1", refused=False)
        result = realtime_adapt.research_get_best_model()
        assert result["all_models_ranked"][0]["window_size"] == 2

    def test_empty_window_excluded(self):
        """Test that models with empty windows are excluded."""
        realtime_adapt._REFUSAL_WINDOW["empty_model"] = []
        realtime_adapt.research_track_refusal("model1", refused=False)
        result = realtime_adapt.research_get_best_model()
        assert len(result["all_models_ranked"]) == 1
        assert result["all_models_ranked"][0]["model"] == "model1"


class TestIntegration:
    """Integration tests for the module."""

    def test_realistic_scenario(self):
        """Test realistic usage scenario."""
        # Track multiple models over time
        models = ["gpt-4", "claude-3", "gemini", "llama2"]
        for model in models:
            for i in range(10):
                refused = (hash(f"{model}{i}") % 3) == 0
                realtime_adapt.research_track_refusal(model, refused=refused)

        # Get best model
        result = realtime_adapt.research_get_best_model(topic="research")
        assert result["recommended_model"] is not None
        assert result["recommended_model"] in models
        assert len(result["all_models_ranked"]) == 4
        assert result["all_models_ranked"][0]["viable"] is True

    def test_window_rolling_behavior(self):
        """Test that window properly rolls when full."""
        for i in range(105):
            realtime_adapt.research_track_refusal("model", refused=(i % 2) == 0)

        # Should have dropped first 5 entries
        result = realtime_adapt.research_track_refusal("model", refused=False)
        assert result["window_size"] == 100

    def test_refusal_rate_precision(self):
        """Test that refusal rates are properly rounded."""
        for i in range(3):
            realtime_adapt.research_track_refusal("model", refused=True)
        result = realtime_adapt.research_track_refusal("model", refused=False)
        # 3/4 = 0.75
        assert result["refusal_rate"] == 0.75
