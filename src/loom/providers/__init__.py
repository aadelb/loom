"""LLM and search provider implementations for Loom."""

from loom.providers.anthropic_provider import AnthropicProvider
from loom.providers.base import LLMProvider, LLMResponse, _estimate_cost
from loom.providers.deepseek_provider import DeepSeekProvider
from loom.providers.gemini_provider import GeminiProvider
from loom.providers.groq_provider import GroqProvider
from loom.providers.moonshot_provider import MoonshotProvider
from loom.providers.nvidia_nim import NvidiaNimProvider
from loom.providers.openai_provider import OpenAIProvider
from loom.providers.ollama_provider import OllamaProvider
from loom.providers.vllm_local import VllmLocalProvider

__all__ = [
    "AnthropicProvider",
    "DeepSeekProvider",
    "GeminiProvider",
    "GroqProvider",
    "LLMProvider",
    "LLMResponse",
    "MoonshotProvider",
    "NvidiaNimProvider",
    "OllamaProvider",
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
    "hn_reddit": "search_hackernews",
    "newsapi_search": "search_newsapi_news",
    "coindesk_search": "search_coindesk_news",
    "binance_data": "search_binance",
    "investing_data": "search_investing",
    "coinmarketcap": "search_coinmarketcap",
    "ahmia_search": "search_ahmia",
    "darksearch_search": "search_darksearch",
    "ummro_rag": "search_ummro_rag",
    "youtube_transcripts": "fetch_youtube_transcript",
    "trafilatura_extract": "extract_with_trafilatura",
}
for _mod_name, _func_name in _search_providers.items():
    try:
        _mod = __import__(f"loom.providers.{_mod_name}", fromlist=[_func_name])
        globals()[_func_name] = getattr(_mod, _func_name)
        __all__.append(_func_name)
    except (ImportError, AttributeError):
        pass
