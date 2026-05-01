#!/usr/bin/env python3
"""Call ALL 346 tools SEQUENTIALLY and save full output to individual files."""
import json
import os
import sys
import time

import httpx

sys.path.insert(0, "/opt/research-toolbox/scripts")
from real_query_test import generate_smart_params, TOOL_SPECIFIC_PARAMS

OUTPUT_DIR = "/opt/research-toolbox/tmp/tool_outputs_346"
os.makedirs(OUTPUT_DIR, exist_ok=True)

MCP_URL = "http://127.0.0.1:8787/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def parse_sse(text):
    """Parse SSE response to get last data event."""
    for line in reversed(text.strip().split("\n")):
        if line.startswith("data: "):
            try:
                return json.loads(line[6:])
            except json.JSONDecodeError:
                continue
    return None


def main():
    client = httpx.Client(timeout=180.0)

    # Initialize session
    r = client.post(MCP_URL, json={
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                   "clientInfo": {"name": "dump-seq", "version": "1.0"}}
    }, headers=HEADERS)
    session_id = r.headers.get("mcp-session-id", "")
    HEADERS["Mcp-Session-Id"] = session_id
    print(f"Session: {session_id[:20]}...")

    # List tools
    r = client.post(MCP_URL, json={
        "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}
    }, headers=HEADERS)
    tools_data = parse_sse(r.text)
    all_tools = tools_data.get("result", {}).get("tools", [])
    print(f"Found {len(all_tools)} tools. Calling each sequentially...\n")

    req_id = 2
    for i, tool in enumerate(all_tools):
        req_id += 1
        name = tool["name"]
        schema = tool.get("inputSchema", {})
        params = generate_smart_params(name, schema)

        start = time.time()
        try:
            r = client.post(MCP_URL, json={
                "jsonrpc": "2.0", "id": req_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": params}
            }, headers=HEADERS, timeout=90.0)

            elapsed_ms = int((time.time() - start) * 1000)
            result = parse_sse(r.text)

            if result is None:
                # Try direct JSON
                try:
                    result = r.json()
                except:
                    result = {"error": "parse_failed", "raw": r.text[:200]}

        except httpx.TimeoutException:
            elapsed_ms = int((time.time() - start) * 1000)
            result = {"error": "TIMEOUT", "timeout_ms": elapsed_ms}
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            result = {"error": str(e)}

        # Save full output
        output = {
            "tool": name,
            "params_sent": params,
            "time_ms": elapsed_ms,
            "response": result,
        }

        filepath = os.path.join(OUTPUT_DIR, f"{name}.json")
        with open(filepath, "w") as f:
            json.dump(output, f, indent=2, default=str)

        # Status
        has_result = isinstance(result, dict) and "result" in result
        status = "OK" if has_result else "ERR"
        print(f"[{i+1:3d}/{len(all_tools)}] {status} {name} ({elapsed_ms}ms)")

    print(f"\nDone. Files saved to {OUTPUT_DIR}")
    client.close()


if __name__ == "__main__":
    main()
