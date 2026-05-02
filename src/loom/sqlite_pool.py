"""SQLite connection pooling to prevent "database is locked" errors.

Async context manager pool with per-database semaphores, WAL mode,
and 5-second busy timeout. Singleton instance via get_pool().
"""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

import aiosqlite

logger = logging.getLogger("loom.sqlite_pool")


class SQLitePool:
    """Connection pool for SQLite with per-DB semaphores."""

    def __init__(self, max_connections: int = 5, base_path: str = "~/.loom/") -> None:
        self.max_connections = max_connections
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._semaphores: dict[str, asyncio.Semaphore] = {}
        self._stats: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self, db_name: str) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Async context manager: async with pool.acquire(db_name) as conn:"""
        async with self._lock:
            if db_name not in self._semaphores:
                self._semaphores[db_name] = asyncio.Semaphore(self.max_connections)
                self._stats[db_name] = {"connections_active": 0, "total_queries": 0, "total_query_time_ms": 0.0}

        semaphore = self._semaphores[db_name]
        await semaphore.acquire()
        conn = None
        try:
            conn = await aiosqlite.connect(str(self.base_path / db_name), timeout=5.0, check_same_thread=False)
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA busy_timeout=5000")
            async with self._lock:
                self._stats[db_name]["connections_active"] += 1
            yield conn
        finally:
            if conn:
                try:
                    await conn.close()
                except Exception as e:
                    logger.warning("close_failed db=%s error=%s", db_name, e)
            semaphore.release()
            async with self._lock:
                self._stats[db_name]["connections_active"] = max(0, self._stats[db_name]["connections_active"] - 1)

    async def close_all(self) -> None:
        """Close all connections and reset pool."""
        async with self._lock:
            self._semaphores.clear()
            self._stats.clear()
        logger.info("pool_reset_complete")


_pool_instance: SQLitePool | None = None


def get_pool() -> SQLitePool:
    """Get or create singleton pool."""
    global _pool_instance
    if _pool_instance is None:
        _pool_instance = SQLitePool(max_connections=5)
    return _pool_instance


async def research_pool_stats() -> dict[str, Any]:
    """Pool stats: databases list, total_active, max_connections, timestamp."""
    pool = get_pool()
    async with pool._lock:
        databases = []
        total_active = 0
        for db_name, stats in pool._stats.items():
            active = stats.get("connections_active", 0)
            total_queries = stats.get("total_queries", 0)
            total_time = stats.get("total_query_time_ms", 0.0)
            databases.append({
                "name": db_name,
                "connections_active": active,
                "total_queries": total_queries,
                "avg_query_ms": round(total_time / total_queries if total_queries else 0, 2),
            })
            total_active += active
    return {"databases": databases, "total_active": total_active, "max_connections": pool.max_connections, "timestamp": time.time()}


async def research_pool_reset() -> dict[str, Any]:
    """Reset all connections and stats."""
    pool = get_pool()
    async with pool._lock:
        db_count = len(pool._stats)
        pool._semaphores.clear()
        pool._stats.clear()
    logger.info("pool_reset databases=%d", db_count)
    return {"reset": True, "databases_reset": db_count, "timestamp": time.time()}
