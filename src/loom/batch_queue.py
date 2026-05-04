"""Batch processing queue for non-time-sensitive queries.

Provides a BatchQueue class that manages a persistent queue of tool invocations
stored in SQLite, with configurable concurrency and background processing.

Public API:
    BatchQueue              Main batch queue class
    get_batch_queue()       Singleton accessor
    research_batch_submit   MCP tool: submit job to batch queue
    research_batch_status   MCP tool: check job status
    research_batch_list     MCP tool: list recent batch items
"""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import random
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field, field_validator

from loom.validators import UrlSafetyError, validate_url

logger = logging.getLogger("loom.batch_queue")

# Constraints
DEFAULT_BATCH_CONCURRENCY = 5
MAX_BATCH_ITEMS_PER_LIST = 100
BATCH_QUEUE_FILE = Path.home() / ".cache" / "loom" / "batch_queue.db"
BATCH_BACKGROUND_INTERVAL_SECS = 10

# Exponential backoff configuration
RETRY_DELAYS = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hr


def _get_retry_delay(retry_count: int) -> int:
    """Calculate retry delay with exponential backoff.

    Args:
        retry_count: number of retries already attempted (0-indexed)

    Returns:
        delay in seconds; caps at 1 hour
    """
    if retry_count < len(RETRY_DELAYS):
        base_delay = RETRY_DELAYS[retry_count]
    else:
        base_delay = RETRY_DELAYS[-1]

    # Add jitter: ±10% of base delay
    jitter = random.uniform(0, base_delay * 0.1)
    return int(base_delay + jitter)


@dataclass
class BatchItem:
    """Represents a single batch queue item.

    Fields:
        id: unique batch job ID (UUID4)
        tool_name: name of the MCP tool to invoke
        params_json: JSON-encoded tool parameters
        status: current status (pending/processing/done/failed)
        result_json: JSON-encoded result (null until completed)
        error_message: error detail if status is 'failed'
        created_at: timestamp when submitted
        started_at: timestamp when processing started
        completed_at: timestamp when processing finished
        retry_count: number of retry attempts
        max_retries: maximum number of retries (default 3)
        next_retry_at: unix timestamp when next retry is eligible (null = ready now)
        callback_url: optional callback URL for webhook notification
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    params_json: str = ""
    status: Literal["pending", "processing", "done", "failed"] = "pending"
    result_json: str | None = None
    error_message: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    started_at: str | None = None
    completed_at: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: float | None = None
    callback_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)


class BatchSubmitParams(BaseModel):
    """Parameters for research_batch_submit tool."""

    tool_name: str = Field(..., min_length=1, max_length=256)
    params: dict[str, Any] = Field(default_factory=dict)
    callback_url: str | None = Field(default=None, max_length=2048)
    max_retries: int = Field(default=3, ge=0, le=10)

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name format."""
        if not v.replace("_", "").isalnum():
            raise ValueError("tool_name must be alphanumeric with underscores")
        return v

    @field_validator("callback_url")
    @classmethod
    def validate_callback_url(cls, v: str | None) -> str | None:
        """Validate callback URL format."""
        if v is None:
            return v
        if not v.startswith(("http://", "https://")):
            raise ValueError("callback_url must start with http:// or https://")
        return v


class BatchStatusParams(BaseModel):
    """Parameters for research_batch_status tool."""

    batch_id: str = Field(..., min_length=36, max_length=36)

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("batch_id")
    @classmethod
    def validate_batch_id(cls, v: str) -> str:
        """Validate batch ID is UUID4 format."""
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError("batch_id must be valid UUID4")
        return v


class BatchListParams(BaseModel):
    """Parameters for research_batch_list tool."""

    limit: int = Field(default=20, ge=1, le=MAX_BATCH_ITEMS_PER_LIST)
    status_filter: Literal["all", "pending", "processing", "done", "failed"] = Field(default="all")
    offset: int = Field(default=0, ge=0)

    model_config = {"extra": "forbid", "strict": True}


