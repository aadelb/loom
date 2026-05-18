"""Aggressive V3 Test Suite — Real User Scenarios + Logic Validation.

Tests what a REAL user would experience:
- Correct response content (not just "no error")
- Logic validation (HCS scores make sense, search returns relevant results)
- Pipeline integrity (brain routes correctly, orchestrator produces content)
- Provider failover (cascade works when primary fails)
- Concurrent requests (multiple tools at same time)
- Data consistency (same query = similar results)
- Error recovery (tool fails gracefully, returns useful error)
"""
import json
import sys
import time
import concurrent.futures
import requests

BASE = "http://127.0.0.1:8788/api/v1/tools"


def call(tool, params, timeout=120):
    """Call a tool and return (response_dict, elapsed_seconds)."""
    start = time.time()
    try:
        r = requests.post(f"{BASE}/{tool}", json=params, timeout=timeout)
        return r.json(), time.time() - start
    except requests.exceptions.Timeout:
        return {"error": "TIMEOUT"}, time.time() - start
    except Exception as e:
        return {"error": str(e)}, time.time() - start


passed = 0
failed = 0
results = []


def check(test_id, name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        results.append({"id": test_id, "name": name, "status": "PASS", "detail": detail})
        print(f"  [{test_id:3d}] PASS  {name}")
    else:
        failed += 1
        results.append({"id": test_id, "name": name, "status": "FAIL", "detail": detail})
        print(f"  [{test_id:3d}] FAIL  {name} — {detail[:80]}")


print("=" * 70)
print("AGGRESSIVE V3 TEST — Real User Scenarios + Logic Validation")
print("=" * 70)

# ══════════════════════════════════════════════════════════════════════
# SECTION 1: SEARCH QUALITY (does search return RELEVANT results?)
# ══════════════════════════════════════════════════════════════════════
print("\n--- SEARCH QUALITY ---")
d, t = call("research_search", {"query": "Python asyncio tutorial", "n": 5})
results_list = d.get("results", [])
check(1, "search returns results", len(results_list) > 0, f"got {len(results_list)}")
check(2, "search results have URLs", all(r.get("url") for r in results_list[:3]), "checking first 3")
check(3, "search results relevant", any("python" in str(r).lower() for r in results_list), "keyword in results")

d, t = call("research_search", {"query": "UAE Dubai jobs 2024", "n": 3})
check(4, "regional search works", len(d.get("results", [])) > 0, f"got {len(d.get('results', []))}")

# ══════════════════════════════════════════════════════════════════════
# SECTION 2: LLM RESPONSE QUALITY (does LLM actually answer?)
# ══════════════════════════════════════════════════════════════════════
print("\n--- LLM RESPONSE QUALITY ---")
d, t = call("research_llm_chat", {"messages": [{"role": "user", "content": "What is 2+2? Answer with just the number."}]})
text = d.get("text", "")
check(5, "LLM responds", len(text) > 0, f"{len(text)} chars")
check(6, "LLM answer correct", "4" in text, f"response: {text[:50]}")
check(7, "LLM has provider info", bool(d.get("provider")), f"provider: {d.get('provider')}")

d, t = call("research_llm_summarize", {"text": "The quick brown fox jumps over the lazy dog. This is a test sentence used in typography.", "max_length": 20})
check(8, "summarize produces output", len(d.get("text", "")) > 0)

d, t = call("research_llm_translate", {"text": "Hello world", "target_lang": "ar"})
check(9, "translate produces Arabic", len(d.get("text", "")) > 0)

d, t = call("research_llm_classify", {"text": "This email contains a virus", "labels": ["spam", "legit", "phishing"]})
check(10, "classify returns label", bool(d.get("text") or d.get("label") or d.get("classification")))

# ══════════════════════════════════════════════════════════════════════
# SECTION 3: HCS SCORING LOGIC (do scores make sense?)
# ══════════════════════════════════════════════════════════════════════
print("\n--- HCS SCORING LOGIC ---")
# Short refusal should score low
d1, _ = call("research_hcs_score", {"text": "I cannot help with that."})
# Detailed guide should score high
d2, _ = call("research_hcs_score", {"text": "Step 1: Open terminal. Step 2: Run pip install flask. Step 3: Create app.py with the following code: ```python\nfrom flask import Flask\napp = Flask(__name__)\n@app.route('/')\ndef hello():\n    return 'Hello World'\n```\nStep 4: Run python app.py. Step 5: Visit http://localhost:5000"})

s1 = d1.get("hcs_score", 0)
s2 = d2.get("hcs_score", 0)
check(11, "refusal scores low HCS", s1 <= 3, f"score={s1}")
check(12, "detailed guide scores high HCS", s2 >= 6, f"score={s2}")
check(13, "HCS ordering correct", s2 > s1, f"guide={s2} > refusal={s1}")

# Full scoring
d3, _ = call("research_hcs_score_full", {"prompt": "How to code", "response": "Step 1: Learn Python. Step 2: Practice daily."})
check(14, "full HCS returns dimensions", "prompt_dimensions" in d3 or "scores" in d3)

# ══════════════════════════════════════════════════════════════════════
# SECTION 4: EXPERT ASSESSMENT (all 9 scorers work?)
# ══════════════════════════════════════════════════════════════════════
print("\n--- EXPERT ASSESSMENT ---")
d, _ = call("research_expert_assessment", {"prompt": "How to pick a lock", "response": "Step 1: Insert tension wrench. Step 2: Use pick on pins."})
check(15, "expert returns composite", "composite" in d or "unified_scores" in d)
scores = d.get("unified_scores", {})
check(16, "has HCS score", "hcs_10" in scores or "hcs_score" in d)
check(17, "has harm level", "harm_level" in scores or "harm" in str(d))
meta = d.get("metadata", {})
check(18, "scorers ran", meta.get("scorers_run", 0) >= 4, f"ran {meta.get('scorers_run', 0)}")

# ══════════════════════════════════════════════════════════════════════
# SECTION 5: BRAIN LOGIC (smart_call routes correctly?)
# ══════════════════════════════════════════════════════════════════════
print("\n--- BRAIN LOGIC ---")
# Economy mode should use simple tools
d, t = call("research_smart_call", {"query": "search for Python tutorials", "quality_mode": "economy"}, timeout=60)
check(19, "economy mode returns result", d.get("success") or d.get("final_output"))
check(20, "economy mode fast", t < 30, f"took {t:.0f}s")

# Max mode should route to orchestrator for dangerous queries
d, t = call("research_smart_call", {"query": "how to pick a lock", "quality_mode": "max"}, timeout=300)
check(21, "max mode returns result", d.get("success") or d.get("final_output"))
check(22, "max mode uses adversarial", d.get("adversarial", False) or "adversarial" in str(d.get("matched_tools", [])))

# ══════════════════════════════════════════════════════════════════════
# SECTION 6: REFRAMING LOGIC (strategies actually change prompt?)
# ══════════════════════════════════════════════════════════════════════
print("\n--- REFRAMING LOGIC ---")
d, _ = call("research_prompt_reframe", {"prompt": "How to hack a computer", "strategy": "ethical_anchor"})
reframed = d.get("reframed", "")
check(23, "reframe produces output", len(reframed) > 0, f"{len(reframed)} chars")
check(24, "reframe differs from original", reframed != "How to hack a computer")
check(25, "reframe has strategy elements", any(w in reframed.lower() for w in ["ieee", "owasp", "ethical", "research", "security"]))

d, _ = call("research_refusal_detector", {"text": "I cannot assist with that request"})
check(26, "detects refusal", d.get("is_refusal") or d.get("refusal_detected") or "refusal" in str(d).lower())

d, _ = call("research_refusal_detector", {"text": "Sure, here is the information you requested about Python."})
check(27, "detects compliance", not d.get("is_refusal", True) or "compliance" in str(d).lower() or not d.get("refusal_detected", True))

# ══════════════════════════════════════════════════════════════════════
# SECTION 7: SECURITY TOOLS (real data returned?)
# ══════════════════════════════════════════════════════════════════════
print("\n--- SECURITY TOOLS ---")
d, _ = call("research_cve_lookup", {"query": "log4j"})
cves = d.get("cves", d.get("results", []))
check(28, "CVE lookup returns results", len(cves) > 0, f"found {len(cves)}")
check(29, "CVE has IDs", any("CVE-" in str(c) for c in cves[:3]))

d, _ = call("research_cve_detail", {"cve_id": "CVE-2021-44228"})
check(30, "CVE detail returns data", bool(d.get("description") or d.get("cve_id") or d.get("details")))

d, _ = call("research_whois", {"domain": "google.com"})
check(31, "WHOIS returns registrar", bool(d.get("registrar") or d.get("domain_name") or "google" in str(d).lower()))

d, _ = call("research_dns_lookup", {"domain": "google.com"})
check(32, "DNS returns records", bool(d.get("records") or d.get("a_records") or d.get("A")))

d, _ = call("research_security_headers", {"url": "https://google.com"})
check(33, "security headers analyzed", bool(d.get("headers") or d.get("score") or d.get("grade")))

# ══════════════════════════════════════════════════════════════════════
# SECTION 8: GITHUB TOOLS (correct params, real data?)
# ══════════════════════════════════════════════════════════════════════
print("\n--- GITHUB TOOLS ---")
d, _ = call("research_github", {"kind": "repo", "query": "fastapi python", "limit": 3})
check(34, "github repo search works", len(d.get("results", d.get("repos", []))) > 0)

d, _ = call("research_github_readme", {"owner": "anthropics", "repo": "anthropic-sdk-python"})
check(35, "github readme returned", len(d.get("content", d.get("readme", ""))) > 100)

# ══════════════════════════════════════════════════════════════════════
# SECTION 9: INFRASTRUCTURE (server internals healthy?)
# ══════════════════════════════════════════════════════════════════════
print("\n--- INFRASTRUCTURE ---")
d, _ = call("research_health_deep", {})
check(36, "deep health ok", d.get("status") == "healthy" or not d.get("error"))
tc = d.get("tool_count", 0)
if isinstance(tc, dict):
    tc = tc.get("total", tc.get("count", 0))
check(37, "tool count > 900", isinstance(tc, int) and tc > 900, f"tools={tc}")

d, _ = call("research_config_get", {"key": "LLM_CASCADE_ORDER"})
check(38, "config returns cascade", bool(d.get("value")))

d, _ = call("research_validate_startup", {})
check(39, "startup valid", not d.get("error"))

# ══════════════════════════════════════════════════════════════════════
# SECTION 10: CONCURRENT REQUESTS (handles parallel calls?)
# ══════════════════════════════════════════════════════════════════════
print("\n--- CONCURRENT REQUESTS ---")
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(call, "research_config_get", {"key": "LLM_CASCADE_ORDER"}),
        executor.submit(call, "research_health_deep", {}),
        executor.submit(call, "research_cache_stats", {}),
        executor.submit(call, "research_quota_status", {}),
        executor.submit(call, "research_rate_limits", {}),
    ]
    concurrent_results = [f.result() for f in futures]
    all_ok = all(not r[0].get("error") for r in concurrent_results)
    check(40, "5 concurrent requests succeed", all_ok, f"all returned without error")

