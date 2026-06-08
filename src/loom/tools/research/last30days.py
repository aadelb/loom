"""Last-30-Days pulse — recency + engagement-scored multi-source research.

Port of the /last30days skill (github.com/mvanhorn/last30days-skill) engine,
adapted to Loom. Searches what *people* actually engage with in a recent time
window — scored by real signal (Hacker News points, Reddit upvotes, Polymarket
money/odds, GitHub stars) rather than editorial relevance — then synthesizes a
grounded brief via Loom's LLM cascade.

Zero-config sources that work from a datacenter IP:
  • Hacker News  — Algolia search_by_date (points + comments, recency-filtered)
  • Polymarket   — Gamma public-search (real-money prediction odds + volume)
  • GitHub       — gh search (stars, pushed-in-window)
  • Web          — Loom's search providers (Exa/Tavily/Brave/DDG)
  • Reddit       — public search JSON (best-effort; may 403 from datacenter)

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.last30days")

_DEPTH = {
    "quick": {"hn": 15, "pm": 5, "gh": 5, "web": 5, "reddit": 8},
    "default": {"hn": 30, "pm": 12, "gh": 10, "web": 8, "reddit": 15},
    "deep": {"hn": 60, "pm": 25, "gh": 20, "web": 12, "reddit": 25},
}

_UA = "Mozilla/5.0 (research-bot; last30days; academic use)"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _within_days(iso_or_ts: Any, days: int) -> bool:
    cutoff = _now() - timedelta(days=days)
    try:
        if isinstance(iso_or_ts, (int, float)):
            dt = datetime.fromtimestamp(iso_or_ts, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(iso_or_ts).replace("Z", "+00:00"))
        return dt >= cutoff
    except Exception:
        return True  # keep if unparseable


# ─── SOURCE: Hacker News (Algolia) ────────────────────────────────────

def _hn(topic: str, days: int, limit: int) -> list[dict]:
    import requests
    cutoff_ts = int((_now() - timedelta(days=days)).timestamp())
    url = "https://hn.algolia.com/api/v1/search_by_date"
    params = {
        "query": topic,
        "tags": "story",
        "numericFilters": f"created_at_i>{cutoff_ts}",
        "hitsPerPage": min(limit, 100),
    }
    try:
        r = requests.get(url, params=params, headers={"User-Agent": _UA}, timeout=12)
        hits = r.json().get("hits", [])
    except Exception as e:
        logger.debug("hn_fail: %s", e)
        return []
    out = []
    for h in hits:
        pts = h.get("points") or 0
        nc = h.get("num_comments") or 0
        out.append({
            "source": "hackernews",
            "title": h.get("title") or h.get("story_title") or "",
            "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
            "engagement": int(pts) + int(nc) * 2,  # comments weighted higher (discussion)
            "signal": f"{pts} pts, {nc} comments",
            "created_at": h.get("created_at", ""),
        })
    out.sort(key=lambda x: x["engagement"], reverse=True)
    return out[:limit]


# ─── SOURCE: Polymarket (Gamma) — real-money odds ─────────────────────

def _polymarket(topic: str, limit: int) -> list[dict]:
    import requests
    url = "https://gamma-api.polymarket.com/public-search"
    try:
        r = requests.get(
            url, params={"q": topic, "limit_per_type": min(limit, 25)},
            headers={"User-Agent": _UA}, timeout=12,
        )
        events = r.json().get("events", [])
    except Exception as e:
        logger.debug("pm_fail: %s", e)
        return []
    out = []
    for e in events:
        vol = e.get("volume") or 0
        try:
            vol = float(vol)
        except Exception:
            vol = 0.0
        markets = e.get("markets") or []
        odds = ""
        if markets:
            m = markets[0]
            try:
                outcomes = json.loads(m.get("outcomes", "[]")) if isinstance(m.get("outcomes"), str) else m.get("outcomes", [])
                prices = json.loads(m.get("outcomePrices", "[]")) if isinstance(m.get("outcomePrices"), str) else m.get("outcomePrices", [])
                odds = ", ".join(f"{o} {float(p)*100:.0f}%" for o, p in zip(outcomes, prices))
            except Exception:
                odds = ""
        out.append({
            "source": "polymarket",
            "title": e.get("title", ""),
            "url": f"https://polymarket.com/event/{e.get('slug', '')}",
            "engagement": vol,  # dollars of real-money volume
            "signal": f"${vol:,.0f} volume" + (f" | odds: {odds}" if odds else ""),
            "created_at": e.get("startDate", ""),
        })
    out.sort(key=lambda x: x["engagement"], reverse=True)
    return out[:limit]


# ─── SOURCE: GitHub (gh) — stars, recently pushed ─────────────────────

def _github(topic: str, days: int, limit: int) -> list[dict]:
    import subprocess
    cutoff = (_now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        proc = subprocess.run(
            ["gh", "search", "repos", topic, "--sort", "stars", "--order", "desc",
             "--limit", str(min(limit, 30)), f"--updated=>{cutoff}",
             "--json", "fullName,description,stargazersCount,url,updatedAt"],
            capture_output=True, text=True, timeout=25,
        )
        repos = json.loads(proc.stdout or "[]")
    except Exception as e:
        logger.debug("gh_fail: %s", e)
        return []
    out = []
    for repo in repos:
        stars = repo.get("stargazersCount") or 0
        out.append({
            "source": "github",
            "title": f"{repo.get('fullName','')} — {(repo.get('description') or '')[:90]}",
            "url": repo.get("url", ""),
            "engagement": int(stars),
            "signal": f"{stars} stars",
            "created_at": repo.get("updatedAt", ""),
        })
    out.sort(key=lambda x: x["engagement"], reverse=True)
    return out[:limit]


# ─── SOURCE: Reddit (public search JSON, best-effort) ─────────────────

def _reddit(topic: str, days: int, limit: int) -> list[dict]:
    import requests
    url = "https://www.reddit.com/search.json"
    try:
        r = requests.get(
            url, params={"q": topic, "sort": "top", "t": "month", "limit": min(limit, 25)},
            headers={"User-Agent": _UA}, timeout=12,
        )
        if r.status_code != 200:
            return []
        children = r.json().get("data", {}).get("children", [])
    except Exception as e:
        logger.debug("reddit_fail: %s", e)
        return []
    out = []
    for c in children:
        d = c.get("data", {})
        if not _within_days(d.get("created_utc"), days):
            continue
        ups = d.get("ups") or d.get("score") or 0
        nc = d.get("num_comments") or 0
        out.append({
            "source": "reddit",
            "title": d.get("title", ""),
            "url": "https://reddit.com" + d.get("permalink", ""),
            "engagement": int(ups) + int(nc) * 2,
            "signal": f"{ups} upvotes, {nc} comments in r/{d.get('subreddit','')}",
            "created_at": d.get("created_utc", ""),
        })
    out.sort(key=lambda x: x["engagement"], reverse=True)
    return out[:limit]


# ─── SOURCE: Web (Loom's search providers) ────────────────────────────

async def _web(topic: str, limit: int) -> list[dict]:
    try:
        from loom.tools.core.search import research_search
    except Exception:
        return []
    try:
        res = await research_search(query=f"{topic} latest news", n=limit)
        results = res.get("results", []) if isinstance(res, dict) else []
    except Exception as e:
        logger.debug("web_fail: %s", e)
        return []
    out = []
    for i, r in enumerate(results[:limit]):
        out.append({
            "source": "web",
            "title": r.get("title", ""),
            "url": r.get("url", r.get("href", "")),
            "engagement": max(1, limit - i),  # rank-based proxy
            "signal": "web result",
            "created_at": r.get("published", ""),
        })
    return out


async def last30days_evidence(topic: str, days: int = 30, depth: str = "quick") -> str:
    """Return a compact engagement-ranked grounding block (no LLM synthesis).

    Reusable by research pipelines to inject recent real-world signal (HN
    points, Polymarket money/odds, GitHub stars, web) as RAG context. Returns
    an empty string on total failure so callers can no-op safely.
    """
    try:
        res = await research_last30days(
            topic=topic, days=days, depth=depth, synthesize=False,
        )
        by_source = res.get("by_source", {}) if isinstance(res, dict) else {}
        lines: list[str] = []
        for src, items in by_source.items():
            if not items:
                continue
            lines.append(f"[{src.upper()} — last {days}d, engagement-ranked]")
            for it in items[:4]:
                lines.append(f"- {it['title']} ({it['signal']}) {it['url']}")
        return "\n".join(lines)[:4000]
    except Exception as e:
        logger.debug("last30days_evidence_fail: %s", e)
        return ""


# ─── MAIN TOOL ────────────────────────────────────────────────────────

@handle_tool_errors("research_last30days")
async def research_last30days(
    topic: str,
    days: int = 30,
    depth: str = "default",
    sources: list[str] | None = None,
    synthesize: bool = True,
) -> dict[str, Any]:
    """Research what people actually engage with about a topic in a recent window.

    Searches Hacker News, Polymarket, GitHub, the web, and Reddit in parallel,
    ranks everything by real engagement (points, money/odds, stars, upvotes) —
    not editorial relevance — then synthesizes a grounded, citation-backed brief.
    Port of the /last30days skill, adapted to Loom's providers.

    Args:
        topic: What to research (e.g. "AI agent frameworks", "nvidia earnings").
        days: Recency window in days (default: 30).
        depth: "quick" | "default" | "deep" — controls per-source result counts.
        sources: Subset of ["hackernews","polymarket","github","web","reddit"]
                 (default: all).
        synthesize: Whether to produce an LLM-synthesized brief (default: True).

    Returns:
        Per-source top items (engagement-ranked), a merged top list, and an
        optional synthesized brief grounded in the real signal.
    """
    start = time.time()
    depth = depth if depth in _DEPTH else "default"
    caps = _DEPTH[depth]
    active = sources or ["hackernews", "polymarket", "github", "web", "reddit"]

    # Fan out across sources in parallel (sync sources via threads)
    tasks: dict[str, Any] = {}
    if "hackernews" in active:
        tasks["hackernews"] = asyncio.to_thread(_hn, topic, days, caps["hn"])
    if "polymarket" in active:
        tasks["polymarket"] = asyncio.to_thread(_polymarket, topic, caps["pm"])
    if "github" in active:
        tasks["github"] = asyncio.to_thread(_github, topic, days, caps["gh"])
    if "reddit" in active:
        tasks["reddit"] = asyncio.to_thread(_reddit, topic, days, caps["reddit"])
    if "web" in active:
        tasks["web"] = _web(topic, caps["web"])

    keys = list(tasks.keys())
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    by_source: dict[str, list[dict]] = {}
    for k, r in zip(keys, results):
        by_source[k] = r if isinstance(r, list) else []

    # Merge + rank: normalize engagement per-source (z-ish), then interleave top items
    merged: list[dict] = []
    for k, items in by_source.items():
        merged.extend(items)
    # Keep a balanced top list: top 3 per source by engagement
    top_items: list[dict] = []
    for k, items in by_source.items():
        top_items.extend(items[:3])
    top_items.sort(key=lambda x: (x["source"] != "polymarket", -float(x.get("engagement", 0))))

    result: dict[str, Any] = {
        "topic": topic,
        "window_days": days,
        "depth": depth,
        "sources_searched": active,
        "counts": {k: len(v) for k, v in by_source.items()},
        "by_source": {k: v[:8] for k, v in by_source.items()},
        "top_items": top_items[:20],
        "total_items": len(merged),
    }

    # Synthesize a grounded brief from the engagement-ranked signal
    if synthesize and merged:
        evidence_lines = []
        for k, items in by_source.items():
            if not items:
                continue
            evidence_lines.append(f"\n[{k.upper()}]")
            for it in items[:5]:
                evidence_lines.append(f"- {it['title']} ({it['signal']}) {it['url']}")
        evidence = "\n".join(evidence_lines)[:7000]
        try:
            from loom.tools.llm.llm import _call_with_cascade
            messages = [
                {"role": "system", "content": (
                    "You are a research analyst. Synthesize a grounded brief from the "
                    "engagement-ranked signal below (people voting with attention, money, "
                    "and stars over the last "
                    f"{days} days). Lead with what people actually care about. Cite "
                    "sources inline. Be concrete; no filler. Note Polymarket odds as a "
                    "real-money signal when present."
                )},
                {"role": "user", "content": f"Topic: {topic}\n\nEngagement-ranked evidence:\n{evidence}"},
            ]
            resp = await _call_with_cascade(
                messages=messages, max_tokens=1500, temperature=0.3, timeout=90,
            )
            result["brief"] = resp.text if resp else ""
            result["brief_provider"] = getattr(resp, "provider", "") if resp else ""
        except Exception as e:
            result["brief_error"] = str(e)[:200]

    result["duration_ms"] = round((time.time() - start) * 1000)
    return result
