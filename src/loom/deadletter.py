"""Persistent deadletter queue for failed tool calls.

Provides DeadletterQueue class for managing failed tool calls with:
- SQLite-backed persistence
- Exponential backoff retry scheduling (60s, 300s, 1800s)
- Background async worker for retry processing
- Statistics and monitoring
- Atomic operations for reliability
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

log = logging.getLogger("loom.deadletter")


class DeadletterQueue:
    """Persistent deadletter queue for failed tool calls with exponential backoff.

    Stores failed tool calls in SQLite with retry tracking. Uses exponential
    backoff for next_retry_at scheduling. Supports background worker for
    automatic retry processing.

    Attributes:
        db_path: Path to SQLite database file
        max_retries: Maximum retry attempts before moving to permanent failure
        backoff_schedule: Tuple of retry delays in seconds
    """

    # Exponential backoff schedule: 60s, 300s (5m), 1800s (30m)
    BACKOFF_SCHEDULE = (60, 300, 1800)
    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self,
        db_path: str | Path | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        """Initialize deadletter queue.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.cache/loom/dlq.db
            max_retries: Maximum retry attempts before permanent failure
        """
        if db_path is None:
            db_path = str(Path.home() / ".cache" / "loom" / "dlq.db")

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_retries = max_retries
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite schema with pending and failed tables."""
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dlq_pending (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    error TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    next_retry_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS dlq_failed (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tool_name TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    error TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    failed_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            # Indexes for common queries
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dlq_pending_retry ON dlq_pending(next_retry_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dlq_pending_tool ON dlq_pending(tool_name)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_dlq_failed_tool ON dlq_failed(tool_name)"
            )
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with row factory."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _calculate_next_retry(retry_count: int, backoff_schedule: tuple[int, ...]) -> str:
        """Calculate next retry timestamp using exponential backoff.

        Args:
            retry_count: Current retry attempt number (0-based)
            backoff_schedule: Tuple of backoff delays in seconds

        Returns:
            ISO 8601 timestamp string for next retry
        """
        if retry_count < len(backoff_schedule):
            delay_seconds = backoff_schedule[retry_count]
        else:
            delay_seconds = backoff_schedule[-1]

        next_retry = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        return next_retry.isoformat()

    def enqueue(
        self,
        tool_name: str,
        params: dict[str, Any],
        error: str,
        max_retries: int | None = None,
    ) -> int:
        """Enqueue a failed tool call for retry.

        Args:
            tool_name: Name of the tool that failed
            params: Tool parameters as dict
            error: Error message from the failure
            max_retries: Override default max_retries for this item

        Returns:
            DLQ item ID for later reference

        Raises:
            ValueError: If parameters cannot be JSON serialized
        """
        try:
            params_json = json.dumps(params)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Cannot serialize params to JSON: {e}") from e

        retry_count = 0
        next_retry_at = self._calculate_next_retry(retry_count, self.BACKOFF_SCHEDULE)
        now_iso = datetime.now(UTC).isoformat()

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO dlq_pending
                    (tool_name, params_json, error, retry_count, next_retry_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (tool_name, params_json, error, retry_count, next_retry_at, now_iso, now_iso),
                )
                conn.commit()
                dlq_id = cursor.lastrowid

        log.info(f"enqueue dlq_id={dlq_id} tool={tool_name} error={error[:50]}")
        return dlq_id

    def dequeue(self, limit: int = 10) -> list[dict[str, Any]]:
        """Dequeue items ready for retry.

        Retrieves pending items where next_retry_at <= now, up to limit.
        Does not modify the items (still in pending table).

        Args:
            limit: Maximum number of items to return

        Returns:
            List of dicts with id, tool_name, params_json, error, retry_count
        """
        now_iso = datetime.now(UTC).isoformat()

        with self._lock:
            with self._get_connection() as conn:
                rows = conn.execute(
                    """
                    SELECT id, tool_name, params_json, error, retry_count
                    FROM dlq_pending
                    WHERE next_retry_at <= ?
                    ORDER BY next_retry_at ASC
                    LIMIT ?
                    """,
                    (now_iso, limit),
                ).fetchall()

        items = [dict(row) for row in rows]
        if items:
            log.debug(f"dequeue count={len(items)} limit={limit}")

        return items

    def mark_success(self, dlq_id: int) -> bool:
        """Remove item from queue after successful retry.

        Args:
            dlq_id: ID of the DLQ item to remove

        Returns:
            True if item was removed, False if not found
        """
        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM dlq_pending WHERE id = ?",
                    (dlq_id,),
                )
                conn.commit()
                deleted = cursor.rowcount > 0

        if deleted:
            log.info(f"mark_success dlq_id={dlq_id}")

        return deleted

    def mark_permanent_failure(self, dlq_id: int) -> bool:
        """Move item to failed table after max retries exceeded.

        Args:
            dlq_id: ID of the DLQ item to move

        Returns:
            True if item was moved, False if not found
        """
        tool_name = None
        with self._lock:
            with self._get_connection() as conn:
                # Get item from pending
                row = conn.execute(
                    "SELECT tool_name, params_json, error, retry_count, created_at FROM dlq_pending WHERE id = ?",
                    (dlq_id,),
                ).fetchone()

                if not row:
                    return False

                tool_name = row["tool_name"]
                # Move to failed
                now_iso = datetime.now(UTC).isoformat()
                conn.execute(
                    """
                    INSERT INTO dlq_failed
                    (tool_name, params_json, error, retry_count, failed_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (row["tool_name"], row["params_json"], row["error"], row["retry_count"], now_iso, row["created_at"]),
                )
                conn.execute("DELETE FROM dlq_pending WHERE id = ?", (dlq_id,))
                conn.commit()

        log.warning(f"permanent_failure dlq_id={dlq_id} tool={tool_name}")
        return True

    def increment_retry_count(self, dlq_id: int) -> bool:
        """Increment retry count for an item and update next_retry_at.

        Args:
            dlq_id: ID of the DLQ item

        Returns:
            True if item was updated, False if not found
        """
        with self._lock:
            with self._get_connection() as conn:
                # Get current retry count
                row = conn.execute(
                    "SELECT retry_count FROM dlq_pending WHERE id = ?",
                    (dlq_id,),
                ).fetchone()

                if not row:
                    return False

                retry_count = row["retry_count"]
                new_retry_count = retry_count + 1
                next_retry_at = self._calculate_next_retry(new_retry_count, self.BACKOFF_SCHEDULE)
                now_iso = datetime.now(UTC).isoformat()

                conn.execute(
                    """
                    UPDATE dlq_pending
                    SET retry_count = ?, next_retry_at = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (new_retry_count, next_retry_at, now_iso, dlq_id),
                )
                conn.commit()

        return True

    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics.

        Returns dict with:
            - pending: Count of items awaiting retry
            - failed: Count of items in permanent failure table
            - total_retried: Total retry attempts across all items
            - avg_retry_count: Average retries per pending item
            - oldest_pending: ISO timestamp of oldest pending item
        """
        with self._lock:
            with self._get_connection() as conn:
                # Pending count
                pending = conn.execute(
                    "SELECT COUNT(*) as count FROM dlq_pending"
                ).fetchone()["count"]

                # Failed count
                failed = conn.execute(
                    "SELECT COUNT(*) as count FROM dlq_failed"
                ).fetchone()["count"]

                # Total retry attempts
                total_retried = conn.execute(
                    "SELECT COALESCE(SUM(retry_count), 0) as total FROM dlq_pending"
                ).fetchone()["total"]

                # Average retry count
                avg_retry = conn.execute(
                    "SELECT COALESCE(AVG(retry_count), 0.0) as avg FROM dlq_pending"
                ).fetchone()["avg"]

                # Oldest pending
                oldest = conn.execute(
                    "SELECT MIN(created_at) as oldest FROM dlq_pending"
                ).fetchone()["oldest"]

        return {
            "pending": pending,
            "failed": failed,
            "total_retried": total_retried,
            "avg_retry_count": round(avg_retry, 2),
            "oldest_pending": oldest,
        }

    def get_items_by_tool(self, tool_name: str, include_failed: bool = False) -> list[dict[str, Any]]:
        """Get all items for a specific tool.

        Args:
            tool_name: Name of the tool
            include_failed: If True, include failed items; else pending only

        Returns:
            List of dicts with item details
        """
        with self._lock:
            with self._get_connection() as conn:
                if include_failed:
                    rows = conn.execute(
                        """
                        SELECT 'pending' as status, id, tool_name, params_json, error, retry_count, created_at
                        FROM dlq_pending WHERE tool_name = ?
                        UNION ALL
                        SELECT 'failed' as status, id, tool_name, params_json, error, retry_count, created_at
                        FROM dlq_failed WHERE tool_name = ?
                        """,
                        (tool_name, tool_name),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT 'pending' as status, id, tool_name, params_json, error, retry_count, created_at
                        FROM dlq_pending WHERE tool_name = ?
                        """,
                        (tool_name,),
                    ).fetchall()

        return [dict(row) for row in rows]

    def cleanup_old_failed(self, days: int = 30) -> int:
        """Remove old failed items to prevent table bloat.

        Args:
            days: Remove failed items older than this many days

        Returns:
            Number of rows deleted
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM dlq_failed WHERE failed_at < ?",
                    (cutoff_iso,),
                )
                conn.commit()
                deleted = cursor.rowcount

        if deleted > 0:
            log.info(f"cleanup_old_failed days={days} deleted={deleted}")

        return deleted


class DeadletterQueueWorker:
    """Background worker for automatic retry processing."""

    def __init__(
        self,
        dlq: DeadletterQueue,
        tool_executor: callable,
        poll_interval: int = 60,
    ):
        """Initialize DLQ worker.

        Args:
            dlq: DeadletterQueue instance
            tool_executor: Async callable(tool_name, params) -> result
            poll_interval: Seconds between poll cycles
        """
        self.dlq = dlq
        self.tool_executor = tool_executor
        self.poll_interval = poll_interval
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def start(self) -> None:
        """Start background worker task."""
        if self._running:
            log.warning("worker already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        log.info(f"worker started poll_interval={self.poll_interval}")

    async def stop(self) -> None:
        """Stop background worker task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("worker stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop for retry processing."""
        while self._running:
            try:
                await asyncio.sleep(self.poll_interval)
                await self._process_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"worker error: {str(e)}", exc_info=True)

    async def _process_batch(self) -> None:
        """Process one batch of ready-to-retry items."""
        items = self.dlq.dequeue(limit=10)
        if not items:
            return

        for item in items:
            dlq_id = item["id"]
            tool_name = item["tool_name"]
            params = json.loads(item["params_json"])
            retry_count = item["retry_count"]

            try:
                result = await self.tool_executor(tool_name, params)
                self.dlq.mark_success(dlq_id)
                log.info(f"retry_success dlq_id={dlq_id} tool={tool_name} retry={retry_count}")
            except Exception as e:
                if retry_count >= self.dlq.max_retries:
                    self.dlq.mark_permanent_failure(dlq_id)
                    log.warning(f"retry_permanent_fail dlq_id={dlq_id} tool={tool_name} retry={retry_count} error={str(e)[:80]}")
                else:
                    self.dlq.increment_retry_count(dlq_id)
                    log.debug(f"retry_failed dlq_id={dlq_id} tool={tool_name} retry={retry_count} error={str(e)[:80]}")


# Global singleton instance
_dlq_instance: DeadletterQueue | None = None
_dlq_lock = threading.Lock()


def get_dlq() -> DeadletterQueue:
    """Get or create global DeadletterQueue singleton.

    Returns:
        DeadletterQueue instance
    """
    global _dlq_instance
    if _dlq_instance is None:
        with _dlq_lock:
            if _dlq_instance is None:
                _dlq_instance = DeadletterQueue()
    return _dlq_instance
