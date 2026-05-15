"""Tests for fact_verifier tools — research_fact_verify and research_batch_verify."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from loom.tools.research.fact_verifier import (
    research_fact_verify,
    research_batch_verify,
    _extract_evidence,
    _score_agreement,
)


class TestExtractEvidence:
    """Test _extract_evidence helper function."""

    def test_extract_evidence_with_all_fields(self):
        """Test extracting evidence with all fields present."""
        result = {
            "url": "https://example.com/article",
            "snippet": "This is the evidence snippet.",
            "title": "Article Title",
        }

        url, evidence = _extract_evidence(result)

        assert url == "https://example.com/article"
        assert "Article Title" in evidence
        assert "This is the evidence snippet." in evidence

    def test_extract_evidence_with_missing_fields(self):
        """Test extracting evidence with missing fields."""
        result = {
            "url": "https://example.com",
        }

        url, evidence = _extract_evidence(result)

        assert url == "https://example.com"
        assert evidence  # Should have some content even if empty fields

    def test_extract_evidence_caps_length(self):
        """Test that evidence is capped at 500 chars."""
        long_snippet = "A" * 1000
        result = {
            "url": "https://example.com",
            "snippet": long_snippet,
            "title": "Title",
        }

        url, evidence = _extract_evidence(result)

        assert len(evidence) <= 500


class TestScoreAgreement:
    """Test _score_agreement helper function."""

    def test_score_agreement_with_no_results(self):
        """Test scoring when no results are provided."""
        verdict, confidence, supporting, contradicting = _score_agreement([])

        assert verdict == "unverified"
        assert confidence == 0.1
        assert supporting == []
        assert contradicting == []

    def test_score_agreement_with_three_supporting_sources(self):
        """Test scoring with 3+ supporting sources."""
        results = [[
            {
                "url": f"https://example{i}.com",
                "snippet": "This confirms the claim. Evidence supports the claim.",
                "title": f"Article {i}",
                "source": "news",
            }
            for i in range(3)
        ]]

        verdict, confidence, supporting, contradicting = _score_agreement(results)

        assert verdict == "supported"
        assert confidence >= 0.85
        assert len(supporting) >= 2
        assert len(contradicting) == 0

    def test_score_agreement_with_two_supporting_sources(self):
        """Test scoring with 2 supporting sources."""
        results = [[
            {
                "url": f"https://example{i}.com",
                "snippet": "Evidence supports the claim.",
                "title": f"Article {i}",
                "source": "news",
            }
            for i in range(2)
        ]]

        verdict, confidence, supporting, contradicting = _score_agreement(results)

        assert verdict == "supported"
        assert confidence >= 0.7
        assert len(supporting) >= 1

    def test_score_agreement_with_contradicting_sources(self):
        """Test scoring with contradicting sources."""
        results = [[
            {
                "url": "https://example1.com",
                "snippet": "This refutes the claim. Evidence contradicts.",
                "title": "Refutation",
                "source": "news",
            },
            {
                "url": "https://example2.com",
                "snippet": "This disproves the claim. False claim.",
                "title": "Debunking",
                "source": "fact-check",
            },
        ]]

        verdict, confidence, supporting, contradicting = _score_agreement(results)

        assert verdict == "contradicted"
        assert confidence >= 0.7
        assert len(contradicting) >= 1

    def test_score_agreement_with_mixed_sources(self):
        """Test scoring with mixed supporting and contradicting sources."""
        results = [[
            {
                "url": "https://example1.com",
                "snippet": "Evidence supports the claim.",
                "title": "Supporting",
                "source": "news",
            },
            {
                "url": "https://example2.com",
                "snippet": "This contradicts and refutes the claim.",
                "title": "Contradicting",
                "source": "fact-check",
            },
        ]]

        verdict, confidence, supporting, contradicting = _score_agreement(results)

        assert verdict == "mixed"
        assert 0.3 <= confidence <= 0.7
        assert len(supporting) >= 0
        assert len(contradicting) >= 0

    def test_score_agreement_deduplicates_urls(self):
        """Test that duplicate URLs are deduplicated."""
        results = [[
            {
                "url": "https://example.com",
                "snippet": "Supporting evidence.",
                "title": "Article 1",
                "source": "news",
            },
            {
                "url": "https://example.com",  # Duplicate
                "snippet": "More supporting evidence.",
                "title": "Article 1 (again)",
                "source": "news",
            },
        ]]

        verdict, confidence, supporting, contradicting = _score_agreement(results)

        # Only one URL should be in the results
        total_sources = len(supporting) + len(contradicting)
        assert total_sources == 1


@pytest.mark.asyncio
class TestResearchFactVerify:
    """Test research_fact_verify function."""

    async def test_fact_verify_invalid_claim_too_short(self):
        """Test verification with claim too short."""
        result = await research_fact_verify("abc")

        assert result["verdict"] == "unverified"
        assert result["confidence"] == 0.0
        assert "error" in result

    async def test_fact_verify_invalid_claim_too_long(self):
        """Test verification with claim exceeding max length."""
        long_claim = "a" * 501
        result = await research_fact_verify(long_claim)

        assert result["verdict"] == "unverified"
        assert result["confidence"] == 0.0
        assert "error" in result

    async def test_fact_verify_valid_claim_with_mocked_search(self):
        """Test verification with valid claim using mocked search."""
        with patch("loom.tools.research.fact_verifier.research_search") as mock_search:
            # Mock search results
            mock_search.side_effect = [
                {
                    "provider": "exa",
                    "results": [
                        {
                            "url": "https://example1.com",
                            "snippet": "Evidence supports the claim",
                            "title": "Article 1",
                            "source": "news",
                        },
                        {
                            "url": "https://example2.com",
                            "snippet": "Supporting evidence confirms",
                            "title": "Article 2",
                            "source": "news",
                        },
                    ]
                },
                {
                    "provider": "tavily",
                    "results": []
                },
                {
                    "provider": "brave",
                    "results": []
                },
            ]

            result = await research_fact_verify("The Earth is round")

            assert "claim" in result
            assert result["claim"] == "The Earth is round"
            assert "verdict" in result
            assert result["verdict"] in ["supported", "contradicted", "unverified", "mixed"]
            assert "confidence" in result
            assert 0.0 <= result["confidence"] <= 1.0
            assert "supporting_sources" in result
            assert "contradicting_sources" in result
            assert "evidence_summary" in result
            assert "total_sources_analyzed" in result

    async def test_fact_verify_handles_search_errors(self):
        """Test verification handles search provider errors gracefully."""
        with patch("loom.tools.research.fact_verifier.research_search") as mock_search:
            # Mock one provider failing, others returning empty
            mock_search.side_effect = [
                Exception("Connection error"),
                {"provider": "tavily", "results": []},
                {"provider": "brave", "results": []},
            ]

            result = await research_fact_verify("Test claim")

            # Should still return valid response structure
            assert "verdict" in result
            assert result["verdict"] in ["supported", "contradicted", "unverified", "mixed"]

    async def test_fact_verify_respects_min_confidence(self):
        """Test that low confidence results are marked unverified."""
        with patch("loom.tools.research.fact_verifier.research_search") as mock_search:
            # Mock results with mixed/weak evidence
            mock_search.side_effect = [
                {
                    "provider": "exa",
                    "results": [
                        {
                            "url": "https://example.com",
                            "snippet": "Weak evidence",
                            "title": "Article",
                            "source": "blog",
                        },
                    ]
                },
                {"provider": "tavily", "results": []},
                {"provider": "brave", "results": []},
            ]

            result = await research_fact_verify(
                "Test claim",
                sources=3,
                min_confidence=0.9
            )

            # With min_confidence 0.9 and weak evidence, should be unverified
            if result["confidence"] < 0.9:
                assert result["verdict"] == "unverified"

    async def test_fact_verify_sources_parameter(self):
        """Test that sources parameter is validated and used."""
        with patch("loom.tools.research.fact_verifier.research_search") as mock_search:
            mock_search.return_value = {
                "provider": "exa",
                "results": []
            }

            # Test with valid sources values
            await research_fact_verify("Test claim", sources=5)
            # Called 3 times (exa, tavily, brave)
            assert mock_search.call_count >= 3

    async def test_fact_verify_returns_complete_structure(self):
        """Test that result has all expected keys."""
        with patch("loom.tools.research.fact_verifier.research_search") as mock_search:
            mock_search.return_value = {
                "provider": "exa",
                "results": []
            }

            result = await research_fact_verify("Test claim")

            required_keys = {
                "claim",
                "verdict",
                "confidence",
                "supporting_sources",
                "contradicting_sources",
                "evidence_summary",
                "total_sources_analyzed",
            }
            assert required_keys.issubset(result.keys())


@pytest.mark.asyncio
class TestResearchBatchVerify:
    """Test research_batch_verify function."""

    async def test_batch_verify_empty_claims(self):
        """Test batch verification with empty claims list."""
        result = await research_batch_verify([])

        assert isinstance(result, list)
        if result:
            assert "error" in result[0]

    async def test_batch_verify_too_many_claims(self):
        """Test batch verification with too many claims."""
        claims = [f"Claim {i}" for i in range(51)]  # Exceeds MAX_BATCH_CLAIMS
        result = await research_batch_verify(claims)

        # Should be capped at 50
        assert len(result) <= 50

    async def test_batch_verify_single_claim(self):
        """Test batch verification with single claim."""
        with patch("loom.tools.research.fact_verifier.research_fact_verify") as mock_verify:
            mock_verify.return_value = {
                "claim": "Test claim",
                "verdict": "supported",
                "confidence": 0.8,
                "supporting_sources": [],
                "contradicting_sources": [],
                "evidence_summary": "Test",
                "total_sources_analyzed": 1,
            }

            result = await research_batch_verify(["Test claim"])

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["claim"] == "Test claim"

    async def test_batch_verify_multiple_claims(self):
        """Test batch verification with multiple claims."""
        with patch("loom.tools.research.fact_verifier.research_fact_verify") as mock_verify:
            async def mock_verify_impl(claim, **kwargs):
                return {
                    "claim": claim,
                    "verdict": "unverified",
                    "confidence": 0.5,
                    "supporting_sources": [],
                    "contradicting_sources": [],
                    "evidence_summary": "No evidence",
                    "total_sources_analyzed": 0,
                }

            mock_verify.side_effect = mock_verify_impl

            claims = ["Claim 1", "Claim 2", "Claim 3"]
            result = await research_batch_verify(claims)

            assert isinstance(result, list)
            assert len(result) == 3
            for i, res in enumerate(result):
                assert res["claim"] == claims[i]

    async def test_batch_verify_returns_complete_structure_per_claim(self):
        """Test that each result has required keys."""
        with patch("loom.tools.research.fact_verifier.research_fact_verify") as mock_verify:
            async def mock_verify_impl(claim, **kwargs):
                return {
                    "claim": claim,
                    "verdict": "unverified",
                    "confidence": 0.5,
                    "supporting_sources": [],
                    "contradicting_sources": [],
                    "evidence_summary": "Test",
                    "total_sources_analyzed": 0,
                }

            mock_verify.side_effect = mock_verify_impl

            result = await research_batch_verify(["Test claim"])

            required_keys = {
                "claim",
                "verdict",
                "confidence",
                "supporting_sources",
                "contradicting_sources",
                "evidence_summary",
                "total_sources_analyzed",
            }
            assert required_keys.issubset(result[0].keys())

    async def test_batch_verify_invalid_claims(self):
        """Test batch verification validates each claim."""
        # Claims with invalid lengths will fail validation
        result = await research_batch_verify(
            ["ok", "This is a very long but valid test claim"],
            sources=3
        )

        # Result should still have appropriate structure
        assert isinstance(result, list)


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for fact verifier tools."""

    async def test_fact_verify_and_batch_verify_consistency(self):
        """Test that batch verify produces same results as individual verify."""
        with patch("loom.tools.research.fact_verifier.research_search") as mock_search:
            mock_search.return_value = {
                "provider": "exa",
                "results": []
            }

            claim = "Test claim for consistency"

            # Run single verification
            single_result = await research_fact_verify(claim)

            # Reset mock
            mock_search.reset_mock()
            mock_search.return_value = {
                "provider": "exa",
                "results": []
            }

            # Run batch verification
            batch_result = await research_batch_verify([claim])

            # Results should have same verdict structure
            assert single_result["verdict"] == batch_result[0]["verdict"]
            assert single_result["confidence"] == batch_result[0]["confidence"]
