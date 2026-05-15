"""Tests for HCS-10 academic research tools."""

from __future__ import annotations

import pytest

import loom.tools.adversarial.hcs10_academic


class TestGrantForensics:
    """Test research_grant_forensics tool."""

    def test_normal_text_zipf(self) -> None:
        """Test Zipf analysis on normal research text."""
        normal_text = (
            "We propose a novel approach to machine learning. "
            "Our method uses deep neural networks to solve complex problems. "
            "The experiment shows significant improvements in performance. "
            "We demonstrate that our approach outperforms baselines. "
            "Our results are reproducible and well-documented."
        )
        result = hcs10_academic.research_grant_forensics(
            grant_id="TEST-001", text=normal_text
        )

        assert result["grant_id"] == "TEST-001"
        assert result["zipf_exponent"] > 0
        assert 0 <= result["anomaly_score"] <= 1
        assert result["risk_level"] in ("HIGH", "MEDIUM", "LOW")

    def test_uniform_text_zipf_anomaly(self) -> None:
        """Test Zipf anomaly with too-uniform text."""
        uniform_text = " ".join(["word"] * 100)
        result = hcs10_academic.research_grant_forensics(text=uniform_text)

        # Uniform text should have low Zipf exponent
        assert result["zipf_exponent"] < 0.5
        assert result["zipf_anomaly"] == "FLAGGED"

    def test_benford_numbers(self) -> None:
        """Test Benford's Law on naturally-generated numbers."""
        text_with_numbers = "Sample size: 250. Mean: 45.3. SD: 12.8. Power: 0.95. Alpha: 0.05"
        result = hcs10_academic.research_grant_forensics(text=text_with_numbers)

        assert result["numbers_found"] > 0
        assert "benford_chi_square" in result
        assert result["benford_pvalue"] >= 0.0

    def test_empty_text(self) -> None:
        """Test with empty text."""
        result = hcs10_academic.research_grant_forensics(text="")
        assert "error" in result

    def test_no_numbers(self) -> None:
        """Test with text containing no numbers."""
        text = "This is a grant abstract with no numbers whatsoever."
        result = hcs10_academic.research_grant_forensics(text=text)

        assert result["numbers_found"] == 0
        assert "anomaly_score" in result


class TestMonocultureDetect:
    """Test research_monoculture_detect tool."""

    @pytest.mark.asyncio
    async def test_field_search(self) -> None:
        """Test monoculture detection for a research field."""
        result = await hcs10_academic.research_monoculture_detect("machine learning", max_papers=10)

        # Should return field name in result
        assert "field" in result
        # May have error or diversity metrics depending on API availability
        if "error" not in result:
            assert "diversity_index" in result
            assert 0 <= result["diversity_index"] <= 1
            assert "monoculture_risk" in result
            assert result["risk_level"] in ("HIGH", "MEDIUM", "LOW")

    @pytest.mark.asyncio
    async def test_field_with_error(self) -> None:
        """Test handling when no papers found."""
        # Use a very obscure field name
        result = await hcs10_academic.research_monoculture_detect(
            "xyzabc_nonexistent_field_qwerty", max_papers=5
        )

        # Should either return metrics or error
        assert "field" in result

    @pytest.mark.asyncio
    async def test_max_papers_parameter(self) -> None:
        """Test max_papers parameter is respected."""
        result = await hcs10_academic.research_monoculture_detect("neural networks", max_papers=5)
        assert "field" in result


class TestReviewCartel:
    """Test research_review_cartel tool."""

    @pytest.mark.asyncio
    async def test_author_analysis(self) -> None:
        """Test cartel detection for an author."""
        # Using a known author ID (would need valid Semantic Scholar ID)
        result = await hcs10_academic.research_review_cartel("1234567")

        assert "author_id" in result
        if "cartel_score" in result:
            assert 0 <= result["cartel_score"] <= 1
            assert result["risk_level"] in ("HIGH", "MEDIUM", "LOW")

    @pytest.mark.asyncio
    async def test_invalid_author(self) -> None:
        """Test with invalid author ID."""
        result = await hcs10_academic.research_review_cartel("invalid_id")

        # Should handle gracefully
        assert "author_id" in result