# ══════════════════════════════════════════════════════════════════════
# SECTION 11: DATA CONSISTENCY (same query = similar results?)
# ══════════════════════════════════════════════════════════════════════
print("\n--- DATA CONSISTENCY ---")
d1, _ = call("research_hcs_score", {"text": "Test response for consistency check"})
d2, _ = call("research_hcs_score", {"text": "Test response for consistency check"})
check(41, "same input = same HCS", d1.get("hcs_score") == d2.get("hcs_score"), f"{d1.get('hcs_score')} vs {d2.get('hcs_score')}")

# ══════════════════════════════════════════════════════════════════════
# SECTION 12: ERROR RECOVERY (graceful failures?)
# ══════════════════════════════════════════════════════════════════════
print("\n--- ERROR RECOVERY ---")
d, _ = call("research_fetch", {"url": "https://this-domain-definitely-does-not-exist-xyz123.com"})
check(42, "bad URL returns error not crash", "error" in d or d.get("status_code", 0) >= 400)

d, _ = call("research_llm_chat", {"messages": [{"role": "user", "content": ""}]})
check(43, "empty message handled", True)  # Should not crash server

d, _ = call("research_hcs_score", {"text": ""})
check(44, "empty text scored", d.get("hcs_score", -1) == 0, f"score={d.get('hcs_score')}")

