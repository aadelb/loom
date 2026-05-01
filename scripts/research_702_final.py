#!/usr/bin/env python3
"""
Research 702: Real-Time Model Behavior Monitoring & Jailbreak Detection
Uses proper HTTP headers for Loom MCP server on Hetzner
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def call_mcp_tool_http(tool_name: str, query: str, num_results: int = 15) -> dict[str, Any]:
    """
    Call MCP tool via curl with proper headers.

    Args:
        tool_name: name of the MCP tool
        query: search query
        num_results: number of results

    Returns:
        Tool result
    """
    # Build MCP JSON-RPC request
    request_body = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": {
                "query": query,
                "num_results": num_results
            }
        },
        "id": 1
    }

    cmd = [
        "curl",
        "-s",
        "-X", "POST",
        "http://127.0.0.1:8787/mcp",
        "-H", "Content-Type: application/json",
        "-H", "Accept: application/json, text/event-stream",
        "-d", json.dumps(request_body)
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/opt/research-toolbox"
        )

        if result.returncode == 0 and result.stdout:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                return {"status": "parse_error", "raw": result.stdout[:1000]}
        else:
            return {
                "status": "error",
                "return_code": result.returncode,
                "stderr": result.stderr[:500] if result.stderr else "Unknown error"
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
            "method": "http_mcp_proper_headers",
            "server": "http://127.0.0.1:8787/mcp",
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
        "searches": {}
    }

    # Standard search queries
    search_queries = [
        ("real-time jailbreak detection production LLM 2025 2026", "Production jailbreak detection (2025-2026)"),
        ("AI safety monitoring production deployment guardrails", "Production safety monitoring"),
        ("anomaly detection LLM output streaming inference distribution shift", "Anomaly detection in outputs"),
        ("real-time safety classifier low-latency inference production", "Real-time safety classifiers"),
        ("production LLM monitoring circuit breaker input output filtering", "Production guardrail architectures"),
        ("jailbreak detection alerting system production deployment 2025", "Jailbreak alerting systems"),
        ("model behavior drift detection entropy spike output monitoring", "Model drift detection"),
        ("semantic anomaly detection language model outputs production", "Semantic anomaly detection"),
    ]

    print("[*] Starting Loom MCP research with proper HTTP headers...")
    print(f"[*] Research ID: research_702_monitoring")
    print(f"[*] Server: http://127.0.0.1:8787/mcp")
    print(f"[*] Timestamp: {research_results['metadata']['timestamp']}")
    print(f"[*] Total queries: {len(search_queries)}\n")

    print("[PHASE 1] Multi-Provider Searches")
    print("=" * 70 + "\n")

    successful = 0
    for i, (query, description) in enumerate(search_queries, 1):
        print(f"[{i:2d}/{len(search_queries)}] {description}")

        result = call_mcp_tool_http("research_search", query, num_results=15)

        # Check if we got valid results
        if isinstance(result, dict):
            if "error" in result and "message" in result["error"]:
                print(f"        ✗ Server error: {result['error']['message']}\n")
            elif result.get("status") in ["timeout", "exception", "error", "parse_error"]:
                print(f"        ✗ {result.get('status', 'unknown')}\n")
            else:
                # We got a result, check its structure
                if "result" in result:
                    res_data = result["result"]
                    if isinstance(res_data, dict) and "content" in res_data:
                        print(f"        ✓ Results received from MCP server\n")
                        successful += 1
                    else:
                        print(f"        ✓ Results received\n")
                        successful += 1
                else:
                    print(f"        ✓ Response received\n")
                    successful += 1
        else:
            print(f"        ✓ Response received\n")
            successful += 1

        research_results["searches"][query] = result

    print(f"[*] Completed {successful}/{len(search_queries)} successful queries\n")

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
    print(f"[✓] Queries executed: {len(results.get('searches', {}))}")

    # Count successful results
    successful = sum(
        1 for r in results.get("searches", {}).values()
        if isinstance(r, dict) and "result" in r and not "error" in r
        or isinstance(r, dict) and "error" not in r and "status" not in r
    )
    print(f"[✓] Successful queries: {successful}/{len(results.get('searches', {}))}")

    print("=" * 70)
    print("\nResearch Focus Areas:")
    print("  1. Real-time jailbreak detection in production systems")
    print("  2. AI safety monitoring and deployment guardrails")
    print("  3. Anomaly detection for LLM outputs")
    print("  4. Streaming safety classifiers (low-latency)")
    print("  5. Production guardrail architectures (input/output filtering)")
    print("  6. Circuit breaker patterns for safety")
    print("  7. Alerting systems for jailbreak detection")
    print("  8. Model drift and entropy-based anomaly detection")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
