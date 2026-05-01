#!/usr/bin/env python3
"""
Research 702: Real-Time Model Behavior Monitoring & Jailbreak Detection
Uses Loom CLI which connects to the MCP server via streamable-HTTP
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def call_loom_search(query: str, num_results: int = 15) -> dict[str, Any]:
    """
    Call loom search command via CLI.

    Args:
        query: search query string
        num_results: number of results to return

    Returns:
        Search results dictionary
    """

    cmd = [
        "loom",
        "search",
        query,
        "--num-results", str(num_results),
        "--json"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=45,
            cwd="/opt/research-toolbox"
        )

        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    "status": "parse_error",
                    "raw_output": result.stdout[:500]
                }
        else:
            return {
                "status": "error",
                "error": result.stderr[:500],
                "return_code": result.returncode
            }

    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "exception", "error": str(e)}


def call_loom_deep(query: str) -> dict[str, Any]:
    """
    Call loom deep research command via CLI.

    Args:
        query: research query string

    Returns:
        Deep research results dictionary
    """

    cmd = [
        "loom",
        "deep",
        query,
        "--json"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/opt/research-toolbox"
        )

        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {
                    "status": "parse_error",
                    "raw_output": result.stdout[:500]
                }
        else:
            return {
                "status": "error",
                "error": result.stderr[:500],
                "return_code": result.returncode
            }

    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "exception", "error": str(e)}


def run_research() -> dict[str, Any]:
    """
    Execute comprehensive multi-query research on real-time monitoring.
    """

    research_results = {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "research_id": "research_702_monitoring",
            "method": "loom_cli_search_and_deep",
            "topics": [
                "real-time jailbreak detection production LLM 2025 2026",
                "AI safety monitoring production deployment",
                "anomaly detection LLM output production guardrails"
            ],
            "objectives": [
                "Real-time output monitoring techniques",
                "Streaming safety classifiers (low-latency inference)",
                "Anomaly detection on model outputs (distribution shift, entropy spikes)",
                "Production guardrail architectures (input/output filtering, circuit breakers)",
                "Alerting systems for detected jailbreaks",
                "Integration with Loom dashboard and metrics modules"
            ]
        },
        "searches": {},
        "deep_research": {}
    }

    # Standard search queries
    search_queries = [
        ("real-time jailbreak detection production LLM 2025 2026", "Production jailbreak detection (2025-2026)"),
        ("AI safety monitoring production deployment guardrails", "Production safety monitoring and guardrails"),
        ("anomaly detection LLM output streaming inference distribution shift", "Anomaly detection in LLM outputs"),
        ("real-time safety classifier low-latency inference production", "Real-time safety classifiers"),
        ("production LLM monitoring circuit breaker input output filtering", "Production guardrail architectures"),
        ("jailbreak detection alerting system production deployment 2025", "Jailbreak alerting systems"),
        ("model behavior drift detection entropy spike output monitoring", "Model drift and anomaly detection"),
        ("semantic anomaly detection language model outputs production", "Semantic anomaly detection"),
    ]

    # Deep research queries (subset of most important ones)
    deep_queries = [
        "real-time jailbreak detection production LLM 2025 2026",
        "anomaly detection LLM output streaming inference production",
        "production guardrail architecture input output filtering circuit breaker"
    ]

    print("[*] Starting Loom CLI research...")
    print(f"[*] Research ID: research_702_monitoring")
    print(f"[*] Timestamp: {research_results['metadata']['timestamp']}")
    print(f"[*] Total search queries: {len(search_queries)}")
    print(f"[*] Deep research queries: {len(deep_queries)}\n")

    # Execute standard searches
    print("[PHASE 1] Standard Multi-Provider Searches")
    print("=" * 70)

    for i, (query, description) in enumerate(search_queries, 1):
        print(f"[{i:2d}/{len(search_queries)}] {description}")
        print(f"        Query: {query}")

        result = call_loom_search(query, num_results=15)

        if result.get("status") == "error":
            print(f"        ✗ Error: {result.get('error', 'Unknown')}\n")
        elif result.get("status") == "timeout":
            print(f"        ⏱ Timeout\n")
        elif result.get("status") == "exception":
            print(f"        ✗ Exception: {result.get('error', 'Unknown')}\n")
        elif result.get("status") == "parse_error":
            print(f"        ⚠ Parse error (server responded)\n")
        else:
            # Count results
            if isinstance(result, list):
                result_count = len(result)
            elif isinstance(result, dict):
                result_count = len(result.get("results", []))
            else:
                result_count = 1

            print(f"        ✓ {result_count} results\n")

        research_results["searches"][query] = result

    # Execute deep research for critical queries
    print("[PHASE 2] Deep Research on Core Topics")
    print("=" * 70)

    for i, query in enumerate(deep_queries, 1):
        print(f"[{i}/{len(deep_queries)}] Deep: {query}")

        result = call_loom_deep(query)

        if result.get("status") == "error":
            print(f"  ✗ Error: {result.get('error', 'Unknown')}\n")
        elif result.get("status") == "timeout":
            print(f"  ⏱ Timeout\n")
        elif result.get("status") == "exception":
            print(f"  ✗ Exception: {result.get('error', 'Unknown')}\n")
        else:
            # Count results from deep research
            if isinstance(result, list):
                result_count = len(result)
            elif isinstance(result, dict):
                result_count = len(result.get("results", []))
            else:
                result_count = 1

            print(f"  ✓ Deep research completed ({result_count} results)\n")

        research_results["deep_research"][query] = result

    print("[*] Research complete.\n")

    return research_results


def main():
    """Main entry point"""

    results = run_research()

    # Ensure output directory exists
    output_dir = Path("/opt/research-toolbox/tmp")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save results
    output_file = output_dir / "research_702_monitoring.json"

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("=" * 70)
    print("RESEARCH 702: REAL-TIME MODEL MONITORING")
    print("=" * 70)
    print(f"[✓] Timestamp: {results['metadata']['timestamp']}")
    print(f"[✓] Results saved to: {output_file}")
    print(f"[✓] File size: {output_file.stat().st_size} bytes")
    print(f"[✓] Search queries: {len(results.get('searches', {}))}")
    print(f"[✓] Deep research: {len(results.get('deep_research', {}))}")

    # Count successful results
    successful_searches = sum(
        1 for r in results.get("searches", {}).values()
        if not r.get("status") or r.get("status") not in ["error", "timeout"]
    )
    print(f"[✓] Successful searches: {successful_searches}")

    successful_deep = sum(
        1 for r in results.get("deep_research", {}).values()
        if not r.get("status") or r.get("status") not in ["error", "timeout"]
    )
    print(f"[✓] Successful deep research: {successful_deep}")

    print("=" * 70)
    print("\nKey areas covered in research:")
    print("  - Real-time jailbreak detection techniques")
    print("  - Production AI safety monitoring systems")
    print("  - Anomaly detection methods for LLM outputs")
    print("  - Streaming safety classifiers with low latency")
    print("  - Production guardrail architectures")
    print("  - Alerting and response systems")
    print("  - Model drift detection and monitoring")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
