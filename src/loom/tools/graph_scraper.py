"""research_graph_scrape — LLM-powered structured data extraction from web pages.

Integrates ScrapeGraphAI for intelligent graph-based scraping, with fallback to
Loom's own LLM providers (GROQ, NVIDIA NIM, DeepSeek, etc.) for structured
data extraction from URLs and text.

Tools:
  - research_graph_scrape(url, query, model="auto") -> dict
    LLM pipeline: URL → smart crawl → extract structured data

  - research_knowledge_extract(text, entity_types=None) -> dict
    Extract entities and relationships from text using LLM

  - research_multi_page_graph(urls, query) -> dict
    Scrape multiple pages and build unified knowledge graph
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from typing import Any

import httpx

from loom.validators import validate_url

try:
    from loom.cache import get_cache
    from loom.config import CONFIG
    from loom.params import (
        GraphScraperParams,
        KnowledgeExtractParams,
        MultiPageGraphParams,
    )
    from loom.providers.base import LLMProvider
    from loom.tools.fetch import research_fetch
    from loom.tools.markdown import research_markdown
    _GRAPH_DEPS = True
except ImportError:
    _GRAPH_DEPS = False

logger = logging.getLogger("loom.tools.graph_scraper")

# Try to import ScrapeGraphAI, fallback gracefully if not available
try:
    from scrapegraphai.graphs import SmartScraperGraph

    SCRAPEGRAPHAI_AVAILABLE = True
except ImportError:
    SCRAPEGRAPHAI_AVAILABLE = False
    logger.debug("ScrapeGraphAI not installed; using fallback LLM extraction")


def _get_llm_provider() -> LLMProvider | None:
    """Get an available LLM provider from Loom's cascade."""
    try:
        from loom.providers.groq_provider import GroqProvider
        from loom.providers.nvidia_nim import NVIDIANIMProvider
        from loom.providers.deepseek_provider import DeepSeekProvider

        # Try each provider in order
        if os.environ.get("GROQ_API_KEY"):
            return GroqProvider()
        if os.environ.get("NVIDIA_NIM_API_KEY"):
            return NVIDIANIMProvider()
        if os.environ.get("DEEPSEEK_API_KEY"):
            return DeepSeekProvider()
        return None
    except (ImportError, Exception) as e:
        logger.debug("Failed to load LLM provider: %s", e)
        return None


async def _fetch_url_content(url: str, max_chars: int = 20000) -> str:
    """Fetch URL content using research_fetch with fallback to raw HTTP."""
    try:
        # Try using Loom's smart fetch
        result = await research_fetch(
            url=url,
            mode="stealthy",
            auto_escalate=True,
            max_chars=max_chars,
        )
        # FIX: Properly handle dict result before checking for string
        if isinstance(result, dict):
            if "text" in result:
                return result.get("text", "")
            # If dict doesn't have text key, fall through to HTTP fallback
        elif isinstance(result, str):
            return result
    except Exception as e:
        logger.debug("research_fetch failed, trying raw HTTP: %s", e)

    # Fallback to raw HTTP fetch
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text[:max_chars]
    except Exception as e:
        logger.error("Failed to fetch URL %s: %s", url, e)
        return ""


async def _extract_with_llm(
    text: str,
    query: str,
    provider: LLMProvider | None = None,
    entity_types: list[str] | None = None,
) -> dict[str, Any]:
    """Extract structured data from text using LLM.

    Returns a dict with extracted entities, relationships, and summary.
    """
    if not provider:
        logger.warning("No LLM provider available for extraction")
        return {
            "entities": [],
            "relationships": [],
            "summary": "Extraction skipped: no LLM provider",
        }

    # Build extraction prompt
    prompt = _build_extraction_prompt(text, query, entity_types)

    try:
        messages = [{"role": "user", "content": prompt}]
        response = await provider.chat(
            messages,
            max_tokens=2000,
            temperature=0.3,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "knowledge_extraction",
                    "description": "Extracted knowledge graph",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "entities": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "type": {"type": "string"},
                                        "properties": {"type": "object"},
                                    },
                                },
                            },
                            "relationships": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "source": {"type": "string"},
                                        "target": {"type": "string"},
                                        "relation": {"type": "string"},
                                    },
                                },
                            },
                            "summary": {"type": "string"},
                        },
                        "required": ["entities", "relationships", "summary"],
                    },
                },
            },
        )

        # Parse JSON response with size limit (SECURITY: prevent unbounded responses)
        response_text = response.text
        if len(response_text) > 100_000:
            logger.error("LLM response too large: %d bytes", len(response_text))
            return {
                "entities": [],
                "relationships": [],
                "summary": "Extraction failed: response too large",
            }

        result = json.loads(response_text)
        return {
            "entities": result.get("entities", []),
            "relationships": result.get("relationships", []),
            "summary": result.get("summary", ""),
        }
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM JSON response: %s", e)
        return {
            "entities": [],
            "relationships": [],
            "summary": "Extraction failed: invalid response format",
        }
    except Exception as e:
        logger.error("LLM extraction failed: %s", e)
        return {
            "entities": [],
            "relationships": [],
            "summary": f"Extraction failed: {str(e)}",
        }


