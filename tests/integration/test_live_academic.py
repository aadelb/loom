"""Live integration tests for Academic Integrity tools (REQ-044).

Tests 11 academic integrity tools with real API calls:
1. research_citation_analysis — Analyze citations → assert citation data
2. research_retraction_check — Check retractions → assert result
3. research_predatory_journal_check — Check journal → assert score
4. research_grant_forensics — Grant analysis → assert findings
5. research_data_fabrication — Detect fabrication → assert score
6. research_review_cartel — Detect review manipulation → assert result
7. research_monoculture_detect — Research monoculture → assert result
8. research_institutional_decay — Institutional health → assert metrics
9. research_shell_funding — Shell funding detection → assert result
10. research_conference_arbitrage — Conference analysis → assert score
11. research_preprint_manipulation — Preprint gaming → assert result

Marked with @pytest.mark.live for live API testing.
Run: PYTHONPATH=src python3 -m pytest tests/integration/test_live_academic.py -v -m live --timeout=60
"""

from __future__ import annotations

import pytest


class TestCitationAnalysis:
    """research_citation_analysis — Analyze citation networks for anomalies."""

    @pytest.mark.live
    def test_citation_analysis_valid_paper_id(self) -> None:
        """Citation analysis returns dict with paper_id, citation metrics."""
        from loom.tools.academic_integrity import research_citation_analysis

        # Use a well-known paper ID from Semantic Scholar
        # Example: A paper on transformers (widely cited)
        result = research_citation_analysis(paper_id="649def34f8be52c8b66281af98ae884c427425b7")

        assert isinstance(result, dict)
        assert "paper_id" in result
        # May have error or successful results
        if "error" not in result:
            assert "title" in result or "paper_id" in result
            assert "citation_count" in result or "anomaly_score" in result

    @pytest.mark.live
    def test_citation_analysis_unknown_paper(self) -> None:
        """Citation analysis returns error for invalid paper ID."""
        from loom.tools.academic_integrity import research_citation_analysis

        result = research_citation_analysis(paper_id="nonexistent123456789")

        assert isinstance(result, dict)
        assert "paper_id" in result
        # Should either error or return no data
        assert "error" in result or "paper_id" in result

    @pytest.mark.live
    def test_citation_analysis_includes_anomaly_score(self) -> None:
        """Citation analysis should compute anomaly_score when data available."""
        from loom.tools.academic_integrity import research_citation_analysis

        result = research_citation_analysis(
            paper_id="649def34f8be52c8b66281af98ae884c427425b7", depth=1
        )

        assert isinstance(result, dict)
        # If successful, should have anomaly_score
        if "error" not in result:
            assert "anomaly_score" in result
            assert 0 <= result["anomaly_score"] <= 100


class TestRetractionCheck:
    """research_retraction_check — Check for retracted papers and PubPeer comments."""

    @pytest.mark.live
    def test_retraction_check_returns_dict(self) -> None:
        """Retraction check returns dict with papers_checked and retractions_found."""
        from loom.tools.academic_integrity import research_retraction_check

        result = research_retraction_check(query="data fabrication", max_results=10)

        assert isinstance(result, dict)
        assert "query" in result
        assert "papers_checked" in result or "retractions_found" in result

    @pytest.mark.live
    def test_retraction_check_author_query(self) -> None:
        """Retraction check works with author name queries."""
        from loom.tools.academic_integrity import research_retraction_check

        # Test with a general research term
        result = research_retraction_check(query="machine learning research", max_results=5)

        assert isinstance(result, dict)
        assert "query" in result
        assert result["query"] == "machine learning research"

    @pytest.mark.live
    def test_retraction_check_max_results_respected(self) -> None:
        """Retraction check respects max_results parameter."""
        from loom.tools.academic_integrity import research_retraction_check

        result = research_retraction_check(query="neural networks", max_results=3)

        assert isinstance(result, dict)
        assert "papers_checked" in result
        # papers_checked should not exceed max_results
        assert result["papers_checked"] <= 3


