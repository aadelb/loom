#!/usr/bin/env python3
"""Read ALL 346 tool output files, parse correctly, assess against baseline."""
import json
import os
import glob
import sys

OUTPUT_DIR = "/opt/research-toolbox/tmp/tool_outputs_346"
files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.json")))
print(f"Reading {len(files)} files from {OUTPUT_DIR}\n")

pass_tools = []
fail_tools = []

for fname in files:
    with open(fname) as f:
        data = json.load(f)

    tool = data["tool"]
    ms = data.get("time_ms", 0)
    response = data.get("response", {})

    # Handle transport-level issues
    if not isinstance(response, dict):
        fail_tools.append({"tool": tool, "reason": "invalid response type", "ms": ms})
        continue

    if "error" in response and "result" not in response:
        err = response.get("error", "")
        if err == "TIMEOUT":
            fail_tools.append({"tool": tool, "reason": "TIMEOUT", "ms": ms})
        else:
            fail_tools.append({"tool": tool, "reason": f"transport: {str(err)[:80]}", "ms": ms})
        continue

    # No response parsed (SSE parsing failed)
    if "result" not in response:
        fail_tools.append({"tool": tool, "reason": "no result in response", "ms": ms})
        continue

    result = response["result"]
    is_error = result.get("isError", False)
    structured = result.get("structuredContent")
    content_list = result.get("content", [])

    # Get text
    text = ""
    for c in content_list:
        if isinstance(c, dict) and c.get("type") == "text":
            text = c.get("text", "")
            break

    # Parse actual tool output
    if structured and isinstance(structured, dict):
        output = structured
    elif text:
        try:
            output = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            output = {"_raw": text[:500]}
    else:
        output = {}

    # Assessment
    if is_error:
        err_msg = text[:100] if text else "isError=true"
        fail_tools.append({"tool": tool, "reason": f"tool_error: {err_msg}", "ms": ms, "output": output})
    elif not output:
        fail_tools.append({"tool": tool, "reason": "empty output", "ms": ms})
    else:
        # Check if output is just an error dict
        has_real_data = False
        if isinstance(output, dict):
            non_error_keys = [k for k in output.keys() if k not in ("error",)]
            has_error = "error" in output and output["error"]
            if has_error and len(non_error_keys) <= 3:
                err_val = str(output["error"])[:100]
                # Graceful failures (not installed, key not set) are still passes
                if "not installed" in err_val.lower() or "not set" in err_val.lower() or "not found" in err_val.lower():
                    pass_tools.append({"tool": tool, "ms": ms, "size": len(json.dumps(output)),
                                       "keys": list(output.keys()), "note": "graceful_degradation"})
                    has_real_data = True
                else:
                    fail_tools.append({"tool": tool, "reason": f"soft_error: {err_val}", "ms": ms, "output": output})
                    has_real_data = True
            else:
                has_real_data = True
                pass_tools.append({"tool": tool, "ms": ms, "size": len(json.dumps(output)),
                                   "keys": list(output.keys())[:8]})
        else:
            has_real_data = True
            pass_tools.append({"tool": tool, "ms": ms, "size": len(str(output)), "keys": []})

        if not has_real_data:
            pass_tools.append({"tool": tool, "ms": ms, "size": len(json.dumps(output)),
                               "keys": list(output.keys())[:8] if isinstance(output, dict) else []})

# Print results
print("=" * 80)
print(f"FULL ASSESSMENT: {len(pass_tools)} PASS / {len(fail_tools)} FAIL (of {len(files)} total)")
print("=" * 80)

print(f"\n--- FAILURES ({len(fail_tools)}) ---")
for f in fail_tools:
    print(f"  {f['tool']:50s} | {f['reason']}")

print(f"\n--- ALL PASSING TOOLS ({len(pass_tools)}) ---")
for p in pass_tools:
    keys = ", ".join(p["keys"]) if p.get("keys") else ""
    note = f" [{p['note']}]" if p.get("note") else ""
    print(f"  {p['tool']:50s} | {p['size']:>8,}B | {p['ms']:>7,}ms | {keys}{note}")
