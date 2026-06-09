"""Unit tests for research_mcp_manage tool.

Tests all 6 actions (list, add, remove, toggle, probe, tools) with offline
mocking and a temp registry file to ensure isolation.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.mcp_registry import (
    delete_registry_entry,
    format_registry_entry,
    get_registry_entry,
    load_registry,
    save_registry,
    set_registry_entry,
)
from loom.tools.infrastructure.mcp_manager import (
    _handle_add,
    _handle_list,
    _handle_probe,
    _handle_remove,
    _handle_toggle,
    _handle_tools,
    research_mcp_manage,
)


@pytest.fixture
def temp_registry():
    """Create a temporary registry for isolated testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "mcp_servers.json"

        # Patch get_registry_path to return our temp file
        with patch("loom.mcp_registry.get_registry_path", return_value=registry_path):
            yield registry_path

        # Cleanup
        if registry_path.exists():
            registry_path.unlink()


@pytest.fixture
def empty_registry(temp_registry):
    """Ensure registry is empty."""
    if temp_registry.exists():
        temp_registry.unlink()
    return temp_registry


@pytest.fixture
def mock_validate_url():
    """Mock validate_url to bypass SSRF checks for testing."""
    with patch("loom.tools.infrastructure.mcp_manager.validate_url", side_effect=lambda x: x):
        yield


class TestRegistryPersistence:
    """Test registry load/save/delete operations."""

    def test_load_empty_registry(self, empty_registry):
        """Load returns {} when registry doesn't exist."""
        result = load_registry()
        assert result == {}

    def test_save_and_load(self, empty_registry):
        """Save then load preserves data."""
        data = {
            "server1": {
                "url": "http://localhost:8787/mcp",
                "transport": "streamable-http",
                "enabled": True,
                "status": "unknown",
                "last_check_ts": None,
                "last_check_latency_ms": None,
                "tool_count": None,
                "error": None,
            }
        }
        save_registry(data)
        loaded = load_registry()
        assert loaded == data

    def test_set_entry(self, empty_registry):
        """set_registry_entry adds/updates entry immutably."""
        entry = {
            "url": "http://mcp1.local:8787/mcp",
            "transport": "streamable-http",
            "enabled": True,
            "status": "unknown",
            "last_check_ts": None,
            "last_check_latency_ms": None,
            "tool_count": None,
            "error": None,
        }
        set_registry_entry("mcp1", entry)

        stored = get_registry_entry("mcp1")
        assert stored is not None
        assert stored["url"] == "http://mcp1.local:8787/mcp"
        assert stored["enabled"] is True

    def test_delete_entry(self, empty_registry):
        """delete_registry_entry removes an entry immutably."""
        entry = {
            "url": "http://mcp1.local:8787/mcp",
            "transport": "streamable-http",
            "enabled": True,
        }
        set_registry_entry("mcp1", entry)
        assert get_registry_entry("mcp1") is not None

        delete_registry_entry("mcp1")
        assert get_registry_entry("mcp1") is None

    def test_update_entry(self, empty_registry):
        """update_registry_entry modifies fields immutably."""
        from loom.mcp_registry import update_registry_entry

        entry = {
            "url": "http://mcp1.local:8787/mcp",
            "transport": "streamable-http",
            "enabled": True,
        }
        set_registry_entry("mcp1", entry)

        update_registry_entry("mcp1", {"enabled": False})
        stored = get_registry_entry("mcp1")
        assert stored["enabled"] is False


class TestHandleList:
    """Test the 'list' action."""

    def test_list_empty(self, empty_registry):
        """List returns empty servers when registry is empty."""
        result = _handle_list()
        assert result["servers"] == []
        assert result["count"] == 0

    def test_list_multiple(self, empty_registry):
        """List returns all servers sorted by name."""
        set_registry_entry("server_a", {
            "url": "http://a.local:8787/mcp",
            "transport": "streamable-http",
            "enabled": True,
        })
        set_registry_entry("server_b", {
            "url": "http://b.local:8787/mcp",
            "transport": "streamable-http",
            "enabled": False,
        })

        result = _handle_list()
        assert result["count"] == 2
        assert len(result["servers"]) == 2
        assert result["servers"][0]["name"] == "server_a"
        assert result["servers"][1]["name"] == "server_b"


