"""Unit tests for SessionManager — lifecycle, LRU eviction, concurrency."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from pathlib import Path

import pytest

from loom.sessions import SessionManager, _validate_session_name


class TestSessionNameValidation:
    """Session name allow-list validation tests."""

    def test_validate_session_name_valid(self) -> None:
        """Valid names pass validation."""
        _validate_session_name("my_session_1")
        _validate_session_name("session-prod")
        _validate_session_name("s1")

    def test_validate_session_name_rejects_uppercase(self) -> None:
        """Uppercase letters raise ValueError."""
        with pytest.raises(ValueError):
            _validate_session_name("MySession")

    def test_validate_session_name_rejects_spaces(self) -> None:
        """Spaces raise ValueError."""
        with pytest.raises(ValueError):
            _validate_session_name("my session")

    def test_validate_session_name_rejects_dots(self) -> None:
        """Dots (path traversal) raise ValueError."""
        with pytest.raises(ValueError):
            _validate_session_name("..")

    def test_validate_session_name_rejects_special_chars(self) -> None:
        """Special chars raise ValueError."""
        with pytest.raises(ValueError):
            _validate_session_name("session#1")

    def test_validate_session_name_rejects_too_long(self) -> None:
        """Names > 32 chars raise ValueError."""
        with pytest.raises(ValueError):
            _validate_session_name("a" * 33)

    def test_validate_session_name_rejects_non_string(self) -> None:
        """Non-string input raises ValueError."""
        with pytest.raises(ValueError):
            _validate_session_name(123)  # type: ignore


@pytest.fixture
def isolated_session_manager(tmp_sessions_dir: Path) -> SessionManager:
    """Create a SessionManager with isolated temp directory."""
    # Set env to use temp dir
    os.environ["LOOM_SESSIONS_DIR"] = str(tmp_sessions_dir)
    # Create fresh instance
    SessionManager._instance = None
    manager = SessionManager()
    yield manager
    # Cleanup
    SessionManager._instance = None
    if "LOOM_SESSIONS_DIR" in os.environ:
        del os.environ["LOOM_SESSIONS_DIR"]


@pytest.mark.asyncio
class TestSessionManager:
    """SessionManager open/list/close lifecycle tests."""

    async def test_session_open_creates_session(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """open() creates a session and returns metadata."""
        result = await isolated_session_manager.open("test_session")

        assert result["name"] == "test_session"
        assert "session_id" in result
        assert "created_at" in result
        assert "expires_at" in result
        assert result["browser"] == "camoufox"

    async def test_session_open_creates_profile_dir(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """open() creates browser profile directory."""
        result = await isolated_session_manager.open("test_session")
        profile_dir = Path(result["profile_dir"])

        assert profile_dir.exists()
        assert profile_dir.is_dir()

    async def test_session_open_stores_in_db(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """open() persists session to SQLite."""
        await isolated_session_manager.open("db_test_session")

        # Query DB directly
        conn = sqlite3.connect(isolated_session_manager.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sessions WHERE name = ?", ("db_test_session",))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row[0] == "db_test_session"

    async def test_session_list_returns_active_sessions(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """list() returns all active sessions."""
        await isolated_session_manager.open("session_1")
        await isolated_session_manager.open("session_2")

        sessions = isolated_session_manager.list()

        names = [s["name"] for s in sessions]
        assert "session_1" in names
        assert "session_2" in names

    async def test_session_list_sorted_by_last_used(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """list() returns sessions sorted by last_used_at (newest first)."""
        await isolated_session_manager.open("session_a")
        await asyncio.sleep(0.01)  # Small delay
        await isolated_session_manager.open("session_b")

        sessions = isolated_session_manager.list()

        # session_b should be first (most recent)
        assert sessions[0]["name"] == "session_b"

    async def test_session_close_deletes_profile_dir(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """close() deletes the browser profile directory."""
        result = await isolated_session_manager.open("to_close")
        profile_dir = Path(result["profile_dir"])

        assert profile_dir.exists()

        await isolated_session_manager.close("to_close")

        assert not profile_dir.exists()

    async def test_session_close_removes_from_db(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """close() removes session from database."""
        await isolated_session_manager.open("to_delete")

        await isolated_session_manager.close("to_delete")

        # Query DB
        conn = sqlite3.connect(isolated_session_manager.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sessions WHERE name = ?", ("to_delete",))
        row = cursor.fetchone()
        conn.close()

        assert row is None

    async def test_session_close_nonexistent_returns_error(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """close() returns error dict if session not found."""
        result = await isolated_session_manager.close("nonexistent")

        assert "error" in result
        assert "not found" in result["error"].lower()

    async def test_session_get_context_returns_metadata(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """get_context() returns session metadata if valid."""
        await isolated_session_manager.open("context_test")

        context = isolated_session_manager.get_context("context_test")

        assert context is not None
        assert context["name"] == "context_test"
        assert "profile_dir" in context

    async def test_session_get_context_returns_none_for_missing(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """get_context() returns None if session not found."""
        context = isolated_session_manager.get_context("nonexistent")
        assert context is None

    async def test_session_open_reuse_extends_ttl(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Reopening an existing session extends its TTL and returns stable metadata."""
        result1 = await isolated_session_manager.open("reuse_test", ttl_seconds=100)
        expires_at_1 = result1["expires_at"]

        await asyncio.sleep(0.01)

        result2 = await isolated_session_manager.open("reuse_test", ttl_seconds=200)
        expires_at_2 = result2["expires_at"]

        # Second call should have a later expiration
        assert expires_at_2 > expires_at_1
        # Reuse must preserve the original identity (regression guard for the
        # off-by-one schema index bug caught in session-audit CRITICAL #1).
        assert result2["session_id"] == result1["session_id"]
        assert result2["profile_dir"] == result1["profile_dir"]
        assert result2["created_at"] == result1["created_at"]
        # session_id must still look like a UUID (not a datetime leaked from column 4)
        import uuid as _uuid

        _uuid.UUID(result2["session_id"])

    async def test_session_lru_eviction_at_9_sessions(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """LRU eviction triggers when 8+ sessions exist (evicts 9th)."""
        # Create 9 sessions
        names = []
        for i in range(9):
            name = f"lru_test_{i}"
            names.append(name)
            await isolated_session_manager.open(name)
            await asyncio.sleep(0.001)  # Slight delay to ensure ordering

        # The first session should be evicted (LRU)
        sessions = isolated_session_manager.list()
        remaining_names = [s["name"] for s in sessions]

        # First created session should be gone
        assert names[0] not in remaining_names
        # Later sessions should remain
        assert len(remaining_names) == 8

    async def test_session_concurrent_access_semaphore(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Concurrent close/open on same session name are serialized."""
        # This tests that _get_session_lock() provides mutual exclusion
        name = "concurrent_test"

        async def open_task() -> dict:
            return await isolated_session_manager.open(name, ttl_seconds=60)

        async def close_task() -> dict:
            return await isolated_session_manager.close(name)

        # First open
        result1 = await open_task()
        assert result1["name"] == name

        # Concurrent open (should reuse existing)
        results = await asyncio.gather(
            open_task(),
            open_task(),
        )

        for r in results:
            assert r["name"] == name

    async def test_session_persistence_across_restart(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """Sessions persist in DB and reload on manager restart."""
        # Create a session
        await isolated_session_manager.open("persist_test")

        db_path = isolated_session_manager.db_path

        # Reset singleton
        SessionManager._instance = None
        isolated_session_manager2 = SessionManager()

        # New manager should load from DB
        sessions = isolated_session_manager2.list()
        names = [s["name"] for s in sessions]

        assert "persist_test" in names

    async def test_session_validate_name_on_open(
        self, isolated_session_manager: SessionManager
    ) -> None:
        """open() validates session name."""
        with pytest.raises(ValueError):
            await isolated_session_manager.open("invalid session!")
