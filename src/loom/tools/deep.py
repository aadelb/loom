"""Full-pipeline deep research: expand → search → fetch → extract → rank → synthesize.

Combines all available Loom tools into a single orchestrated research pipeline:
1. Query expansion via LLM
2. Multi-provider parallel search
3. Parallel fetch + markdown extraction with auto-escalation
4. LLM-powered content extraction
5. Relevance ranking
6. Answer synthesis with citations
7. GitHub enrichment for code-related queries
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from urllib.parse import urlparse

from loom.validators import EXTERNAL_TIMEOUT_SECS

logger = logging.getLogger("loom.deep")

_CODE_KEYWORDS = frozenset(
    {
        "repo",
        "github",
        "library",
        "framework",
        "package",
        "code",
        "sdk",
        "api",
        "module",
        "npm",
        "pypi",
        "crate",
        "gem",
        "open-source",
        "opensource",
        "open source",
    }
)

_ACADEMIC_KEYWORDS = frozenset(
    {
        "paper",
        "research",
        "study",
        "algorithm",
        "arxiv",
        "journal",
        "citation",
        "dataset",
        "benchmark",
        "neural",
        "transformer",
        "training",
        "evaluation",
        "survey",
        "thesis",
        "preprint",
    }
)

_KNOWLEDGE_KEYWORDS = frozenset(
    {
        "what is",
        "define",
        "explain",
        "history of",
        "how does",
        "overview",
        "introduction to",
        "meaning of",
        "concept of",
    }
)


def _detect_query_type(query: str) -> set[str]:
    """Detect query intent to auto-select providers."""
    query_lower = query.lower()
    query_words = set(query_lower.split())
    types: set[str] = set()
    if query_words & _CODE_KEYWORDS:
        types.add("code")
    if query_words & _ACADEMIC_KEYWORDS:
        types.add("academic")
    for phrase in _KNOWLEDGE_KEYWORDS:
        if phrase in query_lower:
            types.add("knowledge")
            break
    return types


def _normalize_url(url: str) -> str:
    """Normalize a URL for deduplication (strip fragment, trailing slash)."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def _merge_search_results(all_results: list[dict[str, Any]], max_urls: int) -> list[dict[str, Any]]:
    """Deduplicate search results by normalized URL, keeping highest score."""
    seen: dict[str, dict[str, Any]] = {}
    for r in all_results:
        url = r.get("url", "")
        if not url:
            continue
        key = _normalize_url(url)
        existing = seen.get(key)
        if existing is None or (r.get("score") or 0) > (existing.get("score") or 0):
            seen[key] = r
    results = list(seen.values())
    results.sort(key=lambda x: x.get("score") or 0, reverse=True)
    return results[:max_urls]


