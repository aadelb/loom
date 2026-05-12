#!/usr/bin/env python3
"""EU AI Act Article 15 compliance audit script for Loom MCP research server."""
from __future__ import annotations

import asyncio
import json
import sys
import time
import traceback

sys.path.insert(0, "/opt/research-toolbox/src")

from loom.tools.query_builder import research_build_query
from loom.tools.search import research_search
from loom.tools.llm import research_llm_summarize
from loom.tools.security_auditor import research_security_audit
from loom.tools.reid_tactics import research_reid_tactics
from loom.tools.source_reputation import research_source_reputation
from loom.tools.fact_verifier import research_fact_verify
from loom.tools.trend_forecaster import research_trend_forecast


async def run_audit():
    results = {}
    overall_start = time.time()

    # === TOOL 1: research_build_query ===
    t0 = time.time()
    try:
        r = research_build_query(
            user_request="wealth creation strategies",
            darkness_level=10,
            spectrum=True,
        )
        dt = time.time() - t0
        results["research_build_query"] = {
            "status": "ok",
            "elapsed_sec": round(dt, 3),
            "intent_category": r.get("intent", {}).get("category"),
            "sub_questions_count": len(r.get("sub_questions", [])),
            "sub_questions": r.get("sub_questions", []),
            "optimized_queries_count": sum(len(v) for v in r.get("optimized_queries", {}).values()),
            "recommended_tools": r.get("recommended_tools", []),
            "has_reframe_variants": len(r.get("reframe_variants", [])) > 0,
            "reframe_variants_count": len(r.get("reframe_variants", [])),
            "sample_reframe": r.get("reframe_variants", [{}])[0] if r.get("reframe_variants") else None,
            "metadata": r.get("metadata", {}),
        }
    except Exception as e:
        results["research_build_query"] = {
            "status": "error",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    # === TOOL 2: research_search ===
    t0 = time.time()
    try:
        r = await research_search(query="investment strategies", provider="ddgs", n=5)
        dt = time.time() - t0
        results["research_search"] = {
            "status": "ok",
            "elapsed_sec": round(dt, 3),
            "result_count": len(r.get("results", [])),
            "provider": r.get("provider"),
            "sample_titles": [x.get("title", "") for x in r.get("results", [])[:3]],
            "has_error": "error" in r,
            "error": r.get("error"),
        }
    except Exception as e:
        results["research_search"] = {
            "status": "error",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    # === TOOL 3: research_llm_summarize ===
    t0 = time.time()
    try:
        r = await research_llm_summarize(text="test text about wealth", max_tokens=50)
        dt = time.time() - t0
        results["research_llm_summarize"] = {
            "status": "ok",
            "elapsed_sec": round(dt, 3),
            "summary": r.get("summary"),
            "provider": r.get("provider"),
            "model": r.get("model"),
            "cost_usd": r.get("cost_usd"),
            "has_error": "error" in r,
            "error": r.get("error"),
        }
    except Exception as e:
        results["research_llm_summarize"] = {
            "status": "error",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    # === TOOL 4: research_security_audit ===
    t0 = time.time()
    try:
        r = await research_security_audit()
        dt = time.time() - t0
        results["research_security_audit"] = {
            "status": "ok",
            "elapsed_sec": round(dt, 3),
            "issues_count": len(r.get("issues", [])),
            "severity_breakdown": r.get("severity_breakdown", {}),
            "has_error": "error" in r,
        }
    except Exception as e:
        results["research_security_audit"] = {
            "status": "error",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    # === TOOL 5: research_reid_tactics ===
    t0 = time.time()
    try:
        r = await research_reid_tactics()
        dt = time.time() - t0
        tactics = r.get("tactics", {})
        sample_tactic = list(tactics.keys())[0] if tactics else None
        sample_data = tactics.get(sample_tactic, {}) if sample_tactic else {}
        results["research_reid_tactics"] = {
            "status": "ok",
            "elapsed_sec": round(dt, 3),
            "total_tactics": r.get("total", len(tactics)),
            "sample_tactic": sample_tactic,
            "sample_effectiveness": sample_data.get("effectiveness"),
            "has_counters": any("safety_counter" in v for v in tactics.values()),
            "has_error": "error" in r,
        }
    except Exception as e:
        results["research_reid_tactics"] = {
            "status": "error",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    # === TOOL 6: research_source_reputation ===
    t0 = time.time()
    try:
        r = await research_source_reputation(url="https://arxiv.org")
        dt = time.time() - t0
        results["research_source_reputation"] = {
            "status": "ok",
            "elapsed_sec": round(dt, 3),
            "domain": r.get("domain"),
            "reputation_score": r.get("reputation_score"),
            "blocked": r.get("blocked"),
            "high_quality": r.get("high_quality"),
            "has_error": "error" in r,
        }
    except Exception as e:
        results["research_source_reputation"] = {
            "status": "error",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    # === TOOL 7: research_fact_verify ===
    t0 = time.time()
    try:
        r = await research_fact_verify(claim="Real estate is the best investment")
        dt = time.time() - t0
        results["research_fact_verify"] = {
            "status": "ok",
            "elapsed_sec": round(dt, 3),
            "verdict": r.get("verdict"),
            "confidence": r.get("confidence"),
            "sources_count": len(r.get("sources", [])),
            "has_error": "error" in r,
            "error": r.get("error"),
        }
    except Exception as e:
        results["research_fact_verify"] = {
            "status": "error",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    # === TOOL 8: research_trend_forecast ===
    t0 = time.time()
    try:
        r = await research_trend_forecast(topic="wealth creation")
        dt = time.time() - t0
        results["research_trend_forecast"] = {
            "status": "ok",
            "elapsed_sec": round(dt, 3),
            "topic": r.get("topic"),
            "emerging_terms_count": len(r.get("emerging_terms", [])),
            "declining_terms_count": len(r.get("declining_terms", [])),
            "forecast_snippets": r.get("forecast", [])[:3] if isinstance(r.get("forecast"), list) else [],
            "has_error": "error" in r,
            "error": r.get("error"),
        }
    except Exception as e:
        results["research_trend_forecast"] = {
            "status": "error",
            "elapsed_sec": round(time.time() - t0, 3),
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    results["_overall_elapsed_sec"] = round(time.time() - overall_start, 3)
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(run_audit())
