#!/usr/bin/env python3
"""Test Loom MCP tools #81-160 through MCP on Hetzner.

Maps tool file modules to their exposed functions and tests each with safe arguments.
"""

import asyncio
import json
import sys
from datetime import datetime
from typing import Any

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: pip install httpx", file=sys.stderr)
    sys.exit(1)


# Map tool modules to their functions and safe test arguments
TOOLS_81_160 = {
    81: ("metrics", "research_metrics_health", {}),
    82: ("misp_backend", "research_misp_search", {"query": "test"}),
    83: ("model_sentiment", "research_model_sentiment_analyze", {"text": "test text"}),
    84: ("multi_llm", "research_multi_llm_cascade", {"prompt": "test prompt"}),
    85: ("multi_search", "research_multi_search", {"query": "test"}),
    86: ("network_persona", "research_network_persona", {"username": "testuser"}),
    87: ("onion_discover", "research_onion_discover", {"query": "test"}),
    88: ("onion_spectra", "research_onion_spectra", {"target": "example.com"}),
    89: ("osint_extended", "research_osint_extended", {"target": "example.com"}),
    90: ("p3_tools", "research_p3_recon", {"target": "example.com"}),
    91: ("param_sweep", "research_param_sweep", {"base_prompt": "test", "variables": {"var1": ["val1"]}}),
    92: ("passive_recon", "research_passive_recon", {"target": "example.com"}),
    93: ("pdf_extract", "research_pdf_extract", {"text": "test content"}),
    94: ("pentest", "research_pentest_scan", {"target": "example.com"}),
    95: ("persona_profile", "research_persona_profile", {"username": "testuser"}),
    96: ("projectdiscovery", "research_projectdiscovery_scan", {"target": "example.com"}),
    97: ("prompt_analyzer", "research_prompt_analyze", {"prompt": "test prompt"}),
    98: ("prompt_reframe", "research_prompt_reframe", {"prompt": "test prompt"}),
    99: ("psycholinguistic", "research_psycholinguistic_analyze", {"text": "test text"}),
    100: ("radicalization_detect", "research_radicalization_detect", {"text": "test text"}),
    101: ("realtime_monitor", "research_realtime_monitor", {"query": "test"}),
    102: ("report_generator", "research_report_generate", {"texts": ["test report"]}),
    103: ("resume_intel", "research_resume_intel", {"resume_text": "test resume"}),
    104: ("rss_monitor", "research_rss_monitor", {"feed_url": "https://example.com/feed"}),
    105: ("salary_synthesizer", "research_salary_synthesize", {"role": "engineer", "location": "US"}),
    106: ("scraper_engine_tools", "research_scraper_engine_fetch", {"url": "https://example.com"}),
    107: ("screenshot", "research_screenshot", {"url": "https://example.com"}),
    108: ("search", "research_search", {"query": "test"}),
    109: ("security_headers", "research_security_headers", {"url": "https://example.com"}),
    110: ("semantic_cache_mgmt", "research_semantic_cache_stats", {}),
    111: ("sentiment_deep", "research_sentiment_deep_analyze", {"text": "test text"}),
    112: ("sherlock_backend", "research_sherlock_search", {"username": "testuser"}),
    113: ("signal_detection", "research_signal_detection", {"data": "test data"}),
    114: ("singlefile_backend", "research_singlefile_archive", {"url": "https://example.com"}),
    115: ("slack", "research_slack_notify", {"message": "test"}),
    116: ("social_analyzer_backend", "research_social_analyzer", {"username": "testuser"}),
    117: ("social_graph", "research_social_graph_map", {"username": "testuser"}),
    118: ("social_intel", "research_social_intel", {"username": "testuser"}),
    119: ("social_scraper", "research_social_scraper", {"username": "testuser"}),
    120: ("spider", "research_spider", {"urls": ["https://example.com"]}),
    121: ("spiderfoot_backend", "research_spiderfoot_scan", {"target": "example.com"}),
    122: ("stealth", "research_camoufox", {"url": "https://example.com"}),
    123: ("stealth_detect", "research_stealth_detect", {"response": "test response"}),
    124: ("stealth_score", "research_stealth_score", {"attack": "test"}),
    125: ("stego_detect", "research_stego_detect", {"file_path": "/tmp/test.bin"}),
    126: ("strategy_oracle", "research_strategy_oracle", {"target_model": "gpt-4"}),
    127: ("stylometry", "research_stylometry_analyze", {"text": "test text"}),
    128: ("supply_chain_intel", "research_supply_chain_intel", {"company": "example"}),
    129: ("synth_echo", "research_synth_echo", {"prompt": "test"}),
    130: ("text_analyze", "research_text_analyze", {"text": "test text"}),
    131: ("threat_intel", "research_threat_intel", {"target": "example.com"}),
    132: ("threat_profile", "research_threat_profile", {"target": "example.com"}),
    133: ("tool_recommender_tool", "research_tool_recommender", {"task": "test task"}),
    134: ("tor", "research_tor_check", {}),
    135: ("toxicity_checker_tool", "research_toxicity_check", {"text": "test text"}),
    136: ("transcribe", "research_transcribe", {"audio_url": "https://example.com/audio.mp3"}),
    137: ("trend_predictor", "research_trend_predict", {"data": ["test"]}),
    138: ("unique_tools", "research_unique_tool_demo", {}),
    139: ("urlhaus_lookup", "research_urlhaus_lookup", {"url": "https://example.com"}),
    140: ("vastai", "research_vastai_search", {"query": "gpu"}),
    141: ("vercel", "research_vercel_list", {}),
    142: ("vuln_intel", "research_vuln_intel", {"target": "example.com"}),
    143: ("yara_backend", "research_yara_scan", {"rule_name": "test"}),
    144: ("ytdlp_backend", "research_ytdlp_download", {"url": "https://example.com/video"}),
}


