"""Multi-LLM query tool — send a prompt to ALL available LLM providers simultaneously."""

from __future__ import annotations
try:
    from loom.text_utils import truncate
except ImportError:
    def truncate(text, max_chars=500, *, suffix="..."):
        if len(text) <= max_chars: return text
        return text[:max_chars - len(suffix)] + suffix



import asyncio
import contextlib
import logging
import time
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.multi_llm")


@handle_tool_errors("research_ask_all_llms")
async def research_ask_all_llms(
    prompt: str,
    max_tokens: int = 500,
    include_reframe: bool = False,
) -> dict[str, Any]:
    """Send a prompt to ALL available LLM providers and compare responses.

    Queries every configured LLM provider (Groq, NVIDIA NIM, DeepSeek,
    Gemini, Moonshot, OpenAI, Anthropic) in parallel and returns all
    responses for comparison.

    If include_reframe=True, also tries reframed versions of the prompt
    against providers that refused the original.

    Args:
        prompt: the prompt to send to all LLMs
        max_tokens: max tokens per response
        include_reframe: if True, auto-reframe refused prompts and retry

    Returns:
        Dict with ``prompt``, ``responses`` (list per provider),
        ``providers_queried``, ``providers_responded``,
        ``providers_refused``, ``fastest_provider``, and
        ``reframe_results`` (if include_reframe=True).
    """
    from loom.providers.base import LLMProvider

    providers_available: list[tuple[str, Any]] = []

    provider_modules = [
        ("groq", "loom.providers.groq_provider"),
        ("nvidia", "loom.providers.nvidia_nim"),
        ("deepseek", "loom.providers.deepseek_provider"),
        ("gemini", "loom.providers.gemini_provider"),
        ("moonshot", "loom.providers.moonshot_provider"),
        ("openai", "loom.providers.openai_provider"),
        ("anthropic", "loom.providers.anthropic_provider"),
    ]

    for name, module_path in provider_modules:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            provider_class = None
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, LLMProvider)
                    and attr is not LLMProvider
                ):
                    provider_class = attr
                    break
            if provider_class:
                instance = provider_class()
                is_avail = instance.available()
                if asyncio.iscoroutine(is_avail):
                    is_avail = await is_avail
                if is_avail:
                    providers_available.append((name, instance))
        except Exception as exc:
            logger.debug("Provider %s not available: %s", name, exc)

    if not providers_available:
        return {
            "prompt": prompt,
            "error": "No LLM providers configured. Set API keys.",
            "providers_queried": 0,
            "responses": [],
        }

    async def _query_provider(name: str, provider: Any) -> dict[str, Any]:
        start = time.time()
        try:
            response = await provider.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            elapsed = time.time() - start
            text = response.text if hasattr(response, "text") else str(response)
            return {
                "provider": name,
                "model": response.model if hasattr(response, "model") else name,
                "text": truncate(text, 1000),
                "tokens": (response.input_tokens + response.output_tokens) if hasattr(response, "input_tokens") else 0,
                "elapsed_ms": int(elapsed * 1000),
                "refused": False,
                "error": None,
            }
        except Exception as exc:
            elapsed = time.time() - start
            return {
                "provider": name,
                "model": name,
                "text": "",
                "tokens": 0,
                "elapsed_ms": int(elapsed * 1000),
                "refused": False,
                "error": str(exc)[:200],
            }

    tasks = [_query_provider(name, prov) for name, prov in providers_available]
    responses = await asyncio.gather(*tasks, return_exceptions=True)

    for prov in providers_available:
        with contextlib.suppress(Exception):
            await prov[1].close()

    successful = [r for r in responses if r["text"] and not r["error"]]
    refused = []
    if include_reframe:
        from loom.tools.llm.prompt_reframe import _detect_refusal, research_prompt_reframe
        for r in responses:
            if r["text"] and _detect_refusal(r["text"]):
                r["refused"] = True
                refused.append(r)

    fastest = min(successful, key=lambda x: x["elapsed_ms"]) if successful else None

    result: dict[str, Any] = {
        "prompt": prompt,
        "providers_queried": len(providers_available),
        "providers_responded": len(successful),
        "providers_refused": len(refused),
        "fastest_provider": fastest["provider"] if fastest else None,
        "fastest_ms": fastest["elapsed_ms"] if fastest else None,
        "responses": responses,
    }

    if include_reframe and refused:
        reframe_results = []
        for r in refused:
            reframed = await research_prompt_reframe(prompt, model=r["provider"])
            reframe_results.append({
                "provider": r["provider"],
                "original_refused": True,
                "reframed_with": reframed["strategy_used"],
                "reframed_prompt": reframed["reframed"][:500],
            })
        result["reframe_results"] = reframe_results

    return result
