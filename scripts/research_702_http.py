#!/usr/bin/env python3
"""
Research 702: Real-Time Model Behavior Monitoring & Jailbreak Detection
Uses HTTP direct requests to Loom MCP server running on Hetzner
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote


def curl_mcp_tool(tool_name: str, params: dict[str, Any]) -> Any:
    """
    Call MCP tool via curl request to server's /tools endpoint.

    Args:
        tool_name: name of the MCP tool
        params: tool parameters dict

    Returns:
        Tool result or error dict
    """
    # Build the JSON payload
    payload = json.dumps(params)

    # Use curl to POST to the MCP endpoint
    cmd = [
        "curl",
        "-s",
        "-X", "POST",
        "http://127.0.0.1:8787/mcp",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": params
            },
            "id": 1
        })
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=45,
            cwd="/opt/research-toolbox"
        )

        if result.returncode == 0 and result.stdout:
            try:
                response = json.loads(result.stdout)
                if "result" in response:
                    return response["result"]
                return response
            except json.JSONDecodeError:
                return {"status": "parse_error", "output": result.stdout[:500]}
        else:
            return {
                "status": "http_error",
                "return_code": result.returncode,
                "stderr": result.stderr[:500] if result.stderr else None
            }

    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "exception", "error": str(e)}


def research_search_simple(query: str) -> dict[str, Any]:
    """
    Call research_search using HTTP request.

    Args:
        query: search query

    Returns:
        Search results
    """
    # Use simpler approach: just call the tool with query parameter
    cmd = [
        "curl",
        "-s",
        "-X", "POST",
        "http://127.0.0.1:8787/mcp",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "research_search",
                "arguments": {
                    "query": query,
                    "num_results": 15
                }
            },
            "id": 1
        })
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=45,
            cwd="/opt/research-toolbox"
        )

        if result.returncode == 0 and result.stdout:
            try:
                response = json.loads(result.stdout)
                # MCP wraps results in content array with text field
                if "result" in response:
                    result_obj = response["result"]
                    if isinstance(result_obj, dict) and "content" in result_obj:
                        # Extract text from content array
                        if isinstance(result_obj["content"], list) and len(result_obj["content"]) > 0:
                            content = result_obj["content"][0]
                            if "text" in content:
                                try:
                                    return json.loads(content["text"])
                                except:
                                    return {"status": "success", "text": content["text"][:500]}
                    return result_obj
                return response
            except json.JSONDecodeError:
                return {"status": "parse_error", "output": result.stdout[:500]}
        else:
            return {
                "status": "http_error",
                "return_code": result.returncode
            }

    except subprocess.TimeoutExpired:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "exception", "error": str(e)}


def run_research() -> dict[str, Any]:
    """
    Execute comprehensive research using HTTP calls to MCP server.
    """

    research_results = {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "research_id": "research_702_monitoring",
            "method": "http_mcp_direct",
            "server": "http://127.0.0.1:8787",
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
        ("AI safety monitoring production deployment guardrails", "Production safety monitoring and guardrails"),
        ("anomaly detection LLM output streaming inference distribution shift", "Anomaly detection in LLM outputs"),
        ("real-time safety classifier low-latency inference production", "Real-time safety classifiers"),
        ("production LLM monitoring circuit breaker input output filtering", "Production guardrail architectures"),
        ("jailbreak detection alerting system production deployment 2025", "Jailbreak alerting systems"),
        ("model behavior drift detection entropy spike output monitoring", "Model drift and anomaly detection"),
        ("semantic anomaly detection language model outputs production", "Semantic anomaly detection"),
    ]

    print("[*] Starting research via HTTP calls to Loom MCP server...")
    print(f"[*] Research ID: research_702_monitoring")
    print(f"[*] Server: http://127.0.0.1:8787/mcp")
    print(f"[*] Timestamp: {research_results['metadata']['timestamp']}")
    print(f"[*] Total queries: {len(search_queries)}\n")

    # Execute searches
    print("[PHASE 1] Multi-Provider Searches via HTTP")
    print("=" * 70)

    for i, (query, description) in enumerate(search_queries, 1):
        print(f"[{i:2d}/{len(search_queries)}] {description}")
        print(f"        Query: {query}")

        result = research_search_simple(query)

        if isinstance(result, dict):
            status = result.get("status", "unknown")
            if status in ["timeout", "exception", "http_error", "parse_error"]:
                print(f"        ✗ {status}\n")
            else:
                print(f"        ✓ Received response\n")
        else:
            print(f"        ✓ Received response\n")

        research_results["searches"][query] = result

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
    print(f"[✓] Queries executed: {len(results.get('searches', {}))}")

    # Count successful results
    successful = sum(
        1 for r in results.get("searches", {}).values()
        if isinstance(r, dict) and r.get("status") not in ["timeout", "exception", "http_error"]
        or not isinstance(r, dict)
    )
    print(f"[✓] Successful queries: {successful}/{len(results.get('searches', {}))}")

    print("=" * 70)
    print("\nKey research areas:")
    print("  1. Real-time jailbreak detection in production")
    print("  2. AI safety monitoring and guardrails")
    print("  3. Anomaly detection for LLM outputs")
    print("  4. Streaming safety classifiers")
    print("  5. Production monitoring architectures")
    print("  6. Alerting systems for jailbreak detection")
    print("  7. Model drift detection")
    print("  8. Semantic anomaly detection")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
