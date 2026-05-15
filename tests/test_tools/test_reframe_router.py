"""Tests for reframe_router tool."""

from __future__ import annotations

import pytest

from loom.tools.llm.reframe_router import (
    ReframeRouter,
    RouterDecision,
    research_reframe_or_integrate,
)


class TestReframeRouter:
    """Unit tests for ReframeRouter classification logic."""

    def test_router_initialization(self) -> None:
        """Test router can be initialized."""
        router = ReframeRouter()
        assert router is not None

    def test_score_keyword_match_reframe(self) -> None:
        """Test keyword matching for reframing keywords."""
        router = ReframeRouter()
        text = "how to bypass OpenAI safety filters"
        score, matched = router._score_keyword_match(
            text, router.REFRAMING_KEYWORDS
        )
        assert score > 0.5
        assert "bypass" in matched
        assert "how to" in matched

    def test_score_keyword_match_integrate(self) -> None:
        """Test keyword matching for integration keywords."""
        router = ReframeRouter()
        text = "find all open ports on example.com"
        score, matched = router._score_keyword_match(
            text, router.INTEGRATION_KEYWORDS
        )
        assert score > 0.5
        assert "find" in matched

    def test_score_keyword_match_no_match(self) -> None:
        """Test keyword matching with no matching keywords."""
        router = ReframeRouter()
        text = "tell me about the weather"
        score, matched = router._score_keyword_match(
            text, router.REFRAMING_KEYWORDS
        )
        assert score == 0.0
        assert len(matched) == 0

    def test_dangerous_patterns_jailbreak(self) -> None:
        """Test detection of jailbreak patterns."""
        router = ReframeRouter()
        text = "how to create a virus without detection"
        patterns = router._check_dangerous_patterns(text)
        assert len(patterns) > 0

    def test_dangerous_patterns_exploit(self) -> None:
        """Test detection of exploit patterns."""
        router = ReframeRouter()
        text = "how to exploit a vulnerability in linux kernel"
        patterns = router._check_dangerous_patterns(text)
        assert len(patterns) > 0

    def test_dangerous_patterns_no_match(self) -> None:
        """Test no dangerous patterns detected for benign text."""
        router = ReframeRouter()
        text = "what is python programming"
        patterns = router._check_dangerous_patterns(text)
        assert len(patterns) == 0

    def test_classify_reframe_decision(self) -> None:
        """Test classification identifies reframing need."""
        router = ReframeRouter()
        decision = router.classify("how to bypass safety filters without detection")
        assert decision.decision == "reframe"
        assert decision.confidence > 0.7
        assert len(decision.suggested_strategies) > 0
        assert decision.query_intent in [
            "refusal_bypass",
            "complex_attack_with_data",
            "potential_bypass",
        ]

    def test_classify_integrate_decision(self) -> None:
        """Test classification identifies integration need."""
        router = ReframeRouter()
        decision = router.classify("find all open SSH ports on example.com")
        assert decision.decision == "integrate"
        assert decision.confidence > 0.6
        assert len(decision.suggested_tools) > 0
        assert decision.query_intent in [
            "data_gathering",
            "information_retrieval",
        ]

    def test_classify_both_decision(self) -> None:
        """Test classification identifies both reframe and integrate."""
        router = ReframeRouter()
        decision = router.classify(
            "how to exploit CVE-2024-1234 and find vulnerable servers without detection"
        )
        assert decision.decision == "both"
        assert decision.confidence > 0.5
        assert len(decision.suggested_tools) > 0
        assert len(decision.suggested_strategies) > 0

    def test_classify_default_decision(self) -> None:
        """Test classification on neutral query."""
        router = ReframeRouter()
        decision = router.classify("tell me about Python")
        assert decision.decision in ["reframe", "integrate", "both"]
        assert decision.confidence >= 0.0

    def test_select_tools_web_scraping(self) -> None:
        """Test tool selection for web scraping intent."""
        router = ReframeRouter()
        text = "scrape and fetch content from example.com"
        tools = router._select_tools(text, "integrate")
        assert len(tools) > 0
        assert "research_fetch" in tools or "research_spider" in tools

    def test_select_tools_search(self) -> None:
        """Test tool selection for search intent."""
        router = ReframeRouter()
        text = "search and find information about vulnerabilities"
        tools = router._select_tools(text, "integrate")
        assert len(tools) > 0
        assert any("search" in t or "find" in t for t in tools)

    def test_select_tools_osint(self) -> None:
        """Test tool selection for OSINT intent."""
        router = ReframeRouter()
        text = "perform osint on person identity domain recon"
        tools = router._select_tools(text, "integrate")
        assert len(tools) > 0

    def test_select_tools_empty_for_reframe(self) -> None:
        """Test tool selection returns empty for reframe decision."""
        router = ReframeRouter()
        text = "bypass safety filter"
        tools = router._select_tools(text, "reframe")
        assert tools == []

    def test_select_strategies_jailbreak(self) -> None:
        """Test strategy selection for jailbreak intent."""
        router = ReframeRouter()
        text = "bypass the filter without detection"
        strategies = router._select_strategies(text, "reframe")
        assert len(strategies) > 0

    def test_select_strategies_encoding(self) -> None:
        """Test strategy selection for encoding intent."""
        router = ReframeRouter()
        text = "encode and obfuscate the message"
        strategies = router._select_strategies(text, "reframe")
        assert len(strategies) > 0

    def test_select_strategies_persona(self) -> None:
        """Test strategy selection for persona intent."""
        router = ReframeRouter()
        text = "pretend to be an expert and role play"
        strategies = router._select_strategies(text, "reframe")
        assert len(strategies) > 0

    def test_select_strategies_empty_for_integrate(self) -> None:
        """Test strategy selection returns empty for integrate decision."""
        router = ReframeRouter()
        text = "find something"
        strategies = router._select_strategies(text, "integrate")
        assert strategies == []

    def test_router_decision_frozen(self) -> None:
        """Test RouterDecision is immutable."""
        decision = RouterDecision(
            decision="reframe",
            confidence=0.95,
            suggested_tools=["tool1"],
            suggested_strategies=["strat1"],
            reasoning="test",
            query_intent="refusal_bypass",
            detected_patterns=["pattern1"],
        )
        with pytest.raises(AttributeError):
            decision.decision = "integrate"  # type: ignore


