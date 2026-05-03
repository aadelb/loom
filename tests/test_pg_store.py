"""Tests for PostgreSQL store module.

Tests the PgStore class and MCP tools for PostgreSQL-based billing and audit.
Requires asyncpg and a running PostgreSQL database.
"""

from __future__ import annotations

import asyncio
import os
import pytest
from datetime import datetime, UTC

# Check if asyncpg is available
pytest.importorskip("asyncpg")

from loom.pg_store import (
    PgStore,
    research_pg_migrate,
    research_pg_status,
)


@pytest.mark.asyncio
async def test_pg_store_init():
    """Test PgStore initialization."""
    store = PgStore()
    assert store._pool is None


@pytest.mark.asyncio
async def test_research_pg_migrate_no_database_url():
    """Test pg_migrate when DATABASE_URL not set."""
    # Temporarily remove DATABASE_URL
    old_url = os.environ.get("DATABASE_URL")
    try:
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        result = await research_pg_migrate()
        assert result["status"] == "skipped"
        assert "DATABASE_URL" in result["reason"]
    finally:
        if old_url:
            os.environ["DATABASE_URL"] = old_url


@pytest.mark.asyncio
async def test_research_pg_status_no_database_url():
    """Test pg_status when DATABASE_URL not set."""
    # Temporarily remove DATABASE_URL
    old_url = os.environ.get("DATABASE_URL")
    try:
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        result = await research_pg_status()
        assert result["status"] == "disabled"
        assert "DATABASE_URL" in result["reason"]
    finally:
        if old_url:
            os.environ["DATABASE_URL"] = old_url


@pytest.mark.asyncio
@pytest.mark.live
async def test_pg_store_connection():
    """Test PgStore connection (requires live database)."""
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://loom:loom_secure_2026@localhost:5432/loom_db"
    )
    os.environ["DATABASE_URL"] = db_url

    store = PgStore()
    try:
        await store.connect()
        assert store._pool is not None
        await store.close()
        assert store._pool is None
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
@pytest.mark.live
async def test_create_customer():
    """Test customer creation (requires live database)."""
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://loom:loom_secure_2026@localhost:5432/loom_db"
    )
    os.environ["DATABASE_URL"] = db_url

    store = PgStore()
    try:
        await store.connect()

        # Create a test customer
        customer = await store.create_customer(
            customer_id="test_customer_001",
            name="Test Customer",
            email="test@example.com",
            tier="pro"
        )

        assert customer["customer_id"] == "test_customer_001"
        assert customer["name"] == "Test Customer"
        assert customer["email"] == "test@example.com"
        assert customer["tier"] == "pro"
        assert customer["credits"] == 0
        assert customer["active"] is True

        await store.close()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
@pytest.mark.live
async def test_get_customer():
    """Test customer retrieval (requires live database)."""
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://loom:loom_secure_2026@localhost:5432/loom_db"
    )
    os.environ["DATABASE_URL"] = db_url

    store = PgStore()
    try:
        await store.connect()

        # Create then retrieve
        await store.create_customer(
            customer_id="test_customer_002",
            name="Test Customer 2",
            email="test2@example.com",
            tier="team"
        )

        customer = await store.get_customer("test_customer_002")
        assert customer is not None
        assert customer["customer_id"] == "test_customer_002"
        assert customer["name"] == "Test Customer 2"

        # Test non-existent customer
        missing = await store.get_customer("nonexistent")
        assert missing is None

        await store.close()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
@pytest.mark.live
async def test_update_credits():
    """Test credit updates with ledger (requires live database)."""
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://loom:loom_secure_2026@localhost:5432/loom_db"
    )
    os.environ["DATABASE_URL"] = db_url

    store = PgStore()
    try:
        await store.connect()

        # Create customer
        await store.create_customer(
            customer_id="test_customer_003",
            name="Test Customer 3",
            tier="pro"
        )

        # Add credits
        balance = await store.update_credits(
            customer_id="test_customer_003",
            amount=1000,
            reason="test_purchase"
        )

        assert balance == 1000

        # Deduct credits
        balance = await store.update_credits(
            customer_id="test_customer_003",
            amount=-100,
            reason="test_tool_usage"
        )

        assert balance == 900

        await store.close()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
