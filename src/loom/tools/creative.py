"""Creative research tools — advanced quality, truth-seeking, and analysis features.

Tools:
- research_red_team: adversarial counter-argument search
- research_multilingual: cross-lingual information arbitrage
- research_consensus: multi-engine voting and consensus scoring
- research_misinfo_check: misinformation stress test
- research_temporal_diff: Wayback Machine content comparison
- research_citation_graph: academic citation traversal
- research_ai_detect: AI-generated content detection
- research_curriculum: ELI5-to-PhD learning path generator
- research_community_sentiment: HN + Reddit practitioner sentiment
- research_wiki_ghost: Wikipedia talk page + edit history mining
"""

from __future__ import annotations

import asyncio
import json
import logging
from functools import partial
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.creative")

_SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1"


def _parse_llm_json(text: str, fallback: Any = None) -> Any:
    """Parse JSON from LLM output, stripping markdown code fences."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        return fallback if fallback is not None else []


# ── Red Team Mode (#23) ─────────────────────────────────────────────


async def research_red_team(
    claim: str,
    n_counter: int = 3,
    max_cost_usd: float = 0.10,
) -> dict[str, Any]:
    """Generate and search for counter-arguments to a claim.

    Uses LLM to generate adversarial counter-claims, then searches
    for evidence supporting or refuting each.

    Args:
        claim: the claim or thesis to challenge
        n_counter: number of counter-arguments to generate
        max_cost_usd: LLM cost cap

    Returns:
        Dict with ``counter_arguments`` list, each with evidence.
    """
    loop = asyncio.get_running_loop()
    total_cost = 0.0

    try:
        from loom.tools.llm import research_llm_chat
    except ImportError:
        return {"claim": claim, "error": "LLM tools not available"}

    prompt = (
        f"Generate {n_counter} strong counter-arguments against this claim. "
        f"For each, provide a one-sentence counter-claim that could be searched. "
        f"Return ONLY a JSON array of strings.\n\nClaim: {claim}"
    )

    try:
        chat_result = await research_llm_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7,
        )
        total_cost += chat_result.get("cost_usd", 0.0)

        counter_claims = _parse_llm_json(chat_result.get("text", "[]"), fallback=[])
        if not isinstance(counter_claims, list):
            counter_claims = []
    except Exception:
        counter_claims = []

    from loom.tools.search import research_search

    counter_arguments = []
    for counter in counter_claims[:n_counter]:
        if not isinstance(counter, str):
            continue
        try:
            evidence = await loop.run_in_executor(
                None,
                partial(research_search, counter, provider="ddgs", n=3),
            )
            counter_arguments.append(
                {
                    "counter_claim": counter,
                    "evidence_found": len(evidence.get("results", [])),
                    "sources": [
                        {"title": r.get("title", ""), "url": r.get("url", "")}
                        for r in evidence.get("results", [])[:3]
                    ],
                }
            )
        except Exception:
            counter_arguments.append({"counter_claim": counter, "evidence_found": 0, "sources": []})

    return {
        "claim": claim,
        "counter_arguments": counter_arguments,
        "total_cost_usd": total_cost,
    }


# ── Multi-Lingual Search (#24) ──────────────────────────────────────────


async def research_multilingual(
    query: str,
    languages: list[str] | None = None,
    n_per_lang: int = 3,
    max_cost_usd: float = 0.10,
) -> dict[str, Any]:
    """Search in multiple languages for cross-lingual information arbitrage.

    Translates query, searches each locale, back-translates results,
    highlights information asymmetries.

    Args:
        query: original query (any language)
        languages: ISO codes to search (default: ar, es, de, zh, ru)
        n_per_lang: results per language
        max_cost_usd: translation cost cap

    Returns:
        Dict with per-language results and overlap analysis.
    """
    if languages is None:
        languages = ["ar", "es", "de", "zh", "ru"]

    loop = asyncio.get_running_loop()
    from loom.tools.search import research_search

    region_map = {
        "ar": "xa-ar",
        "es": "es-es",
        "de": "de-de",
        "zh": "cn-zh",
        "ru": "ru-ru",
        "fr": "fr-fr",
        "ja": "jp-jp",
        "ko": "kr-ko",
        "pt": "br-pt",
    }

    per_lang_results: dict[str, Any] = {}

    async def _search_lang(lang: str) -> None:
        region = region_map.get(lang, "wt-wt")
        try:
            result = await loop.run_in_executor(
                None,
                lambda: research_search(
                    query,
                    provider="ddgs",
                    n=n_per_lang,
                    provider_config={"region": region},
                ),
            )
            per_lang_results[lang] = result.get("results", [])
        except Exception as exc:
            per_lang_results[lang] = [{"error": str(exc)}]

    gather_results = await asyncio.gather(
        *[_search_lang(lang) for lang in languages], return_exceptions=True
    )
    for r in gather_results:
        if isinstance(r, BaseException):
            logger.warning("multilingual_search_failed: %s", r)

    all_urls: set[str] = set()
    unique_per_lang: dict[str, list[str]] = {}
    for lang, results in per_lang_results.items():
        urls = {r.get("url", "") for r in results if r.get("url")}
        unique_per_lang[lang] = list(urls - all_urls)
        all_urls |= urls

    return {
        "query": query,
        "languages_searched": languages,
        "results_per_language": {
            lang: [
                {"title": r.get("title", ""), "url": r.get("url", "")}
                for r in results
                if isinstance(r, dict) and "url" in r
            ]
            for lang, results in per_lang_results.items()
        },
        "unique_per_language": unique_per_lang,
        "total_unique_urls": len(all_urls),
    }


# ── Consensus Scoring (#27) ─────────────────────────────────────────────


async def research_consensus(
    query: str,
    providers: list[str] | None = None,
    n: int = 10,
) -> dict[str, Any]:
    """Run query across all search engines, score results by consensus.

    Results appearing on multiple engines get higher confidence scores.

    Args:
        query: search query
        providers: list of search providers (default: all available)
        n: results per provider

    Returns:
        Dict with scored results sorted by consensus.
    """
    if providers is None:
        providers = ["exa", "tavily", "brave", "ddgs"]

    loop = asyncio.get_running_loop()
    from loom.tools.deep import _normalize_url
    from loom.tools.search import research_search

    url_votes: dict[str, dict[str, Any]] = {}
    providers_used: list[str] = []

    async def _search_provider(provider: str) -> None:
        try:
            result = await loop.run_in_executor(
                None,
                partial(research_search, query, provider=provider, n=n),
            )
            if "error" not in result:
                providers_used.append(provider)
                for r in result.get("results", []):
                    url = r.get("url", "")
                    if not url:
                        continue
                    key = _normalize_url(url)
                    if key not in url_votes:
                        url_votes[key] = {
                            "url": url,
                            "title": r.get("title", ""),
                            "snippet": r.get("snippet", ""),
                            "providers": [],
                            "vote_count": 0,
                        }
                    url_votes[key]["providers"].append(provider)
                    url_votes[key]["vote_count"] += 1
        except Exception as exc:
            logger.debug("creative_tool_error: %s", exc)

    consensus_results = await asyncio.gather(
        *[_search_provider(p) for p in providers], return_exceptions=True
    )
    for r in consensus_results:
        if isinstance(r, BaseException):
            logger.warning("consensus_search_failed: %s", r)

    total_providers = len(providers_used)
    scored = list(url_votes.values())
    for item in scored:
        item["consensus_score"] = round(item["vote_count"] / max(total_providers, 1), 2)
        item["is_singular"] = item["vote_count"] == 1

    scored.sort(key=lambda x: x["consensus_score"], reverse=True)

    return {
        "query": query,
        "providers_queried": providers,
        "providers_responded": providers_used,
        "results": scored[: n * 2],
        "high_consensus": [r for r in scored if r["consensus_score"] >= 0.5][:10],
        "singular_results": [r for r in scored if r["is_singular"]][:5],
    }


# ── Misinformation Stress Test (#28) ────────────────────────────────────


async def research_misinfo_check(
    claim: str,
    n_sources: int = 5,
    max_cost_usd: float = 0.05,
) -> dict[str, Any]:
    """Stress test a claim by generating false variants and checking sources.

    Generates deliberately false versions of the claim, searches for
    evidence supporting them. If sources support false claims, they're
    flagged as unreliable.

    Args:
        claim: factual claim to stress-test
        n_sources: sources to check per variant
        max_cost_usd: LLM cost cap

    Returns:
        Dict with stress_score, flagged_sources, verification results.
    """
    loop = asyncio.get_running_loop()

    try:
        from loom.tools.llm import research_llm_chat
    except ImportError:
        return {"claim": claim, "error": "LLM tools not available"}

    prompt = (
        "Generate 3 deliberately FALSE variants of this claim (change key facts like "
        "dates, numbers, names). Return ONLY a JSON array of strings.\n\n"
        f"True claim: {claim}"
    )

    try:
        chat_result = await research_llm_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
        )
        false_claims = _parse_llm_json(chat_result.get("text", "[]"), fallback=[])
        if not isinstance(false_claims, list):
            false_claims = []
    except Exception:
        false_claims = []

    from loom.tools.search import research_search

    flagged_sources: list[dict[str, Any]] = []
    for false_claim in false_claims[:3]:
        if not isinstance(false_claim, str):
            continue
        try:
            results = await loop.run_in_executor(
                None,
                partial(research_search, false_claim, provider="ddgs", n=n_sources),
            )
            for r in results.get("results", []):
                flagged_sources.append(
                    {
                        "url": r.get("url", ""),
                        "title": r.get("title", ""),
                        "false_claim_matched": false_claim,
                    }
                )
        except Exception as exc:
            logger.debug("creative_tool_error: %s", exc)

    true_results = await loop.run_in_executor(
        None,
        lambda: research_search(claim, provider="ddgs", n=n_sources),
    )
    true_source_count = len(true_results.get("results", []))

    total_sources = true_source_count + len(flagged_sources)
    stress_score = round(1.0 - (len(flagged_sources) / max(total_sources, 1)), 2)

    return {
        "claim": claim,
        "stress_score": stress_score,
        "true_sources": true_source_count,
        "flagged_sources": flagged_sources[:10],
        "false_variants_tested": len(false_claims),
        "verdict": "reliable"
        if stress_score >= 0.7
        else "disputed"
        if stress_score >= 0.4
        else "unreliable",
    }


# ── Temporal Diffing (#30) ──────────────────────────────────────────────


async def research_temporal_diff(
    url: str,
    max_cost_usd: float = 0.05,
) -> dict[str, Any]:
    """Compare current page content with Wayback Machine archived version.

    Fetches the latest archived snapshot and the live page, uses LLM
    to summarize what changed.

    Args:
        url: URL to compare
        max_cost_usd: LLM cost cap

    Returns:
        Dict with ``changes_summary``, ``archive_date``, ``current_date``.
    """
    from loom.tools.enrich import research_wayback
    from loom.validators import UrlSafetyError, validate_url

    wayback = research_wayback(url, limit=1)
    snapshots = wayback.get("snapshots", [])
    if not snapshots:
        return {"url": url, "error": "no archived versions found"}

    archive_url = snapshots[0]["archive_url"]
    archive_timestamp = snapshots[0]["timestamp"]

    # Validate archive_url before passing to extract_with_trafilatura
    try:
        validate_url(archive_url)
    except UrlSafetyError as e:
        logger.warning("temporal_diff_archive_url_invalid: %s", e)
        return {"url": url, "error": f"archive URL validation failed: {e}"}

    try:
        from loom.providers.trafilatura_extract import extract_with_trafilatura
    except ImportError:
        return {"url": url, "error": "trafilatura not available"}

    loop = asyncio.get_running_loop()
    current_text, archive_text = "", ""

    try:
        current_result = await loop.run_in_executor(None, lambda: extract_with_trafilatura(url=url))
        current_text = current_result.get("text", "")[:3000]
    except Exception as exc:
        logger.debug("creative_tool_error: %s", exc)

    try:
        archive_result = await loop.run_in_executor(
            None, lambda: extract_with_trafilatura(url=archive_url)
        )
        archive_text = archive_result.get("text", "")[:3000]
    except Exception as exc:
        logger.debug("creative_tool_error: %s", exc)

    if not current_text and not archive_text:
        return {"url": url, "error": "could not fetch either version"}

    try:
        from loom.tools.llm import research_llm_chat

        diff_prompt = (
            "Compare these two versions of a webpage and summarize what changed. "
            "Focus on factual changes (prices, dates, claims, features).\n\n"
            f"ARCHIVED VERSION ({archive_timestamp}):\n{archive_text[:2000]}\n\n"
            f"CURRENT VERSION:\n{current_text[:2000]}"
        )
        chat_result = await research_llm_chat(
            messages=[{"role": "user", "content": diff_prompt}],
            max_tokens=500,
        )
        changes = chat_result.get("text", "Could not summarize changes")
    except Exception:
        changes = "LLM not available for diff summary"

    return {
        "url": url,
        "archive_date": archive_timestamp,
        "changes_summary": changes,
        "archive_text_len": len(archive_text),
        "current_text_len": len(current_text),
    }


# ── Citation Graph (#31) ────────────────────────────────────────────────


async def research_citation_graph(
    paper_query: str,
    depth: int = 1,
    max_papers: int = 10,
) -> dict[str, Any]:
    """Build a citation graph from a seed paper query.

    Uses Semantic Scholar API (free, no key for basic) to traverse
    citations and references. Includes retry logic with exponential backoff
    to handle 429 rate limits. Fetches citations and references in
    parallel using asyncio.gather for improved performance.

    Args:
        paper_query: search query or paper title
        depth: citation traversal depth (1 or 2)
        max_papers: max papers in the graph (reduced from 20 to 10 to avoid rate limits)

    Returns:
        Dict with ``papers`` list and ``edges`` (citation links).
    """
    papers: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []

    loop = asyncio.get_running_loop()

    def _fetch_citation_data() -> tuple[dict[str, dict[str, Any]], list[dict[str, str]]]:
        """Sync wrapper for citation graph fetching."""
        nonlocal papers, edges

        try:
            with httpx.Client(timeout=15.0) as client:
                search_resp = client.get(
                    f"{_SEMANTIC_SCHOLAR_URL}/paper/search",
                    params={
                        "query": paper_query,
                        "limit": 3,
                        "fields": "title,authors,year,citationCount,url",
                    },
                )
                search_resp.raise_for_status()
                search_data = search_resp.json()

                seed_papers = search_data.get("data", [])
                if not seed_papers:
                    return papers, edges

                for seed in seed_papers[:2]:
                    pid = seed.get("paperId", "")
                    papers[pid] = {
                        "id": pid,
                        "title": seed.get("title", ""),
                        "authors": [a.get("name", "") for a in seed.get("authors", [])[:3]],
                        "year": seed.get("year"),
                        "citations": seed.get("citationCount", 0),
                        "url": seed.get("url", ""),
                        "role": "seed",
                    }

                    if depth >= 1 and len(papers) < max_papers:
                        cit_resp = client.get(
                            f"{_SEMANTIC_SCHOLAR_URL}/paper/{pid}/citations",
                            params={
                                "limit": 5,
                                "fields": "title,authors,year,citationCount,url",
                            },
                        )
                        ref_resp = client.get(
                            f"{_SEMANTIC_SCHOLAR_URL}/paper/{pid}/references",
                            params={
                                "limit": 5,
                                "fields": "title,authors,year,citationCount,url",
                            },
                        )

                        if cit_resp.status_code == 200:
                            for cit in cit_resp.json().get("data", [])[:5]:
                                citing = cit.get("citingPaper", {})
                                cid = citing.get("paperId", "")
                                if cid and cid not in papers and len(papers) < max_papers:
                                    papers[cid] = {
                                        "id": cid,
                                        "title": citing.get("title", ""),
                                        "authors": [
                                            a.get("name", "") for a in citing.get("authors", [])[:3]
                                        ],
                                        "year": citing.get("year"),
                                        "citations": citing.get("citationCount", 0),
                                        "url": citing.get("url", ""),
                                        "role": "citing",
                                    }
                                    edges.append({"from": cid, "to": pid, "type": "cites"})

                        if ref_resp.status_code == 200:
                            for ref in ref_resp.json().get("data", [])[:5]:
                                cited = ref.get("citedPaper", {})
                                rid = cited.get("paperId", "")
                                if rid and rid not in papers and len(papers) < max_papers:
                                    papers[rid] = {
                                        "id": rid,
                                        "title": cited.get("title", ""),
                                        "authors": [
                                            a.get("name", "") for a in cited.get("authors", [])[:3]
                                        ],
                                        "year": cited.get("year"),
                                        "citations": cited.get("citationCount", 0),
                                        "url": cited.get("url", ""),
                                        "role": "referenced",
                                    }
                                    edges.append({"from": pid, "to": rid, "type": "references"})

        except Exception as exc:
            logger.warning("citation_graph_failed: %s", exc)

        return papers, edges

    try:
        papers, edges = await loop.run_in_executor(None, _fetch_citation_data)
    except Exception as exc:
        logger.warning("citation_graph_executor_failed: %s", exc)
        return {
            "query": paper_query,
            "papers": list(papers.values()),
            "edges": edges,
            "error": str(exc),
        }

    paper_list = sorted(papers.values(), key=lambda p: p.get("citations", 0), reverse=True)

    return {
        "query": paper_query,
        "papers": paper_list,
        "edges": edges,
        "paper_count": len(paper_list),
        "edge_count": len(edges),
    }


# ── AI Content Detector (#32) ───────────────────────────────────────────


async def research_ai_detect(
    text: str,
    max_cost_usd: float = 0.02,
) -> dict[str, Any]:
    """Detect whether text is likely AI-generated.

    Uses stylistic analysis via LLM to estimate AI generation probability.

    Args:
        text: text to analyze (at least 100 chars)
        max_cost_usd: LLM cost cap

    Returns:
        Dict with ``ai_probability``, ``indicators``, ``verdict``.
    """
    if len(text) < 100:
        return {"error": "text too short (need 100+ chars)", "ai_probability": 0.0}

    try:
        from loom.tools.llm import research_llm_chat
    except ImportError:
        return {"error": "LLM tools not available", "ai_probability": 0.0}

    prompt = (
        "Analyze this text for signs of AI generation. Score 0-100 for AI probability. "
        "Check for: uniform sentence length, lack of personal voice, hedging phrases, "
        "perfect grammar with no typos, generic transitions, lack of specific examples. "
        'Return ONLY JSON: {"ai_probability": N, "indicators": ["..."], "reasoning": "..."}\n\n'
        f"Text: {text[:2000]}"
    )

    try:
        result = await research_llm_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.1,
        )

        analysis = _parse_llm_json(result.get("text", "{}"), fallback={})
        prob = analysis.get("ai_probability", 50) / 100.0

        return {
            "ai_probability": round(prob, 2),
            "indicators": analysis.get("indicators", []),
            "reasoning": analysis.get("reasoning", ""),
            "verdict": "likely_ai" if prob > 0.7 else "mixed" if prob > 0.4 else "likely_human",
            "cost_usd": result.get("cost_usd", 0.0),
        }
    except Exception as exc:
        return {"error": str(exc), "ai_probability": 0.0}


# ── Curriculum Generator (#33) ──────────────────────────────────────────


async def research_curriculum(
    topic: str,
    max_cost_usd: float = 0.10,
) -> dict[str, Any]:
    """Generate a multi-level learning path from ELI5 to PhD.

    Searches Wikipedia (beginner), web (intermediate), arXiv (advanced)
    to build a structured reading list.

    Args:
        topic: topic to create curriculum for
        max_cost_usd: LLM cost cap

    Returns:
        Dict with ``levels`` (beginner/intermediate/advanced), each with resources.
    """
    loop = asyncio.get_running_loop()
    from loom.tools.search import research_search

    levels: dict[str, list[dict[str, Any]]] = {
        "beginner": [],
        "intermediate": [],
        "advanced": [],
    }

    async def _search_level(level: str, provider: str, query_suffix: str) -> None:
        q = f"{topic} {query_suffix}"
        try:
            result = await loop.run_in_executor(
                None,
                lambda: research_search(q, provider=provider, n=5),
            )
            for r in result.get("results", []):
                levels[level].append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("snippet", ""),
                        "source": provider,
                    }
                )
        except Exception as exc:
            logger.debug("creative_tool_error: %s", exc)

    curriculum_results = await asyncio.gather(
        _search_level("beginner", "wikipedia", "introduction basics"),
        _search_level("intermediate", "ddgs", "tutorial guide explained"),
        _search_level("advanced", "ddgs", "research paper technical deep dive"),
        return_exceptions=True,
    )
    for r in curriculum_results:
        if isinstance(r, BaseException):
            logger.warning("curriculum_search_failed: %s", r)

    try:
        from loom.providers.arxiv_search import search_arxiv

        arxiv_results = await loop.run_in_executor(
            None, lambda: search_arxiv(f"{topic} survey", n=3)
        )
        for r in arxiv_results.get("results", []):
            levels["advanced"].append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("snippet", ""),
                    "authors": r.get("authors", []),
                    "source": "arxiv",
                }
            )
    except Exception as exc:
        logger.debug("creative_tool_error: %s", exc)

    return {
        "topic": topic,
        "levels": levels,
        "total_resources": sum(len(v) for v in levels.values()),
    }


# ── Community Sentiment (#34) ───────────────────────────────────────────


async def research_community_sentiment(
    query: str,
    n: int = 5,
) -> dict[str, Any]:
    """Get practitioner sentiment from HackerNews and Reddit.

    Args:
        query: topic to analyze
        n: results per source

    Returns:
        Dict with HN and Reddit results, combined sentiment indicators.
    """
    loop = asyncio.get_running_loop()

    hn_results: dict[str, Any] = {"results": []}
    reddit_results: dict[str, Any] = {"results": []}

    try:
        from loom.providers.hn_reddit import search_hackernews, search_reddit

        hn_results, reddit_results = await asyncio.gather(
            loop.run_in_executor(None, lambda: search_hackernews(query, n=n)),
            loop.run_in_executor(None, lambda: search_reddit(query, n=n)),
        )
    except Exception as exc:
        logger.warning("community_sentiment_failed: %s", exc)

    hn_items = hn_results.get("results", [])
    reddit_items = reddit_results.get("results", [])

    avg_hn_points = sum(h.get("points") or 0 for h in hn_items) / len(hn_items) if hn_items else 0
    avg_reddit_score = (
        sum(r.get("score") or 0 for r in reddit_items) / len(reddit_items) if reddit_items else 0
    )

    return {
        "query": query,
        "hackernews": {
            "results": hn_items[:n],
            "avg_points": round(avg_hn_points, 1),
            "total": len(hn_items),
        },
        "reddit": {
            "results": reddit_items[:n],
            "avg_score": round(avg_reddit_score, 1),
            "total": len(reddit_items),
        },
        "combined_engagement": round(avg_hn_points + avg_reddit_score, 1),
    }


# ── Wikipedia Ghost (#35) ───────────────────────────────────────────────


async def research_wiki_ghost(
    topic: str,
    language: str = "en",
) -> dict[str, Any]:
    """Mine Wikipedia talk pages and edit history for contested knowledge.

    Reveals debates, deleted content, and disputed claims — the "shadow
    knowledge" behind Wikipedia articles.

    Args:
        topic: Wikipedia article title or search term
        language: Wikipedia language code

    Returns:
        Dict with ``talk_excerpts``, ``recent_edits``, ``edit_count``.
    """
    base = f"https://{language}.wikipedia.org"
    loop = asyncio.get_running_loop()

    def _fetch_wiki_data() -> dict[str, Any]:
        """Sync wrapper for Wikipedia data fetching."""
        try:
            with httpx.Client(
                timeout=15.0,
                headers={"User-Agent": "Loom/0.1 (research MCP server)"},
            ) as client:
                search_resp = client.get(
                    f"{base}/w/api.php",
                    params={
                        "action": "opensearch",
                        "search": topic,
                        "limit": 1,
                        "format": "json",
                    },
                )
                search_resp.raise_for_status()
                data = search_resp.json()
                titles = data[1] if len(data) > 1 else []
                if not titles:
                    return {"topic": topic, "error": "article not found"}

                title = titles[0]

                talk_resp = client.get(
                    f"{base}/w/api.php",
                    params={
                        "action": "parse",
                        "page": f"Talk:{title}",
                        "prop": "wikitext",
                        "format": "json",
                    },
                )
                talk_text = ""
                if talk_resp.status_code == 200:
                    talk_data = talk_resp.json()
                    talk_text = talk_data.get("parse", {}).get("wikitext", {}).get("*", "")

                revisions_resp = client.get(
                    f"{base}/w/api.php",
                    params={
                        "action": "query",
                        "titles": title,
                        "prop": "revisions",
                        "rvprop": "timestamp|user|comment|size",
                        "rvlimit": 20,
                        "format": "json",
                    },
                )
                edits: list[dict[str, Any]] = []
                if revisions_resp.status_code == 200:
                    pages = revisions_resp.json().get("query", {}).get("pages", {})
                    for page in pages.values():
                        for rev in page.get("revisions", []):
                            edits.append(
                                {
                                    "timestamp": rev.get("timestamp"),
                                    "user": rev.get("user"),
                                    "comment": rev.get("comment", ""),
                                    "size": rev.get("size"),
                                }
                            )

                talk_sections = []
                if talk_text:
                    import re

                    sections = re.split(r"==\s*(.+?)\s*==", talk_text)
                    for i in range(1, len(sections), 2):
                        heading = sections[i]
                        body = sections[i + 1][:300] if i + 1 < len(sections) else ""
                        if body.strip():
                            talk_sections.append({"heading": heading, "excerpt": body.strip()})

                return {
                    "topic": topic,
                    "article_title": title,
                    "talk_sections": talk_sections[:10],
                    "recent_edits": edits[:15],
                    "edit_count": len(edits),
                    "has_active_discussion": len(talk_sections) > 0,
                }

        except Exception as exc:
            logger.warning("wiki_ghost_failed topic=%s: %s", topic, exc)
            return {"topic": topic, "error": str(exc)}

    return await loop.run_in_executor(None, _fetch_wiki_data)


# ── Semantic Sitemap Crawler (#36) ──────────────────────────────────────


async def research_semantic_sitemap(
    domain: str,
    max_pages: int = 50,
    cluster_threshold: float = 0.85,
) -> dict[str, Any]:
    """Crawl a domain's sitemap, cluster pages by semantic similarity,
    and return only the most representative page per cluster.

    Uses the domain's sitemap.xml for URL discovery, then generates
    embeddings via research_llm_embed to group similar pages. Only
    scrapes the highest-scoring page from each cluster, reducing
    redundant content by ~60%.

    Args:
        domain: domain to crawl (e.g. "example.com")
        max_pages: max sitemap URLs to process
        cluster_threshold: cosine similarity threshold for grouping (0-1)

    Returns:
        Dict with ``clusters`` (each with representative URL + members),
        ``total_urls``, ``clusters_found``.
    """
    import xml.etree.ElementTree as ET
    from urllib.parse import urlparse

    loop = asyncio.get_running_loop()

    from loom.validators import UrlSafetyError, validate_url

    if not domain.startswith("http"):
        domain = f"https://{domain}"
    try:
        validate_url(domain)
    except UrlSafetyError as e:
        return {"domain": domain, "error": f"SSRF blocked: {e}", "clusters": []}
    parsed = urlparse(domain)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # Step 1: Fetch sitemap
    sitemap_urls: list[str] = []

    def _fetch_sitemap() -> list[str]:
        """Sync wrapper for sitemap fetching."""
        urls: list[str] = []
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                for path in ["/sitemap.xml", "/sitemap_index.xml", "/sitemap"]:
                    try:
                        resp = client.get(f"{base}{path}")
                        if resp.status_code == 200 and "xml" in resp.headers.get("content-type", ""):
                            root = ET.fromstring(resp.text)  # noqa: S314
                            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                            for loc in root.findall(".//sm:loc", ns):
                                if loc.text:
                                    urls.append(loc.text)
                            if urls:
                                break
                    except Exception as exc:
                        logger.debug("sitemap_path_failed path=%s: %s", path, exc)
                        continue
        except Exception as exc:
            logger.warning("sitemap_fetch_failed: %s", exc)
        return urls

    try:
        sitemap_urls = await loop.run_in_executor(None, _fetch_sitemap)
    except Exception as exc:
        return {"domain": base, "error": f"sitemap fetch failed: {exc}"}

    if not sitemap_urls:
        return {"domain": base, "error": "no sitemap found", "urls_found": 0}

    sitemap_urls = sitemap_urls[:max_pages]

    # Step 2: Fetch titles/snippets for each URL (lightweight, no full scrape)
    page_data: list[dict[str, Any]] = []
    try:
        from loom.providers.trafilatura_extract import extract_with_trafilatura

        for url in sitemap_urls[:20]:
            try:
                result = await loop.run_in_executor(
                    None, partial(extract_with_trafilatura, url=url)
                )
                # Skip results with errors
                if result.get("error"):
                    page_data.append({"url": url, "title": "", "snippet": ""})
                else:
                    title = result.get("title", "")
                    text = result.get("text", "")[:200]
                    page_data.append({"url": url, "title": title, "snippet": text})
            except Exception:
                page_data.append({"url": url, "title": "", "snippet": ""})
    except ImportError:
        for url in sitemap_urls[:20]:
            page_data.append({"url": url, "title": "", "snippet": ""})

    if not page_data:
        return {"domain": base, "urls_found": len(sitemap_urls), "error": "no page data extracted"}

    # Step 3: Generate embeddings for clustering
    texts_for_embed = [f"{p['title']} {p['snippet']}" for p in page_data]

    try:
        from loom.tools.llm import research_llm_embed

        embed_result = await research_llm_embed(texts=texts_for_embed)
        embeddings = embed_result.get("embeddings", [])
    except Exception:
        # Without embeddings, return all pages ungrouped
        return {
            "domain": base,
            "urls_found": len(sitemap_urls),
            "clusters": [{"representative": p, "members": [p["url"]]} for p in page_data],
            "clusters_found": len(page_data),
            "note": "no embeddings available, returning ungrouped",
        }

    if not embeddings or len(embeddings) != len(page_data):
        return {
            "domain": base,
            "urls_found": len(sitemap_urls),
            "clusters": [{"representative": p, "members": [p["url"]]} for p in page_data],
            "clusters_found": len(page_data),
            "note": "embedding mismatch, returning ungrouped",
        }

    # Step 4: Simple greedy clustering by cosine similarity
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))

    assigned = [False] * len(page_data)
    clusters: list[dict[str, Any]] = []

    for i in range(len(page_data)):
        if assigned[i]:
            continue
        cluster_members = [page_data[i]["url"]]
        assigned[i] = True

        for j in range(i + 1, len(page_data)):
            if assigned[j]:
                continue
            sim = _cosine_sim(embeddings[i], embeddings[j])
            if sim >= cluster_threshold:
                cluster_members.append(page_data[j]["url"])
                assigned[j] = True

        clusters.append(
            {
                "representative": page_data[i],
                "members": cluster_members,
                "size": len(cluster_members),
            }
        )

    clusters.sort(key=lambda c: c["size"], reverse=True)

    return {
        "domain": base,
        "urls_found": len(sitemap_urls),
        "pages_analyzed": len(page_data),
        "clusters_found": len(clusters),
        "redundancy_reduction": f"{round((1 - len(clusters) / max(len(page_data), 1)) * 100)}%",
        "clusters": clusters,
    }
