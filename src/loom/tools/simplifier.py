"""Darkness Level Zero — simplify complex research into target formats.

Compresses complex research output (potentially thousands of words, technical
jargon) into audience-specific formats: executive (3 bullets + recommendation),
investor (ROI-focused, numbers), child (ELI5 analogies), tweet (280 chars), or
headline (one sentence).
"""

from __future__ import annotations

import logging
from typing import Any, Literal

try:
    from loom.tools.llm import _call_with_cascade
    _LLM_AVAILABLE = True
except ImportError:
    _LLM_AVAILABLE = False
    _call_with_cascade = None  # type: ignore[assignment]

logger = logging.getLogger("loom.tools.simplifier")


PROMPTS = {
    "executive": """You are an executive briefing expert. Compress this research into:
1. Three concise bullet points (key insights)
2. One actionable recommendation

Use business language. Max 200 words total.

Research to simplify:
{text}

Format:
- Bullet 1
- Bullet 2
- Bullet 3
Recommendation: [one sentence]""",
    "investor": """You are a venture investor analyst. Compress this research into:
1. Market opportunity / ROI impact
2. Key numbers or metrics (if any)
3. Investment thesis in 2-3 sentences

Emphasize addressable market, growth potential, and financial upside.
Max 300 words total.

Research to simplify:
{text}

Format:
Market: [size/opportunity]
Metrics: [key numbers]
Thesis: [investment case]""",
    "child": """You are explaining this to a 10-year-old. Use simple words, analogies,
and fun examples. Make it relatable. Avoid jargon. Max 150 words.

Research to simplify:
{text}

Explain in simple, fun language with analogies.""",
    "tweet": """Compress this research into a single tweet (280 chars max).
Make it punchy, memorable, and shareable.

Research to simplify:
{text}

Output only the tweet, nothing else.""",
    "headline": """Create a single headline that captures the key takeaway.
Compelling, clear, under 15 words.

Research to simplify:
{text}

Output only the headline, nothing else.""",
}


async def research_simplify(
    text: str,
    target_audience: str = "executive",
    max_length: int = 500,
) -> dict[str, Any]:
    """Simplify complex research into target format.

    Compresses complex research output into audience-specific formats.
    Uses LLM cascade for optimal quality.

    Args:
        text: complex research text to simplify (can be thousands of words)
        target_audience: "executive", "investor", "child", "tweet", or "headline"
        max_length: maximum output length (soft limit, for validation)

    Returns:
        Dict with:
        - simplified: the compressed text
        - target_audience: the audience type used
        - original_length: word count of input
        - simplified_length: word count of output
        - compression_ratio: simplified_length / original_length
    """
    if target_audience not in PROMPTS:
        raise ValueError(
            f"target_audience must be one of {list(PROMPTS.keys())}; "
            f"got {target_audience}"
        )

    if not text or not text.strip():
        raise ValueError("text cannot be empty")

    if len(text.strip()) > 50000:
        text = text[:50000]
        logger.warning("text truncated to 50000 chars")

    original_length = len(text.split())

    # Build prompt
    prompt_template = PROMPTS[target_audience]
    prompt = prompt_template.format(text=text)

    # Set max_tokens based on audience
    token_targets = {
        "executive": 300,
        "investor": 400,
        "child": 250,
        "tweet": 100,
        "headline": 50,
    }
    max_tokens = token_targets.get(target_audience, 300)

    # Call LLM via cascade
    try:
        response = await _call_with_cascade(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.3,
            timeout=30,
        )
        simplified = response.text.strip()
    except Exception as exc:
        logger.error("simplify_cascade_failed audience=%s error=%s", target_audience, exc)
        raise

    simplified_length = len(simplified.split())
    compression_ratio = (
        simplified_length / original_length if original_length > 0 else 0
    )

    return {
        "simplified": simplified,
        "target_audience": target_audience,
        "original_length": original_length,
        "simplified_length": simplified_length,
        "compression_ratio": round(compression_ratio, 3),
    }
