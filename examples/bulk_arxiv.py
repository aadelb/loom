#!/usr/bin/env python3
"""Daily arXiv crawler: fetch listings, spider abstracts, classify papers.

Fetches arXiv listings for a category and date range, extracts paper IDs,
fetches each abstract via research_spider, and classifies each into
[theoretical, applied, survey, dataset, benchmark] using research_llm_classify.

Writes results to ./arxiv-out/<date>.csv with columns:
  paper_id, title, category, abstract_snippet, classification

Requires:
- Loom server running on http://127.0.0.1:8787/mcp
- Python 3.11+ with `mcp` package installed
- NVIDIA NIM API credentials (for research_llm_classify)

Usage:
    # Fetch CS > Computation & Language for the last 1 day
    python examples/bulk_arxiv.py --category cs.CL --days 1

    # Fetch 3 days of papers
    python examples/bulk_arxiv.py --category cs.AI --days 3

    # Use different output dir
    python examples/bulk_arxiv.py --category cs.CL --days 1 --output ./my-papers.csv
"""
import argparse
import asyncio
import csv
import html
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def extract_arxiv_id(url: str) -> str | None:
    """Extract arXiv ID from URL like https://arxiv.org/abs/2401.12345."""
    match = re.search(r"(\d{4}\.\d{5})", url)
    return match.group(1) if match else None


async def main() -> int:
    parser = argparse.ArgumentParser(description="Crawl arXiv and classify papers")
    parser.add_argument(
        "--category",
        type=str,
        default="cs.CL",
        help="arXiv category (default: cs.CL for NLP)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Number of days to crawl (default: 1)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output CSV file (default: ./arxiv-out/<date>.csv)",
    )
    parser.add_argument(
        "--max-papers",
        type=int,
        default=50,
        help="Max papers to fetch and classify (default: 50)",
    )

    args = parser.parse_args()

    # Setup output directory
    out_dir = Path("arxiv-out")
    out_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.utcnow().strftime("%Y%m%d")
    if args.output:
        csv_file = Path(args.output)
    else:
        csv_file = out_dir / f"arxiv_{date_str}_{args.category.replace('.', '_')}.csv"

    url = "http://127.0.0.1:8787/mcp"

    try:
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Build arXiv listing URL
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=args.days)

                # arXiv query: category + date range
                query = f"cat:{args.category} AND submittedDate:[{start_date.strftime('%Y%m%d%H%M%S')} TO {end_date.strftime('%Y%m%d%H%M%S')}]"
                arxiv_url = f"https://arxiv.org/cgi-bin/arxiv_browse.cgi?is_arxiv=1&query={quote(query)}&searchtype=query&abstracts=show&size=100"

                print(f"Fetching arXiv listing for {args.category}...")
                print(f"URL: {arxiv_url[:100]}...\n")

                # Fetch the arXiv listing
                fetch_result = await session.call_tool(
                    "research_fetch",
                    {
                        "url": arxiv_url,
                        "mode": "http",
                        "max_chars": 20000,
                    },
                )
                listing_body = fetch_result.content[0].text if fetch_result.content else ""

                if not listing_body:
                    print("ERROR: failed to fetch arXiv listing")
                    return 1

                # Extract paper links
                paper_links = re.findall(
                    r"https://arxiv\.org/abs/\d{4}\.\d{5}", listing_body
                )
                paper_ids = list(set(extract_arxiv_id(link) for link in paper_links))
                paper_ids = [p for p in paper_ids if p]
                paper_ids = paper_ids[: args.max_papers]

                print(f"Found {len(paper_ids)} unique papers")

                if not paper_ids:
                    print("No papers found. Exiting.")
                    return 0

                # Fetch abstract pages
                abstract_urls = [f"https://arxiv.org/abs/{pid}" for pid in paper_ids]
                print(f"\nFetching {len(abstract_urls)} abstracts...")

                fetch_result = await session.call_tool(
                    "research_spider",
                    {
                        "urls": abstract_urls,
                        "mode": "http",
                        "max_chars_each": 2000,
                        "concurrency": 5,
                    },
                )
                fetch_body = fetch_result.content[0].text if fetch_result.content else "[]"
                try:
                    abstract_pages = json.loads(fetch_body)
                except json.JSONDecodeError:
                    print("ERROR: failed to parse abstract pages")
                    return 1

                print(f"Fetched {len(abstract_pages)} pages")

                # Classify papers
                print("\nClassifying papers...")
                results = []

                for i, (pid, page) in enumerate(zip(paper_ids, abstract_pages)):
                    if not isinstance(page, dict) or "error" in page:
                        continue

                    title = page.get("title", "Unknown")
                    text = page.get("text", "")

                    # Extract first ~500 chars of abstract
                    abstract_match = re.search(r"Abstract:?\s*(.{1,500})", text)
                    abstract_snippet = (
                        html.unescape(abstract_match.group(1))
                        if abstract_match
                        else text[:200]
                    )

                    # Classify
                    classify_result = await session.call_tool(
                        "research_llm_classify",
                        {
                            "text": f"Title: {title}\n\nAbstract: {abstract_snippet}",
                            "labels": [
                                "theoretical",
                                "applied",
                                "survey",
                                "dataset",
                                "benchmark",
                            ],
                            "multi_label": False,
                        },
                    )
                    classify_body = (
                        classify_result.content[0].text
                        if classify_result.content
                        else ""
                    )

                    # Parse classification (assuming it's JSON with "label" key)
                    try:
                        classify_json = json.loads(classify_body)
                        classification = classify_json.get("label", "other")
                    except json.JSONDecodeError:
                        classification = classify_body.strip() if classify_body else "other"

                    results.append(
                        {
                            "paper_id": pid,
                            "title": title,
                            "category": args.category,
                            "abstract_snippet": abstract_snippet,
                            "classification": classification,
                        }
                    )

                    if (i + 1) % 10 == 0:
                        print(f"  ... classified {i + 1}/{len(paper_ids)}")

                # Write CSV
                with open(csv_file, "w", newline="", encoding="utf-8") as f:
                    if results:
                        writer = csv.DictWriter(
                            f,
                            fieldnames=[
                                "paper_id",
                                "title",
                                "category",
                                "abstract_snippet",
                                "classification",
                            ],
                        )
                        writer.writeheader()
                        writer.writerows(results)

                print(f"\nClassified {len(results)} papers")
                print(f"Results saved to: {csv_file}")

    except Exception as e:
        print(f"ERROR: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
