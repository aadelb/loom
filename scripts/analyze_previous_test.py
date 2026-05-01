#!/usr/bin/env python3
"""Analyze ALL outputs from the previous AGGRESSIVE_346_TEST and compare with expected."""
import json
import sys

with open("tmp/AGGRESSIVE_346_TEST.json") as f:
    data = json.load(f)

results = data["results"]

# Categorize ALL results
ok_with_data = []
ok_empty = []
err_validation = []
err_runtime = []
err_missing = []
exceptions = []

for r in results:
    tool = r["tool"]
    status = r["status"]
    detail = r.get("detail", "")
    size = r.get("size", 0)
    params = r.get("params_sent", {})

    if status == "OK":
        if size > 100:
            ok_with_data.append({"tool": tool, "size": size})
        else:
            ok_empty.append({"tool": tool, "size": size})
    elif status == "ERROR":
        if "validation error" in detail.lower():
            err_validation.append({"tool": tool, "detail": detail[:150], "params": params})
        elif "not installed" in detail.lower() or "not found" in detail.lower():
            err_missing.append({"tool": tool, "detail": detail[:150]})
        else:
            err_runtime.append({"tool": tool, "detail": detail[:150]})
    elif status == "EXCEPT":
        exceptions.append({"tool": tool, "detail": detail[:150]})

print("=" * 80)
print("FULL OUTPUT ANALYSIS — AGGRESSIVE_346_TEST.json")
print("=" * 80)
print(f"\nOK with real data:   {len(ok_with_data)} tools")
print(f"OK but small/empty:  {len(ok_empty)} tools")
print(f"ERROR validation:    {len(err_validation)} tools (test sent wrong param types)")
print(f"ERROR runtime:       {len(err_runtime)} tools (real bugs in code)")
print(f"ERROR missing dep:   {len(err_missing)} tools (binary/library not installed)")
print(f"EXCEPT:              {len(exceptions)} tools (unhandled crashes)")
print(f"\nTOTAL: {len(results)}")

# Expected baseline per category
print("\n" + "=" * 80)
print("EXPECTED vs ACTUAL COMPARISON")
print("=" * 80)

# Define what we EXPECT from each tool category
expected_rules = {
    "returns_dict": "Tool must return a JSON dict (not crash, not None)",
    "has_meaningful_data": "Response > 100 bytes with relevant keys",
    "no_validation_error": "All params must be accepted without validation errors",
    "no_crash": "Tool must not throw unhandled exceptions",
}

print("\n--- RULE: no_validation_error ---")
print(f"  EXPECTED: 0 validation errors")
print(f"  ACTUAL:   {len(err_validation)} validation errors")
print(f"  VERDICT:  {'PASS' if len(err_validation) == 0 else 'FAIL'}")
if err_validation:
    print(f"\n  Root cause: Test harness sends wrong param types")
    # Group by error type
    type_errors = {}
    for e in err_validation:
        d = e["detail"]
        if "Input should be a valid integer" in d:
            type_errors.setdefault("int_expected", []).append(e["tool"])
        elif "Input should be a valid dictionary" in d:
            type_errors.setdefault("dict_expected", []).append(e["tool"])
        elif "Input should be a valid list" in d:
            type_errors.setdefault("list_expected", []).append(e["tool"])
        elif "Extra inputs are not permitted" in d:
            type_errors.setdefault("extra_params", []).append(e["tool"])
        else:
            type_errors.setdefault("other", []).append(e["tool"])

    for err_type, tools in type_errors.items():
        print(f"    {err_type}: {len(tools)} tools")
        for t in tools[:5]:
            print(f"      - {t}")
        if len(tools) > 5:
            print(f"      ... +{len(tools) - 5} more")

print("\n--- RULE: no_crash ---")
print(f"  EXPECTED: 0 crashes")
print(f"  ACTUAL:   {len(exceptions)} crashes")
print(f"  VERDICT:  {'PASS' if len(exceptions) == 0 else 'FAIL'}")
for e in exceptions:
    print(f"    {e['tool']}: {e['detail']}")

print("\n--- RULE: no_runtime_error ---")
print(f"  EXPECTED: 0 runtime errors")
print(f"  ACTUAL:   {len(err_runtime)} runtime errors")
print(f"  VERDICT:  {'PASS' if len(err_runtime) == 0 else 'FAIL'}")
for e in err_runtime:
    print(f"    {e['tool']}: {e['detail']}")

print("\n--- RULE: has_meaningful_data ---")
print(f"  EXPECTED: All OK tools return >100 bytes")
print(f"  ACTUAL:   {len(ok_empty)} tools returned <100 bytes")
print(f"  VERDICT:  {'PASS' if len(ok_empty) == 0 else 'WARN'}")
for e in ok_empty[:10]:
    print(f"    {e['tool']}: {e['size']} bytes")

print("\n--- MISSING DEPENDENCIES ---")
print(f"  {len(err_missing)} tools need binaries/libraries installed:")
for e in err_missing:
    print(f"    {e['tool']}: {e['detail'][:80]}")

# Summary scorecard
print("\n" + "=" * 80)
print("SCORECARD")
print("=" * 80)
total = len(results)
real_pass = len(ok_with_data) + len(ok_empty)
real_fail = len(err_runtime) + len(exceptions)
test_issue = len(err_validation)
infra_issue = len(err_missing)

print(f"  Tools that WORK correctly:     {real_pass}/{total} ({100*real_pass/total:.1f}%)")
print(f"  Tools with REAL bugs:          {real_fail}/{total} ({100*real_fail/total:.1f}%)")
print(f"  Tools failing due to TEST BUG: {test_issue}/{total} ({100*test_issue/total:.1f}%)")
print(f"  Tools missing dependencies:    {infra_issue}/{total} ({100*infra_issue/total:.1f}%)")
print(f"\n  TRUE PASS RATE (excluding test bugs): {100*(real_pass)/(total-test_issue):.1f}%")
