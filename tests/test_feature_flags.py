"""Tests for the feature flags system."""

from __future__ import annotations

import os
from datetime import datetime

import pytest

from loom.feature_flags import (
    DEFAULT_FLAGS,
    FeatureFlags,
    get_feature_flags,
    research_feature_flags,
)


class TestFeatureFlags:
    """Unit tests for FeatureFlags class."""

    def test_init_defaults(self) -> None:
        """Test that FeatureFlags initializes with default values."""
        ff = FeatureFlags()
        assert ff.is_enabled("token_economy") is False
        assert ff.is_enabled("auto_model_routing") is True
        assert ff.is_enabled("refusal_auto_reframe") is True
        assert ff.is_enabled("content_sanitizer") is True
        assert ff.is_enabled("per_tool_rate_limit") is True
        assert ff.is_enabled("lazy_loading") is False
        assert ff.is_enabled("batch_queue") is True
        assert ff.is_enabled("experimental_privacy_tools") is False

    def test_list_all(self) -> None:
        """Test listing all flags."""
        ff = FeatureFlags()
        flags = ff.list_all()
        assert isinstance(flags, dict)
        assert len(flags) == len(DEFAULT_FLAGS)
        assert "token_economy" in flags
        assert "per_tool_rate_limit" in flags

    def test_enable_flag(self) -> None:
        """Test enabling a flag."""
        ff = FeatureFlags()
        assert ff.is_enabled("lazy_loading") is False
        success = ff.enable("lazy_loading")
        assert success is True
        assert ff.is_enabled("lazy_loading") is True

    def test_disable_flag(self) -> None:
        """Test disabling a flag."""
        ff = FeatureFlags()
        assert ff.is_enabled("token_economy") is False
        ff.enable("token_economy")
        assert ff.is_enabled("token_economy") is True
        success = ff.disable("token_economy")
        assert success is True
        assert ff.is_enabled("token_economy") is False

    def test_enable_unknown_flag(self) -> None:
        """Test enabling a flag that doesn't exist."""
        ff = FeatureFlags()
        success = ff.enable("nonexistent_flag")
        assert success is False

    def test_disable_unknown_flag(self) -> None:
        """Test disabling a flag that doesn't exist."""
        ff = FeatureFlags()
        success = ff.disable("nonexistent_flag")
        assert success is False

    def test_is_enabled_unknown_flag(self) -> None:
        """Test checking an unknown flag returns False."""
        ff = FeatureFlags()
        assert ff.is_enabled("nonexistent_flag") is False

    def test_reset_to_defaults(self) -> None:
        """Test resetting all flags to defaults."""
        ff = FeatureFlags()
        ff.enable("lazy_loading")
        ff.disable("token_economy")
        ff.enable("experimental_privacy_tools")

        ff.reset_to_defaults()

        assert ff.is_enabled("lazy_loading") is False
        assert ff.is_enabled("token_economy") is False
        assert ff.is_enabled("experimental_privacy_tools") is False

    def test_load_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading flags from LOOM_FEATURE_FLAGS environment variable."""
        monkeypatch.setenv("LOOM_FEATURE_FLAGS", "token_economy,lazy_loading")
        ff = FeatureFlags()

        assert ff.is_enabled("token_economy") is True
        assert ff.is_enabled("lazy_loading") is True
        assert ff.is_enabled("auto_model_routing") is True  # Still enabled by default

    def test_load_from_env_with_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading flags with whitespace."""
        monkeypatch.setenv("LOOM_FEATURE_FLAGS", "token_economy , lazy_loading , experimental_privacy_tools")
        ff = FeatureFlags()

        assert ff.is_enabled("token_economy") is True
        assert ff.is_enabled("lazy_loading") is True
        assert ff.is_enabled("experimental_privacy_tools") is True

    def test_load_from_env_unknown_flag(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that unknown flags in env are logged but don't crash."""
        monkeypatch.setenv("LOOM_FEATURE_FLAGS", "token_economy,nonexistent_flag")
        ff = FeatureFlags()

        assert ff.is_enabled("token_economy") is True
        # Unknown flag should be logged but not added
        assert ff.is_enabled("nonexistent_flag") is False


class TestResearchFeatureFlagsTool:
    """Tests for research_feature_flags MCP tool."""

    def test_list_action(self) -> None:
        """Test the 'list' action."""
        result = research_feature_flags(action="list")
        assert result["action"] == "list"
        assert isinstance(result["flags"], dict)
        assert "timestamp" in result
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(result["timestamp"])

    def test_enable_action(self) -> None:
        """Test the 'enable' action."""
        # First, disable the flag
        ff = get_feature_flags()
        ff.disable("token_economy")

        result = research_feature_flags(action="enable", flag="token_economy")
        assert result["action"] == "enable"
        assert result["flag"] == "token_economy"
        assert result["enabled"] is True
        assert "timestamp" in result

    def test_disable_action(self) -> None:
        """Test the 'disable' action."""
        # First, enable the flag
        ff = get_feature_flags()
        ff.enable("token_economy")

        result = research_feature_flags(action="disable", flag="token_economy")
        assert result["action"] == "disable"
        assert result["flag"] == "token_economy"
        assert result["enabled"] is False
        assert "timestamp" in result

    def test_enable_missing_flag_param(self) -> None:
        """Test 'enable' without flag parameter."""
        result = research_feature_flags(action="enable", flag=None)
        assert "error" in result
        assert "required" in result["error"].lower()

    def test_disable_missing_flag_param(self) -> None:
        """Test 'disable' without flag parameter."""
        result = research_feature_flags(action="disable", flag=None)
        assert "error" in result
        assert "required" in result["error"].lower()

    def test_unknown_flag(self) -> None:
        """Test with unknown flag name."""
        result = research_feature_flags(action="enable", flag="nonexistent_flag")
        assert "error" in result
        assert "unknown" in result["error"].lower()

    def test_unknown_action(self) -> None:
        """Test with unknown action."""
        result = research_feature_flags(action="invalid_action")  # type: ignore[arg-type]
        assert "error" in result
        assert "unknown action" in result["error"].lower()

    def test_default_action_is_list(self) -> None:
        """Test that default action is 'list'."""
        result = research_feature_flags()
        assert result["action"] == "list"
        assert isinstance(result["flags"], dict)


class TestGetFeatureFlagsSingleton:
    """Tests for the get_feature_flags singleton."""

    def test_singleton_instance(self) -> None:
        """Test that get_feature_flags returns the same instance."""
        ff1 = get_feature_flags()
        ff2 = get_feature_flags()
        assert ff1 is ff2

    def test_singleton_changes_persist(self) -> None:
        """Test that changes to singleton instance persist."""
        ff1 = get_feature_flags()
        ff1.enable("token_economy")

        ff2 = get_feature_flags()
        assert ff2.is_enabled("token_economy") is True
