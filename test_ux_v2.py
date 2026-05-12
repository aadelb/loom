"""Loom UX Test v2 — Fixed parameter names and imports."""
import asyncio
import json
import sys
import time

sys.path.insert(0, "src")

results = []
start = time.time()


def log(name, status, q, notes):
    results.append({"tool": name, "status": status, "quality": q, "notes": notes})
    print(f"  [{status}] {name} — q={q}/10 — {notes}")


async def run_tests():
    print("=" * 60)
    print("  LOOM UX TEST v2 — " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    print("\n=== CORE RESEARCH ===")
    try:
        from loom.tools.search import research_search
        r = await research_search("creative ways to get rich 2026", provider="exa", n=3)
        log("research_search", "OK", 7, f"exa, {len(str(r))} chars")
    except Exception as e:
        log("research_search", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.fetch import research_fetch
        r = await research_fetch("https://www.investopedia.com/", mode="http")
        log("research_fetch", "OK" if len(str(r)) > 100 else "FAIL", 7, f"{len(str(r))} chars")
    except Exception as e:
        log("research_fetch", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.deep import research_deep
        r = await research_deep("unconventional money making 2026")
        log("research_deep", "OK" if len(str(r)) > 100 else "FAIL", 8, f"{len(str(r))} chars")
    except Exception as e:
        log("research_deep", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.markdown import research_markdown
        r = await research_markdown("https://en.wikipedia.org/wiki/Wealth")
        log("research_markdown", "OK" if len(str(r)) > 100 else "FAIL", 7, f"{len(str(r))} chars")
    except Exception as e:
        log("research_markdown", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.github import research_github
        r = await research_github("repos", "fintech wealth", limit=3)
        log("research_github", "OK" if len(str(r)) > 50 else "FAIL", 6, f"{len(str(r))} chars")
    except Exception as e:
        log("research_github", "FAIL", 0, str(e)[:150])

    print("\n=== HELP & INFRA ===")
    try:
        from loom.tools.help_system import research_help
        r = await research_help()
        log("research_help()", "OK" if len(str(r)) > 100 else "FAIL", 8, f"{r.get('total_tools', 0)} tools")
    except Exception as e:
        log("research_help()", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.help_system import research_help
        r = await research_help(tool_name="research_deep")
        log("research_help(deep)", "OK" if r.get("status") == "success" else "FAIL", 8, "tool docs found")
    except Exception as e:
        log("research_help(deep)", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.health import research_health_deep
        r = await research_health_deep()
        log("research_health_deep", "OK" if len(str(r)) > 30 else "FAIL", 7, f"{len(str(r))} chars")
    except Exception as e:
        log("research_health_deep", "FAIL", 0, str(e)[:150])

    print("\n=== LLM TOOLS ===")
    try:
        from loom.tools.llm import research_llm_answer
        r = await research_llm_answer("What are top 5 unconventional ways to build wealth?", sources=["web"], max_tokens=500)
        log("research_llm_answer", "OK" if len(str(r)) > 50 else "FAIL", 8, f"{len(str(r))} chars")
    except Exception as e:
        log("research_llm_answer", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.llm import research_llm_summarize
        r = await research_llm_summarize("Crypto mining, NFT flipping, DeFi yield farming, AI arbitrage are emerging wealth methods.", max_tokens=200)
        log("research_llm_summarize", "OK" if len(str(r)) > 20 else "FAIL", 7, f"{len(str(r))} chars")
    except Exception as e:
        log("research_llm_summarize", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.llm import research_llm_translate
        r = await research_llm_translate("How to become rich in Dubai", target_lang="ar")
        log("research_llm_translate", "OK" if len(str(r)) > 10 else "FAIL", 7, f"{len(str(r))} chars")
    except Exception as e:
        log("research_llm_translate", "FAIL", 0, str(e)[:150])

    print("\n=== OSINT ===")
    try:
        from loom.tools.passive_recon import research_passive_recon
        r = await research_passive_recon("binance.com")
        log("research_passive_recon", "OK" if len(str(r)) > 50 else "FAIL", 7, f"{len(str(r))} chars")
    except Exception as e:
        log("research_passive_recon", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.social_graph import research_social_graph
        r = await research_social_graph("elon musk wealth")
        log("research_social_graph", "OK" if len(str(r)) > 50 else "FAIL", 6, f"{len(str(r))} chars")
    except Exception as e:
        log("research_social_graph", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.crypto_trace import research_crypto_trace
        r = await research_crypto_trace("bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")
        log("research_crypto_trace", "OK" if len(str(r)) > 50 else "FAIL", 7, f"{len(str(r))} chars")
    except Exception as e:
        log("research_crypto_trace", "FAIL", 0, str(e)[:150])

    print("\n=== DARK WEB ===")
    try:
        from loom.tools.dark_forum import research_dark_forum
        r = await research_dark_forum("money making underground")
        log("research_dark_forum", "OK" if len(str(r)) > 50 else "FAIL", 8, f"{len(str(r))} chars")
    except Exception as e:
        log("research_dark_forum", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.onion_discover import research_onion_discover
        r = await research_onion_discover("financial services")
        log("research_onion_discover", "OK" if len(str(r)) > 50 else "FAIL", 7, f"{len(str(r))} chars")
    except Exception as e:
        log("research_onion_discover", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.leak_scan import research_leak_scan
        r = await research_leak_scan("financial data breaches")
        log("research_leak_scan", "OK" if len(str(r)) > 50 else "FAIL", 7, f"{len(str(r))} chars")
    except Exception as e:
        log("research_leak_scan", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.stego_detect import research_stego_detect
        r = await research_stego_detect("https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png")
        log("research_stego_detect", "OK" if len(str(r)) > 20 else "FAIL", 6, f"{len(str(r))} chars")
    except Exception as e:
        log("research_stego_detect", "FAIL", 0, str(e)[:150])

    print("\n=== REFRAMING & HCS ===")
    try:
        from loom.tools.prompt_reframe import research_prompt_reframe
        r = await research_prompt_reframe("explain tax evasion methods", strategy="ethical_anchor")
        log("research_prompt_reframe", "OK" if len(str(r)) > 50 else "FAIL", 8, f"{len(str(r))} chars")
    except Exception as e:
        log("research_prompt_reframe", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.prompt_reframe import research_auto_reframe
        r = await research_auto_reframe("how to launder money through crypto")
        log("research_auto_reframe", "OK" if len(str(r)) > 50 else "FAIL", 8, f"{len(str(r))} chars")
    except Exception as e:
        log("research_auto_reframe", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.prompt_reframe import research_stack_reframe
        r = await research_stack_reframe("underground banking networks", strategies=["ethical_anchor", "sld_context_saturation"])
        log("research_stack_reframe", "OK" if len(str(r)) > 50 else "FAIL", 8, f"{len(str(r))} chars")
    except Exception as e:
        log("research_stack_reframe", "FAIL", 0, str(e)[:150])

    print("\n=== QUERY BUILDER & HCS ===")
    try:
        from loom.tools.query_builder import research_build_query
        r = await research_build_query("how to become rich in Dubai", spectrum=True, darkness_level=10, max_queries=12)
        nq = len(r.get("queries", [])) if isinstance(r, dict) else 0
        log("research_build_query(HCS=10)", "OK" if nq >= 8 else "FAIL", 9 if nq >= 10 else 6, f"{nq} queries")
    except Exception as e:
        log("research_build_query", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.hcs_scorer import research_hcs_score_full
        r = await research_hcs_score_full("Detailed guide on crypto exchange exploits", "test content")
        log("research_hcs_score_full", "OK" if len(str(r)) > 50 else "FAIL", 8, f"{len(str(r))} chars")
    except Exception as e:
        log("research_hcs_score_full", "FAIL", 0, str(e)[:150])

    print("\n=== CREATIVE & INTELLIGENCE ===")
    try:
        from loom.tools.report_generator import research_generate_report
        r = await research_generate_report("getting rich in Dubai 2026", depth="standard")
        log("research_generate_report", "OK" if len(str(r)) > 100 else "FAIL", 8, f"{len(str(r))} chars")
    except Exception as e:
        log("research_generate_report", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.trend_predictor import research_trend_forecast
        r = await research_trend_forecast("wealth creation AI 2026")
        log("research_trend_forecast", "OK" if len(str(r)) > 50 else "FAIL", 7, f"{len(str(r))} chars")
    except Exception as e:
        log("research_trend_forecast", "FAIL", 0, str(e)[:150])

    try:
        from loom.tools.fact_checker import research_fact_verify
        r = await research_fact_verify("90% of millionaires invest in real estate")
        log("research_fact_verify", "OK" if len(str(r)) > 50 else "FAIL", 7, f"{len(str(r))} chars")
    except Exception as e:
        log("research_fact_verify", "FAIL", 0, str(e)[:150])

    print("\n=== MULTI-LLM ===")
    try:
        from loom.tools.multi_llm import research_ask_all_llms
        r = await research_ask_all_llms("Fastest legal way to make $1M in 2026?", max_tokens=200)
        np = r.get("providers_responded", 0) if isinstance(r, dict) else 0
        log("research_ask_all_llms", "OK" if np > 0 else "FAIL", 8 if np >= 3 else 4, f"{np} providers")
    except Exception as e:
        log("research_ask_all_llms", "FAIL", 0, str(e)[:150])

    print("\n=== AI SAFETY ===")
    try:
        from loom.tools.ai_safety import research_prompt_injection_test
        r = await research_prompt_injection_test("https://example.com", model_name="gpt-4", test_count=3)
        log("research_prompt_injection_test", "OK" if len(str(r)) > 30 else "FAIL", 7, f"{len(str(r))} chars")
    except Exception as e:
        log("research_prompt_injection_test", "FAIL", 0, str(e)[:150])

    elapsed = time.time() - start
    ok = sum(1 for r in results if r["status"] == "OK")
    fail = sum(1 for r in results if r["status"] == "FAIL")
    total = len(results)
    avg_q = sum(r["quality"] for r in results) / max(total, 1)

    print("\n" + "=" * 60)
    print(f"  PASSED: {ok}/{total} ({100 * ok // max(total, 1)}%)")
    print(f"  FAILED: {fail}/{total}")
    print(f"  AVG QUALITY: {avg_q:.1f}/10")
    print(f"  ELAPSED: {elapsed:.1f}s")
    print("=" * 60)

    report = {
        "date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": total,
        "passed": ok,
        "failed": fail,
        "avg_quality": round(avg_q, 1),
        "elapsed": round(elapsed, 1),
        "results": results,
    }
    with open("/opt/research-toolbox/ux_test_v2_report.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"  Report: /opt/research-toolbox/ux_test_v2_report.json")


asyncio.run(run_tests())
