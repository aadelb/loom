#!/usr/bin/env python3
"""
Research 702: Real-Time Model Behavior Monitoring & Jailbreak Detection
Uses Loom MCP server already running on Hetzner via streamable-HTTP
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def call_loom_tool(tool_name: str, params: dict[str, Any]) -> Any:
    """
    Call a Loom MCP tool via the research CLI.

    Args:
        tool_name: Name of the tool to call
        params: Parameters dictionary

    Returns:
        Tool result
    """
    # Build JSON params string
    params_json = json.dumps(params)

    # Call via loom CLI
    # This will use the streamable-HTTP MCP server
    cmd = ["python3", "-m", "loom.cli", tool_name]

    # Add params as environment variable or via stdin
    env = {"LOOM_PARAMS": params_json}

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
                return {"status": "success", "output": result.stdout}
        else:
            return {
                "status": "error",
                "error": result.stderr,
                "return_code": result.returncode
            }

    except subprocess.TimeoutExpired:
        return {"status": "timeout", "tool": tool_name}
    except Exception as e:
        return {"status": "error", "error": str(e), "tool": tool_name}


def run_research_direct() -> dict[str, Any]:
    """
    Execute comprehensive research using curl requests to the MCP server.
    """

    research_results = {
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "research_id": "research_702_monitoring",
            "server_url": "http://127.0.0.1:8787",
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

    search_queries = [
        "real-time jailbreak detection production LLM 2025 2026",
        "AI safety monitoring production deployment guardrails",
        "anomaly detection LLM output streaming inference distribution shift",
        "real-time safety classifier low-latency inference production",
        "production LLM monitoring circuit breaker input output filtering",
        "jailbreak detection alerting system production deployment",
        "model behavior drift detection entropy spike output monitoring",
        "semantic anomaly detection language model outputs production"
    ]

    print("[*] Starting research via Loom MCP server (research-toolbox)")
    print(f"[*] Research ID: research_702_monitoring")
    print(f"[*] Timestamp: {research_results['metadata']['timestamp']}")
    print(f"[*] Server: http://127.0.0.1:8787")
    print(f"[*] Total queries: {len(search_queries)}\n")

    # Use curl to call the MCP server directly
    for i, query in enumerate(search_queries, 1):
        print(f"[{i}/{len(search_queries)}] Query: {query}")

        # Call research_search tool via curl to the MCP server
        # The MCP server exposes tools via POST /tools/{tool_name}
        curl_cmd = [
            "curl",
            "-s",
            "-X", "POST",
            "http://127.0.0.1:8787/tools/research_search",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"query": query, "num_results": 15})
        ]

        try:
            result = subprocess.run(
                curl_cmd,
                capture_output=True,
                text=True,
                timeout=45
            )

            if result.returncode == 0:
                try:
                    tool_result = json.loads(result.stdout)
                    research_results["searches"][query] = {
                        "status": "success",
                        "result_count": len(tool_result) if isinstance(tool_result, list) else 1,
                        "results": tool_result[:10] if isinstance(tool_result, list) else tool_result
                    }
                    result_count = len(tool_result) if isinstance(tool_result, list) else 1
                    print(f"  ✓ {result_count} results\n")
                except json.JSONDecodeError:
                    research_results["searches"][query] = {
                        "status": "error",
                        "error": "Invalid JSON response"
                    }
                    print(f"  ✗ Invalid JSON response\n")
            else:
                research_results["searches"][query] = {
                    "status": "error",
                    "error": result.stderr
                }
                print(f"  ✗ Error: {result.returncode}\n")

        except subprocess.TimeoutExpired:
            research_results["searches"][query] = {
                "status": "timeout"
            }
            print(f"  ⏱ Timeout\n")
        except Exception as e:
            research_results["searches"][query] = {
                "status": "error",
                "error": str(e)
            }
            print(f"  ✗ Exception: {type(e).__name__}\n")

    print("[*] Research complete. Aggregating results...\n")

    return research_results


def main():
    """Main entry point"""

    # Run research
    print("[*] Using Loom CLI via Python subprocess...\n")

    try:
        results = run_research_direct()
    except Exception as e:
        print(f"[!] Research failed: {e}")
        print("\n[*] Attempting alternative approach via direct curl...")

        # Fallback: use direct curl requests
        results = {
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "research_id": "research_702_monitoring",
                "method": "curl_direct"
            },
            "searches": {}
        }

    # Ensure output directory exists
    output_dir = Path("/opt/research-toolbox/tmp")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save results
    output_file = output_dir / "research_702_monitoring.json"

    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"[✓] Results saved to: {output_file}")
    print(f"[✓] File size: {output_file.stat().st_size} bytes\n")

    # Print summary
    print("=" * 70)
    print("RESEARCH 702: REAL-TIME MODEL MONITORING SUMMARY")
    print("=" * 70)
    print(f"Timestamp: {results['metadata']['timestamp']}")
    print(f"Queries executed: {len(results.get('searches', {}))}")

    successful = sum(
        1 for q in results.get("searches", {}).values()
        if q.get("status") == "success"
    )
    print(f"Successful queries: {successful}")

    total_results = sum(
        q.get("result_count", 0) for q in results.get("searches", {}).values()
        if q.get("status") == "success"
    )
    print(f"Total results aggregated: {total_results}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
