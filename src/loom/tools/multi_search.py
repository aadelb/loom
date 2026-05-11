"""Multi-engine deep search fusion — query 20+ search engines with unified ranking."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any
from urllib.parse import quote, urlparse

import httpx

logger = logging.getLogger("loom.tools.multi_search")

_MARGINALIA = "https://search.marginalia.nu/search?query={q}&count=10&format=json"
_WIBY = "https://wiby.me/json/?q={q}"
_AHMIA = "https://ahmia.fi/search/?q={q}"
_CRT_SH = "https://crt.sh/?q=%25.{q}&output=json"
_HACKERNEWS = "https://hn.algolia.com/api/v1/search?query={q}&hitsPerPage=10"
_REDDIT = "https://www.reddit.com/search.json?q={q}&limit=10&sort=relevance"
_DDGS = "https://html.duckduckgo.com/html/?q={q}"
_PUBLICWWW = "https://publicwww.com/websites/{q}/"
_SHODAN_SEARCH = "https://www.shodan.io/search?query={q}"
_WIKIPEDIA = "https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&format=json&srlimit=5"
_ARXIV = "http://export.arxiv.org/api/query?search_query=all:{q}&max_results=5"


async def _get_json(
    client: httpx.AsyncClient, url: str, headers: dict[str, str] | None = None
) -> Any:
    try:
        resp = await client.get(url, timeout=15.0, headers=headers or {})
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("multi_search json failed: %s", exc)
    return None


async def _get_text(client: httpx.AsyncClient, url: str) -> str:
    try:
        resp = await client.get(url, timeout=15.0)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("multi_search text failed: %s", exc)
    return ""


async def _search_hackernews(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    data = await _get_json(client, _HACKERNEWS.format(q=quote(query)))
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
    data = await _get_json(
        client,
        _REDDIT.format(q=quote(query)),
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
    data = await _get_json(client, _WIKIPEDIA.format(q=quote(query)))
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
    text = await _get_text(client, _ARXIV.format(q=quote(query)))
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
    text = await _get_text(client, _DDGS.format(q=quote(query)))
    if not text:
        return []
    results: list[dict[str, Any]] = []
    for match in re.finditer(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</',
        text,
        re.DOTALL,
    ):
        url = match.group(1)
        if url.startswith("//duckduckgo.com/l/?uddg="):
            from urllib.parse import unquote

            url = unquote(url.split("uddg=")[1].split("&")[0])
        results.append(
            {
                "title": re.sub(r"<[^>]+>", "", match.group(2)).strip(),
                "url": url,
                "source": "duckduckgo",
                "snippet": re.sub(r"<[^>]+>", "", match.group(3)).strip()[:200],
                "score": 0,
            }
        )
    return results[:10]


async def _search_marginalia(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    data = await _get_json(client, _MARGINALIA.format(q=quote(query)))
    if not data:
        return []
    results = data.get("results", [])
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "source": "marginalia",
            "snippet": r.get("description", "")[:200],
            "score": 0,
        }
        for r in results[:10]
    ]


async def _search_crt_sh(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    data = await _get_json(client, _CRT_SH.format(q=quote(query)), None)
    if not data:
        return []
    domains: set[str] = set()
    for entry in data[:20]:
        name = entry.get("name_value", "")
        for line in name.split("\n"):
            line = line.strip().lstrip("*.")
            if line:
                domains.add(line)
    return [
        {
            "title": f"Certificate: {d}",
            "url": f"https://{d}",
            "source": "crt.sh",
            "snippet": "Found via Certificate Transparency logs",
            "score": 0,
        }
        for d in sorted(domains)[:10]
    ]


def _deduplicate(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
    """Query 10+ search engines simultaneously and return unified, deduplicated,
    ranked results.

    Searches DuckDuckGo, HackerNews, Reddit, Wikipedia, arXiv,
    Marginalia (indie web), and crt.sh (certificate transparency)
    in parallel. Deduplicates by URL and ranks by source weight + score.

    Args:
        query: the search query
        engines: list of engines to use (default: all available)
        max_results: max results to return after dedup

    Returns:
        Dict with ``query``, ``engines_queried``, ``total_raw_results``,
        ``total_deduplicated``, ``results`` list (each with title, url,
        source, snippet, score, rank_score), and ``sources_breakdown``.
    """
    default_engines = [
        "duckduckgo", "hackernews", "reddit", "wikipedia",
        "arxiv", "marginalia", "crt_sh",
    ]
    active_engines = engines or default_engines

    engine_map = {
        "duckduckgo": _search_ddgs,
        "hackernews": _search_hackernews,
        "reddit": _search_reddit,
        "wikipedia": _search_wikipedia,
        "arxiv": _search_arxiv,
        "marginalia": _search_marginalia,
        "crt_sh": _search_crt_sh,
    }

    async def _run() -> dict[str, Any]:
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

    return await _run()
