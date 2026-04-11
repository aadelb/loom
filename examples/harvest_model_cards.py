#!/usr/bin/env python3
"""Generic Hugging Face model card harvester via research_spider.

Fetches model cards from a list of HF model IDs, extracts titles and
descriptions via research_spider with concurrent fetches, and writes
results to ./harvest-out/ as JSON.

Requires:
- Loom server running on http://127.0.0.1:8787/mcp
- Python 3.11+ with `mcp` package installed

Usage:
    # Use default demo models
    python examples/harvest_model_cards.py

    # Provide custom models via CLI
    python examples/harvest_model_cards.py \\
      mistralai/Mistral-7B-v0.1 \\
      meta-llama/Meta-Llama-3-8B \\
      google/gemma-2b

    # Or load from a file (one model ID per line)
    python examples/harvest_model_cards.py --input models.txt
"""
import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


# Default demo models
DEFAULT_MODELS = [
    "mistralai/Mistral-7B-v0.1",
    "meta-llama/Meta-Llama-3-8B",
    "google/gemma-2b",
    "gpt2",
    "bert-base-uncased",
]


async def main() -> int:
    parser = argparse.ArgumentParser(description="Harvest HF model cards via Loom")
    parser.add_argument(
        "models",
        nargs="*",
        help="Model IDs to harvest (default: 5 popular open-source models)",
    )
    parser.add_argument(
        "--input",
        type=str,
        help="Read model IDs from file (one per line)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="harvest-out",
        help="Output directory for JSON files (default: harvest-out)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Concurrent fetches (default: 5)",
    )

    args = parser.parse_args()

    # Determine which models to harvest
    models = args.models if args.models else DEFAULT_MODELS
    if args.input:
        with open(args.input) as f:
            models = [line.strip() for line in f if line.strip()]

    if not models:
        print("ERROR: no models provided and no default models available")
        return 1

    # Create output directory
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build HF URLs for each model
    urls = [f"https://huggingface.co/{model}" for model in models]

    print(f"Harvesting {len(models)} models via Loom...\n")
    for model in models:
        print(f"  {model}")

    url = "http://127.0.0.1:8787/mcp"
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Fetch all model cards in parallel
            print(f"\nCalling research_spider with concurrency={args.concurrency}...")
            result = await session.call_tool(
                "research_spider",
                {
                    "urls": urls,
                    "mode": "stealthy",
                    "max_chars_each": 5000,
                    "concurrency": args.concurrency,
                },
            )

            body = result.content[0].text if result.content else "[]"
            try:
                rows = json.loads(body)
            except json.JSONDecodeError as e:
                print(f"ERROR: failed to parse spider response: {e}")
                return 1

            # Save results
            summary = {
                "timestamp": datetime.utcnow().isoformat(),
                "total_requested": len(models),
                "total_fetched": len(rows),
                "successful": sum(
                    1 for row in rows if isinstance(row, dict) and "error" not in row
                ),
                "failed": sum(
                    1 for row in rows if isinstance(row, dict) and "error" in row
                ),
                "models": models,
            }

            # Save individual results as JSON
            for i, (model, row) in enumerate(zip(models, rows)):
                if isinstance(row, dict):
                    model_file = out_dir / f"{model.replace('/', '_')}.json"
                    with open(model_file, "w") as f:
                        json.dump(row, f, ensure_ascii=False, indent=2)

            # Save summary
            summary_file = out_dir / "SUMMARY.json"
            with open(summary_file, "w") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)

            print(
                f"\nHarvest complete: {summary['successful']}/{summary['total_requested']} succeeded"
            )
            print(f"Results saved to: {out_dir}")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
