"""LOOM BRAIN — Cognitive orchestration layer for 880+ MCP research tools.

5-layer architecture: Perception → Memory → Reasoning → Action → Reflection.
Inspired by Gorilla LLM, ToolBench, DSPy, Semantic Kernel, and HuggingGPT.
"""

from loom.brain.core import research_smart_call
from loom.brain.types import QualityMode, ToolMeta, SmartCallResult

__all__ = ["research_smart_call", "QualityMode", "ToolMeta", "SmartCallResult"]
