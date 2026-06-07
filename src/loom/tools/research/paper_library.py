"""Paper Library — research paper management, indexing, tagging, and organization.

Integrates:
- Docling: PDF/document parsing to structured markdown/JSON
- GROBID: ML-based scholarly metadata extraction (title, authors, citations)
- Semantic Scholar: Paper enrichment from 200M+ papers database
- paperscraper: Multi-source paper discovery (arxiv, pubmed, medrxiv)
- paper-qa: RAG over local paper collections with citations
- Qdrant: Embedding storage for semantic paper search
- arxiv: Direct arxiv paper download and metadata

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.paper_library")

PAPERS_DIR = Path(os.environ.get("LOOM_PAPERS_DIR", "/home/aadel/.loom/papers"))
PAPERS_INDEX = PAPERS_DIR / "index.json"
PAPERS_EMBEDDINGS_DIR = PAPERS_DIR / "embeddings"


def _ensure_dirs() -> None:
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)
    (PAPERS_DIR / "pdfs").mkdir(exist_ok=True)
    (PAPERS_DIR / "parsed").mkdir(exist_ok=True)
    (PAPERS_DIR / "metadata").mkdir(exist_ok=True)
    PAPERS_EMBEDDINGS_DIR.mkdir(exist_ok=True)


def _load_index() -> dict[str, Any]:
    if PAPERS_INDEX.exists():
        return json.loads(PAPERS_INDEX.read_text())
    return {"papers": {}, "tags": {}, "collections": {}}


def _save_index(index: dict[str, Any]) -> None:
    _ensure_dirs()
    PAPERS_INDEX.write_text(json.dumps(index, indent=2, default=str))


def _paper_id(title: str) -> str:
    return hashlib.sha256(title.lower().strip().encode()).hexdigest()[:12]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─── PAPER PARSING (Docling + GROBID) ─────────────────────────────────

@handle_tool_errors("research_paper_parse")
async def research_paper_parse(
    file_path: str,
    extract_references: bool = True,
    extract_figures: bool = False,
) -> dict[str, Any]:
    """Parse a PDF paper and extract structured content, metadata, and references.

    Uses Docling for high-quality document conversion and falls back to
    PyMuPDF + regex for metadata extraction. Stores parsed output locally.

    Args:
        file_path: Path to the PDF file to parse.
        extract_references: Whether to extract reference list (default: True).
        extract_figures: Whether to extract figure descriptions (default: False).

    Returns:
        Parsed paper with title, authors, abstract, sections, and references.
    """
    _ensure_dirs()
    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    result: dict[str, Any] = {
        "file": str(path),
        "title": "",
        "authors": [],
        "abstract": "",
        "sections": [],
        "references": [],
        "metadata": {},
        "parse_method": "",
    }

    # Strategy 1: Docling (best quality)
    try:
        from docling.document_converter import DocumentConverter
        converter = DocumentConverter()
        doc_result = await asyncio.to_thread(converter.convert, str(path))
        doc = doc_result.document

        result["title"] = doc.title or ""
        result["parse_method"] = "docling"

        md_content = doc_result.document.export_to_markdown()
        result["markdown"] = md_content[:5000]

        sections = []
        for item in doc.iterate_items():
            if hasattr(item, "text") and item.text:
                sections.append({"text": item.text[:500]})
        result["sections"] = sections[:20]

    except Exception as e:
        logger.info(f"Docling failed ({e}), falling back to PyMuPDF")

        # Strategy 2: PyMuPDF fallback
        try:
            import fitz
            pdf = await asyncio.to_thread(fitz.open, str(path))
            result["parse_method"] = "pymupdf"
            result["metadata"]["pages"] = len(pdf)

            first_page_text = pdf[0].get_text() if len(pdf) > 0 else ""

            lines = first_page_text.strip().split("\n")
            if lines:
                result["title"] = lines[0].strip()

            abstract_match = re.search(
                r"(?:abstract|summary)[:\s]*(.{50,2000}?)(?:\n\n|\n[A-Z1-9])",
                first_page_text,
                re.IGNORECASE | re.DOTALL,
            )
            if abstract_match:
                result["abstract"] = abstract_match.group(1).strip()

            full_text = ""
            for page in pdf[:5]:
                full_text += page.get_text() + "\n"
            result["markdown"] = full_text[:5000]

            if extract_references:
                last_pages_text = ""
                for page in pdf[-3:]:
                    last_pages_text += page.get_text()
                refs = re.findall(
                    r"\[(\d+)\]\s*(.+?)(?=\[\d+\]|\Z)",
                    last_pages_text,
                    re.DOTALL,
                )
                result["references"] = [
                    {"id": int(r[0]), "text": r[1].strip()[:200]}
                    for r in refs[:50]
                ]

            pdf.close()

        except Exception as e2:
            result["error"] = f"Both parsers failed: docling={e}, pymupdf={e2}"
            return result

    # Save parsed output
    paper_id = _paper_id(result["title"] or path.stem)
    parsed_path = PAPERS_DIR / "parsed" / f"{paper_id}.json"
    parsed_path.write_text(json.dumps(result, indent=2, default=str))

    # Update index
    index = _load_index()
    index["papers"][paper_id] = {
        "id": paper_id,
        "title": result["title"],
        "authors": result["authors"],
        "file": str(path),
        "parsed_at": _utc_now(),
        "sections_count": len(result.get("sections", [])),
        "references_count": len(result.get("references", [])),
    }
    _save_index(index)

    result["paper_id"] = paper_id
    result["indexed"] = True
    return result


# ─── METADATA ENRICHMENT (Semantic Scholar) ────────────────────────────

@handle_tool_errors("research_paper_enrich")
async def research_paper_enrich(
    title: str | None = None,
    doi: str | None = None,
    arxiv_id: str | None = None,
    paper_id: str | None = None,
) -> dict[str, Any]:
    """Enrich paper metadata from Semantic Scholar (200M+ papers).

    Fetches full metadata including citations, references, venue, year,
    abstract, authors with affiliations, and related papers.

    Args:
        title: Paper title to search for.
        doi: DOI identifier (e.g., "10.1234/example").
        arxiv_id: ArXiv ID (e.g., "2301.12345").
        paper_id: Local paper ID from index (auto-fetches title).

    Returns:
        Enriched metadata from Semantic Scholar with citation counts.
    """
    from semanticscholar import SemanticScholar

    sch = SemanticScholar()

    if paper_id:
        index = _load_index()
        paper = index["papers"].get(paper_id)
        if paper:
            title = paper.get("title")

    if not title and not doi and not arxiv_id:
        return {"error": "Provide at least one of: title, doi, arxiv_id, paper_id"}

    try:
        if doi:
            paper_data = await asyncio.to_thread(sch.get_paper, f"DOI:{doi}")
        elif arxiv_id:
            paper_data = await asyncio.to_thread(sch.get_paper, f"ARXIV:{arxiv_id}")
        else:
            results = await asyncio.to_thread(sch.search_paper, title, limit=3)
            if not results or len(results) == 0:
                return {"error": f"No results found for: {title}"}
            paper_data = results[0]

        enriched = {
            "paperId": paper_data.paperId,
            "title": paper_data.title,
            "abstract": paper_data.abstract or "",
            "year": paper_data.year,
            "venue": paper_data.venue or "",
            "citationCount": paper_data.citationCount,
            "referenceCount": paper_data.referenceCount,
            "influentialCitationCount": paper_data.influentialCitationCount,
            "fieldsOfStudy": paper_data.fieldsOfStudy or [],
            "authors": [
                {"name": a.name, "authorId": a.authorId}
                for a in (paper_data.authors or [])
            ],
            "url": paper_data.url or "",
            "doi": getattr(paper_data, "externalIds", {}).get("DOI", ""),
            "arxivId": getattr(paper_data, "externalIds", {}).get("ArXiv", ""),
        }

        # Update local index if we have a paper_id
        if paper_id:
            index = _load_index()
            if paper_id in index["papers"]:
                index["papers"][paper_id]["semantic_scholar"] = enriched
                index["papers"][paper_id]["citation_count"] = enriched["citationCount"]
                index["papers"][paper_id]["year"] = enriched["year"]
                _save_index(index)
                enriched["local_updated"] = True

        return enriched

    except Exception as e:
        return {"error": f"Semantic Scholar lookup failed: {str(e)[:200]}"}


# ─── PAPER DISCOVERY (paperscraper + arxiv) ────────────────────────────

@handle_tool_errors("research_paper_discover")
async def research_paper_discover(
    query: str,
    sources: list[str] | None = None,
    max_results: int = 20,
    year_from: int | None = None,
) -> dict[str, Any]:
    """Discover research papers across multiple academic sources.

    Searches arxiv, pubmed, medrxiv, biorxiv, and Semantic Scholar
    to find relevant papers matching your query.

    Args:
        query: Search query (topic, keywords, or research question).
        sources: Sources to search (default: arxiv, semantic_scholar).
            Available: arxiv, pubmed, medrxiv, biorxiv, semantic_scholar.
        max_results: Maximum papers to return per source (default: 20).
        year_from: Only include papers from this year onward.

    Returns:
        Discovered papers with titles, authors, abstracts, and download links.
    """
    active_sources = sources or ["arxiv", "semantic_scholar"]
    all_papers: list[dict] = []

    # Source 1: arxiv
    if "arxiv" in active_sources:
        try:
            import arxiv
            client = arxiv.Client()
            search = arxiv.Search(
                query=query,
                max_results=min(max_results, 50),
                sort_by=arxiv.SortCriterion.Relevance,
            )
            results = await asyncio.to_thread(list, client.results(search))
            for r in results:
                if year_from and r.published.year < year_from:
                    continue
                all_papers.append({
                    "title": r.title,
                    "authors": [a.name for a in r.authors[:5]],
                    "abstract": r.summary[:500],
                    "year": r.published.year,
                    "url": r.entry_id,
                    "pdf_url": r.pdf_url,
                    "arxiv_id": r.entry_id.split("/")[-1],
                    "categories": r.categories,
                    "source": "arxiv",
                })
        except Exception as e:
            logger.warning(f"arxiv search failed: {e}")

    # Source 2: Semantic Scholar
    if "semantic_scholar" in active_sources:
        try:
            from semanticscholar import SemanticScholar
            sch = SemanticScholar()
            results = await asyncio.to_thread(
                sch.search_paper, query, limit=min(max_results, 50)
            )
            for r in (results or []):
                if year_from and r.year and r.year < year_from:
                    continue
                all_papers.append({
                    "title": r.title,
                    "authors": [a.name for a in (r.authors or [])[:5]],
                    "abstract": (r.abstract or "")[:500],
                    "year": r.year,
                    "url": r.url or "",
                    "citation_count": r.citationCount,
                    "venue": r.venue or "",
                    "source": "semantic_scholar",
                })
        except Exception as e:
            logger.warning(f"Semantic Scholar search failed: {e}")

    # Source 3: paperscraper (pubmed, medrxiv, biorxiv)
    bio_sources = [s for s in active_sources if s in ("pubmed", "medrxiv", "biorxiv")]
    if bio_sources:
        try:
            from paperscraper.get_dumps import QUERY_FN_DICT
            for src in bio_sources:
                if src in QUERY_FN_DICT:
                    papers = await asyncio.to_thread(
                        QUERY_FN_DICT[src], query, max_results
                    )
                    for p in papers:
                        all_papers.append({
                            "title": p.get("title", ""),
                            "authors": p.get("authors", [])[:5],
                            "abstract": p.get("abstract", "")[:500],
                            "year": p.get("year"),
                            "doi": p.get("doi", ""),
                            "source": src,
                        })
        except Exception as e:
            logger.warning(f"paperscraper failed: {e}")

    # Sort by year (newest first)
    all_papers.sort(key=lambda x: x.get("year") or 0, reverse=True)

    return {
        "query": query,
        "sources_searched": active_sources,
        "papers": all_papers[:max_results],
        "total_found": len(all_papers),
    }


# ─── PAPER DOWNLOAD ───────────────────────────────────────────────────

@handle_tool_errors("research_paper_download")
async def research_paper_download(
    arxiv_id: str | None = None,
    pdf_url: str | None = None,
    title: str | None = None,
) -> dict[str, Any]:
    """Download a paper PDF and store it in the local library.

    Downloads from arxiv by ID or any direct PDF URL.
    Auto-parses metadata after download.

    Args:
        arxiv_id: ArXiv paper ID (e.g., "2301.12345").
        pdf_url: Direct URL to PDF file.
        title: Optional title for naming the file.

    Returns:
        Download result with local file path and basic metadata.
    """
    import requests

    _ensure_dirs()

    if not arxiv_id and not pdf_url:
        return {"error": "Provide either arxiv_id or pdf_url"}

    if arxiv_id:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        filename = f"{arxiv_id.replace('/', '_')}.pdf"
    else:
        filename = _paper_id(title or pdf_url or "unknown") + ".pdf"

    save_path = PAPERS_DIR / "pdfs" / filename

    if save_path.exists():
        return {
            "status": "already_exists",
            "path": str(save_path),
            "size_kb": save_path.stat().st_size // 1024,
        }

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (research-bot; academic use)",
        }
        resp = await asyncio.to_thread(
            lambda: requests.get(pdf_url, headers=headers, timeout=30, allow_redirects=True)
        )
        if resp.status_code != 200:
            return {"error": f"Download failed: HTTP {resp.status_code}"}

        if len(resp.content) < 1000:
            return {"error": "Downloaded file too small — likely not a PDF"}

        save_path.write_bytes(resp.content)

        # Update index
        paper_id = _paper_id(title or arxiv_id or filename)
        index = _load_index()
        index["papers"][paper_id] = {
            "id": paper_id,
            "title": title or arxiv_id or filename,
            "file": str(save_path),
            "arxiv_id": arxiv_id,
            "downloaded_at": _utc_now(),
            "size_kb": len(resp.content) // 1024,
        }
        _save_index(index)

        return {
            "status": "downloaded",
            "paper_id": paper_id,
            "path": str(save_path),
            "size_kb": len(resp.content) // 1024,
            "arxiv_id": arxiv_id,
        }

    except Exception as e:
        return {"error": f"Download failed: {str(e)[:200]}"}


# ─── PAPER TAGGING & ORGANIZATION ─────────────────────────────────────

@handle_tool_errors("research_paper_tag")
async def research_paper_tag(
    paper_id: str,
    tags: list[str],
    collection: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Tag and organize a paper in your local library.

    Adds tags, assigns to collections, and attaches notes for
    later retrieval and organization.

    Args:
        paper_id: Local paper ID from index.
        tags: List of tags to add (e.g., ["transformer", "attention", "2026"]).
        collection: Optional collection name to assign to (e.g., "AI Safety").
        notes: Optional research notes to attach.

    Returns:
        Updated paper entry with tags and collection assignment.
    """
    index = _load_index()

    if paper_id not in index["papers"]:
        return {"error": f"Paper {paper_id} not found in index"}

    paper = index["papers"][paper_id]

    # Add tags
    existing_tags = set(paper.get("tags", []))
    existing_tags.update(tags)
    paper["tags"] = sorted(existing_tags)

    # Update tag index
    for tag in tags:
        if tag not in index["tags"]:
            index["tags"][tag] = []
        if paper_id not in index["tags"][tag]:
            index["tags"][tag].append(paper_id)

    # Assign collection
    if collection:
        paper["collection"] = collection
        if collection not in index["collections"]:
            index["collections"][collection] = []
        if paper_id not in index["collections"][collection]:
            index["collections"][collection].append(paper_id)

    # Add notes
    if notes:
        paper["notes"] = paper.get("notes", "") + f"\n[{_utc_now()}] {notes}"

    paper["updated_at"] = _utc_now()
    index["papers"][paper_id] = paper
    _save_index(index)

    return {
        "paper_id": paper_id,
        "title": paper.get("title", ""),
        "tags": paper["tags"],
        "collection": paper.get("collection"),
        "notes_length": len(paper.get("notes", "")),
    }


