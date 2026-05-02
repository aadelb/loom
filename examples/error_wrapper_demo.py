#!/usr/bin/env python3
"""Demonstration of the error_wrapper module.

Shows how the decorator catches exceptions and tracks errors,
preventing MCP client crashes.
"""

import asyncio
import sys

# For local testing
sys.path.insert(0, "../src")

from loom.tools.error_wrapper import (
    safe_tool_call,
    research_error_stats,
    research_error_clear,
)


# Example 1: Sync tool that succeeds
@safe_tool_call
def fetch_data_sync(url: str) -> dict:
    """Example tool that fetches data (succeeds)."""
    return {"url": url, "status": "ok", "data": "sample"}


# Example 2: Sync tool that fails
@safe_tool_call
def validate_url_sync(url: str) -> str:
    """Example tool that validates URL (fails gracefully)."""
    if not url.startswith("http"):
        raise ValueError("URL must start with http:// or https://")
    return url


# Example 3: Async tool that succeeds
@safe_tool_call
async def fetch_data_async(url: str) -> dict:
    """Example async tool that fetches data (succeeds)."""
    await asyncio.sleep(0.1)  # Simulate I/O
    return {"url": url, "status": "ok"}


# Example 4: Async tool that fails
@safe_tool_call
async def process_json_async(data: str) -> dict:
    """Example async tool that processes JSON (fails gracefully)."""
    await asyncio.sleep(0.05)
    import json

    return json.loads(data)


async def main():
    """Run demonstration."""
    print("=" * 60)
    print("Error Wrapper Demonstration")
    print("=" * 60)

    # Clear any previous error state
    await research_error_clear()

    # Example 1: Successful sync call
    print("\n1. Successful sync call:")
    result = fetch_data_sync("https://example.com")
    print(f"   Result: {result}")

    # Example 2: Failed sync call (returns error dict, doesn't crash)
    print("\n2. Failed sync call (gracefully handled):")
    result = validate_url_sync("not-a-url")
    print(f"   Result type: {type(result).__name__}")
    print(f"   Error: {result.get('error')}")
    print(f"   Error type: {result.get('error_type')}")

    # Example 3: Successful async call
    print("\n3. Successful async call:")
    result = await fetch_data_async("https://example.com")
    print(f"   Result: {result}")

    # Example 4: Failed async call (returns error dict, doesn't crash)
    print("\n4. Failed async call (gracefully handled):")
    result = await process_json_async("invalid json{")
    print(f"   Result type: {type(result).__name__}")
    print(f"   Error: {result.get('error')}")
    print(f"   Error type: {result.get('error_type')}")

    # Example 5: Multiple failures - error tracking
    print("\n5. Multiple failures (error tracking):")
    validate_url_sync("bad")
    validate_url_sync("bad")
    await process_json_async("{invalid")

    stats = await research_error_stats()
    print(f"   Total errors tracked: {stats['total_errors']}")
    print(f"   Tools with errors: {stats['total_tools_with_errors']}")

    for tool_name, tool_stats in stats["error_data"].items():
        print(f"\n   {tool_name}:")
        print(f"     - Count: {tool_stats['count']}")
        print(f"     - Error types: {tool_stats['error_types']}")

    # Example 6: Clear error history
    print("\n6. Clear error history:")
    clear_result = await research_error_clear()
    print(f"   Cleared: {clear_result['cleared']}")
    print(f"   Previous error count: {clear_result['previous_error_count']}")

    stats = await research_error_stats()
    print(f"   Errors after clear: {stats['total_errors']}")

    print("\n" + "=" * 60)
    print("Demonstration complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
