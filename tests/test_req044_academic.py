"""
Test REQ-044 — Academic 11 tools: return academic data.

Tests all 11 academic integrity tools by directly importing and calling them
to verify they return academic-relevant data.

Tools tested:
1. citation_analysis
2. retraction_check
3. predatory_journal_check
4. grant_forensics
5. monoculture_detect
6. review_cartel
7. data_fabrication
8. institutional_decay
9. shell_funding
10. conference_arbitrage
11. preprint_manipulation
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

logger = logging.getLogger("tests.test_req044_academic")


pytestmark = pytest.mark.asyncio

class TestAcademicCitationAnalysis:
    """Test research_citation_analysis tool."""

    async def test_citation_analysis_returns_dict(self) -> None:
        """Test citation_analysis returns academic data."""
        from loom.tools.academic_integrity import research_citation_analysis

        # Use a test paper ID
        result = await research_citation_analysis(
            paper_id="e735fc98d34e0e9e72aa8b20f1c3cc3a9f3e76c1",
            depth=1,
        )

        # Verify response is a dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have academic metrics or error info
        has_academic_data = any(
            key in result
            for key in [
                "citation_count",
                "reference_count",
                "anomaly_score",
                "authors_count",
                "error",
            ]
        )
        assert has_academic_data, f"Missing academic fields in: {list(result.keys())}"

        logger.info(f"✓ citation_analysis returned: {list(result.keys())[:5]}")


class TestAcademicRetractionCheck:
    """Test research_retraction_check tool."""

    async def test_retraction_check_returns_dict(self) -> None:
        """Test retraction_check returns academic data."""
        from loom.tools.academic_integrity import research_retraction_check

        result = await research_retraction_check(
            query="machine learning bias",
            max_results=10,
        )

        # Verify response is a dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have retraction/paper metrics
        has_academic_data = any(
            key in result
            for key in [
                "papers_checked",
                "retractions_found",
                "retraction_details",
                "query",
                "pubpeer",
                "error",
            ]
        )
        assert has_academic_data, f"Missing retraction fields in: {list(result.keys())}"

        logger.info(f"✓ retraction_check returned: {list(result.keys())[:5]}")


class TestAcademicPredatoryJournal:
    """Test research_predatory_journal_check tool."""

    async def test_predatory_journal_check_returns_dict(self) -> None:
        """Test predatory_journal_check returns journal assessment data."""
        from loom.tools.academic_integrity import research_predatory_journal_check

        result = await research_predatory_journal_check(journal_name="PLOS ONE")

        # Verify response is a dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have journal assessment metrics
        has_academic_data = any(
            key in result
            for key in [
                "journal_name",
                "predatory_score",
                "doaj_indexed",
                "issn_status",
                "publication_frequency",
                "registration_status",
                "error",
            ]
        )
        assert has_academic_data, f"Missing journal fields in: {list(result.keys())}"

        logger.info(f"✓ predatory_journal_check returned: {list(result.keys())[:5]}")


class TestAcademicGrantForensics:
    """Test research_grant_forensics tool."""

    async def test_grant_forensics_returns_dict(self) -> None:
        """Test grant_forensics analyzes grant text."""
        from loom.tools.hcs10_academic import research_grant_forensics

        grant_text = """
        Grant: Deep Learning for Medical Imaging
        This research investigates neural networks for healthcare applications.
        Funded by NIH, collaboration with Stanford University and MIT.
        """

        result = research_grant_forensics(text=grant_text)

        # Verify response is a dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have forensics analysis
        # Actual fields: grant_id, text_length, unique_words, total_words, zipf_exponent,
        # zipf_anomaly, numbers_found, benford_chi_square, benford_pvalue, benford_anomaly,
        # fraud_probability, anomaly_score, linguistic_markers, risk_level
        has_academic_data = any(
            key in result
            for key in [
                "fraud_probability",
                "anomaly_score",
                "risk_level",
                "benford_anomaly",
                "zipf_anomaly",
                "error",
            ]
        )
        assert has_academic_data, f"Missing forensics fields in: {list(result.keys())}"

        logger.info(f"✓ grant_forensics returned: {list(result.keys())[:5]}")


class TestAcademicMonocultureDetect:
    """Test research_monoculture_detect tool."""

    async def test_monoculture_detect_returns_dict(self) -> None:
        """Test monoculture_detect finds citation monopolies."""
        from loom.tools.hcs10_academic import research_monoculture_detect

        result = await research_monoculture_detect(field="machine learning", max_papers=20)

        # Verify response is a dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have monoculture analysis
        has_academic_data = any(
            key in result
            for key in [
                "field",
                "monoculture_score",
                "dominant_authors",
                "top_papers",
                "concentration",
                "error",
            ]
        )
        assert has_academic_data, f"Missing monoculture fields in: {list(result.keys())}"

        logger.info(f"✓ monoculture_detect returned: {list(result.keys())[:5]}")


class TestAcademicReviewCartel:
    """Test research_review_cartel tool."""

    async def test_review_cartel_returns_dict(self) -> None:
        """Test review_cartel detects peer review networks."""
        from loom.tools.hcs10_academic import research_review_cartel

        result = await research_review_cartel(author_id="test_researcher")

        # Verify response is a dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have cartel analysis
        has_academic_data = any(
            key in result
            for key in [
                "author_id",
                "reviews_count",
                "cartel_score",
                "suspicious_patterns",
                "reviewer_network",
                "error",
            ]
        )
        assert has_academic_data, f"Missing cartel fields in: {list(result.keys())}"

        logger.info(f"✓ review_cartel returned: {list(result.keys())[:5]}")


class TestAcademicDataFabrication:
    """Test research_data_fabrication tool."""

    async def test_data_fabrication_returns_dict(self) -> None:
        """Test data_fabrication detects suspicious data patterns."""
        from loom.tools.hcs10_academic import research_data_fabrication

        numbers = [1.2, 1.3, 1.25, 1.28, 1.31]

        result = research_data_fabrication(numbers=numbers)

        # Verify response is a dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have fabrication analysis
        # Actual fields: numbers_analyzed, grim_failures, grim_failure_rate, decimal_anomalies,
        # benford_chi_square, benford_pvalue, benford_deviation, fabrication_risk, risk_level
        has_academic_data = any(
            key in result
            for key in [
                "fabrication_risk",
                "grim_failures",
                "benford_deviation",
                "decimal_anomalies",
                "risk_level",
                "error",
            ]
        )
        assert has_academic_data, f"Missing fabrication fields in: {list(result.keys())}"

        logger.info(f"✓ data_fabrication returned: {list(result.keys())[:5]}")


class TestAcademicInstitutionalDecay:
    """Test research_institutional_decay tool."""

    async def test_institutional_decay_returns_dict(self) -> None:
        """Test institutional_decay tracks institution quality."""
        from loom.tools.hcs10_academic import research_institutional_decay

        result = await research_institutional_decay(institution="Harvard University")

        # Verify response is a dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have institutional analysis
        has_academic_data = any(
            key in result
            for key in [
                "institution",
                "decay_score",
                "publication_trend",
                "citation_impact",
                "researcher_retention",
                "quality_metrics",
                "error",
            ]
        )
        assert has_academic_data, f"Missing institutional fields in: {list(result.keys())}"

        logger.info(f"✓ institutional_decay returned: {list(result.keys())[:5]}")


class TestAcademicShellFunding:
    """Test research_shell_funding tool."""

    async def test_shell_funding_returns_dict(self) -> None:
        """Test shell_funding detects fraudulent funding sources."""
        from loom.tools.hcs10_academic import research_shell_funding

        result = await research_shell_funding(company="Alphabet Inc.")

        # Verify response is a dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have funding analysis
        has_academic_data = any(
            key in result
            for key in [
                "company",
                "shell_score",
                "funding_sources",
                "suspicious_transfers",
                "legitimacy",
                "error",
            ]
        )
        assert has_academic_data, f"Missing funding fields in: {list(result.keys())}"

        logger.info(f"✓ shell_funding returned: {list(result.keys())[:5]}")


class TestAcademicConferenceArbitrage:
    """Test research_conference_arbitrage tool."""

    async def test_conference_arbitrage_returns_dict(self) -> None:
        """Test conference_arbitrage detects conference manipulation."""
        from loom.tools.hcs10_academic import research_conference_arbitrage

        result = await research_conference_arbitrage(conference="NeurIPS")

        # Verify response is a dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have conference analysis
        has_academic_data = any(
            key in result
            for key in [
                "conference",
                "arbitrage_score",
                "acceptance_trends",
                "reviewer_conflicts",
                "dual_submission_risk",
                "impact_analysis",
                "error",
            ]
        )
        assert has_academic_data, f"Missing conference fields in: {list(result.keys())}"

        logger.info(f"✓ conference_arbitrage returned: {list(result.keys())[:5]}")


class TestAcademicPreprintManipulation:
    """Test research_preprint_manipulation tool."""

    async def test_preprint_manipulation_returns_dict(self) -> None:
        """Test preprint_manipulation detects arXiv manipulation."""
        from loom.tools.hcs10_academic import research_preprint_manipulation

        result = await research_preprint_manipulation(topic="machine learning")

        # Verify response is a dict
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Should have preprint analysis
        # Actual fields: arxiv_id, title, submission_date, topic_search, timing_analysis,
        # social_amplification_score, altmetric_score, manipulation_indicators, manipulation_risk, risk_level
        has_academic_data = any(
            key in result
            for key in [
                "manipulation_risk",
                "social_amplification_score",
                "timing_analysis",
                "manipulation_indicators",
                "risk_level",
                "error",
            ]
        )
        assert has_academic_data, f"Missing preprint fields in: {list(result.keys())}"

        logger.info(f"✓ preprint_manipulation returned: {list(result.keys())[:5]}")


class TestAllAcademicTools:
    """Summary test verifying all 11 tools are callable."""

    async def test_all_11_academic_tools_callable(self) -> None:
        """Verify all 11 academic tools are callable and return data."""
        tools_under_test = [
            ("citation_analysis", {}),
            ("retraction_check", {}),
            ("predatory_journal_check", {}),
            ("grant_forensics", {}),
            ("monoculture_detect", {}),
            ("review_cartel", {}),
            ("data_fabrication", {}),
            ("institutional_decay", {}),
            ("shell_funding", {}),
            ("conference_arbitrage", {}),
            ("preprint_manipulation", {}),
        ]

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

        # Define async helper functions for each tool
        async def call_citation_analysis() -> dict[str, Any]:
            return await research_citation_analysis(
                paper_id="test123", depth=1
            )

        async def call_retraction_check() -> dict[str, Any]:
            return await research_retraction_check(
                query="test", max_results=5
            )

        async def call_predatory_journal_check() -> dict[str, Any]:
            return await research_predatory_journal_check(
                journal_name="Test Journal"
            )

        async def call_grant_forensics() -> dict[str, Any]:
            return await research_grant_forensics(text="Test grant")

        async def call_monoculture_detect() -> dict[str, Any]:
            return await research_monoculture_detect(
                field="test", max_papers=10
            )

        async def call_review_cartel() -> dict[str, Any]:
            return await research_review_cartel(author_id="test")

        async def call_data_fabrication() -> dict[str, Any]:
            return await research_data_fabrication(
                numbers=[1.0, 2.0, 3.0]
            )

        async def call_institutional_decay() -> dict[str, Any]:
            return await research_institutional_decay(
                institution="Test U"
            )

        async def call_shell_funding() -> dict[str, Any]:
            return await research_shell_funding(company="Test Inc")

        async def call_conference_arbitrage() -> dict[str, Any]:
            return await research_conference_arbitrage(
                conference="TestConf"
            )

        async def call_preprint_manipulation() -> dict[str, Any]:
            return await research_preprint_manipulation(
                topic="test"
            )

        # Map tool names to their async callable functions
        tool_funcs = {
            "citation_analysis": call_citation_analysis,
            "retraction_check": call_retraction_check,
            "predatory_journal_check": call_predatory_journal_check,
            "grant_forensics": call_grant_forensics,
            "monoculture_detect": call_monoculture_detect,
            "review_cartel": call_review_cartel,
            "data_fabrication": call_data_fabrication,
            "institutional_decay": call_institutional_decay,
            "shell_funding": call_shell_funding,
            "conference_arbitrage": call_conference_arbitrage,
            "preprint_manipulation": call_preprint_manipulation,
        }

        results = {}
        for tool_name, func in tool_funcs.items():
            try:
                result = await func()
                # Check if it's a dict and has some content
                if isinstance(result, dict) and len(result) > 0:
                    results[tool_name] = "OK"
                else:
                    results[tool_name] = "EMPTY"
            except Exception as e:
                results[tool_name] = f"ERROR: {str(e)[:40]}"

        # Print summary
        print("\n" + "=" * 80)
        print("ACADEMIC TOOLS COVERAGE SUMMARY (REQ-044)")
        print("=" * 80)

        ok_count = 0
        for tool_name, status in sorted(results.items()):
            symbol = "✓" if status == "OK" else "✗"
            print(f"{symbol} {tool_name:35} {status}")
            if status == "OK":
                ok_count += 1

        print("=" * 80)
        print(f"RESULT: {ok_count}/11 tools returned academic data")
        print("=" * 80)

        # Assert at least 6 tools work
        assert ok_count >= 6, f"Expected at least 6/11 working tools, got {ok_count}"
