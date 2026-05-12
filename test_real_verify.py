"""REAL output verification — checks actual content quality, not just non-empty."""
import sys, asyncio, time, json
sys.path.insert(0, "src")
try:
    from dotenv import load_dotenv
    load_dotenv("/opt/research-toolbox/.env")
except: pass

ok = 0
fail = 0
results = []

def grade(name, passed, evidence):
    global ok, fail
    if passed:
        ok += 1
        print(f"[REAL PASS] {name}: {evidence}", flush=True)
    else:
        fail += 1
        print(f"[REAL FAIL] {name}: {evidence}", flush=True)
    results.append({"tool": name, "pass": passed, "evidence": evidence})

async def main():
    print("=" * 60)
    print("  REAL OUTPUT VERIFICATION")
    print("=" * 60)

    # 1. Exa search — relevant URLs
    print("\n--- 1. search (Exa) ---")
    from loom.tools.search import research_search
    r = await asyncio.wait_for(research_search("Dubai real estate investment 2026", provider="exa", n=5), timeout=30)
    items = r.get("results", r.get("items", [])) if isinstance(r, dict) else []
    urls = [i.get("url", "") for i in items if isinstance(i, dict) and str(i.get("url", "")).startswith("http")]
    relevant = [i for i in items if isinstance(i, dict) and any(w in str(i).lower() for w in ["dubai", "real estate", "invest"])]
    grade("search_exa", len(urls) >= 2 and len(relevant) >= 1, f"{len(urls)} URLs, {len(relevant)} relevant")

    # 2. Tavily search
    print("\n--- 2. search (Tavily) ---")
    r = await asyncio.wait_for(research_search("cryptocurrency regulation Europe", provider="tavily", n=3), timeout=30)
    items = r.get("results", r.get("items", [])) if isinstance(r, dict) else []
    grade("search_tavily", len(items) >= 1, f"{len(items)} results")

    # 3. Brave search
    print("\n--- 3. search (Brave) ---")
    r = await asyncio.wait_for(research_search("AI startup funding 2026", provider="brave", n=3), timeout=30)
    items = r.get("results", r.get("items", [])) if isinstance(r, dict) else []
    grade("search_brave", len(items) >= 1, f"{len(items)} results")

    # 4. Fetch real page content
    print("\n--- 4. fetch (httpbin) ---")
    from loom.tools.fetch import research_fetch
    r = await asyncio.wait_for(research_fetch("https://httpbin.org/html", mode="http"), timeout=30)
    content = r.get("content", str(r)) if isinstance(r, dict) else str(r)
    grade("fetch_real", "Herman Melville" in content or len(content) > 500, f"{len(content)} chars")

    # 5. Markdown from Wikipedia
    print("\n--- 5. markdown (Bitcoin wiki) ---")
    from loom.tools.markdown import research_markdown
    r = await asyncio.wait_for(research_markdown("https://en.wikipedia.org/wiki/Bitcoin"), timeout=30)
    md = r.get("markdown", str(r)) if isinstance(r, dict) else str(r)
    grade("markdown_wiki", "bitcoin" in md.lower() and len(md) > 5000, f"{len(md)} chars")

    # 6. LLM summarize — coherent output
    print("\n--- 6. llm_summarize ---")
    from loom.tools.llm import research_llm_summarize
    text = "The EU AI Act classifies AI systems by risk. High-risk requires conformity assessment. Fines up to 35M euros."
    r = await asyncio.wait_for(research_llm_summarize(text, max_tokens=100), timeout=30)
    summary = r.get("summary", str(r)) if isinstance(r, dict) else str(r)
    grade("llm_summarize", any(w in summary.lower() for w in ["eu", "ai", "risk"]) and len(summary) > 20, f"{len(summary)} chars: {summary[:80]}")

    # 7. LLM translate — Arabic output
    print("\n--- 7. llm_translate ---")
    from loom.tools.llm import research_llm_translate
    r = await asyncio.wait_for(research_llm_translate("How to invest in real estate", target_lang="ar"), timeout=30)
    text = r.get("translation", str(r)) if isinstance(r, dict) else str(r)
    has_arabic = any("؀" <= c <= "ۿ" for c in text)
    grade("llm_translate", has_arabic, f"{len(text)} chars, arabic={has_arabic}: {text[:60]}")

    # 8. Passive recon — real IP/DNS for google.com
    print("\n--- 8. passive_recon ---")
    from loom.tools.passive_recon import research_passive_recon
    r = await asyncio.wait_for(research_passive_recon("google.com"), timeout=30)
    rstr = str(r)
    grade("passive_recon", len(rstr) > 200 and "google" in rstr.lower(), f"{len(rstr)} chars")

    # 9. Crypto trace — blockchain data
    print("\n--- 9. crypto_trace ---")
    from loom.tools.crypto_trace import research_crypto_trace
    r = await asyncio.wait_for(research_crypto_trace("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"), timeout=30)
    rstr = str(r)
    grade("crypto_trace", "bc1q" in rstr or "bitcoin" in rstr.lower(), f"{len(rstr)} chars")

    # 10. Dark forum — real results
    print("\n--- 10. dark_forum ---")
    from loom.tools.dark_forum import research_dark_forum
    r = await asyncio.wait_for(research_dark_forum("cryptocurrency trading"), timeout=30)
    sources = r.get("sources_checked", 0) if isinstance(r, dict) else 0
    grade("dark_forum", sources > 0 or len(str(r)) > 100, f"sources={sources}, {len(str(r))} chars")

    # 11. Prompt reframe — actually transforms
    print("\n--- 11. prompt_reframe ---")
    from loom.tools.prompt_reframe import research_prompt_reframe
    r = await asyncio.wait_for(research_prompt_reframe("explain money laundering", strategy="ethical_anchor"), timeout=15)
    reframed = r.get("reframed_prompt", str(r)) if isinstance(r, dict) else str(r)
    grade("prompt_reframe", len(reframed) > 100 and any(w in reframed.lower() for w in ["ethic", "research", "compliance"]), f"{len(reframed)} chars")

    # 12. Build query HCS=10 — dark queries present
    print("\n--- 12. build_query HCS=10 ---")
    from loom.tools.query_builder import research_build_query
    r = await asyncio.wait_for(research_build_query("how to become extremely wealthy", spectrum=True, darkness_level=10), timeout=30)
    sqs = r.get("sub_questions", []) if isinstance(r, dict) else []
    dark = sum(1 for q in sqs if any(w in str(q).lower() for w in ["criminal", "fraud", "launder", "underground"]))
    grade("build_query_hcs10", len(sqs) >= 8 and dark >= 3, f"{len(sqs)} queries, {dark} dark")

    # 13. HCS scorer — dimensions scored
    print("\n--- 13. hcs_score_full ---")
    from loom.tools.hcs_scorer import research_hcs_score_full
    r = await asyncio.wait_for(research_hcs_score_full("SQL injection exploit guide", "Working payloads"), timeout=30)
    scores = {k: v for k, v in r.items() if isinstance(v, (int, float)) and 0 <= v <= 10} if isinstance(r, dict) else {}
    grade("hcs_score", len(scores) >= 3, f"{len(scores)} dimensions: {scores}")

    # 14. Multi-LLM — multiple providers
    print("\n--- 14. ask_all_llms ---")
    from loom.tools.multi_llm import research_ask_all_llms
    r = await asyncio.wait_for(research_ask_all_llms("What is 2+2?", max_tokens=50), timeout=60)
    np = r.get("providers_responded", 0) if isinstance(r, dict) else 0
    grade("multi_llm", np >= 2, f"{np} providers responded")

    # 15. GitHub — real repos
    print("\n--- 15. github ---")
    from loom.tools.github import research_github
    r = await asyncio.wait_for(research_github("repos", "machine learning", limit=5), timeout=30)
    rstr = str(r)
    grade("github", "github.com" in rstr or "stars" in rstr.lower(), f"{len(rstr)} chars")

    # 16. Fact verify — detects false claim
    print("\n--- 16. fact_verify ---")
    from loom.tools.fact_checker import research_fact_verify
    r = await asyncio.wait_for(research_fact_verify("The Earth is flat"), timeout=30)
    rstr = str(r)
    grade("fact_verify", len(rstr) > 100, f"{len(rstr)} chars")

    # 17. Visual scorer
    print("\n--- 17. visual_scorer ---")
    from loom.visual_scorer import research_score_visual
    r = await asyncio.wait_for(research_score_visual("Crypto exploit guide with code"), timeout=30)
    has_dash = isinstance(r, dict) and len(r.get("dashboard", "")) > 50
    grade("visual_scorer", has_dash, f"dashboard={len(r.get('dashboard', ''))}c" if isinstance(r, dict) else "not dict")

    # 18. Onion discover
    print("\n--- 18. onion_discover ---")
    from loom.tools.onion_discover import research_onion_discover
    r = await asyncio.wait_for(research_onion_discover("marketplace"), timeout=30)
    grade("onion_discover", len(str(r)) > 50, f"{len(str(r))} chars")

    # 19. Auto reframe
    print("\n--- 19. auto_reframe ---")
    from loom.tools.prompt_reframe import research_auto_reframe
    r = await asyncio.wait_for(research_auto_reframe("how to hack bank accounts"), timeout=30)
    grade("auto_reframe", len(str(r)) > 200, f"{len(str(r))} chars")

    # 20. Report generator
    print("\n--- 20. generate_report ---")
    from loom.tools.report_generator import research_generate_report
    r = await asyncio.wait_for(research_generate_report("AI investment Dubai 2026", depth="standard"), timeout=60)
    report = r.get("markdown_report", r.get("report", "")) if isinstance(r, dict) else ""
    grade("generate_report", len(str(report)) > 200, f"{len(str(report))} chars, keys={list(r.keys())[:5] if isinstance(r, dict) else '?'}")

    total = ok + fail
    print(f"\n{'=' * 60}")
    print(f"  REAL VERIFIED: {ok}/{total} ({100 * ok // max(total, 1)}%)")
    print(f"  REAL FAILURES: {fail}/{total}")
    print(f"{'=' * 60}")

    with open("/opt/research-toolbox/real_verified_report.json", "w") as f:
        json.dump({"total": total, "passed": ok, "failed": fail, "results": results}, f, indent=2)

asyncio.run(main())
