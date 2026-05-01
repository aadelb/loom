#!/usr/bin/env python3
"""
Comprehensive MCP tool testing script.

Tests ALL registered tools through the MCP streamable-http protocol.
Generates minimal valid arguments based on tool schemas.
Reports success/failure for each tool.
"""

import asyncio
import json
import logging
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Optional
from pathlib import Path

try:
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession
except ImportError as e:
    print(f"ERROR: Failed to import mcp: {e}")
    print("Install: pip install mcp")
    sys.exit(1)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("test_mcp_tools")


@dataclass
class ToolResult:
    """Result of a single tool invocation."""
    tool_name: str
    status: str  # "success", "error", "timeout", "skip"
    response_size: int
    error_message: Optional[str] = None
    response_summary: Optional[str] = None
    elapsed_ms: float = 0.0


def generate_default_args(schema: dict) -> dict:
    """Generate minimal valid arguments from tool schema.

    Args:
        schema: Tool input schema (from tool definition)

    Returns:
        Dictionary of default arguments
    """
    args = {}

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")

        # Skip if not required
        if prop_name not in required:
            continue

        if prop_type == "string":
            # Check for specific patterns
            if "url" in prop_name.lower() or "link" in prop_name.lower():
                args[prop_name] = "https://example.com"
            elif "email" in prop_name.lower():
                args[prop_name] = "test@example.com"
            elif "query" in prop_name.lower() or "search" in prop_name.lower():
                args[prop_name] = "test"
            elif "path" in prop_name.lower():
                args[prop_name] = "/tmp/test"
            elif "id" in prop_name.lower() or "key" in prop_name.lower():
                args[prop_name] = "test_key"
            else:
                args[prop_name] = "test"

        elif prop_type == "integer":
            args[prop_name] = 5

        elif prop_type == "number":
            args[prop_name] = 3.14

        elif prop_type == "boolean":
            args[prop_name] = True

        elif prop_type == "array":
            item_type = prop_schema.get("items", {}).get("type", "string")
            if item_type == "string":
                args[prop_name] = ["test"]
            elif item_type == "integer":
                args[prop_name] = [1]
            else:
                args[prop_name] = []

        elif prop_type == "object":
            args[prop_name] = {}

        else:
            args[prop_name] = None

    return args


async def test_tool(
    session: ClientSession,
    tool_name: str,
    tool_schema: dict,
    timeout_sec: int = 30,
) -> ToolResult:
    """Test a single tool via MCP.

    Args:
        session: Active MCP client session
        tool_name: Name of the tool to test
        tool_schema: Tool input schema
        timeout_sec: Timeout in seconds

    Returns:
        ToolResult with status and details
    """
    start = datetime.now()
    args = generate_default_args(tool_schema)

    try:
        response = await asyncio.wait_for(
            session.call_tool(tool_name, args),
            timeout=timeout_sec,
        )

        elapsed = (datetime.now() - start).total_seconds() * 1000

        # Extract response content
        response_text = ""
        response_size = 0

        if hasattr(response, "content"):
            for item in response.content:
                if hasattr(item, "text"):
                    response_text += item.text
                elif hasattr(item, "blob"):
                    response_size += len(item.blob) if item.blob else 0

        response_size += len(response_text.encode("utf-8"))

        # Create summary (first 200 chars)
        summary = response_text[:200] if response_text else None

        return ToolResult(
            tool_name=tool_name,
            status="success",
            response_size=response_size,
            response_summary=summary,
            elapsed_ms=elapsed,
        )

    except asyncio.TimeoutError:
        elapsed = (datetime.now() - start).total_seconds() * 1000
        return ToolResult(
            tool_name=tool_name,
            status="timeout",
            response_size=0,
            error_message=f"Timeout after {timeout_sec}s",
            elapsed_ms=elapsed,
        )

    except Exception as e:
        elapsed = (datetime.now() - start).total_seconds() * 1000
        error_msg = f"{type(e).__name__}: {str(e)[:200]}"
        return ToolResult(
            tool_name=tool_name,
            status="error",
            response_size=0,
            error_message=error_msg,
            elapsed_ms=elapsed,
        )


