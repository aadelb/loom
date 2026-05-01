#!/usr/bin/env python3
"""Show detailed results from real_query_test_report.json."""
import json

with open("real_query_test_report.json") as f:
    data = json.load(f)

tools = data["tools"]
summary = data["summary"]

print("=" * 80)
print("REAL QUERY TEST RESULTS — Dubai Wealth Building")
print("=" * 80)
print(f"\nTotal: {summary['total']} | OK: {summary['ok']} | ERROR: {summary['error']} | TIMEOUT: {summary['timeout']} | SKIP: {summary['skip']}")
print(f"Success Rate: {100 * summary['ok'] / summary['total']:.1f}%")

# Timeouts
timeouts = [t for t in tools if t["status"] == "TIMEOUT"]
print(f"\n--- TIMEOUTS ({len(timeouts)} tools) ---")
for t in timeouts:
    name = t["tool_name"]
    ms = t["time_ms"]
    print(f"  {name}: {ms}ms")

# Skipped
skipped = [t for t in tools if t["status"] == "SKIP"]
print(f"\n--- SKIPPED ({len(skipped)} tools) ---")
for t in skipped:
    name = t["tool_name"]
    reason = t.get("error_detail", "")
    print(f"  {name}: {reason}")

# Errors
errors = [t for t in tools if t["status"] == "ERROR"]
if errors:
    print(f"\n--- ERRORS ({len(errors)} tools) ---")
    for t in errors:
        name = t["tool_name"]
        detail = t.get("error_detail", "")
        print(f"  {name}: {detail}")

# Top responses by size
ok_tools = [t for t in tools if t["status"] == "OK"]
ok_sorted = sorted(ok_tools, key=lambda x: x["response_size"], reverse=True)
print(f"\n--- TOP 15 RICHEST RESPONSES ---")
for t in ok_sorted[:15]:
    name = t["tool_name"]
    size = t["response_size"]
    ms = t["time_ms"]
    print(f"  {name}: {size:,} bytes ({ms}ms)")

# Fastest
fast = sorted(ok_tools, key=lambda x: x["time_ms"])
print(f"\n--- TOP 10 FASTEST ---")
for t in fast[:10]:
    name = t["tool_name"]
    size = t["response_size"]
    ms = t["time_ms"]
    print(f"  {name}: {ms}ms ({size:,} bytes)")

# Slowest OK tools
slow = sorted(ok_tools, key=lambda x: x["time_ms"], reverse=True)
print(f"\n--- TOP 10 SLOWEST (still OK) ---")
for t in slow[:10]:
    name = t["tool_name"]
    size = t["response_size"]
    ms = t["time_ms"]
    print(f"  {name}: {ms}ms ({size:,} bytes)")

# Small responses (potential quality issues)
small = sorted([t for t in ok_tools if t["response_size"] < 200], key=lambda x: x["response_size"])
print(f"\n--- SMALL RESPONSES (<200 bytes) — potential quality issues ({len(small)} tools) ---")
for t in small[:20]:
    name = t["tool_name"]
    size = t["response_size"]
    print(f"  {name}: {size} bytes")

# Compare with EXPECTED
print("\n" + "=" * 80)
print("EXPECTED vs ACTUAL COMPARISON")
print("=" * 80)
print(f"\n  EXPECTED: 346 tools pass (100%)")
print(f"  ACTUAL:   {summary['ok']} tools pass ({100*summary['ok']/summary['total']:.1f}%)")
print(f"  GAP:      {summary['total'] - summary['ok']} tools ({summary['timeout']} timeouts + {summary['skip']} skipped + {summary['error']} errors)")
print(f"\n  PREVIOUS TEST: 275/346 (79.5%)")
print(f"  CURRENT TEST:  {summary['ok']}/346 ({100*summary['ok']/346:.1f}%)")
print(f"  IMPROVEMENT:   +{summary['ok'] - 275} tools (+{100*(summary['ok']-275)/275:.1f}%)")