def _build_extraction_prompt(
    text: str, query: str, entity_types: list[str] | None = None
) -> str:
    """Build an extraction prompt for the LLM."""
    if not text:
        raise ValueError("text cannot be empty")
    if not query:
        raise ValueError("query cannot be empty")

    text_preview = text[:2000] if len(text) > 2000 else text

    entity_spec = ""
    if entity_types:
        # SECURITY: sanitize entity types to prevent prompt injection
        sanitized_types = [str(t).replace("\n", " ").replace("\r", "")[:100] for t in entity_types]
        entity_spec = f"Focus on these entity types: {', '.join(sanitized_types)}. "

    return f"""Extract a knowledge graph from the following text:

{entity_spec}

Query: {query}

Text:
{text_preview}

Return a JSON object with:
1. entities: List of {{name, type, properties}}
2. relationships: List of {{source, target, relation}}
3. summary: Brief overview of the extracted knowledge

Be concise and accurate. Only extract information explicitly present in the text."""


def _parse_scrapegraphai_config() -> dict[str, Any]:
    """Build ScrapeGraphAI config from environment and defaults."""
    config = {
        "verbose": False,
        "headless": True,
        "cache_enabled": True,
    }

    # Prefer GROQ (free tier)
    if os.environ.get("GROQ_API_KEY"):
        config["llm"] = {
            "api_key": os.environ["GROQ_API_KEY"],
            "model": "groq/llama-3.3-70b-versatile",
        }
    # Fallback to NVIDIA NIM
    elif os.environ.get("NVIDIA_NIM_API_KEY"):
        config["llm"] = {
            "api_key": os.environ["NVIDIA_NIM_API_KEY"],
            "model": "nvidia/llama-3.1-405b-instruct",
            "base_url": "https://integrate.api.nvidia.com/v1",
        }
    # Fallback to DeepSeek
    elif os.environ.get("DEEPSEEK_API_KEY"):
        config["llm"] = {
            "api_key": os.environ["DEEPSEEK_API_KEY"],
            "model": "deepseek-chat",
        }
    else:
        logger.warning("No LLM API key found for ScrapeGraphAI")

    return config


