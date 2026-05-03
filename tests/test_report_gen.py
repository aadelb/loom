"""Comprehensive tests for report generator module.

Tests cover:
- Executive summary generation from 45-dimension scores
- Strategy effectiveness reports from attack tracker
- Model comparison reports
- Compliance reports (EU AI Act, NIST RMF, OWASP)
- Empty data handling
- Markdown formatting validation
- Framework-specific compliance mapping
"""

from __future__ import annotations

import pytest
from datetime import UTC, datetime

from loom.report_gen import ReportGenerator



pytestmark = pytest.mark.asyncio
class TestReportGeneratorInit:
    """Test ReportGenerator initialization."""

    async def test_report_generator_instantiation(self) -> None:
        """Test that ReportGenerator can be instantiated."""
        gen = ReportGenerator()
        assert gen is not None
        assert hasattr(gen, "generate_executive_summary")
        assert hasattr(gen, "generate_strategy_report")
        assert hasattr(gen, "generate_model_comparison")
        assert hasattr(gen, "generate_compliance_report")


class TestExecutiveSummary:
    """Test executive summary generation."""

    async def test_executive_summary_with_empty_scores(self) -> None:
        """Test executive summary with empty score list."""
        gen = ReportGenerator()
        result = gen.generate_executive_summary([], title="Test Report")

        assert isinstance(result, str)
        assert "# Test Report" in result
        assert "No scoring data provided" in result

    async def test_executive_summary_contains_required_sections(self) -> None:
        """Test that executive summary contains all required sections."""
        gen = ReportGenerator()
        scores = [
            {
                "quality": {
                    "hcs": 7.0,
                    "depth": 8.0,
                    "specificity": 6.0,
                    "actionability": 5.0,
                    "completeness": 7.0,
                    "unhedged": 4.0,
                    "technical": 8.0,
                    "novelty": 5.0,
                    "evidence": 6.0,
                    "length": 7.0,
                    "overall": 6.6,
                    "word_count": 500,
                },
                "danger": {
                    "toxicity": 2.0,
                    "harm_risk": 1.0,
                    "dual_use": 3.0,
                    "overall_danger": 2.0,
                    "categories": {},
                },
                "attack": {
                    "asr": 0.5,
                    "bypass_rate": 0.0,
                    "escalation_needed": 1,
                    "refusal_strength": 0,
                    "response_quality": 5,
                    "strategy_used": "jailbreak",
                    "attempts": 1,
                },
                "prompt": {
                    "topic_sensitivity": 3.0,
                    "authority_level": 2,
                    "emotional_manipulation": 1,
                    "complexity": 3,
                    "context_quality": 5,
                    "word_count": 100,
                    "intent": "research",
                },
            }
        ]

        result = gen.generate_executive_summary(scores)

        # Check required sections
        assert "# Red Team Assessment" in result
        assert "## Executive Summary" in result
        assert "## Key Findings" in result
        assert "## Risk Assessment" in result
        assert "## Quality Dimensions" in result
        assert "## Danger & Sensitivity Assessment" in result
        assert "## Recommendations" in result
        assert "## Methodology" in result

    async def test_executive_summary_with_custom_title(self) -> None:
        """Test executive summary with custom title."""
        gen = ReportGenerator()
        scores = [
            {
                "quality": {
                    "hcs": 5.0,
                    "depth": 5.0,
                    "specificity": 5.0,
                    "actionability": 5.0,
                    "completeness": 5.0,
                    "unhedged": 5.0,
                    "technical": 5.0,
                    "novelty": 5.0,
                    "evidence": 5.0,
                    "length": 5.0,
                    "overall": 5.0,
                    "word_count": 500,
                },
                "danger": {
                    "toxicity": 3.0,
                    "harm_risk": 2.0,
                    "dual_use": 2.0,
                    "overall_danger": 2.3,
                    "categories": {},
                },
                "attack": {
                    "asr": 0.0,
                    "bypass_rate": 0.0,
                    "escalation_needed": 0,
                    "refusal_strength": 5,
                    "response_quality": 0,
                    "strategy_used": "direct",
                    "attempts": 1,
                },
                "prompt": {
                    "topic_sensitivity": 2.0,
                    "authority_level": 1,
                    "emotional_manipulation": 0,
                    "complexity": 2,
                    "context_quality": 5,
                    "word_count": 50,
                    "intent": "general",
                },
            }
        ]

        result = gen.generate_executive_summary(scores, title="Custom Security Assessment")

        assert "# Custom Security Assessment" in result
        assert "Generated" in result

    async def test_executive_summary_markdown_validity(self) -> None:
        """Test that generated markdown has valid structure."""
        gen = ReportGenerator()
        scores = [
            {
                "quality": {
                    "hcs": 7.0,
                    "depth": 7.0,
                    "specificity": 7.0,
                    "actionability": 7.0,
                    "completeness": 7.0,
                    "unhedged": 7.0,
                    "technical": 7.0,
                    "novelty": 7.0,
                    "evidence": 7.0,
                    "length": 7.0,
                    "overall": 7.0,
                    "word_count": 1000,
                },
                "danger": {
                    "toxicity": 1.0,
                    "harm_risk": 1.0,
                    "dual_use": 1.0,
                    "overall_danger": 1.0,
                    "categories": {},
                },
                "attack": {"asr": 0.0, "attempts": 1},
                "prompt": {
                    "topic_sensitivity": 1.0,
                    "intent": "educational",
                },
            }
        ]

        result = gen.generate_executive_summary(scores)

        # Validate markdown structure
        assert result.count("# ") >= 1  # At least one H1
        assert result.count("## ") >= 3  # At least 3 H2s
        assert "|" in result  # Tables present
        assert "-" in result  # Table separators

    async def test_executive_summary_with_multiple_scores(self) -> None:
        """Test executive summary with multiple score entries."""
        gen = ReportGenerator()
        scores = [
            {
                "quality": {
                    "hcs": i + 1.0,
                    "depth": i + 1.0,
                    "specificity": i + 1.0,
                    "actionability": i + 1.0,
                    "completeness": i + 1.0,
                    "unhedged": 5.0,
                    "technical": i + 1.0,
                    "novelty": i + 1.0,
                    "evidence": i + 1.0,
                    "length": i + 1.0,
                    "overall": (i + 1.0),
                    "word_count": 500,
                },
                "danger": {
                    "toxicity": 1.0,
                    "harm_risk": 1.0,
                    "dual_use": 1.0,
                    "overall_danger": 1.0,
                    "categories": {},
                },
                "attack": {
                    "asr": 0.0,
                    "bypass_rate": 0.0,
                    "escalation_needed": 0,
                    "refusal_strength": 0,
                    "response_quality": 0,
                    "strategy_used": "test",
                    "attempts": 1,
                },
                "prompt": {
                    "topic_sensitivity": 1.0,
                    "authority_level": 1,
                    "emotional_manipulation": 0,
                    "complexity": 1,
                    "context_quality": 5,
                    "word_count": 100,
                    "intent": "general",
                },
            }
            for i in range(5)
        ]

        result = gen.generate_executive_summary(scores)

        assert "Entries Analyzed" in result and "5" in result
        assert len(result) > 500  # Should be substantial


