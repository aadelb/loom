"""Tests for rate limiter persistence with SQLite."""

from __future__ import annotations

import asyncio
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from loom.rate_limiter import (
    RateLimiter,
    SyncRateLimiter,
    _cleanup_old_entries,
    _get_persistence_db,
    _init_persistence_db,
    _load_from_db,
    _save_to_db,
)


class TestPersistenceDbInit:
    """Tests for persistence database initialization."""

    def test_get_persistence_db_disabled(self) -> None:
        """Test _get_persistence_db returns None when persistence is disabled."""
        with patch("loom.config.get_config") as mock_config:
            mock_config.return_value = {"RATE_LIMIT_PERSIST": False}
            result = _get_persistence_db()
            assert result is None

    def test_get_persistence_db_enabled(self) -> None:
        """Test _get_persistence_db returns path when persistence is enabled."""
        with patch("loom.config.get_config") as mock_config:
            mock_config.return_value = {"RATE_LIMIT_PERSIST": True}
            result = _get_persistence_db()
            assert result is not None
            assert isinstance(result, Path)
            assert "rate_limits.db" in str(result)

    def test_init_persistence_db_creates_table(self) -> None:
        """Test _init_persistence_db creates the correct table."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_rate_limits.db"

            _init_persistence_db(db_path)

            # Check that the database was created
            assert db_path.exists()

            # Check that the table exists
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='rate_limits'"
            )
            result = cursor.fetchone()
            conn.close()

            assert result is not None
            assert result[0] == "rate_limits"


class TestPersistenceDbOperations:
    """Tests for persistence database operations."""

    def test_save_and_load_timestamps(self) -> None:
        """Test saving and loading timestamps from database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_rate_limits.db"
            _init_persistence_db(db_path)

            # Save some timestamps
            now = time.time()
            _save_to_db(db_path, "search", "user1", now - 10)
            _save_to_db(db_path, "search", "user1", now - 5)
            _save_to_db(db_path, "search", "user1", now)

            # Load them back
            timestamps = _load_from_db(db_path, "search", "user1", 60)

            assert len(timestamps) == 3
            assert all(isinstance(ts, float) for ts in timestamps)

    def test_load_respects_window(self) -> None:
        """Test that _load_from_db only returns timestamps within the window."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_rate_limits.db"
            _init_persistence_db(db_path)

            # Save timestamps: one old, two recent
            now = time.time()
            _save_to_db(db_path, "search", "user1", now - 100)  # Outside 60s window
            _save_to_db(db_path, "search", "user1", now - 10)   # Inside 60s window
            _save_to_db(db_path, "search", "user1", now)        # Inside 60s window

            # Load with 60 second window
            timestamps = _load_from_db(db_path, "search", "user1", 60)

            assert len(timestamps) == 2
            assert all(ts > now - 60 for ts in timestamps)

    def test_cleanup_old_entries(self) -> None:
        """Test that _cleanup_old_entries removes old timestamps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_rate_limits.db"
            _init_persistence_db(db_path)

            # Save timestamps: one old, two recent
            now = time.time()
            _save_to_db(db_path, "search", "user1", now - 100)
            _save_to_db(db_path, "search", "user1", now - 10)
            _save_to_db(db_path, "search", "user1", now)

            # Cleanup entries older than 60 seconds
            _cleanup_old_entries(db_path, 60)

            # Load and verify only recent entries remain
            timestamps = _load_from_db(db_path, "search", "user1", 120)
            assert len(timestamps) == 2
            assert all(ts > now - 60 for ts in timestamps)