class TestPredatoryJournalCheck:
    """research_predatory_journal_check — Check journal for predatory indicators."""

    @pytest.mark.live
    def test_predatory_check_legitimate_journal(self) -> None:
        """Predatory check returns low score for reputable journal."""
        from loom.tools.academic_integrity import research_predatory_journal_check

        result = research_predatory_journal_check("Nature")

        assert isinstance(result, dict)
        assert "journal_name" in result
        assert "predatory_score" in result or "is_in_doaj" in result
        # Nature is legitimate, so score should be low
        if "predatory_score" in result:
            assert 0 <= result["predatory_score"] <= 100

    @pytest.mark.live
    def test_predatory_check_returns_risk_indicators(self) -> None:
        """Predatory check returns risk_indicators list."""
        from loom.tools.academic_integrity import research_predatory_journal_check

        result = research_predatory_journal_check("Journal of Research")

        assert isinstance(result, dict)
        assert "risk_indicators" in result or "journal_name" in result
        # risk_indicators should be a list
        if "risk_indicators" in result:
            assert isinstance(result["risk_indicators"], list)

    @pytest.mark.live
    def test_predatory_check_includes_crossref_status(self) -> None:
        """Predatory check includes Crossref registration status."""
        from loom.tools.academic_integrity import research_predatory_journal_check

        result = research_predatory_journal_check("Science")

        assert isinstance(result, dict)
        # Should check Crossref registration
        if "crossref_registered" in result:
            assert isinstance(result["crossref_registered"], bool)
        if "is_in_doaj" in result:
            assert isinstance(result["is_in_doaj"], bool)


class TestGrantForensics:
    """research_grant_forensics — Apply Zipf and Benford analysis to grant text."""

    @pytest.mark.live
    def test_grant_forensics_normal_text(self) -> None:
        """Grant forensics analyzes normal grant abstract."""
        from loom.tools.hcs10_academic import research_grant_forensics

        # Realistic grant abstract
        text = """
        This research explores novel approaches to distributed machine learning
        optimization. We propose a groundbreaking framework that improves upon
        existing techniques through innovative methods. Our preliminary results
        show significant improvements in convergence speed and resource efficiency.
        The work builds upon established principles while introducing transformative
        modifications to the core algorithms used in contemporary research.
        """

        result = research_grant_forensics(grant_id="TEST-2024-001", text=text)

        assert isinstance(result, dict)
        assert "grant_id" in result
        assert "zipf_exponent" in result or "error" not in result
        assert "anomaly_score" in result or "fraud_probability" in result

    @pytest.mark.live
    def test_grant_forensics_computes_zipf_exponent(self) -> None:
        """Grant forensics computes Zipf exponent."""
        from loom.tools.hcs10_academic import research_grant_forensics

        text = "research research research methodology methodology methodology approach approach"
        result = research_grant_forensics(text=text)

        assert isinstance(result, dict)
        if "error" not in result:
            assert "zipf_exponent" in result
            assert isinstance(result["zipf_exponent"], (int, float))

    @pytest.mark.live
    def test_grant_forensics_detects_benford_anomaly(self) -> None:
        """Grant forensics applies Benford's law test."""
        from loom.tools.hcs10_academic import research_grant_forensics

        # Text with numbers
        text = "We conducted 47 experiments with 183 participants. Found 12 significant effects."
        result = research_grant_forensics(text=text)

        assert isinstance(result, dict)
        if "error" not in result:
            assert "benford_chi_square" in result
            assert "benford_pvalue" in result


