"""Example 4: Fetch multiple URLs in parallel.

The spider() method fetches multiple URLs concurrently with:
- Cloudflare bypass
- Content deduplication
- Configurable concurrency
- Error handling per URL

Run the Loom server first:
    loom serve

Then run this example:
    python examples/04_bulk_fetch.py
"""

import asyncio
from loom_sdk import LoomClient


async def main():
    """Fetch multiple URLs in parallel."""
    urls = [
        "https://example.com",
        "https://example.org",
        "https://example.net",
    ]

    async with LoomClient("http://127.0.0.1:8787") as client:
        print(f"Fetching {len(urls)} URLs in parallel...\n")

        results = await client.spider(
            urls=urls,
            mode="stealthy",
            concurrency=5,
            max_chars_each=5000,
        )

        print(f"Queued: {results.urls_queued}")
        print(f"Succeeded: {results.urls_succeeded}")
        print(f"Failed: {results.urls_failed}\n")

        for result in results.results:
            print(f"URL: {result.url}")
            print(f"Status: {result.status_code}")

            if result.content:
                preview = result.content[:100].replace("\n", " ")
                print(f"Content: {preview}...")
            elif result.error:
                print(f"Error: {result.error}")
            print()


if __name__ == "__main__":
    asyncio.run(main())
