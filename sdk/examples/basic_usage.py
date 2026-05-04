"""Basic usage examples for Loom SDK."""

import asyncio
import sys
from pathlib import Path

# Add parent to path for local import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loom_sdk import LoomClient


async def example_search() -> None:
    """Example: Multi-provider search."""
    print("\n=== Search Example ===")
    async with LoomClient("http://localhost:8787") as client:
        results = await client.search(
            "climate change impacts on agriculture",
            provider="auto",
            n=5,
        )
        print(f"Found {len(results.results)} results for: {results.query}")
        print(f"Provider: {results.provider}\n")

        for i, result in enumerate(results.results, 1):
            print(f"{i}. {result.title}")
            print(f"   URL: {result.url}")
            print(f"   Snippet: {result.snippet[:100]}...")
            if result.relevance_score:
                print(f"   Relevance: {result.relevance_score:.2f}")
            print()


async def example_fetch() -> None:
    """Example: Fetch URL content."""
    print("\n=== Fetch Example ===")
    async with LoomClient("http://localhost:8787") as client:
        result = await client.fetch(
            "https://en.wikipedia.org/wiki/Machine_learning",
            mode="auto",
        )
        print(f"URL: {result.url}")
        print(f"Status: {result.status_code}")
        print(f"Title: {result.title}")
        print(f"Content type: {result.content_type}")
        print(f"Body length: {result.body_length} bytes")
        print(f"Extraction time: {result.extraction_time_ms:.1f}ms")

        if result.markdown:
            markdown_preview = result.markdown[:200]
            print(f"\nMarkdown preview:\n{markdown_preview}...")


async def example_deep_research() -> None:
    """Example: Deep research pipeline."""
    print("\n=== Deep Research Example ===")
    async with LoomClient("http://localhost:8787") as client:
        result = await client.deep_research(
            "blockchain scalability solutions 2025",
            max_results=10,
        )
        print(f"Query: {result.query}")
        print(f"Sources found: {len(result.sources)}")
        print(f"Execution time: {result.execution_time_ms:.1f}ms\n")

        print("Key findings:")
        for finding in result.key_findings:
            print(f"• {finding}")

        print("\nTop sources:")
        for i, source in enumerate(result.sources[:5], 1):
            print(f"{i}. {source.title}")
            print(f"   ({source.provider}): {source.url}")

        if result.summary:
            print(f"\nSummary:\n{result.summary}")

        if result.citations:
            print(f"\nCitations ({len(result.citations)}):")
            for cite in result.citations[:3]:
                print(f"• {cite}")


async def example_llm_summarize() -> None:
    """Example: LLM text summarization."""
    print("\n=== LLM Summarize Example ===")

    long_text = """
    Artificial intelligence (AI) has become increasingly important in modern
    society. Machine learning, a subset of AI, enables computers to learn from
    data without being explicitly programmed. Deep learning, which uses neural
    networks with multiple layers, has achieved remarkable results in image
    recognition, natural language processing, and game playing.
    
    The transformer architecture, introduced by Vaswani et al., revolutionized
    NLP by enabling parallel processing of sequences. Large language models
    (LLMs) built on transformers have shown impressive capabilities in text
    generation, reasoning, and knowledge synthesis.
    
    However, these models also present challenges including bias, hallucination,
    and high computational costs. Researchers are actively working on improving
    efficiency, reliability, and alignment with human values.
    """

    async with LoomClient("http://localhost:8787") as client:
        result = await client.llm_summarize(
            long_text,
            max_words=100,
            model=None,  # Auto-select best provider
        )
        print(f"Original text length: {len(long_text.split())} words")
        print(f"Summary length: {result.word_count} words")
        print(f"Model used: {result.model}")
        print(f"Execution time: {result.execution_time_ms:.1f}ms")
        print(f"\nSummary:\n{result.summary}")


async def example_health_check() -> None:
    """Example: Server health check."""
    print("\n=== Health Check Example ===")
    async with LoomClient("http://localhost:8787") as client:
        health = await client.health()
        print(f"Server status: {health.status}")
        print(f"Version: {health.version}")
        print(f"Uptime: {health.uptime_seconds:.1f}s")
        print(f"Tools available: {health.tools_available}")
        print(f"Latency: {health.metadata.get('latency_ms', 'N/A'):.1f}ms")


async def example_generic_tool() -> None:
    """Example: Generic tool invocation."""
    print("\n=== Generic Tool Example ===")
    async with LoomClient("http://localhost:8787") as client:
        result = await client.call_tool(
            "research_github",
            query="async python context manager",
            sort="stars",
            per_page=5,
        )
        print(f"Tool: {result.tool_name}")
        print(f"Success: {result.success}")
        print(f"Execution time: {result.execution_time_ms:.1f}ms")

        if result.success and result.data:
            print(f"Data: {result.data}")
        elif result.error:
            print(f"Error: {result.error}")


async def main() -> None:
    """Run all examples."""
    print("Loom SDK Examples")
    print("=" * 50)

    # Note: These examples assume Loom server is running on localhost:8787
    # Start the server with: loom serve

    try:
        await example_health_check()
        await example_search()
        await example_fetch()
        await example_deep_research()
        await example_llm_summarize()
        await example_generic_tool()

        print("\n" + "=" * 50)
        print("All examples completed!")
    except Exception as e:
        print(f"\nError running examples: {e}")
        print("\nMake sure Loom server is running:")
        print("  loom serve")


if __name__ == "__main__":
    asyncio.run(main())