async def research_graph_scrape(
    url: str,
    query: str,
    model: str = "auto",
) -> dict[str, Any]:
    """DEPRECATED: Use research_graph() unified interface.

    Scrape a URL using LLM-powered graph extraction.

    Uses ScrapeGraphAI if available, otherwise falls back to Loom's LLM
    providers for structured data extraction from fetched content.

    Args:
        url: URL to scrape
        query: Query describing what structured data to extract
        model: LLM model selection ("auto", "groq", "nvidia", "deepseek", etc.)

    Returns:
        dict with keys:
            - url: The input URL
            - query: The extraction query
            - extracted_data: Extracted structured data (entities, relationships)
            - model_used: LLM model identifier
            - graph_nodes: List of extracted entities
            - graph_edges: List of extracted relationships
            - cost_usd: Estimated cost of LLM calls
            - extraction_method: "scrapegraphai" or "llm_fallback"
            - timestamp: ISO timestamp of extraction
    """
    try:
        validate_url(url)
        cache = get_cache()
        cache_key = f"graph_scrape_{url}_{query}"

        # Check cache
        cached = cache.get(cache_key)
        if cached:
            logger.debug("Found cached graph scrape result")
            return cached

        start_time = time.time()
        total_cost = 0.0
        extraction_method = "llm_fallback"
        model_used = "unknown"

        # Try ScrapeGraphAI if available
        if SCRAPEGRAPHAI_AVAILABLE:
            try:
                logger.debug("Attempting ScrapeGraphAI extraction")
                config = _parse_scrapegraphai_config()
                graph = SmartScraperGraph(prompt=query, source=url, config=config)
                # FIX: Wrap sync call in asyncio.to_thread to avoid blocking event loop
                sga_result = await asyncio.to_thread(graph.run)

                extraction_method = "scrapegraphai"
                model_used = config.get("llm", {}).get("model", "unknown")

                # Parse ScrapeGraphAI result
                if isinstance(sga_result, dict):
                    extracted_data = sga_result
                else:
                    extracted_data = {"raw_result": str(sga_result)}

                result = {
                    "url": url,
                    "query": query,
                    "extracted_data": extracted_data,
                    "model_used": model_used,
                    "graph_nodes": _extract_nodes(extracted_data),
                    "graph_edges": _extract_edges(extracted_data),
                    "cost_usd": 0.0,  # GROQ/NVIDIA NIM are free
                    "extraction_method": extraction_method,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }

                cache.put(cache_key, result)
                return result
            except Exception as e:
                logger.warning("ScrapeGraphAI extraction failed, falling back to LLM: %s", e)

        # Fallback: Fetch URL and use LLM extraction
        logger.debug("Using LLM fallback extraction")
        content = await _fetch_url_content(url)

        if not content:
            return {
                "url": url,
                "query": query,
                "extracted_data": {},
                "model_used": "none",
                "graph_nodes": [],
                "graph_edges": [],
                "cost_usd": 0.0,
                "extraction_method": "failed",
                "error": "Could not fetch URL content",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        # Get LLM provider
        provider = _get_llm_provider()
        if not provider:
            return {
                "url": url,
                "query": query,
                "extracted_data": {},
                "model_used": "none",
                "graph_nodes": [],
                "graph_edges": [],
                "cost_usd": 0.0,
                "extraction_method": "failed",
                "error": "No LLM provider configured",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        # FIX: Safely access provider.default_model with fallback
        model_used = getattr(provider, "default_model", "unknown")
        extraction_result = await _extract_with_llm(
            content, query, provider=provider, entity_types=None
        )

        result = {
            "url": url,
            "query": query,
            "extracted_data": extraction_result,
            "model_used": model_used,
            "graph_nodes": extraction_result.get("entities", []),
            "graph_edges": extraction_result.get("relationships", []),
            "cost_usd": total_cost,
            "extraction_method": "llm_fallback",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        cache.put(cache_key, result)
        return result
    except Exception as exc:
        return {"error": str(exc), "tool": "research_graph_scrape"}


async def research_knowledge_extract(
    text: str,
    entity_types: list[str] | None = None,
) -> dict[str, Any]:
    """Extract knowledge graph entities and relationships from text.

    Args:
        text: Text to analyze
        entity_types: Optional list of entity types to focus on
                     (e.g., ["person", "organization", "location"])

    Returns:
        dict with keys:
            - entities: List of extracted entities with properties
            - relationships: List of extracted relationships (source, target, relation)
            - graph_summary: Summary of the extracted knowledge graph
            - entity_count: Number of entities extracted
            - relationship_count: Number of relationships extracted
            - model_used: LLM model identifier
    """
    try:
        if not text:
            return {
                "entities": [],
                "relationships": [],
                "graph_summary": "No text provided",
                "entity_count": 0,
                "relationship_count": 0,
                "model_used": "none",
                "error": "text cannot be empty",
            }

        cache = get_cache()
        entity_types_key = sorted(entity_types or [])
        # FIX: Use SHA-256 instead of hash() to avoid collisions
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        types_hash = hashlib.sha256(",".join(entity_types_key).encode()).hexdigest()[:16]
        cache_key = f"knowledge_extract_{text_hash}_{types_hash}"

        # Check cache
        cached = cache.get(cache_key)
        if cached:
            logger.debug("Found cached knowledge extraction result")
            return cached

        # Get LLM provider
        provider = _get_llm_provider()
        if not provider:
            return {
                "entities": [],
                "relationships": [],
                "graph_summary": "Extraction failed: no LLM provider configured",
                "entity_count": 0,
                "relationship_count": 0,
                "model_used": "none",
                "error": "No LLM provider configured",
            }

        # Extract knowledge
        extraction = await _extract_with_llm(
            text, "Extract all entities and relationships", provider=provider, entity_types=entity_types
        )

        entities = extraction.get("entities", [])
        relationships = extraction.get("relationships", [])

        # FIX: Safely access provider.default_model with fallback
        model_used = getattr(provider, "default_model", "unknown")

        result = {
            "entities": entities,
            "relationships": relationships,
            "graph_summary": extraction.get("summary", ""),
            "entity_count": len(entities),
            "relationship_count": len(relationships),
            "model_used": model_used,
        }

        cache.put(cache_key, result)
        return result
    except Exception as exc:
        return {"error": str(exc), "tool": "research_knowledge_extract"}


async def research_multi_page_graph(
    urls: list[str],
    query: str,
) -> dict[str, Any]:
    """DEPRECATED: Use research_graph() unified interface.

    Scrape multiple pages and build a unified knowledge graph.

    Args:
        urls: List of URLs to scrape
        query: Extraction query for all pages

    Returns:
        dict with keys:
            - pages_processed: Number of successfully processed pages
            - pages_failed: Number of failed pages
            - unified_graph: Merged knowledge graph
            - entities_count: Total unique entities
            - relationships_count: Total unique relationships
            - page_results: List of per-page extraction results
            - total_cost_usd: Combined cost of all extractions
    """
    try:
        if not urls:
            return {
                "pages_processed": 0,
                "pages_failed": 0,
                "unified_graph": {"entities": [], "relationships": []},
                "entities_count": 0,
                "relationships_count": 0,
                "page_results": [],
                "total_cost_usd": 0.0,
                "error": "No URLs provided",
            }

        # Validate all URLs
        for url in urls:
            validate_url(url)

        logger.info("Starting multi-page graph scraping for %d URLs", len(urls))

        # Scrape all pages in parallel
        tasks = [research_graph_scrape(url, query) for url in urls]
        page_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        unified_entities: dict[str, dict[str, Any]] = {}
        unified_relationships: list[dict[str, Any]] = []
        pages_processed = 0
        pages_failed = 0
        failed_urls: list[str] = []
        total_cost = 0.0

        for i, result in enumerate(page_results):
            if isinstance(result, Exception):
                logger.error("Error scraping page %s: %s", urls[i], result)
                pages_failed += 1
                failed_urls.append(urls[i])
                continue

            pages_processed += 1
            total_cost += result.get("cost_usd", 0.0)

            # Merge entities (deduplicate by name)
            for entity in result.get("graph_nodes", []):
                entity_name = entity.get("name", "")
                if entity_name and entity_name not in unified_entities:
                    unified_entities[entity_name] = entity

            # Collect relationships
            unified_relationships.extend(result.get("graph_edges", []))

        # Deduplicate relationships
        unique_relationships = _deduplicate_relationships(unified_relationships)

        result = {
            "pages_processed": pages_processed,
            "pages_failed": pages_failed,
            "failed_urls": failed_urls,  # FIX: Include list of failed URLs for transparency
            "unified_graph": {
                "entities": list(unified_entities.values()),
                "relationships": unique_relationships,
            },
            "entities_count": len(unified_entities),
            "relationships_count": len(unique_relationships),
            "page_results": [r for r in page_results if not isinstance(r, Exception)],
            "total_cost_usd": total_cost,
        }

        return result
    except Exception as exc:
        return {"error": str(exc), "tool": "research_multi_page_graph"}


def _extract_nodes(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract entity nodes from ScrapeGraphAI result."""
    if isinstance(data, dict):
        # If data has entities key, use it
        if "entities" in data:
            return data["entities"]
        # Otherwise, try to build nodes from dict structure
        nodes = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                nodes.append({"name": key, "type": "data", "properties": {"value": value}})
        return nodes
    return []


def _extract_edges(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract relationship edges from ScrapeGraphAI result."""
    if isinstance(data, dict) and "relationships" in data:
        return data["relationships"]
    return []


def _deduplicate_relationships(
    relationships: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate relationships while preserving order."""
    seen = set()
    unique = []
    for rel in relationships:
        source = rel.get("source", "")
        target = rel.get("target", "")
        relation = rel.get("relation", "")
        key = (source, target, relation)
        if key not in seen:
            seen.add(key)
            unique.append(rel)
    return unique
