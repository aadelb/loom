#!/usr/bin/env python3
"""Minimal MCP client example: connect, initialize, list tools, fetch a URL.

This is the first script new users should run. Shows how to:
- Connect to the Loom MCP server via streamable-http
- Initialize the session
- List available tools
- Call research_fetch on a public URL

Requires:
- Loom server running on http://127.0.0.1:8787/mcp
- Python 3.11+ with `mcp` package installed

Usage:
    python examples/quickstart.py
"""
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main() -> int:
    url = "http://127.0.0.1:8787/mcp"
    print(f"Connecting to {url}...")

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            # Initialize the session
            init = await session.initialize()
            print(f"OK: connected to {init.serverInfo.name} v{init.serverInfo.version}\n")

            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {len(tools.tools)}")
            for tool in tools.tools[:5]:
                print(f"  - {tool.name}")
            if len(tools.tools) > 5:
                print(f"  ... and {len(tools.tools) - 5} more\n")

            # Fetch a public URL
            print("Fetching https://example.com...")
            result = await session.call_tool(
                "research_fetch",
                {"url": "https://example.com", "mode": "http", "max_chars": 500},
            )
            body = result.content[0].text if result.content else ""
            if "example" in body.lower():
                print(f"OK: fetched {len(body)} chars")
                print(f"Preview: {body[:200]}...")
            else:
                print(f"ERROR: unexpected response: {body[:200]}")
                return 1

    print("\nSuccess!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