class TestHandleAdd:
    """Test the 'add' action."""

    @pytest.mark.asyncio
    async def test_add_valid(self, empty_registry, mock_validate_url):
        """Add a valid server."""
        result = await _handle_add("test_server", "http://127.0.0.1:8787/mcp", True, "streamable-http")
        assert result["name"] == "test_server"
        assert "added" in result.get("message", "").lower()
        assert get_registry_entry("test_server") is not None

    @pytest.mark.asyncio
    async def test_add_invalid_name(self, empty_registry):
        """Add rejects invalid names."""
        result = await _handle_add("INVALID NAME", "http://localhost:8787/mcp", True, "streamable-http")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_add_duplicate(self, empty_registry, mock_validate_url):
        """Add rejects duplicate names."""
        await _handle_add("test_server", "http://127.0.0.1:8787/mcp", True, "streamable-http")
        result = await _handle_add("test_server", "http://127.0.0.1:8888/mcp", True, "streamable-http")
        assert "error" in result
        assert "already exists" in result["error"]

    @pytest.mark.asyncio
    async def test_add_invalid_url(self, empty_registry):
        """Add rejects invalid URLs."""
        result = await _handle_add("test_server", "ftp://localhost:8787/mcp", True, "streamable-http")
        assert "error" in result


class TestHandleRemove:
    """Test the 'remove' action."""

    def test_remove_valid(self, empty_registry):
        """Remove an existing server."""
        set_registry_entry("test_server", {
            "url": "http://127.0.0.1:8787/mcp",
            "transport": "streamable-http",
            "enabled": True,
        })

        result = _handle_remove("test_server")
        assert result["name"] == "test_server"
        assert "removed" in result.get("message", "").lower()
        assert get_registry_entry("test_server") is None

    def test_remove_nonexistent(self, empty_registry):
        """Remove nonexistent server returns error."""
        result = _handle_remove("nonexistent")
        assert "error" in result


class TestHandleToggle:
    """Test the 'toggle' action."""

    def test_toggle_enabled_to_disabled(self, empty_registry):
        """Toggle flips enabled state."""
        set_registry_entry("test_server", {
            "url": "http://127.0.0.1:8787/mcp",
            "transport": "streamable-http",
            "enabled": True,
        })

        result = _handle_toggle("test_server")
        assert result["enabled"] is False
        assert get_registry_entry("test_server")["enabled"] is False

    def test_toggle_disabled_to_enabled(self, empty_registry):
        """Toggle flips disabled back to enabled."""
        set_registry_entry("test_server", {
            "url": "http://127.0.0.1:8787/mcp",
            "transport": "streamable-http",
            "enabled": False,
        })

        result = _handle_toggle("test_server")
        assert result["enabled"] is True

    def test_toggle_nonexistent(self, empty_registry):
        """Toggle nonexistent server returns error."""
        result = _handle_toggle("nonexistent")
        assert "error" in result


