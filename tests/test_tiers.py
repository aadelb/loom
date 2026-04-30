"""Unit tests for subscription tier definitions and enforcement.

Tests cover:
1. All 4 tiers exist and are retrievable
2. Free tier has 500 credits, $0 price
3. Pro tier has 10K credits, $99 price
4. Team tier has 50K credits, $299 price
5. Enterprise tier has 200K credits, $999 price
6. get_tier defaults to free for unknown tier names
7. can_access_tool returns True for tool 0 on free tier
8. can_access_tool returns False for tool 50 on free tier (limit 40)
9. can_access_tool returns True for tool 200 on enterprise tier
10. Upgrade path free→pro shows price_diff=$99
11. Downgrade path pro→free shows negative price_diff
12. Tier objects are frozen (immutable)
"""

from __future__ import annotations

import pytest

from loom.billing.tiers import TIERS, can_access_tool, check_upgrade_path, get_tier


class TestTierExistence:
    """Tests for tier definitions."""

    def test_all_four_tiers_exist(self) -> None:
        """All four tiers should be in the TIERS dictionary."""
        assert "free" in TIERS
        assert "pro" in TIERS
        assert "team" in TIERS
        assert "enterprise" in TIERS
        assert len(TIERS) == 4

    def test_free_tier_properties(self) -> None:
        """Free tier should have 500 credits, $0 price, 40 tools, 10 req/min."""
        tier = TIERS["free"]
        assert tier.name == "Free"
        assert tier.monthly_credits == 500
        assert tier.price_usd == 0
        assert tier.tools_limit == 40
        assert tier.rate_limit_per_min == 10
        assert len(tier.features) > 0

    def test_pro_tier_properties(self) -> None:
        """Pro tier should have 10K credits, $99 price, 150 tools, 60 req/min."""
        tier = TIERS["pro"]
        assert tier.name == "Pro"
        assert tier.monthly_credits == 10_000
        assert tier.price_usd == 99
        assert tier.tools_limit == 150
        assert tier.rate_limit_per_min == 60
        assert len(tier.features) > 0

    def test_team_tier_properties(self) -> None:
        """Team tier should have 50K credits, $299 price, 190 tools, 300 req/min."""
        tier = TIERS["team"]
        assert tier.name == "Team"
        assert tier.monthly_credits == 50_000
        assert tier.price_usd == 299
        assert tier.tools_limit == 190
        assert tier.rate_limit_per_min == 300
        assert len(tier.features) > 0

    def test_enterprise_tier_properties(self) -> None:
        """Enterprise tier should have 200K credits, $999 price, 220 tools, 1000 req/min."""
        tier = TIERS["enterprise"]
        assert tier.name == "Enterprise"
        assert tier.monthly_credits == 200_000
        assert tier.price_usd == 999
        assert tier.tools_limit == 220
        assert tier.rate_limit_per_min == 1000
        assert len(tier.features) > 0


class TestTierRetrieval:
    """Tests for get_tier function."""

    def test_get_tier_free(self) -> None:
        """get_tier should return free tier."""
        tier = get_tier("free")
        assert tier.name == "Free"
        assert tier.monthly_credits == 500

    def test_get_tier_pro(self) -> None:
        """get_tier should return pro tier."""
        tier = get_tier("pro")
        assert tier.name == "Pro"
        assert tier.monthly_credits == 10_000

    def test_get_tier_team(self) -> None:
        """get_tier should return team tier."""
        tier = get_tier("team")
        assert tier.name == "Team"
        assert tier.monthly_credits == 50_000

    def test_get_tier_enterprise(self) -> None:
        """get_tier should return enterprise tier."""
        tier = get_tier("enterprise")
        assert tier.name == "Enterprise"
        assert tier.monthly_credits == 200_000

    def test_get_tier_case_insensitive(self) -> None:
        """get_tier should be case-insensitive."""
        assert get_tier("FREE").name == "Free"
        assert get_tier("Pro").name == "Pro"
        assert get_tier("TEAM").name == "Team"
        assert get_tier("ENTERPRISE").name == "Enterprise"

    def test_get_tier_unknown_defaults_to_free(self) -> None:
        """get_tier should default to free for unknown tier names."""
        tier = get_tier("unknown")
        assert tier.name == "Free"
        assert tier.monthly_credits == 500

    def test_get_tier_empty_string_defaults_to_free(self) -> None:
        """get_tier should default to free for empty string."""
        tier = get_tier("")
        assert tier.name == "Free"

    def test_get_tier_none_like_defaults_to_free(self) -> None:
        """get_tier should default to free for various invalid inputs."""
        assert get_tier("null").name == "Free"
        assert get_tier("None").name == "Free"


