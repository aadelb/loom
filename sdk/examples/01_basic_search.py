"""Example 1: Basic web search using Loom SDK.

Run the Loom server first:
    loom serve

Then run this example:
    python examples/01_basic_search.py
"""

import asyncio
from loom_sdk import LoomClient


async def main():
    """Search for AI safety research."""
    async with LoomClient("http://127.0.0.1:8787") as client:
        print("Searching for 'AI safety research'...\n")

        results = await client.search(
            query="AI safety research",
            provider="exa",
            n=5,
        )

        print(f"Provider: {results.provider}")
        print(f"Query: {results.query}")
        print(f"Results: {results.count}\n")

        for i, result in enumerate(results.results, 1):
            print(f"{i}. {result.title}")
            print(f"   URL: {result.url}")
            if result.snippet:
                print(f"   Snippet: {result.snippet[:100]}...")
            print()


if __name__ == "__main__":
    asyncio.run(main())