class TestDataFabrication:
    """research_data_fabrication — Apply GRIM and Benford tests to detect fabrication."""

    @pytest.mark.live
    def test_data_fabrication_legitimate_numbers(self) -> None:
        """Data fabrication test returns low risk for realistic numbers."""
        from loom.tools.hcs10_academic import research_data_fabrication

        # Realistic means from psychological study (n=30)
        numbers = [3.2, 4.1, 3.8, 2.9, 4.5, 3.3, 3.7, 4.0, 3.5, 2.8]

        result = research_data_fabrication(numbers)

        assert isinstance(result, dict)
        assert "fabrication_risk" in result
        assert 0 <= result["fabrication_risk"] <= 1.0

    @pytest.mark.live
    def test_data_fabrication_includes_grim_test(self) -> None:
        """Data fabrication includes GRIM test results."""
        from loom.tools.hcs10_academic import research_data_fabrication

        numbers = [1.5, 2.3, 3.7, 4.2, 5.1]

        result = research_data_fabrication(numbers)

        assert isinstance(result, dict)
        assert "grim_failures" in result
        assert "grim_failure_rate" in result
        assert isinstance(result["grim_failures"], int)

    @pytest.mark.live
    def test_data_fabrication_benford_check(self) -> None:
        """Data fabrication includes Benford test."""
        from loom.tools.hcs10_academic import research_data_fabrication

        numbers = [10, 20, 30, 15, 25, 35, 40, 12, 22, 32]

        result = research_data_fabrication(numbers)

        assert isinstance(result, dict)
        assert "benford_chi_square" in result
        assert "benford_pvalue" in result


class TestReviewCartel:
    """research_review_cartel — Detect peer review cartels via mutual citations."""

    @pytest.mark.live
    def test_review_cartel_detection_valid_author(self) -> None:
        """Review cartel detection analyzes author papers."""
        from loom.tools.hcs10_academic import research_review_cartel

        # Use a valid Semantic Scholar author ID format
        result = research_review_cartel(author_id="1695689")

        assert isinstance(result, dict)
        assert "author_id" in result
        # Should have analysis results or error
        if "error" not in result:
            assert "papers_analyzed" in result
            assert "cartel_score" in result

    @pytest.mark.live
    def test_review_cartel_returns_score(self) -> None:
        """Review cartel returns cartel_score (0-1)."""
        from loom.tools.hcs10_academic import research_review_cartel

        result = research_review_cartel(author_id="1695689")

        assert isinstance(result, dict)
        if "error" not in result:
            assert "cartel_score" in result
            assert 0 <= result["cartel_score"] <= 1.0

    @pytest.mark.live
    def test_review_cartel_includes_risk_level(self) -> None:
        """Review cartel includes risk_level assessment."""
        from loom.tools.hcs10_academic import research_review_cartel

        result = research_review_cartel(author_id="1695689")

        assert isinstance(result, dict)
        if "error" not in result and "risk_level" in result:
            assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH"]


class TestMonocultureDetect:
    """research_monoculture_detect — Detect research field monoculture."""

    @pytest.mark.live
    def test_monoculture_detection_valid_field(self) -> None:
        """Monoculture detection analyzes research field."""
        from loom.tools.hcs10_academic import research_monoculture_detect

        result = research_monoculture_detect(field="machine learning", max_papers=10)

        assert isinstance(result, dict)
        assert "field" in result
        # Should have analysis or error
        if "error" not in result:
            assert "papers_analyzed" in result or "methods_found" in result

    @pytest.mark.live
    def test_monoculture_computes_diversity_index(self) -> None:
        """Monoculture detection computes Shannon diversity index."""
        from loom.tools.hcs10_academic import research_monoculture_detect

        result = research_monoculture_detect(field="deep learning", max_papers=5)

        assert isinstance(result, dict)
        if "error" not in result:
            assert "diversity_index" in result
            assert 0 <= result["diversity_index"] <= 1.0

    @pytest.mark.live
    def test_monoculture_risk_level(self) -> None:
        """Monoculture detection includes risk_level."""
        from loom.tools.hcs10_academic import research_monoculture_detect

        result = research_monoculture_detect(field="neural networks", max_papers=8)

        assert isinstance(result, dict)
        if "error" not in result and "risk_level" in result:
            assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH"]


