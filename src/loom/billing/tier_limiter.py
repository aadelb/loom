"""Per-tier rate limiting for subscription tiers.

Rate limits are enforced per customer per subscription tier:
- Free: 10 requests/minute
- Pro: 60 requests/minute
- Team: 300 requests/minute
- Enterprise: 1000 requests/minute

Implements a sliding-window counter in memory with optional
SQLite persistence across restarts.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.billing.tier_limiter")

# Rate limits per tier (requests per minute)
TIER_LIMITS: dict[str, int] = {
    "free": 10,
    "pro": 60,
    "team": 300,
    "enterprise": 1000,
}

WINDOW_SECONDS: int = 60  # 1-minute sliding window


def _get_persistence_db() -> Path | None:
    """Get the path to the tier rate limit persistence database if enabled.

    Returns None if persistence is disabled, otherwise returns the DB path.
    """
    from loom.config import get_config

    cfg = get_config()
    if not cfg.get("RATE_LIMIT_PERSIST", False):
        return None

    db_dir = Path.home() / ".loom"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "tier_rate_limits.db"


def _init_persistence_db(db_path: Path) -> None:
    """Initialize the tier rate limit persistence database."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tier_rate_limits (
                customer_id TEXT NOT NULL,
                tier TEXT NOT NULL,
                timestamp REAL NOT NULL,
                PRIMARY KEY (customer_id, tier, timestamp)
            )
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Failed to initialize tier persistence DB: %s", e)


def _load_from_db(
    db_path: Path, customer_id: str, tier: str, window_seconds: int
) -> list[float]:
    """Load timestamps for a customer from the database (within the window)."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        now = time.time()
        cutoff = now - window_seconds

        cursor.execute(
            "SELECT timestamp FROM tier_rate_limits WHERE customer_id = ? AND tier = ? AND timestamp > ? ORDER BY timestamp",
            (customer_id, tier, cutoff),
        )
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows]
    except Exception as e:
        logger.warning("Failed to load from tier persistence DB: %s", e)
        return []


def _save_to_db(
    db_path: Path, customer_id: str, tier: str, timestamp: float
) -> None:
    """Save a single timestamp to the database."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO tier_rate_limits (customer_id, tier, timestamp) VALUES (?, ?, ?)",
            (customer_id, tier, timestamp),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("Failed to save to tier persistence DB: %s", e)


def _cleanup_old_entries(db_path: Path, window_seconds: int) -> None:
    """Remove old entries from the database (>window_seconds old)."""
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        cutoff = time.time() - window_seconds
        cursor.execute(
            "DELETE FROM tier_rate_limits WHERE timestamp <= ?", (cutoff,)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning("Failed to cleanup old tier entries: %s", e)


class TierRateLimiter:
    """Rate limiter that enforces per-tier per-customer limits.

    Uses a sliding-window counter with optional SQLite persistence.
    Thread-safe via threading.Lock.

    Example:
        limiter = TierRateLimiter()
        result = limiter.check("customer_123", "pro")
        if not result["allowed"]:
            return {"error": "rate_limit_exceeded", "retry_after": result["retry_after"]}
    """

    def __init__(self) -> None:
        """Initialize the tier rate limiter."""
        self._windows: dict[str, list[float]] = {}  # customer_id -> timestamps
        self._lock = threading.Lock()
        self._db_path = _get_persistence_db()
        if self._db_path:
            _init_persistence_db(self._db_path)

    def check(self, customer_id: str, tier: str) -> dict[str, Any]:
        """Check if customer can make a request for their tier.

        Args:
            customer_id: Unique identifier for the customer/user
            tier: Subscription tier (free, pro, team, enterprise)

        Returns:
            Dictionary with keys:
            - allowed: True if request is allowed, False if rate limited
            - remaining: Number of requests remaining in current window
            - limit: Total request limit for this tier
            - retry_after: Seconds to wait before retrying (0 if allowed)
            - tier: The subscription tier that was checked
        """
        with self._lock:
            # Get limit for tier, default to free tier if unknown
            limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
            now = time.time()
            window_start = now - WINDOW_SECONDS

            # Build cache key
            key = customer_id

            # Load from DB if persistence is enabled
            if self._db_path:
                db_timestamps = _load_from_db(
                    self._db_path, customer_id, tier, WINDOW_SECONDS
                )
                window = [t for t in db_timestamps if t > window_start]
            else:
                if key not in self._windows:
                    self._windows[key] = []
                window = [t for t in self._windows[key] if t > window_start]

            current = len(window)

            # If at or above limit, return rate limited response
            if current >= limit:
                # Calculate retry_after: time until oldest request leaves the window
                oldest = min(window) if window else now
                retry_after = int(WINDOW_SECONDS - (now - oldest)) + 1
                retry_after = max(1, retry_after)

                logger.debug(
                    "rate_limit_exceeded customer=%s tier=%s current=%d limit=%d",
                    customer_id,
                    tier,
                    current,
                    limit,
                )

                return {
                    "allowed": False,
                    "remaining": 0,
                    "limit": limit,
                    "retry_after": retry_after,
                    "tier": tier,
                }

            # Request is allowed, record timestamp
            window.append(now)

            # Update in-memory cache
            if not self._db_path:
                self._windows[key] = window

            # Save to DB if persistence is enabled
            if self._db_path:
                _save_to_db(self._db_path, customer_id, tier, now)
                _cleanup_old_entries(self._db_path, WINDOW_SECONDS)

            # Prune empty keys from in-memory store to prevent memory leak
            if not self._db_path:
                empty_keys = [k for k, v in self._windows.items() if not v]
                for k in empty_keys:
                    del self._windows[k]

            logger.debug(
                "rate_limit_allowed customer=%s tier=%s current=%d limit=%d",
                customer_id,
                tier,
                current + 1,
                limit,
            )

            return {
                "allowed": True,
                "remaining": limit - current - 1,
                "limit": limit,
                "retry_after": 0,
                "tier": tier,
            }

    def reset(self, customer_id: str) -> None:
        """Reset rate limit for a customer across all tiers.

        Args:
            customer_id: The customer ID to reset
        """
        with self._lock:
            if customer_id in self._windows:
                del self._windows[customer_id]
            logger.debug("rate_limit_reset customer=%s", customer_id)

    def get_remaining(self, customer_id: str, tier: str) -> int:
        """Get remaining requests for a customer in their tier.

        Args:
            customer_id: Unique identifier for the customer/user
            tier: Subscription tier (free, pro, team, enterprise)

        Returns:
            Number of requests remaining (0 if at/above limit)
        """
        with self._lock:
            limit = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
            now = time.time()
            window_start = now - WINDOW_SECONDS

            if self._db_path:
                db_timestamps = _load_from_db(
                    self._db_path, customer_id, tier, WINDOW_SECONDS
                )
                window = [t for t in db_timestamps if t > window_start]
            else:
                key = customer_id
                if key not in self._windows:
                    return limit
                window = [t for t in self._windows[key] if t > window_start]

            return max(0, limit - len(window))


# Global instance
_tier_limiter: TierRateLimiter | None = None


def get_tier_limiter() -> TierRateLimiter:
    """Get or create the global tier rate limiter instance."""
    global _tier_limiter
    if _tier_limiter is None:
        _tier_limiter = TierRateLimiter()
    return _tier_limiter


def reset_all() -> None:
    """Reset all customer limits (for tests)."""
    global _tier_limiter
    if _tier_limiter is not None:
        _tier_limiter._windows.clear()
        _tier_limiter = None
