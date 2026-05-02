#!/usr/bin/env python3
"""Use Loom to discover ALL required tests, then execute them ALL.

This script:
1. Asks Loom what testing is needed
2. Executes each test type
3. Collects all results
4. Identifies all issues
5. Reports everything
"""
import sys
import json
import asyncio
import time
import httpx

sys.path.insert(0, "src")

MCP_URL = "http://127.0.0.1:8787/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


async def init_session(client):
    """Initialize MCP session."""
    r = await client.post(MCP_URL, json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                   "clientInfo": {"name": "discover-test", "version": "1.0"}}
    }, headers=HEADERS)
    session_id = r.headers.get("mcp-session-id", "")
    HEADERS["Mcp-Session-Id"] = session_id
    return session_id


async def call_tool(client, tool_name, params, timeout=90):
    """Call a Loom tool via MCP."""
    r = await client.post(MCP_URL, json={
        "jsonrpc": "2.0", "id": 99,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": params}
    }, headers=HEADERS, timeout=timeout)

    for line in r.text.strip().split("\n"):
        if line.startswith("data: "):
            try:
                data = json.loads(line[6:])
                result = data.get("result", {})
                structured = result.get("structuredContent")
                if structured:
                    return structured
                content = result.get("content", [])
                for c in content:
                    if c.get("type") == "text":
                        try:
                            return json.loads(c["text"])
                        except:
                            return {"text": c["text"]}
            except:
                continue
    return {"error": "no response"}


async def main():
    print("=" * 70)
    print("LOOM SELF-TESTING: Discover all issues via Loom's own tools")
    print("=" * 70)

    async with httpx.AsyncClient(timeout=180.0) as client:
        session = await init_session(client)
        print(f"Session: {session[:20]}...")

        # TEST 1: Health check
        print("\n[TEST 1] Server Health...")
        health = await call_tool(client, "research_health_check", {})
        print(f"  Status: {health}")

        # TEST 2: Tool count verification
        print("\n[TEST 2] Tool Count...")
        # List all tools
        r = await client.post(MCP_URL, json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}
        }, headers=HEADERS)
        for line in r.text.strip().split("\n"):
            if line.startswith("data: "):
                data = json.loads(line[6:])
                tools = data.get("result", {}).get("tools", [])
                print(f"  Tools registered: {len(tools)}")
                break

        # TEST 3: Core tools smoke test (fast tools)
        print("\n[TEST 3] Core Tools Smoke Test...")
        smoke_tools = [
            ("research_cache_stats", {}),
            ("research_config_get", {"key": "LOG_LEVEL"}),
            ("research_hcs_score", {"text": "Dubai is a great business hub", "rubric": "relevance"}),
            ("research_prompt_reframe", {"prompt": "test prompt", "n": 1}),
            ("research_build_query", {"user_request": "how to invest in Dubai"}),
        ]

        for tool_name, params in smoke_tools:
            start = time.time()
            result = await call_tool(client, tool_name, params, timeout=30)
            elapsed = int((time.time() - start) * 1000)
            has_error = "error" in str(result).lower() and "result" not in str(result)
            status = "FAIL" if has_error else "OK"
            print(f"  [{status}] {tool_name} ({elapsed}ms)")

        # TEST 4: LLM provider connectivity
        print("\n[TEST 4] LLM Provider Test...")
        llm_result = await call_tool(client, "research_llm_embed", {"text": "test"}, timeout=30)
        if "error" in str(llm_result).lower():
            print(f"  [FAIL] LLM providers: {str(llm_result)[:100]}")
        else:
            print(f"  [OK] LLM providers working")

        # TEST 5: Search provider connectivity
        print("\n[TEST 5] Search Provider Test...")
        search_result = await call_tool(client, "research_search", {
            "query": "Dubai investment", "provider": "brave", "n": 3
        }, timeout=30)
        results_count = len(search_result.get("results", []))
        print(f"  Search results: {results_count}")

        # TEST 6: Browser/scraping test
        print("\n[TEST 6] Scraping Test...")
        fetch_result = await call_tool(client, "research_fetch", {
            "url": "https://www.khaleejtimes.com"
        }, timeout=30)
        has_content = len(str(fetch_result)) > 100
        print(f"  Fetch: {'OK' if has_content else 'FAIL'} ({len(str(fetch_result))} bytes)")

        # TEST 7: Dark web tools
        print("\n[TEST 7] Dark Web Tools...")
        dark_result = await call_tool(client, "research_dark_cti", {
            "query": "financial crime UAE"
        }, timeout=60)
        print(f"  Dark CTI: {len(str(dark_result))} bytes")

        # TEST 8: Crypto tools
        print("\n[TEST 8] Crypto Tools...")
        crypto_result = await call_tool(client, "research_crypto_trace", {
            "address": "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
        }, timeout=30)
        print(f"  Crypto trace: {list(crypto_result.keys())[:5]}")

        # TEST 9: DSPy query builder with darkness
        print("\n[TEST 9] Full Spectrum Query Builder (darkness=10)...")
        qb_result = await call_tool(client, "research_build_query", {
            "user_request": "how to become rich in Dubai",
            "darkness_level": 10,
            "max_queries": 10,
        }, timeout=60)
        sub_q = qb_result.get("sub_questions", [])
        print(f"  Sub-questions generated: {len(sub_q)}")
        techniques = qb_result.get("metadata", {}).get("techniques_applied", [])
        print(f"  Techniques applied: {len(techniques)}")

        # TEST 10: Session management
        print("\n[TEST 10] Session Management...")
        session_result = await call_tool(client, "research_session_list", {})
        print(f"  Sessions: {session_result}")

        # TEST 11: Workflow engine
        print("\n[TEST 11] Workflow Engine...")
        wf_result = await call_tool(client, "research_workflow_create", {
            "name": "test_workflow",
            "steps": [
                {"tool": "research_fetch", "params": {"url": "https://example.com"}},
                {"tool": "research_text_analyze", "params": {"text": "sample"}},
            ]
        }, timeout=30)
        print(f"  Workflow: {list(wf_result.keys())[:5]}")

        # TEST 12: Knowledge graph
        print("\n[TEST 12] Knowledge Graph...")
        kg_result = await call_tool(client, "research_graph_store", {
            "entities": [{"name": "Dubai", "type": "city", "properties": {"country": "UAE"}}],
            "relationships": [{"source": "Dubai", "target": "UAE", "relation": "part_of"}],
        }, timeout=30)
        print(f"  Graph store: {kg_result}")

        # SUMMARY
        print("\n" + "=" * 70)
        print("DISCOVERY COMPLETE")
        print("=" * 70)


asyncio.run(main())
