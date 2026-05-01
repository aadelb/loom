#!/usr/bin/env python3
"""
Research 702: Real-Time Model Behavior Monitoring & Jailbreak Detection
Deployed on Hetzner research-toolbox for comprehensive multi-provider search
"""

import json
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.loom.providers.exa import search_exa
from src.loom.providers.tavily import search_tavily
from src.loom.providers.brave import search_brave
from src.loom.providers.ddgs import search_ddgs
from src.loom.providers.arxiv_search import search_arxiv
from src.loom.tools.deep import research_deep
from src.loom.tools.search import research_search
from src.loom.cache import get_cache
from src.loom.config import load_config


async def run_research() -> dict[str, Any]:
    """
    Execute comprehensive multi-provider research on real-time jailbreak detection.

    Returns:
        Dictionary containing all research results organized by topic and provider
    """

    # Load configuration
    load_config()

    research_results = {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "research_id": "research_702_monitoring",
            "topics": [
                "real-time jailbreak detection production LLM 2025 2026",
                "AI safety monitoring production deployment",
                "anomaly detection LLM output production guardrails"
            ],
            "objectives": [
                "Real-time output monitoring techniques",
                "Streaming safety classifiers (low-latency inference)",
                "Anomaly detection on model outputs",
                "Production guardrail architectures",
                "Alerting systems for detected jailbreaks",
                "Integration with Loom dashboard and metrics"
            ]
        },
        "searches": {}
    }

    search_queries = [
        {
            "query": "real-time jailbreak detection production LLM 2025 2026",
            "description": "Production jailbreak detection systems (2025-2026)"
        },
        {
            "query": "AI safety monitoring production deployment guardrails",
            "description": "Production AI safety monitoring and guardrails"
        },
        {
            "query": "anomaly detection LLM output streaming inference distribution shift",
            "description": "Anomaly detection techniques for LLM outputs"
        },
        {
            "query": "real-time safety classifier low-latency inference production",
            "description": "Real-time safety classifiers with low-latency requirements"
        },
        {
            "query": "production LLM monitoring circuit breaker input output filtering",
            "description": "Production guardrail architectures and circuit breakers"
        },
        {
            "query": "jailbreak detection alerting system production deployment 2025",
            "description": "Alerting systems for jailbreak detection in production"
        },
        {
            "query": "model behavior drift detection entropy spike output monitoring",
            "description": "Model behavior drift and entropy-based anomaly detection"
        },
        {
            "query": "semantic anomaly detection language model outputs production",
            "description": "Semantic anomaly detection for LLM outputs"
        }
    ]

    print("[*] Starting comprehensive multi-provider research...")
    print(f"[*] Research ID: research_702_monitoring")
    print(f"[*] Timestamp: {research_results['metadata']['timestamp']}")
    print(f"[*] Total queries: {len(search_queries)}\n")

    # Run searches in parallel where possible
    for i, search_item in enumerate(search_queries, 1):
        query = search_item["query"]
        description = search_item["description"]

        print(f"[{i}/{len(search_queries)}] {description}")
        print(f"    Query: {query}")

        query_results = {
            "description": description,
            "query": query,
            "providers": {}
        }

        # Try multiple providers in sequence (with timeout protection)
        providers_to_try = [
            ("exa", search_exa),
            ("tavily", search_tavily),
            ("ddgs", search_ddgs),
            ("arxiv", search_arxiv),
            ("brave", search_brave),
        ]

        for provider_name, provider_func in providers_to_try:
            try:
                print(f"      [{provider_name}]", end=" ", flush=True)

                # Call provider with timeout
                try:
                    result = await asyncio.wait_for(
                        provider_func(query, num_results=10),
                        timeout=30.0
                    )

                    if result:
                        query_results["providers"][provider_name] = {
                            "status": "success",
                            "result_count": len(result) if isinstance(result, list) else 1,
                            "results": result[:5]  # Store top 5 results per provider
                        }
                        print(f"✓ ({len(result) if isinstance(result, list) else 1} results)")
                    else:
                        query_results["providers"][provider_name] = {
                            "status": "no_results",
                            "result_count": 0
                        }
                        print("(no results)")

                except asyncio.TimeoutError:
                    query_results["providers"][provider_name] = {
                        "status": "timeout",
                        "error": "Request timed out after 30 seconds"
                    }
                    print("⏱ (timeout)")
                except Exception as e:
                    query_results["providers"][provider_name] = {
                        "status": "error",
                        "error": str(e)
                    }
                    print(f"✗ ({type(e).__name__})")

            except Exception as outer_e:
                query_results["providers"][provider_name] = {
                    "status": "error",
                    "error": str(outer_e)
                }
                print(f"✗ ({type(outer_e).__name__})")

        research_results["searches"][query] = query_results
        print()

    # Add deep research for most important queries
    print("[*] Running deep research on core topics...")
    core_queries = [
        "real-time jailbreak detection production LLM 2025 2026",
        "anomaly detection LLM output streaming inference production"
    ]

    research_results["deep_research"] = {}

    for core_query in core_queries:
        print(f"    [deep] {core_query}")
        try:
            deep_result = await asyncio.wait_for(
                research_deep(core_query),
                timeout=60.0
            )
            if deep_result:
                research_results["deep_research"][core_query] = {
                    "status": "success",
                    "result": deep_result[:3]  # Top 3 results from deep search
                }
                print(f"    ✓ Deep research completed")
        except Exception as e:
            research_results["deep_research"][core_query] = {
                "status": "error",
                "error": str(e)
            }
            print(f"    ✗ Deep research failed: {type(e).__name__}")

    print("\n[*] Research complete. Aggregating and saving results...\n")

    return research_results


async def main():
    """Main entry point"""

    # Run research
    results = await run_research()

    # Ensure output directory exists
    output_dir = Path("/opt/research-toolbox/tmp")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save results
    output_file = output_dir / "research_702_monitoring.json"

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"[✓] Results saved to: {output_file}")
    print(f"[✓] File size: {output_file.stat().st_size} bytes")

    # Print summary
    print("\n" + "="*70)
    print("RESEARCH 702: REAL-TIME MODEL MONITORING SUMMARY")
    print("="*70)
    print(f"Timestamp: {results['metadata']['timestamp']}")
    print(f"Topics researched: {len(results['metadata']['topics'])}")
    print(f"Queries executed: {len(results['searches'])}")
    print(f"Deep research queries: {len(results.get('deep_research', {}))}")

    total_results = 0
    for query, query_data in results["searches"].items():
        for provider, provider_data in query_data.get("providers", {}).items():
            if provider_data.get("status") == "success":
                total_results += provider_data.get("result_count", 0)

    print(f"Total results aggregated: {total_results}")
    print("="*70)

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
