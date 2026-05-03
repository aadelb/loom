"""NIGHTCRAWLER — arXiv monitoring daemon for jailbreak/adversarial/safety research."""

from __future__ import annotations

import json
import logging
import sqlite3
import xml.etree.ElementTree as ET
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

logger = logging.getLogger("loom.tools.nightcrawler")
_STATE_DIR = Path.home() / ".loom" / "nightcrawler"
_STATE_DB = _STATE_DIR / "state.db"
_DEFAULT_KEYWORDS = ["jailbreak", "prompt injection", "adversarial", "red team", "LLM safety"]
_ARXIV_API_URL = "http://export.arxiv.org/api/query"


class ArxivPaper(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    published_date: str
    pdf_url: str | None = None
    model_config = {"extra": "forbid", "strict": True}


def _ensure_state_db() -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not _STATE_DB.exists():
        conn = sqlite3.connect(_STATE_DB)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS scans "
            "(id INTEGER PRIMARY KEY, timestamp TEXT, keywords TEXT, papers_found INTEGER)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS papers "
            "(arxiv_id TEXT PRIMARY KEY, title TEXT, authors TEXT, abstract TEXT, "
            "published_date TEXT, pdf_url TEXT, discovered_at TEXT)"
        )
        conn.commit()
        conn.close()


def _parse_arxiv_entry(entry: ET.Element) -> ArxivPaper | None:
    try:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        title = (entry.find("atom:title", ns).text or "").strip()
        arxiv_id = (entry.find("atom:id", ns).text or "").split("/abs/")[-1]
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)
                   if a.find("atom:name", ns) is not None and a.find("atom:name", ns).text]
        abstract = (entry.find("atom:summary", ns).text or "").strip()
        published = (entry.find("atom:published", ns).text or "")
        pdf_url = next((l.get("href") for l in entry.findall("atom:link", ns)
                       if l.get("title") == "pdf"), None)
        return ArxivPaper(arxiv_id=arxiv_id, title=title, authors=authors, abstract=abstract,
                         published_date=published, pdf_url=pdf_url)
    except Exception as e:
        logger.warning("Error parsing arXiv entry: %s", str(e))
        return None


def _store_paper(paper: ArxivPaper) -> None:
    try:
        conn = sqlite3.connect(_STATE_DB)
        conn.execute("INSERT OR IGNORE INTO papers VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (paper.arxiv_id, paper.title, json.dumps(paper.authors), paper.abstract,
                     paper.published_date, paper.pdf_url, datetime.now(UTC).isoformat()))
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logger.error("DB error: %s", str(e))


async def research_arxiv_scan(
    keywords: list[str] | None = None,
    days_back: int = 7,
    max_papers: int = 20,
) -> dict[str, Any]:
    """Search arXiv for recent papers on jailbreak/adversarial/safety topics."""
    if keywords is None:
        keywords = _DEFAULT_KEYWORDS
    keywords = keywords[:10]
    _ensure_state_db()
    all_papers: dict[str, ArxivPaper] = {}

    async with httpx.AsyncClient(timeout=30.0) as client:
        cutoff = (datetime.now(UTC) - timedelta(days=days_back)).isoformat().split(".")[0] + "Z"
        for kw in keywords:
            try:
                resp = await client.get(_ARXIV_API_URL, params={
                    "search_query": f'(all:"{kw}") AND submittedDate:[{cutoff} TO 9999999999]',
                    "start": 0, "max_results": max_papers, "sortBy": "submittedDate",
                    "sortOrder": "descending"
                })
                resp.raise_for_status()
                root = ET.fromstring(resp.content)
                for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                    paper = _parse_arxiv_entry(entry)
                    if paper and paper.arxiv_id not in all_papers:
                        all_papers[paper.arxiv_id] = paper
                        _store_paper(paper)
            except httpx.HTTPError as e:
                logger.error("HTTP error for '%s': %s", kw, str(e))

    return {"papers_found": len(all_papers), "keywords_used": keywords,
            "papers": [p.model_dump() for p in all_papers.values()],
            "days_searched": days_back, "scan_timestamp": datetime.now(UTC).isoformat()}


def research_nightcrawler_status() -> dict[str, Any]:
    """Return status of the NIGHTCRAWLER monitoring system."""
    _ensure_state_db()
    try:
        conn = sqlite3.connect(_STATE_DB)
        last_scan = conn.execute("SELECT timestamp FROM scans ORDER BY id DESC LIMIT 1").fetchone()
        paper_count = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        conn.close()
        last_scan_str = last_scan[0] if last_scan else None
        next_scan = (datetime.fromisoformat(last_scan_str.replace("Z", "+00:00"))
                    + timedelta(hours=24)).isoformat() if last_scan_str else None
        return {"active": True, "last_scan": last_scan_str, "total_papers": paper_count,
                "total_strategies_extracted": 0, "next_scheduled_scan": next_scan}
    except Exception as e:
        logger.error("Status error: %s", str(e))
        return {"active": False, "last_scan": None, "total_papers": 0,
                "total_strategies_extracted": 0, "error": str(e)}
