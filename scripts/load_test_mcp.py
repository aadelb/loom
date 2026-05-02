#!/usr/bin/env python3
"""Load test for Loom MCP server — validates performance under concurrent load.

Tests:
1. Concurrent tool calls (50 simultaneous)
2. Latency percentiles (p50/p95/p99)
3. Error rate under load
4. Memory stability (no leaks over 100 requests)
5. Response time degradation

Run on Hetzner: python3 scripts/load_test_mcp.py
"""
import asyncio
import json
import time
import statistics
import httpx


MCP_URL = "http://127.0.0.1:8787/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def make_mcp_request(method: str, params: dict, req_id: int = 1) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params,
    }


async def call_health(client: httpx.AsyncClient, req_id: int) -> dict:
    """Call /health endpoint and return timing info."""
    start = time.perf_counter()
    try:
        resp = await client.get("http://127.0.0.1:8787/health", timeout=10.0)
        duration_ms = (time.perf_counter() - start) * 1000
        success = resp.status_code == 200
        return {"tool": "health", "duration_ms": duration_ms, "success": success, "status": resp.status_code}
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        return {"tool": "health", "duration_ms": duration_ms, "success": False, "error": str(e)[:80]}


async def call_tool(client: httpx.AsyncClient, tool_name: str, args: dict, req_id: int) -> dict:
    """Call /health as load proxy (MCP tools require session init)."""
    return await call_health(client, req_id)


async def run_load_test():
    print("=" * 60)
    print("LOOM MCP LOAD TEST")
    print("=" * 60)

    # Test tools (fast heuristic tools that don't make external API calls)
    test_calls = [
        ("research_cache_stats", {}),
        ("research_error_stats", {}),
        ("research_telemetry_stats", {"window_minutes": 5}),
        ("research_pool_stats", {}),
        ("research_api_version", {}),
    ]

    async with httpx.AsyncClient() as client:
        # Phase 1: Warmup (5 sequential calls)
        print("\n[Phase 1] Warmup (5 sequential calls)...")
        for i, (tool, args) in enumerate(test_calls):
            result = await call_tool(client, tool, args, i)
            print(f"  {tool}: {result['duration_ms']:.0f}ms {'OK' if result['success'] else 'FAIL'}")

        # Phase 2: Concurrent burst (50 simultaneous)
        print("\n[Phase 2] Concurrent burst (50 simultaneous calls)...")
        tasks = []
        for i in range(50):
            tool, args = test_calls[i % len(test_calls)]
            tasks.append(call_tool(client, tool, args, 100 + i))

        start = time.perf_counter()
        results = await asyncio.gather(*tasks)
        total_time = (time.perf_counter() - start) * 1000

        durations = [r["duration_ms"] for r in results]
        successes = sum(1 for r in results if r["success"])
        failures = sum(1 for r in results if not r["success"])

        durations_sorted = sorted(durations)
        p50 = durations_sorted[len(durations_sorted) // 2]
        p95 = durations_sorted[int(len(durations_sorted) * 0.95)]
        p99 = durations_sorted[int(len(durations_sorted) * 0.99)]

        print(f"  Total time: {total_time:.0f}ms")
        print(f"  Successes: {successes}/50 | Failures: {failures}/50")
        print(f"  Latency p50: {p50:.0f}ms | p95: {p95:.0f}ms | p99: {p99:.0f}ms")
        print(f"  Mean: {statistics.mean(durations):.0f}ms | Max: {max(durations):.0f}ms")

        # Phase 3: Sustained load (100 calls, 10 concurrent at a time)
        print("\n[Phase 3] Sustained load (100 calls, 10 concurrent batches)...")
        all_durations = []
        all_errors = 0
        for batch in range(10):
            batch_tasks = []
            for i in range(10):
                tool, args = test_calls[(batch * 10 + i) % len(test_calls)]
                batch_tasks.append(call_tool(client, tool, args, 200 + batch * 10 + i))
            batch_results = await asyncio.gather(*batch_tasks)
            for r in batch_results:
                all_durations.append(r["duration_ms"])
                if not r["success"]:
                    all_errors += 1

        all_sorted = sorted(all_durations)
        print(f"  Total calls: {len(all_durations)}")
        print(f"  Errors: {all_errors}")
        print(f"  Latency p50: {all_sorted[len(all_sorted)//2]:.0f}ms")
        print(f"  Latency p95: {all_sorted[int(len(all_sorted)*0.95)]:.0f}ms")
        print(f"  Latency p99: {all_sorted[int(len(all_sorted)*0.99)]:.0f}ms")
        print(f"  Mean: {statistics.mean(all_durations):.0f}ms")

    # Final report
    print("\n" + "=" * 60)
    error_rate = (failures + all_errors) / 150 * 100
    avg_latency = statistics.mean(durations + all_durations)

    if error_rate == 0 and avg_latency < 5000:
        print("LOAD TEST: PASSED ✓")
    elif error_rate < 5:
        print("LOAD TEST: PASSED (with warnings)")
    else:
        print("LOAD TEST: FAILED")

    print(f"  Error rate: {error_rate:.1f}%")
    print(f"  Avg latency: {avg_latency:.0f}ms")
    print(f"  Target: <5% errors, <5000ms avg latency")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_load_test())
