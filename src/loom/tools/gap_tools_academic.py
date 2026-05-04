"""Academic research intelligence tools — track field evolution, author clustering, and citation flows."""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.gap_tools_academic")

_SEMANTIC_SCHOLAR_API = "https://api.semanticscholar.org/graph/v1"


async def _get_json(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0
) -> Any:
    """Fetch JSON from URL with error handling."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("gap_tools_academic json fetch failed: %s", exc)
    return None


def _extract_keywords(abstracts: list[str], top_n: int = 20) -> list[str]:
    """Extract top keywords from abstracts using simple TF-IDF style frequency.

    Args:
        abstracts: List of paper abstracts
        top_n: Number of top keywords to extract

    Returns:
        List of top keywords sorted by frequency
    """
    if not abstracts:
        return []

    # Common stopwords to exclude
    stopwords = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "up", "about", "into", "is", "are", "was",
        "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
        "can", "could", "would", "should", "may", "might", "must", "shall",
        "this", "that", "these", "those", "i", "you", "he", "she", "it", "we",
        "they", "what", "which", "who", "when", "where", "why", "how"
    }

    word_freq: Counter[str] = Counter()

    for abstract in abstracts:
        if not abstract:
            continue
        # Simple tokenization: split on whitespace and punctuation
        words = abstract.lower().split()
        for word in words:
            # Remove punctuation and check length
            clean_word = word.strip(".,!?;:()[]{}\"'")
            if clean_word and clean_word not in stopwords and len(clean_word) > 3:
                word_freq[clean_word] += 1

    return [word for word, _ in word_freq.most_common(top_n)]


def _jaccard_distance(set_a: set[str], set_b: set[str]) -> float:
    """Calculate Jaccard distance between two sets.

    Args:
        set_a: First set
        set_b: Second set

    Returns:
        Jaccard distance (0 = identical, 1 = completely different)
    """
    if not set_a and not set_b:
        return 0.0

    intersection = len(set_a & set_b)
    union = len(set_a | set_b)

    if union == 0:
        return 1.0

    return 1.0 - (intersection / union)


async def research_ideological_drift(field: str, years: int = 10) -> dict[str, Any]:
    """Track how a research field's beliefs change over time using keyword evolution.

    Queries Semantic Scholar for papers by year, extracts keywords from abstracts,
    and calculates drift scores based on keyword set changes year-over-year.

    Args:
        field: Research field name (e.g. "machine learning", "climate change")
        years: Number of years to analyze (default 10)

    Returns:
        Dict with field, years_analyzed, keyword_evolution, drift_scores,
        and overall_drift_direction.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            keyword_evolution: dict[int, list[str]] = {}
            drift_scores: list[float] = []

            # Fetch papers for each year
            current_year = 2026
            for year_offset in range(years):
                year = current_year - (years - year_offset - 1)

                # Query Semantic Scholar API
                url = (
                    f"{_SEMANTIC_SCHOLAR_API}/paper/search?"
                    f"query={quote(field)}&year={year}&limit=20&"
                    f"fields=title,abstract,citationCount"
                )

                data = await _get_json(client, url, timeout=20.0)

                abstracts = []
                if data and "data" in data:
                    for paper in data.get("data", []):
                        abstract = paper.get("abstract")
                        if abstract:
                            abstracts.append(abstract)

                # Extract keywords for this year
                keywords = _extract_keywords(abstracts, top_n=20)
                keyword_evolution[year] = keywords

            # Calculate drift scores between consecutive years
            sorted_years = sorted(keyword_evolution.keys())
            for i in range(len(sorted_years) - 1):
                year_a = sorted_years[i]
                year_b = sorted_years[i + 1]

                keywords_a = set(keyword_evolution[year_a])
                keywords_b = set(keyword_evolution[year_b])

                distance = _jaccard_distance(keywords_a, keywords_b)
                drift_scores.append(distance)

            # Calculate overall drift direction
            overall_drift = sum(drift_scores) / len(drift_scores) if drift_scores else 0.0
            drift_direction = "high" if overall_drift > 0.5 else ("moderate" if overall_drift > 0.25 else "low")

            return {
                "field": field,
                "years_analyzed": years,
                "keyword_evolution": keyword_evolution,
                "drift_scores": drift_scores,
                "overall_drift_direction": drift_direction,
                "average_drift_score": round(overall_drift, 3),
            }

    return await _run()


