"""LLM and language model tools — multi-model querying, summarization, knowledge graph.

Tools for interacting with language models and knowledge extraction.
"""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.llm")


def register_llm_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 8 LLM and language model tools.

    Includes multi-search, knowledge graph, fact checking, and report generation.
    """
    from loom.tools import (
        multi_search,
        arxiv_pipeline,
        report_generator,
        knowledge_graph,
        fact_checker,
    )

    # Core LLM and knowledge tools
    mcp.tool()(wrap_tool(multi_search.research_multi_search, "search"))
    mcp.tool()(wrap_tool(arxiv_pipeline.research_arxiv_ingest, "search"))
    mcp.tool()(wrap_tool(arxiv_pipeline.research_arxiv_extract_techniques, "search"))
    mcp.tool()(wrap_tool(report_generator.research_generate_report, "search"))
    mcp.tool()(wrap_tool(knowledge_graph.research_knowledge_graph))
    mcp.tool()(wrap_tool(fact_checker.research_fact_check, "search"))

    # Optional LLM providers
    with suppress(ImportError):
        from loom.tools import enrich as enrich_tools

        mcp.tool()(wrap_tool(enrich_tools.research_detect_language))

    with suppress(ImportError):
        from loom.providers import youtube_transcripts as yt_tools

        mcp.tool()(wrap_tool(yt_tools.fetch_youtube_transcript, "fetch"))

    log.info("registered llm tools count=8")
