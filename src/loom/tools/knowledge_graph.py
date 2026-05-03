"""research_knowledge_graph — Build knowledge graphs from research data.

Combines Semantic Scholar, Wikipedia, and Wikidata APIs to construct
entity-relationship graphs with automatic deduplication and metadata enrichment.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import quote

import httpx

logger = logging.getLogger("loom.tools.knowledge_graph")


async def _fetch_json(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> Any:
    """Fetch and parse JSON from URL, returns None on error."""
    try:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("knowledge_graph fetch failed: %s", exc)
    return None


async def _search_semantic_scholar(
    client: httpx.AsyncClient, query: str
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str]]]:
    """Search Semantic Scholar and extract nodes (papers, authors) and edges.

    Returns:
        (nodes, edges) where edges are tuples of (source_id, target_id, relation)
    """
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/search?"
        f"query={quote(query)}&limit=10&"
        f"fields=title,abstract,authors,references,citations,year"
    )
    data = await _fetch_json(client, url, timeout=20.0)
    if not data or "papers" not in data:
        return [], []

    nodes: list[dict[str, Any]] = []
    edges: list[tuple[str, str, str]] = []
    paper_ids = set()

    for paper in data.get("papers", []):
        paper_id = paper.get("paperId", "")
        if not paper_id or paper_id in paper_ids:
            continue
        paper_ids.add(paper_id)

        # Add paper node
        nodes.append({
            "id": f"paper_{paper_id}",
            "type": "paper",
            "name": paper.get("title", "Unknown"),
            "metadata": {
                "year": paper.get("year"),
                "abstract": paper.get("abstract", ""),
                "citation_count": paper.get("citationCount", 0),
                "semantic_scholar_id": paper_id,
            },
        })

        # Add author nodes and edges
        for author in paper.get("authors", []):
            author_id = author.get("authorId", "")
            author_name = author.get("name", "")
            if author_id and author_name:
                author_node_id = f"author_{author_id}"
                nodes.append({
                    "id": author_node_id,
                    "type": "author",
                    "name": author_name,
                    "metadata": {"semantic_scholar_id": author_id},
                })
                edges.append((author_node_id, f"paper_{paper_id}", "authored"))

        # Add citation edges
        for ref in paper.get("references", [])[:3]:  # Limit references
            ref_id = ref.get("paperId", "")
            if ref_id:
                edges.append((f"paper_{paper_id}", f"paper_{ref_id}", "cites"))

    return nodes, edges


async def _search_wikipedia(
    client: httpx.AsyncClient, query: str
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str]]]:
    """Search Wikipedia and extract concept nodes and relationships."""
    url = (
        f"https://en.wikipedia.org/w/api.php?"
        f"action=query&titles={quote(query)}&"
        f"prop=links|categories&pllimit=50&cllimit=50&"
        f"format=json"
    )
    data = await _fetch_json(client, url)
    if not data or "query" not in data:
        return [], []

    nodes: list[dict[str, Any]] = []
    edges: list[tuple[str, str, str]] = []
    concept_ids = set()

    pages = data.get("query", {}).get("pages", {})
    for page_id, page_data in pages.items():
        if "missing" in page_data:
            continue

        concept_name = page_data.get("title", "")
        if concept_name and concept_name not in concept_ids:
            concept_ids.add(concept_name)
            concept_node_id = f"concept_{concept_name.replace(' ', '_')}"

            nodes.append({
                "id": concept_node_id,
                "type": "concept",
                "name": concept_name,
                "metadata": {
                    "wikipedia_pageid": page_id,
                    "source": "wikipedia",
                },
            })

            # Add category nodes and edges
            for cat in page_data.get("categories", []):
                cat_name = cat.get("title", "").replace("Category:", "")
                if cat_name:
                    cat_node_id = f"category_{cat_name.replace(' ', '_')}"
                    nodes.append({
                        "id": cat_node_id,
                        "type": "category",
                        "name": cat_name,
                        "metadata": {"source": "wikipedia"},
                    })
                    edges.append((concept_node_id, cat_node_id, "belongs_to"))

            # Add link edges
            for link in page_data.get("links", [])[:5]:  # Limit related links
                link_name = link.get("title", "")
                if link_name:
                    link_node_id = f"concept_{link_name.replace(' ', '_')}"
                    edges.append((concept_node_id, link_node_id, "related_to"))

    return nodes, edges


async def _search_wikidata(
    client: httpx.AsyncClient, query: str
) -> tuple[list[dict[str, Any]], list[tuple[str, str, str]]]:
    """Search Wikidata for structured entity data."""
    url = (
        f"https://www.wikidata.org/w/api.php?"
        f"action=wbsearchentities&search={quote(query)}&"
        f"language=en&format=json&limit=10"
    )
    data = await _fetch_json(client, url)
    if not data or "search" not in data:
        return [], []

    nodes: list[dict[str, Any]] = []
    edges: list[tuple[str, str, str]] = []
    entity_ids = set()

    for entity in data.get("search", []):
        entity_id = entity.get("id", "")
        entity_label = entity.get("label", "")
        entity_desc = entity.get("description", "")

        if entity_id and entity_id not in entity_ids:
            entity_ids.add(entity_id)
            nodes.append({
                "id": f"entity_{entity_id}",
                "type": "entity",
                "name": entity_label,
                "metadata": {
                    "wikidata_id": entity_id,
                    "description": entity_desc,
                    "source": "wikidata",
                },
            })

    return nodes, edges


def _deduplicate_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate nodes by name and id, keeping metadata from all duplicates."""
    seen_names: dict[str, dict[str, Any]] = {}
    seen_ids: dict[str, dict[str, Any]] = {}

    for node in nodes:
        node_id = node["id"]
        node_name = node["name"].lower().strip()

        # Already seen by exact ID
        if node_id in seen_ids:
            continue

        # Merge if seen by name
        if node_name in seen_names:
            existing = seen_names[node_name]
            # Merge metadata
            if "metadata" in node and "metadata" in existing:
                existing["metadata"].update(node["metadata"])
            continue

        # New node
        seen_names[node_name] = node
        seen_ids[node_id] = node

    return list(seen_ids.values())


