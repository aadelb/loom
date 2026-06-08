"""Legal case-law search — UK (BAILII) + US (CourtListener) + EU.

Built in response to the dubaiPocase feedback report: the legal-research session
needed real case-law (UK employment tribunal decisions, US court opinions) and
research_deep timed out on every attempt. This tool hits dedicated legal
databases directly:

- CourtListener (free REST API, 9M+ US opinions) — primary, reliable
- BAILII (UK & Ireland case law) — search via their public site
- EUR-Lex (EU law) — best-effort discovery

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any
from urllib.parse import quote_plus

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.legal_cases")

_UA = "Mozilla/5.0 (research-bot; legal-research; academic use)"


def _courtlistener(query: str, limit: int, court: str | None) -> list[dict]:
    """Search CourtListener's free opinion search API (no key required)."""
    import requests
    url = "https://www.courtlistener.com/api/rest/v4/search/"
    params: dict[str, Any] = {"q": query, "type": "o", "order_by": "score desc"}
    if court:
        params["court"] = court
    try:
        r = requests.get(url, params=params, headers={"User-Agent": _UA}, timeout=15)
        if r.status_code != 200:
            return []
        results = r.json().get("results", [])
    except Exception as e:
        logger.debug("courtlistener_fail: %s", e)
        return []
    out = []
    for o in results[:limit]:
        out.append({
            "source": "courtlistener",
            "jurisdiction": "US",
            "case_name": o.get("caseName") or o.get("caseNameFull") or "",
            "court": o.get("court") or o.get("court_id") or "",
            "date": o.get("dateFiled") or "",
            "citation": (o.get("citation") or [None])[0] if isinstance(o.get("citation"), list) else o.get("citation", ""),
            "url": "https://www.courtlistener.com" + (o.get("absolute_url") or ""),
            "snippet": (o.get("snippet") or "")[:300],
        })
    return out


def _bailii(query: str, limit: int) -> list[dict]:
    """Search BAILII (UK & Ireland case law) via its public search endpoint."""
    import requests
    # BAILII's Sino search; returns HTML — extract case links.
    url = "https://www.bailii.org/cgi-bin/lucy_search_1.cgi"
    params = {"query": query, "mask_path": "", "method": "boolean", "highlight": "1"}
    try:
        r = requests.get(url, params=params, headers={"User-Agent": _UA}, timeout=15)
        if r.status_code != 200:
            return []
        html = r.text
    except Exception as e:
        logger.debug("bailii_fail: %s", e)
        return []
    # Extract result links to case documents (/ew/, /uk/, /ie/, /scot/ cases).
    matches = re.findall(
        r'<a href="(/[a-z]{2,4}/cases/[^"]+\.html)"[^>]*>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL,
    )
    out = []
    seen = set()
    for href, title in matches:
        if href in seen:
            continue
        seen.add(href)
        clean = re.sub(r"<[^>]+>", "", title).strip()
        if not clean:
            continue
        out.append({
            "source": "bailii",
            "jurisdiction": "UK/IE",
            "case_name": clean[:160],
            "court": "",
            "date": "",
            "citation": "",
            "url": "https://www.bailii.org" + href,
            "snippet": "",
        })
        if len(out) >= limit:
            break
    return out


def _eurlex(query: str, limit: int) -> list[dict]:
    """Best-effort EUR-Lex discovery (EU law / CJEU)."""
    import requests
    url = "https://eur-lex.europa.eu/search.html"
    params = {"scope": "EURLEX", "text": query, "type": "quick", "lang": "en"}
    try:
        r = requests.get(url, params=params, headers={"User-Agent": _UA}, timeout=15)
        if r.status_code != 200:
            return []
        html = r.text
    except Exception as e:
        logger.debug("eurlex_fail: %s", e)
        return []
    matches = re.findall(r'href="(\./legal-content/[^"]+)"[^>]*title="([^"]+)"', html)
    out = []
    for href, title in matches[:limit]:
        out.append({
            "source": "eurlex",
            "jurisdiction": "EU",
            "case_name": title[:160],
            "court": "CJEU/EU",
            "date": "",
            "citation": "",
            "url": "https://eur-lex.europa.eu" + href.lstrip("."),
            "snippet": "",
        })
    return out


@handle_tool_errors("research_legal_cases")
async def research_legal_cases(
    query: str,
    jurisdiction: str = "all",
    limit: int = 10,
    court: str | None = None,
) -> dict[str, Any]:
    """Search real case-law databases (UK BAILII, US CourtListener, EU EUR-Lex).

    Dedicated legal search that hits case-law databases directly — far more
    reliable for legal research than generic web search (which timed out in
    the dubaiPocase session).

    Args:
        query: Legal search query (e.g. "asthma unfair dismissal probation remote work").
        jurisdiction: "all" | "us" | "uk" | "eu" — which databases to query.
        limit: Max results per source (default: 10).
        court: Optional CourtListener court id filter (e.g. "ca9", "scotus").

    Returns:
        Matching cases with case_name, court, date, citation, url, and snippet,
        grouped by source, plus a merged list.
    """
    start = time.time()
    j = (jurisdiction or "all").lower()
    tasks: dict[str, Any] = {}
    if j in ("all", "us"):
        tasks["courtlistener"] = asyncio.to_thread(_courtlistener, query, limit, court)
    if j in ("all", "uk", "ie"):
        tasks["bailii"] = asyncio.to_thread(_bailii, query, limit)
    if j in ("all", "eu"):
        tasks["eurlex"] = asyncio.to_thread(_eurlex, query, limit)

    keys = list(tasks.keys())
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    by_source: dict[str, list[dict]] = {}
    for k, r in zip(keys, results):
        by_source[k] = r if isinstance(r, list) else []

    merged: list[dict] = []
    for items in by_source.values():
        merged.extend(items)

    notes = []
    # BAILII/EUR-Lex serve a JS bot-challenge to datacenter IPs; they return
    # results only behind a residential proxy / stealth browser.
    if "bailii" in by_source and not by_source["bailii"]:
        notes.append("bailii: no results (often bot-blocked from datacenter IPs — needs a residential proxy)")
    if "eurlex" in by_source and not by_source["eurlex"]:
        notes.append("eurlex: no results (may be bot-blocked or no match)")

    return {
        "query": query,
        "jurisdiction": jurisdiction,
        "by_source": by_source,
        "cases": merged[: limit * 3],
        "counts": {k: len(v) for k, v in by_source.items()},
        "total": len(merged),
        "notes": notes,
        "duration_ms": round((time.time() - start) * 1000),
    }