async def list_all_tools(mcp_url: str) -> dict[str, dict]:
    """List all available tools from MCP server.

    Args:
        mcp_url: MCP server URL (e.g., http://127.0.0.1:8787/mcp)

    Returns:
        Dictionary mapping tool_name -> tool_schema
    """
    log.info(f"Connecting to MCP server at {mcp_url}...")

    async with streamablehttp_client(mcp_url) as (r, w, _):
        async with ClientSession(r, w) as session:
            await session.initialize()

            response = await session.list_tools()
            tools_dict = {}

            if hasattr(response, "tools"):
                for tool in response.tools:
                    tool_name = tool.name
                    tool_schema = {
                        "description": tool.description,
                        "properties": {},
                        "required": [],
                    }

                    # Extract schema from inputSchema
                    if hasattr(tool, "inputSchema"):
                        schema = tool.inputSchema
                        if isinstance(schema, dict):
                            tool_schema = schema

                    tools_dict[tool_name] = tool_schema

            log.info(f"Found {len(tools_dict)} tools")
            return tools_dict


async def test_all_tools(mcp_url: str, output_file: str) -> None:
    """Test all tools and save results.

    Args:
        mcp_url: MCP server URL
        output_file: Path to save JSON results
    """
    # List all tools
    tools_dict = await list_all_tools(mcp_url)

    if not tools_dict:
        log.error("No tools found!")
        return

    total_tools = len(tools_dict)
    log.info(f"Testing {total_tools} tools...")

    results: list[ToolResult] = []
    success_count = 0
    error_count = 0
    timeout_count = 0

    # Test each tool with a fresh session to avoid state issues
    for idx, (tool_name, tool_schema) in enumerate(tools_dict.items(), 1):
        try:
            # Create a new session for each tool
            async with streamablehttp_client(mcp_url) as (r, w, _):
                async with ClientSession(r, w) as session:
                    await session.initialize()

                    log.info(
                        f"[{idx}/{total_tools}] Testing: {tool_name}"
                    )

                    result = await test_tool(
                        session,
                        tool_name,
                        tool_schema,
                        timeout_sec=30,
                    )

                    results.append(result)

                    if result.status == "success":
                        success_count += 1
                        log.info(
                            f"  ✓ SUCCESS ({result.response_size} bytes, "
                            f"{result.elapsed_ms:.1f}ms)"
                        )
                    elif result.status == "timeout":
                        timeout_count += 1
                        log.warning(f"  ⏱ TIMEOUT: {result.error_message}")
                    else:
                        error_count += 1
                        log.error(
                            f"  ✗ ERROR: {result.error_message}"
                        )

        except Exception as e:
            log.error(f"Failed to test {tool_name}: {e}")
            results.append(
                ToolResult(
                    tool_name=tool_name,
                    status="error",
                    response_size=0,
                    error_message=f"Session error: {str(e)[:200]}",
                )
            )
            error_count += 1

    # Save results
    log.info(f"\nSaving results to {output_file}...")

    output_data = {
        "timestamp": datetime.now().isoformat(),
        "mcp_url": mcp_url,
        "summary": {
            "total": total_tools,
            "success": success_count,
            "error": error_count,
            "timeout": timeout_count,
            "success_rate": f"{100 * success_count / total_tools:.1f}%",
        },
        "results": [asdict(r) for r in results],
    }

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)

    log.info(f"Results saved to {output_file}")

    # Print summary
    print("\n" + "="*70)
    print("MCP TOOL TEST SUMMARY")
    print("="*70)
    print(f"Total tools: {total_tools}")
    print(f"Success:     {success_count} ({100*success_count/total_tools:.1f}%)")
    print(f"Errors:      {error_count}")
    print(f"Timeouts:    {timeout_count}")
    print("="*70)

    if error_count > 0 or timeout_count > 0:
        print("\nFailed tools:")
        for result in results:
            if result.status != "success":
                print(f"  - {result.tool_name}: {result.status}")
                if result.error_message:
                    print(f"    {result.error_message[:100]}")


async def main() -> None:
    """Main entry point."""
    mcp_url = "http://127.0.0.1:8787/mcp"
    output_file = "/tmp/all_mcp_tools_test.json"

    log.info(f"Starting MCP tool testing...")
    log.info(f"MCP URL: {mcp_url}")
    log.info(f"Output: {output_file}")

    await test_all_tools(mcp_url, output_file)


if __name__ == "__main__":
    asyncio.run(main())