class BatchQueue:
    """Manages a persistent batch queue for non-time-sensitive tool invocations.

    Uses SQLite for persistence with atomic transactions. Supports:
    - Submitting jobs with custom parameters
    - Checking job status
    - Background processing with configurable concurrency
    - Automatic retries on failure with exponential backoff
    - Optional webhook callbacks on completion
    """

    def __init__(
        self,
        db_path: Path = BATCH_QUEUE_FILE,
        concurrency: int = DEFAULT_BATCH_CONCURRENCY,
    ) -> None:
        """Initialize batch queue.

        Args:
            db_path: path to SQLite database file
            concurrency: max concurrent processing jobs (default 5)
        """
        self.db_path = Path(db_path)
        self.concurrency = max(1, min(concurrency, 20))
        self._processing_count = 0
        self._lock = asyncio.Lock()
        self._tool_registry: dict[str, Callable[[dict[str, Any]], Any]] = {}
        self._init_db()
        self._auto_register_tools()

    def _init_db(self) -> None:
        """Initialize SQLite schema if not exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS batch_items (
                    id TEXT PRIMARY KEY,
                    tool_name TEXT NOT NULL,
                    params_json TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    result_json TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    max_retries INTEGER NOT NULL DEFAULT 3,
                    next_retry_at REAL,
                    callback_url TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status ON batch_items(status)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_created_at ON batch_items(created_at DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_next_retry_at ON batch_items(next_retry_at)
                """
            )
            conn.commit()


    def _auto_register_tools(self) -> None:
        """Auto-register all research_* tools from loom.tools for batch execution.

        Dynamically discovers and imports all research_* functions from tool modules,
        making them available for batch queue execution. Silently skips modules that
        fail to import (e.g., missing dependencies).
        """
        tools_dir = Path(__file__).parent / "tools"
        if not tools_dir.exists():
            logger.warning("tools_dir not found: %s", tools_dir)
            return

        registered_count = 0
        failed_modules = []

        for module_file in sorted(tools_dir.glob("*.py")):
            # Skip private/dunder files
            if module_file.name.startswith("_"):
                continue

            module_name = module_file.stem
            try:
                # Dynamically import the module
                mod = importlib.import_module(f"loom.tools.{module_name}")

                # Scan for functions starting with research_
                for attr_name in dir(mod):
                    if attr_name.startswith("research_"):
                        try:
                            attr = getattr(mod, attr_name)
                            # Verify it's callable
                            if callable(attr):
                                self._tool_registry[attr_name] = attr
                                registered_count += 1
                        except (AttributeError, TypeError):
                            # Skip non-callable attributes
                            pass

            except ImportError as e:
                failed_modules.append((module_name, str(e)))
                # Silently skip modules with import errors (optional dependencies)
            except Exception as e:
                logger.debug(
                    "batch_tool_registration_error module=%s error=%s",
                    module_name,
                    str(e),
                )

        logger.info(
            "batch_queue_auto_register_tools registered=%d failed_modules=%d",
            registered_count,
            len(failed_modules),
        )

        if failed_modules and logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "batch_queue_skipped_modules due to import errors: %s",
                [name for name, _ in failed_modules[:5]],
            )

    def register_tool(self, tool_name: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        """Register a tool handler for batch processing.

        Args:
            tool_name: name of the tool
            handler: callable that takes params dict and returns result
        """
        self._tool_registry[tool_name] = handler

    def submit(
        self,
        tool_name: str,
        params: dict[str, Any],
        callback_url: str | None = None,
        max_retries: int = 3,
    ) -> str:
        """Submit a job to the batch queue.

        Args:
            tool_name: name of the tool to invoke
            params: tool parameters as dict
            callback_url: optional webhook URL to notify on completion
            max_retries: maximum retry attempts on failure (0-10)

        Returns:
            batch_id (UUID4 string)

        Raises:
            ValueError: if tool_name is empty or params not a dict
        """
        if not tool_name or not isinstance(params, dict):
            raise ValueError("tool_name must be non-empty string, params must be dict")

        batch_id = str(uuid.uuid4())
        item = BatchItem(
            id=batch_id,
            tool_name=tool_name,
            params_json=json.dumps(params, default=str),
            callback_url=callback_url,
            max_retries=max(0, min(max_retries, 10)),
            next_retry_at=None,  # Ready to process immediately
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO batch_items (
                    id, tool_name, params_json, status, created_at, max_retries,
                    next_retry_at, callback_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.id,
                    item.tool_name,
                    item.params_json,
                    item.status,
                    item.created_at,
                    item.max_retries,
                    item.next_retry_at,
                    item.callback_url,
                ),
            )
            conn.commit()

        logger.info("batch_submitted batch_id=%s tool=%s", batch_id, tool_name)
        return batch_id

    def get_status(self, batch_id: str) -> dict[str, Any]:
        """Get status of a batch job.

        Args:
            batch_id: the batch item ID

        Returns:
            dict with keys: id, tool_name, status, result, error_message,
                           created_at, started_at, completed_at, retry_count

        Raises:
            ValueError: if batch_id not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM batch_items WHERE id = ?",
                (batch_id,),
            ).fetchone()

        if not row:
            raise ValueError(f"batch_id not found: {batch_id}")

        result = None
        if row["result_json"]:
            try:
                result = json.loads(row["result_json"])
            except json.JSONDecodeError:
                result = row["result_json"]

        return {
            "id": row["id"],
            "tool_name": row["tool_name"],
            "status": row["status"],
            "result": result,
            "error_message": row["error_message"],
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "retry_count": row["retry_count"],
        }

    def list_items(
        self,
        limit: int = 20,
        status_filter: Literal["all", "pending", "processing", "done", "failed"] = "all",
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List batch items with optional filtering.

        Args:
            limit: max items to return (1-100)
            status_filter: filter by status ('all', 'pending', 'processing', 'done', 'failed')
            offset: pagination offset

        Returns:
            list of batch item dicts ordered by created_at DESC
        """
        limit = max(1, min(limit, MAX_BATCH_ITEMS_PER_LIST))
        offset = max(0, offset)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM batch_items"
            params: list[Any] = []

            if status_filter != "all":
                query += " WHERE status = ?"
                params.append(status_filter)

            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()

        items = []
        for row in rows:
            result = None
            if row["result_json"]:
                try:
                    result = json.loads(row["result_json"])
                except json.JSONDecodeError:
                    result = row["result_json"]

            items.append(
                {
                    "id": row["id"],
                    "tool_name": row["tool_name"],
                    "status": row["status"],
                    "result": result,
                    "error_message": row["error_message"],
                    "created_at": row["created_at"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                    "retry_count": row["retry_count"],
                }
            )

        return items

    async def process_pending(self) -> int:
        """Process pending batch items (called by background worker).

        Fetches up to `concurrency` pending items and processes them in parallel
        using asyncio.gather(). Items are locked to 'processing' status, executed
        via registered handler, and marked as 'done' or 'failed'.

        Only processes items where next_retry_at is NULL or <= current time.

        Returns:
            number of items processed in this call
        """
        async with self._lock:
            # Calculate available slots
            available_slots = self.concurrency - self._processing_count
            if available_slots <= 0:
                return 0

            # Fetch up to available_slots pending items that are ready to retry
            current_time = time.time()
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    """
                    SELECT * FROM batch_items
                    WHERE status = 'pending'
                    AND (next_retry_at IS NULL OR next_retry_at <= ?)
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (current_time, available_slots),
                ).fetchall()

                if not rows:
                    return 0

                # Lock all items to 'processing'
                batch_ids = [row["id"] for row in rows]
                now_iso = datetime.now(UTC).isoformat()
                for batch_id in batch_ids:
                    conn.execute(
                        """
                        UPDATE batch_items
                        SET status = 'processing', started_at = ?
                        WHERE id = ?
                        """,
                        (now_iso, batch_id),
                    )
                conn.commit()

                # Extract row data before closing connection
                items_to_process = [
                    {
                        "id": row["id"],
                        "tool_name": row["tool_name"],
                        "params_json": row["params_json"],
                        "retry_count": row["retry_count"],
                        "max_retries": row["max_retries"],
                        "callback_url": row["callback_url"],
                    }
                    for row in rows
                ]

            self._processing_count += len(items_to_process)

        # Process all items concurrently
        tasks = [self._process_single_item(item) for item in items_to_process]
        await asyncio.gather(*tasks)

        return len(items_to_process)

    async def _process_single_item(self, item: dict[str, Any]) -> None:
        """Process a single batch item.

        Args:
            item: dict with id, tool_name, params_json, retry_count, max_retries, callback_url
        """
        batch_id = item["id"]
        tool_name = item["tool_name"]
        params_json = item["params_json"]
        retry_count = item["retry_count"]
        max_retries = item["max_retries"]
        callback_url = item["callback_url"]

        try:
            # Decode params
            try:
                params = json.loads(params_json)
            except json.JSONDecodeError as e:
                raise ValueError(f"invalid params_json: {e}") from e

            # Execute tool
            result = None
            error_msg = None

            if tool_name in self._tool_registry:
                try:
                    handler = self._tool_registry[tool_name]
                    result = await self._call_handler(handler, params)
                except Exception as e:
                    error_msg = f"{type(e).__name__}: {str(e)}"
                    logger.error(
                        "batch_execution_failed batch_id=%s tool=%s error=%s",
                        batch_id,
                        tool_name,
                        error_msg,
                    )
            else:
                error_msg = f"tool not registered: {tool_name}"
                logger.warning("batch_tool_not_found tool=%s", tool_name)

            # Determine final status
            if error_msg and retry_count < max_retries:
                # Retry: set next_retry_at with exponential backoff
                delay_secs = _get_retry_delay(retry_count)
                next_retry_time = time.time() + delay_secs

                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        UPDATE batch_items
                        SET status = 'pending', retry_count = ?, next_retry_at = ?,
                            started_at = NULL
                        WHERE id = ?
                        """,
                        (retry_count + 1, next_retry_time, batch_id),
                    )
                    conn.commit()

                logger.info(
                    "batch_retry batch_id=%s retry_count=%d/%d delay_secs=%d",
                    batch_id,
                    retry_count + 1,
                    max_retries,
                    delay_secs,
                )
            else:
                # Final: done or failed
                final_status = "done" if not error_msg else "failed"
                result_json = json.dumps(result, default=str) if result is not None else None

                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        """
                        UPDATE batch_items
                        SET status = ?, result_json = ?, error_message = ?,
                            completed_at = ?, next_retry_at = NULL
                        WHERE id = ?
                        """,
                        (
                            final_status,
                            result_json,
                            error_msg,
                            datetime.now(UTC).isoformat(),
                            batch_id,
                        ),
                    )
                    conn.commit()

                log_level = "info" if final_status == "done" else "error"
                logger.log(
                    logging.INFO if log_level == "info" else logging.ERROR,
                    "batch_completed batch_id=%s status=%s",
                    batch_id,
                    final_status,
                )

                # Trigger callback if configured
                if callback_url:
                    await self._trigger_callback(callback_url, batch_id, final_status, result, error_msg)

        finally:
            async with self._lock:
                self._processing_count -= 1

    @staticmethod
    async def _call_handler(handler: Callable[[dict[str, Any]], Any], params: dict[str, Any]) -> Any:
        """Call handler, supporting both sync and async functions.

        Args:
            handler: callable to invoke
            params: parameters to pass

        Returns:
            result from handler
        """
        if asyncio.iscoroutinefunction(handler):
            return await handler(params)
        else:
            # Run sync function in executor to avoid blocking
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, handler, params)

    @staticmethod
    async def _trigger_callback(
        callback_url: str, batch_id: str, status: str, result: Any, error_msg: str | None
    ) -> None:
        """Trigger webhook callback on completion.

        Validates the callback URL against SSRF before making the request.
        Blocks private IPs, loopback, link-local, multicast, reserved, and
        unspecified addresses. Logs security events if validation fails.

        Args:
            callback_url: webhook URL
            batch_id: batch ID
            status: final status
            result: execution result
            error_msg: error message if failed
        """
        # SSRF validation: reject private/internal IPs
        try:
            validate_url(callback_url)
        except UrlSafetyError as e:
            logger.warning(
                "callback_ssrf_blocked batch_id=%s url=%s error=%s",
                batch_id,
                callback_url,
                str(e),
            )
            return  # Skip callback

        try:
            import aiohttp

            payload = {
                "batch_id": batch_id,
                "status": status,
                "result": result,
                "error_message": error_msg,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(callback_url, json=payload, timeout=10) as resp:
                    if resp.status < 200 or resp.status >= 300:
                        logger.warning(
                            "callback_failed batch_id=%s url=%s status=%d",
                            batch_id,
                            callback_url,
                            resp.status,
                        )
        except Exception as e:
            logger.error("callback_exception batch_id=%s error=%s", batch_id, e)


# Global singleton instance
_batch_queue: BatchQueue | None = None


def get_batch_queue(
    db_path: Path = BATCH_QUEUE_FILE,
    concurrency: int = DEFAULT_BATCH_CONCURRENCY,
) -> BatchQueue:
    """Get or create singleton batch queue instance.

    Args:
        db_path: path to SQLite database
        concurrency: max concurrent jobs

    Returns:
        BatchQueue singleton
    """
    global _batch_queue
    if _batch_queue is None:
        _batch_queue = BatchQueue(db_path, concurrency)
    return _batch_queue


# ─── MCP Tool Functions ──────────────────────────────────────────────────────


async def research_batch_submit(
    tool_name: str,
    params: dict[str, Any],
    callback_url: str | None = None,
    max_retries: int = 3,
) -> dict[str, Any]:
    """Submit a tool invocation to the batch queue.

    This tool queues non-time-sensitive tool calls for asynchronous processing.
    Use this for expensive operations that can be deferred.

    Args:
        tool_name: name of the tool to invoke (e.g., 'research_fetch')
        params: tool parameters as dict
        callback_url: optional webhook URL for completion notification
        max_retries: max automatic retries on failure (0-10, default 3)

    Returns:
        dict with batch_id (UUID4) and submission confirmation

    Raises:
        ValueError: if tool_name or params invalid
    """
    # Validate with Pydantic
    validated = BatchSubmitParams(
        tool_name=tool_name,
        params=params,
        callback_url=callback_url,
        max_retries=max_retries,
    )

    queue = get_batch_queue()
    batch_id = queue.submit(
        validated.tool_name,
        validated.params,
        callback_url=validated.callback_url,
        max_retries=validated.max_retries,
    )

    return {
        "batch_id": batch_id,
        "tool_name": validated.tool_name,
        "status": "pending",
        "submitted_at": datetime.now(UTC).isoformat(),
        "message": f"Job submitted to batch queue. Check status with batch_id: {batch_id}",
    }


async def research_batch_status(batch_id: str) -> dict[str, Any]:
    """Get the status of a batch job.

    Args:
        batch_id: the batch job ID (UUID4) returned by research_batch_submit

    Returns:
        dict with id, tool_name, status, result, error_message, timestamps, retry_count

    Raises:
        ValueError: if batch_id not found
    """
    # Validate with Pydantic
    validated = BatchStatusParams(batch_id=batch_id)

    queue = get_batch_queue()
    return queue.get_status(validated.batch_id)


async def research_batch_list(
    limit: int = 20,
    status_filter: Literal["all", "pending", "processing", "done", "failed"] = "all",
    offset: int = 0,
) -> dict[str, Any]:
    """List recent batch items with optional filtering.

    Args:
        limit: max items to return (1-100, default 20)
        status_filter: filter by status: 'all', 'pending', 'processing', 'done', 'failed'
        offset: pagination offset (default 0)

    Returns:
        dict with items list and total_count estimate
    """
    # Validate with Pydantic
    validated = BatchListParams(
        limit=limit,
        status_filter=status_filter,
        offset=offset,
    )

    queue = get_batch_queue()
    items = queue.list_items(
        limit=validated.limit,
        status_filter=validated.status_filter,
        offset=validated.offset,
    )

    return {
        "items": items,
        "count": len(items),
        "limit": validated.limit,
        "offset": validated.offset,
        "status_filter": validated.status_filter,
    }


# ─── Background Task ────────────────────────────────────────────────────────


_background_task: asyncio.Task[None] | None = None


async def _batch_queue_background_worker() -> None:
    """Background worker that processes batch queue every BATCH_BACKGROUND_INTERVAL_SECS.

    This runs continuously while the server is up, calling process_pending()
    periodically to drain the queue.
    """
    queue = get_batch_queue()
    while True:
        try:
            await asyncio.sleep(BATCH_BACKGROUND_INTERVAL_SECS)
            processed = await queue.process_pending()
            if processed > 0:
                logger.debug("batch_background_processed count=%d", processed)
        except Exception as e:
            logger.error("batch_background_worker_exception error=%s", e)


def start_batch_queue_background() -> None:
    """Start the background batch processing task.

    Called once at server startup. Creates an asyncio.Task that runs
    indefinitely to process pending batch items.
    """
    global _background_task
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if _background_task is None or _background_task.done():
        _background_task = loop.create_task(_batch_queue_background_worker())
        logger.info("batch_queue_background_started")


def stop_batch_queue_background() -> None:
    """Stop the background batch processing task.

    Called at server shutdown. Cancels the background task gracefully.
    """
    global _background_task
    if _background_task is not None and not _background_task.done():
        _background_task.cancel()
        logger.info("batch_queue_background_stopped")
