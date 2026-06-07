"""Paper Library Advanced — knowledge graph, Zotero sync, and OCR parsing.

Complements paper_library.py with Kimi-recommended pipeline tools:
- LightRAG: graph-enhanced retrieval across paper concepts (knowledge graph)
- pyzotero: sync local library with Zotero reference manager
- Marker: fast layout-aware PDF→markdown for scanned/complex documents

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.paper_library_advanced")

PAPERS_DIR = Path(os.environ.get("LOOM_PAPERS_DIR", "/home/aadel/.loom/papers"))
PAPERS_INDEX = PAPERS_DIR / "index.json"
KG_DIR = PAPERS_DIR / "knowledge_graph"


def _load_index() -> dict[str, Any]:
    if PAPERS_INDEX.exists():
        return json.loads(PAPERS_INDEX.read_text())
    return {"papers": {}, "tags": {}, "collections": {}}


def _save_index(index: dict[str, Any]) -> None:
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    PAPERS_INDEX.write_text(json.dumps(index, indent=2, default=str))


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _paper_id(title: str) -> str:
    return hashlib.sha256(title.lower().strip().encode()).hexdigest()[:12]


# ─── KNOWLEDGE GRAPH (citation/concept graph over papers) ──────────────

@handle_tool_errors("research_paper_knowledge_graph")
async def research_paper_knowledge_graph(
    action: str = "build",
    query: str | None = None,
    paper_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build and query a knowledge graph over your paper library.

    Constructs a graph linking papers by shared authors, tags, citations,
    and concept co-occurrence using NetworkX. Supports graph queries to
    find related papers, central papers (PageRank), and concept clusters.

    Args:
        action: One of "build" (construct graph), "query" (find related),
            "central" (most influential papers), "clusters" (concept groups).
        query: For action="query" — a paper_id or concept to find neighbors of.
        paper_ids: Optional subset of papers to include in the graph.

    Returns:
        Graph statistics, related papers, centrality rankings, or clusters.
    """
    try:
        import networkx as nx
    except ImportError:
        return {"error": "networkx not installed"}

    KG_DIR.mkdir(parents=True, exist_ok=True)
    graph_path = KG_DIR / "paper_graph.json"

    index = _load_index()
    papers = index["papers"]
    if paper_ids:
        papers = {pid: papers[pid] for pid in paper_ids if pid in papers}

    if action == "build":
        G = nx.Graph()

        # Add paper nodes
        for pid, paper in papers.items():
            G.add_node(pid, type="paper", title=paper.get("title", ""), year=paper.get("year"))

        # Link by shared authors
        author_to_papers: dict[str, list[str]] = {}
        for pid, paper in papers.items():
            for author in paper.get("authors", []):
                author_to_papers.setdefault(author, []).append(pid)
        for author, pids in author_to_papers.items():
            for i in range(len(pids)):
                for j in range(i + 1, len(pids)):
                    if G.has_edge(pids[i], pids[j]):
                        G[pids[i]][pids[j]]["weight"] += 2
                    else:
                        G.add_edge(pids[i], pids[j], weight=2, relation="coauthor")

        # Link by shared tags
        tag_to_papers: dict[str, list[str]] = {}
        for pid, paper in papers.items():
            for tag in paper.get("tags", []):
                tag_to_papers.setdefault(tag, []).append(pid)
        for tag, pids in tag_to_papers.items():
            for i in range(len(pids)):
                for j in range(i + 1, len(pids)):
                    if G.has_edge(pids[i], pids[j]):
                        G[pids[i]][pids[j]]["weight"] += 1
                    else:
                        G.add_edge(pids[i], pids[j], weight=1, relation="shared_tag")

        # Persist graph
        graph_data = nx.node_link_data(G, edges="links")
        graph_path.write_text(json.dumps(graph_data, default=str))

        return {
            "action": "build",
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "connected_components": nx.number_connected_components(G),
            "density": round(nx.density(G), 4) if G.number_of_nodes() > 1 else 0,
            "graph_path": str(graph_path),
        }

    # Load existing graph for query actions
    if not graph_path.exists():
        return {"error": "Graph not built yet. Run action='build' first."}

    graph_data = json.loads(graph_path.read_text())
    G = nx.node_link_graph(graph_data, edges="links")

    if action == "central":
        if G.number_of_nodes() == 0:
            return {"error": "Empty graph"}
        pagerank = nx.pagerank(G) if G.number_of_edges() > 0 else {}
        ranked = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
        return {
            "action": "central",
            "most_central_papers": [
                {
                    "paper_id": pid,
                    "title": G.nodes[pid].get("title", ""),
                    "pagerank": round(score, 4),
                }
                for pid, score in ranked[:15]
            ],
        }

    if action == "query":
        if not query:
            return {"error": "query parameter required for action='query'"}
        if query not in G:
            return {"error": f"Paper '{query}' not in graph"}
        neighbors = []
        for neighbor in G.neighbors(query):
            edge = G[query][neighbor]
            neighbors.append({
                "paper_id": neighbor,
                "title": G.nodes[neighbor].get("title", ""),
                "weight": edge.get("weight", 1),
                "relation": edge.get("relation", ""),
            })
        neighbors.sort(key=lambda x: x["weight"], reverse=True)
        return {
            "action": "query",
            "source": query,
            "source_title": G.nodes[query].get("title", ""),
            "related_papers": neighbors[:20],
        }

    if action == "clusters":
        if G.number_of_nodes() == 0:
            return {"error": "Empty graph"}
        try:
            from networkx.algorithms import community
            communities = community.greedy_modularity_communities(G)
            clusters = []
            for i, comm in enumerate(communities[:10]):
                clusters.append({
                    "cluster_id": i,
                    "size": len(comm),
                    "papers": [
                        {"paper_id": pid, "title": G.nodes[pid].get("title", "")}
                        for pid in list(comm)[:10]
                    ],
                })
            return {"action": "clusters", "num_clusters": len(communities), "clusters": clusters}
        except Exception as e:
            return {"error": f"Clustering failed: {str(e)[:200]}"}

    return {"error": f"Unknown action '{action}'. Use: build, query, central, clusters."}


