"""Tests for SQLite connection pooling with context managers."""

from __future__ import annotations

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from loom.sqlite_pool import SQLitePool, get_pool, research_pool_stats, research_pool_reset


@pytest.mark.asyncio
class TestSQLitePool:
    """SQLitePool tests."""

    async def test_pool_init(self) -> None:
        """Pool initializes with correct parameters."""
        with TemporaryDirectory() as tmpdir:
            pool = SQLitePool(max_connections=3, base_path=tmpdir)
            assert pool.max_connections == 3
            assert Path(tmpdir).exists()

    async def test_pool_acquire_context_manager(self) -> None:
        """pool.acquire() is a proper async context manager."""
        with TemporaryDirectory() as tmpdir:
            pool = SQLitePool(max_connections=5, base_path=tmpdir)
            async with pool.acquire("test.db") as conn:
                assert conn is not None
                result = await conn.execute("PRAGMA journal_mode")
                mode = await result.fetchone()
                assert mode is not None

    async def test_pool_database_creation(self) -> None:
        """Database file is created in base_path."""
        with TemporaryDirectory() as tmpdir:
            pool = SQLitePool(max_connections=5, base_path=tmpdir)
            async with pool.acquire("test.db") as conn:
                assert conn is not None
            assert (Path(tmpdir) / "test.db").exists()

    async def test_pool_concurrent_access(self) -> None:
        """Pool handles concurrent requests via semaphore."""
        with TemporaryDirectory() as tmpdir:
            pool = SQLitePool(max_connections=2, base_path=tmpdir)

            async def work(db_id: int) -> None:
                async with pool.acquire(f"db_{db_id}.db") as conn:
                    await asyncio.sleep(0.01)
                    await conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")

            # 5 tasks with max_connections=2 tests queuing
            await asyncio.gather(*[work(i) for i in range(5)])

    async def test_pool_connection_cleanup(self) -> None:
        """Connection is closed after context exit."""
        with TemporaryDirectory() as tmpdir:
            pool = SQLitePool(max_connections=5, base_path=tmpdir)
            async with pool.acquire("cleanup.db") as conn:
                async with pool._lock:
                    assert pool._stats["cleanup.db"]["connections_active"] > 0
            async with pool._lock:
                assert pool._stats["cleanup.db"]["connections_active"] == 0

    async def test_pool_wal_mode(self) -> None:
        """WAL mode is enabled on connections."""
        with TemporaryDirectory() as tmpdir:
            pool = SQLitePool(max_connections=5, base_path=tmpdir)
            async with pool.acquire("wal.db") as conn:
                cursor = await conn.execute("PRAGMA journal_mode")
                row = await cursor.fetchone()
                assert row is not None
                assert "wal" in str(row).lower()

    async def test_pool_multiple_databases(self) -> None:
        """Pool tracks multiple distinct databases."""
        with TemporaryDirectory() as tmpdir:
            pool = SQLitePool(max_connections=5, base_path=tmpdir)
            async with pool.acquire("db1.db") as conn1:
                async with pool.acquire("db2.db") as conn2:
                    async with pool.acquire("db3.db") as conn3:
                        assert conn1 is not conn2
                        assert conn2 is not conn3
                        assert len(pool._semaphores) == 3


@pytest.mark.asyncio
class TestPoolSingleton:
    """Singleton behavior."""

    async def test_get_pool_returns_singleton(self) -> None:
        """get_pool() returns same instance."""
        pool1 = get_pool()
        pool2 = get_pool()
        assert pool1 is pool2

    async def test_get_pool_initializes_once(self) -> None:
        """Singleton initialized only once."""
        import loom.sqlite_pool as pool_module
        old = pool_module._pool_instance
        pool_module._pool_instance = None
        try:
            pool = get_pool()
            assert pool is not None
            assert pool.max_connections == 5
        finally:
            pool_module._pool_instance = old


@pytest.mark.asyncio
class TestPoolIntegration:
    """Integration tests."""

    async def test_pool_table_operations(self) -> None:
        """Pool works with actual table operations."""
        with TemporaryDirectory() as tmpdir:
            pool = SQLitePool(max_connections=5, base_path=tmpdir)
            async with pool.acquire("integration.db") as conn:
                await conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
                await conn.execute('INSERT INTO test (name) VALUES (?)', ("value",))
                await conn.commit()
                cursor = await conn.execute("SELECT name FROM test WHERE id = 1")
                row = await cursor.fetchone()
                assert row is not None
                assert row[0] == "value"

    async def test_pool_sequential_connections(self) -> None:
        """Sequential connection requests work."""
        with TemporaryDirectory() as tmpdir:
            pool = SQLitePool(max_connections=2, base_path=tmpdir)
            async with pool.acquire("seq.db") as conn1:
                assert conn1 is not None
            async with pool.acquire("seq.db") as conn2:
                assert conn2 is not None


@pytest.mark.asyncio
async def test_research_pool_stats_structure() -> None:
    """research_pool_stats returns correct structure."""
    stats = await research_pool_stats()
    assert "databases" in stats
    assert "total_active" in stats
    assert "max_connections" in stats
    assert "timestamp" in stats
    assert isinstance(stats["databases"], list)
    assert isinstance(stats["total_active"], int)
    assert isinstance(stats["max_connections"], int)


@pytest.mark.asyncio
async def test_research_pool_reset_structure() -> None:
    """research_pool_reset returns correct structure."""
    result = await research_pool_reset()
    assert result["reset"] is True
    assert "databases_reset" in result
    assert "timestamp" in result
    assert isinstance(result["databases_reset"], int)
