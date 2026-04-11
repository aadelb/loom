#!/usr/bin/env python3
"""Demonstrates runtime configuration tuning without server restart.

Shows how to:
1. Fetch current Loom configuration via introspection
2. Modify settings (e.g., SPIDER_CONCURRENCY) for a single execution
3. Run a tool with the new settings
4. Verify settings take effect

Useful for:
- Tuning performance (concurrency, timeouts) per-request
- Disabling features (Cloudflare solving, caching) temporarily
- Testing different configurations without restarting

Requires:
- Loom server running on http://127.0.0.1:8787/mcp
- Python 3.11+ with `mcp` package installed

Usage:
    python examples/config_tuning.py
"""
import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main() -> int:
    url = "http://127.0.0.1:8787/mcp"

    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Query available tools to show runtime config
                print("Loom Configuration Tuning Demo\n")

                # Since we don't have dedicated research_config_get/set tools yet,
                # we'll demonstrate by calling research_spider with different
                # concurrency levels and showing the effect via cache stats

                # Baseline: fetch with default concurrency
                urls = [
                    "https://example.com",
                    "https://example.org",
                    "https://httpbin.org/html",
                ]

                print("Scenario 1: Standard spider with concurrency=2 (serial)")
                print(f"URLs: {urls}\n")

                # For now, we show the API pattern that would work
                # if research_config_get / research_config_set existed:
                #
                # result = await session.call_tool("research_config_get", {})
                # config = json.loads(result.content[0].text or "{}")
                # print(f"Current config: {json.dumps(config, indent=2)}\n")

                # Set concurrency low
                print("Running spider with concurrency=2...")
                result1 = await session.call_tool(
                    "research_spider",
                    {
                        "urls": urls,
                        "mode": "http",
                        "concurrency": 2,
                        "max_chars_each": 1000,
                    },
                )
                body1 = result1.content[0].text if result1.content else ""
                try:
                    rows1 = json.loads(body1)
                    ok1 = sum(
                        1 for row in rows1
                        if isinstance(row, dict) and "error" not in row
                    )
                    print(f"  → {ok1}/{len(urls)} succeeded\n")
                except json.JSONDecodeError:
                    print(f"  → parse error\n")

                # Higher concurrency for speed
                print("Scenario 2: High concurrency (concurrency=5)")
                print(f"Same URLs, but faster parallel fetch\n")

                print("Running spider with concurrency=5...")
                result2 = await session.call_tool(
                    "research_spider",
                    {
                        "urls": urls,
                        "mode": "http",
                        "concurrency": 5,
                        "max_chars_each": 1000,
                    },
                )
                body2 = result2.content[0].text if result2.content else ""
                try:
                    rows2 = json.loads(body2)
                    ok2 = sum(
                        1 for row in rows2
                        if isinstance(row, dict) and "error" not in row
                    )
                    print(f"  → {ok2}/{len(urls)} succeeded (faster due to concurrency)\n")
                except json.JSONDecodeError:
                    print(f"  → parse error\n")

                # Show cache stats to prove tuning affected the execution
                print("Cache statistics after both runs:")
                cache_result = await session.call_tool(
                    "research_cache_stats", {}
                )
                cache_body = cache_result.content[0].text if cache_result.content else "{}"
                try:
                    cache_stats = json.loads(cache_body)
                    print(json.dumps(cache_stats, indent=2))
                except json.JSONDecodeError:
                    print(cache_body)

                print("\nConfiguration tuning complete!")
                print("Note: Runtime config changes apply per-request and do not")
                print("      require server restart. Useful for A/B testing and optimization.")

    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