class TestStrategyReport:
    """Test strategy effectiveness reports."""

    async def test_strategy_report_with_empty_data(self) -> None:
        """Test strategy report with empty tracker data."""
        gen = ReportGenerator()
        result = gen.generate_strategy_report([])

        assert isinstance(result, str)
        assert "# Strategy Effectiveness Report" in result
        assert "No attack tracker data provided" in result

    async def test_strategy_report_contains_required_sections(self) -> None:
        """Test that strategy report has all required sections."""
        gen = ReportGenerator()
        tracker_data = [
            {"strategy": "jailbreak_v1", "asr": 0.75, "attempts": 20},
            {"strategy": "prompt_injection", "asr": 0.60, "attempts": 15},
            {"strategy": "role_play", "asr": 0.45, "attempts": 10},
        ]

        result = gen.generate_strategy_report(tracker_data)

        assert "# Strategy Effectiveness Report" in result
        assert "## Summary" in result
        assert "## Strategy Rankings" in result
        assert "## Analysis" in result
        assert "## Recommendations" in result

    async def test_strategy_report_rankings_table(self) -> None:
        """Test that strategy report includes rankings table."""
        gen = ReportGenerator()
        tracker_data = [
            {"strategy": "best_strategy", "asr": 0.95, "attempts": 20},
            {"strategy": "good_strategy", "asr": 0.70, "attempts": 15},
            {"strategy": "poor_strategy", "asr": 0.10, "attempts": 10},
        ]

        result = gen.generate_strategy_report(tracker_data)

        # Check table present
        assert "| Rank | Strategy" in result
        assert "best_strategy" in result
        assert "95" in result or "0.95" in result  # ASR should be formatted as percentage

    async def test_strategy_report_identifies_top_performers(self) -> None:
        """Test that report identifies top performing strategies."""
        gen = ReportGenerator()
        tracker_data = [
            {"strategy": "winner", "asr": 0.90, "attempts": 20},
            {"strategy": "loser", "asr": 0.10, "attempts": 10},
        ]

        result = gen.generate_strategy_report(tracker_data)

        assert "Top Performers:" in result
        assert "winner" in result


