"""Full E2E User Journey — tests ALL 42+ Loom MCP tools with real API calls.

Groups tools by cost (free first, then paid) and runs each individually,
then exercises the full 12-stage deep pipeline.

Usage:
    python tests/journey_e2e.py

Output:
    - Console: pass/fail/skip per tool with timing
    - JSON report: journey-out/e2e_report.json
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ── API Keys (read from .env or environment) ────────────────────────────
# Load .env if it exists
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

os.environ.setdefault("NVIDIA_NIM_ENDPOINT", "https://integrate.api.nvidia.com/v1")
os.environ.setdefault("LOOM_CACHE_DIR", "/tmp/loom-journey-cache")
os.environ.setdefault("LOOM_LOGS_DIR", "/tmp/loom-journey-logs")

# Verify minimum keys
_required_keys = ["NVIDIA_NIM_API_KEY"]
_missing = [k for k in _required_keys if not os.environ.get(k)]
if _missing:
    print(f"ERROR: Missing required env vars: {_missing}")
    print("Set them in .env or environment before running.")
    sys.exit(2)

RESULTS: list[dict[str, Any]] = []
STEP = 0


def _log(name: str, status: str, elapsed_ms: int, detail: str = "") -> None:
    global STEP
    STEP += 1
    icon = {"PASS": "✓", "FAIL": "✗", "SKIP": "○"}.get(status, "?")
    pad = "." * max(1, 50 - len(name))
    detail_str = f" — {detail}" if detail else ""
    print(f"  [{STEP:2d}] {name} {pad} {icon} {status} ({elapsed_ms}ms){detail_str}")


def run_sync(name: str, fn: Any, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
    t0 = time.time()
    try:
        result = fn(*args, **kwargs)
        elapsed = int((time.time() - t0) * 1000)
        keys = list(result.keys()) if isinstance(result, dict) else str(type(result))
        has_error = "error" in result if isinstance(result, dict) else False
        status = "FAIL" if has_error else "PASS"
        detail = result.get("error", "")[:80] if has_error else f"keys={keys}"
        _log(name, status, elapsed, detail)
        RESULTS.append({"tool": name, "status": status, "elapsed_ms": elapsed, "detail": detail})
        return result
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        _log(name, "FAIL", elapsed, str(e)[:80])
        RESULTS.append({"tool": name, "status": "FAIL", "elapsed_ms": elapsed, "error": str(e)[:200]})
        return None


async def run_async(name: str, fn: Any, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
    t0 = time.time()
    try:
        result = await fn(*args, **kwargs)
        elapsed = int((time.time() - t0) * 1000)
        keys = list(result.keys()) if isinstance(result, dict) else str(type(result))
        has_error = "error" in result if isinstance(result, dict) else False
        status = "FAIL" if has_error else "PASS"
        detail = result.get("error", "")[:80] if has_error else f"keys={keys}"
        _log(name, status, elapsed, detail)
        RESULTS.append({"tool": name, "status": status, "elapsed_ms": elapsed, "detail": detail})
        return result
    except Exception as e:
        elapsed = int((time.time() - t0) * 1000)
        _log(name, "FAIL", elapsed, str(e)[:80])
        RESULTS.append({"tool": name, "status": "FAIL", "elapsed_ms": elapsed, "error": str(e)[:200]})
        return None


async def main() -> None:
    start_time = time.time()
    print("=" * 60)
    print("LOOM E2E USER JOURNEY — ALL TOOLS")
    print(f"Started: {datetime.now(UTC).isoformat()}")
    print("=" * 60)

    # ── GROUP 1: Config & Cache (free) ──────────────────────────────────
    print("\n── Group 1: Config & Cache ──")
    from loom.config import research_config_get, research_config_set

    run_sync("config_get", research_config_get)
    run_sync("config_set", research_config_set, "SPIDER_CONCURRENCY", 3)
    run_sync("config_get_key", research_config_get, "SPIDER_CONCURRENCY")

    from loom.tools.cache_mgmt import research_cache_stats, research_cache_clear

    run_sync("cache_stats", research_cache_stats)
    run_sync("cache_clear", research_cache_clear, 365)

    # ── GROUP 2: Enrichment (free) ──────────────────────────────────────
    print("\n── Group 2: Enrichment ──")
    from loom.tools.enrich import research_detect_language, research_wayback

    run_sync("detect_language_en", research_detect_language, "The quick brown fox jumps over the lazy dog")
    run_sync("detect_language_ar", research_detect_language, "هذا نص باللغة العربية للاختبار")
    run_sync("wayback", research_wayback, "https://example.com", 1)

    # ── GROUP 3: Fetch & Markdown (free) ────────────────────────────────
    print("\n── Group 3: Fetch & Markdown ──")
    from loom.tools.fetch import research_fetch
    from loom.tools.markdown import research_markdown
    from loom.tools.spider import research_spider

    run_sync("fetch_http", research_fetch, "https://example.com", "http")
    run_sync("fetch_escalate", research_fetch, "https://example.com", "http", auto_escalate=True)
    await run_async("markdown", research_markdown, "https://en.wikipedia.org/wiki/Python_(programming_language)")
    await run_async("spider", research_spider, ["https://example.com"], "http", concurrency=1)

    # ── GROUP 4: Free Search Providers ──────────────────────────────────
    print("\n── Group 4: Free Search ──")
    from loom.tools.search import research_search

    run_sync("search_ddgs", research_search, "artificial intelligence", provider="ddgs", n=3)
    run_sync("search_wikipedia", research_search, "transformer model", provider="wikipedia", n=2)
    run_sync("search_arxiv", research_search, "attention mechanism", provider="arxiv", n=2)
    run_sync("search_hackernews", research_search, "startup funding", provider="hackernews", n=2)
    run_sync("search_reddit", research_search, "python tips", provider="reddit", n=2)

    # ── GROUP 5: GitHub (free/token) ────────────────────────────────────
    print("\n── Group 5: GitHub ──")
    from loom.tools.github import research_github, research_github_readme, research_github_releases

    run_sync("github_repo", research_github, "repo", "python web framework", limit=3)
    run_sync("github_code", research_github, "code", "asyncio", limit=2)
    run_sync("github_issues", research_github, "issues", "performance", limit=2)
    run_sync("github_readme", research_github_readme, "pallets", "flask")
    run_sync("github_releases", research_github_releases, "python", "cpython", 2)

    # ── GROUP 6: Expert & Citation (free) ───────────────────────────────
    print("\n── Group 6: Expert & Citation ──")
    from loom.tools.experts import research_find_experts
    from loom.tools.creative import (
        research_citation_graph,
        research_community_sentiment,
        research_wiki_ghost,
        research_multilingual,
        research_consensus,
        research_curriculum,
    )

    await run_async("find_experts", research_find_experts, "machine learning", n=3)
    await run_async("citation_graph", research_citation_graph, "transformer attention", depth=1, max_papers=5)
    await run_async("community_sentiment", research_community_sentiment, "rust programming", n=3)
    await run_async("wiki_ghost", research_wiki_ghost, "Climate change")
    await run_async("multilingual", research_multilingual, "bitcoin", languages=["ar", "es"], n_per_lang=2)
    await run_async("consensus", research_consensus, "renewable energy", providers=["ddgs", "wikipedia"], n=3)
    await run_async("curriculum", research_curriculum, "machine learning")

    # ── GROUP 7: YouTube (free, needs yt-dlp) ───────────────────────────
    print("\n── Group 7: YouTube ──")
    try:
        from loom.providers.youtube_transcripts import fetch_youtube_transcript

        run_sync("youtube_transcript", fetch_youtube_transcript, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    except ImportError:
        _log("youtube_transcript", "SKIP", 0, "yt-dlp not installed")
        RESULTS.append({"tool": "youtube_transcript", "status": "SKIP", "elapsed_ms": 0})

    # ── GROUP 8: Paid Search (API keys) ─────────────────────────────────
    print("\n── Group 8: Paid Search ──")
    run_sync("search_exa", research_search, "climate change solutions", provider="exa", n=3)
    run_sync("search_tavily", research_search, "quantum computing", provider="tavily", n=3)
    run_sync("search_firecrawl", research_search, "web scraping", provider="firecrawl", n=3)
    run_sync("search_brave", research_search, "privacy browsers", provider="brave", n=3)

    from loom.providers.exa import find_similar_exa

    run_sync("exa_find_similar", find_similar_exa, "https://en.wikipedia.org/wiki/Machine_learning", n=2)

    # ── GROUP 9: LLM Tools (NVIDIA NIM free) ────────────────────────────
    print("\n── Group 9: LLM Tools ──")
    from loom.tools.llm import (
        research_llm_summarize,
        research_llm_extract,
        research_llm_classify,
        research_llm_translate,
        research_llm_query_expand,
        research_llm_answer,
        research_llm_embed,
        research_llm_chat,
    )

    sample_text = (
        "John Smith works at Acme Corp in New York. He earns $120,000 per year "
        "and has been with the company for 5 years. He specializes in machine learning."
    )

    await run_async("llm_summarize", research_llm_summarize, sample_text, max_tokens=50)
    await run_async("llm_extract", research_llm_extract, sample_text, schema={"name": "str", "company": "str", "salary": "int"})
    await run_async("llm_classify", research_llm_classify, "I love this product! It works perfectly.", labels=["positive", "negative", "neutral"])
    await run_async("llm_translate", research_llm_translate, "Hello, how are you?", target_lang="es")
    await run_async("llm_query_expand", research_llm_query_expand, "artificial intelligence ethics", n=3)
    await run_async("llm_answer", research_llm_answer, "What is photosynthesis?", sources=[{"title": "Biology", "text": "Photosynthesis converts sunlight to energy", "url": "https://example.com"}])
    await run_async("llm_embed", research_llm_embed, ["hello world", "good morning"])
    await run_async("llm_chat", research_llm_chat, messages=[{"role": "user", "content": "What is 2+2? Answer in one word."}], max_tokens=10)

    # ── GROUP 10: Creative Tools (LLM-dependent) ────────────────────────
    print("\n── Group 10: Creative Tools ──")
    from loom.tools.creative import (
        research_red_team,
        research_misinfo_check,
        research_ai_detect,
        research_temporal_diff,
        research_semantic_sitemap,
    )

    await run_async("red_team", research_red_team, "AI will replace all human jobs within 10 years", n_counter=2, max_cost_usd=0.05)
    await run_async("misinfo_check", research_misinfo_check, "The Earth is approximately 4.5 billion years old", n_sources=3, max_cost_usd=0.03)
    await run_async("ai_detect", research_ai_detect, sample_text * 3, max_cost_usd=0.02)
    await run_async("temporal_diff", research_temporal_diff, "https://example.com", max_cost_usd=0.03)
    await run_async("semantic_sitemap", research_semantic_sitemap, "example.com", max_pages=5)

    # ── GROUP 11: Full Deep Pipeline ────────────────────────────────────
    print("\n── Group 11: Full Pipeline ──")
    from loom.tools.deep import research_deep

    await run_async(
        "deep_academic",
        research_deep,
        "transformer attention mechanism paper",
        depth=1,
        expand_queries=True,
        extract=True,
        synthesize=True,
        include_github=False,
        max_cost_usd=0.20,
    )

    await run_async(
        "deep_knowledge",
        research_deep,
        "what is the Model Context Protocol",
        depth=1,
        expand_queries=False,
        extract=False,
        synthesize=True,
        max_cost_usd=0.10,
    )

    await run_async(
        "deep_code",
        research_deep,
        "best Python MCP framework library code",
        depth=1,
        expand_queries=False,
        extract=False,
        synthesize=False,
        include_github=True,
        max_cost_usd=0.05,
    )

    # ── GROUP 12: Session Management ────────────────────────────────────
    print("\n── Group 12: Sessions ──")
    from loom.sessions import research_session_list

    run_sync("session_list", research_session_list)

    # ── SUMMARY ─────────────────────────────────────────────────────────
    elapsed_total = int((time.time() - start_time) * 1000)
    passed = sum(1 for r in RESULTS if r["status"] == "PASS")
    failed = sum(1 for r in RESULTS if r["status"] == "FAIL")
    skipped = sum(1 for r in RESULTS if r["status"] == "SKIP")

    print("\n" + "=" * 60)
    print(f"JOURNEY COMPLETE — {elapsed_total / 1000:.1f}s")
    print(f"  PASS: {passed}  |  FAIL: {failed}  |  SKIP: {skipped}  |  TOTAL: {len(RESULTS)}")
    print("=" * 60)

    if failed > 0:
        print("\nFAILED TOOLS:")
        for r in RESULTS:
            if r["status"] == "FAIL":
                print(f"  ✗ {r['tool']}: {r.get('error', r.get('detail', ''))[:100]}")

    # Write JSON report
    out_dir = Path("journey-out")
    out_dir.mkdir(exist_ok=True)
    report = {
        "started_at": datetime.now(UTC).isoformat(),
        "elapsed_ms": elapsed_total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": len(RESULTS),
        "results": RESULTS,
    }
    report_path = out_dir / "e2e_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport saved: {report_path}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