async def test_tool(client: httpx.AsyncClient, tool_num: int, module: str, func: str, args: dict[str, Any]) -> dict[str, Any]:
    """Test a single tool via MCP."""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": tool_num,
            "method": "tools/call",
            "params": {
                "name": func,
                "arguments": args
            }
        }

        # Set proper MCP headers
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        }

        response = await client.post(
            "http://127.0.0.1:8787/mcp",
            json=payload,
            headers=headers,
            timeout=30.0
        )

        result = response.json()
        status = "OK" if response.status_code == 200 else f"HTTP_{response.status_code}"

        return {
            "tool_num": tool_num,
            "module": module,
            "function": func,
            "status": status,
            "response_code": response.status_code,
            "has_error": "error" in result,
            "error": result.get("error", {}).get("message", ""),
            "result_type": type(result.get("result")).__name__ if "result" in result else "N/A",
        }
    except asyncio.TimeoutError:
        return {
            "tool_num": tool_num,
            "module": module,
            "function": func,
            "status": "TIMEOUT",
            "response_code": None,
            "has_error": True,
            "error": "Request timeout (30s)",
            "result_type": "N/A",
        }
    except Exception as e:
        return {
            "tool_num": tool_num,
            "module": module,
            "function": func,
            "status": "ERROR",
            "response_code": None,
            "has_error": True,
            "error": str(e),
            "result_type": "N/A",
        }


async def main():
    """Run all tests."""
    results = []

    async with httpx.AsyncClient() as client:
        print(f"Testing {len(TOOLS_81_160)} tools #81-160 via MCP on 127.0.0.1:8787")
        print(f"Start time: {datetime.now().isoformat()}")
        print("-" * 100)

        # Test each tool sequentially with small delays to avoid overwhelming the server
        for tool_num in sorted(TOOLS_81_160.keys()):
            module, func, args = TOOLS_81_160[tool_num]
            print(f"[{tool_num:3d}] Testing {module:30s} → {func:40s}", end=" ... ", flush=True)

            result = await test_tool(client, tool_num, module, func, args)
            results.append(result)

            status_icon = "✓" if result["status"] == "OK" and not result["has_error"] else "✗"
            print(f"{status_icon} {result['status']:10s}")

            # Small delay between requests
            await asyncio.sleep(0.1)

    # Summary statistics
    print("-" * 100)
    passed = sum(1 for r in results if r["status"] == "OK" and not r["has_error"])
    failed = len(results) - passed

    print(f"\nTest Results Summary:")
    print(f"  Total:    {len(results)}")
    print(f"  Passed:   {passed}")
    print(f"  Failed:   {failed}")
    print(f"  Success:  {passed/len(results)*100:.1f}%")
    print(f"  End time: {datetime.now().isoformat()}")

    # Save detailed results
    output_file = "/opt/research-toolbox/tmp/tools_test_batch_81_160.json"
    with open(output_file, "w") as f:
        json.dump({
            "test_run": {
                "start_time": datetime.now().isoformat(),
                "tool_range": "81-160",
                "total_tools": len(results),
                "passed": passed,
                "failed": failed,
                "success_rate": passed/len(results)*100,
            },
            "tools": results,
        }, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")

    # Return non-zero if any failures
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
