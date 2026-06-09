"""MCP server discovery and management tool.

Implements research_mcp_manage to:
  - Register external MCP servers
  - List registered servers + status
  - Remove servers
  - Toggle server enabled state
  - Probe health (reachability + latency)
  - Enumerate tools available on each server

Supports streamable-http MCP protocol for connecting to external servers.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import httpx

from loom.error_responses import handle_tool_errors
from loom.mcp_registry import (
    delete_registry_entry,
    format_registry_entry,
    get_registry_entry,
    load_registry,
    set_registry_entry,
    update_registry_entry,
)
from loom.validators import validate_url

logger = logging.getLogger("loom.tools.mcp_manager")


@handle_tool_errors("research_mcp_manage")
async def research_mcp_manage(
    action: str,
    name: str = "",
    url: str = "",
    enabled: bool = True,
    transport: str = "streamable-http",
) -> dict[str, Any]:
    """Manage external MCP servers for discovery and tool routing.

    Supports registering, listing, removing, toggling, probing health, and
    enumerating tools on external MCP servers via streamable-http protocol.

    Args:
        action: One of: list, add, remove, toggle, probe, tools
        name: Server name (required for add, remove, toggle, probe, tools)
        url: MCP endpoint URL (required for add; must be http/https)
        enabled: Enable/disable server (for add; default True)
        transport: Transport protocol (for add; default "streamable-http")

    Returns:
        Dict with action-specific results:
        - list: {servers: [{name, url, transport, enabled, status, ...}, ...]}
        - add: {name, url, enabled, message}
        - remove: {name, message}
        - toggle: {name, enabled, message}
        - probe: {name, url, reachable, status_code?, latency_ms?, error?}
        - tools: {name, url, tool_count, tools: [...], reachable}

    Raises:
        ValueError: if inputs are invalid (via Pydantic validation)
    """
    if action == "list":
        return _handle_list()
    elif action == "add":
        if not name or not url:
            return {"error": "action 'add' requires name and url"}
        return await _handle_add(name, url, enabled, transport)
    elif action == "remove":
        if not name:
            return {"error": "action 'remove' requires name"}
        return _handle_remove(name)
    elif action == "toggle":
        if not name:
            return {"error": "action 'toggle' requires name"}
        return _handle_toggle(name)
    elif action == "probe":
        if not name:
            return {"error": "action 'probe' requires name"}
        return await _handle_probe(name)
    elif action == "tools":
        if not name:
            return {"error": "action 'tools' requires name"}
        return await _handle_tools(name)
    else:
        return {"error": f"unknown action '{action}'"}


def _handle_list() -> dict[str, Any]:
    """List all registered MCP servers."""
    registry = load_registry()
    servers = [
        format_registry_entry(name, entry)
        for name, entry in sorted(registry.items())
    ]
    return {
        "servers": servers,
        "count": len(servers),
    }


async def _handle_add(
    name: str, url: str, enabled: bool, transport: str
) -> dict[str, Any]:
    """Add a new MCP server to the registry."""
    # Validate name format
    if not re.match(r"^[a-z0-9_-]{1,100}$", name):
        return {
            "error": "name must be 1-100 alphanumeric chars, underscore, or hyphen"
        }

    # Check for duplicate
    registry = load_registry()
    if name in registry:
        return {"error": f"server '{name}' already exists"}

    # Validate URL (reuses SSRF prevention from loom.validators)
    try:
        url = validate_url(url)
    except Exception as e:
        return {"error": f"invalid url: {e}"}

    # Create entry (status="unknown" until first probe)
    entry = {
        "url": url,
        "transport": transport,
        "enabled": enabled,
        "status": "unknown",
        "last_check_ts": None,
        "last_check_latency_ms": None,
        "tool_count": None,
        "error": None,
    }

    try:
        set_registry_entry(name, entry)
        return {
            "name": name,
            "url": url,
            "enabled": enabled,
            "message": f"server '{name}' added (status: unknown; run probe to verify)",
        }
    except Exception as e:
        logger.error("add_server_failed name=%s: %s", name, e)
        return {"error": f"failed to add server: {e}"}


def _handle_remove(name: str) -> dict[str, Any]:
    """Remove an MCP server from the registry."""
    entry = get_registry_entry(name)
    if not entry:
        return {"error": f"server '{name}' not found"}

    try:
        delete_registry_entry(name)
        return {
            "name": name,
            "message": f"server '{name}' removed",
        }
    except Exception as e:
        logger.error("remove_server_failed name=%s: %s", name, e)
        return {"error": f"failed to remove server: {e}"}


def _handle_toggle(name: str) -> dict[str, Any]:
    """Toggle enabled state of an MCP server."""
    entry = get_registry_entry(name)
    if not entry:
        return {"error": f"server '{name}' not found"}

    new_enabled = not entry.get("enabled", True)
    try:
        update_registry_entry(name, {"enabled": new_enabled})
        return {
            "name": name,
            "enabled": new_enabled,
            "message": f"server '{name}' is now {'enabled' if new_enabled else 'disabled'}",
        }
    except Exception as e:
        logger.error("toggle_server_failed name=%s: %s", name, e)
        return {"error": f"failed to toggle server: {e}"}


async def _handle_probe(name: str) -> dict[str, Any]:
    """Health-check an MCP server (reachability + latency)."""
    entry = get_registry_entry(name)
    if not entry:
        return {"error": f"server '{name}' not found"}

    url = entry.get("url", "")
    if not url:
        return {"error": f"server '{name}' has no url"}

    result = await _probe_server(url)
    result["name"] = name
    result["url"] = url

    # Update registry with probe results
    try:
        update_data = {
            "status": "reachable" if result["reachable"] else "unreachable",
            "last_check_ts": _iso_now(),
            "last_check_latency_ms": result.get("latency_ms"),
            "error": result.get("error"),
        }
        update_registry_entry(name, update_data)
    except Exception as e:
        logger.debug("probe_update_registry_failed name=%s: %s", name, e)

    return result


async def _handle_tools(name: str) -> dict[str, Any]:
    """List tools available on an MCP server."""
    entry = get_registry_entry(name)
    if not entry:
        return {"error": f"server '{name}' not found"}

    url = entry.get("url", "")
    if not url:
        return {"error": f"server '{name}' has no url"}

    result = await _list_tools(url)
    result["name"] = name
    result["url"] = url

    # Update tool count in registry
    if result.get("reachable") and result.get("tool_count"):
        try:
            update_registry_entry(
                name,
                {
                    "tool_count": result["tool_count"],
                    "last_check_ts": _iso_now(),
                    "status": "reachable",
                },
            )
        except Exception as e:
            logger.debug("tools_update_registry_failed name=%s: %s", name, e)

    return result


async def _probe_server(url: str) -> dict[str, Any]:
    """Probe a single MCP server for health (reachability + latency).

    Tries GET /health or POST /initialize (JSON-RPC init) with 15s timeout.

    Args:
        url: Full MCP endpoint URL

    Returns:
        Dict with keys:
          - reachable: bool
          - status_code: int (if reachable)
          - latency_ms: int
          - error: str (if error occurred)
    """
    timeout = httpx.Timeout(15.0, connect=5.0)
    result: dict[str, Any] = {
        "reachable": False,
        "latency_ms": 0,
        "error": None,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Try GET /health first (common MCP pattern)
        try:
            t0 = time.monotonic()
            response = await client.get(
                f"{url.rstrip('/')}/health", follow_redirects=True
            )
            latency_ms = int((time.monotonic() - t0) * 1000)
            if 200 <= response.status_code < 300:
                result["reachable"] = True
                result["status_code"] = response.status_code
                result["latency_ms"] = latency_ms
                logger.debug("probe_success url=%s latency_ms=%d", url, latency_ms)
                return result
        except Exception as e:
            logger.debug("probe_health_failed url=%s: %s", url, e)

        # Fallback: POST /initialize (JSON-RPC 2.0 init)
        try:
            t0 = time.monotonic()
            response = await client.post(
                url,
                json={"jsonrpc": "2.0", "method": "initialize", "id": 1},
                headers={"content-type": "application/json"},
            )
            latency_ms = int((time.monotonic() - t0) * 1000)
            if 200 <= response.status_code < 300:
                result["reachable"] = True
                result["status_code"] = response.status_code
                result["latency_ms"] = latency_ms
                logger.debug("probe_success url=%s latency_ms=%d", url, latency_ms)
                return result
            else:
                result["error"] = f"HTTP {response.status_code}"
                result["latency_ms"] = latency_ms
        except Exception as e:
            result["error"] = f"connection failed: {e}"

    return result


async def _list_tools(url: str) -> dict[str, Any]:
    """List tools available on an MCP server via JSON-RPC tools/list.

    Sends POST request with JSON-RPC 2.0 tools/list and parses response.
    Tolerates SSE framing. Caps tool list to 100 items.

    Args:
        url: Full MCP endpoint URL

    Returns:
        Dict with keys:
          - reachable: bool
          - tool_count: int (if reachable)
          - tools: list[str] (tool names, capped to 100)
          - error: str (if error occurred)
    """
    timeout = httpx.Timeout(15.0, connect=5.0)
    result: dict[str, Any] = {
        "reachable": False,
        "tool_count": 0,
        "tools": [],
        "error": None,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.post(
                url,
                json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
                headers={
                    "content-type": "application/json",
                    "accept": "application/json, text/event-stream",
                },
                follow_redirects=True,
            )

            if response.status_code != 200:
                result["error"] = f"HTTP {response.status_code}"
                return result

            result["reachable"] = True

            # Parse response (handle SSE framing)
            text = response.text.strip()
            tools = []

            # If SSE framed (data: prefix), extract JSON
            if text.startswith("data:"):
                lines = text.split("\n")
                for line in lines:
                    if line.startswith("data:"):
                        json_str = line[5:].strip()
                        try:
                            data = json.loads(json_str)
                            if isinstance(data, dict) and "result" in data:
                                tools_list = data.get("result", {}).get("tools", [])
                                if isinstance(tools_list, list):
                                    tools.extend(tools_list)
                        except json.JSONDecodeError:
                            pass
            else:
                # Try direct JSON parse
                try:
                    data = json.loads(text)
                    if isinstance(data, dict) and "result" in data:
                        tools_list = data.get("result", {}).get("tools", [])
                        if isinstance(tools_list, list):
                            tools = tools_list
                except json.JSONDecodeError:
                    pass

            # Extract tool names and cap to 100
            tool_names = []
            for tool in tools:
                if isinstance(tool, dict) and "name" in tool:
                    tool_names.append(tool["name"])
                elif isinstance(tool, str):
                    tool_names.append(tool)
            tool_names = tool_names[:100]

            result["tool_count"] = len(tool_names)
            result["tools"] = tool_names
            logger.debug(
                "tools_list_success url=%s tool_count=%d", url, len(tool_names)
            )

        except Exception as e:
            result["error"] = f"request failed: {e}"
            logger.debug("tools_list_failed url=%s: %s", url, e)

    return result


def _iso_now() -> str:
    """Return current UTC time in ISO 8601 format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
