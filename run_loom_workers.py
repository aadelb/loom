#!/usr/bin/env python3
"""Loom MCP server launcher — multi-worker mode via uvicorn.

Usage (systemd or direct):
    uvicorn run_loom_workers:asgi_app --workers 4 --host 127.0.0.1 --port 8787 --limit-max-requests 50000

Each worker gets its own copy of the 642-tool server. SQLite uses WAL mode
for safe concurrent reads. In-memory sessions are per-worker (acceptable
for short-lived MCP tool calls).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from pathlib import Path

env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from loom.server import create_app
from loom.rest_api import create_rest_app

_mcp = create_app()
_mcp_asgi = _mcp.streamable_http_app()
_rest_app = create_rest_app(_mcp)


async def asgi_app(scope, receive, send):
    """Route /api/* to REST API, everything else to MCP."""
    if scope["type"] == "http" and scope["path"].startswith("/api/"):
        await _rest_app(scope, receive, send)
    else:
        await _mcp_asgi(scope, receive, send)
