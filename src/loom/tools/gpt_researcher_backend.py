"""research_gpt_researcher — Autonomous research using GPT Researcher library.

Provides multi-source research reports using the gpt-researcher framework
with automatic source gathering and synthesis.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

try:
    from gpt_researcher import GPTResearcher

    _HAS_GPT_RESEARCHER = True
except ImportError:
    _HAS_GPT_RESEARCHER = False

logger = logging.getLogger("loom.tools.gpt_researcher_backend")

# Constraints
MIN_QUERY_LEN = 3
MAX_QUERY_LEN = 500
MAX_SOURCES = 50
MAX_REPORT_CHARS = 100000


async def research_gpt_researcher(
    query: str,
    report_type: str = "research_report",
    max_sources: int = 10,
    include_tavily: bool = False,
) -> dict[str, Any]:
    """Run autonomous research and generate a report.

    Uses gpt-researcher library to conduct multi-source research with
    automatic report generation and source citation.

    Args:
        query: Research query or topic
        report_type: Report format: 'research_report', 'summary', 'outline',
                    'resources' (default: 'research_report')
        max_sources: Maximum number of sources to use (1-50, default: 10)
        include_tavily: Use Tavily search alongside default providers (default: False)

    Returns:
        Dict with keys:
        - query: Input query
        - report: Generated research report (or error message)
        - sources: List of source dicts with {url, title, content}
        - total_sources: Total number of sources used
        - report_type: Report format used
        - error: Error message if operation failed (optional)
    """
    # Input validation
    if not query or not isinstance(query, str):
        return {
            "query": query,
            "error": "query must be a non-empty string",
            "report": "",
            "sources": [],
            "total_sources": 0,
            "report_type": report_type,
        }

    query = query.strip()
    if len(query) < MIN_QUERY_LEN or len(query) > MAX_QUERY_LEN:
        return {
            "query": query,
            "error": f"query length must be {MIN_QUERY_LEN}-{MAX_QUERY_LEN} chars",
            "report": "",
            "sources": [],
            "total_sources": 0,
            "report_type": report_type,
        }

    # Validate report type
    valid_types = ["research_report", "summary", "outline", "resources"]
    if report_type not in valid_types:
        report_type = "research_report"

    # Validate max_sources
    if not isinstance(max_sources, int) or max_sources < 1 or max_sources > MAX_SOURCES:
        max_sources = 10

    # Check if library is installed
    if not _HAS_GPT_RESEARCHER:
        return {
            "query": query,
            "error": "gpt-researcher library not installed. Install with: pip install gpt-researcher",
            "report": "",
            "sources": [],
            "total_sources": 0,
            "report_type": report_type,
            "library_installed": False,
        }

    try:
        logger.info("gpt_researcher_start query=%s report_type=%s max_sources=%d", query, report_type, max_sources)

        # Initialize researcher
        # Note: GPT Researcher requires LLM API keys (OpenAI, etc.)
        try:
            researcher = GPTResearcher(
                query=query,
                report_type=report_type,
                max_sources=max_sources,
                config_path=None,  # Use default config or env-based config
                verbose=False,
            )
        except TypeError:
            # Older versions might not support all parameters
            researcher = GPTResearcher(query=query)

        # Run research (this is async in newer versions)
        try:
            # Try async/await pattern
            await researcher.conduct_research()
            report = await researcher.write_report()
        except (AttributeError, TypeError):
            # Fallback for synchronous or different API
            try:
                researcher.conduct_research()
                report = researcher.write_report()
            except Exception as e:
                logger.warning("gpt_researcher_execution_failed: %s", e)
                return {
                    "query": query,
                    "error": f"gpt-researcher execution error: {str(e)}",
                    "report": "",
                    "sources": [],
                    "total_sources": 0,
                    "report_type": report_type,
                }

        # Extract sources
        sources = []
        try:
            # Try to access sources attribute
            if hasattr(researcher, "sources"):
                raw_sources = researcher.sources
                if isinstance(raw_sources, list):
                    for src in raw_sources[:max_sources]:
                        if isinstance(src, dict):
                            sources.append({
                                "url": src.get("url", ""),
                                "title": src.get("title", ""),
                                "content": src.get("content", "")[:1000],  # First 1K chars
                            })
                        elif hasattr(src, "url"):
                            sources.append({
                                "url": getattr(src, "url", ""),
                                "title": getattr(src, "title", ""),
                                "content": getattr(src, "content", "")[:1000],
                            })
        except Exception as e:
            logger.warning("gpt_researcher_sources_extraction_failed: %s", e)

        # Limit report size
        if isinstance(report, str) and len(report) > MAX_REPORT_CHARS:
            report = report[:MAX_REPORT_CHARS] + "\n... [report truncated]"

        logger.info(
            "gpt_researcher_complete query=%s report_type=%s sources=%d",
            query,
            report_type,
            len(sources),
        )

        return {
            "query": query,
            "report": report or "",
            "sources": sources,
            "total_sources": len(sources),
            "report_type": report_type,
            "library_installed": True,
        }

    except Exception as e:
        logger.error("gpt_researcher_failed query=%s: %s", query, e)
        return {
            "query": query,
            "error": f"gpt-researcher error: {str(e)}",
            "report": "",
            "sources": [],
            "total_sources": 0,
            "report_type": report_type,
        }
