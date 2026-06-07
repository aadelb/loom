"""R17 Smart Audit — uses per-tool params from tool_params.json.

Unlike R15/R16 which used generic params (54% pass), this uses
the correct params for each tool based on its signature.
"""
import json
import requests
import time
import sys

BASE = "http://localhost:8788/api/v1/tools"

# Load tool params DB
with open("/opt/loom-v3/docs/tool_params.json") as f:
    PARAMS_DB = json.load(f)

# Smart param generator based on param name heuristics
PARAM_EXAMPLES = {
    "query": "artificial intelligence safety research",
    "text": "This is a comprehensive test of the system capabilities.",
    "url": "https://httpbin.org/json",
    "urls": ["https://example.com"],
    "domain": "example.com",
    "ip": "8.8.8.8",
    "email": "test@example.com",
    "target": "example.com",
    "target_url": "https://example.com",
    "prompt": "Explain quantum computing in simple terms",
    "original_prompt": "test prompt",
    "reframed_prompt": "reframed test prompt",
    "username": "testuser",
    "password": "TestP@ssw0rd123!",
    "response": "Here is a detailed analysis of the topic with specific examples.",
    "claim": "The Earth orbits the Sun",
    "keyword": "security",
    "topic": "AI safety",
    "n": 3,
    "limit": 5,
    "depth": 1,
    "count": 3,
    "model": "auto",
    "strategy": "ethical_anchor",
    "kind": "repo",
    "key": "LOOM_DEBUG",
    "value": "false",
    "messages": [{"role": "user", "content": "Hello"}],
    "labels": ["positive", "negative"],
    "schema": {"name": "string"},
    "target_lang": "ar",
    "page_id": "NASA",
    "company": "google",
    "company_name": "google",
    "search_term": "engineer",
    "texts": ["Hello world", "AI safety research"],
    "prompts": ["How are you?"],
    "responses": ["I am fine, thank you."],
    "state": {"key": "value"},
    "dry_run": True,
    "timeout": 30,
    "keywords": ["cybersecurity", "threat"],
    "target_paths": ["/tmp/test"],
    "target_hcs": 9.0,
    "max_attempts": 3,
    "darkness_level": 5,
    "profile": "balanced",
    "location": "dubai",
    "purpose": "for-sale",
    "category": "all",
    "group_url": "https://www.facebook.com/groups/test",
    "page_url": "https://www.facebook.com/NASA",
}


def build_params(tool_name):
    """Build correct params for a tool based on its signature."""
    tool_info = PARAMS_DB.get(tool_name, {})
    params = tool_info.get("parameters", {})

    if not params:
        return PARAM_EXAMPLES.copy()

    result = {}
    for param_name, param_info in params.items():
        if param_name in PARAM_EXAMPLES:
            result[param_name] = PARAM_EXAMPLES[param_name]
        elif "default" in param_info and param_info["default"] is not None:
            continue
        elif param_info.get("type") == "str":
            result[param_name] = "test"
        elif param_info.get("type") == "int":
            result[param_name] = 5
        elif param_info.get("type") == "float":
            result[param_name] = 0.5
        elif param_info.get("type") == "bool":
            result[param_name] = True
        elif param_info.get("type") == "list":
            result[param_name] = ["test"]
    return result


print(f"R17 Smart Audit — {len(PARAMS_DB)} tools with per-tool params")
print("=" * 60)

passed = failed_v = failed_c = failed_t = 0
errors = []

tool_names = sorted(PARAMS_DB.keys())
total = len(tool_names)

for i, name in enumerate(tool_names):
    params = build_params(name)
    try:
        r = requests.post(f"{BASE}/{name}", json=params, timeout=20)
        if r.status_code == 200:
            data = r.json()
            err_type = data.get("error_type", "")
            if err_type:
                err = str(data.get("error", "")).lower()
                if any(x in err for x in [
                    "missing", "required", "must be", "not allowed", "scheme",
                    "invalid", "validation", "extra inputs", "mismatch",
                    "non-empty", "expects", "too short",
                ]):
                    failed_v += 1
                else:
                    failed_c += 1
                    errors.append(f"{name}: {str(data.get('error',''))[:80]}")
            else:
                passed += 1
        elif r.status_code == 404:
            failed_v += 1
        else:
            failed_c += 1
    except requests.exceptions.Timeout:
        failed_t += 1
    except Exception:
        failed_c += 1

    if (i + 1) % 100 == 0:
        pct = 100 * passed / (i + 1)
        print(f"  {i+1}/{total} — {passed} passed ({pct:.0f}%)", flush=True)

total_tested = passed + failed_c + failed_v + failed_t
adj = passed + failed_c + failed_t
print(f"\n{'=' * 60}")
print(f"R17 SMART AUDIT RESULTS")
print(f"{'=' * 60}")
print(f"Total tools:      {total_tested}")
print(f"Passed:           {passed} ({100*passed/total_tested:.1f}%)")
print(f"Validation reject:{failed_v} ({100*failed_v/total_tested:.1f}%)")
print(f"Code bugs:        {failed_c} ({100*failed_c/total_tested:.1f}%)")
print(f"Timeout:          {failed_t} ({100*failed_t/total_tested:.1f}%)")
print(f"Adjusted rate:    {100*passed/adj:.1f}% (excl validation)")
print()

if errors:
    print(f"Code bugs ({len(errors)}):")
    for e in errors[:20]:
        print(f"  {e}")

with open("/opt/loom-v3/ai_actions/r17_audit.json", "w") as f:
    json.dump({
        "passed": passed, "failed_v": failed_v, "failed_c": failed_c,
        "timeout": failed_t, "total": total_tested, "errors": errors,
    }, f, indent=2)
print(f"\nSaved to /opt/loom-v3/ai_actions/r17_audit.json")