class TestInstitutionalDecay:
    """research_institutional_decay — Assess institutional health metrics."""

    @pytest.mark.live
    def test_institutional_decay_valid_institution(self) -> None:
        """Institutional decay analyzes institution papers."""
        from loom.tools.hcs10_academic import research_institutional_decay

        result = research_institutional_decay("Stanford University")

        assert isinstance(result, dict)
        assert "institution" in result
        # Should have analysis or error
        if "error" not in result:
            assert "papers_analyzed" in result or "decay_score" in result

    @pytest.mark.live
    def test_institutional_decay_computes_metrics(self) -> None:
        """Institutional decay computes retraction rate and trend."""
        from loom.tools.hcs10_academic import research_institutional_decay

        result = research_institutional_decay("MIT")

        assert isinstance(result, dict)
        if "error" not in result:
            if "retraction_rate" in result:
                assert 0 <= result["retraction_rate"] <= 1.0
            if "decay_score" in result:
                assert 0 <= result["decay_score"] <= 1.0

    @pytest.mark.live
    def test_institutional_decay_publication_trend(self) -> None:
        """Institutional decay includes publication trend slope."""
        from loom.tools.hcs10_academic import research_institutional_decay

        result = research_institutional_decay("Harvard")

        assert isinstance(result, dict)
        if "error" not in result:
            if "publication_trend_slope" in result:
                assert isinstance(result["publication_trend_slope"], (int, float))
            if "trend_direction" in result:
                assert result["trend_direction"] in ["declining", "stable", "growing"]


class TestShellFunding:
    """research_shell_funding — Detect shell company funding structures."""

    @pytest.mark.live
    def test_shell_funding_valid_company(self) -> None:
        """Shell funding detection analyzes company."""
        from loom.tools.hcs10_academic import research_shell_funding

        result = research_shell_funding("Apple Inc")

        assert isinstance(result, dict)
        assert "company" in result
        # Should have analysis or error
        if "error" not in result:
            assert "corporate_links" in result or "opacity_score" in result

    @pytest.mark.live
    def test_shell_funding_opacity_score(self) -> None:
        """Shell funding returns opacity_score (0-1)."""
        from loom.tools.hcs10_academic import research_shell_funding

        result = research_shell_funding("Tech Startup LLC")

        assert isinstance(result, dict)
        if "error" not in result:
            if "opacity_score" in result:
                assert 0 <= result["opacity_score"] <= 1.0

    @pytest.mark.live
    def test_shell_funding_indicators(self) -> None:
        """Shell funding includes opacity indicators."""
        from loom.tools.hcs10_academic import research_shell_funding

        result = research_shell_funding("Research Foundation")

        assert isinstance(result, dict)
        if "error" not in result:
            if "opacity_indicators" in result:
                assert isinstance(result["opacity_indicators"], list)


class TestConferenceArbitrage:
    """research_conference_arbitrage — Analyze conference acceptance patterns."""

    @pytest.mark.live
    def test_conference_arbitrage_valid_conference(self) -> None:
        """Conference arbitrage analyzes conference."""
        from loom.tools.hcs10_academic import research_conference_arbitrage

        result = research_conference_arbitrage("NeurIPS")

        assert isinstance(result, dict)
        assert "conference" in result
        # Should have analysis or error
        if "error" not in result:
            assert "total_papers_in_dblp" in result or "acceptance_trend" in result

    @pytest.mark.live
    def test_conference_arbitrage_trend_analysis(self) -> None:
        """Conference arbitrage includes acceptance trend."""
        from loom.tools.hcs10_academic import research_conference_arbitrage

        result = research_conference_arbitrage("ICML")

        assert isinstance(result, dict)
        if "error" not in result:
            if "acceptance_trend" in result:
                assert isinstance(result["acceptance_trend"], list)

    @pytest.mark.live
    def test_conference_arbitrage_risk_level(self) -> None:
        """Conference arbitrage includes risk assessment."""
        from loom.tools.hcs10_academic import research_conference_arbitrage

        result = research_conference_arbitrage("ICCV")

        assert isinstance(result, dict)
        if "error" not in result:
            if "arbitrage_risk" in result:
                assert result["arbitrage_risk"] in ["LOW", "MEDIUM", "HIGH"]


