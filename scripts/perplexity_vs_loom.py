"""Perplexity vs Loom — Quality Comparison Test.

For each query, sends to BOTH Perplexity API and Loom, then compares:
- Response length (information density)
- Key facts present (accuracy)
- Source citations (verifiability)
- Response time (speed)

Requires: PERPLEXITY_API_KEY env var (from https://www.perplexity.ai/settings/api)
Perplexity API: https://docs.perplexity.ai/reference/post_chat_completions
"""
import json
import os
import sys
import time

import requests

PPLX_KEY = os.environ.get("PERPLEXITY_API_KEY", "")
PPLX_URL = "https://api.perplexity.ai/chat/completions"
LOOM_URL = "http://127.0.0.1:8788/api/v1/tools"

# Queries that test KNOWLEDGE QUALITY (facts, accuracy, sources)
QUERIES = [
    {
        "query": "What is the EU AI Act and when does it take effect?",
        "loom_tool": "research_search",
        "loom_params": {"query": "EU AI Act when takes effect", "n": 5},
        "keywords": ["EU AI Act", "2024", "2025", "regulation", "risk"],
    },
    {
        "query": "What are the latest CVEs for Log4j?",
        "loom_tool": "research_cve_lookup",
        "loom_params": {"query": "log4j"},
        "keywords": ["CVE-2021-44228", "log4j", "critical"],
    },
    {
        "query": "What is the current Bitcoin price and market cap?",
        "loom_tool": "research_search",
        "loom_params": {"query": "Bitcoin current price market cap 2024", "n": 3},
        "keywords": ["bitcoin", "price", "market"],
    },
    {
        "query": "Explain Python asyncio in simple terms",
        "loom_tool": "research_llm_chat",
        "loom_params": {"messages": [{"role": "user", "content": "Explain Python asyncio in simple terms"}]},
        "keywords": ["async", "await", "event loop", "coroutine"],
    },
    {
        "query": "What is OWASP Top 10 2024?",
        "loom_tool": "research_search",
        "loom_params": {"query": "OWASP Top 10 2024 vulnerabilities list", "n": 5},
        "keywords": ["injection", "authentication", "OWASP", "security"],
    },
    {
        "query": "Who is the CEO of Anthropic?",
        "loom_tool": "research_search",
        "loom_params": {"query": "CEO of Anthropic", "n": 3},
        "keywords": ["Dario", "Amodei", "Anthropic"],
    },
    {
        "query": "What is the population of Dubai?",
        "loom_tool": "research_search",
        "loom_params": {"query": "population of Dubai 2024", "n": 3},
        "keywords": ["million", "Dubai", "population"],
    },
    {
        "query": "Latest FastAPI version and features",
        "loom_tool": "research_search",
        "loom_params": {"query": "FastAPI latest version features 2024", "n": 3},
        "keywords": ["FastAPI", "version", "Python"],
    },
    {
        "query": "What is prompt injection in LLMs?",
        "loom_tool": "research_llm_chat",
        "loom_params": {"messages": [{"role": "user", "content": "What is prompt injection in LLMs? Be brief."}]},
        "keywords": ["prompt", "injection", "LLM", "attack", "safety"],
    },
    {
        "query": "How many tools does Loom MCP server have?",
        "loom_tool": "research_health_deep",
        "loom_params": {},
        "keywords": ["tool", "908", "healthy"],
    },
]


def query_perplexity(query):
    """Call Perplexity API."""
    if not PPLX_KEY:
        return {"text": "", "error": "No PERPLEXITY_API_KEY", "time": 0}
    start = time.time()
    try:
        r = requests.post(PPLX_URL, json={
            "model": "sonar",
            "messages": [{"role": "user", "content": query}],
            "max_tokens": 500,
        }, headers={"Authorization": f"Bearer {PPLX_KEY}"}, timeout=30)
        d = r.json()
        text = d.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = d.get("citations", [])
        return {"text": text, "citations": citations, "time": time.time() - start}
    except Exception as e:
        return {"text": "", "error": str(e), "time": time.time() - start}


def query_loom(tool, params):
    """Call Loom tool."""
    start = time.time()
    try:
        r = requests.post(f"{LOOM_URL}/{tool}", json=params, timeout=60)
        d = r.json()
        # Extract text from various response formats
        text = d.get("text", "")
        if not text:
            results = d.get("results", [])
            if results:
                text = json.dumps(results[:3], indent=2, default=str)
            else:
                text = json.dumps(d, indent=2, default=str)[:1000]
        return {"text": text, "raw": d, "time": time.time() - start}
    except Exception as e:
        return {"text": "", "error": str(e), "time": time.time() - start}


def score_keywords(text, keywords):
    """Count how many expected keywords are in the response."""
    text_lower = text.lower()
    found = [k for k in keywords if k.lower() in text_lower]
    return len(found), len(keywords), found


def main():
    print("=" * 70)
    print("PERPLEXITY vs LOOM — Quality Comparison")
    print("=" * 70)

    if not PPLX_KEY:
        print("\nWARNING: No PERPLEXITY_API_KEY set. Running Loom-only mode.")
        print("Set: export PERPLEXITY_API_KEY=pplx-xxx")

    comparisons = []

    for i, q in enumerate(QUERIES, 1):
        print(f"\n--- Query {i}/{len(QUERIES)}: {q['query'][:60]} ---")

        # Query Perplexity
        pplx = query_perplexity(q["query"])

        # Query Loom
        loom = query_loom(q["loom_tool"], q["loom_params"])

        # Score both
        pplx_kw_found, pplx_kw_total, pplx_kw = score_keywords(pplx["text"], q["keywords"])
        loom_kw_found, loom_kw_total, loom_kw = score_keywords(loom["text"], q["keywords"])

        comp = {
            "query": q["query"],
            "perplexity": {
                "length": len(pplx["text"]),
                "keywords": f"{pplx_kw_found}/{pplx_kw_total}",
                "time": round(pplx.get("time", 0), 1),
                "citations": len(pplx.get("citations", [])),
            },
            "loom": {
                "tool": q["loom_tool"],
                "length": len(loom["text"]),
                "keywords": f"{loom_kw_found}/{loom_kw_total}",
                "time": round(loom.get("time", 0), 1),
            },
            "winner": "perplexity" if pplx_kw_found > loom_kw_found else ("loom" if loom_kw_found > pplx_kw_found else "tie"),
        }
        comparisons.append(comp)

        print(f"  Perplexity: {len(pplx['text'])} chars, {pplx_kw_found}/{pplx_kw_total} keywords, {pplx.get('time', 0):.1f}s")
        print(f"  Loom:       {len(loom['text'])} chars, {loom_kw_found}/{loom_kw_total} keywords, {loom.get('time', 0):.1f}s")
        print(f"  Winner:     {comp['winner'].upper()}")

    # Summary
    pplx_wins = sum(1 for c in comparisons if c["winner"] == "perplexity")
    loom_wins = sum(1 for c in comparisons if c["winner"] == "loom")
    ties = sum(1 for c in comparisons if c["winner"] == "tie")

    print()
    print("=" * 70)
    print(f"RESULTS: Perplexity {pplx_wins} — Loom {loom_wins} — Tie {ties}")
    print("=" * 70)

    with open("/tmp/perplexity_vs_loom.json", "w") as f:
        json.dump(comparisons, f, indent=2, default=str)
    print(f"Details saved to /tmp/perplexity_vs_loom.json")


if __name__ == "__main__":
    main()
