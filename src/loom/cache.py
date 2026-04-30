"""Content-hash cache with atomic writes, gzip compression, and daily directory structure.

Provides a CacheStore class for managing cached responses by content-hash
(SHA-256), organized by date for easy TTL cleanup. Stores cache files as
gzip-compressed JSON (.json.gz) for 60%+ space savings with automatic fallback
to legacy .json files for backward compatibility.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import gzip
import hashlib
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, cast

log = logging.getLogger("loom.cache")


def _utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return _dt.datetime.now(_dt.UTC).isoformat()


class CacheStore:
    """Content-hash cache with gzip compression, atomic writes, and daily directory structure.

    Stores JSON blobs indexed by content-hash (SHA-256), organized under
    daily directories for easy TTL pruning. Uses gzip compression (level 6)
    to achieve 60%+ space savings. Uses atomic writes (uuid tmp +
    os.replace) to prevent corruption from concurrent writers. Automatically
    reads legacy .json files for backward compatibility.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        """Initialize cache store.

        Args:
            base_dir: root directory for cache storage. If None, reads from
                     LOOM_CACHE_DIR environment variable or defaults to
                     ~/.cache/loom.
        """
        if base_dir is None:
            base_dir = os.environ.get(
                "LOOM_CACHE_DIR",
                str(Path.home() / ".cache" / "loom"),
            )
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, key: str) -> Path:
        """Compute cache file path from key.

        Hashes the key (SHA-256, first 32 hex chars) and organizes under
        a daily subdirectory (ISO date) to enable easy TTL cleanup.

        Args:
            key: cache key (typically "<tool>::<params>::<url>")

        Returns:
            Path to cached file (created on put, may not exist on get).
        """
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        day = _dt.date.today().isoformat()
        p = self.base_dir / day / f"{h}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve cached value by key.

        Searches today's directory first, then all date directories
        so entries from previous days still produce cache hits. Tries
        compressed (.json.gz) first, then legacy uncompressed (.json).

        Args:
            key: cache key

        Returns:
            Cached dict if found and valid JSON, None otherwise.
        """
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]

        # Fast path: check today's directory (compressed first, then legacy)
        p = self._cache_path(key)
        gz_path = p.with_suffix(".json.gz")

        if gz_path.exists():
            try:
                compressed_data = gz_path.read_bytes()
                decompressed = gzip.decompress(compressed_data)
                return cast(dict[str, Any] | None, json.loads(decompressed.decode("utf-8")))
            except Exception as e:
                log.debug("cache_get_failed (compressed) key=%s: %s", key, e)
                return None

        if p.exists():
            try:
                return cast(dict[str, Any] | None, json.loads(p.read_text(encoding="utf-8")))
            except Exception as e:
                log.debug("cache_get_failed (legacy) key=%s: %s", key, e)
                return None

        # Slow path: search all date directories (newest first)
        # Try compressed first across all dirs, then legacy
        try:
            # Search for compressed files
            matches = sorted(self.base_dir.glob(f"*/{h}.json.gz"), reverse=True)
            for match in matches:
                try:
                    compressed_data = match.read_bytes()
                    decompressed = gzip.decompress(compressed_data)
                    return cast(dict[str, Any] | None, json.loads(decompressed.decode("utf-8")))
                except Exception:
                    continue

            # Fallback to legacy uncompressed files
            matches = sorted(self.base_dir.glob(f"*/{h}.json"), reverse=True)
            for match in matches:
                try:
                    return cast(dict[str, Any] | None, json.loads(match.read_text(encoding="utf-8")))
                except Exception:
                    continue
        except Exception as e:
            log.debug("cache_glob_failed key=%s: %s", key, e)

        return None

    def get_with_metadata(self, key: str) -> dict[str, Any] | None:
        """Retrieve cached value with freshness metadata.

        Returns cached data along with timestamps and freshness indicators,
        or None if no cache entry exists. Automatically handles both
        compressed and legacy uncompressed files.

        Args:
            key: cache key

        Returns:
            Dict with 'data', 'cached_at' (ISO timestamp), 'freshness_hours',
            and 'is_stale' (True if older than 24 hours), or None if not cached.
        """
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]

        # Try to find the cache file (newest first across all date dirs)
        # Try compressed first, then legacy
        try:
            # Search for compressed files
            matches = sorted(self.base_dir.glob(f"*/{h}.json.gz"), reverse=True)
            for match in matches:
                try:
                    compressed_data = match.read_bytes()
                    decompressed = gzip.decompress(compressed_data)
                    raw = json.loads(decompressed.decode("utf-8"))
                    mtime = _dt.datetime.fromtimestamp(
                        match.stat().st_mtime,
                        tz=_dt.timezone.utc,
                    )
                    now = _dt.datetime.now(_dt.timezone.utc)
                    freshness_seconds = (now - mtime).total_seconds()
                    freshness_hours = freshness_seconds / 3600
                    is_stale = freshness_hours > 24

                    return {
                        "data": raw,
                        "cached_at": mtime.isoformat(),
                        "freshness_hours": round(freshness_hours, 1),
                        "is_stale": is_stale,
                    }
                except Exception as e:
                    log.debug("cache_metadata_extraction_failed (compressed) for %s: %s", match, e)
                    continue

            # Fallback to legacy uncompressed files
            matches = sorted(self.base_dir.glob(f"*/{h}.json"), reverse=True)
            for match in matches:
                try:
                    raw = json.loads(match.read_text(encoding="utf-8"))
                    mtime = _dt.datetime.fromtimestamp(
                        match.stat().st_mtime,
                        tz=_dt.timezone.utc,
                    )
                    now = _dt.datetime.now(_dt.timezone.utc)
                    freshness_seconds = (now - mtime).total_seconds()
                    freshness_hours = freshness_seconds / 3600
                    is_stale = freshness_hours > 24

                    return {
                        "data": raw,
                        "cached_at": mtime.isoformat(),
                        "freshness_hours": round(freshness_hours, 1),
                        "is_stale": is_stale,
                    }
                except Exception as e:
                    log.debug("cache_metadata_extraction_failed (legacy) for %s: %s", match, e)
                    continue
        except Exception as e:
            log.debug("cache_glob_failed key=%s: %s", key, e)

        return None

    def put(self, key: str, value: dict[str, Any]) -> None:
        """Store value in cache with gzip compression and atomic write.

        Uses uuid-suffixed temp file + os.replace to ensure atomic,
        concurrent-safe writes (even within the same process). Compresses
        JSON with gzip level 6 for optimal compression/speed tradeoff.

        Args:
            key: cache key
            value: dict to store (must be JSON-serializable)

        Raises:
            Exception: if JSON encoding fails or disk I/O fails
        """
        p = self._cache_path(key)
        gz_path = p.with_suffix(".json.gz")
        tmp = gz_path.with_suffix(gz_path.suffix + f".tmp-{uuid.uuid4().hex}")

        try:
            # Serialize to JSON, then compress
            json_str = json.dumps(value, ensure_ascii=False)
            json_bytes = json_str.encode("utf-8")
            compressed = gzip.compress(json_bytes, compresslevel=6)

            # Write compressed data to tmp file
            tmp.write_bytes(compressed)
            os.replace(tmp, gz_path)
        except Exception:
            log.exception("cache_put_failed key=%s", key)
            if tmp.exists():
                with contextlib.suppress(Exception):
                    tmp.unlink()
            raise

    def stats(self) -> dict[str, Any]:
        """Return cache statistics.

        Counts both compressed (.json.gz) and legacy (.json) files.

        Returns:
            Dict with file_count, total_bytes, and recent days.
        """
        files = []

        # Collect both compressed and legacy files
        for pattern in ("*.json.gz", "*.json"):
            for f in self.base_dir.rglob(pattern):
                try:
                    # File may be deleted by another process; skip if gone
                    if f.is_file():
                        files.append(f)
                except FileNotFoundError:
                    continue

        total = 0
        for f in files:
            try:
                total += f.stat().st_size
            except FileNotFoundError:
                # File deleted between is_file() check and stat(); skip
                continue

        days = sorted({f.parent.name for f in files if f.parent.name})
        return {
            "file_count": len(files),
            "total_bytes": total,
            "days_present": days[-14:],  # last 14 days
        }

    def clear_older_than(self, days: int = 30) -> int:
        """Remove cache entries older than N days.

        Removes both compressed (.json.gz) and legacy (.json) files.

        Args:
            days: remove entries older than this many days

        Returns:
            Count of removed files.
        """
        cutoff = _dt.date.today() - _dt.timedelta(days=days)
        removed = 0

        for day_dir in self.base_dir.iterdir():
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
                        except FileNotFoundError:
                            # File deleted by another process; skip
                            continue
                        except Exception as e:
                            log.warning("failed to remove cache file %s: %s", f, e)

                with contextlib.suppress(OSError):
                    day_dir.rmdir()

        return removed


# ─── Module-level singleton accessor ─────────────────────────────────────────
_cache_singleton: CacheStore | None = None


def get_cache() -> CacheStore:
    """Return the process-wide CacheStore singleton.

    Honors LOOM_CACHE_DIR on first access. Subsequent callers share the same
    instance so cache stats are consistent across tool invocations.
    """
    global _cache_singleton
    if _cache_singleton is None:
        _cache_singleton = CacheStore()
    return _cache_singleton
