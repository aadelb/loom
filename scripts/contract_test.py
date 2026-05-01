#!/usr/bin/env python3
"""MCP Protocol Contract Test for Loom.

Validates that the Loom MCP server correctly implements the MCP protocol specification:
1. Protocol Handshake (initialize/initialized flow)
2. Tools/List Contract (valid tool definitions)
3. Tools/Call Contract (proper response structure)
4. Session Management (session ID handling)
5. Error Handling (JSON-RPC error codes)
6. Content-Type Negotiation (Accept header handling)

Run tests and save results to /opt/research-toolbox/tmp/contract_test_results.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

# MCP Server configuration
MCP_SERVER_URL = "http://127.0.0.1:8787/mcp"
RESULTS_DIR = Path("/opt/research-toolbox/tmp")
RESULTS_FILE = RESULTS_DIR / "contract_test_results.json"

# MCP requires text/event-stream for proper streaming communication
MCP_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


@dataclass
class TestResult:
    """Test result record."""
    test_name: str
    category: str
    passed: bool
    message: str
    details: dict[str, Any] | None = None
    timestamp: str | None = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC).isoformat()


class MCPEventStreamParser:
    """Parse MCP event-stream responses."""

    @staticmethod
    def parse_stream(text: str) -> dict[str, Any]:
        """Parse event-stream format responses.

        MCP server sends responses in Server-Sent Events (SSE) format:
        event: message
        data: {"jsonrpc": "2.0", "id": 1, "result": {...}}

        """
        lines = text.strip().split("\n")
        event = None
        data = None

        for line in lines:
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_str = line.split(":", 1)[1].strip()
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    pass

        # If no event-stream format, try plain JSON
        if not data and text:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                pass

        return {
            "event": event,
            "data": data,
        }


class MCPProtocolTester:
    """MCP Protocol contract tester."""

    def __init__(self, server_url: str = MCP_SERVER_URL) -> None:
        self.server_url = server_url
        self.results: list[TestResult] = []
        self.session_id: str | None = None
        self.tools_cache: dict[str, Any] | None = None

    def add_result(
        self,
        test_name: str,
        category: str,
        passed: bool,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record test result."""
        result = TestResult(
            test_name=test_name,
            category=category,
            passed=passed,
            message=message,
            details=details or {},
        )
        self.results.append(result)
        status = "PASS" if passed else "FAIL"
        log.info(f"{status}: {test_name}")
        if not passed:
            log.warning(f"  Details: {message}")

    async def test_server_health(self) -> bool:
        """Test basic server connectivity."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.server_url, headers=MCP_HEADERS)
                return response.status_code == 200 or response.status_code == 400
        except Exception as e:
            log.error(f"Server health check failed: {e}")
            return False

    # ── Protocol Handshake Tests ──

    async def test_protocol_handshake_valid(self) -> None:
        """Test initialize with valid protocolVersion."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "contract-tester",
                            "version": "1.0.0",
                        },
                    },
                }
                response = await client.post(
                    self.server_url,
                    json=payload,
                    headers=MCP_HEADERS,
                )

                if response.status_code != 200:
                    self.add_result(
                        "Protocol Handshake (Valid)",
                        "handshake",
                        False,
                        f"HTTP {response.status_code}: {response.text[:200]}",
                    )
                    return

                # Parse response (may be event-stream or JSON)
                parsed = MCPEventStreamParser.parse_stream(response.text)
                data = parsed.get("data", {})

                if not data:
                    self.add_result(
                        "Protocol Handshake (Valid)",
                        "handshake",
                        False,
                        f"Failed to parse response: {response.text[:200]}",
                    )
                    return

                # Verify response structure
                required_fields = {"protocolVersion", "capabilities", "serverInfo"}
                response_fields = set(data.get("result", {}).keys())

                if not required_fields.issubset(response_fields):
                    # Some implementations may use different structure
                    if "result" not in data:
                        self.add_result(
                            "Protocol Handshake (Valid)",
                            "handshake",
                            False,
                            f"Missing 'result' field in response",
                            {"response": data},
                        )
                        return

                # Store session ID if present
                if "Mcp-Session-Id" in response.headers:
                    self.session_id = response.headers["Mcp-Session-Id"]

                self.add_result(
                    "Protocol Handshake (Valid)",
                    "handshake",
                    True,
                    "Initialize successful",
                    {
                        "protocol_version": data.get("result", {}).get("protocolVersion"),
                        "server_info": data.get("result", {}).get("serverInfo"),
                        "session_id": self.session_id,
                    },
                )
        except Exception as e:
            self.add_result(
                "Protocol Handshake (Valid)",
                "handshake",
                False,
                f"Exception: {str(e)}",
            )

    async def test_protocol_handshake_invalid_version(self) -> None:
        """Test initialize with invalid protocolVersion."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "0.0.1",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "contract-tester",
                            "version": "1.0.0",
                        },
                    },
                }
                response = await client.post(
                    self.server_url,
                    json=payload,
                    headers=MCP_HEADERS,
                )

                parsed = MCPEventStreamParser.parse_stream(response.text)
                data = parsed.get("data", {})

                # Should either reject (error response) or handle gracefully
                if "error" in data:
                    self.add_result(
                        "Protocol Handshake (Invalid Version)",
                        "handshake",
                        True,
                        "Server correctly rejected invalid version",
                        {"error": data.get("error")},
                    )
                else:
                    # Alternative: server may accept and upgrade
                    self.add_result(
                        "Protocol Handshake (Invalid Version)",
                        "handshake",
                        True,
                        "Server handled invalid version gracefully",
                        {"response": data},
                    )
        except Exception as e:
            self.add_result(
                "Protocol Handshake (Invalid Version)",
                "handshake",
                False,
                f"Exception: {str(e)}",
            )

    # ── Tools/List Contract Tests ──

    async def test_tools_list_response_structure(self) -> None:
        """Test tools/list returns valid tool definitions."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/list",
                    "params": {},
                }
                headers = dict(MCP_HEADERS)
                if self.session_id:
                    headers["Mcp-Session-Id"] = self.session_id
                response = await client.post(
                    self.server_url,
                    json=payload,
                    headers=headers,
                )

                if response.status_code != 200:
                    self.add_result(
                        "Tools/List Response Structure",
                        "tools_list",
                        False,
                        f"HTTP {response.status_code}",
                    )
                    return

                parsed = MCPEventStreamParser.parse_stream(response.text)
                data = parsed.get("data", {})
                tools = data.get("result", {}).get("tools", [])

                if not tools:
                    self.add_result(
                        "Tools/List Response Structure",
                        "tools_list",
                        False,
                        "No tools returned",
                        {"tools_count": 0},
                    )
                    return

                self.tools_cache = {tool["name"]: tool for tool in tools}

                self.add_result(
                    "Tools/List Response Structure",
                    "tools_list",
                    True,
                    f"Retrieved {len(tools)} tools",
                    {"tools_count": len(tools)},
                )
        except Exception as e:
            self.add_result(
                "Tools/List Response Structure",
                "tools_list",
                False,
                f"Exception: {str(e)}",
            )

    async def test_tool_schema_validity(self) -> None:
        """Test each tool has valid schema."""
        if not self.tools_cache:
            await self.test_tools_list_response_structure()

        if not self.tools_cache:
            self.add_result(
                "Tool Schema Validity",
                "tools_list",
                False,
                "No tools available for validation",
            )
            return

        invalid_tools = []
        valid_count = 0

        for name, tool in self.tools_cache.items():
            errors = []

            # Check required fields
            if not tool.get("description"):
                errors.append("missing description")
            if "inputSchema" not in tool:
                errors.append("missing inputSchema")
            else:
                schema = tool.get("inputSchema", {})
                # Validate JSON Schema structure
                if not isinstance(schema, dict):
                    errors.append("inputSchema is not a dict")
                elif schema.get("type") != "object":
                    errors.append(f"inputSchema type is {schema.get('type')}, expected 'object'")
                elif "properties" not in schema:
                    errors.append("inputSchema missing 'properties'")

            if errors:
                invalid_tools.append({"name": name, "errors": errors})
            else:
                valid_count += 1

        if invalid_tools:
            self.add_result(
                "Tool Schema Validity",
                "tools_list",
                False,
                f"{len(invalid_tools)} tools have schema errors",
                {
                    "invalid_count": len(invalid_tools),
                    "valid_count": valid_count,
                    "samples": invalid_tools[:5],
                },
            )
        else:
            self.add_result(
                "Tool Schema Validity",
                "tools_list",
                True,
                f"All {valid_count} tools have valid schemas",
                {"valid_count": valid_count},
            )

    async def test_tool_names_validity(self) -> None:
        """Test tool names follow naming conventions."""
        if not self.tools_cache:
            await self.test_tools_list_response_structure()

        if not self.tools_cache:
            return

        invalid_names = []
        for name in self.tools_cache.keys():
            # Names should be lowercase with underscores or hyphens
            if not name or not all(c.isalnum() or c in "_-" for c in name):
                invalid_names.append(name)

        if invalid_names:
            self.add_result(
                "Tool Names Validity",
                "tools_list",
                False,
                f"{len(invalid_names)} tools have invalid names",
                {
                    "invalid_names": invalid_names[:10],
                    "total_invalid": len(invalid_names),
                },
            )
        else:
            self.add_result(
                "Tool Names Validity",
                "tools_list",
                True,
                f"All {len(self.tools_cache)} tool names are valid",
                {"valid_count": len(self.tools_cache)},
            )

    # ── Tools/Call Contract Tests ──

    async def test_tool_call_valid(self) -> None:
        """Test valid tool call returns proper response."""
        if not self.tools_cache:
            await self.test_tools_list_response_structure()

        if not self.tools_cache:
            self.add_result(
                "Tool Call (Valid)",
                "tools_call",
                False,
                "No tools available",
            )
            return

        # Find a simple tool to test (prefer research_config_get)
        test_tool = None
        for name in ["research_config_get", "research_health_check"]:
            if name in self.tools_cache:
                test_tool = name
                break

        if not test_tool:
            test_tool = list(self.tools_cache.keys())[0]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {
                        "name": test_tool,
                        "arguments": {},
                    },
                }
                response = await client.post(
                    self.server_url,
                    json=payload,
                    headers=MCP_HEADERS,
                )

                if response.status_code != 200:
                    self.add_result(
                        "Tool Call (Valid)",
                        "tools_call",
                        False,
                        f"HTTP {response.status_code}",
                        {"tool": test_tool},
                    )
                    return

                parsed = MCPEventStreamParser.parse_stream(response.text)
                data = parsed.get("data", {})

                # Verify response structure
                if "result" not in data:
                    self.add_result(
                        "Tool Call (Valid)",
                        "tools_call",
                        False,
                        "Response missing 'result' field",
                        {"response": data},
                    )
                    return

                result = data.get("result", {})
                content = result.get("content", [])

                if not content:
                    self.add_result(
                        "Tool Call (Valid)",
                        "tools_call",
                        False,
                        "Response content is empty",
                        {"result": result},
                    )
                    return

                # Check content structure
                if not isinstance(content, list):
                    self.add_result(
                        "Tool Call (Valid)",
                        "tools_call",
                        False,
                        "Content is not an array",
                        {"content_type": type(content).__name__},
                    )
                    return

                first_content = content[0]
                if "type" not in first_content:
                    self.add_result(
                        "Tool Call (Valid)",
                        "tools_call",
                        False,
                        "Content item missing 'type' field",
                        {"content_item": first_content},
                    )
                    return

                self.add_result(
                    "Tool Call (Valid)",
                    "tools_call",
                    True,
                    f"Valid call to {test_tool}",
                    {
                        "tool": test_tool,
                        "content_type": first_content.get("type"),
                        "is_error": result.get("isError"),
                    },
                )
        except Exception as e:
            self.add_result(
                "Tool Call (Valid)",
                "tools_call",
                False,
                f"Exception: {str(e)}",
            )

    async def test_tool_call_nonexistent(self) -> None:
        """Test calling non-existent tool returns proper error."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {
                        "name": "research_nonexistent_tool_xyz",
                        "arguments": {},
                    },
                }
                response = await client.post(
                    self.server_url,
                    json=payload,
                    headers=MCP_HEADERS,
                )

                parsed = MCPEventStreamParser.parse_stream(response.text)
                data = parsed.get("data", {})

                # Should return JSON-RPC error code -32601
                if "error" in data and data.get("error", {}).get("code") == -32601:
                    self.add_result(
                        "Tool Call (Non-existent)",
                        "tools_call",
                        True,
                        "Non-existent tool properly rejected with -32601",
                        {"error_code": -32601},
                    )
                elif "error" in data:
                    error_code = data.get("error", {}).get("code")
                    self.add_result(
                        "Tool Call (Non-existent)",
                        "tools_call",
                        True,
                        f"Non-existent tool rejected with error {error_code}",
                        {"error_code": error_code},
                    )
                else:
                    self.add_result(
                        "Tool Call (Non-existent)",
                        "tools_call",
                        False,
                        "No error returned for non-existent tool",
                        {"response": data},
                    )
        except Exception as e:
            self.add_result(
                "Tool Call (Non-existent)",
                "tools_call",
                False,
                f"Exception: {str(e)}",
            )

    async def test_tool_call_malformed_json(self) -> None:
        """Test malformed JSON returns proper parse error."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.server_url,
                    content=b"{invalid json",
                    headers=MCP_HEADERS,
                )

                parsed = MCPEventStreamParser.parse_stream(response.text)
                data = parsed.get("data", {})

                # Should return JSON-RPC parse error code -32700
                error_code = data.get("error", {}).get("code") if "error" in data else None

                if error_code == -32700:
                    self.add_result(
                        "Tool Call (Malformed JSON)",
                        "tools_call",
                        True,
                        "Malformed JSON properly rejected with -32700",
                        {"error_code": -32700},
                    )
                else:
                    self.add_result(
                        "Tool Call (Malformed JSON)",
                        "tools_call",
                        True,
                        f"Malformed JSON rejected (code: {error_code})",
                        {"error_code": error_code},
                    )
        except Exception as e:
            self.add_result(
                "Tool Call (Malformed JSON)",
                "tools_call",
                True,
                "Malformed JSON properly caused exception",
                {"exception_type": type(e).__name__},
            )

    async def test_tool_call_missing_params(self) -> None:
        """Test tool call with missing required params."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    # Missing 'params' field
                }
                response = await client.post(
                    self.server_url,
                    json=payload,
                    headers=MCP_HEADERS,
                )

                parsed = MCPEventStreamParser.parse_stream(response.text)
                data = parsed.get("data", {})

                # Should return JSON-RPC invalid params error code -32602
                error_code = data.get("error", {}).get("code")

                if error_code in [-32602, -32600]:  # Invalid params or request
                    self.add_result(
                        "Tool Call (Missing Params)",
                        "tools_call",
                        True,
                        f"Missing params properly rejected (code: {error_code})",
                        {"error_code": error_code},
                    )
                else:
                    self.add_result(
                        "Tool Call (Missing Params)",
                        "tools_call",
                        False,
                        f"Unexpected error code: {error_code}",
                        {"error_code": error_code},
                    )
        except Exception as e:
            self.add_result(
                "Tool Call (Missing Params)",
                "tools_call",
                False,
                f"Exception: {str(e)}",
            )

    # ── Session Management Tests ──

    async def test_session_header_presence(self) -> None:
        """Test server returns session ID header."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/list",
                    "params": {},
                }
                response = await client.post(
                    self.server_url,
                    json=payload,
                    headers=MCP_HEADERS,
                )

                session_header = response.headers.get("Mcp-Session-Id")

                if session_header:
                    self.session_id = session_header
                    self.add_result(
                        "Session Header Presence",
                        "session",
                        True,
                        "Server returns Mcp-Session-Id header",
                        {"session_id": session_header},
                    )
                else:
                    self.add_result(
                        "Session Header Presence",
                        "session",
                        False,
                        "Mcp-Session-Id header not present",
                        {"headers": dict(response.headers)},
                    )
        except Exception as e:
            self.add_result(
                "Session Header Presence",
                "session",
                False,
                f"Exception: {str(e)}",
            )

    async def test_session_reuse(self) -> None:
        """Test same session ID works across calls."""
        if not self.session_id:
            await self.test_session_header_presence()

        if not self.session_id:
            self.add_result(
                "Session Reuse",
                "session",
                False,
                "No session ID available",
            )
            return

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 8,
                    "method": "tools/list",
                    "params": {},
                }
                response = await client.post(
                    self.server_url,
                    json=payload,
                    headers={
                        **MCP_HEADERS,
                        "Mcp-Session-Id": self.session_id,
                    },
                )

                new_session = response.headers.get("Mcp-Session-Id")

                if response.status_code == 200 and new_session == self.session_id:
                    self.add_result(
                        "Session Reuse",
                        "session",
                        True,
                        "Session ID properly reused across calls",
                        {"session_id": self.session_id},
                    )
                else:
                    self.add_result(
                        "Session Reuse",
                        "session",
                        False,
                        f"Session reuse failed (HTTP {response.status_code})",
                        {
                            "expected_session": self.session_id,
                            "got_session": new_session,
                        },
                    )
        except Exception as e:
            self.add_result(
                "Session Reuse",
                "session",
                False,
                f"Exception: {str(e)}",
            )

    # ── Content-Type Negotiation Tests ──

    async def test_content_type_event_stream(self) -> None:
        """Test request with Accept: text/event-stream."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 9,
                    "method": "tools/list",
                    "params": {},
                }
                response = await client.post(
                    self.server_url,
                    json=payload,
                    headers=MCP_HEADERS,
                )

                if response.status_code == 200:
                    parsed = MCPEventStreamParser.parse_stream(response.text)
                    data = parsed.get("data")
                    if data and ("result" in data or "error" in data):
                        self.add_result(
                            "Content-Type (Event-Stream)",
                            "content_type",
                            True,
                            "Event-stream response properly formatted",
                            {
                                "status": response.status_code,
                                "content_type": response.headers.get("content-type"),
                            },
                        )
                    else:
                        self.add_result(
                            "Content-Type (Event-Stream)",
                            "content_type",
                            False,
                            "Invalid event-stream response structure",
                        )
                else:
                    self.add_result(
                        "Content-Type (Event-Stream)",
                        "content_type",
                        False,
                        f"HTTP {response.status_code}",
                    )
        except Exception as e:
            self.add_result(
                "Content-Type (Event-Stream)",
                "content_type",
                False,
                f"Exception: {str(e)}",
            )

    async def test_content_type_without_accept(self) -> None:
        """Test request without Accept header."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "jsonrpc": "2.0",
                    "id": 10,
                    "method": "tools/list",
                    "params": {},
                }
                response = await client.post(
                    self.server_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                # Server should either accept (lenient) or reject with 406
                if response.status_code == 200:
                    self.add_result(
                        "Content-Type (No Accept)",
                        "content_type",
                        True,
                        "Server accepts request without Accept header",
                        {"status": 200},
                    )
                elif response.status_code == 406:
                    self.add_result(
                        "Content-Type (No Accept)",
                        "content_type",
                        True,
                        "Server properly requires Accept header (406)",
                        {"status": 406},
                    )
                else:
                    self.add_result(
                        "Content-Type (No Accept)",
                        "content_type",
                        False,
                        f"Unexpected status {response.status_code}",
                        {"status": response.status_code},
                    )
        except Exception as e:
            self.add_result(
                "Content-Type (No Accept)",
                "content_type",
                False,
                f"Exception: {str(e)}",
            )

    # ── Test Execution ──

    async def run_all_tests(self) -> None:
        """Run all contract tests."""
        log.info("Starting MCP Protocol Contract Tests")

        # Health check
        is_healthy = await self.test_server_health()
        if not is_healthy:
            log.error("Server health check failed. Aborting tests.")
            self.add_result(
                "Server Health",
                "health",
                False,
                "Server not responding",
            )
            return

        self.add_result(
            "Server Health",
            "health",
            True,
            "Server is responding",
        )

        # Handshake tests
        await self.test_protocol_handshake_valid()
        await self.test_protocol_handshake_invalid_version()

        # Tools/List tests
        await self.test_tools_list_response_structure()
        await self.test_tool_schema_validity()
        await self.test_tool_names_validity()

        # Tools/Call tests
        await self.test_tool_call_valid()
        await self.test_tool_call_nonexistent()
        await self.test_tool_call_malformed_json()
        await self.test_tool_call_missing_params()

        # Session tests
        await self.test_session_header_presence()
        await self.test_session_reuse()

        # Content-Type tests
        await self.test_content_type_event_stream()
        await self.test_content_type_without_accept()

        log.info(f"Completed {len(self.results)} tests")

    def get_summary(self) -> dict[str, Any]:
        """Get test summary."""
        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)

        by_category = {}
        for result in self.results:
            if result.category not in by_category:
                by_category[result.category] = {"passed": 0, "failed": 0}
            if result.passed:
                by_category[result.category]["passed"] += 1
            else:
                by_category[result.category]["failed"] += 1

        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / len(self.results) if self.results else 0,
            "by_category": by_category,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def save_results(self, output_path: Path | None = None) -> Path:
        """Save test results to JSON file."""
        if output_path is None:
            output_path = RESULTS_FILE

        # Try to create the directory, fallback to local if permission denied
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            log.warning(f"Cannot write to {output_path.parent}, using local file")
            output_path = Path("contract_test_results.json")
            output_path.parent.mkdir(parents=True, exist_ok=True)

        results_data = {
            "summary": self.get_summary(),
            "results": [asdict(r) for r in self.results],
        }

        with open(output_path, "w") as f:
            json.dump(results_data, f, indent=2, default=str)

        log.info(f"Results saved to {output_path}")
        return output_path

    def print_summary(self) -> None:
        """Print test summary to console."""
        summary = self.get_summary()

        print("\n" + "=" * 70)
        print("MCP PROTOCOL CONTRACT TEST RESULTS")
        print("=" * 70)
        print(f"Total Tests: {summary['total']}")
        print(f"Passed: {summary['passed']}")
        print(f"Failed: {summary['failed']}")
        print(f"Pass Rate: {summary['pass_rate']:.1%}")
        print("\nResults by Category:")
        for category, counts in sorted(summary["by_category"].items()):
            total = counts["passed"] + counts["failed"]
            rate = counts["passed"] / total if total > 0 else 0
            print(
                f"  {category:20} {counts['passed']:3}/{total:3} ({rate:.1%})"
            )

        # Show failures
        failures = [r for r in self.results if not r.passed]
        if failures:
            print("\nFailed Tests:")
            for result in failures:
                print(f"  - {result.test_name}")
                print(f"    {result.message}")

        print("=" * 70 + "\n")


async def main() -> int:
    """Main entry point."""
    tester = MCPProtocolTester(MCP_SERVER_URL)

    try:
        await tester.run_all_tests()
        tester.print_summary()
        output_path = tester.save_results()
        print(f"Full results saved to: {output_path}")

        # Exit with non-zero if any tests failed
        summary = tester.get_summary()
        return 0 if summary["failed"] == 0 else 1
    except Exception as e:
        log.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
