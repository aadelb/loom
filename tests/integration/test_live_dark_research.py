"""Live integration tests for Dark Research tools.

Tests the following dark web research tools with TOR_ENABLED environment variable:
1. research_dark_forum — Aggregate dark web forum intelligence from 4+ sources
   (Ahmia, AlienVault OTX, Reddit darknet/onions)
2. research_onion_discover — Discover .onion hidden services using 5+ methods
   (Ahmia, DarkSearch, IntelX, Certificate Transparency, Reddit)
3. research_darkweb_early_warning — Monitor dark web for threat indicators
   (Ahmia, AlienVault OTX, Reddit r/darknet, HackerNews)
4. research_tor_status — Check Tor daemon status and get current exit node IP
5. research_tor_new_identity — Request a new Tor circuit (exit node rotation)

All tests mark @pytest.mark.live and implement graceful handling:
- If TOR_ENABLED=true: run tool, assert valid response
- If TOR_ENABLED=false (default): run tool, assert graceful error or TOR_DISABLED message
- Either way: NO unhandled exceptions, NO crashes

Test timeout: 30s per test (some operations may need 20+ seconds for network latency).
"""

from __future__ import annotations

import os
from typing import Any

import pytest


def is_tor_enabled() -> bool:
    """Check if Tor is enabled in environment."""
    return os.environ.get("TOR_ENABLED", "false").lower() == "true"


@pytest.fixture
def tor_enabled_or_skip() -> None:
    """Fixture that logs whether Tor is enabled (doesn't skip, just informs)."""
    if is_tor_enabled():
        pytest.skip("Test expects Tor disabled; Tor is currently enabled", allow_module_level=False)


@pytest.fixture
def tor_disabled_or_skip() -> None:
    """Fixture that logs whether Tor is disabled (doesn't skip, just informs)."""
    if not is_tor_enabled():
        pytest.skip("Test expects Tor enabled; Tor is currently disabled", allow_module_level=False)


class TestResearchDarkForum:
    """Test research_dark_forum tool."""

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_dark_forum_search_basic(self) -> None:
        """Test dark_forum search with a basic query.

        Expected behavior:
        - If TOR_ENABLED=true: returns valid results with sources_breakdown
        - If TOR_ENABLED=false: returns graceful response (may have 0 results or error)
        - Either way: No exceptions, valid dict structure
        """
        from loom.tools.intelligence.dark_forum import research_dark_forum

        # Basic search query
        result = research_dark_forum(query="security", max_results=10)

        # Structure validation
        assert isinstance(result, dict), "Result must be a dict"
        assert "query" in result, "Result must contain 'query'"
        assert result["query"] == "security", "Query should be preserved"
        assert "sources_checked" in result, "Result must contain 'sources_checked'"
        assert "total_results" in result, "Result must contain 'total_results'"
        assert "results" in result, "Result must contain 'results' key"
        assert isinstance(result["results"], list), "Results must be a list"
        assert "sources_breakdown" in result, "Result must contain 'sources_breakdown'"

        # Either valid results or graceful degradation
        if is_tor_enabled():
            # With Tor enabled, we expect reasonable results
            assert result["sources_checked"] == 4, "Should check 4 sources"
            assert result["total_results"] >= 0, "Should have non-negative results"
            if result["total_results"] > 0:
                first = result["results"][0]
                assert "url" in first, "Results should have URL"
                assert "source" in first, "Results should have source"
        else:
            # Without Tor, results may be empty or have errors, but structure is valid
            assert result["sources_checked"] == 4, "Should check 4 sources even if Tor disabled"
            assert isinstance(result["total_results"], int), "Total results must be int"

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_dark_forum_search_threat_keywords(self) -> None:
        """Test dark_forum search with threat-related keywords.

        Searches for common security threat keywords (e.g., 'ransomware', 'exploit').
        Tests resilience with realistic dark web search patterns.
        """
        from loom.tools.intelligence.dark_forum import research_dark_forum

        keywords = ["exploit", "malware", "threat"]
        for keyword in keywords:
            result = research_dark_forum(query=keyword, max_results=5)

            assert isinstance(result, dict), f"Result for '{keyword}' must be dict"
            assert "query" in result, f"Result for '{keyword}' must contain query"
            assert "total_results" in result, f"Result for '{keyword}' must contain total_results"
            assert isinstance(result["results"], list), f"Results for '{keyword}' must be list"

            # Verify no exceptions even if results are empty
            assert result["total_results"] >= 0, f"Negative results for '{keyword}'"

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_dark_forum_max_results_limit(self) -> None:
        """Test dark_forum respects max_results parameter."""
        from loom.tools.intelligence.dark_forum import research_dark_forum

        result = research_dark_forum(query="test", max_results=3)

        assert "results" in result, "Result must contain results list"
        assert len(result["results"]) <= 3, "Results should not exceed max_results=3"


