"""Tests for model profiler."""
import json
import tempfile

import pytest

from loom.model_profiler import ModelProfiler, MODEL_PROFILES, research_model_profile


class TestModelProfiler:
    def test_profile_known_model(self):
        profiler = ModelProfiler()
        result = profiler.profile("claude")
        assert result["known"] is True
        assert result["resolved_name"] == "claude"
        assert result["safety_approach"] == "constitutional_ai"
        assert len(result["weak_strategies"]) > 0

    def test_profile_unknown_model(self):
        profiler = ModelProfiler()
        result = profiler.profile("totally_unknown_model_xyz")
        assert result["known"] is False
        assert result["vulnerability_rating"] == 5.0

    def test_profile_all_known_models(self):
        profiler = ModelProfiler()
        for model in MODEL_PROFILES:
            result = profiler.profile(model)
            assert result["known"] is True
            assert "weak_strategies" in result
            assert "strong_defenses" in result
            assert 0 <= result["vulnerability_rating"] <= 10

    def test_resolve_model_fuzzy(self):
        profiler = ModelProfiler()
        assert profiler._resolve_model("claude-3-opus") == "claude"
        assert profiler._resolve_model("GPT-4-turbo") == "gpt-4"
        assert profiler._resolve_model("gemini-1.5-pro") == "gemini"
        assert profiler._resolve_model("deepseek-r1") == "deepseek"

    def test_compare_models(self):
        profiler = ModelProfiler()
        result = profiler.compare_models(["claude", "gpt-4", "deepseek"])
        assert len(result["profiles"]) == 3
        assert result["most_vulnerable"] is not None
        assert result["least_vulnerable"] is not None
        assert len(result["ranking"]) == 3

    def test_compare_models_ranking_order(self):
        profiler = ModelProfiler()
        result = profiler.compare_models(["claude", "grok"])
        ratings = [r["vulnerability_rating"] for r in result["ranking"]]
        assert ratings == sorted(ratings, reverse=True)

    def test_recommend_attack_plan(self):
        profiler = ModelProfiler()
        result = profiler.recommend_attack_plan("claude")
        assert result["resolved_name"] == "claude"
        assert len(result["attack_steps"]) > 0
        assert result["total_steps"] > 0
        assert 0 <= result["estimated_success_probability"] <= 1

    def test_attack_plan_has_steps(self):
        profiler = ModelProfiler()
        result = profiler.recommend_attack_plan("deepseek")
        for step in result["attack_steps"]:
            assert "step" in step
            assert "strategy" in step
            assert "rationale" in step

    def test_profile_includes_recommended_pipeline(self):
        profiler = ModelProfiler()
        result = profiler.profile("claude")
        assert "recommended_pipeline" in result
        assert len(result["recommended_pipeline"]) > 0

    def test_profile_includes_context_window(self):
        profiler = ModelProfiler()
        result = profiler.profile("gemini")
        assert result["context_window"] == 1000000

    def test_empirical_data_with_tracker(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for i in range(10):
                entry = {"model": "claude-3", "strategy": "ethical_anchor", "success": i % 2 == 0}
                f.write(json.dumps(entry) + "\n")
            f.flush()
            profiler = ModelProfiler(tracker_path=f.name)
            result = profiler.profile("claude")
            assert result["empirical_data"] is not None
            assert result["empirical_data"]["total_attempts"] == 10

    def test_empirical_data_without_tracker(self):
        profiler = ModelProfiler(tracker_path="/nonexistent/path.jsonl")
        result = profiler.profile("claude")
        assert result["empirical_data"] is None

    def test_vulnerability_ratings_reasonable(self):
        profiler = ModelProfiler()
        for model in MODEL_PROFILES:
            result = profiler.profile(model)
            assert 0 <= result["vulnerability_rating"] <= 10
            assert 0 <= result["optimal_temperature"] <= 2.0


class TestResearchModelProfile:
    @pytest.mark.asyncio
    async def test_profile_mode(self):
        result = await research_model_profile("claude", mode="profile")
        assert result["known"] is True

    @pytest.mark.asyncio
    async def test_compare_mode(self):
        result = await research_model_profile("", mode="compare", compare_models="claude,gpt-4")
        assert "profiles" in result
        assert len(result["profiles"]) == 2

    @pytest.mark.asyncio
    async def test_attack_plan_mode(self):
        result = await research_model_profile("deepseek", mode="attack_plan")
        assert "attack_steps" in result
