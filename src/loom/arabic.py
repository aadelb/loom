"""Arabic language support for Loom — detection, routing, and RTL handling.

Provides:
- detect_arabic(text: str) -> bool: Check if text contains Arabic characters
- get_arabic_preferred_providers() -> list[str]: Return Arabic-capable providers
- route_by_language(text: str, default_cascade: list[str]) -> list[str]: Reorder cascade for Arabic
- is_rtl_text(text: str) -> bool: Check if text is primarily right-to-left

Arabic Unicode ranges covered:
  - ؀-ۿ   (Arabic block: U+0600 to U+06FF)
  - ݐ-ݿ   (Arabic Supplement: U+0750 to U+077F)
  - ࢠ-ࣿ   (Arabic Extended-A: U+08A0 to U+08FF)
  - ﭐ-﷿   (Arabic Presentation Forms-A: U+FB50 to U+FDFF)
  - ﹰ-﻿   (Arabic Presentation Forms-B: U+FE70 to U+FEFF)

Providers ranked by Arabic support:
  1. qwen (Alibaba): Native Arabic via LLaMA-based training
  2. gemini (Google): Strong multilingual including Arabic
  3. kimi (Moonshot): Optimized for multilingual, including Arabic
  4. deepseek (DeepSeek): Good multilingual coverage
  5. Others: Limited Arabic support
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("loom.arabic")

# Comprehensive regex covering all Arabic Unicode blocks
_ARABIC_PATTERN = re.compile(
    r"[؀-ۿ"  # Arabic block (U+0600–U+06FF)
    r"ݐ-ݿ"   # Arabic Supplement (U+0750–U+077F)
    r"ࢠ-ࣿ"   # Arabic Extended-A (U+08A0–U+08FF)
    r"ﭐ-﷿"   # Arabic Presentation Forms-A (U+FB50–U+FDFF)
    r"ﹰ-﻿]"  # Arabic Presentation Forms-B (U+FE70–U+FEFF)
)

# Arabic-capable LLM providers, ranked by quality
_ARABIC_PROVIDERS = ["qwen", "gemini", "kimi", "deepseek"]


def detect_arabic(text: str) -> bool:
    """Return True if text contains Arabic characters.

    Args:
        text: Input text to check

    Returns:
        bool: True if text contains any Arabic character, False otherwise

    Examples:
        >>> detect_arabic("كيف أصبح غنياً")
        True
        >>> detect_arabic("how to be rich")
        False
        >>> detect_arabic("Hello مرحبا world")
        True
    """
    if not text:
        return False
    return bool(_ARABIC_PATTERN.search(text))


def get_arabic_preferred_providers() -> list[str]:
    """Return list of Arabic-capable providers in preferred order.

    Returns:
        list[str]: Providers optimized for Arabic, ranked by quality:
                   ["qwen", "gemini", "kimi", "deepseek"]
    """
    return _ARABIC_PROVIDERS.copy()


def route_by_language(
    text: str,
    default_cascade: list[str],
) -> list[str]:
    """Reorder LLM provider cascade to prioritize Arabic-capable providers if needed.

    If text contains Arabic characters, moves Arabic-capable providers to the front
    while preserving the order of other providers. If text is not Arabic, returns
    the default cascade unchanged.

    Args:
        text: Input text to analyze
        default_cascade: Default list of provider names (e.g., from config)

    Returns:
        list[str]: Reordered cascade with Arabic providers first (if Arabic detected),
                   or unchanged default cascade if no Arabic detected

    Examples:
        >>> route_by_language("كيف أصبح غنياً", ["groq", "gemini", "openai"])
        ["gemini", "groq", "openai"]

        >>> route_by_language("how to be rich", ["groq", "gemini", "openai"])
        ["groq", "gemini", "openai"]
    """
    if not detect_arabic(text):
        return default_cascade

    # Move Arabic-capable providers to front, preserving order
    arabic_capable = [p for p in _ARABIC_PROVIDERS if p in default_cascade]
    other_providers = [p for p in default_cascade if p not in _ARABIC_PROVIDERS]

    logger.info(
        "arabic_routing_applied text_sample=%s arabic_providers=%s other_providers=%s",
        text[:50],
        arabic_capable,
        other_providers,
    )

    return arabic_capable + other_providers


def is_rtl_text(text: str) -> bool:
    """Check if text is primarily right-to-left (Arabic, Hebrew, Farsi, etc.).

    For now, checks if text contains Arabic characters. Can be extended
    to handle Hebrew and other RTL scripts.

    Args:
        text: Input text to check

    Returns:
        bool: True if text is RTL, False otherwise
    """
    if not text:
        return False

    # Count Arabic characters vs total letters
    if detect_arabic(text):
        return True

    return False