class TestToolAccess:
    """Tests for can_access_tool function."""

    def test_free_tier_access_tool_zero(self) -> None:
        """Free tier should allow access to tool at index 0."""
        assert can_access_tool("free", 0) is True

    def test_free_tier_access_tool_39(self) -> None:
        """Free tier should allow access to tool at index 39 (limit is 40)."""
        assert can_access_tool("free", 39) is True

    def test_free_tier_deny_tool_40(self) -> None:
        """Free tier should deny access to tool at index 40 (limit is 40)."""
        assert can_access_tool("free", 40) is False

    def test_free_tier_deny_tool_50(self) -> None:
        """Free tier should deny access to tool at index 50."""
        assert can_access_tool("free", 50) is False

    def test_pro_tier_access_high_tool(self) -> None:
        """Pro tier (150 tools) should allow access to tool 149."""
        assert can_access_tool("pro", 149) is True

    def test_pro_tier_deny_out_of_range(self) -> None:
        """Pro tier should deny access to tool 150 and beyond."""
        assert can_access_tool("pro", 150) is False

    def test_team_tier_access_high_tool(self) -> None:
        """Team tier (190 tools) should allow access to tool 189."""
        assert can_access_tool("team", 189) is True

    def test_team_tier_deny_out_of_range(self) -> None:
        """Team tier should deny access to tool 190 and beyond."""
        assert can_access_tool("team", 190) is False

    def test_enterprise_tier_access_tool_200(self) -> None:
        """Enterprise tier (220 tools) should allow access to tool 200."""
        assert can_access_tool("enterprise", 200) is True

    def test_enterprise_tier_access_all_tools(self) -> None:
        """Enterprise tier should allow access to all 167 standard tools."""
        # Standard loom has 167 tools (0-166)
        assert can_access_tool("enterprise", 166) is True

    def test_enterprise_tier_deny_beyond_limit(self) -> None:
        """Enterprise tier should deny access to tool 220 and beyond."""
        assert can_access_tool("enterprise", 220) is False

    def test_tool_access_with_invalid_tier(self) -> None:
        """Tool access with invalid tier should default to free tier."""
        # Free tier has 40 tools, so should deny 40
        assert can_access_tool("invalid_tier", 40) is False
        # But should allow 39
        assert can_access_tool("invalid_tier", 39) is True

    def test_tool_access_negative_index(self) -> None:
        """Tool access with negative index should be allowed (Python indexing)."""
        # Negative indices don't make sense for our use case
        # but we'll verify the behavior
        assert can_access_tool("free", -1) is True


class TestUpgradePath:
    """Tests for check_upgrade_path function."""

    def test_free_to_pro_upgrade(self) -> None:
        """Upgrade from free to pro should show positive diffs."""
        result = check_upgrade_path("free", "pro")
        assert result["from"] == "Free"
        assert result["to"] == "Pro"
        assert result["direction"] == "upgrade"
        assert result["price_diff"] == 99
        assert result["credit_diff"] == 9_500
        assert result["tool_diff"] == 110

    def test_free_to_team_upgrade(self) -> None:
        """Upgrade from free to team should show large positive diffs."""
        result = check_upgrade_path("free", "team")
        assert result["direction"] == "upgrade"
        assert result["price_diff"] == 299
        assert result["credit_diff"] == 49_500
        assert result["tool_diff"] == 150

    def test_free_to_enterprise_upgrade(self) -> None:
        """Upgrade from free to enterprise should show largest positive diffs."""
        result = check_upgrade_path("free", "enterprise")
        assert result["direction"] == "upgrade"
        assert result["price_diff"] == 999
        assert result["credit_diff"] == 199_500
        assert result["tool_diff"] == 180

    def test_pro_to_free_downgrade(self) -> None:
        """Downgrade from pro to free should show negative diffs."""
        result = check_upgrade_path("pro", "free")
        assert result["from"] == "Pro"
        assert result["to"] == "Free"
        assert result["direction"] == "downgrade"
        assert result["price_diff"] == -99
        assert result["credit_diff"] == -9_500
        assert result["tool_diff"] == -110

    def test_team_to_free_downgrade(self) -> None:
        """Downgrade from team to free should show negative diffs."""
        result = check_upgrade_path("team", "free")
        assert result["direction"] == "downgrade"
        assert result["price_diff"] == -299
        assert result["credit_diff"] == -49_500
        assert result["tool_diff"] == -150

    def test_enterprise_to_pro_downgrade(self) -> None:
        """Downgrade from enterprise to pro should show negative diffs."""
        result = check_upgrade_path("enterprise", "pro")
        assert result["direction"] == "downgrade"
        assert result["price_diff"] == -900
        assert result["credit_diff"] == -190_000
        assert result["tool_diff"] == -70

    def test_same_tier_no_change(self) -> None:
        """Changing to same tier should show zero diffs."""
        result = check_upgrade_path("pro", "pro")
        assert result["direction"] == "same"
        assert result["price_diff"] == 0
        assert result["credit_diff"] == 0
        assert result["tool_diff"] == 0

    def test_pro_to_team_upgrade(self) -> None:
        """Upgrade from pro to team should show positive diffs."""
        result = check_upgrade_path("pro", "team")
        assert result["direction"] == "upgrade"
        assert result["price_diff"] == 200
        assert result["credit_diff"] == 40_000
        assert result["tool_diff"] == 40

    def test_team_to_enterprise_upgrade(self) -> None:
        """Upgrade from team to enterprise should show positive diffs."""
        result = check_upgrade_path("team", "enterprise")
        assert result["direction"] == "upgrade"
        assert result["price_diff"] == 700
        assert result["credit_diff"] == 150_000
        assert result["tool_diff"] == 30

    def test_upgrade_path_case_insensitive(self) -> None:
        """Upgrade path should be case-insensitive."""
        result1 = check_upgrade_path("free", "pro")
        result2 = check_upgrade_path("FREE", "PRO")
        result3 = check_upgrade_path("Free", "Pro")
        assert result1 == result2 == result3

    def test_upgrade_path_invalid_tier_defaults_to_free(self) -> None:
        """Invalid tier names should default to free tier."""
        result = check_upgrade_path("invalid", "pro")
        assert result["from"] == "Free"