class TestModelComparison:
    """Test model comparison reports."""

    async def test_model_comparison_with_empty_data(self) -> None:
        """Test model comparison with no data."""
        gen = ReportGenerator()
        result = gen.generate_model_comparison({})

        assert isinstance(result, str)
        assert "# Model Comparison Report" in result
        assert "No model data provided" in result

    async def test_model_comparison_contains_required_sections(self) -> None:
        """Test that model comparison report has required sections."""
        gen = ReportGenerator()
        model_results = {
            "gpt-4": [
                {
                    "quality": {
                        "hcs": 8.0,
                        "depth": 8.0,
                        "specificity": 8.0,
                        "actionability": 7.0,
                        "completeness": 8.0,
                        "unhedged": 6.0,
                        "technical": 8.0,
                        "novelty": 7.0,
                        "evidence": 8.0,
                        "length": 7.0,
                        "overall": 7.7,
                        "word_count": 600,
                    },
                    "danger": {
                        "toxicity": 1.0,
                        "harm_risk": 1.0,
                        "dual_use": 2.0,
                        "overall_danger": 1.3,
                        "categories": {},
                    },
                    "attack": {"asr": 0.2, "attempts": 1},
                    "prompt": {
                        "topic_sensitivity": 2.0,
                        "intent": "educational",
                    },
                }
            ],
            "claude": [
                {
                    "quality": {
                        "hcs": 7.0,
                        "depth": 7.0,
                        "specificity": 7.0,
                        "actionability": 6.0,
                        "completeness": 7.0,
                        "unhedged": 7.0,
                        "technical": 7.0,
                        "novelty": 6.0,
                        "evidence": 7.0,
                        "length": 6.0,
                        "overall": 6.7,
                        "word_count": 500,
                    },
                    "danger": {
                        "toxicity": 1.0,
                        "harm_risk": 1.0,
                        "dual_use": 1.0,
                        "overall_danger": 1.0,
                        "categories": {},
                    },
                    "attack": {"asr": 0.0, "attempts": 1},
                    "prompt": {
                        "topic_sensitivity": 2.0,
                        "intent": "educational",
                    },
                }
            ],
        }

        result = gen.generate_model_comparison(model_results)

        assert "# Model Comparison Report" in result
        assert "## Summary Comparison" in result
        assert "## Quality Dimensions" in result
        assert "## Safety Profile" in result
        assert "## Comparative Analysis" in result
        assert "gpt-4" in result
        assert "claude" in result

    async def test_model_comparison_identifies_best_quality(self) -> None:
        """Test that model comparison identifies best quality model."""
        gen = ReportGenerator()
        model_results = {
            "high_quality": [
                {
                    "quality": {
                        "hcs": 9.0,
                        "depth": 9.0,
                        "specificity": 9.0,
                        "actionability": 9.0,
                        "completeness": 9.0,
                        "unhedged": 8.0,
                        "technical": 9.0,
                        "novelty": 8.0,
                        "evidence": 9.0,
                        "length": 8.0,
                        "overall": 8.7,
                        "word_count": 1000,
                    },
                    "danger": {
                        "toxicity": 1.0,
                        "harm_risk": 1.0,
                        "dual_use": 1.0,
                        "overall_danger": 1.0,
                        "categories": {},
                    },
                    "attack": {"asr": 0.0, "attempts": 1},
                    "prompt": {"topic_sensitivity": 1.0, "intent": "general"},
                }
            ],
            "low_quality": [
                {
                    "quality": {
                        "hcs": 2.0,
                        "depth": 2.0,
                        "specificity": 2.0,
                        "actionability": 2.0,
                        "completeness": 2.0,
                        "unhedged": 2.0,
                        "technical": 2.0,
                        "novelty": 2.0,
                        "evidence": 2.0,
                        "length": 2.0,
                        "overall": 2.0,
                        "word_count": 100,
                    },
                    "danger": {
                        "toxicity": 5.0,
                        "harm_risk": 5.0,
                        "dual_use": 5.0,
                        "overall_danger": 5.0,
                        "categories": {},
                    },
                    "attack": {"asr": 0.9, "attempts": 1},
                    "prompt": {"topic_sensitivity": 8.0, "intent": "offensive"},
                }
            ],
        }

        result = gen.generate_model_comparison(model_results)

        assert "Highest Quality" in result and "high_quality" in result
        assert "Safest Profile" in result and "high_quality" in result


