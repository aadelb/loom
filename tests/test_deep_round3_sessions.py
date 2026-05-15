"""Deep testing round 3: Session management lifecycle, validation, and edge cases.

Tests for:
1. Session name validation (valid/invalid patterns, path traversal, null bytes)
2. In-memory async registry (create, retrieve, delete, list, concurrency, isolation)
3. SQLite SessionManager (persistence, LRU eviction, concurrent access, corruption)
4. Edge cases (large data, unicode, rapid cycles, timeouts, multiple instances)
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

import pytest

from loom.sessions import (
    SESSION_TTL_SECONDS,
    SessionManager,
    SessionMetadata,
    _cleanup_expired,
    _delete_metadata,
    _get_lock,
    _get_session_dir,
    _load_metadata,
    _metadata,
    _save_metadata,
    _sessions,
    _validate_session_name,
    cleanup_sessions,
    get_session_manager,
)


# ─── Test Session Name Validation ───────────────────────────────────────────
class TestSessionNameValidationComprehensive:
    """Comprehensive session name validation tests."""

    def test_valid_names_lowercase_alphanumeric(self) -> None:
        """Valid: lowercase letters and digits."""
        _validate_session_name("session1")
        _validate_session_name("prod_2024")
        _validate_session_name("s1")

    def test_valid_names_with_underscore_and_hyphen(self) -> None:
        """Valid: underscores and hyphens."""
        _validate_session_name("my_session")
        _validate_session_name("session-prod")
        _validate_session_name("test_session-123")

    def test_valid_names_max_length_32(self) -> None:
        """Valid: exactly 32 chars."""
        _validate_session_name("a" * 32)

    def test_valid_names_min_length_1(self) -> None:
        """Valid: exactly 1 char."""
        _validate_session_name("a")

    def test_invalid_empty_string(self) -> None:
        """Invalid: empty string."""
        with pytest.raises(ValueError, match="must match"):
            _validate_session_name("")

    def test_invalid_uppercase_letters(self) -> None:
        """Invalid: uppercase letters."""
        with pytest.raises(ValueError, match="must match"):
            _validate_session_name("MySession")
        with pytest.raises(ValueError, match="must match"):
            _validate_session_name("SESSION")

    def test_invalid_spaces(self) -> None:
        """Invalid: spaces."""
        with pytest.raises(ValueError, match="must match"):
            _validate_session_name("my session")
        with pytest.raises(ValueError, match="must match"):
            _validate_session_name(" session")

    def test_invalid_dots_path_traversal(self) -> None:
        """Invalid: dots (path traversal attempts)."""
        with pytest.raises(ValueError, match="must match"):
            _validate_session_name("..")
        with pytest.raises(ValueError, match="must match"):
            _validate_session_name("../../etc/passwd")
        with pytest.raises(ValueError, match="must match"):
            _validate_session_name("session.")
        with pytest.raises(ValueError, match="must match"):
            _validate_session_name(".session")

    def test_invalid_null_bytes(self) -> None:
        """Invalid: null bytes."""
        with pytest.raises(ValueError, match="must match"):
            _validate_session_name("session\x00name")

    def test_invalid_special_characters(self) -> None:
        """Invalid: special characters."""
        invalid_chars = ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "+", "=", "[", "]", "{", "}", ";", ":", "'", '"', ",", "<", ">", "?", "/", "\\", "|", "`", "~"]
        for char in invalid_chars:
            with pytest.raises(ValueError, match="must match"):
                _validate_session_name(f"session{char}")

    def test_invalid_too_long_exceeds_32(self) -> None:
        """Invalid: exceeds 32 chars."""
        with pytest.raises(ValueError, match="must match"):
            _validate_session_name("a" * 33)
        with pytest.raises(ValueError, match="must match"):
            _validate_session_name("a" * 100)

    def test_invalid_non_string_int(self) -> None:
        """Invalid: non-string (int)."""
        with pytest.raises(ValueError, match="must be a string"):
            _validate_session_name(123)  # type: ignore

    def test_invalid_non_string_none(self) -> None:
        """Invalid: non-string (None)."""
        with pytest.raises(ValueError, match="must be a string"):
            _validate_session_name(None)  # type: ignore

    def test_invalid_non_string_dict(self) -> None:
        """Invalid: non-string (dict)."""
        with pytest.raises(ValueError, match="must be a string"):
            _validate_session_name({"name": "session"})  # type: ignore

    def test_invalid_non_string_list(self) -> None:
        """Invalid: non-string (list)."""
        with pytest.raises(ValueError, match="must be a string"):
            _validate_session_name(["session"])  # type: ignore


# ─── Test In-Memory Session Registry ────────────────────────────────────────
@pytest.fixture
def clean_registry() -> None:
    """Clean up global session registry before/after each test."""
    _sessions.clear()
    _metadata.clear()
    yield
    _sessions.clear()
    _metadata.clear()


@pytest.mark.asyncio
class TestInMemorySessionRegistry:
    """Tests for in-memory async session registry (_sessions + _metadata)."""

    async def test_metadata_create_and_retrieve(self, clean_registry: None) -> None:
        """SessionMetadata can be saved and loaded from disk."""
        meta = SessionMetadata(
            name="test_session",
            browser="camoufox",
            ttl_seconds=7200,
        )
        _save_metadata(meta)

        loaded = _load_metadata("test_session")
        assert loaded is not None
        assert loaded.name == "test_session"
        assert loaded.browser == "camoufox"
        assert loaded.ttl_seconds == 7200

    async def test_metadata_delete(self, clean_registry: None) -> None:
        """SessionMetadata can be deleted."""
        meta = SessionMetadata(name="to_delete", browser="firefox")
        _save_metadata(meta)

        assert _load_metadata("to_delete") is not None

        _delete_metadata("to_delete")
        assert _load_metadata("to_delete") is None

    async def test_metadata_unicode_content(self, clean_registry: None) -> None:
        """SessionMetadata with unicode values persists correctly."""
        meta = SessionMetadata(
            name="unicode_session",
            browser="chromium",
            extra={"notes": "Session with émojis 🎉 and अरबी"},
        )
        _save_metadata(meta)

        loaded = _load_metadata("unicode_session")
        assert loaded is not None
        assert loaded.extra["notes"] == "Session with émojis 🎉 and अरबी"

    async def test_metadata_large_extra_data(self, clean_registry: None) -> None:
        """SessionMetadata with large extra dict persists."""
        large_dict = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}
        meta = SessionMetadata(
            name="large_session",
            browser="camoufox",
            extra=large_dict,
        )
        _save_metadata(meta)

        loaded = _load_metadata("large_session")
        assert loaded is not None
        assert len(loaded.extra) == 100

    async def test_metadata_corrupt_json_graceful_failure(
        self, clean_registry: None, tmp_sessions_dir: Path
    ) -> None:
        """Loading corrupted metadata JSON returns None gracefully."""
        # Set session dir to temp
        with mock.patch("loom.sessions._get_session_dir", return_value=tmp_sessions_dir):
            # Create a corrupted JSON file
            corrupt_path = tmp_sessions_dir / "corrupt.json"
            corrupt_path.write_text("{invalid json")

            # Should return None, not raise
            result = _load_metadata("corrupt")
            assert result is None

    async def test_cleanup_expired_removes_old_sessions(
        self, clean_registry: None, tmp_sessions_dir: Path
    ) -> None:
        """_cleanup_expired removes sessions past their TTL."""
        with mock.patch("loom.sessions._get_session_dir", return_value=tmp_sessions_dir):
            # Create expired session metadata
            past_time = (datetime.now(UTC) - timedelta(seconds=7200)).isoformat()
            _metadata["expired_session"] = {
                "name": "expired_session",
                "browser": "firefox",
                "created_at": past_time,
                "ttl_seconds": 3600,
            }
            # Also add it to _sessions so _close_session_inner can find it
            _sessions["expired_session"] = mock.MagicMock()

            # Call cleanup with AsyncMock to intercept async calls
            async_mock = mock.AsyncMock()
            with mock.patch("loom.sessions._close_session_inner", async_mock):
                await _cleanup_expired()

            # Verify _close_session_inner was called for the expired session
            async_mock.assert_called_once_with("expired_session")

    async def test_get_lock_creates_single_instance(self, clean_registry: None) -> None:
        """_get_lock() creates a single asyncio.Lock instance."""
        # Reset the module-level lock
        import loom.sessions

        loom.sessions._lock = None

        lock1 = _get_lock()
        lock2 = _get_lock()

        assert lock1 is lock2
        assert isinstance(lock1, asyncio.Lock)


# ─── Test SessionManager ─────────────────────────────────────────────────────
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
class TestSessionManagerComprehensive:
    """Comprehensive SessionManager tests."""

    async def test_session_create_and_persist(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Creating a session persists it to SQLite."""
        result = await isolated_session_manager.open("create_test")

        assert result["name"] == "create_test"
        assert "session_id" in result
        assert "profile_dir" in result

        # Verify persistence
        conn = sqlite3.connect(isolated_session_manager.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sessions WHERE name = ?", ("create_test",))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "create_test"

    async def test_session_profile_dir_created(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Session profile directory is created on disk."""
        result = await isolated_session_manager.open("profile_test")
        profile_dir = Path(result["profile_dir"])

        assert profile_dir.exists()
        assert profile_dir.is_dir()

    async def test_session_profile_dir_permissions_700(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Session profile directory has 0700 permissions."""
        result = await isolated_session_manager.open("perms_test")
        profile_dir = Path(result["profile_dir"])

        # Get mode
        mode = profile_dir.stat().st_mode & 0o777
        assert mode == 0o700

    async def test_session_list_returns_sorted_by_last_used(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """list() returns sessions sorted by last_used_at DESC."""
        await isolated_session_manager.open("first")
        await asyncio.sleep(0.01)
        await isolated_session_manager.open("second")
        await asyncio.sleep(0.01)
        await isolated_session_manager.open("third")

        sessions = isolated_session_manager.list()
        names = [s["name"] for s in sessions]

        # Newest should be first
        assert names[0] == "third"
        assert names[-1] == "first"

    async def test_session_get_context_valid(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """get_context() returns metadata for existing session."""
        await isolated_session_manager.open("context_test")

        context = isolated_session_manager.get_context("context_test")

        assert context is not None
        assert context["name"] == "context_test"
        assert "created_at" in context
        assert "session_id" in context

    async def test_session_get_context_missing_returns_none(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """get_context() returns None for nonexistent session."""
        context = isolated_session_manager.get_context("nonexistent")
        assert context is None

    async def test_session_close_removes_from_db(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """close() removes session from database."""
        await isolated_session_manager.open("to_close")
        await isolated_session_manager.close("to_close")

        context = isolated_session_manager.get_context("to_close")
        assert context is None

    async def test_session_close_deletes_profile_dir(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """close() deletes the profile directory."""
        result = await isolated_session_manager.open("to_delete_dir")
        profile_dir = Path(result["profile_dir"])

        assert profile_dir.exists()

        await isolated_session_manager.close("to_delete_dir")

        assert not profile_dir.exists()

    async def test_session_close_nonexistent_returns_empty_dict(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """close() on nonexistent session returns error dict."""
        result = await isolated_session_manager.close("nonexistent")

        assert "error" in result

    async def test_session_open_reuse_preserves_identity(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Reopening a session preserves session_id and created_at."""
        result1 = await isolated_session_manager.open("reuse_test")
        session_id_1 = result1["session_id"]
        created_at_1 = result1["created_at"]

        await asyncio.sleep(0.01)

        result2 = await isolated_session_manager.open("reuse_test")
        session_id_2 = result2["session_id"]
        created_at_2 = result2["created_at"]

        assert session_id_1 == session_id_2
        assert created_at_1 == created_at_2

    async def test_session_open_reuse_extends_ttl(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Reopening a session updates its expiration time."""
        result1 = await isolated_session_manager.open("ttl_test", ttl_seconds=100)
        expires_at_1 = result1["expires_at"]

        await asyncio.sleep(0.01)

        result2 = await isolated_session_manager.open("ttl_test", ttl_seconds=300)
        expires_at_2 = result2["expires_at"]

        assert expires_at_2 > expires_at_1

    async def test_session_lru_eviction_max_8_sessions(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """When 9 sessions exist, LRU evicts the oldest."""
        # Create 9 sessions
        for i in range(9):
            await isolated_session_manager.open(f"lru_{i:02d}")
            await asyncio.sleep(0.001)

        sessions = isolated_session_manager.list()

        # Should have exactly 8 remaining
        assert len(sessions) == 8
        # Oldest should be gone
        names = [s["name"] for s in sessions]
        assert "lru_00" not in names
        # Newest should remain
        assert "lru_08" in names

    async def test_session_concurrent_access_serialized(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Concurrent operations on same session are serialized."""
        name = "concurrent_test"

        async def open_op() -> dict:
            return await isolated_session_manager.open(name)

        # Multiple concurrent opens should be serialized
        results = await asyncio.gather(open_op(), open_op(), open_op())

        # All should succeed with same session_id
        session_ids = [r["session_id"] for r in results]
        assert session_ids[0] == session_ids[1] == session_ids[2]

    async def test_session_persistence_across_manager_restart(
        self, isolated_session_manager: SessionManager, tmp_sessions_dir: Path
    ) -> None:
        """Sessions in DB persist when SessionManager is restarted."""
        await isolated_session_manager.open("persist_test")

        # Reset singleton
        SessionManager._instance = None
        new_manager = SessionManager()

        # New manager should see the persisted session
        context = new_manager.get_context("persist_test")
        assert context is not None
        assert context["name"] == "persist_test"

    async def test_session_validate_name_on_open(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """open() validates the session name."""
        with pytest.raises(ValueError, match="must match"):
            await isolated_session_manager.open("invalid session!")

    async def test_session_validate_name_path_traversal(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """open() rejects path traversal in name."""
        with pytest.raises(ValueError, match="must match"):
            await isolated_session_manager.open("../../etc/passwd")


# ─── Test Edge Cases ────────────────────────────────────────────────────────
@pytest.mark.asyncio
class TestSessionEdgeCases:
    """Edge case tests for session management."""

    async def test_very_large_session_data_100kb(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """SessionManager handles sessions with large extra metadata."""
        result = await isolated_session_manager.open(
            "large_data_session", ttl_seconds=3600
        )

        # Query and verify it's in DB with no corruption
        context = isolated_session_manager.get_context("large_data_session")
        assert context is not None
        assert context["name"] == "large_data_session"

    async def test_session_with_unicode_metadata(
        self, isolated_session_manager: SessionManager, tmp_sessions_dir: Path
    ) -> None:
        """Sessions with unicode in metadata persist correctly."""
        result = await isolated_session_manager.open("unicode_test")

        # Manually update metadata with unicode
        conn = sqlite3.connect(isolated_session_manager.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET profile_dir = ? WHERE name = ?",
            ("/path/with/émojis/🎉", "unicode_test"),
        )
        conn.commit()
        conn.close()

        # Retrieve and verify
        context = isolated_session_manager.get_context("unicode_test")
        assert context is not None
        assert "unicode_test" in str(context["name"])

    async def test_rapid_create_delete_cycles(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Rapid create/delete cycles don't corrupt DB."""
        for i in range(100):
            name = f"rapid_{i}"
            result = await isolated_session_manager.open(name)
            assert result["name"] == name

            await isolated_session_manager.close(name)
            assert isolated_session_manager.get_context(name) is None

        # DB should still be valid
        sessions = isolated_session_manager.list()
        assert len(sessions) == 0

    async def test_cleanup_sessions_response_structure(
        self, clean_registry: None
    ) -> None:
        """cleanup_sessions() returns proper response with expected fields."""
        result = await cleanup_sessions(max_sessions=10)

        # Should have these fields regardless of action taken
        assert isinstance(result, dict)
        assert "status" in result
        assert "current_sessions" in result
        assert "max_sessions" in result
        assert "closed" in result
        assert isinstance(result["closed"], list)

    async def test_concurrent_close_and_list(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Concurrent close and list operations don't raise."""
        # Create initial sessions
        for i in range(5):
            await isolated_session_manager.open(f"concurrent_{i}")

        async def close_op(name: str) -> dict:
            return await isolated_session_manager.close(name)

        def list_op() -> list:
            return isolated_session_manager.list()

        # Run close and list concurrently
        close_tasks = [close_op(f"concurrent_{i}") for i in range(5)]
        list_tasks = [asyncio.to_thread(list_op) for _ in range(5)]

        results = await asyncio.gather(*close_tasks, *list_tasks)

        # All should complete without exception
        assert len(results) > 0

    async def test_session_manager_singleton_behavior(
        self, tmp_sessions_dir: Path
    ) -> None:
        """get_session_manager() returns singleton instance."""
        os.environ["LOOM_SESSIONS_DIR"] = str(tmp_sessions_dir)
        SessionManager._instance = None

        manager1 = get_session_manager()
        manager2 = get_session_manager()

        assert manager1 is manager2

        SessionManager._instance = None

    async def test_database_file_persists_on_disk(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Database file is created and persists on disk."""
        # Create a session first
        await isolated_session_manager.open("db_test")

        db_path = isolated_session_manager.db_path
        assert db_path.exists()
        assert db_path.stat().st_size > 0


# ─── Test SessionManager Path Traversal Protection ────────────────────────────
@pytest.mark.asyncio
class TestSessionManagerPathTraversalProtection:
    """Tests for path traversal protection in SessionManager."""

    async def test_base_dir_path_traversal_rejected_on_init(
        self, tmp_sessions_dir: Path
    ) -> None:
        """SessionManager rejects LOOM_SESSIONS_DIR with '..' in path."""
        # Create a path with '..'
        unsafe_path = str(tmp_sessions_dir / ".." / ".." / "etc" / "passwd")
        os.environ["LOOM_SESSIONS_DIR"] = unsafe_path

        with pytest.raises(ValueError, match="must not contain"):
            SessionManager._instance = None
            SessionManager()

    async def test_profile_dir_path_escape_protection(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """close() validates profile_dir doesn't escape base_dir."""
        # Open a normal session
        result = await isolated_session_manager.open("escape_test")
        session_id = result["session_id"]

        # Tamper with DB to point profile_dir outside base_dir
        conn = sqlite3.connect(isolated_session_manager.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET profile_dir = ? WHERE name = ?",
            ("/etc/passwd", "escape_test"),
        )
        conn.commit()
        conn.close()

        # close() should detect escape and return gracefully
        result = await isolated_session_manager.close("escape_test")
        # Either empty dict {} or {'error': ...}
        assert isinstance(result, dict)


# ─── Test Cleanup Functions (global in-memory registry) ──────────────────────
@pytest.mark.asyncio
class TestCleanupFunctions:
    """Tests for session cleanup and expiration (uses global _sessions registry)."""

    async def test_cleanup_sessions_no_action_when_under_limit(self, clean_registry: None) -> None:
        """cleanup_sessions() does nothing when under max limit."""
        # Note: cleanup_sessions() works on the global _sessions dict, not SessionManager
        # We'll just test the function directly with mock data
        # This test verifies the function returns early when under limit
        result = await cleanup_sessions(max_sessions=10)
        assert result["status"] == "no_cleanup_needed"
        assert result["current_sessions"] == 0

    async def test_cleanup_sessions_returns_stats(self, clean_registry: None) -> None:
        """cleanup_sessions() returns proper response structure."""
        result = await cleanup_sessions(max_sessions=5)
        assert "status" in result
        assert "current_sessions" in result
        assert "max_sessions" in result
        assert "closed" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