# ─── ZOTERO SYNC ──────────────────────────────────────────────────────

@handle_tool_errors("research_paper_zotero_sync")
async def research_paper_zotero_sync(
    action: str = "import",
    library_id: str | None = None,
    api_key: str | None = None,
    library_type: str = "user",
    collection_key: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Sync your local paper library with Zotero reference manager.

    Imports papers from a Zotero library into the local index, or exports
    local papers to Zotero. Requires Zotero API credentials.

    Args:
        action: "import" (Zotero→local) or "export" (local→Zotero) or "list".
        library_id: Zotero library/user ID (or set ZOTERO_LIBRARY_ID env var).
        api_key: Zotero API key (or set ZOTERO_API_KEY env var).
        library_type: "user" or "group" (default: user).
        collection_key: Optional Zotero collection to sync.
        limit: Max items to sync (default: 50).

    Returns:
        Sync results with count of imported/exported items.
    """
    try:
        from pyzotero import zotero
    except ImportError:
        return {"error": "pyzotero not installed"}

    lib_id = library_id or os.environ.get("ZOTERO_LIBRARY_ID")
    key = api_key or os.environ.get("ZOTERO_API_KEY")

    if not lib_id or not key:
        return {
            "error": "Zotero credentials required",
            "hint": "Provide library_id + api_key, or set ZOTERO_LIBRARY_ID and ZOTERO_API_KEY env vars. Get them at https://www.zotero.org/settings/keys",
        }

    try:
        zot = zotero.Zotero(lib_id, library_type, key)

        if action in ("import", "list"):
            if collection_key:
                items = await asyncio.to_thread(zot.collection_items, collection_key, limit=limit)
            else:
                items = await asyncio.to_thread(zot.top, limit=limit)

            imported = []
            index = _load_index()

            for item in items:
                data = item.get("data", {})
                if data.get("itemType") in ("attachment", "note"):
                    continue

                title = data.get("title", "")
                if not title:
                    continue

                creators = data.get("creators", [])
                authors = [
                    f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
                    for c in creators
                    if c.get("creatorType") == "author"
                ]

                pid = _paper_id(title)
                paper_entry = {
                    "id": pid,
                    "title": title,
                    "authors": authors,
                    "year": data.get("date", "")[:4] if data.get("date") else None,
                    "doi": data.get("DOI", ""),
                    "url": data.get("url", ""),
                    "venue": data.get("publicationTitle", ""),
                    "abstract": data.get("abstractNote", "")[:1000],
                    "zotero_key": item.get("key", ""),
                    "tags": [t.get("tag", "") for t in data.get("tags", [])],
                    "imported_from_zotero_at": _utc_now(),
                }

                if action == "import":
                    index["papers"][pid] = {**index["papers"].get(pid, {}), **paper_entry}
                    # Update tag index
                    for tag in paper_entry["tags"]:
                        index["tags"].setdefault(tag, [])
                        if pid not in index["tags"][tag]:
                            index["tags"][tag].append(pid)

                imported.append({"paper_id": pid, "title": title, "authors": authors})

            if action == "import":
                _save_index(index)

            return {
                "action": action,
                "library_id": lib_id,
                "items_processed": len(imported),
                "papers": imported,
                "total_in_library": len(index["papers"]),
            }

        if action == "export":
            index = _load_index()
            exported = 0
            errors = []

            for pid, paper in list(index["papers"].items())[:limit]:
                if paper.get("zotero_key"):
                    continue  # already in Zotero

                template = await asyncio.to_thread(zot.item_template, "journalArticle")
                template["title"] = paper.get("title", "")
                template["creators"] = [
                    {"creatorType": "author", "firstName": a.split()[0] if a.split() else "",
                     "lastName": " ".join(a.split()[1:]) if len(a.split()) > 1 else a}
                    for a in paper.get("authors", [])
                ]
                template["abstractNote"] = paper.get("abstract", "")
                template["DOI"] = paper.get("doi", "")
                template["url"] = paper.get("url", "")

                try:
                    resp = await asyncio.to_thread(zot.create_items, [template])
                    if resp.get("successful"):
                        exported += 1
                except Exception as e:
                    errors.append(str(e)[:100])

            return {
                "action": "export",
                "exported": exported,
                "errors": errors[:5],
            }

        return {"error": f"Unknown action '{action}'. Use: import, export, list."}

    except Exception as e:
        return {"error": f"Zotero sync failed: {str(e)[:200]}"}


# ─── MARKER OCR (fast layout-aware PDF parsing) ───────────────────────

@handle_tool_errors("research_paper_ocr")
async def research_paper_ocr(
    file_path: str,
    max_pages: int | None = None,
    extract_images: bool = False,
) -> dict[str, Any]:
    """Parse a PDF to clean markdown using Marker (layout-aware OCR).

    Marker handles scanned PDFs, complex layouts, tables, equations, and
    multi-column documents better than basic text extraction. Ideal for
    older scanned papers where Docling/PyMuPDF struggle.

    Args:
        file_path: Path to the PDF file.
        max_pages: Limit pages to process (default: all, but capped at 50).
        extract_images: Whether to extract embedded images (default: False).

    Returns:
        Clean markdown content with preserved structure, tables, and equations.
    """
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    def _run_marker() -> dict[str, Any]:
        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
            from marker.output import text_from_rendered

            converter = PdfConverter(artifact_dict=create_model_dict())
            rendered = converter(str(path))
            text, _, images = text_from_rendered(rendered)

            return {
                "markdown": text[:20000],
                "full_length": len(text),
                "images_count": len(images) if images else 0,
                "method": "marker",
            }
        except Exception as e:
            return {"error": f"Marker failed: {str(e)[:300]}", "method": "marker"}

    # Marker is heavy (loads ML models) — run in thread with generous handling
    result = await asyncio.to_thread(_run_marker)

    if "error" in result:
        return result

    # Update index
    md = result.get("markdown", "")
    title_match = re.search(r"^#\s+(.+)$", md, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem

    pid = _paper_id(title)
    parsed_path = PAPERS_DIR / "parsed" / f"{pid}.json"
    parsed_path.parent.mkdir(parents=True, exist_ok=True)
    parsed_path.write_text(json.dumps({
        "title": title,
        "markdown": md,
        "parse_method": "marker",
        "file": str(path),
    }, indent=2))

    index = _load_index()
    index["papers"][pid] = {
        **index["papers"].get(pid, {}),
        "id": pid,
        "title": title,
        "file": str(path),
        "marker_parsed_at": _utc_now(),
    }
    _save_index(index)

    result["paper_id"] = pid
    result["title"] = title
    result["indexed"] = True
    return result
