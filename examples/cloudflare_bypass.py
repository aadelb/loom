#!/usr/bin/env python3
"""Stealth escalation ladder: demonstrates Cloudflare bypass strategies.

Shows how to handle Cloudflare-protected targets by escalating through:
1. Standard HTTP fetch with solve_cloudflare=True
2. Camoufox stealth browser if standard fails
3. Prints tool used, page title, and timing

Demonstrates the anti-bot challenge hierarchy that Loom provides.

Requires:
- Loom server running on http://127.0.0.1:8787/mcp
- Python 3.11+ with `mcp` package installed

Usage:
    python examples/cloudflare_bypass.py

    # Custom target (must be Cloudflare-protected)
    python examples/cloudflare_bypass.py --url https://your-cloudflare-site.com
"""
import argparse
import asyncio
import json
import time
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Demonstrate Cloudflare bypass escalation"
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://nopecha.com/demo/cloudflare",
        help="Cloudflare-protected target (default: nopecha demo page)",
    )

    args = parser.parse_args()

    url = "http://127.0.0.1:8787/mcp"
    target_url = args.url

    print(f"Target: {target_url}\n")
    print("Escalation ladder:")
    print("  1. HTTP fetch with solve_cloudflare=True")
    print("  2. Camoufox stealth browser\n")

    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Try 1: Standard fetch with Cloudflare solving
                print("Attempt 1: research_fetch with solve_cloudflare=True")
                start = time.time()
                fetch_result = await session.call_tool(
                    "research_fetch",
                    {
                        "url": target_url,
                        "mode": "stealthy",
                        "solve_cloudflare": True,
                        "max_chars": 5000,
                    },
                )
                elapsed_1 = time.time() - start
                body_1 = fetch_result.content[0].text if fetch_result.content else ""

                if body_1 and "error" not in body_1.lower():
                    title = extract_title(body_1)
                    print(f"  ✓ Success in {elapsed_1:.1f}s")
                    print(f"  Title: {title}")
                    print(f"  Size: {len(body_1)} chars")
                    return 0

                print(f"  ✗ Failed or blocked after {elapsed_1:.1f}s")
                if body_1:
                    print(f"  Response: {body_1[:150]}...")

                # Try 2: Camoufox stealth browser
                print("\nAttempt 2: research_camoufox stealth browser")
                start = time.time()
                camoufox_result = await session.call_tool(
                    "research_camoufox",
                    {
                        "url": target_url,
                        "max_chars": 5000,
                        "wait_for": "body",
                    },
                )
                elapsed_2 = time.time() - start
                body_2 = camoufox_result.content[0].text if camoufox_result.content else ""

                if body_2 and "error" not in body_2.lower():
                    title = extract_title(body_2)
                    print(f"  ✓ Success in {elapsed_2:.1f}s")
                    print(f"  Title: {title}")
                    print(f"  Size: {len(body_2)} chars")
                    return 0

                print(f"  ✗ Failed after {elapsed_2:.1f}s")
                if body_2:
                    print(f"  Response: {body_2[:150]}...")

                print("\nBoth escalation attempts failed.")
                print("Target may not be reachable or requires additional setup.")
                return 1

    except Exception as e:
        print(f"ERROR: {e}")
        return 1


def extract_title(html: str) -> str:
    """Extract <title> tag content from HTML."""
    import re

    match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    return match.group(1) if match else "(no title found)"


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
