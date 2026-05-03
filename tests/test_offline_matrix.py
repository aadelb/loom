"""Tests for offline capability matrix (REQ-095)."""

import pytest

from loom.offline_matrix import (
    CAPABILITY_LEVELS,
    TOOL_CAPABILITIES,
    can_tool_use_cache_fallback,
    get_cache_fallback_tools,
    get_capability_summary,
    get_network_required_tools,
    get_offline_tools,
    get_tool_capability,
    is_tool_available_offline,
)



pytestmark = pytest.mark.asyncio
class TestToolCapability:
    """Test get_tool_capability returns correct level."""

    async def test_get_tool_capability_offline(self):
        """Test that offline tools return full_offline."""
        assert get_tool_capability("research_text_analyze") == "full_offline"
        assert get_tool_capability("research_hcs_score") == "full_offline"
        assert get_tool_capability("research_stylometry") == "full_offline"

    async def test_get_tool_capability_cache_fallback(self):
        """Test that cache fallback tools return cache_fallback."""
        assert get_tool_capability("research_search") == "cache_fallback"
        assert get_tool_capability("research_fetch") == "cache_fallback"
        assert get_tool_capability("research_deep") == "cache_fallback"

    async def test_get_tool_capability_network_required(self):
        """Test that network tools return network_required."""
        assert get_tool_capability("research_spider") == "network_required"
        assert get_tool_capability("research_camoufox") == "network_required"
        assert get_tool_capability("research_onion_discover") == "network_required"

    async def test_get_tool_capability_unknown_defaults_to_network(self):
        """Test that unknown tools default to network_required."""
        assert get_tool_capability("unknown_tool_xyz") == "network_required"
        assert get_tool_capability("research_nonexistent") == "network_required"


class TestOfflineTools:
    """Test get_offline_tools returns correct tools."""

    async def test_get_offline_tools_returns_list(self):
        """Test that offline tools returns a list."""
        offline = get_offline_tools()
        assert isinstance(offline, list)
        assert len(offline) > 0

    async def test_offline_tools_include_expected(self):
        """Test that offline tools include key examples."""
        offline = get_offline_tools()
        expected = {
            "research_hcs_score",
            "research_text_analyze",
            "research_stylometry",
            "research_deception_detect",
            "research_geoip_local",
            "research_cache_stats",
            "research_config_get",
            "research_session_list",
        }
        for tool in expected:
            assert tool in offline, f"{tool} should be in offline tools"

    async def test_offline_tools_are_sorted(self):
        """Test that offline tools are sorted."""
        offline = get_offline_tools()
        assert offline == sorted(offline)

    async def test_offline_tools_only_have_full_offline(self):
        """Test that all returned offline tools have full_offline capability."""
        offline = get_offline_tools()
        for tool in offline:
            assert get_tool_capability(tool) == "full_offline"


class TestCacheFallbackTools:
    """Test get_cache_fallback_tools."""

    async def test_get_cache_fallback_tools_returns_list(self):
        """Test that cache fallback tools returns a list."""
        cache_fallback = get_cache_fallback_tools()
        assert isinstance(cache_fallback, list)
        assert len(cache_fallback) > 0

    async def test_cache_fallback_tools_include_expected(self):
        """Test that cache fallback tools include key examples."""
        cache_fallback = get_cache_fallback_tools()
        expected = {
            "research_search",
            "research_fetch",
            "research_deep",
            "research_markdown",
            "research_llm_summarize",
        }
        for tool in expected:
            assert tool in cache_fallback, f"{tool} should be in cache fallback tools"

    async def test_cache_fallback_tools_are_sorted(self):
        """Test that cache fallback tools are sorted."""
        cache_fallback = get_cache_fallback_tools()
        assert cache_fallback == sorted(cache_fallback)

    async def test_cache_fallback_tools_only_have_cache_fallback(self):
        """Test that all returned cache fallback tools have cache_fallback capability."""
        cache_fallback = get_cache_fallback_tools()
        for tool in cache_fallback:
            assert get_tool_capability(tool) == "cache_fallback"


class TestNetworkRequiredTools:
    """Test get_network_required_tools."""

    async def test_get_network_required_tools_returns_list(self):
        """Test that network required tools returns a list."""
        network = get_network_required_tools()
        assert isinstance(network, list)
        assert len(network) > 0

    async def test_network_required_tools_include_expected(self):
        """Test that network required tools include key examples."""
        network = get_network_required_tools()
        expected = {
            "research_spider",
            "research_camoufox",
            "research_botasaurus",
            "research_onion_discover",
            "research_github",
            "research_screenshot",
        }
        for tool in expected:
            assert tool in network, f"{tool} should be in network required tools"

    async def test_network_required_tools_are_sorted(self):
        """Test that network required tools are sorted."""
        network = get_network_required_tools()
        assert network == sorted(network)

    async def test_network_required_tools_only_have_network(self):
        """Test that all returned network tools have network_required capability."""
        network = get_network_required_tools()
        for tool in network:
            assert get_tool_capability(tool) == "network_required"


