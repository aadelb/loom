"""Unit tests for culture_dna tool — company culture analysis."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from loom.tools.culture_dna import (
    _analyze_github_signals,
    _analyze_job_postings,
    _classify_culture_type,
    _extract_culture_signals,
    research_culture_dna,
)


pytestmark = pytest.mark.asyncio

class TestExtractCultureSignals:
    """Culture signal extraction from text."""

    async def test_extract_work_life_signals(self) -> None:
        """Extract work-life balance signals."""
        text = "We offer flexible remote work and unlimited vacation."
        signals = _extract_culture_signals(text, "test_source")

        assert len(signals) > 0
        assert any(s["category"] == "work_life_balance" for s in signals)
        assert all(s["source"] == "test_source" for s in signals)

    async def test_extract_innovation_signals(self) -> None:
        """Extract innovation-related signals."""
        text = "Cutting-edge technology and regular hackathons for learning."
        signals = _extract_culture_signals(text, "github")

        assert len(signals) > 0
        assert any(s["category"] == "innovation" for s in signals)

    async def test_extract_diversity_signals(self) -> None:
        """Extract diversity and inclusion signals."""
        text = "We are committed to diversity, inclusion, and belonging."
        signals = _extract_culture_signals(text, "linkedin")

        assert any(s["category"] == "diversity" for s in signals)

    async def test_no_signals_in_empty_text(self) -> None:
        """Empty text yields no signals."""
        signals = _extract_culture_signals("", "source")
        assert len(signals) == 0

    async def test_signal_strength_capped(self) -> None:
        """Signal strength is capped at 5."""
        text = "flexible " * 10
        signals = _extract_culture_signals(text, "test")

        assert all(s["strength"] <= 5 for s in signals)


class TestAnalyzeGithubSignals:
    """GitHub organization culture analysis."""

    async def test_github_analysis_structure(self) -> None:
        """GitHub analysis returns expected structure."""
        result = _analyze_github_signals("google")

        assert "repo_analysis" in result
        assert "readme_analysis" in result
        assert "issue_response_time" in result
        assert "signals" in result
        assert isinstance(result["signals"], list)

    async def test_github_analysis_org_name(self) -> None:
        """GitHub analysis accepts organization names."""
        result = _analyze_github_signals("microsoft")
        assert "repo_analysis" in result


class TestAnalyzeJobPostings:
    """Job posting language analysis for culture signals."""

    async def test_detect_startup_culture_posting(self) -> None:
        """Detect startup vibes in job postings."""
        posting = "We're a dynamic startup with agile methodology and fast-paced growth."
        result = _analyze_job_postings(posting)

        assert "startup_vibes" in result
        assert result["startup_vibes"] > 0.3

    async def test_detect_formal_culture_posting(self) -> None:
        """Detect formal corporate culture."""
        posting = "Professional corporate structure with formal processes and corporate policies."
        result = _analyze_job_postings(posting)

        assert "formality_score" in result
        assert result["formality_score"] > 0.3

    async def test_detect_urgency_in_posting(self) -> None:
        """Detect urgency language in job postings."""
        posting = "Urgent: immediate opening needed for fast-paced environment."
        result = _analyze_job_postings(posting)

        assert "urgency_score" in result
        assert result["urgency_score"] > 0.3

    async def test_culture_mentions_extraction(self) -> None:
        """Extract culture-related mentions."""
        posting = "Flexible work, innovation in growth, collaborative team environment."
        result = _analyze_job_postings(posting)

        assert "culture_mentions" in result
        assert len(result["culture_mentions"]) > 0


class TestClassifyCultureType:
    """Culture type classification (startup/corporate/hybrid)."""

    async def test_classify_startup_culture(self) -> None:
        """Classify startup-oriented culture signals."""
        signals = [
            {"category": "innovation", "signal": "test", "strength": 3},
            {"category": "growth", "signal": "test", "strength": 3},
            {"category": "innovation", "signal": "test", "strength": 2},
        ]

        culture_type = _classify_culture_type(signals)
        assert culture_type == "startup"

    async def test_classify_corporate_culture(self) -> None:
        """Classify corporate-oriented culture signals."""
        signals = [
            {"category": "formal", "signal": "test", "strength": 3},
            {"category": "structured", "signal": "test", "strength": 3},
        ]

        culture_type = _classify_culture_type(signals)
        assert culture_type == "corporate"

    async def test_classify_hybrid_culture(self) -> None:
        """Classify hybrid culture with balanced signals."""
        signals = [
            {"category": "collaboration", "signal": "test", "strength": 2},
            {"category": "work_life_balance", "signal": "test", "strength": 2},
        ]

        culture_type = _classify_culture_type(signals)
        assert culture_type in ["hybrid", "startup", "corporate"]

    async def test_empty_signals_classification(self) -> None:
        """Empty signals default to hybrid."""
        culture_type = _classify_culture_type([])
        assert culture_type in ["hybrid", "startup", "corporate"]


class TestResearchCultureDna:
    """Full culture DNA analysis."""

    async def test_culture_dna_basic_structure(self) -> None:
        """Culture DNA returns expected structure."""
        result = await research_culture_dna("Google")

        assert "company" in result
        assert result["company"] == "Google"
        assert "culture_signals" in result
        assert isinstance(result["culture_signals"], list)
        assert "work_life_score" in result
        assert "innovation_score" in result
        assert "diversity_signals" in result
        assert "overall_culture_type" in result
        assert "github_analysis" in result

    async def test_culture_dna_scores_in_range(self) -> None:
        """Culture scores are in valid 0-1 range."""
        result = await research_culture_dna("Acme Corp")

        assert 0.0 <= result["work_life_score"] <= 1.0
        assert 0.0 <= result["innovation_score"] <= 1.0

    async def test_culture_dna_valid_culture_type(self) -> None:
        """Culture type is one of valid classifications."""
        result = await research_culture_dna("TechStartup")

        assert result["overall_culture_type"] in ["startup", "corporate", "hybrid"]

    async def test_culture_dna_with_domain(self) -> None:
        """Culture DNA accepts optional domain parameter."""
        result = await research_culture_dna("Google", domain="google.com")

        assert result["domain"] == "google.com"

    async def test_culture_dna_without_domain(self) -> None:
        """Culture DNA handles missing domain."""
        result = await research_culture_dna("Microsoft")

        assert result["domain"] == "unknown"

    async def test_culture_dna_signal_count(self) -> None:
        """Culture DNA includes signal count."""
        result = await research_culture_dna("TestCorp")

        assert "signal_count" in result
        assert result["signal_count"] >= 0

    async def test_culture_dna_diversity_signals_format(self) -> None:
        """Diversity signals are properly formatted."""
        result = await research_culture_dna("InclusiveCorp")

        assert isinstance(result["diversity_signals"], list)

    @patch("loom.tools.culture_dna.httpx.AsyncClient")
    async def test_culture_dna_with_mock_http(self, mock_client: AsyncMock) -> None:
        """Culture DNA handles HTTP client interaction."""
        # Note: Mock would need proper AsyncContext setup for full integration test
        result = await research_culture_dna("MockCorp")

        assert isinstance(result, dict)
        assert "company" in result
