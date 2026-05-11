"""MCP tools for webhook management.

Provides tools to register, list, unregister, and test webhooks.
"""

from __future__ import annotations

import logging
from typing import Any

from loom.params import WebhookRegisterParams, WebhookUnregisterParams, WebhookTestParams
from loom.webhooks import get_webhook_manager, SUPPORTED_EVENTS

logger = logging.getLogger("loom.tools.webhooks")


async def research_webhook_register(
    url: str,
    events: list[str] | str,
    secret: str | None = None,
) -> dict[str, Any]:
    """Register a new webhook for Loom tool events.

    Webhooks receive HTTP POST notifications when subscribed events occur.
    Each notification includes an HMAC-SHA256 signature in the X-Loom-Signature header
    for verification.

    Args:
        url: Webhook URL (must start with http:// or https://)
        events: List of events to subscribe to. Supported events:
          - "tool.completed" - fired when a tool finishes successfully
          - "tool.failed" - fired when a tool execution fails
          - "job.queued" - fired when a job is queued
          - "job.finished" - fired when a job finishes (success or failure)
          - "alert.error" - fired when an error is detected
        secret: HMAC secret for signature verification (auto-generated if not provided)

    Returns:
        {
          "webhook_id": str,
          "url": str,
          "events": list[str],
          "secret": str (only shown once on registration),
          "created_at": str,
          "active": bool
        }

    Raises:
        ValueError: If URL or events are invalid
    """
    try:
        # Coerce string to list before validation
        if isinstance(events, str):
            events = [events]

        params = WebhookRegisterParams(url=url, events=events, secret=secret)

        manager = get_webhook_manager()
        webhook_id = await manager.register(
            url=params.url,
            events=params.events,
            secret=params.secret,
        )

        webhook = await manager.get_webhook(webhook_id)
        if webhook is None:
            return {
                "error": "failed to retrieve registered webhook",
                "webhook_id": webhook_id,
            }

        result = webhook.to_dict()
        # Include the generated secret only on first registration
        logger.info(
            "webhook_registered webhook_id=%s url=%s events=%s",
            webhook_id,
            params.url,
            params.events,
        )

        return result
    except Exception as exc:
        logger.exception("research_webhook_register failed")
        return {"error": str(exc), "tool": "research_webhook_register"}


async def research_webhook_list() -> dict[str, Any]:
    """List all registered webhooks (without revealing secrets).

    Returns:
        {
          "webhooks": [
            {
              "webhook_id": str,
              "url": str,
              "events": list[str],
              "secret": "***..." (masked),
              "created_at": str,
              "last_triggered": str | None,
              "success_count": int,
              "failure_count": int,
              "active": bool
            }
          ],
          "total": int
        }
    """
    try:
        manager = get_webhook_manager()
        webhooks = await manager.list_webhooks()

        logger.info("webhook_list_requested count=%d", len(webhooks))

        return {
            "webhooks": webhooks,
            "total": len(webhooks),
            "supported_events": sorted(SUPPORTED_EVENTS),
        }
    except Exception as exc:
        logger.exception("research_webhook_list failed")
        return {"error": str(exc), "tool": "research_webhook_list"}


async def research_webhook_unregister(webhook_id: str) -> dict[str, Any]:
    """Unregister a webhook.

    Args:
        webhook_id: ID of webhook to unregister

    Returns:
        {
          "success": bool,
          "webhook_id": str,
          "message": str
        }
    """
    try:
        params = WebhookUnregisterParams(webhook_id=webhook_id)

        manager = get_webhook_manager()
        success = await manager.unregister(params.webhook_id)

        if success:
            logger.info("webhook_unregistered webhook_id=%s", params.webhook_id)
            return {
                "success": True,
                "webhook_id": params.webhook_id,
                "message": f"Webhook {params.webhook_id} unregistered successfully",
            }
        else:
            logger.warning("webhook_unregister_not_found webhook_id=%s", params.webhook_id)
            return {
                "success": False,
                "webhook_id": params.webhook_id,
                "message": f"Webhook {params.webhook_id} not found",
            }
    except Exception as exc:
        logger.exception("research_webhook_unregister failed")
        return {"error": str(exc), "tool": "research_webhook_unregister"}


async def research_webhook_test(webhook_id: str) -> dict[str, Any]:
    """Send a test notification to a webhook.

    This sends a test webhook with event type "tool.completed" and a dummy payload.
    The response will show the HTTP status and any errors encountered.

    Args:
        webhook_id: ID of webhook to test

    Returns:
        {
          "webhook_id": str,
          "url": str,
          "status": "success" | "failed",
          "retries": int,
          "error": str | None,
          "message": str
        }

    Raises:
        ValueError: If webhook not found
    """
    try:
        params = WebhookTestParams(webhook_id=webhook_id)

        manager = get_webhook_manager()
        webhook = await manager.get_webhook(params.webhook_id)

        if webhook is None:
            raise ValueError(f"webhook not found: {params.webhook_id}")

        result = await manager.send_test_notification(params.webhook_id)

        logger.info(
            "webhook_test webhook_id=%s status=%s",
            params.webhook_id,
            result["status"],
        )

        result["message"] = (
            f"Test notification sent to {webhook.url}. "
            f"Status: {result['status']}"
        )

        return result
    except Exception as exc:
        logger.exception("research_webhook_test failed")
        return {"error": str(exc), "tool": "research_webhook_test"}