class TestHandleProbe:
    """Test the 'probe' action (with mocked HTTP)."""

    @pytest.mark.asyncio
    async def test_probe_success_health_endpoint(self, empty_registry):
        """Probe succeeds when /health returns 200."""
        set_registry_entry("test_server", {
            "url": "http://127.0.0.1:8787/mcp",
            "transport": "streamable-http",
            "enabled": True,
        })

        mock_response = AsyncMock()
        mock_response.status_code = 200

        with patch("loom.tools.infrastructure.mcp_manager.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _handle_probe("test_server")

        assert result["reachable"] is True
        assert "status_code" in result
        assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_probe_connection_error(self, empty_registry):
        """Probe handles connection errors gracefully."""
        set_registry_entry("test_server", {
            "url": "http://127.0.0.1:8787/mcp",
            "transport": "streamable-http",
            "enabled": True,
        })

        with patch("loom.tools.infrastructure.mcp_manager.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=Exception("connection refused"))
            mock_client_class.return_value = mock_client

            result = await _handle_probe("test_server")

        assert result["reachable"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_probe_nonexistent(self, empty_registry):
        """Probe nonexistent server returns error."""
        result = await _handle_probe("nonexistent")
        assert "error" in result


class TestHandleTools:
    """Test the 'tools' action (with mocked HTTP)."""

    @pytest.mark.asyncio
    async def test_tools_success(self, empty_registry):
        """List tools succeeds when server responds."""
        set_registry_entry("test_server", {
            "url": "http://127.0.0.1:8787/mcp",
            "transport": "streamable-http",
            "enabled": True,
        })

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {"name": "tool1"},
                    {"name": "tool2"},
                    {"name": "tool3"},
                ]
            },
            "id": 1,
        })

        with patch("loom.tools.infrastructure.mcp_manager.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _handle_tools("test_server")

        assert result["reachable"] is True
        assert result["tool_count"] == 3
        assert len(result["tools"]) == 3
        assert "tool1" in result["tools"]

    @pytest.mark.asyncio
    async def test_tools_caps_to_100(self, empty_registry):
        """Tools list is capped to 100 items."""
        set_registry_entry("test_server", {
            "url": "http://127.0.0.1:8787/mcp",
            "transport": "streamable-http",
            "enabled": True,
        })

        tools = [{"name": f"tool{i}"} for i in range(150)]
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({
            "jsonrpc": "2.0",
            "result": {"tools": tools},
            "id": 1,
        })

        with patch("loom.tools.infrastructure.mcp_manager.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _handle_tools("test_server")

        assert result["tool_count"] == 100
        assert len(result["tools"]) == 100

    @pytest.mark.asyncio
    async def test_tools_sse_framing(self, empty_registry):
        """Tools handles SSE-framed responses."""
        set_registry_entry("test_server", {
            "url": "http://127.0.0.1:8787/mcp",
            "transport": "streamable-http",
            "enabled": True,
        })

        # SSE-framed response
        sse_text = "data: " + json.dumps({
            "jsonrpc": "2.0",
            "result": {"tools": [{"name": "tool1"}]},
            "id": 1,
        })
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.text = sse_text

        with patch("loom.tools.infrastructure.mcp_manager.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await _handle_tools("test_server")

        assert result["reachable"] is True
        assert result["tool_count"] == 1

    @pytest.mark.asyncio
    async def test_tools_nonexistent(self, empty_registry):
        """Tools nonexistent server returns error."""
        result = await _handle_tools("nonexistent")
        assert "error" in result


class TestFullLifecycle:
    """Test the full lifecycle: add → list → toggle → remove."""

    @pytest.mark.asyncio
    async def test_lifecycle(self, empty_registry, mock_validate_url):
        """Full lifecycle without network."""
        # Add 2 servers (use localhost to avoid DNS resolution)
        result_add1 = await _handle_add(
            "server1", "http://127.0.0.1:8787/mcp", True, "streamable-http"
        )
        assert "error" not in result_add1, f"add1 error: {result_add1}"

        result_add2 = await _handle_add(
            "server2", "http://127.0.0.1:8788/mcp", True, "streamable-http"
        )
        assert "error" not in result_add2, f"add2 error: {result_add2}"

        # List should show both
        result_list = _handle_list()
        assert result_list["count"] == 2
        names = [s["name"] for s in result_list["servers"]]
        assert "server1" in names
        assert "server2" in names

        # Toggle server1
        result_toggle = _handle_toggle("server1")
        assert result_toggle["enabled"] is False

        # Remove server2
        result_remove = _handle_remove("server2")
        assert "error" not in result_remove

        # List should show only server1 (disabled)
        result_list2 = _handle_list()
        assert result_list2["count"] == 1
        assert result_list2["servers"][0]["name"] == "server1"
        assert result_list2["servers"][0]["enabled"] is False

    @pytest.mark.asyncio
    async def test_duplicate_add_rejected(self, empty_registry, mock_validate_url):
        """Duplicate add is rejected."""
        await _handle_add(
            "server1", "http://127.0.0.1:8787/mcp", True, "streamable-http"
        )

        # Try to add again
        result = await _handle_add(
            "server1", "http://127.0.0.1:8788/mcp", True, "streamable-http"
        )
        assert "error" in result
        assert "already exists" in result["error"]


@pytest.mark.asyncio
async def test_research_mcp_manage_integration(empty_registry, mock_validate_url):
    """Integration test via research_mcp_manage main function."""
    # List (empty)
    result = await research_mcp_manage("list")
    assert result["count"] == 0

    # Add
    result = await research_mcp_manage(
        "add",
        name="test1",
        url="http://127.0.0.1:8787/mcp",
        enabled=True,
        transport="streamable-http",
    )
    assert "error" not in result

    # List (1 server)
    result = await research_mcp_manage("list")
    assert result["count"] == 1

    # Toggle
    result = await research_mcp_manage("toggle", name="test1")
    assert result["enabled"] is False

    # Remove
    result = await research_mcp_manage("remove", name="test1")
    assert "error" not in result

    # List (empty again)
    result = await research_mcp_manage("list")
    assert result["count"] == 0