class TestCapabilitySummary:
    """Test get_capability_summary."""

    async def test_get_capability_summary_returns_dict(self):
        """Test that capability summary returns a dict."""
        summary = get_capability_summary()
        assert isinstance(summary, dict)

    async def test_get_capability_summary_has_required_keys(self):
        """Test that summary has all three capability levels."""
        summary = get_capability_summary()
        assert "full_offline" in summary
        assert "cache_fallback" in summary
        assert "network_required" in summary

    async def test_get_capability_summary_values_are_integers(self):
        """Test that all summary values are positive integers."""
        summary = get_capability_summary()
        for key, count in summary.items():
            assert isinstance(count, int)
            assert count > 0, f"{key} count should be positive"

    async def test_capability_summary_counts_all_tools(self):
        """Test that summary counts match total tools."""
        summary = get_capability_summary()
        total_from_summary = sum(summary.values())
        total_from_matrix = len(TOOL_CAPABILITIES)
        assert total_from_summary == total_from_matrix

    async def test_get_capability_summary_counts_by_category(self):
        """Test that summary counts match actual tool counts per category."""
        summary = get_capability_summary()
        offline = get_offline_tools()
        cache = get_cache_fallback_tools()
        network = get_network_required_tools()

        assert summary["full_offline"] == len(offline)
        assert summary["cache_fallback"] == len(cache)
        assert summary["network_required"] == len(network)


class TestIsToolAvailableOffline:
    """Test is_tool_available_offline."""

    async def test_offline_tool_available_offline(self):
        """Test that offline tools are available offline."""
        assert is_tool_available_offline("research_text_analyze") is True
        assert is_tool_available_offline("research_hcs_score") is True

    async def test_cache_fallback_tool_not_available_offline(self):
        """Test that cache fallback tools are not fully offline."""
        assert is_tool_available_offline("research_fetch") is False
        assert is_tool_available_offline("research_search") is False

    async def test_network_tool_not_available_offline(self):
        """Test that network tools are not available offline."""
        assert is_tool_available_offline("research_spider") is False
        assert is_tool_available_offline("research_github") is False

    async def test_unknown_tool_not_available_offline(self):
        """Test that unknown tools are not available offline."""
        assert is_tool_available_offline("unknown_tool") is False


class TestCanToolUseCacheFallback:
    """Test can_tool_use_cache_fallback."""

    async def test_offline_tool_can_use_cache(self):
        """Test that offline tools can use cache (trivially true)."""
        assert can_tool_use_cache_fallback("research_text_analyze") is True

    async def test_cache_fallback_tool_can_use_cache(self):
        """Test that cache fallback tools can use cache."""
        assert can_tool_use_cache_fallback("research_fetch") is True
        assert can_tool_use_cache_fallback("research_search") is True

    async def test_network_required_tool_cannot_use_cache(self):
        """Test that network required tools cannot use cache."""
        assert can_tool_use_cache_fallback("research_spider") is False
        assert can_tool_use_cache_fallback("research_github") is False

    async def test_unknown_tool_cannot_use_cache(self):
        """Test that unknown tools default to network_required."""
        # Unknown tools default to network_required, so they can't use cache
        assert can_tool_use_cache_fallback("unknown_tool") is False