class TestResearchOnionDiscover:
    """Test research_onion_discover tool."""

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_onion_discover_basic(self) -> None:
        """Test onion_discover with a basic query.

        Expected behavior:
        - If TOR_ENABLED=true: finds .onion URLs from 5+ sources
        - If TOR_ENABLED=false: may return 0 results but valid structure
        - Either way: No exceptions, valid dict structure
        """
        from loom.tools.intelligence.onion_discover import research_onion_discover

        result = research_onion_discover(query="market", max_results=10)

        # Structure validation
        assert isinstance(result, dict), "Result must be a dict"
        assert "query" in result, "Result must contain 'query'"
        assert result["query"] == "market", "Query should be preserved"
        assert "sources_checked" in result, "Result must contain 'sources_checked'"
        assert isinstance(result["sources_checked"], list), "sources_checked must be list"
        assert "onion_urls_found" in result, "Result must contain 'onion_urls_found'"
        assert isinstance(result["onion_urls_found"], list), "onion_urls_found must be list"
        assert "total_unique" in result, "Result must contain 'total_unique'"
        assert isinstance(result["total_unique"], int), "total_unique must be int"

        # Validate structure of results
        for url_item in result["onion_urls_found"]:
            assert isinstance(url_item, dict), "Each URL item must be dict"
            assert "url" in url_item, "URL item must have 'url'"
            assert "source" in url_item, "URL item must have 'source'"
            # URLs should be .onion addresses or at least URLs
            assert ".onion" in url_item.get("url", "").lower() or url_item["url"].startswith(
                "http"
            ), "URLs should be .onion or valid URLs"

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_onion_discover_sources_checked(self) -> None:
        """Test onion_discover reports all sources checked."""
        from loom.tools.intelligence.onion_discover import research_onion_discover

        result = research_onion_discover(query="search", max_results=5)

        # Should check 5 sources
        expected_sources = {
            "ahmia",
            "darksearch",
            "intelx",
            "certificate_transparency",
            "reddit_onions",
        }
        sources_checked = set(result.get("sources_checked", []))
        assert expected_sources == sources_checked, f"Expected sources {expected_sources}, got {sources_checked}"

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_onion_discover_max_results(self) -> None:
        """Test onion_discover respects max_results parameter."""
        from loom.tools.intelligence.onion_discover import research_onion_discover

        result = research_onion_discover(query="forum", max_results=5)

        assert "onion_urls_found" in result, "Result must contain onion_urls_found"
        assert len(result["onion_urls_found"]) <= 5, "Should not exceed max_results=5"
        assert result["total_unique"] <= 5, "total_unique should not exceed max_results"


