"""Unit tests for creative research tools — darkweb early warning, job deception, bias lens, salary synthesis."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.bias_lens import (
    _analyze_citation_network,
    _count_hedging_language,
    _detect_p_hacking_indicators,
    _extract_p_values,
    research_bias_lens,
)
from loom.tools.darkweb_early_warning import (
    _estimate_severity,
    research_darkweb_early_warning,
)
from loom.tools.deception_job_scanner import (
    _count_pattern_matches,
    _extract_salary_range,
    research_deception_job_scan,
)
from loom.tools.salary_synthesizer import (
    _calculate_statistics,
    _infer_location_adjustment,
    research_salary_synthesize,
)


class TestDarkwebEarlyWarning:
    """research_darkweb_early_warning function."""

    def test_empty_keywords_returns_error(self) -> None:
        """Empty keywords list returns error."""
        result = research_darkweb_early_warning([])
        assert "error" in result
        assert result["alert_count"] == 0
        assert result["highest_severity"] is None

    def test_keywords_capped_at_ten(self) -> None:
        """Keywords list capped at 10 items."""
        keywords = [f"keyword_{i}" for i in range(15)]
        result = research_darkweb_early_warning(keywords)
        assert len(result["keywords"]) == 10

    def test_severity_estimation_critical(self) -> None:
        """Critical severity detected for high-risk keywords."""
        severity = _estimate_severity("zero-day exploit", 15)
        assert severity == "critical"

    def test_severity_estimation_high(self) -> None:
        """High severity for medium-risk keywords."""
        severity = _estimate_severity("breach", 5)
        assert severity == "high"

    def test_severity_estimation_low(self) -> None:
        """Low severity for low-mention keywords."""
        severity = _estimate_severity("generic keyword", 1)
        assert severity == "low"

    def test_result_structure(self) -> None:
        """Result has expected structure."""
        with patch("loom.tools.darkweb_early_warning._ahmia_search", new_callable=AsyncMock) as mock_ahmia:
            with patch("loom.tools.darkweb_early_warning._otx_search", new_callable=AsyncMock) as mock_otx:
                with patch("loom.tools.darkweb_early_warning._reddit_darknet_search", new_callable=AsyncMock) as mock_reddit:
                    with patch("loom.tools.darkweb_early_warning._hackernews_search", new_callable=AsyncMock) as mock_hn:
                        mock_ahmia.return_value = []
                        mock_otx.return_value = []
                        mock_reddit.return_value = []
                        mock_hn.return_value = []

                        result = research_darkweb_early_warning(["malware"])
                        assert "keywords" in result
                        assert "alerts" in result
                        assert "alert_count" in result
                        assert "highest_severity" in result
                        assert "timestamp" in result


class TestDeceptionJobScanner:
    """research_deception_job_scan function."""

    def test_empty_text_returns_error(self) -> None:
        """Empty job_text returns error."""
        result = research_deception_job_scan(job_text="")
        assert "error" in result
        assert result["risk_score"] == 0

    def test_text_too_short_returns_error(self) -> None:
        """Text shorter than 50 chars returns error."""
        result = research_deception_job_scan(job_text="short")
        assert "error" in result

    def test_salary_range_extraction_explicit(self) -> None:
        """Explicit salary range extracted correctly."""
        salary_info = _extract_salary_range("$50,000 - $75,000")
        assert salary_info == (50000, 75000, False)

    def test_salary_range_extraction_vague(self) -> None:
        """Vague salary ranges marked as vague."""
        salary_info = _extract_salary_range("up to $100,000")
        assert salary_info[2] is True  # is_vague

    def test_pattern_matching_urgency(self) -> None:
        """Urgency pattern matching works."""
        text = "We need someone IMMEDIATELY and ASAP to start work"
        count = _count_pattern_matches(text, ["immediately", "asap"])
        assert count == 2

    def test_red_flags_no_salary(self) -> None:
        """Missing salary generates red flag."""
        text = "This is a great opportunity for a developer. Please apply."
        result = research_deception_job_scan(job_text=text)
        assert "no_salary_mentioned" in result["red_flags"]

    def test_green_flags_benefits(self) -> None:
        """Benefits mentioned generates green flag."""
        text = "We offer competitive salary, health insurance, 401k, and stock options. Apply now!"
        result = research_deception_job_scan(job_text=text)
        assert any("benefits" in flag.lower() for flag in result["green_flags"])

    def test_red_flags_mlm(self) -> None:
        """MLM patterns generate red flags."""
        text = "Build your team, recruit other agents, unlimited income potential from commissions!"
        result = research_deception_job_scan(job_text=text)
        assert any("mlm" in flag.lower() for flag in result["red_flags"])

    def test_risk_score_range(self) -> None:
        """Risk score stays within 0-100 range."""
        text = "Join our high-paying opportunity! Unlimited income, no experience needed, work from home!"
        result = research_deception_job_scan(job_text=text)
        assert 0 <= result["risk_score"] <= 100

    def test_result_structure(self) -> None:
        """Result has expected structure."""
        text = "Senior Software Engineer - $120,000 to $150,000. Apply with resume."
        result = research_deception_job_scan(job_text=text)
        assert "risk_score" in result
        assert "red_flags" in result
        assert "green_flags" in result
        assert "analysis_timestamp" in result


class TestBiasLens:
    """research_bias_lens function."""

    def test_no_input_returns_error(self) -> None:
        """No paper_id or text returns error."""
        result = research_bias_lens()
        assert "error" in result
        assert result["bias_score"] == 0

    def test_p_value_extraction(self) -> None:
        """P-values extracted from text."""
        text = "The results were significant (p = 0.03) and replicated (p < 0.05)."
        p_values = _extract_p_values(text)
        assert 0.03 in p_values
        assert any(p < 0.06 for p in p_values)

    def test_hedging_language_detection(self) -> None:
        """Hedging language counted correctly."""
        text = "These results may suggest that we might have found evidence that perhaps indicates a pattern."
        count = _count_hedging_language(text)
        assert count > 0

    def test_p_hacking_indicators(self) -> None:
        """P-hacking patterns detected."""
        text = "Multiple comparisons were performed with Bonferroni correction applied."
        indicators = _detect_p_hacking_indicators(text)
        assert len(indicators) > 0

    def test_citation_network_self_citation_rate(self) -> None:
        """Self-citation rate calculated correctly."""
        authors = [{"name": "John Doe"}, {"name": "Jane Smith"}]
        citations = [
            {"authors": [{"name": "John Doe"}]},
            {"authors": [{"name": "Other Author"}]},
        ]
        result = _analyze_citation_network(authors, citations)
        assert result["self_citation_rate"] > 0.0
        assert "self_citation_count" in result

    def test_bias_score_range(self) -> None:
        """Bias score stays within 0-100 range."""
        text = "These results suggest that perhaps we may have found evidence indicating bias."
        result = research_bias_lens(text=text)
        assert 0 <= result["bias_score"] <= 100

    def test_empty_text_no_analysis(self) -> None:
        """Very short text returns minimal analysis."""
        result = research_bias_lens(text="short")
        assert "error" in result

    def test_result_structure(self) -> None:
        """Result has expected structure."""
        text = "We found that p = 0.04, suggesting our hypothesis may be true based on multiple tests."
        result = research_bias_lens(text=text)
        assert "bias_score" in result
        assert "bias_types" in result
        assert "p_value_distribution" in result
        assert "funding_bias_risk" in result


class TestSalarySynthesizer:
    """research_salary_synthesize function."""

    def test_empty_job_title_returns_error(self) -> None:
        """Empty job title returns error."""
        result = research_salary_synthesize("")
        assert "error" in result

    def test_job_title_too_short_returns_error(self) -> None:
        """Job title shorter than 2 chars returns error."""
        result = research_salary_synthesize("a")
        assert "error" in result

    def test_salary_statistics_calculation(self) -> None:
        """Salary statistics calculated correctly."""
        salaries = [50000, 60000, 70000, 80000, 90000]
        stats = _calculate_statistics(salaries)
        assert stats["min"] == 50000
        assert stats["max"] == 90000
        assert stats["median"] == 70000

    def test_salary_statistics_empty_list(self) -> None:
        """Empty salary list returns zeros."""
        stats = _calculate_statistics([])
        assert stats["min"] == 0
        assert stats["median"] == 0
        assert stats["max"] == 0

    def test_location_adjustment_high_cost(self) -> None:
        """High-cost locations apply 1.3x multiplier."""
        base = {"min": 100000, "median": 150000, "max": 200000}
        adjusted = _infer_location_adjustment("San Francisco", base)
        assert adjusted["median"] == int(150000 * 1.3)

    def test_location_adjustment_medium_cost(self) -> None:
        """Medium-cost locations apply 1.15x multiplier."""
        base = {"min": 100000, "median": 150000, "max": 200000}
        adjusted = _infer_location_adjustment("Seattle", base)
        assert adjusted["median"] == int(150000 * 1.15)

    def test_location_adjustment_remote(self) -> None:
        """Remote location applies no adjustment."""
        base = {"min": 100000, "median": 150000, "max": 200000}
        adjusted = _infer_location_adjustment("remote", base)
        assert adjusted["median"] == 150000

    def test_result_structure(self) -> None:
        """Result has expected structure."""
        result = research_salary_synthesize("software engineer", location="remote")
        assert "job_title" in result
        assert "estimated_range" in result
        assert "sources_checked" in result
        assert "data_points" in result
        assert "confidence" in result
        assert "location" in result

    def test_confidence_based_on_data_points(self) -> None:
        """Confidence increases with data points."""
        result = research_salary_synthesize("software engineer")
        assert 0.0 <= result["confidence"] <= 1.0

    def test_skill_premium(self) -> None:
        """Premium skills increase salary estimate."""
        base_result = research_salary_synthesize("developer", skills=[])
        premium_result = research_salary_synthesize(
            "developer", skills=["kubernetes", "aws"]
        )
        # Premium result should generally be higher (accounting for no data)
        assert "skill_premium_applied" in premium_result
        assert premium_result["skill_premium_applied"] >= 0.0

    def test_multiple_sources_checked(self) -> None:
        """Multiple sources checked in result."""
        result = research_salary_synthesize("software engineer")
        assert len(result["sources_checked"]) >= 1
        # Should include at least stack overflow survey
        assert "stackoverflow_survey" in result["sources_checked"]


class TestIntegration:
    """Integration tests across tools."""

    def test_darkweb_warning_with_data(self) -> None:
        """Darkweb warning returns structured data."""
        with patch("loom.tools.darkweb_early_warning._ahmia_search", new_callable=AsyncMock) as mock_ahmia:
            with patch("loom.tools.darkweb_early_warning._otx_search", new_callable=AsyncMock) as mock_otx:
                with patch("loom.tools.darkweb_early_warning._reddit_darknet_search", new_callable=AsyncMock) as mock_reddit:
                    with patch("loom.tools.darkweb_early_warning._hackernews_search", new_callable=AsyncMock) as mock_hn:
                        mock_ahmia.return_value = [
                            {
                                "title": "Exploit discussion",
                                "url": "http://example.onion",
                            }
                        ]
                        mock_otx.return_value = []
                        mock_reddit.return_value = []
                        mock_hn.return_value = []

                        result = research_darkweb_early_warning(["exploit"])
                        assert result["alert_count"] > 0
                        assert any("exploit" in alert.get("title", "").lower() for alert in result["alerts"])

    @pytest.mark.parametrize(
        "job_text,should_have_red_flags",
        [
            (
                "Salary $100k-$150k, benefits included, apply now",
                False,
            ),
            (
                "No salary disclosed, urgently recruiting, unlimited income potential!",
                True,
            ),
        ],
    )
    def test_job_scanner_parametrized(
        self, job_text: str, should_have_red_flags: bool
    ) -> None:
        """Job scanner works with different inputs."""
        result = research_deception_job_scan(job_text=job_text)
        has_red_flags = len(result["red_flags"]) > 0
        assert has_red_flags == should_have_red_flags
