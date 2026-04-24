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
_search_providers = {
    "exa": "search_exa",
    "tavily": "search_tavily",
    "firecrawl": "search_firecrawl",
    "brave": "search_brave",
    "ddgs": "search_ddgs",
    "arxiv_search": "search_arxiv",
    "wikipedia_search": "search_wikipedia",
}
for _mod_name, _func_name in _search_providers.items():
    try:
        _mod = __import__(f"loom.providers.{_mod_name}", fromlist=[_func_name])
        globals()[_func_name] = getattr(_mod, _func_name)
        __all__.append(_func_name)
    except (ImportError, AttributeError):
        pass
