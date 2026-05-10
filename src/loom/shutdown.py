"""Graceful shutdown orchestration for Loom MCP server.

Extracted from server.py to reduce monolith size.
Handles session cleanup, provider close, and signal handling.
"""
from __future__ import annotations

import asyncio
import logging
import signal
from typing import Any

from loom.server_state import set_shutting_down, is_shutting_down

log = logging.getLogger("loom.shutdown")


async def _shutdown() -> None:
    """Graceful shutdown: close all browser sessions, HTTP clients, and providers.

    Cleanup sequence:
    1. Mark server as shutting down (reject new requests)
    2. Wait briefly for in-flight requests to drain
    3. Flush DLQ (deadletter queue) if exists
    4. Save strategy adapter state
    5. Close HTTP client pool
    6. Close LLM provider clients
    7. Stop background task scheduler
    8. Stop batch queue background processing
    """
    set_shutting_down()

    # Wait briefly for in-flight requests
    try:
        await asyncio.sleep(0.5)
        log.info("shutdown_grace_period_active max_wait_seconds=5")
    except Exception:
        pass

    log.info("shutdown_signal_received")

    # Close browser sessions
    try:
        from loom.sessions import cleanup_all_sessions

        result = await cleanup_all_sessions()
        log.info(
            "shutdown_sessions_closed=%d errors=%d",
            len(result.get("closed", [])),
            len(result.get("errors", [])),
        )
    except Exception as exc:
        log.error("shutdown_sessions_error: %s", exc)

    # Flush DLQ (deadletter queue) if it exists
    try:
        from loom.batch_queue import get_dlq

        dlq = get_dlq()
        if dlq and hasattr(dlq, "flush"):
            flushed = await dlq.flush()
            log.info("shutdown_dlq_flushed count=%d", len(flushed) if isinstance(flushed, list) else 0)
    except (ImportError, AttributeError):
        pass
    except Exception as exc:
        log.warning("shutdown_dlq_flush_failed: %s", exc)

    # Save strategy adapter state if it exists
    try:
        from loom.reid_auto import ReidAutoReframe

        adapter = ReidAutoReframe._instance if hasattr(ReidAutoReframe, "_instance") else None
        if adapter and hasattr(adapter, "save_state"):
            await adapter.save_state()
            log.info("shutdown_strategy_state_saved")
    except (ImportError, AttributeError):
        pass
    except Exception as exc:
        log.warning("shutdown_strategy_state_save_failed: %s", exc)

    # Close httpx connection pool
    try:
        from loom.tools.fetch import _http_client

        if _http_client is not None:
            _http_client.close()
            log.info("shutdown_http_client_closed")
    except Exception as exc:
        log.error("shutdown_http_client_error: %s", exc)

    # Close LLM provider clients
    try:
        from loom.tools.llm import close_all_providers

        await close_all_providers()
        log.info("shutdown_providers_closed")
    except (ImportError, AttributeError):
        pass
    except Exception as exc:
        log.error("shutdown_providers_error: %s", exc)

    # Stop background task scheduler
    try:
        from loom.scheduler import get_scheduler

        scheduler = get_scheduler()
        await scheduler.stop()
        log.info("background_task_scheduler_stopped")
    except Exception as exc:
        log.error("scheduler_shutdown_failed: %s", exc)

    # Stop batch queue background processing
    try:
        from loom.batch_queue import stop_batch_queue_background

        stop_batch_queue_background()
        log.info("batch_queue_background_stopped")
    except Exception as exc:
        log.error("batch_queue_shutdown_failed: %s", exc)

    log.info("shutdown_complete")


_background_tasks: set[asyncio.Task[None]] = set()


def _handle_signal(sig: int, _frame: Any) -> None:
    """Signal handler that runs graceful shutdown in a new event loop."""
    set_shutting_down()
    log.info("signal_handler_invoked signal=%s", signal.Signals(sig).name)
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(_shutdown())
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        asyncio.run(_shutdown())
