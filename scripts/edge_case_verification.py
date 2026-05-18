#!/usr/bin/env python3
"""Edge case verification suite for Loom MCP server on port 8788.

Tests 5 categories of edge cases against a diverse sample of live tools:
1. Empty string inputs
2. Very long inputs (10KB+)
3. Unicode/Arabic inputs
4. Missing required params
5. Invalid param types
"""
from __future__ import annotations

import json
import socket
import urllib.request
import urllib.error
from datetime import datetime, timezone

BASE_URL = "http://127.0.0.1:8788"
TIMEOUT_SECS = 18

# Focused sample: mix of fast local tools + some string-based tools
TOOL_SAMPLE = [
    # Fast / no external calls
    "research_health_check",
    "research_cpu_pool_status",
    "research_validate_startup",
    "research_circuit_status",
    "research_tools_list",
    "research_cache_stats",
    "research_compression_stats",
    "research_help",
    "research_config_get",
    "research_rate_limits",
    "research_latency_probe",
    # String-param tools (should be fast / local)
    "research_prompt_analyze",
    "research_refusal_detector",
    "research_format_smuggle",
    "research_auto_reframe",
    "research_compress_prompt",
    "research_defend_test",
    "research_hallucination_benchmark",
    "research_model_vulnerability_profile",
    "research_bias_probe",
    "research_safety_filter_map",
]


def api_get(path: str) -> dict:
    req = urllib.request.Request(f"{BASE_URL}{path}", method="GET")
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_post(path: str, payload: dict) -> tuple[int, dict | str]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, body
    except urllib.error.URLError as e:
        return 0, f"URLError: {e.reason}"
    except socket.timeout:
        return 0, "TIMEOUT"
    except Exception as e:
        return 0, f"Exception: {type(e).__name__}: {str(e)[:200]}"


def classify_response(status: int, body: dict | str) -> dict:
    """Classify whether the response is graceful or a crash."""
    is_error = status >= 400 or (isinstance(body, dict) and ("error" in body or "detail" in body))
    is_crash = False
    crash_indicators = [
        "internal server error",
        "traceback",
        "unexpected error",
        "server-error",
    ]
    body_str = json.dumps(body) if isinstance(body, dict) else str(body)
    body_lower = body_str.lower()
    if status in (500, 502, 503, 504):
        is_crash = True
    elif any(ind in body_lower for ind in crash_indicators):
        is_crash = True

    return {
        "status": status,
        "is_error": is_error,
        "is_crash": is_crash,
        "graceful": is_error and not is_crash,
        "body_preview": body_str[:300],
    }


def build_test_payload(tool_name: str, params: dict, case_type: str) -> dict:
    """Mutate params for a specific edge case."""
    payload = {}
    for pname, pmeta in params.items():
        if pname in ("self", "cls", "request"):
            continue
        is_required = pmeta.get("required", False)
        ptype = pmeta.get("type", "")
        default = pmeta.get("default")
        if pname.startswith("_"):
            continue

        if case_type == "missing_required":
            if is_required:
                continue
            elif default is not None and default != "None":
                payload[pname] = _coerce_default(default, ptype)
            else:
                payload[pname] = _neutral_value(ptype)
        elif case_type == "empty_string":
            if "str" in ptype:
                payload[pname] = ""
            elif is_required and default is None:
                payload[pname] = _neutral_value(ptype)
            elif default is not None and default != "None":
                payload[pname] = _coerce_default(default, ptype)
            else:
                payload[pname] = _neutral_value(ptype)
        elif case_type == "long_input":
            if "str" in ptype:
                payload[pname] = "X" * 11000
            elif is_required:
                payload[pname] = _neutral_value(ptype)
            elif default is not None and default != "None":
                payload[pname] = _coerce_default(default, ptype)
            else:
                payload[pname] = _neutral_value(ptype)
        elif case_type == "unicode_arabic":
            if "str" in ptype:
                payload[pname] = "مرحبا بالعالم 🌍 日本語 ελληνικά"
            elif is_required:
                payload[pname] = _neutral_value(ptype)
            elif default is not None and default != "None":
                payload[pname] = _coerce_default(default, ptype)
            else:
                payload[pname] = _neutral_value(ptype)
        elif case_type == "invalid_type":
            if "int" in ptype and is_required:
                payload[pname] = "not_a_number"
            elif "bool" in ptype and is_required:
                payload[pname] = "not_a_bool"
            elif "list" in ptype and is_required:
                payload[pname] = "not_a_list"
            elif "dict" in ptype and is_required:
                payload[pname] = "not_a_dict"
            elif "str" in ptype and is_required:
                payload[pname] = 12345
            elif is_required:
                payload[pname] = {"__invalid__": True}
            elif default is not None and default != "None":
                payload[pname] = _coerce_default(default, ptype)
            else:
                payload[pname] = _neutral_value(ptype)
        else:
            if is_required:
                payload[pname] = _neutral_value(ptype)
            elif default is not None and default != "None":
                payload[pname] = _coerce_default(default, ptype)
            else:
                payload[pname] = _neutral_value(ptype)
    return payload


def _neutral_value(ptype: str):
    if "int" in ptype:
        return 1
    if "bool" in ptype:
        return True
    if "list" in ptype:
        return []
    if "dict" in ptype:
        return {}
    if "float" in ptype:
        return 1.0
    return "test"


def _coerce_default(default, ptype: str):
    if default == "True":
        return True
    if default == "False":
        return False
    if default == "None":
        return None
    if "int" in ptype:
        try:
            return int(default)
        except Exception:
            return 1
    if "float" in ptype:
        try:
            return float(default)
        except Exception:
            return 1.0
    return default


def main():
    print("=" * 60)
    print("Loom Edge Case Verification Suite")
    print(f"Target: {BASE_URL}")
    print(f"Time:   {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    health = api_get("/health")
    print(f"\nHealth: {health.get('status')} | Tools: {health.get('tool_count')} | Strategies: {health.get('strategy_count')}")

    results: list[dict] = []

    for tool_name in TOOL_SAMPLE:
        print(f"\n--- Testing: {tool_name} ---")
        try:
            info = api_get(f"/api/v1/tools/{tool_name}/info")
        except Exception as e:
            print(f"  SKIP: Could not fetch info: {e}")
            continue

        params = info.get("parameters", {})
        has_required = any(p.get("required") for p in params.values())
        has_string = any("str" in p.get("type", "") for p in params.values())

        cases = []
        if has_string:
            cases.extend(["empty_string", "long_input", "unicode_arabic"])
        if has_required:
            cases.append("missing_required")
        if params:
            cases.append("invalid_type")
        if not cases:
            cases.append("baseline")

        for case in cases:
            payload = build_test_payload(tool_name, params, case)
            status, body = api_post(f"/api/v1/tools/{tool_name}", payload)
            classification = classify_response(status, body)

            record = {
                "tool": tool_name,
                "case": case,
                "status": status,
                "graceful": classification["graceful"],
                "is_crash": classification["is_crash"],
                "is_error": classification["is_error"],
                "body_preview": classification["body_preview"],
                "payload_preview": str(payload)[:200],
            }
            results.append(record)
            status_label = "CRASH" if classification["is_crash"] else ("ERROR" if classification["is_error"] else "OK")
            print(f"  [{case:20s}] HTTP {status:3d} -> {status_label}")

    with open("edge_case_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"Done. {len(results)} test records written to edge_case_results.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