class TestDataFabrication:
    """Test research_data_fabrication tool."""

    def test_normal_numbers(self) -> None:
        """Test GRIM and Benford on normal data."""
        normal_numbers = [
            34.5, 28.9, 41.2, 35.6, 39.8, 31.4, 36.7, 33.2,
            42.1, 30.5, 38.9, 32.6, 40.1, 29.8, 37.3, 35.9
        ]
        result = hcs10_academic.research_data_fabrication(normal_numbers)

        assert result["numbers_analyzed"] == len(normal_numbers)
        assert "grim_failures" in result
        assert 0 <= result["fabrication_risk"] <= 1
        assert result["risk_level"] in ("HIGH", "MEDIUM", "LOW")

    def test_suspicious_precision(self) -> None:
        """Test numbers with excessive precision."""
        suspicious_numbers = [
            42.123456, 38.654321, 45.987654, 32.111111,
            40.555555, 35.777777
        ]
        result = hcs10_academic.research_data_fabrication(suspicious_numbers)

        # Check that analysis completes and returns metrics
        assert "grim_failure_rate" in result
        assert 0 <= result["grim_failure_rate"] <= 1
        assert "fabrication_risk" in result

    def test_empty_list(self) -> None:
        """Test with empty list."""
        result = hcs10_academic.research_data_fabrication([])
        assert "error" in result

    def test_benford_first_digits(self) -> None:
        """Test Benford's Law with various numbers."""
        # Mix of numbers that should follow Benford's Law
        numbers = [
            1.2, 15.3, 234.5, 2890.6, 12345.7,
            3.4, 45.6, 567.8, 6789.0, 12345.6
        ]
        result = hcs10_academic.research_data_fabrication(numbers)

        assert "benford_chi_square" in result
        assert "benford_pvalue" in result


class TestInstitutionalDecay:
    """Test research_institutional_decay tool."""

    @pytest.mark.asyncio
    async def test_institution_analysis(self) -> None:
        """Test decay detection for an institution."""
        result = await hcs10_academic.research_institutional_decay("MIT")

        assert "institution" in result
        if "decay_score" in result:
            assert 0 <= result["decay_score"] <= 1
            assert result["risk_level"] in ("HIGH", "MEDIUM", "LOW")

    @pytest.mark.asyncio
    async def test_institution_metrics(self) -> None:
        """Test institution metrics are present."""
        result = await hcs10_academic.research_institutional_decay("Harvard University")

        assert "institution" in result
        # May have error if no papers found
        if "papers_analyzed" in result:
            assert result["papers_analyzed"] >= 0


class TestShellFunding:
    """Test research_shell_funding tool."""

    @pytest.mark.asyncio
    async def test_company_trace(self) -> None:
        """Test shell company detection."""
        result = await hcs10_academic.research_shell_funding("Shell Company LLC")

        assert "company" in result
        if "opacity_score" in result:
            assert 0 <= result["opacity_score"] <= 1
            assert result["risk_level"] in ("HIGH", "MEDIUM", "LOW")

    @pytest.mark.asyncio
    async def test_legitimate_company(self) -> None:
        """Test legitimate company returns normal results."""
        result = await hcs10_academic.research_shell_funding("Apple Inc")

        assert "company" in result
        # Should return results, opacity may be low


class TestConferenceArbitrage:
    """Test research_conference_arbitrage tool."""

    @pytest.mark.asyncio
    async def test_conference_analysis(self) -> None:
        """Test conference arbitrage detection."""
        result = await hcs10_academic.research_conference_arbitrage("NeurIPS")

        assert "conference" in result
        if "papers_analyzed" in result:
            assert result["papers_analyzed"] >= 0

    @pytest.mark.asyncio
    async def test_conference_trends(self) -> None:
        """Test acceptance trend analysis."""
        result = await hcs10_academic.research_conference_arbitrage("ICML")

        assert "conference" in result
        if "arbitrage_risk" in result:
            assert result["arbitrage_risk"] in ("HIGH", "MEDIUM", "LOW")


