#!/usr/bin/env python3
"""
Research 701: Proactive Adversarial Patching (Standalone Version)
================================================================

Task: Research proactive adversarial defense and attack prediction methodologies.

This is a standalone version that can run independently on Hetzner.
It implements the multi_search functionality inline to avoid dependency issues.

Search queries:
1. "proactive adversarial defense LLM anticipate attacks 2025 2026"
2. "red team automation continuous testing AI"
3. "predictive vulnerability discovery machine learning"

Output: /opt/research-toolbox/tmp/research_701_proactive.json

Author: Ahmed Adel Bakr Alderai
Date: 2026-05-01
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse, unquote

import httpx

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("research_701_standalone")


async def _get_json(
    client: httpx.AsyncClient, url: str, headers: dict[str, str] | None = None
) -> Any:
    """Fetch and parse JSON from URL."""
    try:
        resp = await client.get(url, timeout=15.0, headers=headers or {})
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("json fetch failed: %s", exc)
    return None


async def _get_text(client: httpx.AsyncClient, url: str) -> str:
    """Fetch raw text from URL."""
    try:
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("text fetch failed: %s", exc)
    return ""


async def _search_hackernews(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    """Search HackerNews API."""
    url = f"https://hn.algolia.com/api/v1/search?query={quote(query)}&hitsPerPage=10"
    data = await _get_json(client, url)
    if not data:
        return []
    return [
        {
            "title": hit.get("title", hit.get("story_title", "")),
            "url": hit.get("url", f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"),
            "source": "hackernews",
            "snippet": hit.get("_highlightResult", {}).get("title", {}).get("value", ""),
            "score": hit.get("points", 0),
        }
        for hit in data.get("hits", [])[:10]
        if hit.get("title") or hit.get("story_title")
    ]


async def _search_reddit(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    """Search Reddit API."""
    url = f"https://www.reddit.com/search.json?q={quote(query)}&limit=10&sort=relevance"
    data = await _get_json(
        client,
        url,
        headers={"User-Agent": "Loom-Research/1.0"},
    )
    if not data:
        return []
    children = data.get("data", {}).get("children", [])
    return [
        {
            "title": child["data"].get("title", ""),
            "url": child["data"].get("url", ""),
            "source": "reddit",
            "snippet": child["data"].get("selftext", "")[:200],
            "score": child["data"].get("score", 0),
        }
        for child in children[:10]
        if child.get("data", {}).get("title")
    ]


async def _search_wikipedia(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    """Search Wikipedia API."""
    url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={quote(query)}&format=json&srlimit=5"
    data = await _get_json(client, url)
    if not data:
        return []
    results = data.get("query", {}).get("search", [])
    return [
        {
            "title": r.get("title", ""),
            "url": f"https://en.wikipedia.org/wiki/{quote(r.get('title', '').replace(' ', '_'))}",
            "source": "wikipedia",
            "snippet": re.sub(r"<[^>]+>", "", r.get("snippet", "")),
            "score": r.get("wordcount", 0),
        }
        for r in results[:5]
    ]


async def _search_arxiv(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    """Search arXiv API."""
    url = f"http://export.arxiv.org/api/query?search_query=all:{quote(query)}&max_results=5"
    text = await _get_text(client, url)
    if not text:
        return []
    results: list[dict[str, Any]] = []
    for match in re.finditer(r"<entry>(.*?)</entry>", text, re.DOTALL):
        entry = match.group(1)
        title_m = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
        link_m = re.search(r'<id>(.*?)</id>', entry)
        summary_m = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
        if title_m:
            results.append(
                {
                    "title": title_m.group(1).strip().replace("\n", " "),
                    "url": link_m.group(1).strip() if link_m else "",
                    "source": "arxiv",
                    "snippet": summary_m.group(1).strip()[:200] if summary_m else "",
                    "score": 0,
                }
            )
    return results[:5]


async def _search_ddgs(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    """Search DuckDuckGo."""
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    text = await _get_text(client, url)
    if not text:
        return []
    results: list[dict[str, Any]] = []
    for match in re.finditer(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</',
        text,
        re.DOTALL,
    ):
        url_match = match.group(1)
        if url_match.startswith("//duckduckgo.com/l/?uddg="):
            url_match = unquote(url_match.split("uddg=")[1].split("&")[0])
        results.append(
            {
                "title": re.sub(r"<[^>]+>", "", match.group(2)).strip(),
                "url": url_match,
                "source": "duckduckgo",
                "snippet": re.sub(r"<[^>]+>", "", match.group(3)).strip()[:200],
                "score": 0,
            }
        )
    return results[:10]


def _deduplicate(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove duplicate results by URL."""
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for r in results:
        url = r.get("url", "")
        if not url:
            continue
        parsed = urlparse(url)
        key = f"{parsed.netloc}{parsed.path}".lower().rstrip("/")
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def _rank_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rank results by source weight and score."""
    source_weights = {
        "wikipedia": 5,
        "arxiv": 4,
        "hackernews": 3,
        "reddit": 3,
        "duckduckgo": 3,
        "marginalia": 2,
        "crt.sh": 1,
    }
    for r in results:
        base_score = r.get("score", 0)
        source_weight = source_weights.get(r.get("source", ""), 1)
        r["rank_score"] = base_score + source_weight * 10
    return sorted(results, key=lambda x: x.get("rank_score", 0), reverse=True)


async def research_multi_search(
    query: str,
    engines: list[str] | None = None,
    max_results: int = 50,
) -> dict[str, Any]:
    """Query multiple search engines and return unified, ranked results."""
    default_engines = [
        "duckduckgo",
        "hackernews",
        "reddit",
        "wikipedia",
        "arxiv",
    ]
    active_engines = engines or default_engines

    engine_map = {
        "duckduckgo": _search_ddgs,
        "hackernews": _search_hackernews,
        "reddit": _search_reddit,
        "wikipedia": _search_wikipedia,
        "arxiv": _search_arxiv,
    }

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "Loom-Research/1.0"},
        timeout=30.0,
    ) as client:
        tasks = []
        engines_used = []
        for eng in active_engines:
            if eng in engine_map:
                tasks.append(engine_map[eng](client, query))
                engines_used.append(eng)

        all_results_raw = await asyncio.gather(*tasks, return_exceptions=True)

        all_results: list[dict[str, Any]] = []
        for result in all_results_raw:
            if isinstance(result, list):
                all_results.extend(result)

        total_raw = len(all_results)
        deduped = _deduplicate(all_results)
        ranked = _rank_results(deduped)[:max_results]

        source_breakdown: dict[str, int] = {}
        for r in ranked:
            src = r.get("source", "unknown")
            source_breakdown[src] = source_breakdown.get(src, 0) + 1

        return {
            "query": query,
            "engines_queried": engines_used,
            "total_raw_results": total_raw,
            "total_deduplicated": len(ranked),
            "results": ranked,
            "sources_breakdown": source_breakdown,
        }


def parse_research_results(multi_search_output: dict[str, Any]) -> dict[str, Any]:
    """Parse multi_search output into structured research findings."""
    query = multi_search_output.get("query", "")
    results = multi_search_output.get("results", [])

    findings = {
        "query": query,
        "result_count": len(results),
        "sources": multi_search_output.get("sources_breakdown", {}),
        "key_results": [],
    }

    # Extract top 5 results
    for i, result in enumerate(results[:5], 1):
        finding = {
            "rank": i,
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "source": result.get("source", ""),
            "snippet": result.get("snippet", "")[:300],
            "score": result.get("rank_score", 0),
        }
        findings["key_results"].append(finding)

    return findings


async def main() -> None:
    """Execute proactive adversarial patching research."""
    logger.info("Starting Research 701: Proactive Adversarial Patching")

    # Research queries
    queries = [
        "proactive adversarial defense LLM anticipate attacks 2025 2026",
        "red team automation continuous testing AI",
        "predictive vulnerability discovery machine learning",
    ]

    research_output: dict[str, Any] = {
        "research_id": "701_proactive_adversarial_patching",
        "title": "Proactive Adversarial Patching: Anticipate & Defend Against Attacks",
        "description": "Research on proactive defense methodologies, attack prediction, continuous red-teaming, and automated defense hardening for LLM safety.",
        "date": datetime.now().isoformat(),
        "queries": queries,
        "findings": [],
        "integration_notes": {
            "drift_monitor": "Can leverage baseline detection to predict attack vectors before they succeed",
            "jailbreak_evolution": "Track strategy evolution patterns to anticipate next-generation attack forms",
        },
        "raw_search_results": [],
    }

    try:
        logger.info("Executing multi-engine search for %d queries", len(queries))

        for query in queries:
            logger.info(f"Searching: {query}")

            # Execute multi_search
            result = await research_multi_search(query, max_results=15)

            # Parse results
            findings = parse_research_results(result)
            research_output["findings"].append(findings)
            research_output["raw_search_results"].append(result)

            logger.info(f"Found {findings['result_count']} results for: {query}")

        # Create output directory
        output_dir = Path("/opt/research-toolbox/tmp")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Write JSON results
        output_file = output_dir / "research_701_proactive.json"
        with open(output_file, "w") as f:
            json.dump(research_output, f, indent=2)

        logger.info(f"Research complete! Results saved to {output_file}")
        logger.info(f"Total findings: {len(research_output['findings'])} query groups")

        # Print summary
        print("\n" + "="*80)
        print("RESEARCH 701 SUMMARY: PROACTIVE ADVERSARIAL PATCHING")
        print("="*80)

        for i, finding in enumerate(research_output["findings"], 1):
            print(f"\nQuery {i}: {finding['query']}")
            print(f"  Results: {finding['result_count']} total")
            print(f"  Sources: {finding['sources']}")
            print(f"  Top results:")

            for result in finding["key_results"][:3]:
                print(f"    - {result['title']}")
                print(f"      Source: {result['source']} | Score: {result['score']:.1f}")
                print(f"      URL: {result['url']}")

        print(f"\n✓ Output saved: {output_file}")
        print("="*80)

    except Exception as e:
        logger.error(f"Research failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
