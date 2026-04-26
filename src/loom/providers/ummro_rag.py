"""UMMRO RAG — Semantic vector search over 2.6M doc + 7M code corpus."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger("loom.providers.ummro_rag")

# UMMRO RAG API endpoint (must be set via UMMRO_RAG_URL environment variable)
# Using direct IPs is not recommended; use domain names with HTTPS for production


def search_ummro_rag(
    query: str,
    n: int = 10,
    collection: str = "documents",
    **kwargs: Any,
) -> dict[str, Any]:
    """Search UMMRO's semantic vector corpus for relevant documents/code.

    Connects to UMMRO's on-Hetzner RAG service supporting:
    - documents: 2.6M vectors from academic papers, articles, PDFs, etc.
    - code: 7M vectors from GitHub repositories, CodeSearchNet, etc.

    Handles connection failures gracefully (Hetzner may be down).

    Args:
        query: semantic search query (free text, supports multi-language)
        n: number of top-k results to return (1-100, default 10)
        collection: "documents" (2.6M vectors) or "code" (7M vectors)
        **kwargs: ignored (accepted for interface compatibility)

    Returns:
        Dict with keys:
        - results: list of dicts with keys:
          - text: document/code snippet text
          - score: semantic relevance score (0-1)
          - metadata: dict with source, url, author, language, etc.
        - query: original query string
        - collection: collection searched
        - count: number of results returned
        - error: error message if search failed
    """
    # Validate collection
    if collection not in ("documents", "code"):
        return {
            "results": [],
            "query": query,
            "error": f"Invalid collection: {collection}. "
            "Must be 'documents' or 'code'",
        }

    # Validate n (top-k)
    n = max(1, min(n, 100))

    # Validate query
    if not query or not query.strip():
        return {
            "results": [],
            "query": query,
            "error": "query must be non-empty",
        }

    query = query.strip()

    # Get API endpoint from environment (required)
    api_url = os.environ.get("UMMRO_RAG_URL", "").rstrip("/")
    if not api_url:
        return {
            "results": [],
            "query": query,
            "error": "UMMRO_RAG_URL environment variable not set",
        }

    logger.info(
        "ummro_rag_search query=%s collection=%s top_k=%d",
        query[:60],
        collection,
        n,
    )

    try:
        # Validate API URL scheme (require https for security)
        if not api_url.startswith(("http://", "https://")):
            return {
                "results": [],
                "query": query,
                "error": "Invalid UMMRO_RAG_URL scheme (must be http:// or https://)",
            }

        # Call UMMRO RAG API
        endpoint = f"{api_url}/search"

        payload = {
            "query": query,
            "top_k": n,
            "collection": collection,
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # Normalize results
        results = []
        if isinstance(data.get("results"), list):
            for item in data["results"]:
                if isinstance(item, dict):
                    results.append(
                        {
                            "text": item.get("text", "")[:5000],  # Cap snippet
                            "score": float(item.get("score", 0.0)),
                            "metadata": item.get("metadata", {}),
                        }
                    )

        return {
            "results": results,
            "query": query,
            "collection": collection,
            "count": len(results),
        }

    except httpx.ConnectError:
        logger.warning("ummro_rag_connect_error url=%s", api_url)
        return {
            "results": [],
            "query": query,
            "collection": collection,
            "error": f"Cannot connect to UMMRO RAG at {api_url} (Hetzner may be down)",
            "count": 0,
        }

    except httpx.TimeoutException:
        logger.warning("ummro_rag_timeout query=%s", query[:60])
        return {
            "results": [],
            "query": query,
            "collection": collection,
            "error": "UMMRO RAG search timed out",
            "count": 0,
        }

    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        logger.warning(
            "ummro_rag_http_error query=%s status=%d",
            query[:60],
            code,
        )
        return {
            "results": [],
            "query": query,
            "collection": collection,
            "error": f"UMMRO RAG returned HTTP {code}",
            "count": 0,
        }

    except ValueError:
        logger.error("ummro_rag_json_error query=%s", query[:60])
        return {
            "results": [],
            "query": query,
            "collection": collection,
            "error": "UMMRO RAG returned invalid JSON",
            "count": 0,
        }

    except Exception as exc:
        logger.error(
            "ummro_rag_failed query=%s error=%s",
            query[:60],
            type(exc).__name__,
        )
        return {
            "results": [],
            "query": query,
            "collection": collection,
            "error": f"UMMRO RAG search failed: {type(exc).__name__}",
            "count": 0,
        }
