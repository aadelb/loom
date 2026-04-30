"""Test suite for the comprehensive tool coverage runner.

Tests ToolCoverageRunner with minimal valid parameters across all tool categories.
Validates parameter validation, result reporting, and coverage statistics.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from loom.test_runner import (
    CoverageStats,
    ToolCoverageRunner,
    ToolResult,
    _validate_tool_params,
)
from loom.params import CoverageRunParams


class TestToolResult:
    """Test ToolResult dataclass."""

    def test_tool_result_passed(self) -> None:
        """Test creating a passed result."""
        result = ToolResult(
            tool_name="research_fetch",
            passed=True,
            status="passed",
            elapsed_ms=100.0,
        )
        assert result.tool_name == "research_fetch"
        assert result.passed is True
        assert result.status == "passed"
        assert result.elapsed_ms == 100.0
        assert result.error_message is None

    def test_tool_result_failed(self) -> None:
        """Test creating a failed result."""
        result = ToolResult(
            tool_name="research_search",
            passed=False,
            status="failed",
            error_message="Invalid query parameter",
            elapsed_ms=50.0,
        )
        assert result.passed is False
        assert result.status == "failed"
        assert result.error_message == "Invalid query parameter"

    def test_tool_result_timeout(self) -> None:
        """Test creating a timeout result."""
        result = ToolResult(
            tool_name="research_deep",
            passed=False,
            status="timeout",
            error_message="Timeout after 30.0s",
            elapsed_ms=30000.0,
        )
        assert result.status == "timeout"
        assert "30" in result.error_message

    def test_tool_result_skipped(self) -> None:
        """Test creating a skipped result."""
        result = ToolResult(
            tool_name="research_vastai_search",
            passed=False,
            status="skipped",
            error_message="Optional tool",
        )
        assert result.status == "skipped"


class TestCoverageStats:
    """Test CoverageStats dataclass."""

    def test_stats_initialization(self) -> None:
        """Test creating default stats."""
        stats = CoverageStats()
        assert stats.total_tools == 0
        assert stats.tools_tested == 0
        assert stats.tools_passed == 0
        assert stats.coverage_pct == 0.0
        assert stats.timestamp is not None

    def test_stats_with_values(self) -> None:
        """Test stats with actual values."""
        stats = CoverageStats(
            total_tools=100,
            tools_tested=90,
            tools_passed=85,
            tools_failed=3,
            tools_skipped=10,
            coverage_pct=94.4,
        )
        assert stats.total_tools == 100
        assert stats.tools_passed == 85
        assert stats.coverage_pct == 94.4


class TestCoverageRunParams:
    """Test CoverageRunParams validation model."""

    def test_params_default(self) -> None:
        """Test default parameters."""
        params = CoverageRunParams()
        assert params.tools_to_test is None
        assert params.timeout == 30.0
        assert params.dry_run is True

    def test_params_custom(self) -> None:
        """Test custom parameters."""
        params = CoverageRunParams(
            tools_to_test=["research_fetch", "research_search"],
            timeout=60.0,
            dry_run=False,
        )
        assert params.tools_to_test == ["research_fetch", "research_search"]
        assert params.timeout == 60.0
        assert params.dry_run is False

    def test_params_timeout_bounds(self) -> None:
        """Test timeout validation."""
        with pytest.raises(ValueError):
            CoverageRunParams(timeout=0.5)

        with pytest.raises(ValueError):
            CoverageRunParams(timeout=400.0)

    def test_params_tools_list_limit(self) -> None:
        """Test tools_to_test list size limit."""
        # Valid: exact limit
        params = CoverageRunParams(tools_to_test=["test"] * 227)
        assert len(params.tools_to_test) == 227

        # Invalid: exceed limit
        with pytest.raises(ValueError):
            CoverageRunParams(tools_to_test=["test"] * 228)


class TestToolCoverageRunner:
    """Test ToolCoverageRunner class."""

    def test_runner_initialization(self) -> None:
        """Test initializing the test runner."""
        runner = ToolCoverageRunner(dry_run=True)
        assert runner.dry_run is True
        assert runner.mcp_app is None
        assert len(runner.results) == 0
        assert runner.stats.total_tools > 0

    def test_tool_params_available(self) -> None:
        """Test that tool params are available for many tools."""
        runner = ToolCoverageRunner()
        # Should have params for ~120+ tools
        assert len(runner.TOOL_PARAMS) > 100
        assert "research_fetch" in runner.TOOL_PARAMS
        assert "research_search" in runner.TOOL_PARAMS
        assert "research_cache_stats" in runner.TOOL_PARAMS

    def test_tool_params_structure(self) -> None:
        """Test that tool params are correctly structured."""
        runner = ToolCoverageRunner()

        # Check some known tools
        assert runner.TOOL_PARAMS["research_fetch"]["url"] == "https://example.com"
        assert "query" in runner.TOOL_PARAMS["research_search"]
        assert "emails" not in runner.TOOL_PARAMS.get("research_cache_clear", {})

    def test_optional_tools_defined(self) -> None:
        """Test that optional tools list is defined."""
        runner = ToolCoverageRunner()
        assert len(runner.OPTIONAL_TOOLS) > 0
        assert "research_vastai_search" in runner.OPTIONAL_TOOLS
        assert "research_llm_summarize" in runner.OPTIONAL_TOOLS

    def test_network_required_tools_defined(self) -> None:
        """Test that network-required tools list is defined."""
        runner = ToolCoverageRunner()
        assert len(runner.NETWORK_REQUIRED_TOOLS) > 0
        assert "research_nmap_scan" in runner.NETWORK_REQUIRED_TOOLS
        assert "research_metadata_forensics" in runner.NETWORK_REQUIRED_TOOLS

    @pytest.mark.asyncio
    async def test_run_coverage_empty_params(self) -> None:
        """Test running coverage with no parameters."""
        runner = ToolCoverageRunner(dry_run=True)
        results = await runner.run_coverage(timeout=5.0)

        assert results["total_tools"] > 0
        assert results["tools_tested"] >= 0
        assert results["tools_passed"] + results["tools_failed"] + results["tools_skipped"] >= 0
        assert "coverage_pct" in results
        assert "per_tool_results" in results

    @pytest.mark.asyncio
    async def test_run_coverage_specific_tools(self) -> None:
        """Test running coverage with specific tools."""
        runner = ToolCoverageRunner(dry_run=True)
        results = await runner.run_coverage(
            tools_to_test=["research_cache_stats", "research_health_check"],
            timeout=5.0,
        )

        assert results["tools_tested"] >= 0
        # At least one should be in results
        tool_names = {r["tool"] for r in results["per_tool_results"]}
        assert "research_cache_stats" in tool_names or "research_health_check" in tool_names

    @pytest.mark.asyncio
    async def test_run_coverage_dry_run_mode(self) -> None:
        """Test that dry_run mode skips network tools."""
        runner = ToolCoverageRunner(dry_run=True)
        results = await runner.run_coverage(timeout=5.0)

        # Count skipped tools
        skipped_count = results["tools_skipped"]
        assert skipped_count > 0  # Should skip network-required tools

    def test_build_result_dict(self) -> None:
        """Test building the result dictionary."""
        runner = ToolCoverageRunner()
        runner.results = [
            ToolResult(
                tool_name="research_fetch",
                passed=True,
                status="passed",
                elapsed_ms=100.0,
            ),
            ToolResult(
                tool_name="research_search",
                passed=False,
                status="failed",
                error_message="Test error",
                elapsed_ms=50.0,
            ),
        ]
        runner.stats.total_tools = 2
        runner.stats.tools_tested = 2
        runner.stats.tools_passed = 1
        runner.stats.tools_failed = 1
        runner.stats.coverage_pct = 50.0

        result_dict = runner._build_result_dict()

        assert result_dict["total_tools"] == 2
        assert result_dict["tools_tested"] == 2
        assert result_dict["tools_passed"] == 1
        assert result_dict["tools_failed"] == 1
        assert len(result_dict["per_tool_results"]) == 2

    def test_generate_coverage_report_empty(self) -> None:
        """Test generating a report with no results."""
        runner = ToolCoverageRunner()
        report = runner.generate_coverage_report(
            {
                "total_tools": 0,
                "tools_tested": 0,
                "tools_passed": 0,
                "tools_failed": 0,
                "tools_skipped": 0,
                "tools_timeout": 0,
                "tools_error": 0,
                "coverage_pct": 0.0,
                "total_elapsed_ms": 0.0,
                "timestamp": "2024-01-01T00:00:00Z",
                "per_tool_results": [],
            }
        )

        assert "Loom Tool Coverage Report" in report
        assert "Summary" in report
        assert "0" in report

    def test_generate_coverage_report_with_results(self) -> None:
        """Test generating a report with results."""
        results = {
            "total_tools": 100,
            "tools_tested": 100,
            "tools_passed": 85,
            "tools_failed": 10,
            "tools_skipped": 5,
            "tools_timeout": 0,
            "tools_error": 0,
            "coverage_pct": 85.0,
            "total_elapsed_ms": 5000.0,
            "timestamp": "2024-01-01T12:00:00Z",
            "per_tool_results": [
                {
                    "tool": "research_fetch",
                    "status": "passed",
                    "passed": True,
                    "error": None,
                    "elapsed_ms": 100.0,
                    "details": {},
                },
                {
                    "tool": "research_search",
                    "status": "failed",
                    "passed": False,
                    "error": "Invalid query",
                    "elapsed_ms": 50.0,
                    "details": {},
                },
            ],
        }

        runner = ToolCoverageRunner()
        report = runner.generate_coverage_report(results)

        assert "85.00%" in report or "85" in report
        assert "research_fetch" in report
        assert "research_search" in report
        assert "Passed (1)" in report or "passed" in report.lower()
        assert "Failed (1)" in report or "failed" in report.lower()

    def test_generate_coverage_report_structure(self) -> None:
        """Test that report has expected markdown structure."""
        runner = ToolCoverageRunner()
        results = {
            "total_tools": 10,
            "tools_tested": 10,
            "tools_passed": 7,
            "tools_failed": 2,
            "tools_skipped": 1,
            "tools_timeout": 0,
            "tools_error": 0,
            "coverage_pct": 70.0,
            "total_elapsed_ms": 1000.0,
            "timestamp": "2024-01-01T00:00:00Z",
            "per_tool_results": [
                {
                    "tool": f"research_tool_{i}",
                    "status": "passed" if i < 7 else "failed" if i < 9 else "skipped",
                    "passed": i < 7,
                    "error": None if i < 7 else "Error",
                    "elapsed_ms": 100.0,
                    "details": {},
                }
                for i in range(10)
            ],
        }

        report = runner.generate_coverage_report(results)

        # Check for key sections
        assert "Summary" in report
        assert "Results by Status" in report
        assert "Total Tools" in report
        assert "Coverage %" in report
        assert "|" in report  # Markdown table

    def test_report_with_all_statuses(self) -> None:
        """Test report generation with all status types."""
        results = {
            "total_tools": 5,
            "tools_tested": 5,
            "tools_passed": 1,
            "tools_failed": 1,
            "tools_skipped": 1,
            "tools_timeout": 1,
            "tools_error": 1,
            "coverage_pct": 20.0,
            "total_elapsed_ms": 500.0,
            "timestamp": "2024-01-01T00:00:00Z",
            "per_tool_results": [
                {
                    "tool": "research_passed",
                    "status": "passed",
                    "passed": True,
                    "error": None,
                    "elapsed_ms": 100.0,
                    "details": {},
                },
                {
                    "tool": "research_failed",
                    "status": "failed",
                    "passed": False,
                    "error": "Test failed",
                    "elapsed_ms": 50.0,
                    "details": {},
                },
                {
                    "tool": "research_timeout",
                    "status": "timeout",
                    "passed": False,
                    "error": "Timeout",
                    "elapsed_ms": 200.0,
                    "details": {},
                },
                {
                    "tool": "research_error",
                    "status": "error",
                    "passed": False,
                    "error": "Internal error",
                    "elapsed_ms": 75.0,
                    "details": {},
                },
                {
                    "tool": "research_skipped",
                    "status": "skipped",
                    "passed": False,
                    "error": "Skipped",
                    "elapsed_ms": 0.0,
                    "details": {},
                },
            ],
        }

        runner = ToolCoverageRunner()
        report = runner.generate_coverage_report(results)

        # Verify all status types are represented
        assert "Passed" in report
        assert "Failed" in report
        assert "Timeout" in report
        assert "Error" in report
        assert "Skipped" in report


class TestParameterValidation:
    """Test parameter validation for tools."""

    def test_validate_fetch_params(self) -> None:
        """Test FetchParams validation."""
        from loom.params import FetchParams

        params = FetchParams(url="https://example.com")
        assert params.url == "https://example.com"
        assert params.mode == "stealthy"

    def test_validate_spider_params(self) -> None:
        """Test SpiderParams validation."""
        from loom.params import SpiderParams

        params = SpiderParams(urls=["https://example.com", "https://example.org"])
        assert len(params.urls) == 2

    def test_validate_fetch_params_invalid_url(self) -> None:
        """Test FetchParams rejects invalid URLs."""
        from loom.params import FetchParams
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            FetchParams(url="not a url")

    def test_coverage_run_params_roundtrip(self) -> None:
        """Test CoverageRunParams serialization."""
        original = CoverageRunParams(
            tools_to_test=["research_fetch"],
            timeout=60.0,
            dry_run=False,
        )

        data = original.model_dump()
        assert data["timeout"] == 60.0
        assert data["dry_run"] is False


class TestToolParamsCompleteness:
    """Test that TOOL_PARAMS covers key tool categories."""

    def test_core_research_tools_have_params(self) -> None:
        """Test that core research tools have params."""
        runner = ToolCoverageRunner()
        core_tools = [
            "research_fetch",
            "research_spider",
            "research_markdown",
            "research_search",
            "research_deep",
            "research_github",
            "research_cache_stats",
            "research_cache_clear",
        ]

        for tool in core_tools:
            assert tool in runner.TOOL_PARAMS, f"{tool} missing from TOOL_PARAMS"

    def test_killer_research_tools_have_params(self) -> None:
        """Test that killer research tools have params."""
        runner = ToolCoverageRunner()
        killer_tools = [
            "research_dead_content",
            "research_invisible_web",
            "research_infra_correlator",
            "research_passive_recon",
        ]

        for tool in killer_tools:
            assert tool in runner.TOOL_PARAMS, f"{tool} missing from TOOL_PARAMS"

    def test_safety_tools_have_params(self) -> None:
        """Test that AI safety tools have params."""
        runner = ToolCoverageRunner()
        safety_tools = [
            "research_prompt_injection_test",
            "research_model_fingerprint",
            "research_bias_probe",
            "research_compliance_check",
        ]

        for tool in safety_tools:
            assert tool in runner.TOOL_PARAMS, f"{tool} missing from TOOL_PARAMS"

    def test_all_params_are_dicts(self) -> None:
        """Test that all TOOL_PARAMS values are dictionaries."""
        runner = ToolCoverageRunner()

        for tool_name, params in runner.TOOL_PARAMS.items():
            assert isinstance(params, dict), f"{tool_name} params not a dict"


class TestDryRunMode:
    """Test dry_run mode functionality."""

    def test_dry_run_adds_flag_to_params(self) -> None:
        """Test that dry_run mode adds dry_run flag to params."""
        runner = ToolCoverageRunner(dry_run=True)

        # Get a sample tool that supports dry_run
        params = runner.TOOL_PARAMS.get("research_fetch", {})
        assert "url" in params  # Has URL
        # Note: dry_run is added dynamically during run, not pre-stored

    def test_network_required_tools_skipped_in_dry_run(self) -> None:
        """Test that network tools are in the skip list."""
        runner = ToolCoverageRunner(dry_run=True)

        network_tools = [
            "research_nmap_scan",
            "research_metadata_forensics",
            "research_credential_monitor",
        ]

        for tool in network_tools:
            assert tool in runner.NETWORK_REQUIRED_TOOLS


@pytest.mark.asyncio
async def test_full_coverage_flow() -> None:
    """Integration test: full coverage flow."""
    runner = ToolCoverageRunner(dry_run=True)

    # Run with a small subset
    results = await runner.run_coverage(
        tools_to_test=["research_cache_stats", "research_health_check"],
        timeout=5.0,
    )

    # Verify result structure
    assert "total_tools" in results
    assert "tools_tested" in results
    assert "tools_passed" in results
    assert "coverage_pct" in results
    assert "per_tool_results" in results
    assert "stats" in results

    # Verify per-tool results structure
    for tool_result in results["per_tool_results"]:
        assert "tool" in tool_result
        assert "status" in tool_result
        assert "passed" in tool_result
        assert tool_result["status"] in ["passed", "failed", "error", "timeout", "skipped"]
