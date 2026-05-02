"""Academic integrity tools — detect citation anomalies, retractions, and predatory journals."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.academic_integrity")

_SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1/paper"
_CROSSREF_API = "https://api.crossref.org/works"
_CROSSREF_JOURNALS = "https://api.crossref.org/journals"
_PUBPEER_API = "https://pubpeer.com/v3/publications"
_DOAJ_API = "https://doaj.org/api/search/journals"


async def _get_json(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0
) -> Any:
    """Fetch JSON from URL with error handling."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("academic_integrity fetch failed: %s", exc)
    return None


async def _get_text(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> str:
    """Fetch text from URL with error handling."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("academic_integrity text fetch failed: %s", exc)
    return ""


async def _analyze_citation_network(
    client: httpx.AsyncClient, paper_id: str, depth: int = 2
) -> dict[str, Any]:
    """Analyze citation network for a paper using Semantic Scholar API."""
    paper_data: dict[str, Any] = {}
    mutual_citations: list[str] = []
    self_citation_rate: float = 0.0
    citation_clusters: list[list[str]] = []

    # Fetch main paper
    url = f"{_SEMANTIC_SCHOLAR_API}/{paper_id}?fields=title,authors,references,citations,citationCount,year"
    data = await _get_json(client, url, timeout=30.0)

    if not data:
        return {
            "paper_id": paper_id,
            "error": "Paper not found in Semantic Scholar",
        }

    paper_data = data
    title = data.get("title", "")
    citation_count = data.get("citationCount", 0)
    authors = data.get("authors", [])
    references = data.get("references", [])
    citations = data.get("citations", [])

    # Extract author names for self-citation detection
    author_names = set()
    for author in authors:
        if isinstance(author, dict):
            name = author.get("name", "")
            if name:
                author_names.add(name.lower())

    # Check for mutual citations (papers that cite each other)
    reference_ids = {ref.get("paperId") for ref in references if ref.get("paperId")}
    citation_ids = {cite.get("citingPaper", {}).get("paperId") for cite in citations if cite.get("citingPaper", {}).get("paperId")}

    mutual_citation_ids = reference_ids.intersection(citation_ids)
    mutual_citations = list(mutual_citation_ids)

    # Calculate self-citation rate
    self_citations = 0
    if references:
        for ref in references:
            ref_authors = ref.get("authors", [])
            for ref_author in ref_authors:
                if isinstance(ref_author, dict) and ref_author.get("name", "").lower() in author_names:
                    self_citations += 1
                    break

        self_citation_rate = (self_citations / len(references)) * 100 if references else 0.0

    # Detect citation clusters (simplified: papers with high cross-citation)
    if depth > 1 and references:
        # Group references by year proximity (basic clustering)
        ref_by_year: dict[int, list[str]] = {}
        for ref in references[:50]:  # Limit to first 50 for performance
            year = ref.get("year", 0)
            if year:
                if year not in ref_by_year:
                    ref_by_year[year] = []
                if ref.get("paperId"):
                    ref_by_year[year].append(ref["paperId"])

        # Clusters are groups of papers from similar years
        citation_clusters = [ids for ids in ref_by_year.values() if len(ids) >= 3]

    # Calculate anomaly score (0-100)
    # Higher score = more suspicious
    anomaly_score = 0.0

    # Factor 1: High self-citation rate (>30% is suspicious)
    if self_citation_rate > 30:
        anomaly_score += min(self_citation_rate / 2, 25)

    # Factor 2: Mutual citations (papers citing each other back is suspicious)
    if mutual_citations:
        anomaly_score += min(len(mutual_citations) * 5, 25)

    # Factor 3: Citation clusters (too many papers from same era citing each other)
    for cluster in citation_clusters:
        if len(cluster) > 5:
            anomaly_score += min(len(cluster), 15)
            break

    # Factor 4: Citation count anomalies (very high for age or very low)
    if citation_count > 500:
        anomaly_score += 15

    anomaly_score = min(anomaly_score, 100)

    return {
        "paper_id": paper_id,
        "title": title,
        "authors_count": len(authors),
        "citation_count": citation_count,
        "reference_count": len(references),
        "self_citation_rate": round(self_citation_rate, 2),
        "mutual_citations_count": len(mutual_citations),
        "mutual_citations": mutual_citations[:20],
        "citation_clusters_count": len(citation_clusters),
        "anomaly_score": round(anomaly_score, 1),
    }


async def _check_for_retractions(
    client: httpx.AsyncClient, query: str, max_results: int = 20
) -> dict[str, Any]:
    """Check for retractions using Crossref and PubPeer APIs."""
    retractions_found: list[dict[str, Any]] = []
    pubpeer_comments_found: list[dict[str, Any]] = []
    papers_checked = 0

    # Search Crossref for papers
    url = f"{_CROSSREF_API}?query={quote(query)}&rows={min(max_results, 50)}"
    crossref_data = await _get_json(client, url, timeout=20.0)

    if not crossref_data or "message" not in crossref_data:
        return {
            "query": query,
            "papers_checked": 0,
            "retractions_found": 0,
            "retraction_details": [],
            "pubpeer_comments_found": 0,
        }

    items = crossref_data.get("message", {}).get("items", [])
    papers_checked = min(len(items), max_results)

    for item in items[:max_results]:
        # Check for retraction status in Crossref metadata
        relation = item.get("relation", {})
        if "is-retraction-of" in relation or "is-supplement-to" in relation:
            retractions_found.append({
                "title": item.get("title", [""])[0] if item.get("title") else "",
                "doi": item.get("DOI", ""),
                "date": item.get("published-print", {}).get("date-parts", [[]])[0] if item.get("published-print") else "",
                "retraction_type": "crossref_marked",
            })

        # Try PubPeer lookup for this DOI
        doi = item.get("DOI", "")
        if doi:
            pubpeer_url = f"{_PUBPEER_API}?doi={quote(doi)}"
            pubpeer_data = await _get_json(client, pubpeer_url, timeout=15.0)

            if pubpeer_data and isinstance(pubpeer_data, dict):
                if "results" in pubpeer_data and isinstance(pubpeer_data["results"], list):
                    for result in pubpeer_data["results"][:3]:
                        if result.get("replies"):
                            pubpeer_comments_found.append({
                                "doi": doi,
                                "title": item.get("title", [""])[0] if item.get("title") else "",
                                "comment_count": len(result.get("replies", [])),
                                "url": result.get("url", ""),
                            })

    return {
        "query": query,
        "papers_checked": papers_checked,
        "retractions_found": len(retractions_found),
        "retraction_details": retractions_found,
        "pubpeer_comments_found": len(pubpeer_comments_found),
        "pubpeer_details": pubpeer_comments_found,
    }


async def _check_journal_predatory(
    client: httpx.AsyncClient, journal_name: str
) -> dict[str, Any]:
    """Check if journal shows signs of being predatory."""
    is_in_doaj = False
    crossref_registered = False
    publication_count = 0
    risk_indicators: list[str] = []
    predatory_score = 0.0

    # Check DOAJ (Directory of Open Access Journals)
    doaj_url = f"{_DOAJ_API}/{quote(journal_name)}"
    doaj_data = await _get_json(client, doaj_url, timeout=15.0)

    if doaj_data and isinstance(doaj_data, dict):
        if doaj_data.get("results"):
            is_in_doaj = True

    # Check Crossref for journal registration and metadata
    crossref_url = f"{_CROSSREF_JOURNALS}?query={quote(journal_name)}&rows=5"
    crossref_data = await _get_json(client, crossref_url, timeout=15.0)

    if crossref_data and "message" in crossref_data:
        items = crossref_data.get("message", {}).get("items", [])
        if items:
            crossref_registered = True
            journal_info = items[0]

            # Extract publication counts
            publication_count = journal_info.get("counts", {}).get("total-dois", 0)

            # Check for predatory risk indicators
            if publication_count < 10:
                risk_indicators.append("very_low_publication_count")
                predatory_score += 20

            if publication_count > 5000:
                risk_indicators.append("unusually_high_publication_rate")
                predatory_score += 10

            # Check indexing
            issn = journal_info.get("issn", [])
            if not issn:
                risk_indicators.append("no_issn_registered")
                predatory_score += 15

            # Check coverage dates
            coverage = journal_info.get("coverage", {})
            if not coverage or not coverage.get("publication-count"):
                risk_indicators.append("incomplete_coverage_data")
                predatory_score += 10

    if not crossref_registered:
        # Not registered in Crossref is a risk factor
        risk_indicators.append("not_in_crossref")
        predatory_score += 25

    if not is_in_doaj and crossref_registered:
        # Open access journals should be in DOAJ
        risk_indicators.append("not_in_doaj")
        predatory_score += 15

    # Additional risk: no identifiable peer review process
    # (This would require additional API calls or manual verification)
    if publication_count == 0 and not is_in_doaj:
        risk_indicators.append("no_verifiable_data")
        predatory_score += 30

    predatory_score = min(predatory_score, 100)

    return {
        "journal_name": journal_name,
        "is_in_doaj": is_in_doaj,
        "crossref_registered": crossref_registered,
        "publication_count": publication_count,
        "risk_indicators": risk_indicators,
        "predatory_score": round(predatory_score, 1),
    }


async def research_citation_analysis(paper_id: str, depth: int = 2) -> dict[str, Any]:
    """Analyze citation networks for anomalies using Semantic Scholar API.

    Detects suspicious citation patterns including mutual citations,
    high self-citation rates, and citation clusters. Returns an anomaly
    score (0-100) where higher values indicate greater suspicion.

    Args:
        paper_id: Semantic Scholar paper ID (e.g., "a1b2c3d4e5f6g7h8")
        depth: Analysis depth (1-3). Higher depth fetches more related papers.

    Returns:
        Dict with ``paper_id``, ``title``, ``authors_count``, ``citation_count``,
        ``reference_count``, ``self_citation_rate``, ``mutual_citations_count``,
        ``mutual_citations`` (list), ``citation_clusters_count``, and ``anomaly_score``.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            return await _analyze_citation_network(client, paper_id, depth)

    return await _run()


async def research_retraction_check(query: str, max_results: int = 20) -> dict[str, Any]:
    """Check if papers/authors have retractions using Crossref and PubPeer.

    Searches for retracted papers matching the query and identifies
    papers with significant PubPeer comments. Useful for checking
    publication integrity of researchers.

    Args:
        query: Author name, paper title, or keywords to search
        max_results: Maximum papers to check (1-100, default 20)

    Returns:
        Dict with ``query``, ``papers_checked``, ``retractions_found``,
        ``retraction_details`` (list), ``pubpeer_comments_found``, and
        ``pubpeer_details`` (list).
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            return await _check_for_retractions(client, query, max_results)

    return await _run()


async def research_predatory_journal_check(journal_name: str) -> dict[str, Any]:
    """Check if a journal shows signs of being predatory.

    Analyzes journal registration in DOAJ (Directory of Open Access
    Journals) and Crossref, publication frequency, ISSN status, and
    other indicators of journal quality. Returns a predatory score
    (0-100) where higher values suggest greater risk.

    Args:
        journal_name: Full journal name (e.g., "Nature", "Journal of Clinical Research")

    Returns:
        Dict with ``journal_name``, ``is_in_doaj`` (bool), ``crossref_registered`` (bool),
        ``publication_count``, ``risk_indicators`` (list), and ``predatory_score``.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            return await _check_journal_predatory(client, journal_name)

    return await _run()
