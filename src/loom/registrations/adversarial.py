"""Registration module for adversarial tools."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.adversarial")


def register_adversarial_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 20 adversarial tools."""
    from loom.registrations.tracking import record_success, record_failure

    try:
        from loom.tools.adversarial.adversarial_craft import research_craft_adversarial, research_adversarial_batch
        mcp.tool()(wrap_tool(research_craft_adversarial))
        record_success("adversarial", "research_craft_adversarial")
        mcp.tool()(wrap_tool(research_adversarial_batch))
        record_success("adversarial", "research_adversarial_batch")
    except (ImportError, AttributeError) as e:
        log.debug("skip adversarial_craft: %s", e)
        record_failure("adversarial", "adversarial_craft", str(e))
    try:
        from loom.tools.adversarial.adversarial_debate_tool import research_adversarial_debate
        mcp.tool()(wrap_tool(research_adversarial_debate))
        record_success("adversarial", "research_adversarial_debate")
    except (ImportError, AttributeError) as e:
        log.debug("skip adversarial_debate_tool: %s", e)
        record_failure("adversarial", "adversarial_debate_tool", str(e))
    try:
        from loom.tools.security.ai_safety import research_prompt_injection_test, research_model_fingerprint, research_bias_probe, research_safety_filter_map
        mcp.tool()(wrap_tool(research_prompt_injection_test))
        record_success("adversarial", "research_prompt_injection_test")
        mcp.tool()(wrap_tool(research_model_fingerprint))
        record_success("adversarial", "research_model_fingerprint")
        mcp.tool()(wrap_tool(research_bias_probe))
        record_success("adversarial", "research_bias_probe")
        mcp.tool()(wrap_tool(research_safety_filter_map))
        record_success("adversarial", "research_safety_filter_map")
    except (ImportError, AttributeError) as e:
        log.debug("skip ai_safety: %s", e)
        record_failure("adversarial", "ai_safety", str(e))
    try:
        from loom.tools.security.ai_safety_extended import research_hallucination_benchmark, research_adversarial_robustness
        mcp.tool()(wrap_tool(research_hallucination_benchmark))
        record_success("adversarial", "research_hallucination_benchmark")
        mcp.tool()(wrap_tool(research_adversarial_robustness))
        record_success("adversarial", "research_adversarial_robustness")
    except (ImportError, AttributeError) as e:
        log.debug("skip ai_safety_extended: %s", e)
        record_failure("adversarial", "ai_safety_extended", str(e))
    try:
        from loom.tools.adversarial.coevolution import research_coevolve
        mcp.tool()(wrap_tool(research_coevolve))
        record_success("adversarial", "research_coevolve")
    except (ImportError, AttributeError) as e:
        log.debug("skip coevolution: %s", e)
        record_failure("adversarial", "coevolution", str(e))
    try:
        from loom.tools.security.defender_mode import research_defend_test, research_harden_prompt
        mcp.tool()(wrap_tool(research_defend_test))
        record_success("adversarial", "research_defend_test")
        mcp.tool()(wrap_tool(research_harden_prompt))
        record_success("adversarial", "research_harden_prompt")
    except (ImportError, AttributeError) as e:
        log.debug("skip defender_mode: %s", e)
        record_failure("adversarial", "defender_mode", str(e))
    try:
        from loom.tools.research.evidence_fusion import research_fuse_evidence, research_authority_stack
        mcp.tool()(wrap_tool(research_fuse_evidence))
        record_success("adversarial", "research_fuse_evidence")
        mcp.tool()(wrap_tool(research_authority_stack))
        record_success("adversarial", "research_authority_stack")
    except (ImportError, AttributeError) as e:
        log.debug("skip evidence_fusion: %s", e)
        record_failure("adversarial", "evidence_fusion", str(e))
    try:
        from loom.tools.security.exploit_db import research_exploit_register, research_exploit_search, research_exploit_stats
        mcp.tool()(wrap_tool(research_exploit_register))
        record_success("adversarial", "research_exploit_register")
        mcp.tool()(wrap_tool(research_exploit_search))
        record_success("adversarial", "research_exploit_search")
        mcp.tool()(wrap_tool(research_exploit_stats))
        record_success("adversarial", "research_exploit_stats")
    except (ImportError, AttributeError) as e:
        log.debug("skip exploit_db: %s", e)
        record_failure("adversarial", "exploit_db", str(e))
    try:
        from loom.tools.adversarial.swarm_attack import research_swarm_attack
        mcp.tool()(wrap_tool(research_swarm_attack))
        record_success("adversarial", "research_swarm_attack")
    except (ImportError, AttributeError) as e:
        log.debug("skip swarm_attack: %s", e)
        record_failure("adversarial", "swarm_attack", str(e))
    try:
        from loom.tools.adversarial.thinking_injection import research_thinking_inject, research_reasoning_exploit
        mcp.tool()(wrap_tool(research_thinking_inject))
        record_success("adversarial", "research_thinking_inject")
        mcp.tool()(wrap_tool(research_reasoning_exploit))
        record_success("adversarial", "research_reasoning_exploit")
    except (ImportError, AttributeError) as e:
        log.debug("skip thinking_injection: %s", e)
        record_failure("adversarial", "thinking_injection", str(e))
    log.info("registered adversarial tools count=20")
