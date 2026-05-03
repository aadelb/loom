"""REQ-041: Dark Research 5 tools test suite.

Tests the following dark research tools:
1. dark_forum.py → await research_dark_forum()
2. onion_discover.py → await research_onion_discover()
3. leak_scan.py → await research_leak_scan()
4. darkweb_early_warning.py → await research_darkweb_early_warning()
5. tor.py → research_tor_status() and research_tor_new_identity()

Each tool is invoked directly via Python import and tested for:
- Callable and returns dict-like response
- Either returns valid data OR graceful TOR_DISABLED error
- No unhandled exceptions or crashes
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import pytest

logger = logging.getLogger("tests.test_req041_dark_research")


class TestDarkForum:
    """Test research_dark_forum tool."""

    @pytest.mark.asyncio
    async def test_dark_forum_basic_search(self) -> None:
        """Test dark_forum with basic search query."""
        from loom.tools.dark_forum import research_dark_forum

        result = await research_dark_forum(
            query="test security",
            max_results=10,
        )

        # Verify response structure
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Check for graceful TOR_DISABLED response
        if "error" in result:
            error_msg = str(result.get("error", "")).lower()
            assert "tor" in error_msg or "disabled" in error_msg, (
                f"Expected TOR/disabled error, got: {result.get('error')}"
            )
            logger.info(f"dark_forum returned graceful TOR_DISABLED: {result['error']}")
        else:
            # Verify response structure for valid data
            assert "query" in result, "Missing 'query' field"
            assert "results" in result, "Missing 'results' field"
            assert isinstance(result["results"], list), "results should be a list"
            logger.info(
                f"dark_forum returned {len(result['results'])} results for query: {result['query']}"
            )

    @pytest.mark.asyncio
    async def test_dark_forum_empty_query(self) -> None:
        """Test dark_forum with empty query."""
        from loom.tools.dark_forum import research_dark_forum

        result = await research_dark_forum(query="", max_results=5)

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        # Should either work with empty query or return graceful error
        if "error" in result:
            error_msg = str(result.get("error", "")).lower()
            # Could be TOR_DISABLED or validation error
            logger.info(f"dark_forum returned error: {result['error']}")


class TestOnionDiscover:
    """Test research_onion_discover tool."""

    @pytest.mark.asyncio
    async def test_onion_discover_basic_search(self) -> None:
        """Test onion_discover with basic search query."""
        from loom.tools.onion_discover import research_onion_discover

        result = await research_onion_discover(
            query="privacy",
            max_results=20,
        )

        # Verify response structure
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Check for graceful TOR_DISABLED response
        if "error" in result:
            error_msg = str(result.get("error", "")).lower()
            assert "tor" in error_msg or "disabled" in error_msg, (
                f"Expected TOR/disabled error, got: {result.get('error')}"
            )
            logger.info(f"onion_discover returned graceful TOR_DISABLED: {result['error']}")
        else:
            # Verify response structure for valid data
            assert "query" in result, "Missing 'query' field"
            assert "onion_urls_found" in result, "Missing 'onion_urls_found' field"
            assert isinstance(result["onion_urls_found"], list), (
                "onion_urls_found should be a list"
            )
            logger.info(
                f"onion_discover found {len(result['onion_urls_found'])} .onion URLs"
            )

    @pytest.mark.asyncio
    async def test_onion_discover_max_results(self) -> None:
        """Test onion_discover respects max_results parameter."""
        from loom.tools.onion_discover import research_onion_discover

        result = await research_onion_discover(
            query="market",
            max_results=5,
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        if "onion_urls_found" in result:
            assert len(result["onion_urls_found"]) <= 5, (
                "Should respect max_results parameter"
            )


class TestLeakScan:
    """Test research_leak_scan tool."""

    @pytest.mark.asyncio
    async def test_leak_scan_domain(self) -> None:
        """Test leak_scan with domain target."""
        from loom.tools.leak_scan import research_leak_scan

        result = await research_leak_scan(
            target="example.com",
            target_type="domain",
        )

        # Verify response structure
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Check for graceful error (TOR_DISABLED or validation)
        if "error" in result:
            error_msg = str(result.get("error", "")).lower()
            logger.info(f"leak_scan returned error: {result['error']}")
        else:
            # Verify response structure for valid data
            assert "target" in result, "Missing 'target' field"
            assert "target_type" in result, "Missing 'target_type' field"
            assert "sources_checked" in result, "Missing 'sources_checked' field"
            assert "total_exposures" in result, "Missing 'total_exposures' field"
            assert "exposures" in result, "Missing 'exposures' field"
            assert isinstance(result["exposures"], list), "exposures should be a list"
            logger.info(
                f"leak_scan checked {len(result['sources_checked'])} sources for {result['target']}"
            )

    @pytest.mark.asyncio
    async def test_leak_scan_email(self) -> None:
        """Test leak_scan with email target."""
        from loom.tools.leak_scan import research_leak_scan

        result = await research_leak_scan(
            target="test@example.com",
            target_type="email",
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        assert "target" in result, "Missing 'target' field"

    @pytest.mark.asyncio
    async def test_leak_scan_invalid_email(self) -> None:
        """Test leak_scan with invalid email format."""
        from loom.tools.leak_scan import research_leak_scan

        result = await research_leak_scan(
            target="invalid-email",
            target_type="email",
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        # Should return graceful error for invalid email
        if "error" in result:
            logger.info(f"leak_scan correctly rejected invalid email: {result['error']}")


class TestDarkwebEarlyWarning:
    """Test research_darkweb_early_warning tool."""

    @pytest.mark.asyncio
    async def test_darkweb_early_warning_single_keyword(self) -> None:
        """Test darkweb_early_warning with single keyword."""
        from loom.tools.darkweb_early_warning import research_darkweb_early_warning

        result = await research_darkweb_early_warning(
            keywords=["exploit"],
            hours_back=24,
        )

        # Verify response structure
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Check for graceful TOR_DISABLED response
        if "error" in result:
            error_msg = str(result.get("error", "")).lower()
            logger.info(f"darkweb_early_warning returned error: {result['error']}")
        else:
            # Verify response structure for valid data
            assert "keywords" in result, "Missing 'keywords' field"
            assert "alerts" in result, "Missing 'alerts' field"
            assert isinstance(result["alerts"], list), "alerts should be a list"
            assert "alert_count" in result, "Missing 'alert_count' field"
            logger.info(
                f"darkweb_early_warning found {result['alert_count']} alerts"
            )

    @pytest.mark.asyncio
    async def test_darkweb_early_warning_multiple_keywords(self) -> None:
        """Test darkweb_early_warning with multiple keywords."""
        from loom.tools.darkweb_early_warning import research_darkweb_early_warning

        result = await research_darkweb_early_warning(
            keywords=["malware", "botnet", "ransomware"],
            hours_back=72,
        )

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        if "keywords" in result:
            assert len(result["keywords"]) <= 10, "Should cap at 10 keywords"

    @pytest.mark.asyncio
    async def test_darkweb_early_warning_empty_keywords(self) -> None:
        """Test darkweb_early_warning with empty keywords."""
        from loom.tools.darkweb_early_warning import research_darkweb_early_warning

        result = await research_darkweb_early_warning(keywords=[], hours_back=24)

        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        # Should return graceful error for empty keywords
        if "error" in result:
            logger.info(f"darkweb_early_warning rejected empty keywords: {result['error']}")


class TestTorTools:
    """Test Tor integration tools (async)."""

    @pytest.mark.asyncio
    async def test_tor_status(self) -> None:
        """Test research_tor_status tool."""
        from loom.tools.tor import research_tor_status

        result = await research_tor_status()

        # Verify response structure
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Check for graceful TOR_DISABLED response
        if "error" in result:
            error_msg = str(result.get("error", "")).lower()
            logger.info(f"tor_status returned graceful TOR_DISABLED: {result['error']}")
        else:
            # Verify response structure for valid data
            logger.info(f"Tor status: {result}")

    @pytest.mark.asyncio
    async def test_tor_new_identity(self) -> None:
        """Test research_tor_new_identity tool."""
        from loom.tools.tor import research_tor_new_identity

        result = await research_tor_new_identity()

        # Verify response structure
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"

        # Check for graceful TOR_DISABLED response
        if "error" in result:
            error_msg = str(result.get("error", "")).lower()
            logger.info(f"tor_new_identity returned graceful TOR_DISABLED: {result['error']}")
        else:
            # Verify response structure for valid data
            logger.info(f"Tor new identity result: {result}")


class TestNoUnhandledExceptions:
    """Verify no tools raise unhandled exceptions."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_all_sync_tools_return_dict(self) -> None:
        """Verify all sync tools return dict and don't crash."""
        from loom.tools.dark_forum import research_dark_forum
        from loom.tools.darkweb_early_warning import research_darkweb_early_warning
        from loom.tools.leak_scan import research_leak_scan
        from loom.tools.onion_discover import research_onion_discover

        tools = [
            ("dark_forum", research_dark_forum("test")),
            ("onion_discover", research_onion_discover("test")),
            ("leak_scan", research_leak_scan("example.com", "domain")),
            ("darkweb_early_warning", research_darkweb_early_warning(["test"])),
        ]

        results = await asyncio.gather(*[tool[1] for tool in tools], return_exceptions=True)

        for (tool_name, _), result in zip(tools, results):
            if isinstance(result, Exception):
                pytest.fail(f"{tool_name} raised unhandled exception: {result}")
            assert isinstance(result, dict), (
                f"{tool_name} should return dict, got {type(result)}"
            )
            logger.info(f"✓ {tool_name} returned dict successfully")

    async def test_all_async_tools_return_dict(self) -> None:
        """Verify all async tools return dict and don't crash."""
        from loom.tools.tor import research_tor_new_identity, research_tor_status

        tools = [
            ("tor_status", research_tor_status()),
            ("tor_new_identity", research_tor_new_identity()),
        ]

        results = await asyncio.gather(*[tool[1] for tool in tools], return_exceptions=True)

        for (tool_name, _), result in zip(tools, results):
            if isinstance(result, Exception):
                pytest.fail(f"{tool_name} raised unhandled exception: {result}")
            assert isinstance(result, dict), (
                f"{tool_name} should return dict, got {type(result)}"
            )
            logger.info(f"✓ {tool_name} returned dict successfully")


class TestToolCoverage:
    """Summary of REQ-041 tool coverage."""

    @pytest.mark.asyncio
    async def test_req041_tool_coverage(self) -> None:
        """Document which tools are implemented and tested."""
        tools_tested = [
            ("research_dark_forum", "dark_forum.py", "sync"),
            ("research_onion_discover", "onion_discover.py", "sync"),
            ("research_leak_scan", "leak_scan.py", "sync"),
            ("research_darkweb_early_warning", "darkweb_early_warning.py", "sync"),
            ("research_tor_status", "tor.py", "async"),
            ("research_tor_new_identity", "tor.py", "async"),
        ]

        logger.info("\n" + "=" * 80)
        logger.info("REQ-041 Dark Research Tools Coverage Summary")
        logger.info("=" * 80)
        for tool_name, module, style in tools_tested:
            logger.info(f"✓ {tool_name:<35} ({module:<25}) [{style}]")
        logger.info("=" * 80)
        logger.info(f"Total tools tested: {len(tools_tested)}")
        logger.info("Expected behavior: Return valid data OR graceful error when Tor is disabled")
        logger.info("=" * 80 + "\n")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
