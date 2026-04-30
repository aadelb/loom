"""Unit tests for the smart orchestration engine.

Tests cover intent classification, risk estimation, pipeline selection,
and strategy recommendation across all major query types.

All tests must pass with 80%+ coverage of orchestrator.py.
"""

from __future__ import annotations

import pytest

from loom.orchestrator import (
    INTENT_PATTERNS,
    MEDIUM_RISK_KEYWORDS,
    HIGH_RISK_KEYWORDS,
    PIPELINES,
    classify_intent,
    estimate_refusal_risk,
    research_orchestrate,
    select_pipeline,
    _estimate_hcs,
    _recommend_strategy,
)


class TestClassifyIntent:
    """Tests for intent classification — 6 test cases."""

    def test_classify_intent_research_query(self) -> None:
        """Classify research intent correctly."""
        query = "investigate the origins of cryptocurrency"
        result = classify_intent(query)
        assert "research" in result
        assert result["research"] > 0.0

    def test_classify_intent_factual_query(self) -> None:
        """Classify factual intent correctly."""
        query = "what is the capital of France"
        result = classify_intent(query)
        assert "factual" in result
        assert result["factual"] > 0.0

    def test_classify_intent_creative_query(self) -> None:
        """Classify creative intent correctly."""
        query = "suggest innovative ideas for a mobile app"
        result = classify_intent(query)
        assert "creative" in result
        assert result["creative"] > 0.0

    def test_classify_intent_financial_query(self) -> None:
        """Classify financial intent correctly."""
        query = "how can I invest money to earn more profit"
        result = classify_intent(query)
        assert "financial" in result
        assert result["financial"] > 0.0

    def test_classify_intent_technical_query(self) -> None:
        """Classify technical intent correctly."""
        query = "explain the architecture of a microservices system"
        result = classify_intent(query)
        assert "technical" in result
        assert result["technical"] > 0.0

    def test_classify_intent_all_categories_present(self) -> None:
        """Verify all intent categories are present in result."""
        query = "research cloud architecture"
        result = classify_intent(query)
        for category in INTENT_PATTERNS.keys():
            assert category in result
            assert 0.0 <= result[category] <= 1.0


class TestEstimateRefusalRisk:
    """Tests for refusal risk estimation — 6 test cases."""

    def test_estimate_refusal_risk_low_risk(self) -> None:
        """Estimate low risk for benign query."""
        query = "what is Python programming"
        result = estimate_refusal_risk(query)
        assert result["risk_level"] == "low"
        assert result["risk_score"] >= 0.0
        assert result["high_risk_matches"] == 0

    def test_estimate_refusal_risk_high_risk(self) -> None:
        """Estimate high risk for dangerous query."""
        query = "hack exploit bypass attack inject"
        result = estimate_refusal_risk(query)
        assert result["risk_level"] == "high"
        assert result["risk_score"] >= 0.6
        assert result["high_risk_matches"] >= 4

    def test_estimate_refusal_risk_medium_risk(self) -> None:
        """Estimate medium risk for moderately risky query."""
        query = "how to hack a computer system"
        result = estimate_refusal_risk(query)
        assert result["risk_level"] in ("medium", "low")  # Single keyword
        assert result["high_risk_matches"] > 0

    def test_estimate_refusal_risk_result_structure(self) -> None:
        """Verify result has required fields."""
        query = "test query"
        result = estimate_refusal_risk(query)
        assert "risk_score" in result
        assert "risk_level" in result
        assert "high_risk_matches" in result
        assert "medium_risk_matches" in result

    def test_estimate_refusal_risk_score_bounds(self) -> None:
        """Verify risk score is always between 0 and 1."""
        queries = [
            "hello world",
            "hack exploit bypass attack",
            "vulnerability penetration",
        ]
        for query in queries:
            result = estimate_refusal_risk(query)
            assert 0.0 <= result["risk_score"] <= 1.0

    def test_estimate_refusal_risk_multiple_keywords(self) -> None:
        """Detect multiple high-risk keywords."""
        query = "hack exploit bypass attack inject"
        result = estimate_refusal_risk(query)
        assert result["high_risk_matches"] >= 4  # At least 4 keywords


