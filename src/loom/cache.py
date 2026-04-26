"""Content-hash cache with atomic writes and daily directory structure.

Provides a CacheStore class for managing cached responses by content-hash
(SHA-256), organized by date for easy TTL cleanup.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
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
    """Content-hash cache with atomic writes and daily directory structure.

    Stores JSON blobs indexed by content-hash (SHA-256), organized under
    daily directories for easy TTL pruning. Uses atomic writes (uuid tmp +
    os.replace) to prevent corruption from concurrent writers.
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
        so entries from previous days still produce cache hits.

        Args:
            key: cache key

        Returns:
            Cached dict if found and valid JSON, None otherwise.
        """
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        filename = f"{h}.json"

        # Fast path: check today's directory
        p = self._cache_path(key)
        if p.exists():
            try:
                return cast(dict[str, Any] | None, json.loads(p.read_text(encoding="utf-8")))
            except Exception as e:
                log.debug("cache_get_failed key=%s: %s", key, e)
                return None

        # Slow path: search all date directories (newest first)
        try:
            matches = sorted(self.base_dir.glob(f"*/{filename}"), reverse=True)
            for match in matches:
                try:
                    return cast(dict[str, Any] | None, json.loads(match.read_text(encoding="utf-8")))
                except Exception:
                    continue
        except Exception as e:
            log.debug("cache_glob_failed key=%s: %s", key, e)

        return None

    def put(self, key: str, value: dict[str, Any]) -> None:
        """Store value in cache with atomic write.

        Uses uuid-suffixed temp file + os.replace to ensure atomic,
        concurrent-safe writes (even within the same process).

        Args:
            key: cache key
            value: dict to store (must be JSON-serializable)

        Raises:
            Exception: if JSON encoding fails or disk I/O fails
        """
        p = self._cache_path(key)
        tmp = p.with_suffix(p.suffix + f".tmp-{uuid.uuid4().hex}")
        try:
            tmp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            os.replace(tmp, p)
        except Exception:
            log.exception("cache_put_failed key=%s", key)
            if tmp.exists():
                with contextlib.suppress(Exception):
                    tmp.unlink()
            raise

    def stats(self) -> dict[str, Any]:
        """Return cache statistics.

        Returns:
            Dict with file_count, total_bytes, and recent days.
        """
        files = list(self.base_dir.rglob("*.json"))
        total = sum(f.stat().st_size for f in files)
        days = sorted({f.parent.name for f in files})
        return {
            "file_count": len(files),
            "total_bytes": total,
            "days_present": days[-14:],  # last 14 days
        }

    def clear_older_than(self, days: int = 30) -> int:
        """Remove cache entries older than N days.

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
                for f in day_dir.glob("*.json"):
                    try:
                        f.unlink()
                        removed += 1
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