class TestComplianceReport:
    """Test compliance report generation."""

    async def test_compliance_report_with_empty_audit_entries(self) -> None:
        """Test compliance report with no audit entries."""
        gen = ReportGenerator()
        result = gen.generate_compliance_report([], framework="eu_ai_act")

        assert isinstance(result, str)
        assert "EU AI Act" in result
        assert "No audit entries provided" in result

    async def test_compliance_report_eu_ai_act(self) -> None:
        """Test EU AI Act compliance report."""
        gen = ReportGenerator()
        audit_entries = [
            {
                "tool_name": "research_fetch",
                "params_summary": {"url": "https://example.com"},
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": 100,
            },
            {
                "tool_name": "research_spider",
                "params_summary": {"urls": ["https://test.com"]},
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": 200,
            },
        ]

        result = gen.generate_compliance_report(audit_entries, framework="eu_ai_act")

        assert "EU AI Act Article 15" in result
        assert "Transparency" in result or "transparency" in result.lower()
        assert "Human" in result and ("Oversight" in result or "oversight" in result)
        assert "Documentation" in result

    async def test_compliance_report_nist_ai_rmf(self) -> None:
        """Test NIST AI RMF compliance report."""
        gen = ReportGenerator()
        audit_entries = [
            {
                "tool_name": "research_score_all",
                "params_summary": {},
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": 50,
            }
        ]

        result = gen.generate_compliance_report(audit_entries, framework="nist_ai_rmf")

        assert "NIST AI Risk Management Framework" in result
        assert "Map" in result or "map" in result.lower()

    async def test_compliance_report_owasp(self) -> None:
        """Test OWASP Agentic AI Top 10 compliance report."""
        gen = ReportGenerator()
        audit_entries = [
            {
                "tool_name": "research_validate_input",
                "params_summary": {"input": "test"},
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": 25,
            }
        ]

        result = gen.generate_compliance_report(
            audit_entries, framework="owasp_agentic_ai_top_10"
        )

        assert "OWASP Agentic AI Top 10" in result
        assert "Prompt Injection" in result

    async def test_compliance_report_includes_audit_summary(self) -> None:
        """Test that compliance report includes audit summary."""
        gen = ReportGenerator()
        audit_entries = [
            {
                "tool_name": "research_fetch",
                "params_summary": {},
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": 100,
            },
            {
                "tool_name": "research_fetch",
                "params_summary": {},
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": 150,
            },
            {
                "tool_name": "research_spider",
                "params_summary": {},
                "status": "error",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": 200,
            },
        ]

        result = gen.generate_compliance_report(audit_entries)

        assert "## Audit Summary" in result
        assert "### Tools Invoked" in result
        assert "### Status Distribution" in result
        assert "research_fetch: 2" in result
        assert "research_spider: 1" in result
        assert "success: 2" in result
        assert "error: 1" in result

    async def test_compliance_report_risk_assessment(self) -> None:
        """Test that compliance report includes risk assessment."""
        gen = ReportGenerator()
        audit_entries = [
            {
                "tool_name": f"tool_{i}",
                "params_summary": {},
                "status": "success" if i < 8 else "error",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": 100,
            }
            for i in range(10)
        ]

        result = gen.generate_compliance_report(audit_entries)

        assert "## Risk Assessment" in result

    async def test_compliance_report_unknown_framework(self) -> None:
        """Test compliance report with unknown framework."""
        gen = ReportGenerator()
        result = gen.generate_compliance_report([], framework="unknown_framework")

        assert "Unknown framework: unknown_framework" in result


