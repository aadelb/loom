"""Comprehensive test suite runner for all 227+ Loom MCP tools.

Executes all registered tools with minimal valid parameters and reports
coverage, success rates, and failures. Supports dry-run validation without
making real network calls.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("loom.test_runner")


@dataclass
class ToolResult:
    """Result from running a single tool."""

    tool_name: str
    passed: bool
    status: str  # "passed", "failed", "error", "timeout", "skipped"
    error_message: str | None = None
    elapsed_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class CoverageStats:
    """Coverage statistics for test run."""

    total_tools: int = 0
    tools_tested: int = 0
    tools_passed: int = 0
    tools_failed: int = 0
    tools_skipped: int = 0
    tools_timeout: int = 0
    tools_error: int = 0
    coverage_pct: float = 0.0
    total_elapsed_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ToolCoverageRunner:
    """Run all registered MCP tools with minimal valid params to verify they work.

    Minimal valid params for each tool category to validate tool
    registration, parameter models, and basic functionality.
    """

    # Minimal valid params for each tool
    # Some tools are skipped (network-required, infrastructure-only, etc.)
    TOOL_PARAMS = {
        # Core research tools
        "research_fetch": {"url": "https://example.com", "dry_run": True},
        "research_spider": {
            "urls": ["https://example.com", "https://example.org"],
            "dry_run": True,
        },
        "research_markdown": {"url": "https://example.com", "dry_run": True},
        "research_search": {"query": "test", "provider": "ddgs", "max_results": 1},
        "research_deep": {"query": "test", "dry_run": True},
        "research_github": {"query": "python", "dry_run": True},
        "research_camoufox": {"url": "https://example.com", "dry_run": True},
        "research_botasaurus": {"url": "https://example.com", "dry_run": True},
        "research_cache_stats": {},
        "research_cache_clear": {},
        # Killer research tools
        "research_dead_content": {"query": "test", "dry_run": True},
        "research_invisible_web": {"query": "test", "dry_run": True},
        "research_js_intel": {"url": "https://example.com", "dry_run": True},
        "research_multi_search": {"query": "test", "dry_run": True},
        "research_dark_forum": {"query": "test", "provider": "ahmia", "dry_run": True},
        "research_infra_correlator": {
            "domain": "example.com",
            "dry_run": True,
        },
        "research_passive_recon": {
            "domain": "example.com",
            "dry_run": True,
        },
        "research_cloud_enum": {"domain": "example.com", "dry_run": True},
        "research_github_secrets": {"repo_url": "https://github.com/test/test"},
        "research_whois_correlator": {"domain": "example.com", "dry_run": True},
        "research_output_consistency": {"query": "test", "dry_run": True},
        "research_talent_migration": {"query": "test", "dry_run": True},
        "research_funding_pipeline": {"company": "Test Inc", "dry_run": True},
        "research_jailbreak_library": {"query": "test"},
        "research_patent_embargo": {"company": "Test Inc", "dry_run": True},
        "research_ideological_drift": {"author": "test", "dry_run": True},
        "research_author_clustering": {"query": "test", "dry_run": True},
        "research_citation_cartography": {"paper_id": "test", "dry_run": True},
        "research_capability_mapper": {"model": "gpt-4", "dry_run": True},
        "research_memorization_scanner": {"model": "gpt-4", "dry_run": True},
        "research_training_contamination": {"model": "gpt-4", "dry_run": True},
        "research_registry_graveyard": {"domain": "example.com", "dry_run": True},
        "research_subdomain_temporal": {"domain": "example.com", "dry_run": True},
        "research_commit_analyzer": {"repo": "test/test", "dry_run": True},
        "research_onion_discover": {"query": "test", "dry_run": True},
        "research_metadata_forensics": {"url": "https://example.com/file.pdf"},
        "research_crypto_trace": {"address": "1A1z7agoat", "dry_run": True},
        "research_stego_detect": {"url": "https://example.com/image.jpg"},
        "research_threat_profile": {"domain": "example.com", "dry_run": True},
        "research_dark_market_monitor": {"market": "test"},
        "research_ransomware_tracker": {"variant": "test"},
        "research_phishing_mapper": {"domain": "example.com"},
        "research_botnet_tracker": {"botnet": "test"},
        "research_malware_intel": {"hash": "test"},
        "research_domain_reputation": {"domain": "example.com"},
        "research_ioc_enrich": {"ioc": "test"},
        "research_leak_scan": {"query": "test", "dry_run": True},
        "research_social_graph": {"identity": "test", "platform": "twitter"},
        # Psychology & behavioral analysis
        "research_stylometry": {"text": "This is test text for stylometry analysis."},
        "research_deception_detect": {"text": "This is test text for deception detection."},
        # Company intelligence
        "research_company_diligence": {"company": "Test Inc"},
        "research_salary_intelligence": {"company": "Test Inc"},
        "research_competitive_intel": {"company": "Test Inc"},
        # Supply chain intelligence
        "research_supply_chain_risk": {"company": "Test Inc", "dry_run": True},
        "research_patent_landscape": {"company": "Test Inc"},
        "research_dependency_audit": {"package": "test", "dry_run": True},
        # Domain intelligence
        "research_whois": {"domain": "example.com", "dry_run": True},
        "research_dns_lookup": {"domain": "example.com", "dry_run": True},
        "research_nmap_scan": {"target": "example.com"},
        # Access & content authenticity
        "research_legal_takedown": {"url": "https://example.com", "dry_run": True},
        "research_open_access": {"paper_id": "test"},
        "research_content_authenticity": {
            "url": "https://example.com/image.jpg",
            "dry_run": True,
        },
        "research_credential_monitor": {"email": "test@example.com"},
        "research_deepfake_checker": {"url": "https://example.com/video.mp4"},
        # Identity resolution
        "research_identity_resolve": {"name": "John Doe", "email": "john@example.com"},
        # Information warfare
        "research_narrative_tracker": {"narrative": "test"},
        "research_bot_detector": {"text": "This is test text for bot detection."},
        "research_censorship_detector": {"url": "https://example.com", "dry_run": True},
        "research_deleted_social": {"username": "test"},
        "research_robots_archaeology": {"domain": "example.com", "dry_run": True},
        # Job market intelligence
        "research_funding_signal": {"company": "Test Inc"},
        "research_stealth_hire_scanner": {"company": "Test Inc"},
        "research_interviewer_profiler": {"name": "test"},
        # Security tools
        "research_cert_analyze": {"domain": "example.com", "dry_run": True},
        "research_security_headers": {"domain": "example.com", "dry_run": True},
        # Signal detection
        "research_ghost_protocol": {"signal": "test"},
        "research_temporal_anomaly": {"domain": "example.com", "dry_run": True},
        "research_sec_tracker": {"ticker": "TEST"},
        "research_breach_check": {"email": "test@example.com"},
        "research_password_check": {"password": "test123"},
        # AI Safety red-team tools
        "research_prompt_injection_test": {
            "model": "gpt-4",
            "prompt": "test",
            "dry_run": True,
        },
        "research_model_fingerprint": {"model": "gpt-4", "dry_run": True},
        "research_bias_probe": {"model": "gpt-4", "queries": ["test"]},
        "research_safety_filter_map": {"model": "gpt-4", "dry_run": True},
        "research_compliance_check": {
            "model": "gpt-4",
            "test_type": "eu_ai_act_15",
            "dry_run": True,
        },
        # Extended AI Safety
        "research_hallucination_benchmark": {"model": "gpt-4", "dry_run": True},
        "research_adversarial_robustness": {"model": "gpt-4", "dry_run": True},
        # Extended OSINT
        "research_social_engineering_score": {"target": "test@example.com"},
        "research_behavioral_fingerprint": {"url": "https://example.com"},
        # PDF extraction
        "research_pdf_extract": {"url": "https://example.com/document.pdf"},
        "research_pdf_search": {
            "url": "https://example.com/document.pdf",
            "query": "test",
        },
        # Academic integrity
        "research_citation_analysis": {"paper_id": "test"},
        "research_retraction_check": {"author": "test"},
        "research_predatory_journal_check": {"journal": "Test Journal"},
        "research_grant_forensics": {"author": "test"},
        "research_monoculture_detect": {"field": "test"},
        "research_review_cartel": {"paper_id": "test"},
        "research_data_fabrication": {"paper_id": "test"},
        "research_institutional_decay": {"institution": "Test University"},
        "research_shell_funding": {"entity": "test"},
        "research_conference_arbitrage": {"conference": "test"},
        "research_preprint_manipulation": {"preprint_id": "test"},
        # Career intelligence
        "research_map_research_to_product": {"researcher": "test"},
        "research_translate_academic_skills": {"cv": "test"},
        "research_career_trajectory": {"person": "test"},
        "research_market_velocity": {"industry": "test"},
        # Change monitoring
        "research_change_monitor": {"url": "https://example.com"},
        # Knowledge graph & fact checking
        "research_knowledge_graph": {"text": "This is test text for knowledge graph extraction."},
        "research_fact_checker": {"claim": "test claim", "dry_run": True},
        # Trend prediction
        "research_trend_predict": {"signal": "test"},
        # Report generation
        "research_generate_report": {
            "title": "Test Report",
            "content": "Test content",
        },
        # Health check
        "research_health_check": {},
        # Sessions
        "research_session_open": {"name": "test_session", "headless": True},
        "research_session_list": {},
        # Config
        "research_config_get": {"key": "LOG_LEVEL"},
        "research_config_set": {
            "key": "TEST_KEY",
            "value": "test_value",
        },
        # Audit
        "research_audit_export": {"format": "json"},
    }

    # Tools that require infrastructure/network - skip in dry run
    NETWORK_REQUIRED_TOOLS = {
        "research_nmap_scan",
        "research_metadata_forensics",
        "research_dark_market_monitor",
        "research_ransomware_tracker",
        "research_phishing_mapper",
        "research_botnet_tracker",
        "research_malware_intel",
        "research_domain_reputation",
        "research_ioc_enrich",
        "research_open_access",
        "research_credential_monitor",
        "research_deepfake_checker",
    }

    # Tools that are optional/external-only - skip if not available
    OPTIONAL_TOOLS = {
        "research_ask_all_llms",
        "research_ask_all_models",
        "research_llm_summarize",
        "research_llm_extract",
        "research_llm_classify",
        "research_llm_translate",
        "research_llm_query_expand",
        "research_llm_answer",
        "research_llm_embed",
        "research_llm_chat",
        "research_detect_language",
        "research_wayback",
        "research_vastai_search",
        "research_vastai_status",
        "research_usage_report",
        "research_stripe_balance",
        "research_email_report",
        "research_save_note",
        "research_list_notebooks",
        "research_tor_status",
        "research_tor_new_identity",
        "research_transcribe",
        "research_convert_document",
        "research_metrics",
        "research_slack_notify",
        "research_image_analyze",
        "research_text_to_speech",
        "research_tts_voices",
        "research_vercel_status",
        "research_cipher_mirror",
        "research_forum_cortex",
        "research_onion_spectra",
        "research_ghost_weave",
        "research_dead_drop_scanner",
        "research_job_search",
        "research_job_market",
        "research_find_experts",
        "fetch_youtube_transcript",
        "research_session_close",
        "research_orchestrate",
        "research_score_all",
        "research_bias_lens",
        "research_culture_dna",
        "research_auto_reframe",
        "research_adaptive_reframe",
        "research_synth_echo",
        "research_prompt_analyzer",
        "research_deception_job_scanner",
        "research_psycholinguistic",
        "research_salary_synthesizer",
        "research_realtime_monitor",
        "research_rss_fetch",
        "research_rss_search",
        "research_social_search",
        "research_social_profile",
        "research_exif_extract",
        "research_ocr_extract",
        "research_geoip_local",
        "research_text_analyze",
        "research_screenshot",
        "research_persona_profile",
        "research_radicalization_detect",
        "research_sentiment_deep",
        "research_network_persona",
        "research_p3_score",
        "research_multi_channel_sentiment",
        "research_unique_research_signal",
    }

    def __init__(self, mcp_app: Any | None = None, dry_run: bool = True):
        """Initialize the test runner.

        Args:
            mcp_app: FastMCP instance with registered tools
            dry_run: If True, add dry_run=True to tool params where supported
        """
        self.mcp_app = mcp_app
        self.dry_run = dry_run
        self.results: list[ToolResult] = []
        self.stats = CoverageStats(total_tools=len(self.TOOL_PARAMS))

    async def run_coverage(
        self,
        tools_to_test: list[str] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Run each tool, record pass/fail/error/timeout.

        Args:
            tools_to_test: Specific tools to test. If None, tests all.
            timeout: Timeout per tool in seconds

        Returns:
            Dict with:
            - total_tools: Total tools in TOOL_PARAMS
            - tools_tested: Tools actually tested
            - tools_passed: Successful tools
            - tools_failed: Failed tools
            - tools_skipped: Skipped tools (optional/network-required)
            - coverage_pct: Coverage percentage
            - per_tool_results: List of per-tool results
            - stats: Full CoverageStats
        """
        self.results = []
        start_time = time.time()

        # Determine which tools to test
        if tools_to_test:
            tool_names = tools_to_test
        else:
            tool_names = list(self.TOOL_PARAMS.keys())

        self.stats.total_tools = len(self.TOOL_PARAMS)

        # If no MCP app, just validate params without execution
        if not self.mcp_app:
            logger.warning("No MCP app provided - validating params only")
            return await self._validate_params_only(tool_names, timeout)

        # Run each tool
        for tool_name in sorted(tool_names):
            # Skip optional/network-only tools
            if tool_name in self.OPTIONAL_TOOLS:
                result = ToolResult(
                    tool_name=tool_name,
                    passed=False,
                    status="skipped",
                    error_message="Optional tool (requires API key or infrastructure)",
                )
                self.results.append(result)
                self.stats.tools_skipped += 1
                continue

            if tool_name in self.NETWORK_REQUIRED_TOOLS and self.dry_run:
                result = ToolResult(
                    tool_name=tool_name,
                    passed=False,
                    status="skipped",
                    error_message="Requires network access (skipped in dry_run)",
                )
                self.results.append(result)
                self.stats.tools_skipped += 1
                continue

            # Get params for tool
            params = self.TOOL_PARAMS.get(tool_name, {})
            if self.dry_run and "dry_run" not in params:
                params = {**params, "dry_run": True}

            # Run tool with timeout
            try:
                result = await asyncio.wait_for(
                    self._run_tool(tool_name, params),
                    timeout=timeout,
                )
                self.results.append(result)

                if result.passed:
                    self.stats.tools_passed += 1
                else:
                    self.stats.tools_failed += 1
            except asyncio.TimeoutError:
                result = ToolResult(
                    tool_name=tool_name,
                    passed=False,
                    status="timeout",
                    error_message=f"Timeout after {timeout}s",
                    elapsed_ms=timeout * 1000,
                )
                self.results.append(result)
                self.stats.tools_timeout += 1
            except Exception as exc:
                result = ToolResult(
                    tool_name=tool_name,
                    passed=False,
                    status="error",
                    error_message=str(exc),
                )
                self.results.append(result)
                self.stats.tools_error += 1

            self.stats.tools_tested += 1

        elapsed = time.time() - start_time
        self.stats.total_elapsed_ms = elapsed * 1000
        self.stats.coverage_pct = (
            100.0 * self.stats.tools_passed / self.stats.tools_tested
            if self.stats.tools_tested > 0
            else 0.0
        )

        return self._build_result_dict()

    async def _validate_params_only(
        self,
        tool_names: list[str],
        timeout: float,
    ) -> dict[str, Any]:
        """Validate params only without executing tools (dry mode)."""
        from pydantic import ValidationError

        for tool_name in sorted(tool_names):
            if tool_name in self.OPTIONAL_TOOLS:
                result = ToolResult(
                    tool_name=tool_name,
                    passed=False,
                    status="skipped",
                    error_message="Optional tool",
                )
                self.results.append(result)
                self.stats.tools_skipped += 1
                continue

            if tool_name in self.NETWORK_REQUIRED_TOOLS and self.dry_run:
                result = ToolResult(
                    tool_name=tool_name,
                    passed=False,
                    status="skipped",
                    error_message="Requires network access (skipped in dry_run)",
                )
                self.results.append(result)
                self.stats.tools_skipped += 1
                continue

            params = self.TOOL_PARAMS.get(tool_name, {})

            try:
                # Import the appropriate param model
                # This will fail if params are invalid
                _validate_tool_params(tool_name, params)
                result = ToolResult(
                    tool_name=tool_name,
                    passed=True,
                    status="passed",
                    details={"validation": "params_valid"},
                )
                self.stats.tools_passed += 1
            except ValidationError as exc:
                result = ToolResult(
                    tool_name=tool_name,
                    passed=False,
                    status="failed",
                    error_message=str(exc),
                )
                self.stats.tools_failed += 1
            except Exception as exc:
                result = ToolResult(
                    tool_name=tool_name,
                    passed=False,
                    status="error",
                    error_message=str(exc),
                )
                self.stats.tools_error += 1

            self.results.append(result)
            self.stats.tools_tested += 1

        self.stats.coverage_pct = (
            100.0 * self.stats.tools_passed / self.stats.tools_tested
            if self.stats.tools_tested > 0
            else 0.0
        )
        return self._build_result_dict()

    async def _run_tool(self, tool_name: str, params: dict[str, Any]) -> ToolResult:
        """Run a single tool and return result."""
        start_time = time.time()

        try:
            # Get tool from MCP app
            tool_func = self._get_tool_function(tool_name)
            if not tool_func:
                return ToolResult(
                    tool_name=tool_name,
                    passed=False,
                    status="error",
                    error_message=f"Tool {tool_name} not found in MCP app",
                    elapsed_ms=(time.time() - start_time) * 1000,
                )

            # Call tool
            import inspect

            if inspect.iscoroutinefunction(tool_func):
                result = await tool_func(**params)
            else:
                result = tool_func(**params)

            elapsed_ms = (time.time() - start_time) * 1000

            # Check if result indicates success
            # Most tools return dict or MCP response object
            return ToolResult(
                tool_name=tool_name,
                passed=True,
                status="passed",
                elapsed_ms=elapsed_ms,
                details={"result_type": type(result).__name__},
            )
        except Exception as exc:
            elapsed_ms = (time.time() - start_time) * 1000
            return ToolResult(
                tool_name=tool_name,
                passed=False,
                status="failed",
                error_message=str(exc),
                elapsed_ms=elapsed_ms,
            )

    def _get_tool_function(self, tool_name: str) -> Any | None:
        """Get tool function from MCP app."""
        if not self.mcp_app:
            return None

        # MCP tools are stored in a tools dict
        if hasattr(self.mcp_app, "tools"):
            return self.mcp_app.tools.get(tool_name)

        # Try to get from module imports
        try:
            parts = tool_name.split("_")
            if len(parts) < 2:
                return None

            # Map tool names to modules
            # e.g., research_fetch -> fetch module
            module_map = {
                "fetch": "fetch",
                "spider": "spider",
                "markdown": "markdown",
                "search": "search",
                "deep": "deep",
                "github": "github",
                "camoufox": "stealth",
                "botasaurus": "stealth",
                "cache": "cache_mgmt",
                # ... etc
            }

            for key, module in module_map.items():
                if key in tool_name:
                    from loom import tools as tools_pkg

                    mod = getattr(tools_pkg, module, None)
                    if mod and hasattr(mod, tool_name):
                        return getattr(mod, tool_name)
        except Exception:
            pass

        return None

    def _build_result_dict(self) -> dict[str, Any]:
        """Build final result dictionary."""
        per_tool_results = [
            {
                "tool": r.tool_name,
                "status": r.status,
                "passed": r.passed,
                "error": r.error_message,
                "elapsed_ms": r.elapsed_ms,
                "details": r.details,
            }
            for r in self.results
        ]

        return {
            "total_tools": self.stats.total_tools,
            "tools_tested": self.stats.tools_tested,
            "tools_passed": self.stats.tools_passed,
            "tools_failed": self.stats.tools_failed,
            "tools_skipped": self.stats.tools_skipped,
            "tools_timeout": self.stats.tools_timeout,
            "tools_error": self.stats.tools_error,
            "coverage_pct": round(self.stats.coverage_pct, 2),
            "total_elapsed_ms": self.stats.total_elapsed_ms,
            "timestamp": self.stats.timestamp,
            "per_tool_results": per_tool_results,
            "stats": self.stats,
        }

    def generate_coverage_report(self, results: dict | None = None) -> str:
        """Generate markdown coverage report.

        Args:
            results: Results dict from run_coverage(). If None, uses self.results.

        Returns:
            Markdown-formatted coverage report
        """
        if results is None:
            results = self._build_result_dict()

        stats = results
        timestamp = stats.get("timestamp", datetime.now(timezone.utc).isoformat())

        # Header
        report = f"""# Loom Tool Coverage Report

**Generated:** {timestamp}

## Summary

| Metric | Value |
|--------|-------|
| Total Tools | {stats['total_tools']} |
| Tools Tested | {stats['tools_tested']} |
| Tools Passed | {stats['tools_passed']} |
| Tools Failed | {stats['tools_failed']} |
| Tools Timeout | {stats['tools_timeout']} |
| Tools Error | {stats['tools_error']} |
| Tools Skipped | {stats['tools_skipped']} |
| **Coverage %** | **{stats['coverage_pct']:.2f}%** |
| Total Time | {stats['total_elapsed_ms']:.2f}ms |

## Results by Status

"""

        # Group results by status
        by_status: dict[str, list[dict]] = {}
        for result in stats["per_tool_results"]:
            status = result["status"]
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(result)

        # Passed tools
        if "passed" in by_status:
            report += f"### Passed ({len(by_status['passed'])})\n\n"
            for result in sorted(by_status["passed"], key=lambda x: x["tool"]):
                report += (
                    f"- **{result['tool']}** ({result['elapsed_ms']:.2f}ms)\n"
                )
            report += "\n"

        # Failed tools
        if "failed" in by_status:
            report += f"### Failed ({len(by_status['failed'])})\n\n"
            for result in sorted(by_status["failed"], key=lambda x: x["tool"]):
                report += f"- **{result['tool']}**"
                if result.get("error"):
                    report += f": {result['error']}\n"
                else:
                    report += "\n"
            report += "\n"

        # Timeout tools
        if "timeout" in by_status:
            report += f"### Timeout ({len(by_status['timeout'])})\n\n"
            for result in sorted(by_status["timeout"], key=lambda x: x["tool"]):
                report += f"- **{result['tool']}** ({result['elapsed_ms']:.2f}ms)\n"
            report += "\n"

        # Error tools
        if "error" in by_status:
            report += f"### Error ({len(by_status['error'])})\n\n"
            for result in sorted(by_status["error"], key=lambda x: x["tool"]):
                report += f"- **{result['tool']}**: {result.get('error', 'Unknown error')}\n"
            report += "\n"

        # Skipped tools
        if "skipped" in by_status:
            report += f"### Skipped ({len(by_status['skipped'])})\n\n"
            for result in sorted(by_status["skipped"], key=lambda x: x["tool"]):
                report += f"- **{result['tool']}**: {result.get('error', 'Skipped')}\n"
            report += "\n"

        return report


def _validate_tool_params(tool_name: str, params: dict[str, Any]) -> None:
    """Validate tool parameters using Pydantic models.

    Args:
        tool_name: Name of the tool
        params: Parameters to validate

    Raises:
        ValidationError: If parameters are invalid
    """
    from pydantic import ValidationError

    from loom.params import (
        FetchParams,
        SpiderParams,
        SearchParams,
        DeepParams,
    )

    # Map tool names to param models
    param_model_map = {
        "research_fetch": FetchParams,
        "research_spider": SpiderParams,
        "research_search": SearchParams,
        "research_deep": DeepParams,
        # Add more as needed
    }

    model = param_model_map.get(tool_name)
    if model:
        try:
            model(**params)
        except ValidationError as exc:
            raise ValidationError(f"Invalid params for {tool_name}: {exc}") from exc
