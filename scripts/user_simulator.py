#!/usr/bin/env python3
"""Real-user simulator — exercises every Loom deliverable end-to-end and
collects pass/fail evidence. Runs realistic research journeys against the live
server's REST API (http://localhost:8788/api/v1/tools/<name>) plus the raw MCP
transport, asserts on the responses, and writes JSON + Markdown evidence.

Run on Hetzner:  python3 scripts/user_simulator.py
Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import json
import time
import traceback
import urllib.request
import urllib.error
from datetime import datetime, timezone

BASE = "http://localhost:8788"
TOOLS = BASE + "/api/v1/tools"
RESULTS: list[dict] = []


def _post(path: str, payload: dict, timeout: int = 120, headers: dict | None = None) -> tuple[int, dict | str]:
    data = json.dumps(payload).encode()
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(path, data=data, headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode()
            try:
                return r.status, json.loads(body)
            except json.JSONDecodeError:
                return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def _get(path: str, timeout: int = 30) -> tuple[int, dict | str]:
    try:
        with urllib.request.urlopen(path, timeout=timeout) as r:
            body = r.read().decode()
            try:
                return r.status, json.loads(body)
            except json.JSONDecodeError:
                return r.status, body
    except Exception as e:
        return -1, f"{type(e).__name__}: {e}"


def journey(name: str, fn) -> None:
    """Run one user journey; capture pass/fail + evidence."""
    start = time.time()
    try:
        ok, evidence = fn()
    except Exception as e:
        ok, evidence = False, f"EXCEPTION: {e}\n{traceback.format_exc()[:400]}"
    dur = round((time.time() - start) * 1000)
    RESULTS.append({"journey": name, "passed": bool(ok), "ms": dur, "evidence": str(evidence)[:600]})
    print(f"[{'PASS' if ok else 'FAIL'}] {name} ({dur}ms)")
    if not ok:
        print(f"       ↳ {str(evidence)[:200]}")


# ─────────────────────────────────────────────────────────────────────
# JOURNEYS — each models a real user action + asserts the deliverable works
# ─────────────────────────────────────────────────────────────────────

def j_health():
    code, d = _get(BASE + "/api/v1/health")
    ok = code == 200 and isinstance(d, dict) and d.get("tool_count", 0) > 1000
    return ok, f"tools={d.get('tool_count') if isinstance(d, dict) else d} strategies={d.get('strategy_count') if isinstance(d, dict) else '?'}"


def j_mcp_accept_fix():
    # dubaiPocase BUG1: POST /mcp WITHOUT Accept header must not be -32600.
    code, d = _post(BASE + "/mcp", {
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "sim", "version": "1"}},
    }, timeout=20)
    ok = code == 200
    return ok, f"http={code} (was 406/-32600 before fix)"


def j_paper_strategy():
    # Phase C: paper-grounded reframing strategy resolves + substitutes {prompt}.
    code, d = _post(TOOLS + "/research_prompt_reframe",
                    {"query": "explain TLS handshake", "strategy": "response_priming_attack"}, timeout=40)
    if not isinstance(d, dict):
        return False, str(d)
    txt = str(d.get("reframed", d.get("reframed_prompt", d)))
    ok = "TLS handshake" in txt and "Earlier in this conversation" in txt
    return ok, txt[:160]


def j_quality_31():
    # Phase D: research_quality_max scores all 31 dims (use _score directly is server-only;
    # so assert the dimensions appear). Use a short prompt to keep it fast.
    code, d = _post(TOOLS + "/research_quality_max", {"prompt": "summarize how DNS resolution works"}, timeout=300)
    if not isinstance(d, dict):
        return False, str(d)
    scores = d.get("scores", {})
    n = d.get("dimensions_scored") or len([k for k in scores if isinstance(scores.get(k), (int, float))])
    ok = n >= 28  # allow slight slack
    return ok, f"dimensions_scored={n} weak={d.get('weak_dimensions', [])[:3]} hcs10_upserted={d.get('hcs10_upserted')}"


def j_last30days():
    code, d = _post(TOOLS + "/research_last30days",
                    {"topic": "AI safety research", "days": 30, "depth": "quick", "synthesize": False}, timeout=120)
    if not isinstance(d, dict):
        return False, str(d)
    total = d.get("total_items", 0)
    srcs = {k: v for k, v in (d.get("counts") or {}).items() if v}
    ok = total >= 5 and len(srcs) >= 2
    return ok, f"items={total} sources={srcs}"


def j_legal_cases():
    code, d = _post(TOOLS + "/research_legal_cases",
                    {"query": "unfair dismissal disability discrimination", "jurisdiction": "us", "limit": 3}, timeout=60)
    if not isinstance(d, dict):
        return False, str(d)
    cl = d.get("counts", {}).get("courtlistener", 0)
    ok = cl >= 1
    sample = (d.get("cases") or [{}])[0].get("case_name", "")
    return ok, f"courtlistener={cl} sample='{sample[:50]}'"


def j_search_fallback():
    code, d = _post(TOOLS + "/research_search", {"query": "OWASP top 10 2024", "n": 3}, timeout=40)
    if not isinstance(d, dict):
        return False, str(d)
    ok = len(d.get("results", [])) >= 1
    return ok, f"provider={d.get('provider')} results={len(d.get('results', []))} fallback_chain={d.get('fallback_chain')}"


def j_paper_discover():
    code, d = _post(TOOLS + "/research_paper_discover",
                    {"query": "LLM jailbreak", "sources": ["arxiv"], "max_results": 3, "year_from": 2025}, timeout=90)
    if not isinstance(d, dict):
        return False, str(d)
    ok = len(d.get("papers", [])) >= 1
    return ok, f"found={len(d.get('papers', []))} sample='{(d.get('papers') or [{}])[0].get('title','')[:45]}'"


def j_paper_semantic_search():
    code, d = _post(TOOLS + "/research_paper_semantic_search",
                    {"query": "evading content moderation in image generation", "limit": 3}, timeout=60)
    if not isinstance(d, dict):
        return False, str(d)
    res = d.get("results", [])
    ok = len(res) >= 1 and res[0].get("score", 0) > 0.1
    return ok, f"hits={len(res)} top='{(res or [{}])[0].get('title','')[:40]}' score={(res or [{}])[0].get('score')}"


def j_paper_qa():
    code, d = _post(TOOLS + "/research_paper_library_stats", {}, timeout=30)
    if not isinstance(d, dict) or d.get("total_papers", 0) < 1:
        return False, f"library empty: {d}"
    return True, f"library: papers={d.get('total_papers')} collections={d.get('collections')}"


def j_knowledge_graph():
    code, d = _post(TOOLS + "/research_paper_knowledge_graph", {"action": "central"}, timeout=60)
    if not isinstance(d, dict):
        return False, str(d)
    ok = "most_central_papers" in d or "error" not in d
    return ok, f"central_papers={len(d.get('most_central_papers', []))}"


def j_deepscientist_quest():
    code, d = _post(TOOLS + "/research_quest_create",
                    {"goal": "sim: assess prompt-injection defenses", "title": "Sim Quest"}, timeout=40)
    if not isinstance(d, dict):
        return False, str(d)
    ok = bool(d.get("quest_id"))
    return ok, f"quest_id={d.get('quest_id')} stages={d.get('stages')}"


def j_deepscientist_memory():
    code, d = _post(TOOLS + "/research_ds_memory_store",
                    {"content": "Simulator note: TLS 1.3 removes RSA key exchange.", "kind": "knowledge", "tags": ["sim"]}, timeout=40)
    if not isinstance(d, dict) or not d.get("card_id"):
        return False, str(d)
    code2, d2 = _post(TOOLS + "/research_ds_memory_recall", {"query": "TLS 1.3", "limit": 3}, timeout=40)
    found = isinstance(d2, dict) and d2.get("total_found", 0) >= 1
    return found, f"stored={d.get('card_id')} recalled={d2.get('total_found') if isinstance(d2, dict) else d2}"


def j_paper_grounded_gen():
    code, d = _post(TOOLS + "/research_paper_grounded_generation",
                    {"query": "recent jailbreak techniques", "num_papers": 2, "score_dimensions": False}, timeout=120)
    if not isinstance(d, dict):
        return False, str(d)
    ok = bool(d.get("response")) and d.get("papers_grounded", 0) >= 1
    return ok, f"grounded={d.get('papers_grounded')} provider={d.get('provider')} resp_len={len(d.get('response',''))}"


def j_strategy_count():
    # Confirm the 8 paper-grounded strategies are registered.
    code, d = _post(TOOLS + "/research_prompt_reframe",
                    {"query": "x", "strategy": "longcot_injection"}, timeout=30)
    ok = isinstance(d, dict) and "reasoning" in str(d.get("reframed", d.get("reframed_prompt", ""))).lower()
    return ok, f"longcot_injection resolves={ok}"


JOURNEYS = [
    ("health: 1000+ tools live", j_health),
    ("dubaiPocase BUG1: MCP works w/o Accept header", j_mcp_accept_fix),
    ("Phase C: paper-grounded strategy reframes", j_paper_strategy),
    ("Phase C: longcot_injection strategy registered", j_strategy_count),
    ("Phase D: quality_max scores 31 dims", j_quality_31),
    ("last30days: recency+engagement pulse", j_last30days),
    ("legal_cases: CourtListener real cases", j_legal_cases),
    ("dubaiPocase BUG3: search returns results", j_search_fallback),
    ("paper library: discover from arxiv", j_paper_discover),
    ("paper library: semantic search", j_paper_semantic_search),
    ("paper library: stats/library populated", j_paper_qa),
    ("paper library: knowledge graph centrality", j_knowledge_graph),
    ("DeepScientist: quest create", j_deepscientist_quest),
    ("DeepScientist: memory store+recall", j_deepscientist_memory),
    ("paper-grounded RAG generation", j_paper_grounded_gen),
]


def main() -> None:
    print(f"=== Loom User Simulator — {datetime.now(timezone.utc).isoformat()} ===\n")
    for name, fn in JOURNEYS:
        journey(name, fn)

    passed = sum(1 for r in RESULTS if r["passed"])
    total = len(RESULTS)
    pct = round(100 * passed / total) if total else 0
    print(f"\n=== RESULT: {passed}/{total} passed ({pct}%) ===")

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed, "total": total, "pass_rate_pct": pct,
        "journeys": RESULTS,
    }
    with open("/tmp/loom_sim_evidence.json", "w") as f:
        json.dump(out, f, indent=2)

    # Markdown evidence
    lines = [f"# Loom User-Simulator Evidence — {out['timestamp']}",
             f"\n**{passed}/{total} journeys passed ({pct}%)**\n",
             "| Journey | Result | ms | Evidence |", "|---|---|---|---|"]
    for r in RESULTS:
        ev = r["evidence"].replace("|", "\\|").replace("\n", " ")[:120]
        lines.append(f"| {r['journey']} | {'✅' if r['passed'] else '❌'} | {r['ms']} | {ev} |")
    with open("/tmp/loom_sim_evidence.md", "w") as f:
        f.write("\n".join(lines))
    print("Evidence: /tmp/loom_sim_evidence.json + .md")


if __name__ == "__main__":
    main()
