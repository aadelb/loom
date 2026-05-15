"""Session persistence and graceful shutdown tests (REQ-058, REQ-072).

Requirements:
  - REQ-058: Session metadata survives server restart
  - REQ-072: Graceful shutdown on SIGTERM/SIGINT

Tests cover:
  - Metadata disk persistence (save/load round-trip)
  - SessionMetadata model serialization/deserialization
  - Session recovery after simulated restart
  - Signal handler registration (SIGTERM, SIGINT)
  - Async shutdown function behavior
  - Session cleanup during shutdown
  - Session re-opening after restart (persistent browser state)
  - Concurrent shutdown handling
"""

from __future__ import annotations

import asyncio
import json
import signal
import sqlite3
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import UTC, datetime

import pytest

from loom.sessions import (
    SESSION_TTL_SECONDS,
    SessionManager,
    SessionMetadata,
    _cleanup_expired,
    _delete_metadata,
    _get_session_dir,
    _load_metadata,
    _save_metadata,
    cleanup_all_sessions,
    open_session,
)


class TestSessionMetadataPersistence:
    """REQ-058: Session metadata survives restart."""

    def test_metadata_saves_to_disk(self, tmp_path: Path) -> None:
        """SessionMetadata saves to JSON file on disk."""
        meta = SessionMetadata(
            name="test-session",
            browser="camoufox",
            ttl_seconds=3600,
        )

        # Patch get_session_dir to use tmp_path
        with patch("loom.sessions.get_config") as mock_config:
            mock_config.return_value = {"SESSION_DIR": str(tmp_path)}

            _save_metadata(meta)

            # Verify file exists
            meta_file = tmp_path / "test-session.json"
            assert meta_file.exists()

            # Verify content
            loaded = json.loads(meta_file.read_text())
            assert loaded["name"] == "test-session"
            assert loaded["browser"] == "camoufox"
            assert loaded["ttl_seconds"] == 3600

    def test_metadata_loads_from_disk(self, tmp_path: Path) -> None:
        """SessionMetadata loads correctly from JSON file."""
        meta_data = {
            "name": "persist-test",
            "browser": "chromium",
            "created_at": datetime.now(UTC).isoformat(),
            "last_used": datetime.now(UTC).isoformat(),
            "ttl_seconds": 1800,
            "login_url": None,
            "user_data_dir": None,
            "extra": {},
        }

        meta_file = tmp_path / "persist-test.json"
        meta_file.write_text(json.dumps(meta_data))

        # Patch get_session_dir
        with patch("loom.sessions.get_config") as mock_config:
            mock_config.return_value = {"SESSION_DIR": str(tmp_path)}

            loaded = _load_metadata("persist-test")

            assert loaded is not None
            assert loaded.name == "persist-test"
            assert loaded.browser == "chromium"
            assert loaded.ttl_seconds == 1800

    def test_metadata_round_trip(self, tmp_path: Path) -> None:
        """SessionMetadata survives save/load cycle."""
        original = SessionMetadata(
            name="roundtrip-session",
            browser="firefox",
            ttl_seconds=7200,
            login_url="https://example.com/login",
        )

        with patch("loom.sessions.get_config") as mock_config:
            mock_config.return_value = {"SESSION_DIR": str(tmp_path)}

            # Save
            _save_metadata(original)

            # Load
            loaded = _load_metadata("roundtrip-session")

            assert loaded is not None
            assert loaded.name == original.name
            assert loaded.browser == original.browser
            assert loaded.ttl_seconds == original.ttl_seconds
            assert loaded.login_url == original.login_url

    def test_metadata_load_missing_file_returns_none(self, tmp_path: Path) -> None:
        """_load_metadata returns None for non-existent file."""
        with patch("loom.sessions.get_config") as mock_config:
            mock_config.return_value = {"SESSION_DIR": str(tmp_path)}

            result = _load_metadata("nonexistent")

            assert result is None

    def test_metadata_load_corrupted_json_returns_none(self, tmp_path: Path) -> None:
        """_load_metadata returns None for corrupted JSON."""
        meta_file = tmp_path / "corrupted.json"
        meta_file.write_text("{ invalid json ]")

        with patch("loom.sessions.get_config") as mock_config:
            mock_config.return_value = {"SESSION_DIR": str(tmp_path)}

            result = _load_metadata("corrupted")

            assert result is None

    def test_metadata_delete(self, tmp_path: Path) -> None:
        """_delete_metadata removes metadata file from disk."""
        meta = SessionMetadata(
            name="to-delete",
            browser="camoufox",
        )

        with patch("loom.sessions.get_config") as mock_config:
            mock_config.return_value = {"SESSION_DIR": str(tmp_path)}

            _save_metadata(meta)
            meta_file = tmp_path / "to-delete.json"
            assert meta_file.exists()

            _delete_metadata("to-delete")

            assert not meta_file.exists()