# ─── PAPER SEARCH & RETRIEVAL ─────────────────────────────────────────

@handle_tool_errors("research_paper_search")
async def research_paper_search(
    query: str | None = None,
    tags: list[str] | None = None,
    collection: str | None = None,
    year: int | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Search your local paper library by text, tags, collection, or year.

    Searches across all indexed papers with combined filtering.

    Args:
        query: Text search in title, abstract, and notes.
        tags: Filter by tags (papers with ANY matching tag).
        collection: Filter by collection name.
        year: Filter by publication year.
        limit: Maximum results (default: 20).

    Returns:
        Matching papers with metadata, tags, and collection info.
    """
    index = _load_index()
    results = []
    query_lower = (query or "").lower()

    for pid, paper in index["papers"].items():
        # Text filter
        if query_lower:
            searchable = " ".join([
                paper.get("title", ""),
                paper.get("abstract", ""),
                paper.get("notes", ""),
                " ".join(paper.get("tags", [])),
            ]).lower()
            if query_lower not in searchable:
                continue

        # Tag filter
        if tags:
            paper_tags = set(paper.get("tags", []))
            if not paper_tags.intersection(set(tags)):
                continue

        # Collection filter
        if collection and paper.get("collection") != collection:
            continue

        # Year filter
        if year and paper.get("year") != year:
            continue

        results.append({
            "paper_id": pid,
            "title": paper.get("title", ""),
            "authors": paper.get("authors", []),
            "year": paper.get("year"),
            "tags": paper.get("tags", []),
            "collection": paper.get("collection"),
            "citation_count": paper.get("citation_count"),
            "file": paper.get("file", ""),
        })

    # Sort by citation count (if available), then by date
    results.sort(
        key=lambda x: (x.get("citation_count") or 0, x.get("year") or 0),
        reverse=True,
    )

    return {
        "query": query,
        "filters": {"tags": tags, "collection": collection, "year": year},
        "results": results[:limit],
        "total_found": len(results),
        "total_in_library": len(index["papers"]),
    }


# ─── PAPER EMBEDDING & SEMANTIC SEARCH ────────────────────────────────

@handle_tool_errors("research_paper_embed")
async def research_paper_embed(
    paper_id: str | None = None,
    embed_all: bool = False,
) -> dict[str, Any]:
    """Generate embeddings for papers and store in Qdrant for semantic search.

    Embeds paper title + abstract using sentence-transformers (MiniLM-L6-v2)
    and upserts into a dedicated Qdrant collection for paper search.

    Args:
        paper_id: Specific paper to embed (omit with embed_all=True for batch).
        embed_all: Embed all un-embedded papers in the library.

    Returns:
        Embedding results with count of papers embedded.
    """
    try:
        from sentence_transformers import SentenceTransformer
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct, VectorParams, Distance
    except ImportError as e:
        return {"error": f"Missing dependency: {e}. Install sentence-transformers and qdrant-client."}

    index = _load_index()
    model = SentenceTransformer("all-MiniLM-L6-v2")
    qdrant = QdrantClient(url="http://localhost:6333")

    collection_name = "loom_paper_library"

    # Ensure collection exists
    try:
        qdrant.get_collection(collection_name)
    except Exception:
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

    papers_to_embed = []
    if paper_id:
        if paper_id in index["papers"]:
            papers_to_embed.append((paper_id, index["papers"][paper_id]))
    elif embed_all:
        for pid, paper in index["papers"].items():
            if not paper.get("embedded"):
                papers_to_embed.append((pid, paper))

    if not papers_to_embed:
        return {"message": "No papers to embed", "total_in_library": len(index["papers"])}

    points = []
    for pid, paper in papers_to_embed:
        text = f"{paper.get('title', '')}. {paper.get('abstract', '')}"
        if not text.strip():
            continue

        embedding = model.encode(text).tolist()
        points.append(PointStruct(
            id=int(hashlib.md5(pid.encode(), usedforsecurity=False).hexdigest()[:8], 16),
            vector=embedding,
            payload={
                "paper_id": pid,
                "title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "year": paper.get("year"),
                "tags": paper.get("tags", []),
                "collection": paper.get("collection"),
            },
        ))

        paper["embedded"] = True
        paper["embedded_at"] = _utc_now()

    if points:
        await asyncio.to_thread(
            qdrant.upsert, collection_name=collection_name, points=points
        )

    _save_index(index)

    return {
        "embedded_count": len(points),
        "collection": collection_name,
        "total_in_library": len(index["papers"]),
    }


@handle_tool_errors("research_paper_semantic_search")
async def research_paper_semantic_search(
    query: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Semantic search across your paper library using embeddings.

    Finds papers by meaning similarity, not just keyword matching.
    Papers must be embedded first (use research_paper_embed).

    Args:
        query: Natural language research question or topic.
        limit: Maximum results (default: 10).

    Returns:
        Semantically similar papers ranked by relevance score.
    """
    try:
        from sentence_transformers import SentenceTransformer
        from qdrant_client import QdrantClient
    except ImportError as e:
        return {"error": f"Missing dependency: {e}"}

    model = SentenceTransformer("all-MiniLM-L6-v2")
    qdrant = QdrantClient(url="http://localhost:6333")

    query_vector = model.encode(query).tolist()

    try:
        results = await asyncio.to_thread(
            qdrant.search,
            collection_name="loom_paper_library",
            query_vector=query_vector,
            limit=limit,
        )
    except Exception as e:
        return {"error": f"Search failed: {str(e)[:200]}"}

    papers = []
    for hit in results:
        payload = hit.payload or {}
        papers.append({
            "paper_id": payload.get("paper_id", ""),
            "title": payload.get("title", ""),
            "authors": payload.get("authors", []),
            "year": payload.get("year"),
            "tags": payload.get("tags", []),
            "score": round(hit.score, 4),
        })

    return {
        "query": query,
        "results": papers,
        "total_found": len(papers),
    }


# ─── PAPER QA (RAG over papers) ───────────────────────────────────────

@handle_tool_errors("research_paper_qa")
async def research_paper_qa(
    question: str,
    paper_ids: list[str] | None = None,
    collection: str | None = None,
) -> dict[str, Any]:
    """Ask questions about your paper collection with cited answers.

    Uses RAG (Retrieval-Augmented Generation) to answer questions
    from your local paper library with specific citations.

    Args:
        question: Research question to answer from papers.
        paper_ids: Specific papers to search (omit for all).
        collection: Filter to papers in a specific collection.

    Returns:
        Answer with citations pointing to specific papers and passages.
    """
    index = _load_index()

    # Gather relevant paper texts
    papers_text = []
    target_papers = {}

    if paper_ids:
        target_papers = {pid: index["papers"][pid] for pid in paper_ids if pid in index["papers"]}
    elif collection:
        pids = index["collections"].get(collection, [])
        target_papers = {pid: index["papers"][pid] for pid in pids if pid in index["papers"]}
    else:
        target_papers = index["papers"]

    for pid, paper in list(target_papers.items())[:20]:
        parsed_path = PAPERS_DIR / "parsed" / f"{pid}.json"
        if parsed_path.exists():
            parsed = json.loads(parsed_path.read_text())
            text = parsed.get("markdown", parsed.get("abstract", ""))[:2000]
            papers_text.append({
                "paper_id": pid,
                "title": paper.get("title", ""),
                "text": text,
            })

    if not papers_text:
        return {
            "error": "No parsed papers found. Parse papers first with research_paper_parse.",
            "suggestion": "Run research_paper_parse on your PDFs first.",
        }

    # Build context for LLM
    context = "\n\n".join([
        f"[Paper: {p['title']}]\n{p['text']}"
        for p in papers_text[:10]
    ])

    # Use Loom's LLM to answer (research_llm_chat — standard messages format)
    try:
        import aiohttp
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a research assistant. Answer the question using ONLY the "
                    "provided paper excerpts. Cite the paper title in brackets for each "
                    "claim. If the papers don't contain the answer, say so."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nPaper excerpts:\n{context[:8000]}",
            },
        ]
        payload = {"messages": messages, "max_tokens": 1500, "temperature": 0.2}
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8788/api/v1/tools/research_llm_chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=90),
            ) as resp:
                if resp.status == 200:
                    llm_result = await resp.json()
                    answer = (
                        llm_result.get("content")
                        or llm_result.get("response")
                        or llm_result.get("answer")
                        or llm_result.get("text")
                        or str(llm_result)
                    )
                    return {
                        "question": question,
                        "answer": answer,
                        "model": llm_result.get("model", ""),
                        "provider": llm_result.get("provider", ""),
                        "papers_consulted": len(papers_text),
                        "sources": [{"paper_id": p["paper_id"], "title": p["title"]} for p in papers_text[:10]],
                    }
                body = await resp.text()
                return {"error": f"LLM call failed: HTTP {resp.status}", "detail": body[:300]}
    except Exception as e:
        return {"error": f"QA failed: {str(e)[:200]}"}


