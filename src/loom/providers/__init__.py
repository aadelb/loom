"""LLM and search provider implementations for Loom."""

from loom.providers.anthropic_provider import AnthropicProvider
from loom.providers.base import LLMProvider, LLMResponse, _estimate_cost
from loom.providers.nvidia_nim import NvidiaNimProvider
from loom.providers.openai_provider import OpenAIProvider
from loom.providers.vllm_local import VllmLocalProvider

__all__ = [
    "AnthropicProvider",
    "LLMProvider",
    "LLMResponse",
    "NvidiaNimProvider",
    "OpenAIProvider",
    "VllmLocalProvider",
    "_estimate_cost",
]

# Search providers — optional, may fail if SDKs not installed
for _name in ("exa", "tavily", "firecrawl", "brave"):
    try:
        _mod = __import__(f"loom.providers.{_name}", fromlist=[f"search_{_name}"])
        globals()[f"search_{_name}"] = getattr(_mod, f"search_{_name}")
        __all__.append(f"search_{_name}")
    except (ImportError, AttributeError):
        pass