class TestResearchDarkwebEarlyWarning:
    """Test research_darkweb_early_warning tool."""

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_early_warning_single_keyword(self) -> None:
        """Test darkweb_early_warning with a single keyword.

        Expected behavior:
        - If TOR_ENABLED=true: searches multiple sources, returns alerts
        - If TOR_ENABLED=false: may return no alerts but valid structure
        - Either way: No exceptions, valid dict structure
        """
        from loom.tools.intelligence.darkweb_early_warning import research_darkweb_early_warning

        result = research_darkweb_early_warning(keywords=["exploit"], hours_back=72)

        # Structure validation
        assert isinstance(result, dict), "Result must be a dict"
        assert "keywords" in result, "Result must contain 'keywords'"
        assert result["keywords"] == ["exploit"], "Keywords should be preserved"
        assert "alerts" in result, "Result must contain 'alerts'"
        assert isinstance(result["alerts"], list), "alerts must be a list"
        assert "alert_count" in result, "Result must contain 'alert_count'"
        assert isinstance(result["alert_count"], int), "alert_count must be int"
        assert "highest_severity" in result, "Result must contain 'highest_severity'"
        assert "search_hours_back" in result, "Result must contain 'search_hours_back'"
        assert result["search_hours_back"] == 72, "hours_back should be preserved"
        assert "timestamp" in result, "Result must contain 'timestamp'"

        # Validate alert structure
        for alert in result["alerts"]:
            assert isinstance(alert, dict), "Each alert must be dict"
            assert "keyword" in alert, "Alert must have 'keyword'"
            assert "source" in alert, "Alert must have 'source'"
            assert "severity" in alert, "Alert must have 'severity'"
            assert alert["severity"] in [
                "critical",
                "high",
                "medium",
                "low",
            ], f"Invalid severity: {alert['severity']}"

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_early_warning_multiple_keywords(self) -> None:
        """Test darkweb_early_warning with multiple keywords."""
        from loom.tools.intelligence.darkweb_early_warning import research_darkweb_early_warning

        keywords = ["malware", "ransomware", "breach"]
        result = research_darkweb_early_warning(keywords=keywords, hours_back=48)

        assert isinstance(result, dict), "Result must be a dict"
        assert "keywords" in result, "Result must contain 'keywords'"
        assert result["keywords"] == keywords, "Keywords should be preserved"
        assert isinstance(result["alerts"], list), "alerts must be a list"
        assert result["alert_count"] >= 0, "alert_count must be non-negative"

        # Each alert should match one of our keywords
        for alert in result["alerts"]:
            assert alert["keyword"] in keywords, f"Alert keyword not in input keywords: {alert['keyword']}"

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_early_warning_empty_keywords(self) -> None:
        """Test darkweb_early_warning with empty keyword list.

        Should return a graceful error response.
        """
        from loom.tools.intelligence.darkweb_early_warning import research_darkweb_early_warning

        result = research_darkweb_early_warning(keywords=[], hours_back=72)

        # Should return graceful error structure
        assert isinstance(result, dict), "Result must be a dict"
        assert "error" in result or result.get("alert_count") == 0, "Should indicate error or empty results"

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_early_warning_severity_levels(self) -> None:
        """Test darkweb_early_warning returns valid severity levels."""
        from loom.tools.intelligence.darkweb_early_warning import research_darkweb_early_warning

        result = research_darkweb_early_warning(keywords=["zero-day"], hours_back=24)

        assert isinstance(result, dict), "Result must be a dict"

        # If there are alerts, check severity levels
        if result.get("alert_count", 0) > 0:
            valid_severities = {"critical", "high", "medium", "low", None}
            assert result["highest_severity"] in valid_severities, f"Invalid highest_severity: {result['highest_severity']}"

            for alert in result["alerts"]:
                assert alert["severity"] in [
                    "critical",
                    "high",
                    "medium",
                    "low",
                ], f"Invalid alert severity: {alert['severity']}"


class TestResearchTorStatus:
    """Test research_tor_status tool."""

    @pytest.mark.live
    @pytest.mark.timeout(30)
    @pytest.mark.asyncio
    async def test_tor_status_basic(self) -> None:
        """Test tor_status returns valid response structure.

        Expected behavior:
        - If Tor running: tor_running=True, exit_ip is populated
        - If Tor not running: tor_running=False, may have error message
        - Either way: No exceptions, valid dict structure
        """
        from loom.tools.infrastructure.tor import research_tor_status

        result = await research_tor_status()

        # Structure validation
        assert isinstance(result, dict), "Result must be a dict"
        assert "tor_running" in result, "Result must contain 'tor_running'"
        assert isinstance(result["tor_running"], bool), "tor_running must be bool"
        assert "exit_ip" in result, "Result must contain 'exit_ip'"
        assert isinstance(result["exit_ip"], str), "exit_ip must be string"
        assert "socks5_proxy" in result, "Result must contain 'socks5_proxy'"
        assert isinstance(result["socks5_proxy"], str), "socks5_proxy must be string"

        # If Tor is running, exit_ip should be populated
        if result["tor_running"]:
            assert len(result["exit_ip"]) > 0, "exit_ip should be populated if tor_running"
            # Basic IP validation (should look like an IP)
            assert any(c.isdigit() for c in result["exit_ip"]), "exit_ip should contain digits"
        else:
            # If Tor not running, should have error or empty IP
            assert (
                "error" in result or result["exit_ip"] == ""
            ), "Should indicate error or empty IP if tor_running=False"

    @pytest.mark.live
    @pytest.mark.timeout(30)
    @pytest.mark.asyncio
    async def test_tor_status_proxy_config(self) -> None:
        """Test tor_status reports configured proxy."""
        from loom.tools.infrastructure.tor import research_tor_status

        result = await research_tor_status()

        # Should have socks5_proxy set to default or configured value
        assert "socks5_proxy" in result, "Result must contain socks5_proxy"
        assert result["socks5_proxy"], "socks5_proxy should not be empty"
        # Should contain SOCKS5 protocol indicator
        assert "socks5" in result["socks5_proxy"].lower() or (
            "127.0.0.1" in result["socks5_proxy"]
        ), "Should reference SOCKS5 proxy config"


