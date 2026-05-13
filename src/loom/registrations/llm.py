"""Registration module for llm tools."""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.llm")


def register_llm_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 2 llm tools."""
    from loom.registrations.tracking import record_success, record_failure

    try:
        from loom.tools.llm.ask_all_models import research_ask_all_models
        mcp.tool()(wrap_tool(research_ask_all_models))
        record_success("llm", "research_ask_all_models")
    except (ImportError, AttributeError) as e:
        log.debug("skip ask_all_models: %s", e)
        record_failure("llm", "ask_all_models", str(e))
    try:
        from loom.tools.llm.multi_llm import research_ask_all_llms
        mcp.tool()(wrap_tool(research_ask_all_llms))
        record_success("llm", "research_ask_all_llms")
    except (ImportError, AttributeError) as e:
        log.debug("skip multi_llm: %s", e)
        record_failure("llm", "multi_llm", str(e))
    log.info("registered llm tools count=2")

def register_compression_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 3 prompt compression tools."""
    from loom.registrations.tracking import record_success, record_failure

    try:
        from loom.tools.llm.prompt_compression import (
            research_compress_prompt,
            research_compression_stats,
            research_compression_reset,
        )
        mcp.tool()(wrap_tool(research_compress_prompt))
        record_success("compression", "research_compress_prompt")
        mcp.tool()(wrap_tool(research_compression_stats))
        record_success("compression", "research_compression_stats")
        mcp.tool()(wrap_tool(research_compression_reset))
        record_success("compression", "research_compression_reset")
        log.info("registered compression tools count=3")
    except (ImportError, AttributeError) as e:
        log.debug("skip compression tools: %s", e)
        record_failure("compression", "prompt_compression", str(e))
