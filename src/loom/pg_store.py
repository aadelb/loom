"""PostgreSQL store for billing and audit data.

Migrates Loom's billing and audit systems from SQLite/JSON to PostgreSQL.
Provides async operations with connection pooling via asyncpg.

Connection: DATABASE_URL env var (default: postgresql://loom:loom_secure_2026@localhost:5432/loom_db)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

import asyncpg

log = logging.getLogger("loom.pg_store")

# Global connection pool
_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def get_pool() -> asyncpg.Pool:
    """Get or create the PostgreSQL connection pool."""
    global _pool

    if _pool is not None:
        return _pool

    async with _pool_lock:
        if _pool is not None:
            return _pool

        db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://loom:loom_secure_2026@localhost:5432/loom_db"
        )

        try:
            _pool = await asyncpg.create_pool(
                db_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            log.info("pg_pool_created")
            return _pool
        except Exception as e:
            log.error("pg_pool_creation_failed error=%s", str(e))
            raise


class PgStore:
    """PostgreSQL store for billing and audit data."""

    def __init__(self):
        """Initialize the store (connection happens on first use)."""
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Create connection pool from DATABASE_URL environment variable."""
        if self._pool is not None:
            return

        db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://loom:loom_secure_2026@localhost:5432/loom_db"
        )

        try:
            self._pool = await asyncpg.create_pool(
                db_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            log.info("pg_store_connected")
            await self.ensure_schema()
        except Exception as e:
            log.error("pg_store_connection_failed error=%s", str(e))
            raise

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            log.info("pg_store_closed")

    async def ensure_schema(self) -> None:
        """Create tables if they don't exist."""
        if self._pool is None:
            raise RuntimeError("Not connected to database")

        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT,
                    api_key_hash TEXT,
                    tier TEXT DEFAULT 'free',
                    credits INTEGER DEFAULT 0,
                    active BOOLEAN DEFAULT true,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS credits_ledger (
                    id SERIAL PRIMARY KEY,
                    customer_id TEXT REFERENCES customers(customer_id),
                    amount INTEGER NOT NULL,
                    reason TEXT,
                    tool_name TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_meter (
                    id SERIAL PRIMARY KEY,
                    customer_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    credits_used INTEGER NOT NULL,
                    duration_ms REAL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_meter_customer_date
                ON usage_meter(customer_id, created_at)
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    tool_name TEXT NOT NULL,
                    customer_id TEXT,
                    params_hash TEXT,
                    result_status TEXT,
                    duration_ms REAL,
                    hmac_signature TEXT
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp
                ON audit_log(timestamp)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_customer
                ON audit_log(customer_id)
            """)


            await conn.execute("""
                CREATE TABLE IF NOT EXISTS idempotency_keys (
                    id SERIAL PRIMARY KEY,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    customer_id TEXT,
                    operation TEXT NOT NULL,
                    result JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_idempotency_key_expires
                ON idempotency_keys(idempotency_key, expires_at)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_idempotency_customer_created
                ON idempotency_keys(customer_id, created_at)
            """)

            log.info("pg_schema_ready")

    # ===== Customers =====

    async def create_customer(
        self,
        customer_id: str,
        name: str,
        email: str | None = None,
        tier: str = "free"
    ) -> dict:
        """Create a new customer record.

        Args:
            customer_id: Unique customer identifier
            name: Customer name
            email: Optional email address
            tier: Tier level (default: free)

        Returns:
            Customer record as dict
        """
        if self._pool is None:
            raise RuntimeError("Not connected to database")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO customers (customer_id, name, email, tier, credits)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (customer_id) DO UPDATE
                SET name = $2, email = $3, updated_at = NOW()
                RETURNING *
            """, customer_id, name, email, tier, 0)

            log.info("pg_customer_created customer_id=%s", customer_id)
            return dict(row) if row else {}

    async def get_customer(self, customer_id: str) -> dict | None:
        """Get customer by ID.

        Args:
            customer_id: Customer identifier

        Returns:
            Customer record as dict, or None if not found
        """
        if self._pool is None:
            raise RuntimeError("Not connected to database")

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM customers WHERE customer_id = $1",
                customer_id
            )
            return dict(row) if row else None

    async def update_credits(
        self,
        customer_id: str,
        amount: int,
        reason: str = "manual_adjustment"
    ) -> int:
        """Update customer credits and record ledger entry.

        Args:
            customer_id: Customer identifier
            amount: Amount to add (negative to deduct)
            reason: Reason for adjustment (e.g., 'tool_usage', 'purchase')

        Returns:
            New credit balance
        """
        if self._pool is None:
            raise RuntimeError("Not connected to database")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Update credits
                row = await conn.fetchrow("""
                    UPDATE customers
                    SET credits = credits + $1, updated_at = NOW()
                    WHERE customer_id = $2
                    RETURNING credits
                """, amount, customer_id)

                new_balance = row["credits"] if row else 0

                # Log to ledger
                await conn.execute("""
                    INSERT INTO credits_ledger (customer_id, amount, reason)
                    VALUES ($1, $2, $3)
                """, customer_id, amount, reason)

                log.info(
                    "pg_credits_updated customer_id=%s amount=%d new_balance=%d",
                    customer_id, amount, new_balance
                )

                return new_balance

    # ===== Usage =====

    async def record_usage(
        self,
        customer_id: str,
        tool_name: str,
        credits: int,
        duration_ms: float | None = None
    ) -> None:
        """Record tool usage for a customer.

        Args:
            customer_id: Customer identifier
            tool_name: Name of tool used
            credits: Credits consumed
            duration_ms: Execution duration in milliseconds
        """
        if self._pool is None:
            raise RuntimeError("Not connected to database")

        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO usage_meter (customer_id, tool_name, credits_used, duration_ms)
                VALUES ($1, $2, $3, $4)
            """, customer_id, tool_name, credits, duration_ms)

            log.debug(
                "pg_usage_recorded customer_id=%s tool=%s credits=%d",
                customer_id, tool_name, credits
            )

    async def get_usage(
        self,
        customer_id: str,
        date: str | None = None
    ) -> dict:
        """Get usage statistics for a customer.

        Args:
            customer_id: Customer identifier
            date: Optional date filter (YYYY-MM-DD)

        Returns:
            Dict with total_credits, call_count, by_tool
        """
        if self._pool is None:
            raise RuntimeError("Not connected to database")

        async with self._pool.acquire() as conn:
            query = "SELECT tool_name, SUM(credits_used) as credits, COUNT(*) as calls FROM usage_meter WHERE customer_id = $1"
            params: list[Any] = [customer_id]

            if date:
                query += " AND DATE(created_at AT TIME ZONE 'UTC') = $2 GROUP BY tool_name"
                params.append(date)
            else:
                query += " GROUP BY tool_name"

            rows = await conn.fetch(query, *params)

            by_tool = {row["tool_name"]: {
                "credits": row["credits"],
                "calls": row["calls"]
            } for row in rows}

            total_credits = sum(row["credits"] for row in rows)
            total_calls = sum(row["calls"] for row in rows)

            return {
                "customer_id": customer_id,
                "total_credits": total_credits,
                "total_calls": total_calls,
                "by_tool": by_tool
            }

    async def get_top_tools(
        self,
        customer_id: str,
        limit: int = 10
    ) -> list[dict]:
        """Get top tools by credit usage for a customer.

        Args:
            customer_id: Customer identifier
            limit: Number of tools to return

        Returns:
            List of dicts with tool_name, credits, calls
        """
        if self._pool is None:
            raise RuntimeError("Not connected to database")

        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT tool_name, SUM(credits_used) as credits, COUNT(*) as calls
                FROM usage_meter
                WHERE customer_id = $1
                GROUP BY tool_name
                ORDER BY credits DESC
                LIMIT $2
            """, customer_id, limit)

            return [dict(row) for row in rows]

    # ===== Audit =====

    async def log_audit(
        self,
        tool_name: str,
        customer_id: str | None,
        params_hash: str | None,
        status: str,
        duration_ms: float | None,
        hmac_signature: str | None = None
    ) -> None:
        """Log a tool invocation for audit purposes.

        Args:
            tool_name: Name of tool invoked
            customer_id: Optional customer identifier
            params_hash: Optional SHA-256 hash of params
            status: Status (success, error, timeout, etc.)
            duration_ms: Execution duration in milliseconds
            hmac_signature: Optional HMAC-SHA256 signature
        """
        if self._pool is None:
            raise RuntimeError("Not connected to database")

        async with self._pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO audit_log
                (tool_name, customer_id, params_hash, result_status, duration_ms, hmac_signature)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, tool_name, customer_id, params_hash, status, duration_ms, hmac_signature)

            log.debug(
                "pg_audit_logged tool=%s customer=%s status=%s",
                tool_name, customer_id or "unknown", status
            )

    async def query_audit(
        self,
        customer_id: str | None = None,
        since: str | None = None,
        limit: int = 100
    ) -> list[dict]:
        """Query audit logs.

        Args:
            customer_id: Optional customer filter
            since: Optional ISO timestamp filter
            limit: Maximum results (default: 100)

        Returns:
            List of audit entries as dicts
        """
        if self._pool is None:
            raise RuntimeError("Not connected to database")

        query = "SELECT * FROM audit_log WHERE 1=1"
        params: list[Any] = []

        if customer_id:
            query += f" AND customer_id = ${len(params) + 1}"
            params.append(customer_id)

        if since:
            query += f" AND timestamp >= ${len(params) + 1}"
            params.append(since)

        query += f" ORDER BY timestamp DESC LIMIT ${len(params) + 1}"
        params.append(limit)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]