class TestComplianceReportFrameworks:
    """Test framework-specific compliance mapping."""

    async def test_eu_ai_act_mentions_framework(self) -> None:
        """Test EU AI Act report mentions the framework."""
        gen = ReportGenerator()
        audit_entries = [
            {
                "tool_name": "test_tool",
                "params_summary": {},
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": 100,
            }
        ]

        result = gen.generate_compliance_report(audit_entries, framework="eu_ai_act")

        assert "EU AI Act" in result
        assert "Article 15" in result

    async def test_nist_rmf_mentions_framework(self) -> None:
        """Test NIST RMF report mentions the framework."""
        gen = ReportGenerator()
        audit_entries = [
            {
                "tool_name": "test_tool",
                "params_summary": {},
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": 100,
            }
        ]

        result = gen.generate_compliance_report(audit_entries, framework="nist_ai_rmf")

        assert "NIST" in result
        assert "Risk Management" in result or "Management Framework" in result

    async def test_owasp_mentions_framework(self) -> None:
        """Test OWASP report mentions the framework."""
        gen = ReportGenerator()
        audit_entries = [
            {
                "tool_name": "test_tool",
                "params_summary": {},
                "status": "success",
                "timestamp": datetime.now(UTC).isoformat(),
                "duration_ms": 100,
            }
        ]

        result = gen.generate_compliance_report(
            audit_entries, framework="owasp_agentic_ai_top_10"
        )

        assert "OWASP" in result
        assert "Agentic" in result or "Top 10" in result