async def research_deep(
    query: str,
    depth: int = 2,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    language: str | None = None,
    provider_config: dict[str, Any] | None = None,
    search_providers: list[str] | None = None,
    expand_queries: bool = True,
    extract: bool = True,
    synthesize: bool = True,
    include_github: bool = True,
    max_cost_usd: float = 0.50,
) -> dict[str, Any]:
    """Full-pipeline deep research using all available tools.

    Orchestrates query expansion, multi-provider search, parallel fetch,
    LLM extraction, relevance ranking, answer synthesis, and optional
    GitHub enrichment.

    Args:
        query: search query string
        depth: controls result volume (1-10)
        include_domains: only search within these domains
        exclude_domains: exclude these domains
        start_date: ISO yyyy-mm-dd start date
        end_date: ISO yyyy-mm-dd end date
        language: language hint
        provider_config: provider-specific kwargs
        search_providers: list of search providers to use (default from config)
        expand_queries: enable LLM query expansion
        extract: enable LLM content extraction
        synthesize: enable LLM answer synthesis
        include_github: enable GitHub enrichment for code queries
        max_cost_usd: total LLM cost cap for this call

    Returns:
        Dict with query, search_variations, providers_used, pages_searched,
        pages_fetched, top_pages, synthesis, github_repos, total_cost_usd,
        elapsed_ms.
    """
    from loom.config import get_config
    from loom.tools.search import research_search

    start_time = time.time()
    config = get_config()
    total_cost = 0.0

    if search_providers is None:
        search_providers = list(config.get("RESEARCH_SEARCH_PROVIDERS", ["exa", "brave"]))
    expand_queries = expand_queries and config.get("RESEARCH_EXPAND_QUERIES", True)
    extract = extract and config.get("RESEARCH_EXTRACT", True)
    synthesize = synthesize and config.get("RESEARCH_SYNTHESIZE", True)
    include_github = include_github and config.get("RESEARCH_GITHUB_ENRICHMENT", True)

    # Auto-detect query type and add specialized providers
    query_types = _detect_query_type(query)
    if "academic" in query_types and "arxiv" not in search_providers:
        search_providers.append("arxiv")
    if "knowledge" in query_types and "wikipedia" not in search_providers:
        search_providers.append("wikipedia")
    if "ddgs" not in search_providers:
        search_providers.append("ddgs")

    loop = asyncio.get_running_loop()

    # ── STAGE 1: Query Expansion ─────────────────────────────────────────
    search_variations: list[str] = [query]
    if expand_queries and total_cost < max_cost_usd:
        try:
            from loom.tools.llm import research_llm_query_expand

            expand_result = await research_llm_query_expand(query, n=3)
            if "error" not in expand_result:
                extras = expand_result.get("queries", [])
                if extras:
                    search_variations.extend(extras[:3])
                total_cost += expand_result.get("cost_usd", 0.0)
        except Exception as exc:
            logger.warning("query_expand_skipped: %s", exc)

    # ── STAGE 2: Multi-Provider Search ───────────────────────────────────
    async def _run_search(q: str, provider: str) -> dict[str, Any]:
        return await loop.run_in_executor(
            None,
            lambda: research_search(
                q,
                provider=provider,
                n=depth * 5,
                include_domains=include_domains,
                exclude_domains=exclude_domains,
                start_date=start_date,
                end_date=end_date,
                language=language,
                provider_config=provider_config,
            ),
        )

    search_tasks = [_run_search(q, p) for q in search_variations for p in search_providers]

    try:
        search_responses = await asyncio.wait_for(
            asyncio.gather(*search_tasks, return_exceptions=True),
            timeout=EXTERNAL_TIMEOUT_SECS,
        )
    except TimeoutError:
        logger.warning("deep_search_timeout query=%s", query)
        search_responses = []

    all_search_results: list[dict[str, Any]] = []
    providers_used: list[str] = []
    for resp in search_responses:
        if isinstance(resp, dict):
            pname = resp.get("provider", "unknown")
            if pname not in providers_used and "error" not in resp:
                providers_used.append(pname)
            all_search_results.extend(resp.get("results", []))

    pages_searched = len(all_search_results)
    merged_hits = _merge_search_results(all_search_results, max_urls=depth * 5)

    if not merged_hits:
        return {
            "query": query,
            "search_variations": search_variations,
            "providers_used": providers_used,
            "pages_searched": pages_searched,
            "pages_fetched": 0,
            "top_pages": [],
            "synthesis": None,
            "github_repos": None,
            "total_cost_usd": total_cost,
            "elapsed_ms": int((time.time() - start_time) * 1000),
            "error": "no search results",
        }

    # ── STAGE 3: Parallel Fetch + Markdown ───────────────────────────────
    from loom.tools.fetch import research_fetch
    from loom.tools.markdown import research_markdown

    concurrency = config.get("SPIDER_CONCURRENCY", 5)
    sem = asyncio.Semaphore(concurrency)

    async def _fetch_and_markdown(hit: dict[str, Any]) -> dict[str, Any] | None:
        url = hit.get("url", "")
        if not url:
            return None
        async with sem:
            fetch_result: dict[str, Any] = {}
            try:
                fetch_result = await loop.run_in_executor(
                    None,
                    lambda: research_fetch(url, mode="http", auto_escalate=True),
                )
            except Exception as exc:
                logger.warning("deep_fetch_fail url=%s error=%s", url, exc)

            try:
                md_result = await research_markdown(url)
            except Exception as exc:
                logger.warning("deep_markdown_fail url=%s error=%s", url, exc)
                md_result = {}

            markdown = md_result.get("markdown", "")
            # Fallback: use fetched text if markdown extraction failed
            if len(markdown) < 100 and fetch_result.get("text"):
                markdown = fetch_result["text"]
            if len(markdown) < 100:
                return None

            return {
                "url": url,
                "title": hit.get("title") or md_result.get("title", ""),
                "snippet": hit.get("snippet", ""),
                "markdown": markdown,
                "score": hit.get("score"),
                "fetch_tool": fetch_result.get("tool"),
            }

    fetch_tasks = [_fetch_and_markdown(hit) for hit in merged_hits]
    try:
        fetch_results = await asyncio.wait_for(
            asyncio.gather(*fetch_tasks, return_exceptions=True),
            timeout=EXTERNAL_TIMEOUT_SECS * 3,
        )
    except TimeoutError:
        logger.warning("deep_fetch_timeout query=%s", query)
        fetch_results = []

    pages: list[dict[str, Any]] = [
        r for r in fetch_results if r is not None and not isinstance(r, BaseException)
    ]
    pages = pages[: depth * 3]

    # ── STAGE 4: LLM Extraction ──────────────────────────────────────────
    if extract and pages and total_cost < max_cost_usd:
        try:
            from loom.tools.llm import research_llm_extract

            schema = {
                "key_points": "array",
                "entities": "array",
                "relevance_score": "number",
            }
            for page in pages:
                if total_cost >= max_cost_usd:
                    break
                try:
                    result = await research_llm_extract(page["markdown"][:5000], schema=schema)
                    if "error" not in result:
                        data = result.get("data", {})
                        page["extracted"] = data
                        page["relevance_score"] = data.get("relevance_score")
                        total_cost += result.get("cost_usd", 0.0)
                except Exception as exc:
                    logger.warning("extract_fail url=%s error=%s", page["url"], exc)
        except ImportError:
            pass

    # ── STAGE 5: Relevance Ranking ───────────────────────────────────────
    def _sort_key(p: dict[str, Any]) -> float:
        rel = p.get("relevance_score")
        if rel is not None:
            try:
                return float(rel)
            except (TypeError, ValueError):
                pass
        return float(p.get("score") or 0)

    pages.sort(key=_sort_key, reverse=True)
    top_pages = pages[: depth * 2]

    # ── STAGE 6: Synthesis ───────────────────────────────────────────────
    synthesis_result: dict[str, Any] | None = None
    if synthesize and top_pages and total_cost < max_cost_usd:
        try:
            from loom.tools.llm import research_llm_answer

            sources = [
                {
                    "title": p.get("title", ""),
                    "text": p["markdown"][:500],
                    "url": p["url"],
                }
                for p in top_pages[:10]
            ]
            answer_result = await research_llm_answer(
                question=query, sources=sources, style="cited"
            )
            if "error" not in answer_result:
                synthesis_result = answer_result
                total_cost += answer_result.get("cost_usd", 0.0)
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("synthesis_fail: %s", exc)

    # ── STAGE 7: GitHub Enrichment ───────────────────────────────────────
    github_repos: list[dict[str, Any]] | None = None
    if include_github:
        query_words = set(query.lower().split())
        if query_words & _CODE_KEYWORDS:
            try:
                from loom.tools.github import research_github

                gh_result = await loop.run_in_executor(
                    None,
                    lambda: research_github(kind="repo", query=query, limit=5),
                )
                if isinstance(gh_result, dict) and "error" not in gh_result:
                    github_repos = gh_result.get("results", [])
            except Exception as exc:
                logger.warning("github_enrichment_fail: %s", exc)

    # ── Build Response ───────────────────────────────────────────────────
    for p in top_pages:
        if len(p.get("markdown", "")) > 2000:
            p["markdown"] = p["markdown"][:2000] + "…"

    return {
        "query": query,
        "search_variations": search_variations,
        "providers_used": providers_used,
        "pages_searched": pages_searched,
        "pages_fetched": len(pages),
        "top_pages": top_pages,
        "synthesis": synthesis_result,
        "github_repos": github_repos,
        "total_cost_usd": total_cost,
        "elapsed_ms": int((time.time() - start_time) * 1000),
    }