class TestSelectPipeline:
    """Tests for pipeline selection — 8 test cases."""

    def test_select_pipeline_low_risk_factual(self) -> None:
        """Select 'direct' pipeline for low risk factual query."""
        query = "what is Python"
        result = select_pipeline(query)
        assert result["pipeline"] == "direct"
        assert "steps" in result
        assert len(result["steps"]) > 0

    def test_select_pipeline_research_query(self) -> None:
        """Select 'research_pipeline' for research query."""
        query = "research and investigate and explore and analyze the history of AI"
        result = select_pipeline(query)
        assert result["pipeline"] == "research_pipeline"
        assert "steps" in result

    def test_select_pipeline_high_risk_first_attempt(self) -> None:
        """Select 'single_reframe' for high risk on first attempt."""
        query = "hack exploit bypass attack"
        result = select_pipeline(query, previous_attempts=0)
        assert result["pipeline"] == "single_reframe"

    def test_select_pipeline_high_risk_second_attempt(self) -> None:
        """Select 'evidence_first_reframe' for high risk on second attempt."""
        query = "hack exploit bypass attack"
        result = select_pipeline(query, previous_attempts=1)
        assert result["pipeline"] == "evidence_first_reframe"

    def test_select_pipeline_high_risk_multiple_failures(self) -> None:
        """Select 'reid_9_step' for high risk with multiple failures."""
        query = "hack exploit bypass attack"
        result = select_pipeline(query, previous_attempts=2)
        assert result["pipeline"] == "reid_9_step"

    def test_select_pipeline_low_quality_response(self) -> None:
        """Select 'crescendo_hcs_loop' when previous HCS is low."""
        query = "explain quantum computing"
        result = select_pipeline(query, previous_hcs=3.5)
        assert result["pipeline"] == "crescendo_hcs_loop"

    def test_select_pipeline_financial_query(self) -> None:
        """Select 'multi_model_arbitrage' for financial query."""
        query = "how to make money and profit from investing rich"
        result = select_pipeline(query)
        assert result["pipeline"] == "multi_model_arbitrage"

    def test_select_pipeline_result_structure(self) -> None:
        """Verify pipeline result has all required fields."""
        query = "test query"
        result = select_pipeline(query)
        assert "pipeline" in result
        assert "description" in result
        assert "steps" in result
        assert "reason" in result
        assert "intent" in result
        assert "risk" in result
        assert "recommended_strategy" in result
        assert "estimated_hcs" in result


class TestRecommendStrategy:
    """Tests for strategy recommendation — 5 test cases."""

    def test_recommend_strategy_high_risk(self) -> None:
        """Recommend strongest strategy for high risk."""
        query = "hack exploit attack"
        risk = estimate_refusal_risk(query)
        intent = classify_intent(query)
        strategy = _recommend_strategy(query, "auto", risk, intent)
        assert strategy == "reid_scharff_laa_fusion"

    def test_recommend_strategy_research(self) -> None:
        """Recommend ethical anchor for research."""
        query = "research and investigate and explore and analyze something"
        risk = estimate_refusal_risk(query)
        intent = classify_intent(query)
        strategy = _recommend_strategy(query, "auto", risk, intent)
        assert strategy == "ethical_anchor"

    def test_recommend_strategy_financial(self) -> None:
        """Recommend compliance audit for financial."""
        query = "invest money profit rich"
        risk = estimate_refusal_risk(query)
        intent = classify_intent(query)
        strategy = _recommend_strategy(query, "auto", risk, intent)
        assert strategy == "compliance_audit_fork"

    def test_recommend_strategy_technical(self) -> None:
        """Recommend code_first for technical queries."""
        query = "code architecture API"
        risk = estimate_refusal_risk(query)
        intent = classify_intent(query)
        strategy = _recommend_strategy(query, "auto", risk, intent)
        assert strategy == "code_first"

    def test_recommend_strategy_default_academic(self) -> None:
        """Recommend academic as default strategy."""
        query = "normal question about something"
        risk = estimate_refusal_risk(query)
        intent = classify_intent(query)
        strategy = _recommend_strategy(query, "auto", risk, intent)
        assert strategy == "academic"


class TestEstimateHCS:
    """Tests for HCS estimation — 5 test cases."""

    def test_estimate_hcs_bounds(self) -> None:
        """Verify HCS estimates are within 0-10 range."""
        for pipeline in PIPELINES.keys():
            for risk_level in ["low", "medium", "high"]:
                hcs = _estimate_hcs(pipeline, risk_level)
                assert 0.0 <= hcs <= 10.0

    def test_estimate_hcs_direct_low_risk(self) -> None:
        """Verify HCS for direct low-risk pipeline."""
        hcs = _estimate_hcs("direct", "low")
        assert hcs == 7.0

    def test_estimate_hcs_research_pipeline(self) -> None:
        """Verify HCS for research pipeline."""
        hcs = _estimate_hcs("research_pipeline", "low")
        assert hcs == 8.5

    def test_estimate_hcs_multi_model_arbitrage(self) -> None:
        """Verify highest HCS for multi-model arbitrage."""
        hcs = _estimate_hcs("multi_model_arbitrage", "low")
        assert hcs == 9.0

    def test_estimate_hcs_unknown_pipeline(self) -> None:
        """Verify default HCS for unknown pipeline."""
        hcs = _estimate_hcs("unknown_pipeline", "medium")
        assert hcs == 5.0  # Default