class TestCapabilityLevels:
    """Test CAPABILITY_LEVELS definitions."""

    async def test_capability_levels_has_three_levels(self):
        """Test that CAPABILITY_LEVELS has exactly three levels."""
        assert len(CAPABILITY_LEVELS) == 3

    async def test_capability_levels_has_required_keys(self):
        """Test that CAPABILITY_LEVELS has all three required keys."""
        assert "full_offline" in CAPABILITY_LEVELS
        assert "cache_fallback" in CAPABILITY_LEVELS
        assert "network_required" in CAPABILITY_LEVELS

    async def test_capability_levels_values_are_strings(self):
        """Test that all capability level values are non-empty strings."""
        for key, desc in CAPABILITY_LEVELS.items():
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestToolCapabilitiesMatrix:
    """Test TOOL_CAPABILITIES matrix structure."""

    async def test_tool_capabilities_is_dict(self):
        """Test that TOOL_CAPABILITIES is a dictionary."""
        assert isinstance(TOOL_CAPABILITIES, dict)

    async def test_tool_capabilities_not_empty(self):
        """Test that TOOL_CAPABILITIES contains tools."""
        assert len(TOOL_CAPABILITIES) > 0

    async def test_all_tool_capabilities_are_valid(self):
        """Test that all tool capabilities are valid levels."""
        valid_levels = set(CAPABILITY_LEVELS.keys())
        for tool, cap in TOOL_CAPABILITIES.items():
            assert cap in valid_levels, f"Tool {tool} has invalid capability {cap}"

    async def test_all_tool_names_start_with_research_or_fetch(self):
        """Test that tool names follow naming convention."""
        for tool in TOOL_CAPABILITIES.keys():
            assert tool.startswith("research_") or tool.startswith("fetch_") or tool.startswith("find_"), \
                f"Tool {tool} should start with research_, fetch_, or find_"


class TestOfflineMatrixConsistency:
    """Test consistency across offline matrix functions."""

    async def test_no_tool_in_multiple_categories(self):
        """Test that no tool appears in multiple categories."""
        offline = set(get_offline_tools())
        cache = set(get_cache_fallback_tools())
        network = set(get_network_required_tools())

        # Check no overlaps
        assert len(offline & cache) == 0, "Tools in both offline and cache"
        assert len(offline & network) == 0, "Tools in both offline and network"
        assert len(cache & network) == 0, "Tools in both cache and network"

    async def test_all_tools_in_some_category(self):
        """Test that every tool is in exactly one category."""
        offline = set(get_offline_tools())
        cache = set(get_cache_fallback_tools())
        network = set(get_network_required_tools())
        all_tools = set(TOOL_CAPABILITIES.keys())

        categorized = offline | cache | network
        assert categorized == all_tools, "Not all tools are categorized"

    async def test_summary_includes_all_tools(self):
        """Test that capability summary includes all tools."""
        summary = get_capability_summary()
        total = sum(summary.values())
        assert total == len(TOOL_CAPABILITIES)


class TestOfflineCriticalTools:
    """Test that critical tools have correct offline capabilities."""

    async def test_cache_management_offline(self):
        """Test that cache management tools are offline."""
        assert get_tool_capability("research_cache_stats") == "full_offline"
        assert get_tool_capability("research_cache_clear") == "full_offline"

    async def test_config_offline(self):
        """Test that config tools are offline."""
        assert get_tool_capability("research_config_get") == "full_offline"
        assert get_tool_capability("research_config_set") == "full_offline"

    async def test_session_list_offline(self):
        """Test that session listing is offline."""
        assert get_tool_capability("research_session_list") == "full_offline"

    async def test_health_check_offline(self):
        """Test that health check is offline."""
        assert get_tool_capability("research_health_check") == "full_offline"

    async def test_search_needs_network(self):
        """Test that search tools prefer network."""
        assert get_tool_capability("research_search") == "cache_fallback"
        assert get_tool_capability("research_multi_search") == "cache_fallback"

    async def test_fetch_needs_network(self):
        """Test that fetch tools prefer network."""
        assert get_tool_capability("research_fetch") == "cache_fallback"
        assert get_tool_capability("research_deep") == "cache_fallback"

    async def test_spider_requires_network(self):
        """Test that spider requires network."""
        assert get_tool_capability("research_spider") == "network_required"

    async def test_github_requires_network(self):
        """Test that GitHub tools require network."""
        assert get_tool_capability("research_github") == "network_required"
        assert get_tool_capability("research_github_secrets") == "network_required"


class TestOfflineToolDistribution:
    """Test the distribution of tools across capability levels."""

    async def test_significant_offline_tools_available(self):
        """Test that a reasonable number of tools work offline."""
        offline = get_offline_tools()
        # Should have at least 30 fully offline tools
        assert len(offline) >= 30, f"Expected 30+ offline tools, got {len(offline)}"

    async def test_significant_cache_fallback_tools(self):
        """Test that many tools can use cache fallback."""
        cache = get_cache_fallback_tools()
        # Should have at least 60 cache fallback tools
        assert len(cache) >= 60, f"Expected 60+ cache fallback tools, got {len(cache)}"

    async def test_network_tools_minority(self):
        """Test that network-required tools are a smaller set."""
        network = get_network_required_tools()
        total = len(TOOL_CAPABILITIES)
        # Network tools should be less than 30% of total
        ratio = len(network) / total
        assert ratio < 0.3, f"Network tools ratio {ratio} should be <0.3"