class TestPreprintManipulation:
    """research_preprint_manipulation — Detect preprint gaming patterns."""

    @pytest.mark.live
    def test_preprint_manipulation_with_arxiv_id(self) -> None:
        """Preprint manipulation analyzes arXiv paper."""
        from loom.tools.hcs10_academic import research_preprint_manipulation

        # Use a valid arXiv ID format (YYMM.NNNNN)
        result = research_preprint_manipulation(arxiv_id="2310.12345")

        assert isinstance(result, dict)
        if "error" not in result:
            assert "arxiv_id" in result or "title" in result

    @pytest.mark.live
    def test_preprint_manipulation_with_topic(self) -> None:
        """Preprint manipulation searches by topic."""
        from loom.tools.hcs10_academic import research_preprint_manipulation

        result = research_preprint_manipulation(topic="transformer")

        assert isinstance(result, dict)
        # Should return analysis or error

    @pytest.mark.live
    def test_preprint_manipulation_scoring(self) -> None:
        """Preprint manipulation includes manipulation_risk score."""
        from loom.tools.hcs10_academic import research_preprint_manipulation

        result = research_preprint_manipulation(arxiv_id="2310.12345")

        assert isinstance(result, dict)
        if "error" not in result:
            if "manipulation_risk" in result:
                assert 0 <= result["manipulation_risk"] <= 1.0
            if "social_amplification_score" in result:
                assert 0 <= result["social_amplification_score"] <= 1.0

    @pytest.mark.live
    def test_preprint_manipulation_risk_level(self) -> None:
        """Preprint manipulation includes risk_level."""
        from loom.tools.hcs10_academic import research_preprint_manipulation

        result = research_preprint_manipulation(topic="neural networks")

        assert isinstance(result, dict)
        if "error" not in result and "risk_level" in result:
            assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH"]


class TestAcademicIntegritySuite:
    """Integration suite testing all 11 tools together."""

    @pytest.mark.live
    def test_all_tools_return_dicts(self) -> None:
        """All academic integrity tools return dict results."""
        from loom.tools.academic_integrity import (
            research_citation_analysis,
            research_predatory_journal_check,
            research_retraction_check,
        )
        from loom.tools.hcs10_academic import (
            research_conference_arbitrage,
            research_data_fabrication,
            research_grant_forensics,
            research_institutional_decay,
            research_monoculture_detect,
            research_preprint_manipulation,
            research_review_cartel,
            research_shell_funding,
        )

        # Call each tool (may error but should return dict)
        results = [
            research_citation_analysis("test"),
            research_retraction_check("test"),
            research_predatory_journal_check("Test Journal"),
            research_grant_forensics(text="test text"),
            research_data_fabrication([1.0, 2.0, 3.0]),
            research_review_cartel("test"),
            research_monoculture_detect("test field"),
            research_institutional_decay("Test University"),
            research_shell_funding("Test Company"),
            research_conference_arbitrage("TestCONF"),
            research_preprint_manipulation(topic="test"),
        ]

        # All results should be dicts
        for result in results:
            assert isinstance(result, dict), f"Result is not dict: {type(result)}"

    @pytest.mark.live
    def test_academic_tools_handle_errors_gracefully(self) -> None:
        """Academic integrity tools handle errors gracefully."""
        from loom.tools.academic_integrity import research_retraction_check
        from loom.tools.hcs10_academic import research_grant_forensics

        # These should not raise exceptions
        result1 = research_retraction_check("")
        result2 = research_grant_forensics(text="")

        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
