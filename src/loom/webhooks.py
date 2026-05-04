"""Webhook notification system for Loom tool completion events.

Provides a WebhookManager for registering and managing webhooks, with:
  - Event filtering (tool.completed, tool.failed, job.queued, job.finished, alert.error)
  - HMAC-SHA256 signature verification
  - Retry logic with exponential backoff (1s, 4s, 16s)
  - Async HTTP POST notifications with timeout protection
  - In-memory storage (optional Redis support via config)

Example usage:
  manager = get_webhook_manager()
  webhook_id = await manager.register(
      url="https://example.com/webhook",
      events=["tool.completed", "tool.failed"],
      secret="my-secret-key"
  )
  await manager.notify("tool.completed", {
      "tool_name": "research_fetch",
      "duration": 2.5,
      "success": True
  })
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import secrets
import uuid
from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger("loom.webhooks")

# Global webhook manager instance
_webhook_manager: WebhookManager | None = None

# Supported events
SUPPORTED_EVENTS = {
    "tool.completed",
    "tool.failed",
    "job.queued",
    "job.finished",
    "alert.error",
}


@dataclass
class Webhook:
    """Webhook registration record."""

    webhook_id: str
    url: str
    events: list[str]
    secret: str
    created_at: str
    last_triggered: str | None = None
    success_count: int = 0
    failure_count: int = 0
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return asdict(self)

    def matches_event(self, event: str) -> bool:
        """Check if this webhook should be notified for the event."""
        return event in self.events and self.active


class WebhookManager:
    """Manages webhook registrations and notifications.

    Stores webhooks in-memory (or Redis if configured).
    Sends async HTTP POST notifications with HMAC-SHA256 signature.
    Retries failed notifications with exponential backoff.
    """

    def __init__(self):
        """Initialize webhook manager with empty registry."""
        self._webhooks: dict[str, Webhook] = {}
        self._lock = asyncio.Lock()
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client (lazy initialization)."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    async def register(
        self,
        url: str,
        events: list[str],
        secret: str | None = None,
    ) -> str:
        """Register a new webhook.

        Args:
            url: Webhook URL to POST to
            events: List of events to subscribe to (from SUPPORTED_EVENTS)
            secret: HMAC secret for signature verification (generated if not provided)

        Returns:
            Webhook ID for later management

        Raises:
            ValueError: If URL or events are invalid
        """
        # Validate URL
        if not url.startswith(("http://", "https://")):
            raise ValueError("webhook URL must start with http:// or https://")

        # Validate events
        invalid_events = set(events) - SUPPORTED_EVENTS
        if invalid_events:
            raise ValueError(
                f"invalid events: {invalid_events}. "
                f"supported: {SUPPORTED_EVENTS}"
            )

        if not events:
            raise ValueError("at least one event must be specified")

        # Generate secret if not provided
        if secret is None:
            secret = secrets.token_urlsafe(32)

        webhook_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        webhook = Webhook(
            webhook_id=webhook_id,
            url=url,
            events=events,
            secret=secret,
            created_at=now,
        )

        async with self._lock:
            self._webhooks[webhook_id] = webhook

        logger.info(
            "webhook_registered webhook_id=%s url=%s events=%s",
            webhook_id,
            url,
            events,
        )

        return webhook_id

    async def unregister(self, webhook_id: str) -> bool:
        """Unregister a webhook.

        Args:
            webhook_id: ID of webhook to unregister

        Returns:
            True if unregistered, False if not found
        """
        async with self._lock:
            if webhook_id not in self._webhooks:
                return False

            del self._webhooks[webhook_id]

        logger.info("webhook_unregistered webhook_id=%s", webhook_id)

        return True

    async def list_webhooks(self) -> list[dict[str, Any]]:
        """List all registered webhooks (without secrets).

        Returns:
            List of webhook dicts with secret masked
        """
        async with self._lock:
            webhooks = list(self._webhooks.values())

        return [
            {
                **webhook.to_dict(),
                "secret": "***" + webhook.secret[-4:] if webhook.secret else "***",
            }
            for webhook in webhooks
        ]

    async def get_webhook(self, webhook_id: str) -> Webhook | None:
        """Get a specific webhook by ID.

        Args:
            webhook_id: ID of webhook to retrieve

        Returns:
            Webhook object or None if not found
        """
        async with self._lock:
            return self._webhooks.get(webhook_id)

    async def notify(
        self,
        event: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Notify all webhooks subscribed to an event.

        Args:
            event: Event type (must be in SUPPORTED_EVENTS)
            payload: Event payload (will be JSON-encoded)

        Returns:
            Dict with notification results:
              {
                "event": event,
                "total_webhooks": int,
                "succeeded": int,
                "failed": int,
                "results": [
                  {
                    "webhook_id": str,
                    "url": str,
                    "status": "success" | "failed",
                    "retries": int,
                    "error": str | None
                  }
                ]
              }
        """
        if event not in SUPPORTED_EVENTS:
            raise ValueError(f"unsupported event: {event}. supported: {SUPPORTED_EVENTS}")

        async with self._lock:
            matching_webhooks = [
                webhook
                for webhook in self._webhooks.values()
                if webhook.matches_event(event)
            ]

        if not matching_webhooks:
            return {
                "event": event,
                "total_webhooks": 0,
                "succeeded": 0,
                "failed": 0,
                "results": [],
            }

        # Send notifications concurrently
        results = await asyncio.gather(
            *[
                self._send_notification(webhook, event, payload)
                for webhook in matching_webhooks
            ],
            return_exceptions=False,
        )

        succeeded = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "failed")

        logger.info(
            "webhook_notify event=%s total=%d succeeded=%d failed=%d",
            event,
            len(matching_webhooks),
            succeeded,
            failed,
        )

        return {
            "event": event,
            "total_webhooks": len(matching_webhooks),
            "succeeded": succeeded,
            "failed": failed,
            "results": results,
        }

    async def _send_notification(
        self,
        webhook: Webhook,
        event: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a single notification with retry logic.

        Args:
            webhook: Webhook to notify
            event: Event type
            payload: Event payload

        Returns:
            Result dict with status, retries, and optional error
        """
        body = json.dumps({
            "event": event,
            "timestamp": datetime.now(UTC).isoformat(),
            "webhook_id": webhook.webhook_id,
            "payload": payload,
        })

        # Compute HMAC-SHA256 signature
        signature = hmac.new(
            webhook.secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-Loom-Signature": f"sha256={signature}",
            "X-Loom-Event": event,
            "X-Loom-Webhook-ID": webhook.webhook_id,
            "User-Agent": "Loom/1.0",
        }

        # Retry logic: 1s, 4s, 16s
        retry_delays = [1, 4, 16]
        last_error = None

        for attempt in range(len(retry_delays) + 1):
            try:
                client = await self._get_client()
                response = await client.post(
                    webhook.url,
                    content=body,
                    headers=headers,
                )

                # Consider 2xx and 3xx as success
                if 200 <= response.status_code < 400:
                    async with self._lock:
                        webhook.last_triggered = datetime.now(UTC).isoformat()
                        webhook.success_count += 1

                    logger.info(
                        "webhook_notification_success webhook_id=%s url=%s status=%d attempts=%d",
                        webhook.webhook_id,
                        webhook.url,
                        response.status_code,
                        attempt + 1,
                    )

                    return {
                        "webhook_id": webhook.webhook_id,
                        "url": webhook.url,
                        "status": "success",
                        "retries": attempt,
                        "error": None,
                    }

                # 4xx are client errors, don't retry
                if 400 <= response.status_code < 500:
                    last_error = f"HTTP {response.status_code}: {response.text[:100]}"
                    break

                # 5xx are server errors, retry
                last_error = f"HTTP {response.status_code}: {response.text[:100]}"

            except asyncio.TimeoutError:
                last_error = "Request timeout (10s)"
            except httpx.ConnectError as e:
                last_error = f"Connection error: {str(e)[:100]}"
            except httpx.RequestError as e:
                last_error = f"HTTP error: {str(e)[:100]}"
            except Exception as e:
                last_error = f"Unexpected error: {str(e)[:100]}"

            # Retry with exponential backoff (except on last attempt)
            if attempt < len(retry_delays):
                delay = retry_delays[attempt]
                logger.warning(
                    "webhook_notification_retry webhook_id=%s attempt=%d delay=%ds error=%s",
                    webhook.webhook_id,
                    attempt + 1,
                    delay,
                    last_error,
                )
                await asyncio.sleep(delay)

        # All retries exhausted
        async with self._lock:
            webhook.failure_count += 1

        logger.error(
            "webhook_notification_failed webhook_id=%s url=%s attempts=%d error=%s",
            webhook.webhook_id,
            webhook.url,
            len(retry_delays) + 1,
            last_error,
        )

        return {
            "webhook_id": webhook.webhook_id,
            "url": webhook.url,
            "status": "failed",
            "retries": len(retry_delays),
            "error": last_error,
        }

    async def send_test_notification(self, webhook_id: str) -> dict[str, Any]:
        """Send a test notification to a specific webhook.

        Args:
            webhook_id: ID of webhook to test

        Returns:
            Result dict with status and error (if any)
        """
        webhook = await self.get_webhook(webhook_id)
        if webhook is None:
            raise ValueError(f"webhook not found: {webhook_id}")

        return await self._send_notification(
            webhook,
            "tool.completed",
            {
                "tool_name": "test",
                "duration": 0.1,
                "success": True,
                "message": "This is a test notification",
            },
        )

    async def close(self) -> None:
        """Close the HTTP client and cleanup resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def get_webhook_manager() -> WebhookManager:
    """Get or create the global webhook manager instance."""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager()
    return _webhook_manager
