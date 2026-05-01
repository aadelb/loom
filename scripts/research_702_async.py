#!/usr/bin/env python3
"""
Research 702: Real-Time Model Behavior Monitoring & Jailbreak Detection
Uses direct async MCP client connection
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Try to use Python MCP client directly
try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamablehttp_client
except ImportError:
    print("[!] MCP client not available in this environment")
    print("[*] Falling back to curl-based approach")
    SKIP_MCP = True
else:
    SKIP_MCP = False


async def call_tool_async(
    server_url: str,
    tool_name: str,
    params: dict[str, Any]
) -> dict[str, Any]:
    """
    Call an MCP tool using async client.

    Args:
        server_url: MCP server URL
        tool_name: name of the tool
        params: tool parameters

    Returns:
        Tool result
    """
    if SKIP_MCP:
        return {"status": "mcp_unavailable"}

    try:
        async with (
            streamablehttp_client(server_url, timeout=60) as (read, write, _),
            ClientSession(read, write) as session,
        ):
            # Call the tool
            result = await session.call_tool(tool_name, params)

            # Extract result content
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, "text"):
                    try:
                        return json.loads(content.text)
                    except json.JSONDecodeError:
                        return {"status": "success", "text": content.text[:500]}
                return {"status": "success", "content": str(content)[:500]}
            return {"status": "success"}

    except asyncio.TimeoutError:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def run_research() -> dict[str, Any]:
    """
    Execute comprehensive research using async MCP client.
    """

    research_results = {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "research_id": "research_702_monitoring",
            "method": "async_mcp_client",
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

    print("[*] Starting Loom MCP research with async client...")
    print(f"[*] Research ID: research_702_monitoring")
    print(f"[*] Server: http://127.0.0.1:8787/mcp")
    print(f"[*] Timestamp: {research_results['metadata']['timestamp']}")
    print(f"[*] Total queries: {len(search_queries)}\n")

    print("[PHASE 1] Multi-Provider Searches")
    print("=" * 70 + "\n")

    successful = 0
    server_url = "http://127.0.0.1:8787/mcp"

    # Execute searches concurrently
    tasks = []
    for query, description in search_queries:
        task = call_tool_async(
            server_url,
            "research_search",
            {"query": query, "num_results": 15}
        )
        tasks.append((query, description, task))

    # Process results as they complete
    for query, description, task in tasks:
        result = await task
        print(f"[{len(research_results['searches']) + 1:2d}/{len(search_queries)}] {description}")

        if isinstance(result, dict):
            if result.get("status") == "error":
                print(f"        ✗ {result.get('error', 'Unknown error')}\n")
            elif result.get("status") in ["timeout", "mcp_unavailable"]:
                print(f"        ✗ {result.get('status')}\n")
            else:
                print(f"        ✓ Results received\n")
                successful += 1
        else:
            print(f"        ✓ Results received\n")
            successful += 1

        research_results["searches"][query] = result

    print(f"[*] Completed {successful}/{len(search_queries)} successful queries\n")

    return research_results


def main():
    """Main entry point"""

    # Run async research
    results = asyncio.run(run_research())

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
        if isinstance(r, dict) and r.get("status") == "success"
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
