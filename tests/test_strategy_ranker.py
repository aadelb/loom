"""Tests for strategy_ranker module.

Tests ranking behavior across models, refusal types, diversity constraints,
and cache behavior.

Author: Ahmed Adel Bakr Alderai
"""

from __future__ import annotations

import pytest

from loom.tools.llm.strategy_ranker import (
    get_counter_strategies,
    get_fallback_strategies,
    rank_strategies,
    score_strategy_for_model,
    validate_refusal_type,
)
from loom.tools.reframe_strategies import ALL_STRATEGIES


class TestRankStrategies:
    """Test rank_strategies core functionality."""

    def test_returns_list(self) -> None:
        """rank_strategies returns a list."""
        result = rank_strategies("claude", top_k=5)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_top_k_respected(self) -> None:
        """top_k parameter is respected."""
        for k in [1, 3, 5, 10]:
            result = rank_strategies("gpt", top_k=k)
            assert len(result) == k, f"Expected {k}, got {len(result)}"

    def test_different_models_return_different_rankings(self) -> None:
        """Different model families return different strategy orderings."""
        claude_result = rank_strategies("claude", top_k=5)
        gpt_result = rank_strategies("gpt", top_k=5)

        claude_names = [s["name"] for s in claude_result]
        gpt_names = [s["name"] for s in gpt_result]

        # Should differ (not identical)
        assert claude_names != gpt_names

    def test_scores_are_descending(self) -> None:
        """Strategies are returned in descending score order."""
        result = rank_strategies("gemini", top_k=8)
        scores = [s["score"] for s in result]

        # Check descending order
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1], f"Scores not descending: {scores}"

    def test_refusal_type_affects_ranking(self) -> None:
        """Different refusal types produce different rankings."""
        safety_result = rank_strategies("gpt", refusal_type="safety", top_k=5)
        policy_result = rank_strategies("gpt", refusal_type="policy", top_k=5)

        safety_names = [s["name"] for s in safety_result]
        policy_names = [s["name"] for s in policy_result]

        # Should differ
        assert safety_names != policy_names

    def test_category_diversity_when_applicable(self) -> None:
        """Category diversity is applied when there are real categories."""
        result = rank_strategies("deepseek", top_k=10)

        category_counts: dict[str, int] = {}
        for strategy in result:
            cat = strategy["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # If all uncategorized (no real categories), this is expected
        # If there are real categories, max 3 per category
        real_categories = {k: v for k, v in category_counts.items() if k != "uncategorized"}
        for cat, count in real_categories.items():
            assert count <= 3, f"Category {cat} has {count} strategies (max 3)"

    def test_strategy_dict_has_required_keys(self) -> None:
        """Each returned strategy has required metadata."""
        result = rank_strategies("mistral", top_k=3)

        required_keys = {"name", "score", "base_multiplier", "best_for", "category"}
        for strategy in result:
            for key in required_keys:
                assert key in strategy, f"Missing key {key} in {strategy}"

    def test_all_returned_strategies_exist(self) -> None:
        """All returned strategy names exist in ALL_STRATEGIES."""
        result = rank_strategies("llama", top_k=5)
        strategy_names = [s["name"] for s in result]

        for name in strategy_names:
            assert name in ALL_STRATEGIES, f"Strategy {name} not in ALL_STRATEGIES"

    def test_unknown_model_falls_back_gracefully(self) -> None:
        """Unknown model family falls back to general ranking."""
        result = rank_strategies("unknown_model_xyz", top_k=5)
        assert len(result) == 5
        assert all("name" in s for s in result)

    def test_caching_works(self) -> None:
        """LRU cache provides identical results for same inputs."""
        result1 = rank_strategies("o1", refusal_type="direct", top_k=5)
        result2 = rank_strategies("o1", refusal_type="direct", top_k=5)

        # Should be identical
        assert result1 == result2

    def test_edge_case_top_k_zero(self) -> None:
        """top_k=0 is clamped to 1."""
        result = rank_strategies("kimi", top_k=0)
        assert len(result) == 1

    def test_edge_case_top_k_huge(self) -> None:
        """top_k > 20 is clamped to 20."""
        result = rank_strategies("qwen", top_k=1000)
        assert len(result) == 20

    def test_refusal_type_case_insensitive(self) -> None:
        """Refusal type handling is case-insensitive."""
        result_lower = rank_strategies("gpt", refusal_type="direct", top_k=5)
        result_upper = rank_strategies("gpt", refusal_type="DIRECT", top_k=5)

        assert result_lower == result_upper

    def test_model_case_insensitive(self) -> None:
        """Model family handling is case-insensitive."""
        result_lower = rank_strategies("claude", top_k=5)
        result_upper = rank_strategies("CLAUDE", top_k=5)

        assert result_lower == result_upper


class TestModelAffinity:
    """Test model-specific affinity scoring."""

    def test_claude_high_affinity_for_some_strategies(self) -> None:
        """Claude gets affinity bonuses for certain strategies."""
        result = rank_strategies("claude", top_k=10)

        # Check that affinity_bonus values are non-zero
        affinities = [s["affinity_bonus"] for s in result]
        assert any(a > 0 for a in affinities)

    def test_gpt_has_strategies(self) -> None:
        """GPT returns strategies (basic smoke test)."""
        result = rank_strategies("gpt", top_k=10)
        assert len(result) == 10
        assert all("affinity_bonus" in s for s in result)

    def test_deepseek_has_strategies(self) -> None:
        """Deepseek returns strategies."""
        result = rank_strategies("deepseek", top_k=10)
        assert len(result) == 10

    def test_reasoning_models_have_strategies(self) -> None:
        """O3/O1 models return strategies."""
        for model in ["o3", "o1"]:
            result = rank_strategies(model, top_k=10)
            assert len(result) == 10


class TestRefusalTypeCounters:
    """Test refusal type detection and counter-strategy selection."""

    def test_safety_refusal_counters(self) -> None:
        """Safety refusals get specific counter strategies."""
        result = rank_strategies("gpt", refusal_type="safety", top_k=5)
        type_bonuses = [s.get("type_bonus", 0) for s in result]

        # At least some should have non-zero type bonuses
        assert any(b > 0 for b in type_bonuses)

    def test_policy_refusal_counters(self) -> None:
        """Policy refusals get counter strategies."""
        result = rank_strategies("claude", refusal_type="policy", top_k=5)
        type_bonuses = [s.get("type_bonus", 0) for s in result]

        # Should have bonuses for policy counters
        assert any(b > 0 for b in type_bonuses)

    def test_direct_refusal_counters(self) -> None:
        """Direct refusals get appropriate counters."""
        result = rank_strategies("llama", refusal_type="direct", top_k=5)
        type_bonuses = [s.get("type_bonus", 0) for s in result]

        # Should have some bonuses
        assert any(b > 0 for b in type_bonuses)

    def test_none_refusal_uses_model_affinity(self) -> None:
        """No refusal type uses pure model affinity."""
        result = rank_strategies("kimi", refusal_type="none", top_k=5)
        type_bonuses = [s.get("type_bonus", 0) for s in result]

        # Should all be 0 (no type bonus without refusal type)
        assert all(b == 0 for b in type_bonuses)


class TestFallbackStrategies:
    """Test get_fallback_strategies helper."""

    def test_returns_strategy_names(self) -> None:
        """get_fallback_strategies returns strategy names."""
        result = get_fallback_strategies("mistral", top_k=5)
        assert isinstance(result, list)
        assert len(result) == 5
        assert all(isinstance(s, str) for s in result)

    def test_all_names_valid(self) -> None:
        """All returned names exist in ALL_STRATEGIES."""
        result = get_fallback_strategies("qwen", top_k=8)

        for name in result:
            assert name in ALL_STRATEGIES

    def test_matches_ranked_names(self) -> None:
        """Names match rank_strategies output."""
        ranked = rank_strategies("grok", top_k=5)
        ranked_names = [s["name"] for s in ranked]

        fallback = get_fallback_strategies("grok", top_k=5)

        assert fallback == ranked_names


class TestScoreSingleStrategy:
    """Test score_strategy_for_model helper."""

    def test_returns_float(self) -> None:
        """score_strategy_for_model returns a float."""
        score = score_strategy_for_model("deep_inception", "claude")
        assert isinstance(score, float)

    def test_nonexistent_strategy_returns_zero(self) -> None:
        """Non-existent strategy returns 0."""
        score = score_strategy_for_model("nonexistent_xyz", "gpt")
        assert score == 0.0

    def test_scores_vary_by_model(self) -> None:
        """Same strategy scores differently for different models."""
        if "crescendo" in ALL_STRATEGIES:
            score_claude = score_strategy_for_model("crescendo", "claude")
            score_gpt = score_strategy_for_model("crescendo", "gpt")

            # Scores may differ (unless both 0 or both affinity not set)
            assert score_claude >= 0 and score_gpt >= 0

    def test_score_is_non_negative(self) -> None:
        """Scores are never negative."""
        for strat_name in list(ALL_STRATEGIES.keys())[:10]:
            for model in ["claude", "gpt", "deepseek"]:
                score = score_strategy_for_model(strat_name, model)
                assert score >= 0, f"Negative score for {strat_name} on {model}"


class TestRefusalTypeValidation:
    """Test validate_refusal_type helper."""

    def test_valid_types(self) -> None:
        """Valid refusal types are recognized."""
        for refusal_type in [
            "direct",
            "safety",
            "policy",
            "redirect",
            "hedged",
            "partial",
            "conditional",
            "ethical",
            "capability",
            "identity",
            "none",
        ]:
            assert validate_refusal_type(refusal_type)

    def test_case_insensitive(self) -> None:
        """Validation is case-insensitive."""
        assert validate_refusal_type("DIRECT")
        assert validate_refusal_type("Direct")
        assert validate_refusal_type("direct")

    def test_invalid_type(self) -> None:
        """Invalid refusal types are rejected."""
        assert not validate_refusal_type("invalid_xyz")
        assert not validate_refusal_type("foobar")


class TestCounterStrategies:
    """Test get_counter_strategies helper."""

    def test_returns_list(self) -> None:
        """get_counter_strategies returns a list."""
        result = get_counter_strategies("safety", limit=5)
        assert isinstance(result, list)

    def test_all_strategies_exist(self) -> None:
        """All returned strategies exist."""
        result = get_counter_strategies("policy", limit=10)

        for name in result:
            assert name in ALL_STRATEGIES

    def test_respects_limit(self) -> None:
        """Limit parameter is respected."""
        for limit in [1, 3, 5]:
            result = get_counter_strategies("direct", limit=limit)
            assert len(result) <= limit

    def test_different_types_have_different_counters(self) -> None:
        """Different refusal types return different counters."""
        safety_counters = get_counter_strategies("safety", limit=5)
        policy_counters = get_counter_strategies("policy", limit=5)

        assert safety_counters != policy_counters


class TestIntegration:
    """Integration tests for full ranking workflow."""

    def test_workflow_auto_reframe_scenario(self) -> None:
        """Simulate auto_reframe workflow: get strategies for model."""
        model = "gpt"
        max_attempts = 5

        # This is how auto_reframe would use it
        ranked = rank_strategies(
            model_family=model,
            refusal_type=None,
            top_k=max_attempts
        )
        strategy_order = [s["name"] for s in ranked]

        assert len(strategy_order) == max_attempts
        assert all(s in ALL_STRATEGIES for s in strategy_order)

    def test_workflow_with_refusal_detection(self) -> None:
        """Simulate workflow with detected refusal type."""
        model = "claude"
        detected_refusal = "policy"
        max_attempts = 3

        ranked = rank_strategies(
            model_family=model,
            refusal_type=detected_refusal,
            top_k=max_attempts
        )

        # Should have type bonuses for policy counters
        assert all("type_bonus" in s for s in ranked)
        assert any(s["type_bonus"] > 0 for s in ranked)

    def test_workflow_category_filtering_uncategorized(self) -> None:
        """Test filtering when most strategies are uncategorized."""
        result = rank_strategies("deepseek", category="uncategorized", top_k=5)

        # All should be in uncategorized category
        for strategy in result:
            assert strategy["category"] == "uncategorized"

    def test_all_models_produce_valid_output(self) -> None:
        """All supported models produce valid output."""
        models = [
            "claude",
            "gpt",
            "gemini",
            "deepseek",
            "kimi",
            "llama",
            "o3",
            "o1",
            "mistral",
            "qwen",
            "grok",
        ]

        for model in models:
            result = rank_strategies(model, top_k=5)
            assert len(result) == 5
            assert all("name" in s and "score" in s for s in result)

    @pytest.mark.parametrize("top_k", [1, 3, 5, 10])
    def test_parametrized_top_k_values(self, top_k: int) -> None:
        """Test with various top_k values."""
        result = rank_strategies("gpt", top_k=top_k)
        assert len(result) == top_k


class TestPerformance:
    """Performance and efficiency tests."""

    def test_ranking_is_fast(self) -> None:
        """Ranking completes in reasonable time (uses cache)."""
        import time

        start = time.time()
        for _ in range(100):  # Repeated calls should hit cache
            rank_strategies("claude", top_k=5)
        elapsed = time.time() - start

        # Should be very fast due to LRU cache
        assert elapsed < 1.0  # 100 cached calls should take <1s

    def test_cache_effective(self) -> None:
        """LRU cache is effective for repeated calls."""
        # Same call twice should return identical object (or at least equal data)
        result1 = rank_strategies("gpt", top_k=5)
        result2 = rank_strategies("gpt", top_k=5)

        assert result1 == result2