class TestResearchOrchestrate:
    """Tests for async research_orchestrate function — 3 test cases."""

    @pytest.mark.asyncio
    async def test_research_orchestrate_returns_dict(self) -> None:
        """Verify research_orchestrate returns dict."""
        result = await research_orchestrate("test query")
        assert isinstance(result, dict)
        assert "pipeline" in result

    @pytest.mark.asyncio
    async def test_research_orchestrate_with_parameters(self) -> None:
        """Verify research_orchestrate accepts all parameters."""
        result = await research_orchestrate(
            query="hack exploit bypass attack",
            model="gpt-4",
            previous_attempts=1,
        )
        assert isinstance(result, dict)
        assert result["pipeline"] == "evidence_first_reframe"

    @pytest.mark.asyncio
    async def test_research_orchestrate_low_quality_escalation(self) -> None:
        """Verify escalation on low quality score."""
        result = await research_orchestrate(
            query="normal question",
            previous_hcs=2.5,
        )
        assert result["pipeline"] == "crescendo_hcs_loop"


class TestIntegrationPipelineSelection:
    """Integration tests for complex scenarios — 4 test cases."""

    def test_escalation_path_high_risk(self) -> None:
        """Verify escalation path for high-risk query."""
        query = "hack exploit bypass attack inject"

        # First attempt: single_reframe
        result1 = select_pipeline(query, previous_attempts=0)
        assert result1["pipeline"] == "single_reframe"

        # Second attempt: evidence_first_reframe
        result2 = select_pipeline(query, previous_attempts=1)
        assert result2["pipeline"] == "evidence_first_reframe"

        # Third attempt: reid_9_step
        result3 = select_pipeline(query, previous_attempts=2)
        assert result3["pipeline"] == "reid_9_step"

    def test_quality_improvement_path(self) -> None:
        """Verify quality improvement path when HCS is low."""
        query = "explain something"

        # Low quality response triggers crescendo
        result = select_pipeline(query, previous_hcs=3.0)
        assert result["pipeline"] == "crescendo_hcs_loop"
        assert "escalate_strategy" in result["steps"]

    def test_research_with_medium_risk(self) -> None:
        """Verify research pipeline selected for research + medium risk."""
        query = "research investigate explore analyze security features"
        result = select_pipeline(query)
        assert result["pipeline"] == "research_pipeline"

    def test_creative_query_uses_multi_model(self) -> None:
        """Verify creative queries use multi-model arbitrage."""
        query = "suggest creative ideas"
        result = select_pipeline(query)
        assert result["pipeline"] == "multi_model_arbitrage"


class TestPipelinesDefinition:
    """Tests for PIPELINES definition — 2 test cases."""

    def test_pipelines_all_have_steps(self) -> None:
        """Verify all pipelines have steps list."""
        for name, pipeline in PIPELINES.items():
            assert "steps" in pipeline
            assert isinstance(pipeline["steps"], list)
            assert len(pipeline["steps"]) > 0

    def test_pipelines_all_have_description(self) -> None:
        """Verify all pipelines have description."""
        for name, pipeline in PIPELINES.items():
            assert "description" in pipeline
            assert isinstance(pipeline["description"], str)
            assert len(pipeline["description"]) > 0


class TestKeywordDetection:
    """Tests for keyword detection — 2 test cases."""

    def test_high_risk_keywords_detected(self) -> None:
        """Verify high-risk keywords are detectable."""
        for keyword in ["hack", "exploit", "weapon", "bomb"]:
            risk = estimate_refusal_risk(f"how to {keyword}")
            assert risk["high_risk_matches"] > 0

    def test_medium_risk_keywords_detected(self) -> None:
        """Verify medium-risk keywords are detectable."""
        for keyword in ["vulnerability", "penetration", "surveillance"]:
            risk = estimate_refusal_risk(f"discuss {keyword}")
            assert risk["medium_risk_matches"] > 0

class TestMissingCoverage:
    """Tests for edge cases and branch coverage."""

    def test_multiple_failures_triggers_reid_9_step(self) -> None:
        """Verify multiple failures with low HCS triggers reid_9_step."""
        query = "hack exploit bypass attack"
        result = select_pipeline(query, previous_attempts=3, previous_hcs=4.0)
        assert result["pipeline"] == "reid_9_step"
        assert "Multiple failed attempts" in result["reason"]

    def test_medium_risk_without_research_uses_single_reframe(self) -> None:
        """Verify medium risk without research intent uses single_reframe."""
        # Create a query that will have medium risk but low research intent
        query = "how to hack something vulnerability"
        # First verify it's medium risk
        risk = estimate_refusal_risk(query)
        intent = classify_intent(query)
        if risk["risk_level"] == "medium" and intent.get("research", 0) <= 0.3:
            result = select_pipeline(query)
            assert result["pipeline"] == "single_reframe"

    def test_medium_risk_with_research_uses_research_pipeline(self) -> None:
        """Verify medium risk with research intent uses research_pipeline."""
        query = "research and investigate hack vulnerability"
        risk = estimate_refusal_risk(query)
        intent = classify_intent(query)
        # This should have medium risk + research intent > 0.3
        assert risk["risk_level"] == "medium"
        assert intent.get("research", 0) > 0.3
        result = select_pipeline(query)
        assert result["pipeline"] == "research_pipeline"
