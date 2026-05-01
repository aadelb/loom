#!/usr/bin/env python3
"""Read ALL 346 tool output files and assess each against expected behavior."""
import json
import os
import glob

OUTPUT_DIR = "/opt/research-toolbox/tmp/tool_outputs_346"
files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.json")))
print(f"Reading {len(files)} tool output files...\n")

results = {"pass": [], "soft_error": [], "real_error": [], "timeout": [], "empty": []}

for fname in files:
    with open(fname) as f:
        data = json.load(f)

    tool = data["tool"]
    ms = data["time_ms"]
    params = data.get("params_sent", {})
    response = data.get("response", {})

    # Handle timeout
    if isinstance(response, dict) and response.get("error") == "TIMEOUT":
        results["timeout"].append({"tool": tool, "ms": ms})
        continue

    # Handle connection/transport error
    if isinstance(response, dict) and "error" in response and "result" not in response:
        results["real_error"].append({"tool": tool, "ms": ms, "error": str(response["error"])[:150]})
        continue

    # Get MCP result
    result = response.get("result", {})
    is_error = result.get("isError", False)
    structured = result.get("structuredContent", {})

    # Parse text content
    text_content = ""
    for c in result.get("content", []):
        if isinstance(c, dict) and c.get("type") == "text":
            text_content = c.get("text", "")
            break

    # Try to get actual output dict
    if structured:
        output = structured
    elif text_content:
        try:
            output = json.loads(text_content)
        except (json.JSONDecodeError, TypeError):
            output = {"_raw": text_content[:500]}
    else:
        output = {}

    # Classify
    if is_error:
        err_msg = text_content[:150] if text_content else "isError=true"
        results["soft_error"].append({"tool": tool, "ms": ms, "error": err_msg, "params": params})
    elif not output or (isinstance(output, dict) and len(output) == 0):
        results["empty"].append({"tool": tool, "ms": ms})
    elif isinstance(output, dict) and "error" in output and output.get("text", "") == "" and len(output) <= 4:
        # Tool returned but with an error field (partial failure)
        err = output.get("error", "")
        if err and "not installed" not in str(err).lower():
            results["soft_error"].append({"tool": tool, "ms": ms, "error": str(err)[:150], "params": params})
        else:
            results["pass"].append({"tool": tool, "ms": ms, "size": len(json.dumps(output)), "output_keys": list(output.keys())[:6]})
    else:
        results["pass"].append({"tool": tool, "ms": ms, "size": len(json.dumps(output)), "output_keys": list(output.keys())[:6]})

# Print full report
print("=" * 80)
print(f"FULL OUTCOME ASSESSMENT — {len(files)} TOOLS")
print("=" * 80)
print(f"\n  PASS (real data returned):  {len(results['pass'])}")
print(f"  SOFT ERROR (tool returned error): {len(results['soft_error'])}")
print(f"  REAL ERROR (MCP/transport):       {len(results['real_error'])}")
print(f"  TIMEOUT:                          {len(results['timeout'])}")
print(f"  EMPTY:                            {len(results['empty'])}")

print(f"\n{'='*80}")
print("SOFT ERRORS — tools that returned but reported an issue:")
print("=" * 80)
for e in results["soft_error"]:
    print(f"  {e['tool']:50s} | {e['error'][:80]}")
    if e.get("params"):
        print(f"    params: {json.dumps(e['params'])[:100]}")

print(f"\n{'='*80}")
print("REAL ERRORS:")
print("=" * 80)
for e in results["real_error"]:
    print(f"  {e['tool']:50s} | {e['error'][:80]}")

print(f"\n{'='*80}")
print("TIMEOUTS:")
print("=" * 80)
for e in results["timeout"]:
    print(f"  {e['tool']:50s} | {e['ms']}ms")

print(f"\n{'='*80}")
print(f"PASSING TOOLS ({len(results['pass'])}) — output keys sample:")
print("=" * 80)
for p in results["pass"]:
    keys = ", ".join(p["output_keys"])
    print(f"  {p['tool']:50s} | {p['size']:>8,}B | {p['ms']:>7,}ms | {keys}")