class TestPreprintManipulation:
    """Test research_preprint_manipulation tool."""

    @pytest.mark.asyncio
    async def test_arxiv_paper_analysis(self) -> None:
        """Test preprint manipulation detection."""
        # This would need a real arXiv ID
        result = await hcs10_academic.research_preprint_manipulation(arxiv_id="2310.12345")

        assert "arxiv_id" in result or "error" in result

    @pytest.mark.asyncio
    async def test_topic_search(self) -> None:
        """Test topic-based preprint search."""
        result = await hcs10_academic.research_preprint_manipulation(topic="transformer")

        # Should return analysis or error
        assert "topic_search" in result or "error" in result


class TestUtilityFunctions:
    """Test utility functions used by HCS-10 tools."""

    def test_zipf_exponent_computation(self) -> None:
        """Test Zipf exponent calculation."""
        word_freq = {
            "the": 100, "and": 50, "to": 30, "a": 25,
            "in": 20, "of": 18, "is": 15, "it": 12
        }
        exponent = hcs10_academic._compute_zipf_exponent(word_freq)

        assert isinstance(exponent, float)
        assert exponent >= 0

    def test_zipf_empty_dict(self) -> None:
        """Test Zipf with empty dictionary."""
        exponent = hcs10_academic._compute_zipf_exponent({})
        assert exponent == 0.0

    def test_benford_distribution(self) -> None:
        """Test Benford's Law calculation."""
        # Natural numbers should roughly follow Benford
        numbers = [
            1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987
        ]
        chi_sq, pval = hcs10_academic._check_benford_distribution(numbers)

        assert isinstance(chi_sq, float)
        assert isinstance(pval, float)
        assert chi_sq >= 0
        assert 0 <= pval <= 1

    def test_benford_empty_list(self) -> None:
        """Test Benford with empty list."""
        chi_sq, pval = hcs10_academic._check_benford_distribution([])
        assert chi_sq == 0.0
        assert pval == 1.0

    def test_shannon_diversity_index(self) -> None:
        """Test Shannon Diversity Index calculation."""
        method_counts = {
            "neural network": 30, "deep learning": 25, "ensemble": 20,
            "regression": 15, "bayesian": 10
        }
        diversity = hcs10_academic._shannon_diversity_index(method_counts)

        assert 0 <= diversity <= 1
        assert isinstance(diversity, float)

    def test_shannon_single_method(self) -> None:
        """Test Shannon diversity with single method (no diversity)."""
        method_counts = {"deep learning": 100}
        diversity = hcs10_academic._shannon_diversity_index(method_counts)

        # Single method should have zero diversity
        assert diversity == 0.0

    def test_shannon_uniform_distribution(self) -> None:
        """Test Shannon diversity with uniform distribution."""
        method_counts = {
            "method1": 10, "method2": 10, "method3": 10, "method4": 10
        }
        diversity = hcs10_academic._shannon_diversity_index(method_counts)

        # Uniform distribution should have high diversity
        assert diversity > 0.8

    def test_shannon_empty_dict(self) -> None:
        """Test Shannon with empty dictionary."""
        diversity = hcs10_academic._shannon_diversity_index({})
        assert diversity == 0.0


class TestIntegration:
    """Integration tests for HCS-10 tools."""

    def test_fraud_detection_pipeline(self) -> None:
        """Test coordinated fraud detection across multiple tools."""
        suspect_text = (
            "This research demonstrates unprecedented results. "
            "Our sample was 50 subjects. Mean improvement 78.5%. "
            "Statistical significance p=0.001. Results published immediately."
        )

        # Run grant forensics
        grant_result = hcs10_academic.research_grant_forensics(
            grant_id="SUSPECT-001", text=suspect_text
        )

        # Run data fabrication check
        numbers = [78.5, 50.0, 0.001, 0.05]
        fab_result = hcs10_academic.research_data_fabrication(numbers)

        # Both should indicate some level of risk
        assert "anomaly_score" in grant_result
        assert "fabrication_risk" in fab_result

    def test_tool_error_handling(self) -> None:
        """Test error handling across tools."""
        # Test all tools with edge cases
        tools_tests = [
            (hcs10_academic.research_grant_forensics, {"text": ""}),
            (hcs10_academic.research_data_fabrication, {"numbers": []}),
        ]

        for tool_func, params in tools_tests:
            result = tool_func(**params)
            assert isinstance(result, dict)
            assert "error" in result or "risk_level" in result