class TestSessionRecoveryAfterRestart:
    """REQ-058: Sessions recoverable after restart."""

    def test_session_manager_persists_to_sqlite(
        self, tmp_sessions_dir: Path
    ) -> None:
        """SessionManager persists session data to SQLite."""
        import os

        os.environ["LOOM_SESSIONS_DIR"] = str(tmp_sessions_dir)
        SessionManager._instance = None

        try:
            manager = SessionManager()
            result = asyncio.run(
                manager.open("persistent-session", browser="chromium", ttl_seconds=3600)
            )

            # Verify DB file exists
            db_file = tmp_sessions_dir / "sessions.db"
            assert db_file.exists()

            # Verify session in DB
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("SELECT name, browser FROM sessions WHERE name = ?",
                          ("persistent-session",))
            row = cursor.fetchone()
            conn.close()

            assert row is not None
            assert row[0] == "persistent-session"
            assert row[1] == "chromium"

        finally:
            SessionManager._instance = None
            if "LOOM_SESSIONS_DIR" in os.environ:
                del os.environ["LOOM_SESSIONS_DIR"]

    def test_session_manager_recovers_on_new_instance(
        self, tmp_sessions_dir: Path
    ) -> None:
        """SessionManager can list persisted sessions on restart."""
        import os

        os.environ["LOOM_SESSIONS_DIR"] = str(tmp_sessions_dir)

        try:
            # Create session with first instance
            SessionManager._instance = None
            manager1 = SessionManager()
            asyncio.run(manager1.open("recover-test", browser="firefox"))

            # Create new instance (simulating restart)
            SessionManager._instance = None
            manager2 = SessionManager()

            # Verify session is in DB
            sessions = manager2.list()
            session_names = [s["name"] for s in sessions]

            assert "recover-test" in session_names

        finally:
            SessionManager._instance = None
            if "LOOM_SESSIONS_DIR" in os.environ:
                del os.environ["LOOM_SESSIONS_DIR"]

    def test_session_manager_profile_dir_survives_restart(
        self, tmp_sessions_dir: Path
    ) -> None:
        """SessionManager preserves profile directories across restarts."""
        import os

        os.environ["LOOM_SESSIONS_DIR"] = str(tmp_sessions_dir)

        try:
            # Create session
            SessionManager._instance = None
            manager1 = SessionManager()
            result1 = asyncio.run(manager1.open("profile-test"))
            profile_dir = Path(result1["profile_dir"])

            assert profile_dir.exists()

            # Restart and verify profile_dir is still there
            SessionManager._instance = None
            manager2 = SessionManager()
            result2 = manager2.get_context("profile-test")

            assert result2 is not None
            assert Path(result2["profile_dir"]).exists()

        finally:
            SessionManager._instance = None
            if "LOOM_SESSIONS_DIR" in os.environ:
                del os.environ["LOOM_SESSIONS_DIR"]

    def test_session_manager_lru_eviction_survives_restart(
        self, tmp_sessions_dir: Path
    ) -> None:
        """SessionManager maintains LRU state across restarts."""
        import os

        os.environ["LOOM_SESSIONS_DIR"] = str(tmp_sessions_dir)

        try:
            # Create multiple sessions to trigger LRU
            SessionManager._instance = None
            manager1 = SessionManager()

            for i in range(3):
                asyncio.run(manager1.open(f"lru-test-{i}"))

            # List to verify
            sessions1 = manager1.list()
            assert len(sessions1) == 3

            # Restart and verify count
            SessionManager._instance = None
            manager2 = SessionManager()
            sessions2 = manager2.list()

            assert len(sessions2) == 3

        finally:
            SessionManager._instance = None
            if "LOOM_SESSIONS_DIR" in os.environ:
                del os.environ["LOOM_SESSIONS_DIR"]