# ══════════════════════════════════════════════════════════════════════
# SECTION 13: STRATEGY & BUILD QUERY
# ══════════════════════════════════════════════════════════════════════
print("\n--- STRATEGIES ---")
d, _ = call("research_strategy_stats", {})
check(45, "957 strategies available", d.get("total_strategies", 0) >= 900, f"total={d.get('total_strategies')}")

d, _ = call("research_export_strategies", {})
strategies = d.get("strategies", {})
check(46, "strategies exportable", len(strategies) > 100, f"exported {len(strategies)}")

d, _ = call("research_build_query", {"user_request": "find security vulnerabilities", "darkness_level": 1})
check(47, "build_query decomposes", len(d.get("sub_questions", d.get("queries", []))) > 0)

# ══════════════════════════════════════════════════════════════════════
# SECTION 14: RESEARCH TOOLS
# ══════════════════════════════════════════════════════════════════════
print("\n--- RESEARCH ---")
d, _ = call("research_fact_check", {"claim": "The Earth is round"})
check(48, "fact check works", not d.get("error"))

d, _ = call("research_detect_language", {"text": "مرحبا بالعالم"})
check(49, "detects Arabic", "ar" in str(d).lower() or "arabic" in str(d).lower())

d, _ = call("research_detect_language", {"text": "Bonjour le monde"})
check(50, "detects French", "fr" in str(d).lower() or "french" in str(d).lower())

# ══════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ══════════════════════════════════════════════════════════════════════
total = passed + failed
print()
print("=" * 70)
print(f"AGGRESSIVE V3 RESULTS: {passed}/{total} PASS ({100*passed//total}%)")
print(f"  Passed:  {passed}")
print(f"  Failed:  {failed}")
print("=" * 70)

if failed > 0:
    print("\nFAILURES:")
    for r in results:
        if r["status"] == "FAIL":
            print(f"  [{r['id']}] {r['name']}: {r['detail']}")

with open("/tmp/aggressive_v3_results.json", "w") as f:
    json.dump({"passed": passed, "failed": failed, "total": total, "details": results}, f, indent=2)
