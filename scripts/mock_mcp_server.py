#!/usr/bin/env python3
"""Mock MCP Server for testing the contract test suite.

Implements a minimal MCP server that validates against the protocol specification.
Useful for testing the contract_test.py script without running the full Loom server.

Usage:
    python3 mock_mcp_server.py --port 8888
    # In another terminal:
    python3 contract_test.py --server http://127.0.0.1:8888/mcp
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

try:
    import uvicorn
    from fastapi import FastAPI, Request, Response
    from fastapi.responses import StreamingResponse
except ImportError:
    print("Error: FastAPI and uvicorn required. Install with: pip install fastapi uvicorn")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

app = FastAPI(title="Mock MCP Server")


class MockMCPServer:
    """Mock MCP server implementation."""

    def __init__(self) -> None:
        self.sessions: dict[str, dict[str, Any]] = {}
        self.tools: dict[str, dict[str, Any]] = {
            "research_fetch": {
                "name": "research_fetch",
                "description": "Fetch content from a URL with anti-bot protection",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to fetch"},
                        "mode": {
                            "type": "string",
                            "enum": ["http", "stealthy", "dynamic"],
                            "description": "Fetch mode",
                        },
                    },
                    "required": ["url"],
                },
            },
            "research_spider": {
                "name": "research_spider",
                "description": "Multi-URL fetch with concurrent requests",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URLs to fetch",
                        },
                    },
                    "required": ["urls"],
                },
            },
            "research_config_get": {
                "name": "research_config_get",
                "description": "Get a configuration value",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Config key"},
                    },
                    "required": ["key"],
                },
            },
        }

    def format_event_stream(self, data: dict[str, Any]) -> str:
        """Format response as MCP event stream."""
        return f"event: message\ndata: {json.dumps(data)}\n\n"

    async def handle_initialize(
        self, request_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle initialize method."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "MockMCP",
                    "version": "1.0.0",
                },
            },
        }

    async def handle_tools_list(self, request_id: str) -> dict[str, Any]:
        """Handle tools/list method."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": list(self.tools.values()),
            },
        }

    async def handle_tools_call(
        self, request_id: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle tools/call method."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tools:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}",
                },
            }

        # Mock successful tool call
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": f"Mock response from {tool_name}",
                    }
                ],
                "isError": False,
            },
        }

    async def process_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Process a JSON-RPC request."""
        # Validate JSON-RPC structure
        if "jsonrpc" not in payload or payload["jsonrpc"] != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": payload.get("id", "unknown"),
                "error": {
                    "code": -32600,
                    "message": "Invalid Request",
                },
            }

        request_id = payload.get("id", str(uuid.uuid4()))
        method = payload.get("method")
        params = payload.get("params", {})

        # Route to appropriate handler
        try:
            if method == "initialize":
                return await self.handle_initialize(request_id, params)
            elif method == "tools/list":
                return await self.handle_tools_list(request_id)
            elif method == "tools/call":
                return await self.handle_tools_call(request_id, params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}",
                    },
                }
        except Exception as e:
            log.error(f"Error processing request: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                },
            }


# Global mock server instance
mock_server = MockMCPServer()


@app.post("/mcp")
async def mcp_endpoint(request: Request) -> Response:
    """MCP protocol endpoint."""
    # Check Accept header
    accept_header = request.headers.get("Accept", "")
    if (
        "application/json" not in accept_header
        and "text/event-stream" not in accept_header
    ):
        return Response(
            content=json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": "server-error",
                    "error": {
                        "code": -32600,
                        "message": "Not Acceptable: Client must accept application/json or text/event-stream",
                    },
                }
            ),
            status_code=406,
            media_type="application/json",
        )

    # Get session ID from header or create new
    session_id = request.headers.get("Mcp-Session-Id") or str(uuid.uuid4())

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return Response(
            content=mock_server.format_event_stream(
                {
                    "jsonrpc": "2.0",
                    "id": "parse-error",
                    "error": {
                        "code": -32700,
                        "message": "Parse error",
                    },
                }
            ),
            status_code=200,
            media_type="text/event-stream",
            headers={"Mcp-Session-Id": session_id},
        )

    # Process request
    result = await mock_server.process_request(payload)

    # Format as event stream
    response_body = mock_server.format_event_stream(result)

    return Response(
        content=response_body,
        status_code=200,
        media_type="text/event-stream",
        headers={"Mcp-Session-Id": session_id},
    )


@app.get("/")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "MockMCP"}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mock MCP Server")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=8888, help="Server port")
    args = parser.parse_args()

    log.info(f"Starting Mock MCP Server on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
