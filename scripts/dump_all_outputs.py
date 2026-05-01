#!/usr/bin/env python3
"""Call all 346 tools and save each tool's FULL output to a separate file."""
import asyncio
import json
import os
import time

import httpx

OUTPUT_DIR = "/opt/research-toolbox/tmp/tool_outputs_346"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Import param generation from our test
from real_query_test import generate_smart_params, TOOL_SPECIFIC_PARAMS


async def main():
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Initialize
        r = await client.post("http://127.0.0.1:8787/mcp", json={
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "dump", "version": "1.0"}}
        }, headers=headers)
        session_id = r.headers.get("mcp-session-id", "")
        headers["Mcp-Session-Id"] = session_id

        # List tools
        r = await client.post("http://127.0.0.1:8787/mcp", json={
            "jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}
        }, headers=headers)

        tools_data = None
        for line in r.text.strip().split("\n"):
            if line.startswith("data: "):
                tools_data = json.loads(line[6:])
                break

        all_tools = tools_data.get("result", {}).get("tools", [])
        print(f"Found {len(all_tools)} tools. Calling each and saving full output...")

        sem = asyncio.Semaphore(10)
        req_id = 2

        async def call_and_save(tool, idx):
            nonlocal req_id
            req_id += 1
            name = tool["name"]
            schema = tool.get("inputSchema", {})
            params = generate_smart_params(name, schema)

            async with sem:
                start = time.time()
                try:
                    r = await client.post("http://127.0.0.1:8787/mcp", json={
                        "jsonrpc": "2.0", "id": req_id,
                        "method": "tools/call",
                        "params": {"name": name, "arguments": params}
                    }, headers=headers, timeout=90)

                    elapsed_ms = int((time.time() - start) * 1000)

                    # Parse SSE response
                    result = None
                    for line in r.text.strip().split("\n"):
                        if line.startswith("data: "):
                            result = json.loads(line[6:])
                            break

                    if result is None:
                        result = {"error": "no response parsed"}

                except asyncio.TimeoutError:
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

                status = "OK" if "error" not in result else "ERR"
                print(f"[{idx+1}/{len(all_tools)}] {status} {name} ({elapsed_ms}ms)")

        tasks = [call_and_save(tool, i) for i, tool in enumerate(all_tools)]
        await asyncio.gather(*tasks)

    print(f"\nDone. {len(all_tools)} files saved to {OUTPUT_DIR}")


asyncio.run(main())
