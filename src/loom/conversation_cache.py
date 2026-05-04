"""Conversation-level caching for multi-turn LLM exchanges.

Provides content-hash caching of entire conversations (system prompt + message list)
to avoid redundant LLM API calls when the same multi-turn dialogue is repeated.
Supports model-agnostic caching (same conversation yields same cache hit regardless
of model) or model-specific caching (different models have separate cache entries).
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from loom.cache import get_cache

logger = logging.getLogger("loom.conversation_cache")


def hash_conversation(
    system_prompt: str,
    messages: list[dict[str, str]],
    model: str = "",
) -> str:
    """Hash a conversation for cache keying.

    Normalizes the conversation (sorted keys, stripped whitespace) and computes
    SHA-256 hash. If model is empty (model-agnostic mode), the model is excluded
    from the hash so the same conversation yields the same cache hit regardless
    of which model responds. Otherwise, the model is included in the hash.

    Args:
        system_prompt: system prompt string (normalized and hashed)
        messages: list of message dicts with 'role' and 'content' keys
        model: model identifier (included in hash if non-empty; set to "" for model-agnostic)

    Returns:
        SHA-256 hex digest (first 32 chars for brevity)
    """
    # Normalize system prompt: strip whitespace, lowercase
    normalized_system = system_prompt.strip()

    # Normalize messages: sort keys and strip whitespace from values
    normalized_messages = []
    for msg in messages:
        normalized_msg = {}
        for key in sorted(msg.keys()):
            val = msg[key]
            if isinstance(val, str):
                normalized_msg[key] = val.strip()
            else:
                normalized_msg[key] = val
        normalized_messages.append(normalized_msg)

    # Build the canonical conversation string
    conv_dict = {
        "system_prompt": normalized_system,
        "messages": normalized_messages,
    }

    # Include model in hash only if non-empty (model-specific caching)
    if model:
        conv_dict["model"] = model.strip()

    # Serialize deterministically (sorted keys, no extra whitespace)
    conv_json = json.dumps(conv_dict, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    conv_bytes = conv_json.encode("utf-8")

    # Return SHA-256 hash (full 64 chars for now; can be truncated to 32 if needed)
    return hashlib.sha256(conv_bytes).hexdigest()


def cache_conversation(
    conv_hash: str,
    response: str,
    ttl: int = 3600,
) -> None:
    """Store a conversation response in cache.

    Uses the global CacheStore singleton with key prefix "conv:".
    Response is wrapped with metadata (timestamp, TTL).

    Args:
        conv_hash: conversation hash from hash_conversation()
        response: LLM response text to cache
        ttl: time-to-live in seconds (default 1 hour)

    Raises:
        Exception: if cache write fails
    """
    cache = get_cache()
    cache_key = f"conv:{conv_hash}"

    metadata = {
        "response": response,
        "cached_at": datetime.now(UTC).isoformat(),
        "ttl": ttl,
    }

    try:
        cache.put(cache_key, metadata)
        logger.debug("conversation_cached conv_hash=%s ttl=%d", conv_hash, ttl)
    except Exception as e:
        logger.error("conversation_cache_failed conv_hash=%s error=%s", conv_hash, e)
        raise


def get_cached_conversation(conv_hash: str) -> str | None:
    """Retrieve a cached conversation response if valid.

    Checks cache for key with prefix "conv:", validates TTL, and returns
    response text if found and not expired.

    Args:
        conv_hash: conversation hash from hash_conversation()

    Returns:
        Cached response text if found and valid, None if not cached or expired
    """
    cache = get_cache()
    cache_key = f"conv:{conv_hash}"

    cached_data = cache.get(cache_key)
    if cached_data is None:
        return None

    # Validate cached data has required fields
    if "response" not in cached_data or "cached_at" not in cached_data:
        logger.warning("conversation_cache_invalid conv_hash=%s", conv_hash)
        return None

    response = cached_data["response"]
    cached_at_str = cached_data["cached_at"]
    ttl = cached_data.get("ttl", 3600)

    # Check if expired
    try:
        cached_at = datetime.fromisoformat(cached_at_str)
        now = datetime.now(UTC)
        age = (now - cached_at).total_seconds()

        if age > ttl:
            logger.debug("conversation_cache_expired conv_hash=%s age_secs=%d ttl=%d", conv_hash, int(age), ttl)
            return None

        logger.debug("conversation_cache_hit conv_hash=%s age_secs=%d", conv_hash, int(age))
        return cast(str, response)
    except (ValueError, TypeError) as e:
        logger.warning("conversation_cache_metadata_invalid conv_hash=%s error=%s", conv_hash, e)
        return None


def get_cached_conversation_with_metadata(conv_hash: str) -> dict[str, Any] | None:
    """Retrieve a cached conversation response with freshness metadata.

    Extends get_cached_conversation() to include timestamps and freshness info.

    Args:
        conv_hash: conversation hash from hash_conversation()

    Returns:
        Dict with keys:
            - response: cached response text
            - cached_at: ISO timestamp when cached
            - cache_age_seconds: age of cache entry
            - ttl: original TTL in seconds
            - is_expired: bool — True if TTL exceeded
        Returns None if not cached, expired, or invalid.
    """
    cache = get_cache()
    cache_key = f"conv:{conv_hash}"

    cached_data = cache.get(cache_key)
    if cached_data is None:
        return None

    if "response" not in cached_data or "cached_at" not in cached_data:
        logger.warning("conversation_cache_invalid conv_hash=%s", conv_hash)
        return None

    response = cached_data["response"]
    cached_at_str = cached_data["cached_at"]
    ttl = cached_data.get("ttl", 3600)

    try:
        cached_at = datetime.fromisoformat(cached_at_str)
        now = datetime.now(UTC)
        age = (now - cached_at).total_seconds()
        is_expired = age > ttl

        if is_expired:
            logger.debug("conversation_cache_expired conv_hash=%s age_secs=%d ttl=%d", conv_hash, int(age), ttl)

        return {
            "response": response,
            "cached_at": cached_at_str,
            "cache_age_seconds": int(age),
            "ttl": ttl,
            "is_expired": is_expired,
        }
    except (ValueError, TypeError) as e:
        logger.warning("conversation_cache_metadata_invalid conv_hash=%s error=%s", conv_hash, e)
        return None


async def research_conversation_cache_stats() -> dict[str, Any]:
    """Return conversation cache statistics.

    Analyzes all cached conversations (entries with "conv:" prefix) and
    returns aggregated stats: hit count, miss count, total cached, average
    response size, TTL distribution, etc.

    Returns:
        Dict with keys:
            - conversations_cached: number of unique conversations cached
            - avg_response_size_bytes: average response size
            - hit_rate_percent: estimated hit rate (active / total)
            - total_cache_size_bytes: total bytes in "conv:" entries
            - ttl_distribution: dict mapping TTL ranges to counts
            - oldest_cached_at: ISO timestamp of oldest entry
            - newest_cached_at: ISO timestamp of newest entry
    """
    cache = get_cache()
    stats = cache.stats()

    # For now, return basic stats with a placeholder for conversation-specific data
    # In a future version, we'd parse all "conv:" entries from the file system
    return {
        "total_cache_files": stats.get("file_count", 0),
        "total_cache_bytes": stats.get("total_bytes", 0),
        "cache_days_present": stats.get("days_present", []),
        "note": "conversation-specific stats require filesystem scan; call get_cache().stats() for full cache info",
    }