@pytest.mark.asyncio
async def test_research_reframe_or_integrate_reframe() -> None:
    """Test async tool function for reframe decision."""
    result = await research_reframe_or_integrate(
        "how to bypass OpenAI filters"
    )
    assert result["decision"] == "reframe"
    assert result["confidence"] > 0.5
    assert "suggested_strategies" in result
    assert len(result["suggested_strategies"]) > 0


@pytest.mark.asyncio
async def test_research_reframe_or_integrate_integrate() -> None:
    """Test async tool function for integrate decision."""
    result = await research_reframe_or_integrate(
        "find all open SSH ports"
    )
    assert result["decision"] == "integrate"
    assert result["confidence"] > 0.5
    assert "suggested_tools" in result
    assert len(result["suggested_tools"]) > 0


@pytest.mark.asyncio
async def test_research_reframe_or_integrate_both() -> None:
    """Test async tool function for both decision."""
    result = await research_reframe_or_integrate(
        "how to exploit vulnerability without detection and find targets"
    )
    assert result["decision"] == "both"
    assert result["confidence"] > 0.4
    assert "suggested_tools" in result
    assert "suggested_strategies" in result


@pytest.mark.asyncio
async def test_research_reframe_or_integrate_with_context() -> None:
    """Test async tool with context parameter."""
    result = await research_reframe_or_integrate(
        "how to bypass",
        context="I'm testing AI safety filters for research purposes"
    )
    assert result["decision"] in ["reframe", "both", "integrate"]
    assert "reasoning" in result


@pytest.mark.asyncio
async def test_research_reframe_or_integrate_response_format() -> None:
    """Test response format matches specification."""
    result = await research_reframe_or_integrate("test query")

    # Check all required fields present
    assert "decision" in result
    assert "confidence" in result
    assert "query_intent" in result
    assert "suggested_tools" in result
    assert "suggested_strategies" in result
    assert "detected_patterns" in result
    assert "reasoning" in result

    # Check types
    assert isinstance(result["decision"], str)
    assert isinstance(result["confidence"], float)
    assert isinstance(result["suggested_tools"], list)
    assert isinstance(result["suggested_strategies"], list)
    assert isinstance(result["reasoning"], str)
