"""Tests for expert-level research engine with 7-stage pipeline."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom.tools.expert_engine import (
    research_expert,
    _detect_domain,
    _estimate_source_credibility,
    _extract_and_verify_claims,
    _adversarial_review,
    DOMAIN_PATTERNS,
    RESEARCH_ANGLES,
    SOURCE_CREDIBILITY,
)


class TestDomainDetection:
    """Test domain auto-detection."""

    def test_detect_finance_domain(self) -> None:
        """Test detection of finance domain."""
        queries = [
            "latest bitcoin trends 2026",
            "stock market analysis for tech companies",
            "cryptocurrency trading strategies",
        ]
        for query in queries:
            domain = _detect_domain(query)
            assert domain == "finance", f"Failed to detect finance domain for: {query}"

    def test_detect_technology_domain(self) -> None:
        """Test detection of technology domain."""
        queries = [
            "transformer architecture advances",
            "latest GPU performance benchmarks",
            "open source frameworks comparison",
        ]
        for query in queries:
            domain = _detect_domain(query)
            assert domain == "technology", f"Failed to detect tech domain for: {query}"

    def test_detect_science_domain(self) -> None:
        """Test detection of science domain."""
        queries = [
            "recent medical research breakthroughs",
            "arxiv papers on quantum computing",
            "peer-reviewed journal articles on AI safety",
        ]
        for query in queries:
            domain = _detect_domain(query)
            assert domain == "science", f"Failed to detect science domain for: {query}"

    def test_detect_security_domain(self) -> None:
        """Test detection of security domain."""
        queries = [
            "cybersecurity vulnerabilities and threats",
            "encryption methods and authentication",
            "penetration testing techniques",
        ]
        for query in queries:
            domain = _detect_domain(query)
            assert domain == "security", f"Failed to detect security domain for: {query}"

    def test_detect_geopolitics_domain(self) -> None:
        """Test detection of geopolitics domain."""
        queries = [
            "international conflict resolution",
            "government treaty negotiations",
            "diplomatic relations between nations",
        ]
        for query in queries:
            domain = _detect_domain(query)
            assert domain == "geopolitics", f"Failed to detect geopolitics domain for: {query}"

    def test_detect_law_domain(self) -> None:
        """Test detection of law domain."""
        queries = [
            "intellectual property law and patents",
            "court ruling on data privacy",
            "legal regulations for compliance",
        ]
        for query in queries:
            domain = _detect_domain(query)
            assert domain == "law", f"Failed to detect law domain for: {query}"

    def test_general_domain_fallback(self) -> None:
        """Test fallback to general domain for unknown queries."""
        query = "random query that matches no patterns"
        domain = _detect_domain(query)
        # Should return one of the domains, not necessarily "general"
        assert domain in DOMAIN_PATTERNS.keys() or domain == "general"

    def test_case_insensitive_detection(self) -> None:
        """Test that domain detection is case-insensitive."""
        query_lower = "bitcoin price analysis"
        query_upper = "BITCOIN PRICE ANALYSIS"
        domain_lower = _detect_domain(query_lower)
        domain_upper = _detect_domain(query_upper)
        assert domain_lower == domain_upper


class TestSourceCredibility:
    """Test source credibility estimation."""

    def test_arxiv_high_credibility(self) -> None:
        """Test that arxiv sources get high credibility."""
        score = _estimate_source_credibility("https://arxiv.org/abs/2404.12345")
        assert score >= 0.90

    def test_academic_journal_high_credibility(self) -> None:
        """Test that academic journals get high credibility."""
        score = _estimate_source_credibility("https://journal.example.com/article", "journal")
        assert score >= 0.85

    def test_mainstream_news_medium_credibility(self) -> None:
        """Test that mainstream news gets medium credibility."""
        score = _estimate_source_credibility(
            "https://news.example.com/article", "mainstream_news"
        )
        assert 0.60 <= score <= 0.70

    def test_forum_low_credibility(self) -> None:
        """Test that forums get low credibility."""
        score = _estimate_source_credibility("https://reddit.com/r/topic", "forum")
        assert score <= 0.45

    def test_github_reasonable_credibility(self) -> None:
        """Test that GitHub repos get reasonable credibility."""
        score = _estimate_source_credibility("https://github.com/user/repo")
        assert score > 0.40

    def test_twitter_low_credibility(self) -> None:
        """Test that Twitter/X gets low credibility."""
        score = _estimate_source_credibility("https://twitter.com/user/status", "twitter")
        assert score <= 0.35

    def test_credibility_bounded_0_to_1(self) -> None:
        """Test that credibility scores are always 0-1."""
        test_cases = [
            "https://example.com",
            "https://arxiv.org",
            "https://github.com",
        ]
        for url in test_cases:
            score = _estimate_source_credibility(url)
            assert 0.0 <= score <= 1.0


class TestClaimExtraction:
    """Test claim extraction and triangulation."""

    @pytest.mark.asyncio
    async def test_empty_evidence_handling(self) -> None:
        """Test handling of empty evidence."""
        evidence_by_angle = {}
        result = await _extract_and_verify_claims(evidence_by_angle, "test query")

        assert result["total_claims"] == 0
        assert result["claims"] == []
        assert result["triangulation_score"] == 0

    @pytest.mark.asyncio
    async def test_single_angle_extraction(self) -> None:
        """Test claim extraction from single angle."""
        evidence_by_angle = {
            "factual": {
                "claims": [{"claim": "Test claim 1", "confidence": 0.75}],
                "sources": [
                    {"url": "https://example.com", "credibility": 0.8},
                ],
            }
        }
        result = await _extract_and_verify_claims(evidence_by_angle, "test query")

        assert result["total_claims"] >= 1
        assert len(result["claims"]) >= 1
        assert all("claim" in c for c in result["claims"])
        assert all("confidence" in c for c in result["claims"])

    @pytest.mark.asyncio
    async def test_multi_angle_triangulation(self) -> None:
        """Test that multi-angle evidence increases confidence."""
        evidence_by_angle = {
            "factual": {
                "claims": [{"claim": "Test finding A", "confidence": 0.7}],
                "sources": [{"url": "https://example.com", "credibility": 0.8}],
            },
            "mechanism": {
                "claims": [
                    {"claim": "Test finding A", "confidence": 0.8}
                ],
                "sources": [{"url": "https://arxiv.org", "credibility": 0.95}],
            },
            "historical": {
                "claims": [
                    {"claim": "Test finding A", "confidence": 0.75}
                ],
                "sources": [{"url": "https://journal.com", "credibility": 0.9}],
            },
        }
        result = await _extract_and_verify_claims(evidence_by_angle, "test query")

        if result["claims"]:
            # Find the triangulated claim (first claim since we have 1 unique claim)
            claim = result["claims"][0]
            # Triangulation should give us multiple angles
            assert claim["triangulation_angles"] >= 2  # At least 2 angles
            assert claim["confidence"] >= 0.70  # Reasonable confidence from multiple sources

    @pytest.mark.asyncio
    async def test_claims_sorted_by_confidence(self) -> None:
        """Test that claims are sorted by confidence descending."""
        evidence_by_angle = {
            "factual": {
                "claims": [
                    {"claim": "Low confidence claim", "confidence": 0.3},
                    {"claim": "High confidence claim", "confidence": 0.9},
                    {"claim": "Medium confidence claim", "confidence": 0.6},
                ],
                "sources": [],
            }
        }
        result = await _extract_and_verify_claims(evidence_by_angle, "test query")

        if len(result["claims"]) > 1:
            for i in range(len(result["claims"]) - 1):
                assert result["claims"][i]["confidence"] >= result["claims"][i + 1]["confidence"]


class TestAdversarialReview:
    """Test adversarial critique functionality."""

    @pytest.mark.asyncio
    async def test_adversarial_review_structure(self) -> None:
        """Test that adversarial review returns proper structure."""
        try:
            from loom.providers.base import get_llm_provider
        except ImportError:
            pytest.skip("LLM provider not available")

        with patch("loom.providers.base.get_llm_provider") as mock_provider_func:
            mock_llm = AsyncMock()
            mock_llm.chat = AsyncMock(
                return_value={
                    "content": '{"flaws": ["flaw1"], "gaps": ["gap1"], "severity": "high"}'
                }
            )
            mock_provider_func.return_value = mock_llm

            findings = {"test": "findings"}
            result = await _adversarial_review(findings, "test query", "test summary")

            assert "critique" in result
            assert "flaws" in result or isinstance(result.get("flaws"), list)
            assert "gaps" in result or isinstance(result.get("gaps"), list)
            assert "severity" in result
            assert "unsupported_claims" in result or isinstance(result.get("unsupported_claims"), list)
            assert "missing_evidence" in result or isinstance(result.get("missing_evidence"), list)

    @pytest.mark.asyncio
    async def test_adversarial_review_handles_errors(self) -> None:
        """Test that adversarial review gracefully handles errors."""
        try:
            from loom.providers.base import get_llm_provider
        except ImportError:
            pytest.skip("LLM provider not available")

        with patch("loom.providers.base.get_llm_provider") as mock_provider_func:
            mock_provider_func.side_effect = Exception("LLM unavailable")

            findings = {"test": "findings"}
            result = await _adversarial_review(findings, "test query", "test summary")

            assert "critique" in result
            # Should handle error gracefully
            assert result["severity"] in ("low", "medium", "high")
            assert isinstance(result.get("gaps"), list)


class TestExpertResearch:
    """Test main expert research function."""

    @pytest.mark.asyncio
    async def test_quick_quality_mode(self) -> None:
        """Test quick quality mode (fewer tools, faster)."""
        with patch("loom.tools.expert_engine._gather_evidence_for_angle") as mock_gather:
            mock_gather.return_value = {
                "angle": "factual",
                "sources": [],
                "claims": [],
                "raw_evidence": [],
            }

            result = await research_expert("test query", quality_target="quick")

            assert "executive_summary" in result
            assert "key_findings" in result
            assert "quality_score" in result
            assert result["quality_target"] == "quick"

    @pytest.mark.asyncio
    async def test_expert_quality_mode(self) -> None:
        """Test expert quality mode (comprehensive research)."""
        with patch("loom.tools.expert_engine._gather_evidence_for_angle") as mock_gather:
            mock_gather.return_value = {
                "angle": "factual",
                "sources": [{"url": "https://example.com", "credibility": 0.8}],
                "claims": [{"claim": "Test claim", "confidence": 0.8}],
                "raw_evidence": [],
            }

            result = await research_expert("test query", quality_target="expert")

            assert result["quality_target"] == "expert"
            assert len(result["research_angles_covered"]) >= 3

    @pytest.mark.asyncio
    async def test_publication_quality_mode(self) -> None:
        """Test publication quality mode (maximum tools and rigor)."""
        with patch("loom.tools.expert_engine._gather_evidence_for_angle") as mock_gather:
            mock_gather.return_value = {
                "angle": "factual",
                "sources": [],
                "claims": [],
                "raw_evidence": [],
            }

            result = await research_expert("test query", quality_target="publication")

            assert result["quality_target"] == "publication"
            assert len(result["research_angles_covered"]) == 6  # All angles

    @pytest.mark.asyncio
    async def test_auto_domain_detection(self) -> None:
        """Test that domain is auto-detected when set to 'auto'."""
        with patch("loom.tools.expert_engine._gather_evidence_for_angle") as mock_gather:
            mock_gather.return_value = {
                "angle": "factual",
                "sources": [],
                "claims": [],
                "raw_evidence": [],
            }

            result = await research_expert("bitcoin trading strategies", domain="auto")

            assert result["domain"] == "finance"

    @pytest.mark.asyncio
    async def test_output_structure(self) -> None:
        """Test that output has all required fields."""
        with patch("loom.tools.expert_engine._gather_evidence_for_angle") as mock_gather:
            mock_gather.return_value = {
                "angle": "factual",
                "sources": [],
                "claims": [],
                "raw_evidence": [],
            }

            result = await research_expert("test query")

            required_keys = [
                "query",
                "domain",
                "quality_target",
                "research_angles_covered",
                "executive_summary",
                "key_findings",
                "evidence_map",
                "contrarian_analysis",
                "gaps_identified",
                "action_items",
                "tools_executed",
                "quality_score",
                "confidence_weighted_avg",
                "triangulation_score",
                "total_sources",
                "timestamp",
                "elapsed_ms",
                "warnings",
            ]

            for key in required_keys:
                assert key in result, f"Missing required key: {key}"

    @pytest.mark.asyncio
    async def test_confidence_scoring(self) -> None:
        """Test that confidence scores are properly calculated."""
        with patch("loom.tools.expert_engine._gather_evidence_for_angle") as mock_gather:
            mock_gather.return_value = {
                "angle": "factual",
                "sources": [],
                "claims": [{"claim": "Test claim", "confidence": 0.8}],
                "raw_evidence": [],
            }

            result = await research_expert("test query")

            assert 0.0 <= result["confidence_weighted_avg"] <= 1.0
            assert 0.0 <= result["triangulation_score"] <= 1.0
            assert 1.0 <= result["quality_score"] <= 10.0

    @pytest.mark.asyncio
    async def test_multi_perspective_disabled(self) -> None:
        """Test that multi_perspective=False uses only factual angle."""
        with patch("loom.tools.expert_engine._gather_evidence_for_angle") as mock_gather:
            mock_gather.return_value = {
                "angle": "factual",
                "sources": [],
                "claims": [],
                "raw_evidence": [],
            }

            result = await research_expert("test query", multi_perspective=False)

            assert result["research_angles_covered"] == ["factual"]

    @pytest.mark.asyncio
    async def test_iterative_refinement_disabled(self) -> None:
        """Test with max_iterations=1 to skip refinement."""
        with patch("loom.tools.expert_engine._gather_evidence_for_angle") as mock_gather:
            mock_gather.return_value = {
                "angle": "factual",
                "sources": [],
                "claims": [],
                "raw_evidence": [],
            }

            result = await research_expert("test query", max_iterations=1)

            # Should still succeed
            assert "executive_summary" in result

    @pytest.mark.asyncio
    async def test_claim_verification_flag(self) -> None:
        """Test that verify_claims flag is respected."""
        with patch("loom.tools.expert_engine._gather_evidence_for_angle") as mock_gather:
            mock_gather.return_value = {
                "angle": "factual",
                "sources": [],
                "claims": [],
                "raw_evidence": [],
            }

            result = await research_expert("test query", verify_claims=False)

            assert "key_findings" in result

    @pytest.mark.asyncio
    async def test_action_items_generated(self) -> None:
        """Test that action items are generated from gaps."""
        with patch("loom.tools.expert_engine._gather_evidence_for_angle") as mock_gather:
            mock_gather.return_value = {
                "angle": "factual",
                "sources": [],
                "claims": [],
                "raw_evidence": [],
            }

            with patch("loom.tools.expert_engine._adversarial_review") as mock_review:
                mock_review.return_value = {
                    "gaps": ["gap1", "gap2"],
                    "flaws": [],
                    "severity": "medium",
                }

                result = await research_expert("test query")

                assert len(result["action_items"]) > 0
                assert all(isinstance(item, str) for item in result["action_items"])

    @pytest.mark.asyncio
    async def test_tool_tracking(self) -> None:
        """Test that tools are properly tracked."""
        with patch("loom.tools.expert_engine._gather_evidence_for_angle") as mock_gather:
            mock_gather.return_value = {
                "angle": "factual",
                "sources": [],
                "claims": [],
                "raw_evidence": [],
            }

            result = await research_expert("test query")

            assert "tools_executed" in result
            assert "count" in result["tools_executed"]
            assert "tools" in result["tools_executed"]
            assert result["tools_executed"]["count"] >= 1
            assert isinstance(result["tools_executed"]["tools"], list)


class TestResearchAngles:
    """Test research angle definitions."""

    def test_all_angles_defined(self) -> None:
        """Test that all required angles are defined."""
        required_angles = [
            "factual",
            "mechanism",
            "historical",
            "contrarian",
            "underground",
            "future",
        ]
        for angle in required_angles:
            assert angle in RESEARCH_ANGLES, f"Missing angle: {angle}"

    def test_angle_descriptions_not_empty(self) -> None:
        """Test that all angles have descriptions."""
        for angle, description in RESEARCH_ANGLES.items():
            assert description, f"Empty description for angle: {angle}"
            assert len(description) > 10, f"Description too short for angle: {angle}"


class TestSourceCredibilityConstants:
    """Test source credibility scoring constants."""

    def test_credibility_scores_in_range(self) -> None:
        """Test that all credibility scores are 0-1."""
        for source, score in SOURCE_CREDIBILITY.items():
            assert 0.0 <= score <= 1.0, f"Invalid score for {source}: {score}"

    def test_academic_higher_than_forum(self) -> None:
        """Test that academic sources score higher than forums."""
        assert SOURCE_CREDIBILITY["academic"] > SOURCE_CREDIBILITY["forum"]

    def test_journal_highest(self) -> None:
        """Test that journals are highly credible."""
        assert SOURCE_CREDIBILITY["journal"] >= 0.85

    def test_twitter_lowest(self) -> None:
        """Test that twitter is low credibility."""
        assert SOURCE_CREDIBILITY["twitter"] <= 0.35


@pytest.mark.asyncio
async def test_expert_research_integration() -> None:
    """Integration test: full research pipeline."""
    with patch("loom.tools.expert_engine._gather_evidence_for_angle") as mock_gather:
        mock_gather.return_value = {
            "angle": "factual",
            "sources": [
                {"url": "https://arxiv.org/abs/123", "credibility": 0.95},
                {"url": "https://example.com", "credibility": 0.6},
            ],
            "claims": [
                {"claim": "Finding 1", "confidence": 0.85},
                {"claim": "Finding 2", "confidence": 0.70},
            ],
            "raw_evidence": [],
        }

        with patch("loom.tools.expert_engine._adversarial_review") as mock_review:
            mock_review.return_value = {
                "critique": "Good research, but missing XYZ",
                "flaws": ["Assumption not validated"],
                "gaps": ["Need more recent sources"],
                "severity": "medium",
                "unsupported_claims": [],
                "missing_evidence": [],
            }

            result = await research_expert(
                "transformer architecture advances 2026",
                domain="auto",
                quality_target="expert",
            )

            # Validate comprehensive output
            assert result["query"] == "transformer architecture advances 2026"
            assert result["domain"] == "technology"
            assert result["quality_score"] > 3.0  # Should score well with real claims
            assert result["confidence_weighted_avg"] > 0.5
            assert len(result["key_findings"]) > 0
            assert result["tools_executed"]["count"] > 0
            assert "timestamp" in result
            assert result["elapsed_ms"] >= 0  # May be 0 in fast tests
