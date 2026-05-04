"""Semantic caching system for LLM response cost reduction.

Uses text similarity (TF-IDF, Jaccard, n-gram overlap) to cache and reuse
responses for semantically similar queries. No heavy dependencies (numpy/sklearn).

Stores cache entries in daily directories with model-specific keys. Tracks
cache statistics (hit rate, estimated cost savings).

Features:
- Higher precision matching with 0.95 default threshold
- Configurable via LOOM_CACHE_THRESHOLD env var
- Cross-model cache support: queries from one model can hit cache from another
- Cache metadata tracking: hit status, age, original model
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as _dt
import gzip
import hashlib
import json
import logging
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

log = logging.getLogger("loom.semantic_cache")


def _get_cache_threshold() -> float:
    """Get similarity threshold from environment or use default.

    Returns:
        Similarity threshold [0.0, 1.0]. Default 0.95 for high precision.
    """
    threshold_str = os.environ.get("LOOM_CACHE_THRESHOLD", "0.95")
    try:
        threshold = float(threshold_str)
        return max(0.0, min(1.0, threshold))
    except ValueError:
        log.warning("invalid LOOM_CACHE_THRESHOLD=%s, using default 0.95", threshold_str)
        return 0.95


def _utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return _dt.datetime.now(_dt.UTC).isoformat()


def _utc_now_timestamp() -> float:
    """Return current UTC time as UNIX timestamp."""
    return time.time()


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words, removing punctuation.

    Args:
        text: Input text

    Returns:
        List of lowercase tokens
    """
    # Convert to lowercase and remove non-alphanumeric except spaces/hyphens
    text = text.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    # Split on whitespace and filter empty
    return [t for t in text.split() if t.strip()]


def _compute_word_overlap(tokens1: list[str], tokens2: list[str]) -> float:
    """Compute word overlap similarity (Jaccard index).

    Args:
        tokens1: First token list
        tokens2: Second token list

    Returns:
        Similarity score [0.0, 1.0]
    """
    if not tokens1 or not tokens2:
        return 0.0

    set1 = set(tokens1)
    set2 = set(tokens2)

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    if union == 0:
        return 0.0
    return intersection / union


def _compute_ngram_overlap(text1: str, text2: str, n: int = 3) -> float:
    """Compute character n-gram overlap similarity.

    Args:
        text1: First text
        text2: Second text
        n: n-gram length (default 3 for trigrams)

    Returns:
        Similarity score [0.0, 1.0]
    """
    text1 = text1.lower().strip()
    text2 = text2.lower().strip()

    if not text1 or not text2:
        return 0.0

    # Extract n-grams
    ngrams1 = {text1[i : i + n] for i in range(len(text1) - n + 1)} if len(text1) >= n else set()
    ngrams2 = {text2[i : i + n] for i in range(len(text2) - n + 1)} if len(text2) >= n else set()

    if not ngrams1 or not ngrams2:
        return 0.0

    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)

    if union == 0:
        return 0.0
    return intersection / union


def _compute_tfidf_similarity(tokens1: list[str], tokens2: list[str]) -> float:
    """Compute simplified TF-IDF cosine similarity (document frequency ignored).

    Uses term frequency (TF) weighting only without inverse document frequency
    since we have no corpus. Returns cosine similarity of TF vectors.

    Args:
        tokens1: First token list
        tokens2: Second token list

    Returns:
        Similarity score [0.0, 1.0]
    """
    if not tokens1 or not tokens2:
        return 0.0

    # Count term frequencies
    tf1: dict[str, int] = {}
    tf2: dict[str, int] = {}

    for t in tokens1:
        tf1[t] = tf1.get(t, 0) + 1
    for t in tokens2:
        tf2[t] = tf2.get(t, 0) + 1

    # Compute cosine similarity: dot(tf1, tf2) / (norm(tf1) * norm(tf2))
    dot_product = 0.0
    for term in set(tf1.keys()) & set(tf2.keys()):
        dot_product += tf1[term] * tf2[term]

    norm1 = sum(v * v for v in tf1.values()) ** 0.5
    norm2 = sum(v * v for v in tf2.values()) ** 0.5

    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