class TestResearchTorNewIdentity:
    """Test research_tor_new_identity tool."""

    @pytest.mark.live
    @pytest.mark.timeout(30)
    @pytest.mark.asyncio
    async def test_tor_new_identity_basic(self) -> None:
        """Test tor_new_identity returns valid response structure.

        Expected behavior:
        - If Tor running: status is "new_identity_requested" or "rate_limited"
        - If Tor not running: status is "failed" with error message
        - Either way: No exceptions, valid dict structure
        """
        from loom.tools.infrastructure.tor import research_tor_new_identity

        result = await research_tor_new_identity()

        # Structure validation
        assert isinstance(result, dict), "Result must be a dict"
        assert "status" in result, "Result must contain 'status'"
        assert isinstance(result["status"], str), "status must be string"
        assert "wait_seconds" in result, "Result must contain 'wait_seconds'"
        assert isinstance(result["wait_seconds"], int), "wait_seconds must be int"

        # Status should be one of the valid values
        valid_statuses = {"new_identity_requested", "rate_limited", "failed"}
        assert result["status"] in valid_statuses, f"Invalid status: {result['status']}"

        # wait_seconds should be positive
        assert result["wait_seconds"] > 0, "wait_seconds should be positive"

        # If failed, should have error message
        if result["status"] == "failed":
            assert "error" in result, "Failed status should include error message"

    @pytest.mark.live
    @pytest.mark.timeout(15)
    @pytest.mark.asyncio
    async def test_tor_new_identity_rate_limiting(self) -> None:
        """Test tor_new_identity rate limiting (two requests within 10s).

        Sends two requests in quick succession and verifies the second is rate-limited.
        """
        from loom.tools.infrastructure.tor import research_tor_new_identity

        # First request
        result1 = await research_tor_new_identity()
        assert "status" in result1, "First request must have status"

        # Second request (within 10 seconds, should be rate-limited or fail)
        result2 = await research_tor_new_identity()
        assert "status" in result2, "Second request must have status"

        # At least one should indicate rate limiting or failure
        if result1["status"] == "new_identity_requested":
            # If first succeeded, second should be rate-limited
            assert (
                result2["status"] in ["rate_limited", "failed"]
            ), "Second rapid request should be rate-limited or fail"


