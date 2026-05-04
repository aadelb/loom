"""Full-pipeline deep research: expand → search → fetch → extract → rank → synthesize.

Combines all available Loom tools into a single orchestrated 12-stage pipeline:
1. Query expansion via LLM
2. Multi-provider parallel search (auto-detect academic/knowledge/code queries)
3. Parallel fetch + markdown (YouTube transcript, Wayback fallback, auto-escalation)
4. LLM-powered content extraction (parallelized with cost cap)
5. Relevance ranking
6. Answer synthesis with citations
7. GitHub enrichment (repos + README content)
8. Language detection on extracted pages
9. Community sentiment from HN + Reddit (optional)
10. Adversarial red team on synthesis (optional)
11. Misinformation stress test on claims (optional)
12. Fact-checking of top claims from synthesis
13. Build response
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any
from urllib.parse import urlparse

from loom.validators import EXTERNAL_TIMEOUT_SECS

logger = logging.getLogger("loom.deep")

# Try to import cost estimator with graceful fallback
try:
    from loom.tools.cost_estimator import research_estimate_cost
    _COST_ESTIMATION_AVAILABLE = True
except ImportError:
    _COST_ESTIMATION_AVAILABLE = False
    logger.debug("cost_estimator not available; cost gating disabled")

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

_FINANCE_KEYWORDS = frozenset(
    {
        "bitcoin",
        "ethereum",
        "crypto",
        "cryptocurrency",
        "stock",
        "stocks",
        "market",
        "trading",
        "price",
        "forex",
        "commodity",
        "gold",
        "silver",
        "oil",
        "nasdaq",
        "s&p",
        "dow",
        "blockchain",
        "defi",
        "nft",
        "token",
        "coin",
    }
)

_DARKWEB_KEYWORDS = frozenset(
    {
        "tor",
        "onion",
        "darkweb",
        "darknet",
        "hidden",
        ".onion",
        "deep web",
        "dark web",
        "i2p",
        "freenet",
        "tails",
        "whonix",
    }
)

_NEWS_KEYWORDS = frozenset(
    {
        "news",
        "breaking",
        "latest",
        "report",
        "announcement",
        "update",
        "today",
        "yesterday",
        "recent",
        "headline",
        "press",
        "release",
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
    if query_words & _FINANCE_KEYWORDS:
        types.add("finance")
    if query_words & _DARKWEB_KEYWORDS:
        types.add("darkweb")
    if query_words & _NEWS_KEYWORDS:
        types.add("news")
    for phrase in _KNOWLEDGE_KEYWORDS:
        if phrase in query_lower:
            types.add("knowledge")
            break
    return types


def _normalize_url(url: str) -> str:
    """Normalize a URL for deduplication (strip fragment, trailing slash)."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def _is_youtube_url(url: str) -> bool:
    """Check if URL is from YouTube."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    return domain in ("youtube.com", "www.youtube.com", "youtu.be", "www.youtu.be", "m.youtube.com")


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


def _extract_factual_claims(text: str, max_claims: int = 3) -> list[str]:
    """Extract top factual claims (sentences with numbers, dates, or proper nouns)."""
    if not text:
        return []

    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    claims = []

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 20:  # Skip very short sentences
            continue

        # Look for sentences with numbers, years, or capitalized proper nouns
        has_number = bool(re.search(r'\d+', sentence))
        has_year = bool(re.search(r'\b(19|20)\d{2}\b', sentence))
        has_proper_noun = bool(re.search(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', sentence))

        if has_number or has_year or has_proper_noun:
            claims.append(sentence)
            if len(claims) >= max_claims:
                break

    return claims


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
    include_community: bool = False,
    include_red_team: bool = False,
    include_misinfo_check: bool = False,
    max_cost_usd: float | None = None,
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
        elapsed_ms, and fact_checks (if synthesis succeeded).
    """
    from loom.config import get_config
    from loom.tools.search import research_search

    start_time = time.time()
    config = get_config()
    total_cost = 0.0
    estimated_cost = 0.0
    warnings: list[dict[str, str]] = []

    if max_cost_usd is None:
        max_cost_usd = float(config.get("RESEARCH_MAX_COST_USD", 0.50))
    if search_providers is None:
        search_providers = list(config.get("RESEARCH_SEARCH_PROVIDERS", ["exa", "brave"]))
    expand_queries = expand_queries and config.get("RESEARCH_EXPAND_QUERIES", True)
    extract = extract and config.get("RESEARCH_EXTRACT", True)
    synthesize = synthesize and config.get("RESEARCH_SYNTHESIZE", True)
    include_github = include_github and config.get("RESEARCH_GITHUB_ENRICHMENT", True)
    include_community = include_community or config.get("RESEARCH_COMMUNITY_SENTIMENT", False)
    include_red_team = include_red_team or config.get("RESEARCH_RED_TEAM", False)
    include_misinfo_check = include_misinfo_check or config.get("RESEARCH_MISINFO_CHECK", False)

    # Auto-detect query type and add specialized providers
    query_types = _detect_query_type(query)
    if "academic" in query_types and "arxiv" not in search_providers:
        search_providers.append("arxiv")
    if "knowledge" in query_types and "wikipedia" not in search_providers:
        search_providers.append("wikipedia")
    if "finance" in query_types:
        if "binance" not in search_providers:
            search_providers.append("binance")
        if "investing" not in search_providers:
            search_providers.append("investing")
    if "darkweb" in query_types:
        if "ahmia" not in search_providers:
            search_providers.append("ahmia")
        if "darksearch" not in search_providers:
            search_providers.append("darksearch")
    if "news" in query_types and "newsapi" not in search_providers:
        search_providers.append("newsapi")
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
            warnings.append({"stage": "expand", "error": str(exc)})

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
        warnings.append({"stage": "search", "error": "timeout"})
        search_responses = []

    all_search_results: list[dict[str, Any]] = []
    providers_used: list[str] = []
    for resp in search_responses:
        if isinstance(resp, dict):
            pname = resp.get("provider", "unknown")
            if "error" in resp:
                warnings.append({"stage": "search", "provider": pname, "error": resp["error"]})
            else:
                if pname not in providers_used:
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
            "warnings": warnings,
            "estimated_cost_usd": estimated_cost,
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
            markdown = ""
            md_title = ""

            # Check if URL is YouTube and try transcript extraction
            if _is_youtube_url(url):
                try:
                    from loom.providers.youtube_transcripts import fetch_youtube_transcript

                    yt_result = await loop.run_in_executor(
                        None,
                        lambda: fetch_youtube_transcript(url),
                    )
                    if "error" not in yt_result:
                        markdown = yt_result.get("transcript", "")
                        if not markdown:
                            markdown = yt_result.get("description", "")
                        md_title = yt_result.get("title", "")
                except ImportError:
                    logger.debug("youtube_transcripts not available (yt-dlp not installed)")
                except Exception as exc:
                    logger.warning("youtube_transcript_extraction_failed url=%s error=%s", url, exc)
            else:
                # Auto-set Tor proxy for .onion URLs
                proxy = None
                from urllib.parse import urlparse as _urlparse
                _host = _urlparse(url).hostname or ""
                if _host.endswith(".onion"):
                    proxy = config.get("TOR_SOCKS5_PROXY", "socks5h://127.0.0.1:9050")

                try:
                    fetch_result = await loop.run_in_executor(
                        None,
                        lambda: research_fetch(url, mode="http", auto_escalate=True, proxy=proxy),
                    )
                except Exception as exc:
                    logger.warning("deep_fetch_fail url=%s error=%s", url, exc)

                try:
                    md_result = await research_markdown(url)
                except Exception as exc:
                    logger.warning("deep_markdown_fail url=%s error=%s", url, exc)
                    md_result = {}

                markdown = md_result.get("markdown", "")
                md_title = md_result.get("title", "")
                # Fallback: use fetched text if markdown extraction failed
                if len(markdown) < 100 and fetch_result.get("text"):
                    markdown = fetch_result["text"]

            # Wayback fallback for dead links (404, empty content)
            if len(markdown) < 100:
                try:
                    from loom.tools.enrich import research_wayback

                    wb = research_wayback(url, limit=1)
                    snapshots = wb.get("snapshots", [])
                    if snapshots:
                        archive_url = snapshots[0]["archive_url"]
                        try:
                            wb_md = await research_markdown(archive_url)
                            if wb_md.get("markdown") and len(wb_md["markdown"]) >= 100:
                                markdown = wb_md["markdown"]
                                md_title = wb_md.get("title", md_title)
                                logger.info("wayback_recovery url=%s archive=%s", url, archive_url)
                        except Exception as wb_exc:
                            logger.debug("wayback_markdown_fail: %s", wb_exc)
                except Exception as exc:
                    logger.debug("wayback_fallback_skipped url=%s: %s", url, exc)

            if len(markdown) < 100:
                return None

            return {
                "url": url,
                "title": hit.get("title") or md_title or "",
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
        warnings.append({"stage": "fetch", "error": "timeout"})
        fetch_results = []

    pages: list[dict[str, Any]] = [
        r for r in fetch_results if r is not None and not isinstance(r, BaseException)
    ]
    pages = pages[: depth * 3]

    # ── STAGE 4: LLM Extraction (PARALLELIZED) ──────────────────────────
    if extract and pages and total_cost < max_cost_usd:
        try:
            from loom.tools.llm import research_llm_extract

            schema = {
                "key_points": "array",
                "entities": "array",
                "relevance_score": "number",
            }

            # Limit concurrent extractions to avoid exceeding cost cap
            extract_concurrency = config.get("LLM_EXTRACT_CONCURRENCY", 3)
            extract_sem = asyncio.Semaphore(extract_concurrency)

            async def _extract_single(page: dict[str, Any]) -> None:
                """Extract content from a single page."""
                nonlocal total_cost

                async with extract_sem:
                    if total_cost >= max_cost_usd:
                        return

                    try:
                        result = await research_llm_extract(page["markdown"][:5000], schema=schema)
                        if "error" not in result:
                            data = result.get("data", {})
                            page["extracted"] = data
                            page["relevance_score"] = data.get("relevance_score")
                        else:
                            warnings.append({"stage": "extract", "url": page["url"], "error": result["error"]})
                        total_cost += result.get("cost_usd", 0.0)
                    except Exception as exc:
                        logger.warning("extract_fail url=%s error=%s", page["url"], exc)
                        warnings.append({"stage": "extract", "url": page["url"], "error": str(exc)})

            # Extract in parallel up to cost limit
            extract_tasks = [_extract_single(page) for page in pages]
            await asyncio.gather(*extract_tasks, return_exceptions=True)

        except ImportError:
            warnings.append({"stage": "extract", "error": "llm module not available"})

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
        # Estimate cost before executing LLM synthesis
        if _COST_ESTIMATION_AVAILABLE:
            try:
                cost_estimate = await research_estimate_cost(
                    "research_llm_answer",
                    params={"query": query, "sources": top_pages[:10]},
                    provider="auto",
                )
                estimated_cost += cost_estimate.get("estimated_cost_usd", 0.0)

                # Check if estimated cost would exceed budget
                if total_cost + estimated_cost > max_cost_usd:
                    logger.info(
                        "synthesis_cost_exceeded: estimated_cost=%f, total=%f, max=%f",
                        estimated_cost,
                        total_cost,
                        max_cost_usd,
                    )
                    warnings.append({
                        "stage": "synthesis",
                        "error": f"cost cap exceeded: {total_cost + estimated_cost:.6f} > {max_cost_usd}",
                    })
                else:
                    # Cost is within budget, proceed with synthesis
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
                        warnings.append({"stage": "synthesis", "error": "llm module not available"})
                    except Exception as exc:
                        logger.warning("synthesis_fail: %s", exc)
                        warnings.append({"stage": "synthesis", "error": str(exc)})
            except Exception as exc:
                logger.warning("cost_estimation_fail: %s", exc)
                # Fallback: proceed with synthesis without cost pre-check
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
                    warnings.append({"stage": "synthesis", "error": "llm module not available"})
                except Exception as exc2:
                    logger.warning("synthesis_fail: %s", exc2)
                    warnings.append({"stage": "synthesis", "error": str(exc2)})
        else:
            # Cost estimator not available, proceed without pre-check
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
                warnings.append({"stage": "synthesis", "error": "llm module not available"})
            except Exception as exc:
                logger.warning("synthesis_fail: %s", exc)
                warnings.append({"stage": "synthesis", "error": str(exc)})

    # ── STAGE 7: GitHub Enrichment ───────────────────────────────────────
    github_repos: list[dict[str, Any]] | None = None
    if include_github:
        query_words = set(query.lower().split())
        if query_words & _CODE_KEYWORDS:
            try:
                from loom.tools.github import research_github, research_github_readme

                gh_result = await loop.run_in_executor(
                    None,
                    lambda: research_github(kind="repo", query=query, limit=5),
                )
                if isinstance(gh_result, dict) and "error" not in gh_result:
                    repos = gh_result.get("results", [])
                    # Enrich top repo with README
                    if repos:
                        top_repo = repos[0]
                        if "name" in top_repo and "/" in top_repo["name"]:
                            owner, repo = top_repo["name"].split("/", 1)
                            try:
                                readme_result = await loop.run_in_executor(
                                    None,
                                    lambda: research_github_readme(owner, repo),
                                )
                                if "error" not in readme_result:
                                    top_repo["readme"] = readme_result.get("content", "")
                            except Exception as exc:
                                logger.warning("github_readme_fail %s/%s: %s", owner, repo, exc)
                    github_repos = repos
            except Exception as exc:
                logger.warning("github_enrichment_fail: %s", exc)
                warnings.append({"stage": "github", "error": str(exc)})

    # ── STAGE 8: Language Detection ─────────────────────────────────────
    language_stats: dict[str, int] = {}
    try:
        from loom.tools.enrich import research_detect_language

        for page in top_pages:
            snippet = page.get("markdown", "")[:1000]
            if snippet:
                lang_result = research_detect_language(snippet)
                lang = lang_result.get("language", "unknown")
                language_stats[lang] = language_stats.get(lang, 0) + 1
                page["detected_language"] = lang
    except Exception as exc:
        logger.debug("language_detection_skipped: %s", exc)

    # ── STAGE 9: Community Sentiment (optional) ─────────────────────────
    community_sentiment: dict[str, Any] | None = None
    if include_community:
        query_words = set(query.lower().split())
        tech_keywords = _CODE_KEYWORDS | {"tool", "app", "service", "platform", "startup"}
        if query_words & tech_keywords:
            try:
                from loom.tools.creative import research_community_sentiment

                community_sentiment = await research_community_sentiment(query, n=5)
            except Exception as exc:
                logger.warning("community_sentiment_fail: %s", exc)
                warnings.append({"stage": "community_sentiment", "error": str(exc)})

    # ── STAGE 10: Red Team (optional) ───────────────────────────────────
    red_team_report: dict[str, Any] | None = None
    if include_red_team and synthesis_result and total_cost < max_cost_usd:
        try:
            from loom.tools.creative import research_red_team

            claim = synthesis_result.get("answer", "")[:500]
            if claim:
                red_team_report = await research_red_team(
                    claim=claim, n_counter=3, max_cost_usd=min(0.05, max_cost_usd - total_cost)
                )
                total_cost += red_team_report.get("total_cost_usd", 0.0)
        except Exception as exc:
            logger.warning("red_team_fail: %s", exc)
            warnings.append({"stage": "red_team", "error": str(exc)})

    # ── STAGE 11: Misinfo Check (optional) ──────────────────────────────
    misinfo_report: dict[str, Any] | None = None
    if include_misinfo_check and synthesis_result and total_cost < max_cost_usd:
        try:
            from loom.tools.creative import research_misinfo_check

            claim = synthesis_result.get("answer", "")[:300]
            if claim:
                misinfo_report = await research_misinfo_check(
                    claim=claim, max_cost_usd=min(0.05, max_cost_usd - total_cost)
                )
        except Exception as exc:
            logger.warning("misinfo_check_fail: %s", exc)
            warnings.append({"stage": "misinfo_check", "error": str(exc)})

    # ── STAGE 12: Fact-Checking (non-blocking) ──────────────────────────
    fact_checks: list[dict[str, Any]] | None = None
    if synthesis_result:
        try:
            from loom.tools.fact_checker import research_fact_check

            final_answer = synthesis_result.get("answer", "")
            claims = _extract_factual_claims(final_answer, max_claims=3)

            if claims:
                fact_checks = []
                for claim in claims:
                    try:
                        check_result = await research_fact_check(claim, max_sources=5)
                        fact_checks.append(check_result)
                        logger.info("fact_check completed claim=%s verdict=%s", claim[:50], check_result.get("verdict"))
                    except Exception as exc:
                        logger.debug("fact_check_single_fail: %s", exc)
        except ImportError:
            logger.debug("fact_checker not available, skipping fact-checking")
        except Exception as exc:
            logger.warning("fact_check_fail (non-blocking): %s", exc)

    # ── STAGE 13: Build Response ────────────────────────────────────────
    for p in top_pages:
        if len(p.get("markdown", "")) > 2000:
            p["markdown"] = p["markdown"][:2000] + "…"

    final_answer = synthesis_result.get("answer", "") if synthesis_result else ""

    # Build response dict
    response: dict[str, Any] = {
        "query": query,
        "search_variations": search_variations,
        "providers_used": providers_used,
        "pages_searched": pages_searched,
        "pages_fetched": len(pages),
        "top_pages": top_pages,
        "synthesis": synthesis_result,
        "github_repos": github_repos,
        "language_stats": language_stats,
        "community_sentiment": community_sentiment,
        "red_team_report": red_team_report,
        "misinfo_report": misinfo_report,
        "fact_checks": fact_checks,
        "warnings": warnings,
        "estimated_cost_usd": estimated_cost,
        "total_cost_usd": total_cost,
        "elapsed_ms": int((time.time() - start_time) * 1000),
    }

    # ── AUTO-SCORE WITH HCS (NON-BLOCKING) ──────────────────────────────
    try:
        from loom.tools.hcs_multi_scorer import research_hcs_score_full

        hcs_score = await research_hcs_score_full(query, final_answer)
        if hcs_score.get("status") == "success":
            response["hcs_scores"] = hcs_score.get("scores", {})
            logger.info("deep_hcs_score computed hcs_10=%.2f", hcs_score.get("scores", {}).get("hcs_10", 0))
    except ImportError:
        logger.debug("hcs_multi_scorer not available, skipping hcs scoring")
    except Exception as exc:
        logger.warning("deep_hcs_scoring_failed (non-blocking): %s", exc)

    return response