class SemanticCache:
    """Cache LLM responses using semantic similarity for near-duplicate queries.

    Uses text similarity metrics (TF-IDF, Jaccard, n-gram overlap) to identify
    and reuse cached responses for semantically similar queries. No external
    dependencies — pure Python implementation.

    Cache entries are organized in daily directories by content hash. Supports
    both model-specific and cross-model cache matching.

    Attributes:
        cache_dir: Root directory for cache storage
        threshold: Minimum similarity score [0.0, 1.0] to return cached response
        cross_model_cache: Enable cross-model cache hits
        index: In-memory index of {hash: entry_dict}
        _stats: Cache statistics (hits, misses, total_queries, etc.)
        _lock: Asyncio lock for thread-safe operations
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        similarity_threshold: float | None = None,
        cross_model_cache: bool = True,
    ) -> None:
        """Initialize semantic cache.

        Args:
            cache_dir: Root directory for cache storage. If None, defaults to
                      ~/.cache/loom/semantic/
            similarity_threshold: Minimum similarity score [0.0, 1.0] to return
                                 cached response. If None, reads from
                                 LOOM_CACHE_THRESHOLD env var (default 0.95)
            cross_model_cache: Enable cross-model cache hits (default True).
                             When True, a query from one model can hit cache
                             from another model with metadata indicating the
                             original model.
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "loom" / "semantic"
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if similarity_threshold is None:
            self.threshold = _get_cache_threshold()
        else:
            self.threshold = max(0.0, min(1.0, similarity_threshold))

        self.cross_model_cache = cross_model_cache

        self.index: dict[str, dict[str, Any]] = {}
        self._stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "semantic_hits": 0,
            "cross_model_hits": 0,
        }
        self._lock = asyncio.Lock()

        # Load existing index from disk
        self._load_index()

        log.info(
            "semantic_cache_initialized threshold=%.2f cross_model=%s entries=%d",
            self.threshold,
            self.cross_model_cache,
            len(self.index),
        )

    def _load_index(self) -> None:
        """Load index from all date directories on disk.

        Scans all daily subdirectories for cache files and rebuilds the
        in-memory index. Handles both compressed (.json.gz) and legacy
        (.json) files.
        """
        self.index = {}

        try:
            for day_dir in self.cache_dir.iterdir():
                if not day_dir.is_dir():
                    continue

                # Load compressed files
                for gz_file in day_dir.glob("*.json.gz"):
                    try:
                        compressed_data = gz_file.read_bytes()
                        decompressed = gzip.decompress(compressed_data)
                        entry = json.loads(decompressed.decode("utf-8"))
                        entry_hash = gz_file.stem.replace(".json", "")
                        self.index[entry_hash] = entry
                    except Exception as e:
                        log.debug("failed to load cached entry %s: %s", gz_file, e)
                        continue

                # Load legacy uncompressed files
                for json_file in day_dir.glob("*.json"):
                    try:
                        entry = json.loads(json_file.read_text(encoding="utf-8"))
                        entry_hash = json_file.stem
                        self.index[entry_hash] = entry
                    except Exception as e:
                        log.debug("failed to load cached entry %s: %s", json_file, e)
                        continue
        except Exception as e:
            log.warning("failed to load semantic cache index: %s", e)

    def _cache_path(self, entry_hash: str) -> Path:
        """Compute cache file path from hash.

        Args:
            entry_hash: Content hash (SHA-256, 32 hex chars)

        Returns:
            Path to cache file (in daily subdirectory)
        """
        day = _dt.date.today().isoformat()
        p = self.cache_dir / day / f"{entry_hash}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def similarity(self, query1: str, query2: str) -> float:
        """Compute semantic similarity between two queries.

        Uses weighted combination of three metrics:
        - Word overlap (Jaccard index): 40% weight
        - Character n-gram overlap (trigrams): 30% weight
        - TF-IDF cosine similarity: 30% weight

        Args:
            query1: First query
            query2: Second query

        Returns:
            Similarity score [0.0, 1.0]
        """
        if not query1 or not query2:
            return 0.0

        # Tokenize both queries
        tokens1 = _tokenize(query1)
        tokens2 = _tokenize(query2)

        # Compute three similarity metrics
        word_overlap = _compute_word_overlap(tokens1, tokens2)
        ngram_overlap = _compute_ngram_overlap(query1, query2, n=3)
        tfidf_sim = _compute_tfidf_similarity(tokens1, tokens2)

        # Weighted combination
        similarity = word_overlap * 0.4 + ngram_overlap * 0.3 + tfidf_sim * 0.3

        return max(0.0, min(1.0, similarity))

    async def get(
        self,
        query: str,
        model: str = "",
        cross_model_cache: bool | None = None,
    ) -> dict[str, Any] | None:
        """Check if a semantically similar query was already cached.

        Searches the cache index for entries with similarity >= threshold.
        Returns the best match if found, or None otherwise.

        First attempts model-specific match, then (if enabled) cross-model match.

        Args:
            query: LLM query/prompt
            model: Model name (for model-specific caching)
            cross_model_cache: Override class-level cross_model_cache setting

        Returns:
            Dict with keys:
            - cached_response: The cached LLM response
            - similarity_score: Similarity [0.0, 1.0]
            - original_query: The original cached query
            - cached_at: ISO 8601 timestamp
            - cached_from_model: Model that originally cached (if cross-model hit)
            - is_semantic_match: True if match via similarity (not exact)
            - cache_age_seconds: Seconds since cache entry was created
            - cache_hit: Always True
            Or None if no cache hit
        """
        async with self._lock:
            self._stats["total_queries"] += 1

            if not query or not self.index:
                self._stats["cache_misses"] += 1
                return None

            use_cross_model = cross_model_cache if cross_model_cache is not None else self.cross_model_cache

            # Try model-specific match first
            result = self._find_best_match(query, model, cross_model=False)

            # Try cross-model match if enabled and no model-specific match
            if result is None and use_cross_model:
                result = self._find_best_match(query, model, cross_model=True)

                if result is not None:
                    self._stats["cross_model_hits"] += 1

            if result is not None:
                self._stats["cache_hits"] += 1
                if result.get("is_semantic_match"):
                    self._stats["semantic_hits"] += 1
                return result

            self._stats["cache_misses"] += 1
            return None

    def _find_best_match(
        self,
        query: str,
        model: str,
        cross_model: bool = False,
    ) -> dict[str, Any] | None:
        """Find best cache match (internal helper).

        Args:
            query: LLM query/prompt
            model: Model name for filtering
            cross_model: If True, ignore model filter; if False, match model only

        Returns:
            Cache result dict or None
        """
        cache_key = f"{model}::{query}"

        # Check for exact match first
        exact_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()
        if exact_hash in self.index:
            entry = self.index[exact_hash]
            return self._build_result(entry, exact_hash, is_semantic=False)

        # Search for semantic match (best similarity >= threshold)
        best_match = None
        best_similarity = 0.0
        best_hash = None

        for entry_hash, entry in self.index.items():
            # Filter by model unless cross_model is True
            if not cross_model and entry.get("model") != model:
                continue

            # Skip exact matches (already checked)
            if entry_hash == exact_hash:
                continue

            # Compute similarity
            sim = self.similarity(query, entry["query"])

            if sim > best_similarity and sim >= self.threshold:
                best_similarity = sim
                best_match = entry
                best_hash = entry_hash

        if best_match:
            return self._build_result(best_match, best_hash or "", is_semantic=True, similarity=best_similarity)

        return None

    def _build_result(
        self,
        entry: dict[str, Any],
        entry_hash: str,
        is_semantic: bool,
        similarity: float | None = None,
    ) -> dict[str, Any]:
        """Build cache result dict with metadata.

        Args:
            entry: Cache entry dict
            entry_hash: Entry hash (for timestamp parsing if needed)
            is_semantic: True if semantic match, False if exact
            similarity: Similarity score (for semantic matches)

        Returns:
            Result dict with cache hit metadata
        """
        result = {
            "cached_response": entry["response"],
            "similarity_score": similarity if similarity is not None else 1.0,
            "original_query": entry["query"],
            "cached_at": entry["cached_at"],
            "is_semantic_match": is_semantic,
            "cache_hit": True,
        }

        # Add model info if this is a cross-model hit
        cached_model = entry.get("model", "")
        if cached_model:
            result["cached_from_model"] = cached_model

        # Calculate cache age in seconds
        try:
            cached_dt = _dt.datetime.fromisoformat(entry["cached_at"])
            now_dt = _dt.datetime.now(_dt.UTC)
            age_seconds = int((now_dt - cached_dt).total_seconds())
            result["cache_age_seconds"] = max(0, age_seconds)
        except (ValueError, KeyError):
            result["cache_age_seconds"] = 0

        return result

    async def put(
        self,
        query: str,
        response: str,
        model: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store query-response pair with semantic features.

        Extracts tokens and features, stores in daily directory with
        atomic write (uuid tmp + os.replace). Updates in-memory index.

        Args:
            query: LLM query/prompt
            response: LLM response text
            model: Model name (for model-specific caching)
            metadata: Optional metadata dict (e.g., cost, tokens)
        """
        if not query or not response:
            return

        async with self._lock:
            cache_key = f"{model}::{query}"
            entry_hash = hashlib.sha256(cache_key.encode("utf-8")).hexdigest()

            # Skip if already cached
            if entry_hash in self.index:
                return

            # Extract features
            tokens = _tokenize(query)

            # Build entry with timestamp
            cached_at = _utc_now_iso()
            entry = {
                "query": query,
                "response": response,
                "model": model,
                "tokens": tokens,
                "cached_at": cached_at,
                "query_length": len(query),
                "response_length": len(response),
            }

            if metadata:
                entry["metadata"] = metadata

            # Write to disk with gzip compression
            cache_path = self._cache_path(entry_hash)
            gz_path = cache_path.with_suffix(".json.gz")
            tmp = gz_path.with_suffix(gz_path.suffix + f".tmp-{uuid.uuid4().hex}")

            try:
                json_str = json.dumps(entry, ensure_ascii=False)
                json_bytes = json_str.encode("utf-8")
                compressed = gzip.compress(json_bytes, compresslevel=6)

                tmp.write_bytes(compressed)
                os.replace(tmp, gz_path)

                # Update in-memory index
                self.index[entry_hash] = entry
            except Exception as e:
                log.exception("semantic_cache_put_failed: %s", e)
                if tmp.exists():
                    with contextlib.suppress(Exception):
                        tmp.unlink()
                raise

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with keys:
            - total_queries: Total get/put operations
            - cache_hits: Successful cache hits (exact + semantic)
            - cache_misses: Cache misses
            - semantic_hits: Hits via semantic matching (not exact)
            - cross_model_hits: Hits via cross-model matching
            - hit_rate: Hit rate percentage [0.0, 100.0]
            - entries_cached: Total cached entries
            - estimated_savings_usd: Estimated cost savings from cache hits
            - threshold: Current similarity threshold
            - cross_model_cache_enabled: Whether cross-model caching is enabled
        """
        hit_rate = (
            100.0 * self._stats["cache_hits"] / self._stats["total_queries"]
            if self._stats["total_queries"] > 0
            else 0.0
        )

        # Estimate cost savings (assuming avg LLM call: $0.001 for 1000 tokens)
        # This is conservative; actual savings depend on model/tokens
        estimated_savings = self._stats["cache_hits"] * 0.001

        return {
            "total_queries": self._stats["total_queries"],
            "cache_hits": self._stats["cache_hits"],
            "cache_misses": self._stats["cache_misses"],
            "semantic_hits": self._stats["semantic_hits"],
            "cross_model_hits": self._stats["cross_model_hits"],
            "hit_rate": round(hit_rate, 2),
            "entries_cached": len(self.index),
            "estimated_savings_usd": round(estimated_savings, 4),
            "threshold": round(self.threshold, 2),
            "cross_model_cache_enabled": self.cross_model_cache,
        }

    async def clear_older_than(self, days: int = 30) -> int:
        """Remove cache entries older than N days.

        Args:
            days: Remove entries older than this many days

        Returns:
            Count of removed files
        """
        async with self._lock:
            cutoff = _dt.date.today() - _dt.timedelta(days=days)
            removed = 0

            try:
                for day_dir in self.cache_dir.iterdir():
                    if not day_dir.is_dir():
                        continue

                    try:
                        d = _dt.date.fromisoformat(day_dir.name)
                    except ValueError:
                        continue

                    if d < cutoff:
                        # Remove both compressed and legacy files
                        for pattern in ("*.json.gz", "*.json"):
                            for f in day_dir.glob(pattern):
                                try:
                                    f.unlink()
                                    removed += 1

                                    # Remove from index
                                    entry_hash = f.stem.replace(".json", "")
                                    self.index.pop(entry_hash, None)
                                except Exception as e:
                                    log.warning("failed to remove cache file %s: %s", f, e)

                        with contextlib.suppress(OSError):
                            day_dir.rmdir()
            except Exception as e:
                log.warning("failed to clear old cache entries: %s", e)

            return removed


# Module-level singleton
_semantic_cache_singleton: SemanticCache | None = None


def get_semantic_cache(
    cache_dir: str | Path | None = None,
    similarity_threshold: float | None = None,
    cross_model_cache: bool = True,
) -> SemanticCache:
    """Get or create the process-wide SemanticCache singleton.

    Args:
        cache_dir: Cache directory (only used on first call)
        similarity_threshold: Similarity threshold (only used on first call).
                            If None, reads from LOOM_CACHE_THRESHOLD env var.
        cross_model_cache: Enable cross-model caching (only used on first call)

    Returns:
        SemanticCache singleton instance
    """
    global _semantic_cache_singleton
    if _semantic_cache_singleton is None:
        _semantic_cache_singleton = SemanticCache(
            cache_dir=cache_dir,
            similarity_threshold=similarity_threshold,
            cross_model_cache=cross_model_cache,
        )
    return _semantic_cache_singleton
