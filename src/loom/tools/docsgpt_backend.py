"""research_docs_ai — AI-powered documentation search via DocsGPT API.

Provides semantic search and Q&A over documentation using DocsGPT instances
via HTTP API calls.
"""
from __future__ import annotations

import logging
from typing import Any
import httpx

from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.docsgpt_backend")

# Constraints
MIN_QUERY_LEN = 2
MAX_QUERY_LEN = 1000
DEFAULT_DOCS_URL = "http://localhost:7091"
REQUEST_TIMEOUT = 30


@handle_tool_errors("research_docs_ai")
async def research_docs_ai(
    query: str,
    docs_url: str | None = None,
    timeout: int = 30,
    language: str = "en",
) -> dict[str, Any]:
    """Query documentation using DocsGPT API.

    Sends a question to a running DocsGPT instance and returns
    AI-generated answers with source citations.

    Args:
        query: Question or search query for documentation
        docs_url: DocsGPT API endpoint URL (default: http://localhost:7091)
        timeout: Request timeout in seconds (1-120, default: 30)
        language: Response language code (e.g., 'en', 'es', 'fr')

    Returns:
        Dict with keys:
        - query: Input query
        - answer: AI-generated answer from documentation
        - sources: List of source citations with {name, content, metadata}
        - confidence: Confidence score (0.0-1.0)
        - error: Error message if operation failed (optional)
    """
    # Input validation
    if not query or not isinstance(query, str):
        return {
            "query": "" if not isinstance(query, str) else query,
            "error": "query must be a non-empty string",
            "answer": "",
            "sources": [],
            "confidence": 0.0,
        }

    query = query.strip()
    if len(query) < MIN_QUERY_LEN or len(query) > MAX_QUERY_LEN:
        return {
            "query": query,
            "error": f"query length must be {MIN_QUERY_LEN}-{MAX_QUERY_LEN} chars",
            "answer": "",
            "sources": [],
            "confidence": 0.0,
        }

    # Validate and normalize docs_url
    if not docs_url:
        docs_url = DEFAULT_DOCS_URL
    else:
        docs_url = str(docs_url).strip()

    # Ensure docs_url has a scheme
    if not docs_url.startswith(("http://", "https://")):
        docs_url = f"http://{docs_url}"

    # Validate timeout
    if not isinstance(timeout, int) or timeout < 1 or timeout > 120:
        timeout = REQUEST_TIMEOUT

    # Validate language
    if not isinstance(language, str):
        language = "en"
    language = language.strip().lower()[:10]  # Max 10 chars
    # Ensure language code is alphanumeric + hyphen (ISO 639 format)
    if not all(c.isalnum() or c == "-" for c in language):
        language = "en"

    try:
        # Construct endpoint URL
        endpoint = docs_url.rstrip("/") + "/api/answer"

        logger.info("docsgpt_query_start query=%s endpoint=%s", query[:50], endpoint)

        # Prepare request payload
        payload = {
            "question": query,
            "language": language,
        }

        # Make async HTTP request
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()

        try:
            result_data = response.json()
        except ValueError as e:
            logger.warning("docsgpt_json_parse_error endpoint=%s: %s", endpoint, e)
            return {
                "query": query,
                "error": "DocsGPT returned invalid JSON response",
                "answer": "",
                "sources": [],
                "confidence": 0.0,
                "docs_url": docs_url,
            }

        # Parse response
        answer = ""
        sources = []
        confidence = 0.0

        if isinstance(result_data, dict):
            # Extract answer
            if "answer" in result_data:
                answer = str(result_data["answer"])
            elif "result" in result_data:
                answer = str(result_data["result"])
            elif "data" in result_data:
                data = result_data["data"]
                if isinstance(data, dict):
                    answer = str(data.get("answer", data.get("result", "")))

            # Extract sources
            if "sources" in result_data:
                raw_sources = result_data["sources"]
                if isinstance(raw_sources, list):
                    for src in raw_sources:
                        if isinstance(src, dict):
                            sources.append({
                                "name": src.get("name", src.get("title", "Unknown")),
                                "content": src.get("content", "")[:500],  # First 500 chars
                                "metadata": {
                                    "page": src.get("page"),
                                    "location": src.get("location"),
                                    "score": src.get("score"),
                                },
                            })

            # Extract confidence score
            if "confidence" in result_data:
                try:
                    confidence = float(result_data["confidence"])
                except (ValueError, TypeError):
                    confidence = 0.0

        logger.info(
            "docsgpt_query_complete query=%s sources=%d confidence=%.2f",
            query[:50],
            len(sources),
            confidence,
        )

        return {
            "query": query,
            "answer": answer,
            "sources": sources,
            "confidence": min(1.0, max(0.0, confidence)),  # Clamp to [0, 1]
            "docs_url": docs_url,
        }

    except httpx.ConnectError as e:
        logger.warning("docsgpt_connection_failed endpoint=%s: %s", docs_url, e)
        return {
            "query": query,
            "error": f"DocsGPT service not available at {docs_url}",
            "answer": "",
            "sources": [],
            "confidence": 0.0,
            "docs_url": docs_url,
        }

    except httpx.TimeoutException as e:
        logger.warning("docsgpt_timeout query=%s timeout=%ds: %s", query[:50], timeout, e)
        return {
            "query": query,
            "error": f"DocsGPT request timeout after {timeout} seconds",
            "answer": "",
            "sources": [],
            "confidence": 0.0,
            "docs_url": docs_url,
        }

    except httpx.HTTPStatusError as e:
        logger.warning("docsgpt_http_error query=%s status=%d: %s", query[:50], e.response.status_code, e)
        return {
            "query": query,
            "error": f"DocsGPT API error: HTTP {e.response.status_code}",
            "answer": "",
            "sources": [],
            "confidence": 0.0,
            "docs_url": docs_url,
        }

    except Exception as e:
        logger.error("docsgpt_failed query=%s: %s", query[:50], e)
        return {
            "query": query,
            "error": f"DocsGPT error: {str(e)}",
            "answer": "",
            "sources": [],
            "confidence": 0.0,
            "docs_url": docs_url,
        }
