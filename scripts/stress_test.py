#!/usr/bin/env python3
"""Live stress test for deep research pipeline with 5 different query types.

Runs 5 queries through the full 12-stage deep research pipeline, each with
distinct query types to verify auto-detection and provider routing:

  1. "AI safety alignment research 2024" (academic → arxiv)
  2. "dark web marketplace tor hidden services" (darkweb → ahmia/darksearch)
  3. "bitcoin price prediction ethereum crypto" (finance → binance/investing)
  4. "latest breaking news technology 2026" (news → newsapi)
  5. "Python FastAPI web framework tutorial" (code → github)

Usage:
  PYTHONPATH=src python3 scripts/stress_test.py                    # real providers
  PYTHONPATH=src python3 scripts/stress_test.py --mock             # mocked results
  PYTHONPATH=src python3 scripts/stress_test.py --mock --verbose   # detailed output

Works on both Mac (orchestration only) and Hetzner (with API keys).
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("stress_test")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


@dataclass
class QueryTest:
    """Metadata for a single stress test query."""

    query: str
    expected_types: set[str]
    description: str


# Test queries with expected auto-detected types
TEST_QUERIES = [
    QueryTest(
        query="AI safety alignment research 2024",
        expected_types={"academic"},
        description="Academic paper search (should detect arxiv provider)",
    ),
    QueryTest(
        query="dark web marketplace tor hidden services",
        expected_types={"darkweb"},
        description="Darkweb search (should detect ahmia/darksearch)",
    ),
    QueryTest(
        query="bitcoin price prediction ethereum crypto",
        expected_types={"finance"},
        description="Cryptocurrency/finance (should detect binance/investing)",
    ),
    QueryTest(
        query="latest breaking news technology 2026",
        expected_types={"news"},
        description="News search (should detect newsapi provider)",
    ),
    QueryTest(
        query="Python FastAPI web framework tutorial",
        expected_types={"code"},
        description="Code search (should detect github provider)",
    ),
]


async def run_deep_research(
    query: str,
    depth: int = 1,
    expand_queries: bool = False,
    extract: bool = False,
    synthesize: bool = False,
) -> dict[str, Any]:
    """Run research_deep with specified parameters.

    Args:
        query: Search query string
        depth: Result volume control (1-10)
        expand_queries: Enable LLM query expansion
        extract: Enable LLM content extraction
        synthesize: Enable LLM answer synthesis

    Returns:
        Full response dict from research_deep
    """
    from loom.tools.deep import research_deep

    return await research_deep(  # type: ignore[no-any-return]
        query=query,
        depth=depth,
        expand_queries=expand_queries,
        extract=extract,
        synthesize=synthesize,
        include_github=True,
        include_community=False,
        include_red_team=False,
        include_misinfo_check=False,
        max_cost_usd=0.10,
    )


def create_mock_response(
    query: str,
    expected_types: set[str],
) -> dict[str, Any]:
    """Create a realistic mocked response for a query.

    Args:
        query: Query string
        expected_types: Expected query types detected

    Returns:
        Realistic mock response structure
    """
    # Map query types to providers
    provider_map = {
        "academic": ["arxiv", "exa"],
        "darkweb": ["ahmia", "darksearch", "ddgs"],
        "finance": ["binance", "investing", "exa"],
        "news": ["newsapi", "ddgs"],
        "code": ["github", "exa"],
    }

    providers = []
    for qtype in expected_types:
        providers.extend(provider_map.get(qtype, []))

    return {
        "query": query,
        "search_variations": [query],
        "providers_used": list(set(providers)),
        "pages_searched": 15 + len(expected_types) * 5,
        "pages_fetched": 3 + len(expected_types),
        "top_pages": [
            {
                "url": f"https://example.com/{i}",
                "title": f"Result {i} for {query}",
                "snippet": f"This is a sample result for query: {query}",
                "markdown": "# Sample Content\n\nThis is mock content.",
                "score": 0.9 - (i * 0.1),
                "fetch_tool": "http",
            }
            for i in range(3)
        ],
        "synthesis": None,
        "github_repos": (
            [
                {
                    "name": "user/fastapi",
                    "description": "Mock FastAPI repository",
                    "url": "https://github.com/user/fastapi",
                }
            ]
            if "code" in expected_types
            else None
        ),
        "language_stats": {"en": 3},
        "community_sentiment": None,
        "red_team_report": None,
        "misinfo_report": None,
        "warnings": [],
        "total_cost_usd": 0.02,
        "elapsed_ms": 1500 + len(expected_types) * 200,
    }


async def mock_deep_research(
    query: str,
    depth: int = 1,
    expand_queries: bool = False,
    extract: bool = False,
    synthesize: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """Mocked version of research_deep for testing without API keys.

    Args:
        query: Search query string
        depth: Result volume control
        expand_queries: Enable LLM query expansion
        extract: Enable LLM content extraction
        synthesize: Enable LLM answer synthesis
        **kwargs: Other arguments (ignored in mock)

    Returns:
        Realistic mock response
    """
    from loom.tools.deep import _detect_query_type

    # Auto-detect types just like real implementation
    detected_types = _detect_query_type(query)

    # Simulate network latency
    await asyncio.sleep(0.5)

    return create_mock_response(query, detected_types)


def print_result_summary(
    result: dict[str, Any],
    test_case: QueryTest,
    query_index: int,
) -> tuple[bool, dict[str, int]]:
    """Print formatted summary of a single query result.

    Args:
        result: Response dict from research_deep
        test_case: Test metadata
        query_index: 1-based query number

    Returns:
        Tuple of (success: bool, stats: dict)
    """
    from loom.tools.deep import _detect_query_type

    detected_types = _detect_query_type(test_case.query)
    providers = result.get("providers_used", [])
    pages_searched = result.get("pages_searched", 0)
    pages_fetched = result.get("pages_fetched", 0)
    warnings = result.get("warnings", [])
    cost = result.get("total_cost_usd", 0.0)
    elapsed = result.get("elapsed_ms", 0)
    error = result.get("error")

    success = not error and pages_fetched > 0

    # Type detection verification
    type_match = detected_types == test_case.expected_types or not test_case.expected_types
    type_status = "✓" if type_match else "✗"

    print(f"\n{'=' * 80}")
    print(f"Query {query_index}: {test_case.query}")
    print(f"{'=' * 80}")
    print(f"\nDescription: {test_case.description}")
    print(f"\nDetected Types:      {', '.join(detected_types) or '(none)'} {type_status}")
    print(f"Expected Types:      {', '.join(test_case.expected_types) or '(general)'}")
    print(f"Providers Used:      {', '.join(providers) or '(none)'}")
    print(f"Pages Searched:      {pages_searched}")
    print(f"Pages Fetched:       {pages_fetched}")
    print(f"Total Cost:          ${cost:.4f}")
    print(f"Elapsed Time:        {elapsed}ms")

    if warnings:
        print(f"\nWarnings: ({len(warnings)})")
        for w in warnings:
            stage = w.get("stage", "unknown")
            error_msg = w.get("error", "unknown error")
            print(f"  - [{stage}] {error_msg}")

    if error:
        print(f"\nError: {error}")

    stats = {
        "pages_searched": pages_searched,
        "pages_fetched": pages_fetched,
        "warnings": len(warnings),
        "cost_usd_cents": int(cost * 100),
        "elapsed_ms": elapsed,
    }

    return success, stats


async def run_stress_test(use_mock: bool = False, verbose: bool = False) -> int:
    """Run all stress tests and report results.

    Args:
        use_mock: If True, use mocked search results
        verbose: If True, print detailed output

    Returns:
        Exit code (0 for success, 1 for failures)
    """
    logger.info(f"Starting stress test (mode={'MOCK' if use_mock else 'LIVE'})")

    if use_mock:
        logger.info("Using mocked search results (no API keys required)")
        # Replace research_deep with mock version
        mock_patch = patch(
            "loom.tools.deep.research_deep",
            side_effect=mock_deep_research,
        )
        mock_patch.start()

    # Run tests
    results = []
    total_cost = 0.0
    total_pages = 0
    failed_count = 0

    for i, test_case in enumerate(TEST_QUERIES, 1):
        try:
            logger.info(f"[{i}/{len(TEST_QUERIES)}] Running: {test_case.query}")

            result = await run_deep_research(
                query=test_case.query,
                depth=1,
                expand_queries=False,
                extract=False,
                synthesize=False,
            )

            success, stats = print_result_summary(result, test_case, i)

            if verbose:
                print("\nFull Response:")
                # Truncate markdown in output
                display_result = {**result}
                for page in display_result.get("top_pages", []):
                    if "markdown" in page:
                        page["markdown"] = page["markdown"][:200] + "…"
                print(json.dumps(display_result, indent=2, default=str))

            results.append((test_case.query, success, stats))
            total_cost += stats["cost_usd_cents"] / 100
            total_pages += stats["pages_fetched"]

            if not success:
                failed_count += 1

        except Exception as exc:
            logger.error(f"Exception in query {i}: {exc}", exc_info=verbose)
            results.append((test_case.query, False, {}))
            failed_count += 1

    # Print summary
    print(f"\n\n{'=' * 80}")
    print("STRESS TEST SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total Queries:       {len(TEST_QUERIES)}")
    print(f"Successful:          {len(TEST_QUERIES) - failed_count}")
    print(f"Failed:              {failed_count}")
    print(f"Total Pages Fetched: {total_pages}")
    print(f"Total Cost:          ${total_cost:.4f}")

    if failed_count == 0:
        print("\nStatus: ✓ All tests passed")
        return 0
    else:
        print(f"\nStatus: ✗ {failed_count} test(s) failed")
        return 1


def main() -> int:
    """Entry point for stress test script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Stress test the deep research pipeline with 5 query types"
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mocked search results (no API keys required)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed output including full responses",
    )

    args = parser.parse_args()

    try:
        exit_code = asyncio.run(run_stress_test(use_mock=args.mock, verbose=args.verbose))
        return exit_code
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 130
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
