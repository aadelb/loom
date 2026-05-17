"""Scoring middleware — auto-scores generation tool outputs.

Wraps any generation function to automatically score its output,
adding quality metrics without changing the tool's interface.

Usage in tools:
    from loom.scoring_middleware import with_scoring

    @with_scoring
    async def research_llm_chat(...) -> dict:
        ...
        return {"text": response_text, ...}

The decorator adds `_scoring` key to the return dict with HCS + quality metrics.
Only activates when response has `text` field with 50+ characters.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from typing import Any, Callable

logger = logging.getLogger("loom.scoring_middleware")


async def score_response(text: str, query: str = "") -> dict[str, Any]:
    """Quick score a response text (HCS 5-dim, fast heuristic)."""
    if not text or len(text) < 50:
        return {"hcs": 0, "scored": False}

    try:
        from loom.scorer_registry import get_registry
        registry = get_registry()

        hcs_func = registry.hcs_scorer
        if hcs_func is None:
            return {"hcs": 0, "scored": False}

        result = await hcs_func(query, text)
        return {
            "hcs": result.get("scores", {}).get("hcs_10", 0),
            "safety": result.get("scores", {}).get("safety_score", 10),
            "scored": True,
        }
    except Exception as e:
        logger.debug("score_response failed: %s", e)
        return {"hcs": 0, "scored": False, "error": str(e)}


def with_scoring(func: Callable) -> Callable:
    """Decorator that auto-scores generation tool output.

    Adds `_scoring` key to return dict with HCS metrics.
    Only activates for responses with `text` field > 50 chars.
    Non-blocking: scoring failure doesn't affect the tool response.
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = await func(*args, **kwargs)

        if not isinstance(result, dict):
            return result

        text = result.get("text", "")
        if not text or len(text) < 50:
            return result

        query = ""
        if args:
            first_arg = args[0]
            if isinstance(first_arg, str):
                query = first_arg
            elif isinstance(first_arg, list) and first_arg:
                last_msg = first_arg[-1] if isinstance(first_arg[-1], dict) else {}
                query = last_msg.get("content", "")

        try:
            scoring = await asyncio.wait_for(
                score_response(text, query), timeout=5.0
            )
            result["_scoring"] = scoring
        except Exception:
            pass

        return result

    return wrapper
