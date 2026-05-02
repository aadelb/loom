"""Async Webhook/Callback system for long-running research tasks."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger("loom.webhook_system")
DEFAULT_EVENTS = [
    "task_complete",
    "hcs_threshold_reached",
    "exploit_discovered",
    "error",
]


class WebhookRegisterParams(BaseModel):
    """Parameters for webhook registration."""

    url: str = Field(..., description="Webhook URL")
    events: list[str] | None = None
    secret: str = ""
    model_config = {"extra": "forbid", "strict": True}


class WebhookFireParams(BaseModel):
    """Parameters for firing webhook events."""

    event: str
    payload: dict[str, Any] = Field(default_factory=dict)
    model_config = {"extra": "forbid", "strict": True}


def _db_path() -> Path:
    """Get webhooks database path."""
    p = Path.home() / ".loom" / "webhooks.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


async def _init_db() -> None:
    """Initialize database schema."""
    async with aiosqlite.connect(_db_path()) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS webhooks (
            id TEXT PRIMARY KEY, url TEXT NOT NULL, events TEXT NOT NULL,
            secret TEXT, created TEXT NOT NULL, active BOOLEAN NOT NULL)""")
        await db.commit()


def _sign(payload: str, secret: str) -> str:
    """Compute HMAC-SHA256 signature."""
    return hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()


async def research_webhook_register(
    url: str, events: list[str] | None = None, secret: str = ""
) -> dict[str, Any]:
    """Register webhook URL for task notifications."""
    await _init_db()
    webhook_id = str(uuid.uuid4())
    subs = events or DEFAULT_EVENTS
    created = datetime.now(UTC).isoformat()
    async with aiosqlite.connect(_db_path()) as db:
        sql = (
            "INSERT INTO webhooks "
            "(id, url, events, secret, created, active) "
            "VALUES (?, ?, ?, ?, ?, 1)"
        )
        await db.execute(
            sql,
            (webhook_id, url, json.dumps(subs), secret, created),
        )
        await db.commit()
    logger.info("webhook_registered id=%s url=%s", webhook_id, url)
    return {
        "webhook_id": webhook_id,
        "url": url,
        "events": subs,
        "status": "active",
    }


async def research_webhook_fire(
    event: str, payload: dict[str, Any]
) -> dict[str, Any]:
    """Fire webhook event to all registered listeners."""
    await _init_db()
    async with aiosqlite.connect(_db_path()) as db:
        cursor = await db.execute(
            "SELECT id, url, events, secret FROM webhooks WHERE active = 1"
        )
        webhooks = await cursor.fetchall()
    tasks = [
        _send_webhook(wid, url, event, payload, secret)
        for wid, url, events_json, secret in webhooks
        if event in json.loads(events_json)
    ]
    results = (
        await asyncio.gather(*tasks, return_exceptions=True) if tasks else []
    )
    successes = sum(1 for r in results if r is True)
    failures = len(tasks) - successes
    logger.info(
        "webhook_fired event=%s notified=%d successes=%d",
        event,
        len(tasks),
        successes,
    )
    return {
        "event": event,
        "listeners_notified": len(tasks),
        "successes": successes,
        "failures": failures,
    }


async def _send_webhook(
    webhook_id: str, url: str, event: str, payload: dict[str, Any], secret: str
) -> bool:
    """Send webhook POST with HMAC signature."""
    try:
        body = json.dumps(
            {
                "webhook_id": webhook_id,
                "event": event,
                "timestamp": datetime.now(UTC).isoformat(),
                "payload": payload,
            }
        )
        headers = {"Content-Type": "application/json"}
        if secret:
            headers["X-Webhook-Signature"] = _sign(body, secret)
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(url, content=body, headers=headers)
        return True
    except Exception as e:
        logger.warning(
            "webhook_send_failed id=%s url=%s error=%s", webhook_id, url, e
        )
        return False


async def research_webhook_list() -> dict[str, Any]:
    """List all registered webhooks."""
    await _init_db()
    async with aiosqlite.connect(_db_path()) as db:
        cursor = await db.execute(
            "SELECT id, url, events, active, created FROM webhooks "
            "ORDER BY created DESC"
        )
        rows = await cursor.fetchall()
    webhooks = [
        {
            "id": wid,
            "url": url,
            "events": json.loads(events_json),
            "active": bool(active),
            "created": created,
        }
        for wid, url, events_json, active, created in rows
    ]
    total = sum(1 for w in webhooks if w["active"])
    logger.info("webhook_list total=%d active=%d", len(webhooks), total)
    return {"webhooks": webhooks, "total_active": total}