def _deduplicate_edges(
    edges: list[tuple[str, str, str]],
) -> list[tuple[str, str, str]]:
    """Remove duplicate edges."""
    return list(set(edges))


async def research_knowledge_graph(
    query: str,
    max_nodes: int = 100,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    """Build a knowledge graph from research data.

    Combines Semantic Scholar (papers & authors), Wikipedia (concepts & categories),
    and Wikidata (structured entities) to construct an entity-relationship graph.
    Automatically deduplicates nodes by name and merges metadata.

    Args:
        query: search query (e.g., "machine learning safety")
        max_nodes: maximum number of nodes to return (1-500)
        sources: list of sources to include (semantic_scholar, wikipedia, wikidata).
            If None, uses all sources.

    Returns:
        Dict with keys:
        - query: original query
        - nodes: list of {id, type, name, metadata}
        - edges: list of {source, target, relation}
        - total_nodes: count of deduplicated nodes
        - total_edges: count of edges
        - sources_used: list of sources queried
    """
    if sources is None:
        sources = ["semantic_scholar", "wikipedia", "wikidata"]

    # Validate inputs
    max_nodes = max(1, min(max_nodes, 500))
    sources = [s.lower().strip() for s in sources if s]

    logger.info("knowledge_graph query=%s sources=%s", query[:50], sources)

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": "Loom-Research/1.0"},
        ) as client:
            tasks = []

            if "semantic_scholar" in sources:
                tasks.append(_search_semantic_scholar(client, query))
            else:
                tasks.append(asyncio.sleep(0, result=([], [])))  # type: ignore[arg-type]

            if "wikipedia" in sources:
                tasks.append(_search_wikipedia(client, query))
            else:
                tasks.append(asyncio.sleep(0, result=([], [])))  # type: ignore[arg-type]

            if "wikidata" in sources:
                tasks.append(_search_wikidata(client, query))
            else:
                tasks.append(asyncio.sleep(0, result=([], [])))  # type: ignore[arg-type]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_nodes: list[dict[str, Any]] = []
            all_edges: list[tuple[str, str, str]] = []

            for result in results:
                if isinstance(result, tuple) and not isinstance(result, Exception):
                    nodes, edges = result
                    all_nodes.extend(nodes)
                    all_edges.extend(edges)

            # Deduplicate
            dedup_nodes = _deduplicate_nodes(all_nodes)
            dedup_edges = _deduplicate_edges(all_edges)

            # Truncate to max_nodes
            if len(dedup_nodes) > max_nodes:
                dedup_nodes = dedup_nodes[:max_nodes]

            # Always filter edges to only include valid nodes (prevents dangling refs)
            node_ids = {n["id"] for n in dedup_nodes}
            dedup_edges = [
                e for e in dedup_edges
                if e[0] in node_ids and e[1] in node_ids
            ]

            # Convert edges to dict format
            edge_dicts = [
                {"source": src, "target": tgt, "relation": rel}
                for src, tgt, rel in dedup_edges
            ]

            return {
                "query": query,
                "nodes": dedup_nodes,
                "edges": edge_dicts,
                "total_nodes": len(dedup_nodes),
                "total_edges": len(edge_dicts),
                "sources_used": sources,
            }

    return await _run()