# ─── LIBRARY STATS ────────────────────────────────────────────────────

@handle_tool_errors("research_paper_library_stats")
async def research_paper_library_stats() -> dict[str, Any]:
    """Get statistics about your local paper library.

    Returns:
        Library stats: paper count, tags, collections, storage usage.
    """
    _ensure_dirs()
    index = _load_index()

    pdf_dir = PAPERS_DIR / "pdfs"
    total_size = sum(f.stat().st_size for f in pdf_dir.glob("*.pdf")) if pdf_dir.exists() else 0

    return {
        "total_papers": len(index["papers"]),
        "total_tags": len(index["tags"]),
        "total_collections": len(index["collections"]),
        "collections": {k: len(v) for k, v in index["collections"].items()},
        "top_tags": sorted(
            [(tag, len(pids)) for tag, pids in index["tags"].items()],
            key=lambda x: x[1],
            reverse=True,
        )[:20],
        "embedded_count": sum(1 for p in index["papers"].values() if p.get("embedded")),
        "storage_mb": round(total_size / (1024 * 1024), 1),
        "papers_dir": str(PAPERS_DIR),
    }


# ─── GROBID METADATA EXTRACTION ───────────────────────────────────────

@handle_tool_errors("research_paper_grobid")
async def research_paper_grobid(
    file_path: str,
    grobid_url: str = "https://kermitt2-grobid.hf.space",
) -> dict[str, Any]:
    """Extract structured metadata from a paper using GROBID ML service.

    GROBID uses machine learning to extract: title, authors with affiliations,
    abstract, keywords, full reference list with DOIs, and section structure.

    Args:
        file_path: Path to the PDF file.
        grobid_url: GROBID service URL (default: HuggingFace hosted instance).

    Returns:
        Structured metadata: title, authors, abstract, keywords, references.
    """
    import requests

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    try:
        with open(path, "rb") as f:
            resp = await asyncio.to_thread(
                lambda: requests.post(
                    f"{grobid_url}/api/processHeaderDocument",
                    files={"input": f},
                    timeout=60,
                )
            )

        if resp.status_code != 200:
            return {"error": f"GROBID returned HTTP {resp.status_code}"}

        # Parse TEI XML response
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.text)

        ns = {"tei": "http://www.tei-c.org/ns/1.0"}

        title_el = root.find(".//tei:titleStmt/tei:title", ns)
        title = title_el.text if title_el is not None else ""

        authors = []
        for author in root.findall(".//tei:author/tei:persName", ns):
            first = author.find("tei:forename", ns)
            last = author.find("tei:surname", ns)
            name = f"{first.text if first is not None else ''} {last.text if last is not None else ''}".strip()
            if name:
                authors.append(name)

        abstract_el = root.find(".//tei:profileDesc/tei:abstract", ns)
        abstract = ""
        if abstract_el is not None:
            abstract = " ".join(abstract_el.itertext()).strip()

        keywords = []
        for kw in root.findall(".//tei:keywords/tei:term", ns):
            if kw.text:
                keywords.append(kw.text.strip())

        result = {
            "title": title,
            "authors": authors,
            "abstract": abstract[:1000],
            "keywords": keywords,
            "method": "grobid",
            "grobid_url": grobid_url,
        }

        # Update index
        if title:
            pid = _paper_id(title)
            index = _load_index()
            if pid not in index["papers"]:
                index["papers"][pid] = {}
            index["papers"][pid].update({
                "id": pid,
                "title": title,
                "authors": authors,
                "keywords": keywords,
                "file": str(path),
                "grobid_parsed_at": _utc_now(),
            })
            _save_index(index)
            result["paper_id"] = pid
            result["indexed"] = True

        return result

    except Exception as e:
        return {"error": f"GROBID extraction failed: {str(e)[:200]}"}
