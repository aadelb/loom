"""Example 2: Deep research pipeline.

The deep() method runs a full 12-stage pipeline:
1. Query expansion
2. Multi-provider search
3. Parallel fetch with Cloudflare bypass
4. Content extraction
5. Relevance ranking
6. Answer synthesis
7. GitHub enrichment
8. Language detection
9. Community sentiment (HN/Reddit)
10. Optional red-team analysis
11. Optional misinformation checks
12. Final report

Run the Loom server first:
    loom serve

Then run this example:
    python examples/02_deep_research.py
"""

import asyncio
from loom_sdk import LoomClient


async def main():
    """Deep research on transformers architecture."""
    async with LoomClient("http://127.0.0.1:8787") as client:
        print("Running deep research on 'transformers architecture'...\n")

        report = await client.deep(
            query="how does transformers architecture work",
            max_results=20,
            include_sentiment=False,
        )

        print(f"Query: {report.query}")
        print(f"Confidence: {report.confidence:.2%}\n")

        if report.summary:
            print("Summary:")
            print(report.summary)
            print()

        if report.findings:
            print("Key Findings:")
            for i, finding in enumerate(report.findings[:5], 1):
                print(f"{i}. {finding}")
            print()

        if report.sources:
            print(f"Sources ({len(report.sources)}):")
            for source in report.sources[:5]:
                print(f"- {source}")

        if report.error:
            print(f"\nError: {report.error}")


if __name__ == "__main__":
    asyncio.run(main())
