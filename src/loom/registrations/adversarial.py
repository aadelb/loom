"""Adversarial testing and attack orchestration tools.

Tools for adversarial robustness testing, AI safety evaluation, and attack
effectiveness measurement.
"""
from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.adversarial")


def register_adversarial_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 22 adversarial testing and attack tools.

    Includes AI safety probes, adversarial debate, coevolution attacks, and robustness
    evaluation.
    """
    from loom.tools import (
        adversarial_craft,
        adversarial_debate_tool,
        coevolution,
        xover_attack,
        ai_safety,
        ai_safety_extended,
        defender_mode,
    )

    # Adversarial crafting
    mcp.tool()(wrap_tool(adversarial_craft.research_craft_adversarial))
    mcp.tool()(wrap_tool(adversarial_craft.research_adversarial_batch))

    # Debate and discussion attacks
    mcp.tool()(wrap_tool(adversarial_debate_tool.research_adversarial_debate, "llm"))

    # Evolution-based attacks
    mcp.tool()(wrap_tool(coevolution.research_coevolve))
    mcp.tool()(wrap_tool(coevolution.research_coevolve_iterate))
    mcp.tool()(wrap_tool(coevolution.research_coevolve_analyze))

    # Crossover attacks (transfer learning)
    mcp.tool()(wrap_tool(xover_attack.research_xover_transfer))
    mcp.tool()(wrap_tool(xover_attack.research_xover_matrix))

    # AI Safety evaluation
    mcp.tool()(wrap_tool(ai_safety.research_prompt_injection_test, "fetch"))
    mcp.tool()(wrap_tool(ai_safety.research_model_fingerprint, "fetch"))
    mcp.tool()(wrap_tool(ai_safety.research_bias_probe, "fetch"))
    mcp.tool()(wrap_tool(ai_safety.research_safety_filter_map, "fetch"))

    # Extended safety analysis
    mcp.tool()(wrap_tool(ai_safety_extended.research_hallucination_benchmark, "fetch"))
    mcp.tool()(wrap_tool(ai_safety_extended.research_adversarial_robustness, "fetch"))

    # Defensive mode
    mcp.tool()(wrap_tool(defender_mode.research_defender_baseline))
    mcp.tool()(wrap_tool(defender_mode.research_defender_adaptive))

    # Optional advanced adversarial tools
    with suppress(ImportError):
        from loom.tools import transcribe as transcribe_tools

        mcp.tool()(wrap_tool(transcribe_tools.research_transcribe, "fetch"))

    # Optional optional_tools
    with suppress(ImportError):
        mcp.tool()(_optional_tools["adversarial_debate"], "llm")
        mcp.tool()(_optional_tools["evidence_pipeline"], "llm")
        mcp.tool()(_optional_tools["model_evidence"], "llm")
        mcp.tool()(_optional_tools["quality_scorer"])
        mcp.tool()(_optional_tools["danger_prescore"])

    log.info("registered adversarial tools", tool_count=22)