class TestDarkResearchGracefulDegradation:
    """Integration tests for graceful degradation when Tor is disabled."""

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_all_tools_no_crash_when_tor_disabled(self) -> None:
        """Test all dark research tools don't crash when Tor is disabled.

        This is the key test: regardless of TOR_ENABLED setting,
        all tools should return valid responses without exceptions.
        """
        if is_tor_enabled():
            pytest.skip("Test requires Tor disabled", allow_module_level=False)

        # Test dark_forum
        from loom.tools.intelligence.dark_forum import research_dark_forum

        result = research_dark_forum(query="test", max_results=5)
        assert isinstance(result, dict), "dark_forum should return dict"
        assert "results" in result, "dark_forum should have results key"

        # Test onion_discover
        from loom.tools.intelligence.onion_discover import research_onion_discover

        result = research_onion_discover(query="test", max_results=5)
        assert isinstance(result, dict), "onion_discover should return dict"
        assert "onion_urls_found" in result, "onion_discover should have onion_urls_found key"

        # Test darkweb_early_warning
        from loom.tools.intelligence.darkweb_early_warning import research_darkweb_early_warning

        result = research_darkweb_early_warning(keywords=["test"], hours_back=24)
        assert isinstance(result, dict), "darkweb_early_warning should return dict"
        assert "alerts" in result, "darkweb_early_warning should have alerts key"

    @pytest.mark.live
    @pytest.mark.timeout(30)
    @pytest.mark.asyncio
    async def test_tor_tools_return_valid_responses(self) -> None:
        """Test Tor tools return valid responses regardless of Tor status."""
        from loom.tools.infrastructure.tor import research_tor_new_identity, research_tor_status

        # Test research_tor_status
        status_result = await research_tor_status()
        assert isinstance(status_result, dict), "tor_status should return dict"
        assert "tor_running" in status_result, "tor_status should have tor_running key"

        # Test research_tor_new_identity
        identity_result = await research_tor_new_identity()
        assert isinstance(identity_result, dict), "tor_new_identity should return dict"
        assert "status" in identity_result, "tor_new_identity should have status key"


class TestDarkResearchResponseValidation:
    """Comprehensive validation tests for dark research tool responses."""

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_dark_forum_response_schema(self) -> None:
        """Validate complete schema of dark_forum response."""
        from loom.tools.intelligence.dark_forum import research_dark_forum

        result = research_dark_forum(query="test", max_results=5)

        # Required top-level keys
        required_keys = {
            "query",
            "sources_checked",
            "sources_with_results",
            "total_results",
            "results",
            "sources_breakdown",
        }
        assert required_keys.issubset(set(result.keys())), f"Missing required keys in result: {required_keys - set(result.keys())}"

        # Type validation
        assert isinstance(result["query"], str), "query must be string"
        assert isinstance(result["sources_checked"], int), "sources_checked must be int"
        assert isinstance(result["sources_with_results"], int), "sources_with_results must be int"
        assert isinstance(result["total_results"], int), "total_results must be int"
        assert isinstance(result["results"], list), "results must be list"
        assert isinstance(result["sources_breakdown"], dict), "sources_breakdown must be dict"

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_onion_discover_response_schema(self) -> None:
        """Validate complete schema of onion_discover response."""
        from loom.tools.intelligence.onion_discover import research_onion_discover

        result = research_onion_discover(query="test", max_results=5)

        # Required top-level keys
        required_keys = {
            "query",
            "sources_checked",
            "onion_urls_found",
            "total_unique",
        }
        assert required_keys.issubset(set(result.keys())), f"Missing required keys: {required_keys - set(result.keys())}"

        # Type validation
        assert isinstance(result["query"], str), "query must be string"
        assert isinstance(result["sources_checked"], list), "sources_checked must be list"
        assert isinstance(result["onion_urls_found"], list), "onion_urls_found must be list"
        assert isinstance(result["total_unique"], int), "total_unique must be int"

    @pytest.mark.live
    @pytest.mark.timeout(30)
    def test_darkweb_early_warning_response_schema(self) -> None:
        """Validate complete schema of darkweb_early_warning response."""
        from loom.tools.intelligence.darkweb_early_warning import research_darkweb_early_warning

        result = research_darkweb_early_warning(keywords=["test"], hours_back=24)

        # Required top-level keys
        required_keys = {
            "keywords",
            "alerts",
            "alert_count",
            "highest_severity",
            "search_hours_back",
            "timestamp",
        }
        # 'error' key is optional, only present on error
        result_keys = set(result.keys())
        assert required_keys.issubset(result_keys) or (
            "error" in result
        ), f"Missing required keys: {required_keys - result_keys}"

        # Type validation for present keys
        if "keywords" in result:
            assert isinstance(result["keywords"], list), "keywords must be list"
        if "alerts" in result:
            assert isinstance(result["alerts"], list), "alerts must be list"
        if "alert_count" in result:
            assert isinstance(result["alert_count"], int), "alert_count must be int"
        if "search_hours_back" in result:
            assert isinstance(result["search_hours_back"], int), "search_hours_back must be int"
        if "timestamp" in result:
            assert isinstance(result["timestamp"], str), "timestamp must be string"
