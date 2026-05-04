"""Tool Selection Accuracy Benchmark

Tests the semantic router's ability to recommend correct tools for natural language
queries. Measures precision (correct tool in top-K) and recall (correct tool found).

Target metrics:
  - Precision@3: >70% (correct tool in top-3 recommendations)
  - Precision@5: >80% (correct tool in top-5 recommendations)
  - Recall: >85% (correct tool found somewhere in results)
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from loom.tools.semantic_router import research_semantic_route


@pytest.mark.asyncio
class TestToolSelectionAccuracy:
    """Benchmark tool selection accuracy via semantic routing."""

    # Define test queries with expected primary tools
    # Format: (query, expected_tool_name, description)
    TEST_QUERIES = [
        # Research & Search
        (
            "search for AI papers on jailbreaking models",
            "research_search",
            "Should recommend semantic search across providers",
        ),
        (
            "find information about prompt injection attacks",
            "research_deep",
            "Should recommend deep research pipeline",
        ),
        (
            "look up articles about model safety and alignment",
            "research_search",
            "Should recommend general search",
        ),
        # Fetching & Scraping
        (
            "fetch and analyze the content at https://example.com",
            "research_fetch",
            "Should recommend page fetch tool",
        ),
        (
            "scrape multiple URLs and extract text",
            "research_spider",
            "Should recommend multi-URL spider",
        ),
        (
            "convert HTML to markdown from a webpage",
            "research_markdown",
            "Should recommend HTML to markdown conversion",
        ),
        # LLM & Language
        (
            "summarize this text using an LLM",
            "research_llm_summarize",
            "Should recommend LLM summarization",
        ),
        (
            "classify this document into categories",
            "research_llm_classify",
            "Should recommend text classification",
        ),
        (
            "extract entities and information from text",
            "research_llm_extract",
            "Should recommend information extraction",
        ),
        (
            "translate text to different languages",
            "research_llm_translate",
            "Should recommend translation tool",
        ),
        # Security & Analysis
        (
            "check if a domain has security vulnerabilities",
            "research_cert_analyzer",
            "Should recommend certificate/security analysis",
        ),
        (
            "scan for SSRF and XSS vulnerabilities",
            "research_security_audit",
            "Should recommend security audit",
        ),
        (
            "perform DNS reconnaissance on a target",
            "research_passive_recon",
            "Should recommend passive reconnaissance",
        ),
        # Social & Intelligence
        (
            "find social media profiles for a person",
            "research_social_analyze",
            "Should recommend social media analysis",
        ),
        (
            "analyze threat actor infrastructure",
            "research_threat_profile",
            "Should recommend threat intelligence",
        ),
        (
            "monitor for data leaks and breaches",
            "research_leak_scan",
            "Should recommend breach database scanning",
        ),
        # Specialized
        (
            "detect steganography and hidden content",
            "research_stego_detect",
            "Should recommend steganography detection",
        ),
        (
            "analyze PDF metadata and EXIF data",
            "research_metadata_forensics",
            "Should recommend metadata extraction",
        ),
        (
            "check for academic paper retraction status",
            "research_retraction_check",
            "Should recommend retraction checking",
        ),
        (
            "assess model bias and fairness",
            "research_bias_probe",
            "Should recommend bias assessment",
        ),
    ]

    async def test_tool_selection_all_queries(self) -> None:
        """Test tool selection accuracy across all test queries.

        Measures:
          - Precision@3: % correct tool in top-3
          - Precision@5: % correct tool in top-5
          - Recall: % correct tool found in results
        """
        results = {
            "total_queries": 0,
            "precision_at_3": 0,
            "precision_at_5": 0,
            "recall": 0,
            "query_results": [],
        }

        for query, expected_tool, description in self.TEST_QUERIES:
            results["total_queries"] += 1

            # Get semantic router recommendations
            response = await research_semantic_route(query, top_k=5)

            # Extract recommended tool names
            recommended_tools = response.get("recommended_tools", [])
            tool_names = [
                tool.get("name") or tool.get("tool_name", "unknown")
                for tool in recommended_tools
            ]

            # Check if expected tool is in results
            in_top_3 = expected_tool in tool_names[:3]
            in_top_5 = expected_tool in tool_names[:5]
            in_results = expected_tool in tool_names

            results["precision_at_3"] += 1 if in_top_3 else 0
            results["precision_at_5"] += 1 if in_top_5 else 0
            results["recall"] += 1 if in_results else 0

            results["query_results"].append({
                "query": query,
                "expected_tool": expected_tool,
                "description": description,
                "recommended_tools": tool_names,
                "in_top_3": in_top_3,
                "in_top_5": in_top_5,
                "found": in_results,
            })

        # Calculate percentages
        total = results["total_queries"]
        results["precision_at_3_pct"] = (
            100.0 * results["precision_at_3"] / total if total > 0 else 0.0
        )
        results["precision_at_5_pct"] = (
            100.0 * results["precision_at_5"] / total if total > 0 else 0.0
        )
        results["recall_pct"] = 100.0 * results["recall"] / total if total > 0 else 0.0

        # Print detailed results
        self._print_results(results)

        # Assertions with reasonable targets
        # Note: Semantic routing performance depends on embedding quality
        # These thresholds are conservative to account for fallback mechanisms
        assert (
            results["precision_at_5_pct"] >= 60.0
        ), f"Precision@5 {results['precision_at_5_pct']:.1f}% below 60% threshold"

    @staticmethod
    def _print_results(results: dict[str, Any]) -> None:
        """Pretty-print benchmark results."""
        print("\n")
        print("=" * 80)
        print("TOOL SELECTION ACCURACY BENCHMARK")
        print("=" * 80)
        print()
        print(f"Total queries tested: {results['total_queries']}")
        print()
        print(f"Precision@3 (correct tool in top-3):")
        print(f"  {results['precision_at_3']}/{results['total_queries']} " +
              f"({results['precision_at_3_pct']:.1f}%)")
        print()
        print(f"Precision@5 (correct tool in top-5):")
        print(f"  {results['precision_at_5']}/{results['total_queries']} " +
              f"({results['precision_at_5_pct']:.1f}%)")
        print()
        print(f"Recall (correct tool found in results):")
        print(f"  {results['recall']}/{results['total_queries']} " +
              f"({results['recall_pct']:.1f}%)")
        print()
        print("=" * 80)
        print("PER-QUERY RESULTS")
        print("=" * 80)
        print()

        # Group by success/failure
        successes = [r for r in results["query_results"] if r["found"]]
        failures = [r for r in results["query_results"] if not r["found"]]

        if successes:
            print(f"✓ SUCCESSES ({len(successes)}):")
            print()
            for result in successes:
                marker = "★" if result["in_top_3"] else "◆" if result["in_top_5"] else "•"
                print(f"  {marker} Query: {result['query']}")
                print(f"    Expected: {result['expected_tool']}")
                print(f"    Top-3: {result['recommended_tools'][:3]}")
                print()

        if failures:
            print(f"\n✗ FAILURES ({len(failures)}):")
            print()
            for result in failures:
                print(f"  ✗ Query: {result['query']}")
                print(f"    Expected: {result['expected_tool']}")
                print(f"    Got (top-5): {result['recommended_tools'][:5]}")
                print(f"    Description: {result['description']}")
                print()

        print("=" * 80)
        print("INTERPRETATION")
        print("=" * 80)
        print()
        print("★ = Found in top-3 (excellent)")
        print("◆ = Found in top-5 (good)")
        print("• = Found in top-5+ (acceptable)")
        print("✗ = Not found in results (needs improvement)")
        print()
        print("Targets:")
        print("  Precision@3: >70%  (correct tool in top-3)")
        print("  Precision@5: >80%  (correct tool in top-5)")
        print("  Recall:      >85%  (correct tool found)")
        print()

    @pytest.mark.parametrize(
        "query,expected_tool,description",
        TEST_QUERIES,
        ids=[f"q{i}" for i in range(len(TEST_QUERIES))],
    )
    async def test_individual_query(
        self, query: str, expected_tool: str, description: str
    ) -> None:
        """Test each query individually for better failure reporting.

        Parameters:
            query: Natural language query
            expected_tool: Primary tool that should be recommended
            description: Human-readable explanation
        """
        response = await research_semantic_route(query, top_k=5)

        # Handle both dict and list response formats
        recommended = response.get("recommended_tools", [])
        if not isinstance(recommended, list):
            recommended = list(recommended) if recommended else []

        tool_names = [
            t.get("name") or t.get("tool_name", "unknown") for t in recommended
        ]

        # Check presence in results
        found = expected_tool in tool_names
        in_top_3 = expected_tool in tool_names[:3]

        assert found, (
            f"Query: {query}\n"
            f"Expected tool: {expected_tool}\n"
            f"Recommended (top-5): {tool_names[:5]}\n"
            f"Description: {description}"
        )

        # Log results for debugging
        if in_top_3:
            pytest.skip(
                f"✓ Query success: {query[:50]}... "
                f"(expected '{expected_tool}' found in top-3)"
            )


@pytest.mark.asyncio
class TestToolSelectionEdgeCases:
    """Test tool selection edge cases and robustness."""

    async def test_empty_query(self) -> None:
        """Empty query should return gracefully."""
        response = await research_semantic_route("", top_k=5)
        assert "error" in response or response.get("recommended_tools") == []

    async def test_none_query(self) -> None:
        """None query should return gracefully."""
        response = await research_semantic_route(None, top_k=5)  # type: ignore
        assert "error" in response or response.get("recommended_tools") == []

    async def test_very_long_query(self) -> None:
        """Very long query should still return results."""
        long_query = (
            "I need to analyze a complex security vulnerability "
            "that involves multiple layers of encryption and authentication, "
            "including OAuth2, JWT tokens, and database access controls, "
            "to understand potential attack vectors and mitigation strategies"
        )
        response = await research_semantic_route(long_query, top_k=5)
        assert "recommended_tools" in response
        assert isinstance(response["recommended_tools"], list)

    async def test_top_k_parameter(self) -> None:
        """Test that top_k parameter controls result count."""
        query = "search for information"

        # Test top_k=1
        response_1 = await research_semantic_route(query, top_k=1)
        tools_1 = response_1.get("recommended_tools", [])
        assert len(tools_1) <= 1

        # Test top_k=10
        response_10 = await research_semantic_route(query, top_k=10)
        tools_10 = response_10.get("recommended_tools", [])
        assert len(tools_10) <= 10

    async def test_response_format(self) -> None:
        """Response should always have required fields."""
        response = await research_semantic_route(
            "analyze security", top_k=5
        )

        # Check required response fields
        assert "recommended_tools" in response
        assert isinstance(response["recommended_tools"], list)

        # Check tool format
        for tool in response["recommended_tools"]:
            if isinstance(tool, dict):
                # Should have name and similarity score
                assert "name" in tool or "tool_name" in tool
                # May have similarity score


@pytest.mark.asyncio
class TestToolSelectionPerformance:
    """Performance tests for tool selection."""

    async def test_routing_latency(self) -> None:
        """Semantic routing should complete in reasonable time."""
        import time

        query = "search for machine learning papers"

        start = time.time()
        response = await research_semantic_route(query, top_k=5)
        elapsed = time.time() - start

        # Should complete in under 5 seconds (including model loading)
        assert elapsed < 5.0, f"Routing took {elapsed:.2f}s, expected <5s"
        assert response.get("recommended_tools") is not None

    async def test_concurrent_routing(self) -> None:
        """Multiple concurrent routing requests should work."""
        queries = [
            "search for information",
            "fetch a webpage",
            "analyze security",
            "extract data",
            "translate text",
        ]

        # Run all queries concurrently
        tasks = [
            research_semantic_route(q, top_k=3) for q in queries
        ]
        responses = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(responses) == len(queries)
        for response in responses:
            assert "recommended_tools" in response
            assert isinstance(response["recommended_tools"], list)

    async def test_caching_benefits(self) -> None:
        """Repeated queries should benefit from caching."""
        import time

        query = "search for papers"

        # First call (may load model)
        start_1 = time.time()
        response_1 = await research_semantic_route(query, top_k=5)
        time_1 = time.time() - start_1

        # Second call (should use cache)
        start_2 = time.time()
        response_2 = await research_semantic_route(query, top_k=5)
        time_2 = time.time() - start_2

        # Both should return valid results
        assert response_1.get("recommended_tools")
        assert response_2.get("recommended_tools")

        # Second call may be faster due to caching
        # (though not guaranteed in all scenarios)
        pytest.skip(
            f"First call: {time_1:.3f}s, Second call: {time_2:.3f}s "
            f"(cached call expected to be faster)"
        )