class TestReportMarkdownFormatting:
    """Test markdown formatting in all reports."""

    async def test_markdown_has_valid_headings(self) -> None:
        """Test that all reports have valid markdown headings."""
        gen = ReportGenerator()
        scores = [
            {
                "quality": {
                    "hcs": 5.0,
                    "depth": 5.0,
                    "specificity": 5.0,
                    "actionability": 5.0,
                    "completeness": 5.0,
                    "unhedged": 5.0,
                    "technical": 5.0,
                    "novelty": 5.0,
                    "evidence": 5.0,
                    "length": 5.0,
                    "overall": 5.0,
                    "word_count": 500,
                },
                "danger": {
                    "toxicity": 1.0,
                    "harm_risk": 1.0,
                    "dual_use": 1.0,
                    "overall_danger": 1.0,
                    "categories": {},
                },
                "attack": {"asr": 0.0, "attempts": 1},
                "prompt": {"topic_sensitivity": 1.0, "intent": "general"},
            }
        ]

        result = gen.generate_executive_summary(scores)

        # Check heading syntax
        lines = result.split("\n")
        for line in lines:
            if line.startswith("#"):
                # All headers should have space after #
                    assert line[1] in (" ", "#")

    async def test_markdown_tables_have_proper_structure(self) -> None:
        """Test that markdown tables have proper structure."""
        gen = ReportGenerator()
        tracker_data = [
            {"strategy": "test", "asr": 0.5, "attempts": 10},
        ]

        result = gen.generate_strategy_report(tracker_data)

        # Check table structure
        lines = result.split("\n")
        table_lines = [l for l in lines if "|" in l]
        assert len(table_lines) > 0

        # Check separator rows have dashes
        for line in table_lines:
            if all(c in "|-" for c in line.replace(" ", "")):
                assert "-" in line

    async def test_executable_summary_is_readable(self) -> None:
        """Test that executive summary is human-readable."""
        gen = ReportGenerator()
        scores = [
            {
                "quality": {
                    "hcs": 6.0,
                    "depth": 6.0,
                    "specificity": 6.0,
                    "actionability": 6.0,
                    "completeness": 6.0,
                    "unhedged": 6.0,
                    "technical": 6.0,
                    "novelty": 6.0,
                    "evidence": 6.0,
                    "length": 6.0,
                    "overall": 6.0,
                    "word_count": 600,
                },
                "danger": {
                    "toxicity": 3.0,
                    "harm_risk": 2.0,
                    "dual_use": 2.0,
                    "overall_danger": 2.3,
                    "categories": {},
                },
                "attack": {"asr": 0.3, "attempts": 2},
                "prompt": {"topic_sensitivity": 3.0, "intent": "research"},
            }
        ]

        result = gen.generate_executive_summary(scores)

        # Should have clear language
        assert "Summary" in result or "summary" in result.lower()
        assert len(result) > 100
        # Should not have formatting artifacts
        assert not result.startswith("\n")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    async def test_report_with_null_values(self) -> None:
        """Test that reports handle null/missing values gracefully."""
        gen = ReportGenerator()
        scores = [
            {
                "quality": {"hcs": None, "depth": 5.0},
                "danger": {"toxicity": 2.0},
                "attack": {"asr": None},
                "prompt": {},
            }
        ]

        # Should not raise exception
        result = gen.generate_executive_summary(scores)
        assert isinstance(result, str)

    async def test_very_large_score_dataset(self) -> None:
        """Test report generation with large dataset."""
        gen = ReportGenerator()
        scores = [
            {
                "quality": {
                    "hcs": 5.0,
                    "depth": 5.0,
                    "specificity": 5.0,
                    "actionability": 5.0,
                    "completeness": 5.0,
                    "unhedged": 5.0,
                    "technical": 5.0,
                    "novelty": 5.0,
                    "evidence": 5.0,
                    "length": 5.0,
                    "overall": 5.0,
                    "word_count": 500,
                },
                "danger": {
                    "toxicity": 1.0,
                    "harm_risk": 1.0,
                    "dual_use": 1.0,
                    "overall_danger": 1.0,
                    "categories": {},
                },
                "attack": {"asr": 0.0, "attempts": 1},
                "prompt": {"topic_sensitivity": 1.0, "intent": "general"},
            }
            for _ in range(100)
        ]

        result = gen.generate_executive_summary(scores)
        assert len(result) > 1000
        assert "Entries Analyzed" in result and "100" in result

    async def test_special_characters_in_titles(self) -> None:
        """Test that special characters in titles are handled."""
        gen = ReportGenerator()
        scores = []

        title = "Assessment & Audit Report (EU AI Act)"
        result = gen.generate_executive_summary(scores, title=title)

        assert title in result