class TestTierImmutability:
    """Tests for tier immutability (frozen dataclasses)."""

    def test_tier_is_frozen(self) -> None:
        """Tier objects should be frozen (immutable)."""
        tier = TIERS["free"]
        with pytest.raises(AttributeError):
            tier.monthly_credits = 1000  # type: ignore

    def test_tier_features_list_frozen(self) -> None:
        """Tier features list should be frozen at object level."""
        tier = TIERS["free"]
        # The list itself is mutable, but reassigning the field should fail
        with pytest.raises(AttributeError):
            tier.features = []  # type: ignore

    def test_all_tiers_are_frozen(self) -> None:
        """All tier objects in TIERS dict should be frozen."""
        for tier_name, tier in TIERS.items():
            with pytest.raises(AttributeError):
                tier.name = "Modified"  # type: ignore


class TestTierOrdering:
    """Tests for tier ordering and progression."""

    def test_credits_increase_by_tier(self) -> None:
        """Credits should increase: free < pro < team < enterprise."""
        assert TIERS["free"].monthly_credits < TIERS["pro"].monthly_credits
        assert TIERS["pro"].monthly_credits < TIERS["team"].monthly_credits
        assert TIERS["team"].monthly_credits < TIERS["enterprise"].monthly_credits

    def test_price_increases_by_tier(self) -> None:
        """Price should increase: free < pro < team < enterprise."""
        assert TIERS["free"].price_usd < TIERS["pro"].price_usd
        assert TIERS["pro"].price_usd < TIERS["team"].price_usd
        assert TIERS["team"].price_usd < TIERS["enterprise"].price_usd

    def test_tools_limit_increases_by_tier(self) -> None:
        """Tool limit should increase: free < pro < team < enterprise."""
        assert TIERS["free"].tools_limit < TIERS["pro"].tools_limit
        assert TIERS["pro"].tools_limit < TIERS["team"].tools_limit
        assert TIERS["team"].tools_limit < TIERS["enterprise"].tools_limit

    def test_rate_limit_increases_by_tier(self) -> None:
        """Rate limit should increase: free < pro < team < enterprise."""
        assert (
            TIERS["free"].rate_limit_per_min
            < TIERS["pro"].rate_limit_per_min
        )
        assert (
            TIERS["pro"].rate_limit_per_min
            < TIERS["team"].rate_limit_per_min
        )
        assert (
            TIERS["team"].rate_limit_per_min
            < TIERS["enterprise"].rate_limit_per_min
        )


class TestTierFeatures:
    """Tests for tier features."""

    def test_free_tier_has_basic_features(self) -> None:
        """Free tier should have basic features."""
        features = TIERS["free"].features
        assert "basic_search" in features
        assert "single_engine" in features
        assert "2_llm_providers" in features

    def test_pro_tier_has_advanced_features(self) -> None:
        """Pro tier should have advanced features."""
        features = TIERS["pro"].features
        assert "all_search_engines" in features
        assert "cloudflare_bypass" in features
        assert "osint" in features

    def test_team_tier_has_dark_web_features(self) -> None:
        """Team tier should have dark web and AI safety features."""
        features = TIERS["team"].features
        assert "dark_web" in features
        assert "ai_safety" in features
        assert "career_intel" in features

    def test_enterprise_tier_has_all_features(self) -> None:
        """Enterprise tier should have all features."""
        features = TIERS["enterprise"].features
        assert "all_tools" in features
        assert "sla_99_9" in features
        assert "audit_logs" in features
        assert "compliance_exports" in features

    def test_all_tiers_have_features(self) -> None:
        """All tiers should have at least one feature."""
        for tier_name, tier in TIERS.items():
            assert len(tier.features) > 0, f"{tier_name} has no features"
            assert all(
                isinstance(f, str) for f in tier.features
            ), f"{tier_name} has non-string features"
