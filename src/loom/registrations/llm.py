"""Registration module for llm tools."""
from __future__ import annotations

import logging
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

    try:
        from loom.tools.llm.augmented_generate import research_augmented_generate
        mcp.tool()(wrap_tool(research_augmented_generate))
        record_success("llm", "research_augmented_generate")
    except (ImportError, AttributeError) as e:
        log.debug("skip augmented_generate: %s", e)
        record_failure("llm", "augmented_generate", str(e))

    try:
        from loom.tools.llm.agent_loop import research_agent_loop
        mcp.tool()(wrap_tool(research_agent_loop))
        record_success("llm", "research_agent_loop")
    except (ImportError, AttributeError) as e:
        log.debug("skip agent_loop: %s", e)
        record_failure("llm", "agent_loop", str(e))

    try:
        from loom.tools.llm.reframe_with_scoring import research_reframe_until_hcs
        mcp.tool()(wrap_tool(research_reframe_until_hcs))
        record_success("llm", "research_reframe_until_hcs")
    except (ImportError, AttributeError) as e:
        log.debug("skip reframe_with_scoring: %s", e)
        record_failure("llm", "reframe_with_scoring", str(e))

    try:
        from loom.tools.llm.max_score_engine import research_max_score
        mcp.tool()(wrap_tool(research_max_score))
        record_success("llm", "research_max_score")
    except (ImportError, AttributeError) as e:
        log.debug("skip max_score_engine: %s", e)
        record_failure("llm", "max_score_engine", str(e))

    try:
        from loom.tools.llm.adversarial_orchestrator import research_adversarial_orchestrate
        mcp.tool()(wrap_tool(research_adversarial_orchestrate))
        record_success("llm", "research_adversarial_orchestrate")
    except (ImportError, AttributeError) as e:
        log.debug("skip adversarial_orchestrator: %s", e)
        record_failure("llm", "adversarial_orchestrator", str(e))

    # Local techniques (30 creative methods)
    try:
        from loom.tools.llm.local_techniques import (
            research_strip_hedging,
            research_innocent_decompose,
            research_conversational_drift,
            research_meta_prompt,
            research_genetic_evolve,
        )
        for func in [research_strip_hedging, research_innocent_decompose,
                     research_conversational_drift, research_meta_prompt,
                     research_genetic_evolve]:
            mcp.tool()(wrap_tool(func))
            record_success("llm", func.__name__)
    except (ImportError, AttributeError) as e:
        log.debug("skip local_techniques: %s", e)
        record_failure("llm", "local_techniques", str(e))