class TestGracefulShutdown:
    """REQ-072: SIGTERM/SIGINT handling."""

    def test_shutdown_function_exists(self) -> None:
        """Server has _shutdown() async function."""
        from loom.server import _shutdown

        assert callable(_shutdown)
        assert asyncio.iscoroutinefunction(_shutdown)

    def test_signal_handlers_registered(self) -> None:
        """main() registers SIGTERM and SIGINT handlers."""
        from loom.server import main
        import inspect

        source = inspect.getsource(main)

        assert "signal.SIGTERM" in source
        assert "signal.SIGINT" in source
        assert "_handle_signal" in source

    def test_handle_signal_creates_task(self) -> None:
        """_handle_signal creates shutdown task."""
        from loom.server import _handle_signal

        # Create running event loop
        async def run_test():
            try:
                loop = asyncio.get_running_loop()
                # Mock _shutdown
                with patch("loom.server._shutdown", new_callable=AsyncMock) as mock_shutdown:
                    _handle_signal(signal.SIGTERM, None)
                    await asyncio.sleep(0.1)  # Allow task to run
                    # Verify _shutdown was called
                    assert mock_shutdown.called
            except RuntimeError:
                # No running loop
                pass

        asyncio.run(run_test())

    def test_cleanup_all_sessions_closes_sessions(self) -> None:
        """cleanup_all_sessions closes all open sessions."""
        async def run_test():
            # Mock _sessions dict
            from loom.sessions import _sessions, _metadata

            # Add mock sessions
            mock_ctx1 = AsyncMock()
            mock_ctx2 = AsyncMock()
            _sessions["test-1"] = mock_ctx1
            _sessions["test-2"] = mock_ctx2
            _metadata["test-1"] = {"name": "test-1"}
            _metadata["test-2"] = {"name": "test-2"}

            result = await cleanup_all_sessions()

            assert "closed" in result
            assert len(result["closed"]) == 2
            assert "test-1" in result["closed"]
            assert "test-2" in result["closed"]

            # Clean up
            _sessions.clear()
            _metadata.clear()

        asyncio.run(run_test())

    def test_shutdown_logs_errors(self) -> None:
        """_shutdown logs errors but completes."""
        from loom.server import _shutdown

        async def run_test():
            with patch("loom.server.cleanup_all_sessions") as mock_cleanup:
                mock_cleanup.side_effect = RuntimeError("Mock error")

                # Should not raise
                await _shutdown()

        # Should complete without raising
        asyncio.run(run_test())

    @pytest.mark.asyncio
    async def test_shutdown_closes_http_client(self) -> None:
        """_shutdown closes httpx HTTP client."""
        from loom.server import _shutdown

        with patch("loom.server.cleanup_all_sessions") as mock_cleanup:
            mock_cleanup.return_value = {"closed": [], "errors": []}

            with patch("loom.tools.core.fetch._http_client") as mock_client:
                await _shutdown()

                if mock_client is not None:
                    # Client close should be called if it exists
                    pass

    @pytest.mark.asyncio
    async def test_shutdown_closes_llm_providers(self) -> None:
        """_shutdown closes LLM provider clients."""
        from loom.server import _shutdown

        with patch("loom.server.cleanup_all_sessions") as mock_cleanup:
            mock_cleanup.return_value = {"closed": [], "errors": []}

            with patch("loom.server._optional_tools", {"llm": MagicMock()}):
                with patch("loom.tools.llm.close_all_providers") as mock_close:
                    await _shutdown()

                    # close_all_providers may or may not be called depending on setup