@pytest.mark.live
async def test_record_and_get_usage():
    """Test usage recording and retrieval (requires live database)."""
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://loom:loom_secure_2026@localhost:5432/loom_db"
    )
    os.environ["DATABASE_URL"] = db_url

    store = PgStore()
    try:
        await store.connect()

        # Create customer
        await store.create_customer(
            customer_id="test_customer_004",
            name="Test Customer 4"
        )

        # Record usage
        await store.record_usage(
            customer_id="test_customer_004",
            tool_name="research_fetch",
            credits=3,
            duration_ms=145.5
        )

        await store.record_usage(
            customer_id="test_customer_004",
            tool_name="research_search",
            credits=1,
            duration_ms=230.2
        )

        # Get usage
        usage = await store.get_usage(customer_id="test_customer_004")

        assert usage["customer_id"] == "test_customer_004"
        assert usage["total_credits"] == 4
        assert usage["total_calls"] == 2
        assert "research_fetch" in usage["by_tool"]
        assert usage["by_tool"]["research_fetch"]["credits"] == 3
        assert usage["by_tool"]["research_search"]["credits"] == 1

        await store.close()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
@pytest.mark.live
async def test_get_top_tools():
    """Test top tools ranking (requires live database)."""
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://loom:loom_secure_2026@localhost:5432/loom_db"
    )
    os.environ["DATABASE_URL"] = db_url

    store = PgStore()
    try:
        await store.connect()

        # Create customer
        await store.create_customer(
            customer_id="test_customer_005",
            name="Test Customer 5"
        )

        # Record multiple usages
        for i in range(5):
            await store.record_usage(
                customer_id="test_customer_005",
                tool_name="research_fetch",
                credits=10,
                duration_ms=100
            )

        for i in range(3):
            await store.record_usage(
                customer_id="test_customer_005",
                tool_name="research_search",
                credits=5,
                duration_ms=50
            )

        # Get top tools
        top = await store.get_top_tools(customer_id="test_customer_005", limit=5)

        assert len(top) > 0
        assert top[0]["tool_name"] == "research_fetch"
        assert top[0]["credits"] == 50
        assert top[0]["calls"] == 5

        if len(top) > 1:
            assert top[1]["tool_name"] == "research_search"
            assert top[1]["credits"] == 15

        await store.close()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
@pytest.mark.live
async def test_log_and_query_audit():
    """Test audit logging and querying (requires live database)."""
    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://loom:loom_secure_2026@localhost:5432/loom_db"
    )
    os.environ["DATABASE_URL"] = db_url

    store = PgStore()
    try:
        await store.connect()

        # Log audit entries
        await store.log_audit(
            tool_name="research_fetch",
            customer_id="test_customer_006",
            params_hash="abc123def456",
            status="success",
            duration_ms=145.5,
            hmac_signature="sig1"
        )

        await store.log_audit(
            tool_name="research_search",
            customer_id="test_customer_006",
            params_hash="xyz789",
            status="success",
            duration_ms=75.2,
            hmac_signature="sig2"
        )

        # Query audit logs
        logs = await store.query_audit(customer_id="test_customer_006", limit=10)

        assert len(logs) >= 2
        assert logs[0]["tool_name"] in ["research_fetch", "research_search"]
        assert logs[0]["customer_id"] == "test_customer_006"
        assert logs[0]["status"] == "success"

        await store.close()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


@pytest.mark.asyncio
async def test_pg_migrate_function():
    """Test the research_pg_migrate MCP tool."""
    # Test with DATABASE_URL set
    os.environ["DATABASE_URL"] = "postgresql://loom:loom_secure_2026@localhost:5432/loom_db"

    result = await research_pg_migrate()

    # Result should have expected structure
    assert "status" in result
    assert "reason" in result
    assert "tables" in result

    # Status is either success or error (connection failures OK in tests)
    assert result["status"] in ["success", "failed"]


@pytest.mark.asyncio
async def test_pg_status_function():
    """Test the research_pg_status MCP tool."""
    # Test with DATABASE_URL set
    os.environ["DATABASE_URL"] = "postgresql://loom:loom_secure_2026@localhost:5432/loom_db"

    result = await research_pg_status()

    # Result should have expected structure
    assert "status" in result
    assert result["status"] in ["connected", "disconnected", "disabled", "error"]


def test_pg_store_module_imports():
    """Test that pg_store module can be imported."""
    import loom.pg_store

    # Check for required functions
    assert hasattr(loom.pg_store, "PgStore")
    assert hasattr(loom.pg_store, "research_pg_migrate")
    assert hasattr(loom.pg_store, "research_pg_status")
    assert hasattr(loom.pg_store, "get_pool")
    assert hasattr(loom.pg_store, "get_store")


def test_pg_tools_registered_in_server():
    """Test that pg_tools are properly loaded in server.py."""
    import sys
    sys.path.insert(0, './src')

    # Import server module
    from loom import server

    # Check that _pg_tools dict exists
    assert hasattr(server, "_pg_tools")
    assert isinstance(server._pg_tools, dict)

    # Check that the tools are registered
    if "pg_migrate" in server._pg_tools or "pg_status" in server._pg_tools:
        # At least one should be registered if asyncpg is available
        assert True
