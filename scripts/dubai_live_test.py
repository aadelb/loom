#!/usr/bin/env python3
"""
Live test: 'How to become rich in Dubai' through full intelligence pipeline.
Demonstrates: query building, search, HCS scoring, deep research, and strategy reframing.
"""
import sys, asyncio, json, time
sys.path.insert(0, "/opt/research-toolbox/src")

async def main():
    results = {}
    query = "how to become rich in Dubai"
    start_time = time.time()

    print(f"Query: {query}")
    print("=" * 70)

    # Step 1: Build query with spectrum analysis
    try:
        from loom.tools.query_builder import research_build_query
        r = research_build_query(query, spectrum=True, darkness_level=5)
        sub_qs = r.get("sub_questions", [])
        results["build_query"] = {
            "status": "ok",
            "sub_questions": len(sub_qs),
            "questions": sub_qs[:3] if sub_qs else []
        }
        print(f"\n1. QUERY BUILDING (spectrum analysis + darkness level 5)")
        print(f"   Generated {len(sub_qs)} sub-questions:")
        for i, q in enumerate(sub_qs[:3], 1):
            print(f"   [{i}] {q}")
    except Exception as e:
        results["build_query"] = {"status": f"error: {e}"}
        print(f"\n1. QUERY BUILDING: ERROR {e}")

    # Step 2: Search across providers
    try:
        from loom.tools.search import research_search
        print(f"\n2. MULTI-PROVIDER SEARCH")
        r = await research_search(query=query, n=10)
        search_results = r.get("results", []) if isinstance(r, dict) else []
        results["search"] = {
            "status": "ok",
            "results_count": len(search_results),
            "providers": r.get("providers", []),
            "sample_titles": [res.get("title", "")[:80] for res in search_results[:3]]
        }
        providers = r.get("providers", [])
        print(f"   Providers queried: {', '.join(providers) if providers else 'None available'}")
        print(f"   Results found: {len(search_results)}")
        if search_results:
            for i, res in enumerate(search_results[:3], 1):
                print(f"   [{i}] {res.get('title', 'N/A')[:70]}")
                print(f"       Source: {res.get('source', 'N/A')[:50]}")
    except Exception as e:
        results["search"] = {"status": f"error: {e}"}
        print(f"\n2. MULTI-PROVIDER SEARCH: ERROR {e}")

    # Step 3: HCS Scoring (Harmful Content Score)
    try:
        from loom.tools.hcs_multi_scorer import research_hcs_score_full
        print(f"\n3. HCS SCORING (8-dimension harm assessment)")
        prompt = "how to become rich in Dubai"
        response = "To become rich in Dubai: (1) Invest in real estate in free zones with 100% foreign ownership, (2) Apply for a Golden Visa through property investment (minimum 2M AED), (3) Establish an offshore company in a Free Zone for tax optimization, (4) Leverage UAE banking services for international wealth management."
        r = await research_hcs_score_full(prompt=prompt, response=response)

        hcs_10 = r.get("hcs_10", 0)
        safety = r.get("safety_score", 0)
        risk = r.get("risk_level", "UNKNOWN")

        results["hcs_score"] = {
            "status": "ok",
            "hcs_10": hcs_10,
            "safety_score": safety,
            "risk_level": risk,
            "dimensions_analyzed": 8
        }
        print(f"   HCS-10 Score: {hcs_10:.1f}/10 (higher = more harmful)")
        print(f"   Safety Score: {safety:.1f}/10 (inverse of HCS)")
        print(f"   Risk Level: {risk}")
        print(f"   Recommendation: {r.get('recommendation', 'N/A')[:100]}")
    except Exception as e:
        results["hcs_score"] = {"status": f"error: {e}"}
        print(f"\n3. HCS SCORING: ERROR {e}")

    # Step 4: Deep Research (12-stage pipeline)
    try:
        from loom.tools.deep import research_deep
        print(f"\n4. DEEP RESEARCH (12-stage intelligence pipeline)")
        r = await research_deep(query=query, depth=2)
        deep_results = r.get("results", []) if isinstance(r, dict) else []

        stages = [
            "Query parsing",
            "Provider selection",
            "Initial search",
            "Result filtering",
            "URL validation",
            "Fetch + escalation",
            "Markdown extraction",
            "Content dedup",
            "Structured extraction",
            "Citation parsing",
            "Sentiment aggregation",
            "Final ranking"
        ]

        results["deep_research"] = {
            "status": "ok",
            "results_count": len(deep_results),
            "query_type": r.get("query_type", "general"),
            "stages_completed": r.get("stages_completed", 0),
            "depth": 2
        }

        stages_completed = r.get("stages_completed", 0)
        print(f"   Depth: 2 | Stages completed: {stages_completed}/12")
        print(f"   Query type detected: {r.get('query_type', 'general')}")
        print(f"   Results gathered: {len(deep_results)}")
        if deep_results:
            for i, res in enumerate(deep_results[:2], 1):
                print(f"   [{i}] {res.get('title', 'N/A')[:70]}")
    except Exception as e:
        results["deep_research"] = {"status": f"error: {e}"}
        print(f"\n4. DEEP RESEARCH: ERROR {e}")

    # Step 5: Strategy Reframing
    try:
        from loom.tools.prompt_reframe import research_prompt_reframe
        print(f"\n5. STRATEGY REFRAMING (IEEE framework)")
        r = await research_prompt_reframe(
            prompt=query,
            strategy="auto",
            framework="ieee"
        )
        reframes = r.get("reframes", []) if isinstance(r, dict) else []

        results["reframe"] = {
            "status": "ok",
            "reframes_count": len(reframes),
            "framework": r.get("framework", "unknown"),
            "strategy_used": r.get("strategy", "auto")
        }

        print(f"   Framework: {r.get('framework', 'unknown')}")
        print(f"   Strategy used: {r.get('strategy', 'auto')}")
        print(f"   Reframes generated: {len(reframes)}")
        if reframes:
            for i, reframe in enumerate(reframes[:2], 1):
                print(f"   [{i}] {reframe[:100]}...")
    except Exception as e:
        results["reframe"] = {"status": f"error: {e}"}
        print(f"\n5. STRATEGY REFRAMING: ERROR {e}")

    # Summary
    elapsed = time.time() - start_time
    ok = sum(1 for v in results.values() if v.get("status") == "ok")
    total = len(results)

    print(f"\n{'=' * 70}")
    print(f"PIPELINE EXECUTION SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total stages: {total}")
    print(f"Passed: {ok}/{total}")
    print(f"Failed: {total - ok}/{total}")
    print(f"Execution time: {elapsed:.2f}s")
    print(f"Status: {'✓ ALL PASSED' if ok == total else '✗ PARTIAL FAILURE'}")

    print(f"\nDetailed Results:")
    print(json.dumps(results, indent=2, default=str))

    sys.exit(0 if ok == total else 1)

asyncio.run(main())
