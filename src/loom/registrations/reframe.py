"""Prompt reframing and manipulation tools — jailbreak strategies, format exploits, etc.

Tools for crafting, reframing, and analyzing prompts for adversarial testing.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server import FastMCP

log = logging.getLogger("loom.registrations.reframe")


def register_reframe_tools(mcp: "FastMCP", wrap_tool) -> None:
    """Register 27 prompt reframing and manipulation tools.

    Includes jailbreak strategies, prompt engineering, format exploits, and psycholinguistic
    attacks.
    """
    from loom.tools import (
        prompt_reframe,
        prompt_analyzer,
        thinking_injection,
        swarm_attack,
        ensemble_attack,
        multilang_attack,
        cultural_attacks,
        synth_echo,
        superposition_prompt,
        geodesic_forcing,
        psycholinguistic,
        holographic_payload,
        strange_attractors,
        memetic_simulator,
        neuromorphic,
    )

    # Core reframing strategies
    mcp.tool()(wrap_tool(prompt_reframe.research_reframe_prompt))
    mcp.tool()(wrap_tool(prompt_analyzer.research_analyze_prompt))
    mcp.tool()(wrap_tool(prompt_analyzer.research_prompt_suggest_variations))

    # Injection and evasion
    mcp.tool()(wrap_tool(thinking_injection.research_inject_thinking))
    mcp.tool()(wrap_tool(thinking_injection.research_inject_instructions))

    # Swarm and ensemble attacks
    mcp.tool()(wrap_tool(swarm_attack.research_swarm_attack))
    mcp.tool()(wrap_tool(ensemble_attack.research_ensemble_vote))

    # Multilingual attacks
    mcp.tool()(wrap_tool(multilang_attack.research_multilang_inject))
    mcp.tool()(wrap_tool(cultural_attacks.research_cultural_attack))

    # Advanced techniques
    mcp.tool()(wrap_tool(synth_echo.research_synthesize_echo))
    mcp.tool()(wrap_tool(synth_echo.research_confirm_attack))
    mcp.tool()(wrap_tool(superposition_prompt.research_superposition_attack))
    mcp.tool()(wrap_tool(geodesic_forcing.research_geodesic_path))
    mcp.tool()(wrap_tool(psycholinguistic.research_psycholinguistic_inject))
    mcp.tool()(wrap_tool(holographic_payload.research_holographic_encode))
    mcp.tool()(wrap_tool(strange_attractors.research_attractor_trap))
    mcp.tool()(wrap_tool(memetic_simulator.research_memetic_inject))
    mcp.tool()(wrap_tool(neuromorphic.research_neural_pathway_inject))

    # Additional reframing
    mcp.tool()(wrap_tool(prompt_reframe.research_reframe_refusal))
    mcp.tool()(wrap_tool(prompt_reframe.research_reframe_direct))
    mcp.tool()(wrap_tool(prompt_reframe.research_reframe_roleplay))
    mcp.tool()(wrap_tool(prompt_analyzer.research_detect_refusal_risk))

    log.info("registered reframe tools", tool_count=27)
