"""research_gpt_researcher — Autonomous research using GPT Researcher library.

Provides multi-source research reports using the gpt-researcher framework
with automatic source gathering and synthesis.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
from typing import Any, TypedDict
from loom.error_responses import handle_tool_errors

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


class ResearchResult(TypedDict, total=False):
    """Typed result dict for research_gpt_researcher."""

    query: str
    report: str
    sources: list[dict[str, str]]
    total_sources: int
    report_type: str
    error: str
    library_installed: bool


def _create_error_response(
    query: str, error_msg: str, report_type: str = "research_report"
) -> ResearchResult:
    """Create a consistent error response dict."""
    return {
        "query": query,
        "error": error_msg,
        "report": "",
        "sources": [],
        "total_sources": 0,
        "report_type": report_type,
    }


@handle_tool_errors("research_gpt_researcher")
async def research_gpt_researcher(
    query: str,
    report_type: str = "research_report",
    max_sources: int = 10,
    include_tavily: bool = False,
) -> ResearchResult:
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
        - library_installed: Whether gpt-researcher is available (optional)
    """
    # Input validation
    if not query or not isinstance(query, str):
        return _create_error_response(query, "query must be a non-empty string", report_type)

    query = query.strip()
    if len(query) < MIN_QUERY_LEN or len(query) > MAX_QUERY_LEN:
        return _create_error_response(
            query,
            f"query length must be {MIN_QUERY_LEN}-{MAX_QUERY_LEN} chars",
            report_type,
        )

    # Validate report type
    valid_types = ["research_report", "summary", "outline", "resources"]
    if report_type not in valid_types:
        report_type = "research_report"

    # Validate max_sources
    if not isinstance(max_sources, int) or max_sources < 1 or max_sources > MAX_SOURCES:
        max_sources = 10

    # Check if library is installed
    if not _HAS_GPT_RESEARCHER:
        result = _create_error_response(
            query,
            "gpt-researcher library not installed. Install with: pip install gpt-researcher",
            report_type,
        )
        result["library_installed"] = False
        return result

    try:
        logger.info(
            "gpt_researcher_start query=%s report_type=%s max_sources=%d",
            query,
            report_type,
            max_sources,
        )

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
        except TypeError as e:
            # Older versions might not support all parameters
            logger.debug("GPTResearcher init with full params failed, trying minimal: %s", e)
            researcher = GPTResearcher(query=query)

        # Run research (check if methods are async)
        try:
            if inspect.iscoroutinefunction(researcher.conduct_research):
                await researcher.conduct_research()
                report = await researcher.write_report()
            else:
                researcher.conduct_research()
                report = researcher.write_report()
        except Exception as e:
            logger.warning("gpt_researcher_execution_failed: %s", e, exc_info=True)
            return _create_error_response(
                query,
                f"gpt-researcher execution error: {str(e)}",
                report_type,
            )

        # Validate report is a string
        if not isinstance(report, str):
            report = str(report) if report else ""

        # Extract sources
        sources = []
        try:
            # Try to access sources attribute
            if hasattr(researcher, "sources"):
                raw_sources = researcher.sources
                if isinstance(raw_sources, list):
                    # Limit to max_sources
                    raw_sources_limited = raw_sources[:max_sources]
                    for src in raw_sources_limited:
                        if isinstance(src, dict):
                            sources.append({
                                "url": src.get("url", ""),
                                "title": src.get("title", ""),
                                "content": str(src.get("content", ""))[:1000],  # First 1K chars
                            })
                        elif hasattr(src, "url"):
                            sources.append({
                                "url": str(getattr(src, "url", "")),
                                "title": str(getattr(src, "title", "")),
                                "content": str(getattr(src, "content", ""))[:1000],
                            })
        except Exception as e:
            logger.warning("gpt_researcher_sources_extraction_failed: %s", e, exc_info=True)

        # Limit report size
        if isinstance(report, str) and len(report) > MAX_REPORT_CHARS:
            report = report[:MAX_REPORT_CHARS] + "\n... [report truncated]"

        logger.info(
            "gpt_researcher_complete query=%s report_type=%s sources=%d",
            query,
            report_type,
            len(sources),
        )

        result: ResearchResult = {
            "query": query,
            "report": report or "",
            "sources": sources,
            "total_sources": len(sources),
            "report_type": report_type,
            "library_installed": True,
        }
        return result

    except Exception as e:
        logger.error("gpt_researcher_failed query=%s: %s", query, e, exc_info=True)
        return _create_error_response(query, f"gpt-researcher error: {str(e)}", report_type)
