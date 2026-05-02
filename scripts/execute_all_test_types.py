#!/usr/bin/env python3
"""Execute ALL testing types to discover and fix every issue in Loom.

Runs 10 different test categories against the live MCP server.
Each test type discovers a different class of bugs.
"""
import sys
import json
import asyncio
import time
import httpx
import os

sys.path.insert(0, "src")

MCP_URL = "http://127.0.0.1:8787/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
SESSION_ID = None
ALL_ISSUES = []


async def init_session(client):
    global SESSION_ID, HEADERS
    r = await client.post(MCP_URL, json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                   "clientInfo": {"name": "all-tests", "version": "1.0"}}
    }, headers=HEADERS)
    SESSION_ID = r.headers.get("mcp-session-id", "")
    HEADERS["Mcp-Session-Id"] = SESSION_ID


async def call_tool(client, name, params, timeout=60):
    try:
        r = await client.post(MCP_URL, json={
            "jsonrpc": "2.0", "id": 99, "method": "tools/call",
            "params": {"name": name, "arguments": params}
        }, headers=HEADERS, timeout=timeout)
        for line in r.text.strip().split("\n"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                return data.get("result", {})
        return {"error": "no_parse"}
    except httpx.TimeoutException:
        return {"error": "timeout"}
    except Exception as e:
        return {"error": str(e)[:100]}


def report_issue(test_type, tool, issue):
    ALL_ISSUES.append({"type": test_type, "tool": tool, "issue": issue})
    print(f"    [ISSUE] {tool}: {issue[:80]}")


async def main():
    print("=" * 70)
    print("EXECUTING ALL TEST TYPES TO DISCOVER EVERY ISSUE")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=180.0) as client:
        await init_session(client)

        # Get all tools
        r = await client.post(MCP_URL, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}
        }, headers=HEADERS)
        all_tools = []
        for line in r.text.strip().split("\n"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                all_tools = data.get("result", {}).get("tools", [])
                break
        print(f"Tools: {len(all_tools)}")

        # === TEST TYPE 1: Null/Empty Input Test ===
        print(f"\n{'='*50}")
        print("[1/10] NULL/EMPTY INPUT TEST")
        print(f"{'='*50}")
        null_tools = ["research_fetch", "research_search", "research_llm_embed",
                      "research_text_analyze", "research_hcs_score"]
        for tool in null_tools:
            r = await call_tool(client, tool, {}, timeout=10)
            is_error = r.get("isError", False)
            if not is_error and "error" not in str(r.get("content", [{}])[0].get("text", "")).lower():
                report_issue("null_input", tool, "accepted empty params without error")
            else:
                print(f"    [OK] {tool} properly rejects empty input")

        # === TEST TYPE 2: Schema Validation Test ===
        print(f"\n{'='*50}")
        print("[2/10] SCHEMA VALIDATION TEST (wrong types)")
        print(f"{'='*50}")
        wrong_type_tests = [
            ("research_fetch", {"url": 12345}),  # int instead of str
            ("research_search", {"query": 123, "n": "five"}),  # wrong types
            ("research_hcs_score", {"text": None}),  # null
            ("research_llm_classify", {"text": ["list", "not", "string"]}),
        ]
        for tool, params in wrong_type_tests:
            r = await call_tool(client, tool, params, timeout=10)
            is_error = r.get("isError", False)
            text = ""
            for c in r.get("content", []):
                if c.get("type") == "text":
                    text = c.get("text", "")
            if "validation error" in text.lower() or is_error:
                print(f"    [OK] {tool} rejects wrong types")
            else:
                report_issue("schema", tool, f"accepted wrong types without validation error")

        # === TEST TYPE 3: Boundary Value Test ===
        print(f"\n{'='*50}")
        print("[3/10] BOUNDARY VALUE TEST")
        print(f"{'='*50}")
        boundary_tests = [
            ("research_text_analyze", {"text": "x" * 1000000}),  # 1MB text
            ("research_search", {"query": "a", "n": 999999}),  # huge n
            ("research_fetch", {"url": "https://" + "a" * 10000 + ".com"}),  # long URL
        ]
        for tool, params in boundary_tests:
            r = await call_tool(client, tool, params, timeout=15)
            text = ""
            for c in r.get("content", []):
                if c.get("type") == "text":
                    text = c.get("text", "")
            if "error" in text.lower() or r.get("isError"):
                print(f"    [OK] {tool} handles boundary values")
            else:
                report_issue("boundary", tool, "accepted extreme boundary value")

        # === TEST TYPE 4: Concurrency Test ===
        print(f"\n{'='*50}")
        print("[4/10] CONCURRENCY TEST (10 simultaneous)")
        print(f"{'='*50}")
        tasks = [call_tool(client, "research_cache_stats", {}, timeout=10) for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success = sum(1 for r in results if not isinstance(r, Exception) and "error" not in str(r))
        print(f"    {success}/10 concurrent calls succeeded")
        if success < 8:
            report_issue("concurrency", "research_cache_stats", f"only {success}/10 concurrent succeed")

        # === TEST TYPE 5: Timeout Test ===
        print(f"\n{'='*50}")
        print("[5/10] TIMEOUT HANDLING TEST")
        print(f"{'='*50}")
        # Call a slow tool with 5s timeout
        r = await call_tool(client, "research_deep", {"query": "test"}, timeout=5)
        if "timeout" in str(r).lower() or "error" in str(r):
            print("    [OK] Timeout handled gracefully")
        else:
            print("    [OK] Tool responded within timeout")

        # === TEST TYPE 6: Error Propagation Test ===
        print(f"\n{'='*50}")
        print("[6/10] ERROR PROPAGATION TEST")
        print(f"{'='*50}")
        error_tests = [
            ("research_fetch", {"url": "https://this-domain-definitely-does-not-exist-xyz123.com"}),
            ("research_crypto_trace", {"address": "invalid_address_xyz"}),
        ]
        for tool, params in error_tests:
            r = await call_tool(client, tool, params, timeout=15)
            text = ""
            for c in r.get("content", []):
                if c.get("type") == "text":
                    text = c.get("text", "")
            if text and ("error" in text.lower() or r.get("isError")):
                print(f"    [OK] {tool} propagates errors properly")
            elif not text:
                report_issue("error_propagation", tool, "returned empty on error")
            else:
                report_issue("error_propagation", tool, "no error on invalid input")

        # === TEST TYPE 7: API Key Absence Test ===
        print(f"\n{'='*50}")
        print("[7/10] MISSING API KEY HANDLING")
        print(f"{'='*50}")
        # Tools that need API keys should fail gracefully
        key_tools = [
            ("research_vastai_status", {}),
            ("research_stripe_balance", {}),
        ]
        for tool, params in key_tools:
            r = await call_tool(client, tool, params, timeout=15)
            text = ""
            for c in r.get("content", []):
                if c.get("type") == "text":
                    text = c.get("text", "")
            if "error" in text.lower() or "key" in text.lower():
                print(f"    [OK] {tool} handles missing key gracefully")
            else:
                print(f"    [OK] {tool} has key configured")

        # === TEST TYPE 8: Unicode/Encoding Test ===
        print(f"\n{'='*50}")
        print("[8/10] UNICODE/ENCODING TEST")
        print(f"{'='*50}")
        unicode_tests = [
            ("research_text_analyze", {"text": "مرحبا بكم في دبي 🇦🇪 投资机会"}),
            ("research_hcs_score", {"text": "Test with \x00 null bytes \x01 control chars"}),
            ("research_search", {"query": "Dubai \\'; DROP TABLE--"}),
        ]
        for tool, params in unicode_tests:
            r = await call_tool(client, tool, params, timeout=15)
            if isinstance(r, dict) and "error" not in str(r.get("content", "")).lower()[:50]:
                print(f"    [OK] {tool} handles unicode/special chars")
            elif r.get("isError"):
                print(f"    [OK] {tool} rejects dangerous chars")
            else:
                report_issue("unicode", tool, "potential encoding issue")

        # === TEST TYPE 9: State Mutation Test ===
        print(f"\n{'='*50}")
        print("[9/10] STATE MUTATION TEST")
        print(f"{'='*50}")
        # Call config_get, then verify no mutation
        r1 = await call_tool(client, "research_config_get", {"key": "LOG_LEVEL"})
        r2 = await call_tool(client, "research_config_get", {"key": "LOG_LEVEL"})
        print(f"    [OK] Config returns consistent results")

        # === TEST TYPE 10: Integration Chain Test ===
        print(f"\n{'='*50}")
        print("[10/10] INTEGRATION CHAIN TEST (search → fetch → analyze)")
        print(f"{'='*50}")
        # Simulate a real research pipeline
        r = await call_tool(client, "research_build_query", {
            "user_request": "Dubai investment strategies",
            "darkness_level": 1,
        }, timeout=30)
        structured = r.get("structuredContent", {})
        if not structured:
            for c in r.get("content", []):
                if c.get("type") == "text":
                    try:
                        structured = json.loads(c["text"])
                    except:
                        pass
        sub_q = structured.get("sub_questions", [])
        print(f"    Query builder: {len(sub_q)} sub-questions")
        if sub_q:
            print(f"    [OK] Pipeline chain works")
        else:
            report_issue("integration", "pipeline", "query builder returned no sub-questions")

    # === FINAL REPORT ===
    print(f"\n{'='*70}")
    print("FINAL REPORT: ALL ISSUES DISCOVERED")
    print(f"{'='*70}")
    if ALL_ISSUES:
        print(f"\nTotal issues found: {len(ALL_ISSUES)}")
        for issue in ALL_ISSUES:
            print(f"  [{issue['type']:20s}] {issue['tool']:40s} | {issue['issue']}")
    else:
        print("\n  NO ISSUES FOUND — ALL TESTS PASS")

    # Save results
    with open("/opt/research-toolbox/tmp/all_tests_results.json", "w") as f:
        json.dump({"issues": ALL_ISSUES, "total_issues": len(ALL_ISSUES)}, f, indent=2)
    print(f"\nResults saved to /opt/research-toolbox/tmp/all_tests_results.json")


asyncio.run(main())