# Global singleton instance
_store_instance: PgStore | None = None


async def get_store() -> PgStore:
    """Get or create the global PgStore instance."""
    global _store_instance

    if _store_instance is None:
        _store_instance = PgStore()
        await _store_instance.connect()

    return _store_instance


# ===== MCP Tools =====


async def research_pg_migrate() -> dict:
    """Run database schema migration.

    Creates all required tables if they don't exist.
    Safe to run multiple times.

    Returns:
        Dict with migration_status, tables_created, and any errors
    """
    try:
        # Check if DATABASE_URL is set
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            log.warning("pg_migrate_skipped DATABASE_URL_not_set")
            return {
                "status": "skipped",
                "reason": "DATABASE_URL not set",
                "tables": []
            }

        # Get or create store
        store = await get_store()

        # Ensure schema
        await store.ensure_schema()

        return {
            "status": "success",
            "reason": "Schema migration completed",
            "tables": ["customers", "credits_ledger", "usage_meter", "audit_log"]
        }
    except Exception as e:
        log.error("pg_migrate_failed error=%s", str(e))
        return {
            "status": "failed",
            "reason": str(e),
            "tables": []
        }


async def research_pg_status() -> dict:
    """Check PostgreSQL connection and table status.

    Returns:
        Dict with connection_status, tables, and statistics
    """
    try:
        # Check if DATABASE_URL is set
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            return {
                "status": "disabled",
                "reason": "DATABASE_URL not set",
                "connection": "not_configured"
            }

        # Get or create store
        store = await get_store()
        pool = store._pool

        if pool is None:
            return {
                "status": "disconnected",
                "connection": "not_initialized"
            }

        # Get pool stats
        pool_size = pool.get_size()
        pool_free = pool.get_idle_size()

        # Check tables
        async with pool.acquire() as conn:
            tables_result = await conn.fetch("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)

            tables = [row["table_name"] for row in tables_result]

            # Get row counts
            stats = {}
            for table in tables:
                count_result = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                stats[table] = count_result or 0

        return {
            "status": "connected",
            "connection": "postgresql",
            "pool_size": pool_size,
            "pool_free": pool_free,
            "tables": tables,
            "row_counts": stats
        }
    except Exception as e:
        log.error("pg_status_check_failed error=%s", str(e))
        return {
            "status": "error",
            "reason": str(e)
        }