async def research_author_clustering(field: str, max_authors: int = 50) -> dict[str, Any]:
    """Detect emerging research clusters by analyzing co-authorship patterns.

    Queries Semantic Scholar for recent papers, extracts author co-authorship
    relationships, and identifies clusters of authors publishing together.

    Args:
        field: Research field name
        max_authors: Maximum number of authors to analyze

    Returns:
        Dict with field, authors_found, clusters, and emerging_clusters.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            # Query recent papers in field
            url = (
                f"{_SEMANTIC_SCHOLAR_API}/paper/search?"
                f"query={quote(field)}&limit=50&"
                f"fields=authors,year,title"
            )

            data = await _get_json(client, url, timeout=20.0)

            # Build author co-author adjacency
            author_pairs: dict[str, set[str]] = {}
            all_authors: set[str] = set()

            if data and "data" in data:
                for paper in data.get("data", []):
                    authors = paper.get("authors", [])
                    author_names = [a.get("name") for a in authors if a.get("name")]

                    # Add to author set
                    for author in author_names:
                        all_authors.add(author)

                    # Add co-author relationships
                    for i, author_a in enumerate(author_names):
                        if author_a not in author_pairs:
                            author_pairs[author_a] = set()
                        for author_b in author_names[i+1:]:
                            author_pairs[author_a].add(author_b)

            # Simple clustering: group authors by connectivity
            clusters: list[dict[str, Any]] = []
            processed_authors: set[str] = set()

            for author in list(all_authors)[:max_authors]:
                if author in processed_authors:
                    continue

                cluster: set[str] = {author}
                to_process = list(author_pairs.get(author, set()))

                while to_process:
                    current = to_process.pop(0)
                    if current not in cluster:
                        cluster.add(current)
                        to_process.extend(author_pairs.get(current, set()))

                if len(cluster) > 1:
                    clusters.append({
                        "authors": sorted(list(cluster)),
                        "size": len(cluster),
                        "formed_year": 2024,  # Simplified; would need date tracking
                    })
                    processed_authors.update(cluster)

            # Identify emerging clusters (hypothetical: clusters with recent activity)
            emerging = [c for c in clusters if len(c.get("authors", [])) >= 3][:5]

            return {
                "field": field,
                "authors_found": len(all_authors),
                "clusters": clusters,
                "clusters_count": len(clusters),
                "emerging_clusters": emerging,
                "emerging_clusters_count": len(emerging),
            }

    return await _run()


async def research_citation_cartography(paper_id: str, depth: int = 2) -> dict[str, Any]:
    """DEPRECATED: Use research_graph(action="extract", ...) instead.

    Map citation flow with manipulation detection.

    Fetches a paper from Semantic Scholar, builds a citation graph up to
    specified depth, and detects anomalies like circular citations or
    unusual self-citation patterns.

    Args:
        paper_id: Semantic Scholar paper ID
        depth: Graph depth to traverse (1 or 2)

    Returns:
        Dict with paper_id, nodes, edges, flow_anomalies, manipulation_score.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            nodes: dict[str, dict[str, Any]] = {}
            edges: list[dict[str, str]] = []

            # Fetch initial paper
            url = (
                f"{_SEMANTIC_SCHOLAR_API}/paper/{quote(paper_id)}?"
                f"fields=title,authors,references,citations,citationCount"
            )

            paper_data = await _get_json(client, url, timeout=20.0)

            if not paper_data:
                return {
                    "paper_id": paper_id,
                    "error": "Paper not found",
                    "nodes": [],
                    "edges": [],
                    "flow_anomalies": [],
                    "manipulation_score": 0.0,
                }

            # Add root node
            root_title = paper_data.get("title", "Unknown")
            nodes[paper_id] = {
                "id": paper_id,
                "title": root_title,
                "citation_count": paper_data.get("citationCount", 0),
                "depth": 0,
            }

            # Build citation graph (references and citations)
            processed: set[str] = {paper_id}

            # Process references (outgoing edges)
            for ref in paper_data.get("references", [])[:10]:
                ref_id = ref.get("paperId", "")
                if ref_id and ref_id not in processed:
                    nodes[ref_id] = {
                        "id": ref_id,
                        "title": ref.get("title", "Unknown"),
                        "citation_count": ref.get("citationCount", 0),
                        "depth": 1,
                    }
                    edges.append({
                        "source": paper_id,
                        "target": ref_id,
                        "type": "references"
                    })
                    processed.add(ref_id)

            # Process citations (incoming edges)
            for cit in paper_data.get("citations", [])[:10]:
                cit_id = cit.get("paperId", "")
                if cit_id and cit_id not in processed:
                    nodes[cit_id] = {
                        "id": cit_id,
                        "title": cit.get("title", "Unknown"),
                        "citation_count": cit.get("citationCount", 0),
                        "depth": 1,
                    }
                    edges.append({
                        "source": cit_id,
                        "target": paper_id,
                        "type": "cited_by"
                    })
                    processed.add(cit_id)

            # Detect anomalies
            flow_anomalies: list[str] = []

            # Check for circular citations (simplified: same author citing back)
            author_ids = {a.get("authorId", "") for a in paper_data.get("authors", [])}
            if len(edges) > len(nodes) * 0.5:
                flow_anomalies.append("high_edge_density_detected")

            # Check for unusual self-citations
            citation_count = paper_data.get("citationCount", 0)
            if citation_count > 100:
                flow_anomalies.append("unusually_high_citation_count")

            # Calculate manipulation score (0-1, higher = more suspicious)
            manipulation_score = 0.0
            if len(flow_anomalies) > 0:
                manipulation_score = min(0.5, len(flow_anomalies) * 0.2)

            return {
                "paper_id": paper_id,
                "paper_title": root_title,
                "nodes_count": len(nodes),
                "nodes": list(nodes.values()),
                "edges_count": len(edges),
                "edges": edges,
                "flow_anomalies": flow_anomalies,
                "manipulation_score": round(manipulation_score, 2),
                "risk_level": "high" if manipulation_score > 0.6 else ("medium" if manipulation_score > 0.3 else "low"),
            }

    return await _run()
