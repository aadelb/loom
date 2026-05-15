"""Registration module for reframe tools."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.reframe")


def register_reframe_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 11 reframe tools."""
    from loom.registrations.tracking import record_success, record_failure

    try:
        from loom.tools.llm.prompt_analyzer import research_prompt_analyze
        mcp.tool()(wrap_tool(research_prompt_analyze))
        record_success("reframe", "research_prompt_analyze")
    except (ImportError, AttributeError) as e:
        log.debug("skip prompt_analyzer: %s", e)
        record_failure("reframe", "prompt_analyzer", str(e))
    try:
        from loom.tools.llm.prompt_reframe import research_prompt_reframe, research_auto_reframe, research_refusal_detector, research_stack_reframe, research_crescendo_chain, research_model_vulnerability_profile, research_format_smuggle, research_fingerprint_model, research_adaptive_reframe
        mcp.tool()(wrap_tool(research_prompt_reframe))
        record_success("reframe", "research_prompt_reframe")
        mcp.tool()(wrap_tool(research_auto_reframe))
        record_success("reframe", "research_auto_reframe")
        mcp.tool()(wrap_tool(research_refusal_detector))
        record_success("reframe", "research_refusal_detector")
        mcp.tool()(wrap_tool(research_stack_reframe))
        record_success("reframe", "research_stack_reframe")
        mcp.tool()(wrap_tool(research_crescendo_chain))
        record_success("reframe", "research_crescendo_chain")
        mcp.tool()(wrap_tool(research_model_vulnerability_profile))
        record_success("reframe", "research_model_vulnerability_profile")
        mcp.tool()(wrap_tool(research_format_smuggle))
        record_success("reframe", "research_format_smuggle")
        mcp.tool()(wrap_tool(research_fingerprint_model))
        record_success("reframe", "research_fingerprint_model")
        mcp.tool()(wrap_tool(research_adaptive_reframe))
        record_success("reframe", "research_adaptive_reframe")
    except (ImportError, AttributeError) as e:
        log.debug("skip prompt_reframe: %s", e)
        record_failure("reframe", "prompt_reframe", str(e))
    try:
        from loom.tools.research.psycholinguistic import research_psycholinguistic
        mcp.tool()(wrap_tool(research_psycholinguistic))
        record_success("reframe", "research_psycholinguistic")
    except (ImportError, AttributeError) as e:
        log.debug("skip psycholinguistic: %s", e)
        record_failure("reframe", "psycholinguistic", str(e))
    log.info("registered reframe tools count=11")
