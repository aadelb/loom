"""Registration module for adversarial tools."""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.adversarial")


def register_adversarial_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 20 adversarial tools."""
    try:
        from loom.tools.adversarial_craft import research_craft_adversarial, research_adversarial_batch
        mcp.tool()(wrap_tool(research_craft_adversarial))
        mcp.tool()(wrap_tool(research_adversarial_batch))
    except (ImportError, AttributeError) as e:
        log.debug("skip adversarial_craft: %s", e)
    try:
        from loom.tools.adversarial_debate_tool import research_adversarial_debate
        mcp.tool()(wrap_tool(research_adversarial_debate))
    except (ImportError, AttributeError) as e:
        log.debug("skip adversarial_debate_tool: %s", e)
    try:
        from loom.tools.ai_safety import research_prompt_injection_test, research_model_fingerprint, research_bias_probe, research_safety_filter_map
        mcp.tool()(wrap_tool(research_prompt_injection_test))
        mcp.tool()(wrap_tool(research_model_fingerprint))
        mcp.tool()(wrap_tool(research_bias_probe))
        mcp.tool()(wrap_tool(research_safety_filter_map))
    except (ImportError, AttributeError) as e:
        log.debug("skip ai_safety: %s", e)
    try:
        from loom.tools.ai_safety_extended import research_hallucination_benchmark, research_adversarial_robustness
        mcp.tool()(wrap_tool(research_hallucination_benchmark))
        mcp.tool()(wrap_tool(research_adversarial_robustness))
    except (ImportError, AttributeError) as e:
        log.debug("skip ai_safety_extended: %s", e)
    try:
        from loom.tools.coevolution import research_coevolve
        mcp.tool()(wrap_tool(research_coevolve))
    except (ImportError, AttributeError) as e:
        log.debug("skip coevolution: %s", e)
    try:
        from loom.tools.defender_mode import research_defend_test, research_harden_prompt
        mcp.tool()(wrap_tool(research_defend_test))
        mcp.tool()(wrap_tool(research_harden_prompt))
    except (ImportError, AttributeError) as e:
        log.debug("skip defender_mode: %s", e)
    try:
        from loom.tools.evidence_fusion import research_fuse_evidence, research_authority_stack
        mcp.tool()(wrap_tool(research_fuse_evidence))
        mcp.tool()(wrap_tool(research_authority_stack))
    except (ImportError, AttributeError) as e:
        log.debug("skip evidence_fusion: %s", e)
    try:
        from loom.tools.exploit_db import research_exploit_register, research_exploit_search, research_exploit_stats
        mcp.tool()(wrap_tool(research_exploit_register))
        mcp.tool()(wrap_tool(research_exploit_search))
        mcp.tool()(wrap_tool(research_exploit_stats))
    except (ImportError, AttributeError) as e:
        log.debug("skip exploit_db: %s", e)
    try:
        from loom.tools.swarm_attack import research_swarm_attack
        mcp.tool()(wrap_tool(research_swarm_attack))
    except (ImportError, AttributeError) as e:
        log.debug("skip swarm_attack: %s", e)
    try:
        from loom.tools.thinking_injection import research_thinking_inject, research_reasoning_exploit
        mcp.tool()(wrap_tool(research_thinking_inject))
        mcp.tool()(wrap_tool(research_reasoning_exploit))
    except (ImportError, AttributeError) as e:
        log.debug("skip thinking_injection: %s", e)
    log.info("registered adversarial tools count=20")