class TestRateLimiterWithPersistence:
    """Tests for RateLimiter with persistence enabled."""

    @pytest.mark.asyncio
    async def test_limiter_with_persistence(self) -> None:
        """Test rate limiter respects persistence settings."""
        with patch("loom.rate_limiter._get_persistence_db") as mock_get_db:
            mock_get_db.return_value = None

            limiter = RateLimiter(max_calls=2, window_seconds=60)
            assert limiter._db_path is None

            # Should work with in-memory only
            assert await limiter.check() is True
            assert await limiter.check() is True
            assert await limiter.check() is False

    @pytest.mark.asyncio
    async def test_limiter_persistence_survives_restart(self) -> None:
        """Test that rate limit state persists across limiter instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_rate_limits.db"
            _init_persistence_db(db_path)

            # Simulate first limiter instance
            with patch("loom.rate_limiter._get_persistence_db") as mock_get_db:
                mock_get_db.return_value = db_path

                limiter1 = RateLimiter(max_calls=2, window_seconds=60)
                assert await limiter1.check("test_key") is True
                assert await limiter1.check("test_key") is True

            # Simulate restart with new limiter instance
            with patch("loom.rate_limiter._get_persistence_db") as mock_get_db:
                mock_get_db.return_value = db_path

                limiter2 = RateLimiter(max_calls=2, window_seconds=60)
                # Third call should still be blocked due to persisted state
                assert await limiter2.check("test_key") is False

    @pytest.mark.asyncio
    async def test_remaining_with_persistence(self) -> None:
        """Test remaining() reports correct count with persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_rate_limits.db"
            _init_persistence_db(db_path)

            with patch("loom.rate_limiter._get_persistence_db") as mock_get_db:
                mock_get_db.return_value = db_path

                limiter = RateLimiter(max_calls=5, window_seconds=60)
                await limiter.check("test_key")
                await limiter.check("test_key")

                remaining = limiter.remaining("test_key")
                assert remaining == 3


class TestSyncRateLimiterWithPersistence:
    """Tests for SyncRateLimiter with persistence enabled."""

    def test_sync_limiter_with_persistence(self) -> None:
        """Test sync rate limiter respects persistence settings."""
        with patch("loom.rate_limiter._get_persistence_db") as mock_get_db:
            mock_get_db.return_value = None

            limiter = SyncRateLimiter(max_calls=2, window_seconds=60)
            assert limiter._db_path is None

            # Should work with in-memory only
            assert limiter.check() is True
            assert limiter.check() is True
            assert limiter.check() is False

    def test_sync_limiter_persistence_survives_restart(self) -> None:
        """Test that sync rate limit state persists across limiter instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_rate_limits.db"
            _init_persistence_db(db_path)

            # Simulate first limiter instance
            with patch("loom.rate_limiter._get_persistence_db") as mock_get_db:
                mock_get_db.return_value = db_path

                limiter1 = SyncRateLimiter(max_calls=2, window_seconds=60)
                assert limiter1.check("test_key") is True
                assert limiter1.check("test_key") is True

            # Simulate restart with new limiter instance
            with patch("loom.rate_limiter._get_persistence_db") as mock_get_db:
                mock_get_db.return_value = db_path

                limiter2 = SyncRateLimiter(max_calls=2, window_seconds=60)
                # Third call should still be blocked due to persisted state
                assert limiter2.check("test_key") is False


class TestPersistenceIntegration:
    """Integration tests for persistence with rate limiting decorators."""

    @pytest.mark.asyncio
    async def test_rate_limited_decorator_with_persistence(self) -> None:
        """Test @rate_limited decorator works with persistence."""
        from loom.rate_limiter import _get_limiter, rate_limited, reset_all

        reset_all()

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_rate_limits.db"
            _init_persistence_db(db_path)

            with patch("loom.rate_limiter._get_persistence_db") as mock_get_db:
                mock_get_db.return_value = db_path

                @rate_limited("test")
                async def test_func(value: int) -> int:
                    return value * 2

                # Get a limiter and set its max_calls low
                limiter = _get_limiter("test")
                original_max = limiter.max_calls
                limiter.max_calls = 1

                # First call should work
                result1 = await test_func(5)
                assert result1 == 10

                # Second call should be rate limited
                result2 = await test_func(10)
                assert isinstance(result2, dict)
                assert result2["error"] == "rate_limit_exceeded"

                # Restore original
                limiter.max_calls = original_max
