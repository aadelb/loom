#!/usr/bin/env python3
"""Deep research workflow: search → fetch → summarize → answer with citations.

Demonstrates the full research pipeline:
1. Search for a topic using research_search (Exa provider)
2. Fetch top N results using research_spider
3. Summarize each result using research_llm_summarize (NVIDIA NIM)
4. Synthesize a cited answer using research_llm_answer

Writes final report to ./deep-out/<timestamp>.md with full citations.

Requires:
- Loom server running on http://127.0.0.1:8787/mcp
- Python 3.11+ with `mcp` package installed
- EXA_API_KEY environment variable set (for research_search)
- NVIDIA NIM API credentials (for research_llm_summarize/answer)

Usage:
    python examples/deep_research.py --query "latest advances in transformer efficiency"

    python examples/deep_research.py \\
      --query "How do large language models handle context windows?" \\
      --output ./my-research.md
"""
import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run deep research workflow")
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Research question to investigate",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output markdown file (default: ./deep-out/<timestamp>.md)",
    )
    parser.add_argument(
        "--search-count",
        type=int,
        default=10,
        help="Number of search results to fetch (default: 10)",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=3000,
        help="Max characters per page to fetch (default: 3000)",
    )

    args = parser.parse_args()

    # Setup output directory
    out_dir = Path("deep-out")
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.output:
        out_file = Path(args.output)
    else:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        out_file = out_dir / f"research_{timestamp}.md"

    url = "http://127.0.0.1:8787/mcp"

    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                print(f"Query: {args.query}\n")

                # Step 1: Search
                print("Step 1: Searching...")
                search_result = await session.call_tool(
                    "research_search",
                    {
                        "query": args.query,
                        "provider": "exa",
                        "n": args.search_count,
                    },
                )
                search_body = search_result.content[0].text if search_result.content else "[]"
                try:
                    search_results = json.loads(search_body)
                except json.JSONDecodeError:
                    print(f"ERROR: failed to parse search results")
                    return 1

                if not search_results:
                    print("No search results found.")
                    return 1

                print(f"Found {len(search_results)} results.")

                # Extract URLs for fetching
                urls = [
                    result.get("url")
                    for result in search_results
                    if result.get("url")
                ]
                urls = urls[: args.search_count]

                if not urls:
                    print("ERROR: no URLs found in search results")
                    return 1

                # Step 2: Fetch
                print(f"\nStep 2: Fetching {len(urls)} pages...")
                fetch_result = await session.call_tool(
                    "research_spider",
                    {
                        "urls": urls,
                        "mode": "stealthy",
                        "max_chars_each": args.max_chars,
                        "concurrency": 5,
                    },
                )
                fetch_body = fetch_result.content[0].text if fetch_result.content else "[]"
                try:
                    fetched_pages = json.loads(fetch_body)
                except json.JSONDecodeError:
                    print(f"ERROR: failed to parse fetch results")
                    return 1

                ok_pages = [
                    p for p in fetched_pages if isinstance(p, dict) and "error" not in p
                ]
                print(f"Successfully fetched {len(ok_pages)} pages.")

                # Step 3: Summarize
                print("\nStep 3: Summarizing pages...")
                summaries = []
                for i, page in enumerate(ok_pages[:5]):
                    title = page.get("title", f"Page {i+1}")
                    text = page.get("text", "")[:2000]
                    if not text:
                        continue

                    summary_result = await session.call_tool(
                        "research_llm_summarize",
                        {
                            "text": text,
                            "max_tokens": 300,
                        },
                    )
                    summary_body = (
                        summary_result.content[0].text
                        if summary_result.content
                        else ""
                    )
                    if summary_body:
                        summaries.append(
                            {
                                "title": title,
                                "url": urls[i] if i < len(urls) else "",
                                "summary": summary_body,
                            }
                        )

                print(f"Summarized {len(summaries)} pages.")

                # Step 4: Synthesize answer
                print("\nStep 4: Synthesizing answer...")
                sources = [
                    {"title": s["title"], "url": s["url"]} for s in summaries
                ]
                context = "\n\n".join(
                    [f"# {s['title']}\n{s['summary']}" for s in summaries]
                )

                answer_result = await session.call_tool(
                    "research_llm_answer",
                    {
                        "question": args.query,
                        "sources": sources,
                        "max_tokens": 800,
                        "style": "cited",
                    },
                )
                answer = (
                    answer_result.content[0].text
                    if answer_result.content
                    else ""
                )

                # Write report
                report = f"""# Research Report

**Query:** {args.query}

**Date:** {datetime.utcnow().isoformat()}

## Answer

{answer}

## Sources

{json.dumps(sources, indent=2)}

## Process

- Search provider: Exa
- Pages fetched: {len(ok_pages)}
- Pages summarized: {len(summaries)}
- LLM model: auto (fallback chain)
"""

                with open(out_file, "w") as f:
                    f.write(report)

                print(f"\nReport saved to: {out_file}")

    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