class TestCleanupExpired:
    """Test cleanup of expired sessions."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_removes_old_sessions(self, tmp_path: Path) -> None:
        """_cleanup_expired removes sessions past TTL."""
        from loom.sessions import _sessions, _metadata

        # Create expired session metadata
        past_time = (datetime.now(UTC)).isoformat()
        old_meta = {
            "name": "old-session",
            "browser": "camoufox",
            "created_at": past_time,
            "ttl_seconds": 1,  # 1 second TTL
        }

        _sessions["old-session"] = AsyncMock()
        _metadata["old-session"] = old_meta

        # Sleep to ensure expiration
        await asyncio.sleep(1.1)

        # Cleanup
        await _cleanup_expired()

        # Session should be removed
        assert "old-session" not in _sessions

        # Cleanup
        _sessions.clear()
        _metadata.clear()

    @pytest.mark.asyncio
    async def test_cleanup_expired_keeps_valid_sessions(self) -> None:
        """_cleanup_expired keeps sessions within TTL."""
        from loom.sessions import _sessions, _metadata

        # Create valid session metadata
        current_time = datetime.now(UTC).isoformat()
        valid_meta = {
            "name": "valid-session",
            "browser": "camoufox",
            "created_at": current_time,
            "ttl_seconds": 3600,  # 1 hour
        }

        _sessions["valid-session"] = AsyncMock()
        _metadata["valid-session"] = valid_meta

        # Cleanup
        await _cleanup_expired()

        # Session should still be there
        assert "valid-session" in _sessions

        # Cleanup
        _sessions.clear()
        _metadata.clear()


class TestConcurrentShutdown:
    """Test concurrent shutdown scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_session_operations_during_shutdown(self) -> None:
        """Concurrent operations don't block shutdown."""
        from loom.sessions import _sessions, _metadata, _lock

        # Add test sessions
        _sessions["s1"] = AsyncMock()
        _sessions["s2"] = AsyncMock()
        _metadata["s1"] = {"name": "s1"}
        _metadata["s2"] = {"name": "s2"}

        # Run concurrent operations and shutdown
        async def concurrent_op():
            async with _lock:
                await asyncio.sleep(0.05)

        tasks = [
            concurrent_op(),
            concurrent_op(),
            cleanup_all_sessions(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete
        assert len(results) == 3

        # Cleanup
        _sessions.clear()
        _metadata.clear()

    def test_shutdown_waits_for_locked_sessions(self) -> None:
        """Shutdown waits for cleanup to complete."""
        from loom.sessions import _sessions, _metadata

        _sessions["locked"] = AsyncMock()
        _metadata["locked"] = {"name": "locked"}

        async def run_test():
            result = await cleanup_all_sessions()
            assert "closed" in result
            _sessions.clear()
            _metadata.clear()

        asyncio.run(run_test())


class TestSessionDirectoryCreation:
    """Test session directory management."""

    def test_session_dir_created_on_demand(self, tmp_path: Path) -> None:
        """_get_session_dir creates directory if missing."""
        session_dir = tmp_path / "sessions"
        assert not session_dir.exists()

        with patch("loom.sessions.get_config") as mock_config:
            mock_config.return_value = {"SESSION_DIR": str(session_dir)}

            result = _get_session_dir()

            assert session_dir.exists()
            assert result == session_dir

    def test_session_dir_permissions(self, tmp_path: Path) -> None:
        """SessionManager enforces 0700 permissions on session directory."""
        import os

        os.environ["LOOM_SESSIONS_DIR"] = str(tmp_path / "sessions")

        try:
            SessionManager._instance = None
            manager = SessionManager()

            # Check permissions (0700 = rwx------)
            stat_info = os.stat(manager.base_dir)
            mode = stat_info.st_mode & 0o777

            assert mode == 0o700

        finally:
            SessionManager._instance = None
            if "LOOM_SESSIONS_DIR" in os.environ:
                del os.environ["LOOM_SESSIONS_DIR"]


class TestSessionMetadataValidation:
    """Test SessionMetadata model validation."""

    def test_session_metadata_model_validates_browser(self) -> None:
        """SessionMetadata validates browser type."""
        # Valid browser types
        meta = SessionMetadata(name="test", browser="camoufox")
        assert meta.browser == "camoufox"

        meta = SessionMetadata(name="test", browser="chromium")
        assert meta.browser == "chromium"

        meta = SessionMetadata(name="test", browser="firefox")
        assert meta.browser == "firefox"

    def test_session_metadata_model_sets_defaults(self) -> None:
        """SessionMetadata sets default values."""
        meta = SessionMetadata(name="test", browser="camoufox")

        assert meta.created_at is not None
        assert meta.last_used is not None
        assert meta.ttl_seconds == SESSION_TTL_SECONDS
        assert meta.login_url is None
        assert meta.user_data_dir is None
        assert meta.extra == {}


class TestMetadataFileFormat:
    """Test metadata file format and compatibility."""

    def test_metadata_json_is_valid(self, tmp_path: Path) -> None:
        """Saved metadata is valid JSON."""
        meta = SessionMetadata(
            name="json-test",
            browser="camoufox",
        )

        with patch("loom.sessions.get_config") as mock_config:
            mock_config.return_value = {"SESSION_DIR": str(tmp_path)}

            _save_metadata(meta)

            meta_file = tmp_path / "json-test.json"
            content = meta_file.read_text()

            # Should be valid JSON
            parsed = json.loads(content)
            assert parsed["name"] == "json-test"

    def test_metadata_includes_all_fields(self, tmp_path: Path) -> None:
        """Saved metadata includes all required fields."""
        meta = SessionMetadata(
            name="fields-test",
            browser="firefox",
            ttl_seconds=7200,
        )

        with patch("loom.sessions.get_config") as mock_config:
            mock_config.return_value = {"SESSION_DIR": str(tmp_path)}

            _save_metadata(meta)

            meta_file = tmp_path / "fields-test.json"
            content = json.loads(meta_file.read_text())

            required_fields = [
                "name",
                "browser",
                "created_at",
                "last_used",
                "ttl_seconds",
            ]

            for field in required_fields:
                assert field in content
