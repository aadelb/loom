"""High-level LLM client helpers.

Provides simple functions for common LLM operations (summarize, classify,
extract, translate) without needing to know provider internals.
Uses the cascade system via provider_router.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("loom.llm_client")


async def query_llm(
    prompt: str,
    *,
    system: str = "",
    model: str = "",
    provider: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Send a query to the LLM cascade and return the response.

    This is the simplest way to call an LLM from within a tool.
    Uses the configured cascade order to find an available provider.

    Returns dict with 'text', 'provider', 'model', 'cost_usd', 'error'.
    """
    from loom.tools.llm import _call_with_cascade

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = await _call_with_cascade(
            messages,
            model=model or None,
            provider=provider or None,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return {
            "text": response.text,
            "provider": response.provider,
            "model": response.model,
            "cost_usd": getattr(response, "cost_usd", 0.0),
            "input_tokens": getattr(response, "input_tokens", 0),
            "output_tokens": getattr(response, "output_tokens", 0),
        }
    except Exception as exc:
        logger.error("llm_query_failed: %s", exc)
        return {"text": "", "error": str(exc)}


async def summarize(text: str, *, max_words: int = 100) -> str:
    """Summarize text using the LLM cascade."""
    result = await query_llm(
        f"Summarize the following text in {max_words} words or less:\n\n{text[:10000]}",
        temperature=0.3,
    )
    return result.get("text", "")


async def classify(text: str, categories: list[str]) -> str:
    """Classify text into one of the given categories."""
    cats = ", ".join(categories)
    result = await query_llm(
        f"Classify the following text into exactly one category from: {cats}\n\nText: {text[:5000]}\n\nRespond with only the category name.",
        temperature=0.1,
    )
    response = result.get("text", "").strip()
    # Try to match to a known category
    for cat in categories:
        if cat.lower() in response.lower():
            return cat
    return response


async def extract_entities(text: str) -> list[str]:
    """Extract named entities from text."""
    result = await query_llm(
        f"Extract all named entities (people, organizations, locations, products) from this text. Return one per line, nothing else:\n\n{text[:8000]}",
        temperature=0.1,
    )
    text_result = result.get("text", "")
    return [line.strip() for line in text_result.splitlines() if line.strip()]
