"""Comprehensive lifecycle tests for sessions, config, and health check (REQ-049).

Tests session_open→list→close lifecycle, config_set→get round-trip, and
health_check status responses.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import pytest

from loom.config import CONFIG, ConfigModel, load_config, research_config_get, research_config_set, set
from loom.sessions import SessionManager, research_session_close, research_session_list, research_session_open


# ─── Session Lifecycle Tests ──────────────────────────────────────────────────


@pytest.fixture
def isolated_session_manager(tmp_sessions_dir: Path) -> SessionManager:
    """Create a SessionManager with isolated temp directory."""
    os.environ["LOOM_SESSIONS_DIR"] = str(tmp_sessions_dir)
    SessionManager._instance = None
    manager = SessionManager()
    yield manager
    SessionManager._instance = None
    if "LOOM_SESSIONS_DIR" in os.environ:
        del os.environ["LOOM_SESSIONS_DIR"]


@pytest.mark.asyncio
class TestSessionLifecycle:
    """Test session_open→list→close lifecycle."""

    async def test_session_open_returns_session_info(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Test 1: Open a session with valid name → returns session info."""
        result = await isolated_session_manager.open("valid_session")

        assert result["name"] == "valid_session"
        assert "session_id" in result
        assert "created_at" in result
        assert "expires_at" in result
        assert "browser" in result
        assert "profile_dir" in result
        assert Path(result["profile_dir"]).exists()

    async def test_session_list_includes_opened_session(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Test 2: List sessions → includes the opened session."""
        await isolated_session_manager.open("list_test_1")
        await isolated_session_manager.open("list_test_2")

        sessions = isolated_session_manager.list()

        names = [s["name"] for s in sessions]
        assert "list_test_1" in names
        assert "list_test_2" in names
        assert len(sessions) >= 2

    async def test_session_close_returns_success(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Test 3: Close session → returns success."""
        await isolated_session_manager.open("to_close")

        result = await isolated_session_manager.close("to_close")

        # close() returns empty dict {} on success
        assert isinstance(result, dict)
        assert "error" not in result

    async def test_session_list_after_close_session_no_longer_listed(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Test 4: List after close → session no longer listed."""
        await isolated_session_manager.open("removable_session")
        sessions_before = isolated_session_manager.list()
        names_before = [s["name"] for s in sessions_before]
        assert "removable_session" in names_before

        await isolated_session_manager.close("removable_session")

        sessions_after = isolated_session_manager.list()
        names_after = [s["name"] for s in sessions_after]
        assert "removable_session" not in names_after

    async def test_session_open_invalid_name_with_special_chars_rejected(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Test 5: Open with invalid name (special chars) → rejected."""
        with pytest.raises(ValueError, match="must match"):
            await isolated_session_manager.open("invalid!@#$session")

    async def test_session_open_invalid_name_uppercase_rejected(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Test 5b: Open with invalid name (uppercase) → rejected."""
        with pytest.raises(ValueError, match="must match"):
            await isolated_session_manager.open("InvalidSession")

    async def test_session_open_invalid_name_too_long_rejected(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Test 5c: Open with invalid name (too long) → rejected."""
        with pytest.raises(ValueError, match="must match"):
            await isolated_session_manager.open("a" * 33)

    async def test_session_open_invalid_name_empty_rejected(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Test 5d: Open with empty name → rejected."""
        with pytest.raises(ValueError, match="must match"):
            await isolated_session_manager.open("")

    async def test_session_open_duplicate_name_reuses_and_extends_ttl(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Test 6: Open duplicate name → reuses session and extends TTL."""
        result1 = await isolated_session_manager.open("duplicate_test", ttl_seconds=100)
        session_id_1 = result1["session_id"]
        expires_1 = result1["expires_at"]

        await asyncio.sleep(0.01)

        result2 = await isolated_session_manager.open("duplicate_test", ttl_seconds=200)
        session_id_2 = result2["session_id"]
        expires_2 = result2["expires_at"]

        # Session IDs must match (same session)
        assert session_id_1 == session_id_2
        # Expiration should have been extended (later expiry time)
        assert expires_2 > expires_1
        # Both calls should return success
        assert "error" not in result1
        assert "error" not in result2


# ─── Config Lifecycle Tests ──────────────────────────────────────────────────


@pytest.fixture
def isolated_config(tmp_config_path: Path) -> None:
    """Setup and teardown isolated config for tests."""
    # Create config file with defaults
    tmp_config_path.parent.mkdir(parents=True, exist_ok=True)
    defaults = ConfigModel().model_dump()
    tmp_config_path.write_text(json.dumps(defaults))

    # Load it
    old_path = os.environ.get("LOOM_CONFIG_PATH")
    os.environ["LOOM_CONFIG_PATH"] = str(tmp_config_path)
    load_config(tmp_config_path)

    yield

    # Cleanup
    CONFIG.clear()
    if old_path:
        os.environ["LOOM_CONFIG_PATH"] = old_path
    else:
        os.environ.pop("LOOM_CONFIG_PATH", None)


class TestConfigLifecycle:
    """Test config_set→get round-trip."""

    def test_config_get_returns_current_values(self, isolated_config: None) -> None:
        """Test 7: Get config returns current values."""
        result = research_config_get()

        assert isinstance(result, dict)
        assert "SPIDER_CONCURRENCY" in result
        assert "CACHE_TTL_DAYS" in result
        assert "LLM_CASCADE_ORDER" in result

    def test_config_get_single_key(self, isolated_config: None) -> None:
        """Test 7b: Get config with key parameter returns single entry."""
        result = research_config_get("SPIDER_CONCURRENCY")

        assert isinstance(result, dict)
        assert "SPIDER_CONCURRENCY" in result
        assert len(result) == 1

    def test_config_set_persists_value(self, tmp_config_path: Path, isolated_config: None) -> None:
        """Test 8: Set a config value → persists."""
        result = research_config_set("SPIDER_CONCURRENCY", 12)

        assert result["key"] == "SPIDER_CONCURRENCY"
        assert result["new"] == 12
        assert "persisted_at" in result

        # Verify it was actually persisted
        saved_config = json.loads(tmp_config_path.read_text())
        assert saved_config["SPIDER_CONCURRENCY"] == 12

    def test_config_get_after_set_returns_new_value(
        self, tmp_config_path: Path, isolated_config: None
    ) -> None:
        """Test 9: Get after set → returns new value."""
        old_value = research_config_get("CACHE_TTL_DAYS")["CACHE_TTL_DAYS"]
        assert old_value == 30  # Default

        research_config_set("CACHE_TTL_DAYS", 60)

        new_result = research_config_get("CACHE_TTL_DAYS")
        assert new_result["CACHE_TTL_DAYS"] == 60

    def test_config_set_invalid_value_returns_error(
        self, isolated_config: None
    ) -> None:
        """Test 10: Set with invalid value → appropriate error."""
        # SPIDER_CONCURRENCY must be 1-20
        result = research_config_set("SPIDER_CONCURRENCY", 100)

        assert "error" in result

    def test_config_set_value_too_low_returns_error(
        self, isolated_config: None
    ) -> None:
        """Test 10b: Set with value below minimum → appropriate error."""
        # SPIDER_CONCURRENCY minimum is 1
        result = research_config_set("SPIDER_CONCURRENCY", 0)

        assert "error" in result

    def test_config_set_unknown_key_persists_extra_field(
        self, tmp_config_path: Path, isolated_config: None
    ) -> None:
        """Test 10c: ConfigModel allows extra fields, so unknown keys persist."""
        # ConfigModel has extra="allow", so setting a custom key succeeds
        result = research_config_set("CUSTOM_USER_FIELD", "custom_value")

        # Should succeed and persist
        assert "error" not in result
        assert result["new"] == "custom_value"

        # Verify it was persisted
        saved = json.loads(tmp_config_path.read_text())
        assert saved.get("CUSTOM_USER_FIELD") == "custom_value"

    def test_config_has_expected_defaults(self, isolated_config: None) -> None:
        """Test 11: Config has expected defaults (LLM_CASCADE_ORDER, etc.)."""
        result = research_config_get()

        # Verify key defaults exist
        assert result["SPIDER_CONCURRENCY"] == 10
        assert result["EXTERNAL_TIMEOUT_SECS"] == 30
        assert result["MAX_CHARS_HARD_CAP"] == 200_000
        assert result["CACHE_TTL_DAYS"] == 30
        assert isinstance(result["LLM_CASCADE_ORDER"], list)
        assert len(result["LLM_CASCADE_ORDER"]) > 0


# ─── Health Check Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health_check returns status with expected fields."""

    async def test_health_check_returns_dict_with_status(self) -> None:
        """Test 12: Health check returns dict with status field."""
        # Import here to avoid circular deps
        from loom.server import research_health_check

        result = await research_health_check()

        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] in ("healthy", "degraded", "unhealthy")

    async def test_health_check_has_tool_count(self) -> None:
        """Test 13: Health check has tool_count."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert "tool_count" in result
        assert isinstance(result["tool_count"], int)
        assert result["tool_count"] > 0

    async def test_health_check_has_uptime_seconds(self) -> None:
        """Test 13b: Health check has uptime_seconds."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert "uptime_seconds" in result
        assert isinstance(result["uptime_seconds"], (int, float))

    async def test_health_check_has_timestamp(self) -> None:
        """Test 13c: Health check has ISO 8601 timestamp."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert "timestamp" in result
        # Verify it's a valid ISO format string
        assert "T" in result["timestamp"]

    async def test_health_check_has_version(self) -> None:
        """Test 13d: Health check has version field."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert "version" in result

    async def test_health_check_has_llm_providers(self) -> None:
        """Test 13e: Health check includes LLM provider statuses."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert "llm_providers" in result
        assert isinstance(result["llm_providers"], dict)

    async def test_health_check_has_search_providers(self) -> None:
        """Test 13f: Health check includes search provider statuses."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert "search_providers" in result
        assert isinstance(result["search_providers"], dict)

    async def test_health_check_has_cache_stats(self) -> None:
        """Test 13g: Health check includes cache stats."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert "cache" in result
        assert isinstance(result["cache"], dict)

    async def test_health_check_has_sessions(self) -> None:
        """Test 13h: Health check includes session count."""
        from loom.server import research_health_check

        result = await research_health_check()

        assert "sessions" in result
        assert isinstance(result["sessions"], dict)


# ─── Integration: Complete Lifecycle Test ────────────────────────────────────


@pytest.mark.asyncio
class TestCompleteLifecycle:
    """End-to-end session+config lifecycle integration test."""

    async def test_complete_session_lifecycle_flow(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Complete flow: open → list → verify → close → re-list → verify gone."""
        # Step 1: Open session
        open_result = await isolated_session_manager.open("e2e_test_session")
        assert open_result["name"] == "e2e_test_session"

        # Step 2: List includes session
        list_result = isolated_session_manager.list()
        names = [s["name"] for s in list_result]
        assert "e2e_test_session" in names

        # Step 3: Verify session properties
        session = isolated_session_manager.get_context("e2e_test_session")
        assert session is not None
        assert session["name"] == "e2e_test_session"

        # Step 4: Close session
        close_result = await isolated_session_manager.close("e2e_test_session")
        assert "error" not in close_result

        # Step 5: List no longer includes session
        list_result_after = isolated_session_manager.list()
        names_after = [s["name"] for s in list_result_after]
        assert "e2e_test_session" not in names_after

        # Step 6: get_context returns None
        session_after = isolated_session_manager.get_context("e2e_test_session")
        assert session_after is None

    def test_complete_config_lifecycle_flow(
        self, tmp_config_path: Path, isolated_config: None
    ) -> None:
        """Complete flow: get → set → get → verify persisted."""
        # Step 1: Get initial value
        get1 = research_config_get("CACHE_TTL_DAYS")
        initial = get1["CACHE_TTL_DAYS"]
        assert initial == 30

        # Step 2: Set new value
        set_result = research_config_set("CACHE_TTL_DAYS", 45)
        assert set_result["new"] == 45
        assert "error" not in set_result

        # Step 3: Get new value
        get2 = research_config_get("CACHE_TTL_DAYS")
        assert get2["CACHE_TTL_DAYS"] == 45

        # Step 4: Verify persisted to disk
        saved = json.loads(tmp_config_path.read_text())
        assert saved["CACHE_TTL_DAYS"] == 45


# ─── Error Handling Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling in lifecycle operations."""

    async def test_close_nonexistent_session_returns_error(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Closing nonexistent session returns error dict."""
        result = await isolated_session_manager.close("does_not_exist")

        assert "error" in result
        assert "not found" in result["error"].lower()

    async def test_get_context_nonexistent_returns_none(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """get_context for nonexistent session returns None."""
        result = isolated_session_manager.get_context("does_not_exist")

        assert result is None

    def test_config_get_with_unknown_key_returns_error(
        self, isolated_config: None
    ) -> None:
        """Getting an unknown config key returns error."""
        result = research_config_get("DOES_NOT_EXIST_KEY")

        assert "error" in result


# ─── Boundary Condition Tests ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestBoundaryConditions:
    """Test boundary conditions in lifecycle operations."""

    async def test_session_name_exactly_32_chars_accepted(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Session name of exactly 32 chars is accepted."""
        name = "a" * 32
        result = await isolated_session_manager.open(name)

        assert result["name"] == name
        assert "error" not in result

    async def test_session_name_33_chars_rejected(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Session name of 33 chars is rejected."""
        name = "a" * 33

        with pytest.raises(ValueError):
            await isolated_session_manager.open(name)

    async def test_session_name_single_char_accepted(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Session name of single lowercase char is accepted."""
        result = await isolated_session_manager.open("a")

        assert result["name"] == "a"

    async def test_session_name_with_hyphens_accepted(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Session name with hyphens is accepted."""
        result = await isolated_session_manager.open("my-test-session")

        assert result["name"] == "my-test-session"

    async def test_session_name_with_underscores_accepted(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Session name with underscores is accepted."""
        result = await isolated_session_manager.open("my_test_session")

        assert result["name"] == "my_test_session"

    def test_config_spider_concurrency_minimum_boundary(
        self, isolated_config: None
    ) -> None:
        """Config SPIDER_CONCURRENCY minimum (1) is accepted."""
        result = research_config_set("SPIDER_CONCURRENCY", 1)

        assert result["new"] == 1
        assert "error" not in result

    def test_config_spider_concurrency_maximum_boundary(
        self, isolated_config: None
    ) -> None:
        """Config SPIDER_CONCURRENCY maximum (20) is accepted."""
        result = research_config_set("SPIDER_CONCURRENCY", 20)

        assert result["new"] == 20
        assert "error" not in result

    def test_config_cache_ttl_maximum_boundary(
        self, isolated_config: None
    ) -> None:
        """Config CACHE_TTL_DAYS maximum (365) is accepted."""
        result = research_config_set("CACHE_TTL_DAYS", 365)

        assert result["new"] == 365
        assert "error" not in result

    def test_config_cache_ttl_minimum_boundary(
        self, isolated_config: None
    ) -> None:
        """Config CACHE_TTL_DAYS minimum (1) is accepted."""
        result = research_config_set("CACHE_TTL_DAYS", 1)

        assert result["new"] == 1
        assert "error" not in result
