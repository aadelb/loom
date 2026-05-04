"""Tests for the webhook notification system."""

from __future__ import annotations

import asyncio
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.webhooks import (
    Webhook,
    WebhookManager,
    get_webhook_manager,
    SUPPORTED_EVENTS,
)


class TestWebhook:
    """Test Webhook dataclass."""

    def test_webhook_creation(self):
        """Test creating a webhook instance."""
        webhook = Webhook(
            webhook_id="wh_123",
            url="https://example.com/webhook",
            events=["tool.completed"],
            secret="my-secret",
            created_at="2026-05-04T00:00:00Z",
        )

        assert webhook.webhook_id == "wh_123"
        assert webhook.url == "https://example.com/webhook"
        assert webhook.events == ["tool.completed"]
        assert webhook.active is True

    def test_webhook_matches_event(self):
        """Test event matching."""
        webhook = Webhook(
            webhook_id="wh_123",
            url="https://example.com/webhook",
            events=["tool.completed", "tool.failed"],
            secret="my-secret",
            created_at="2026-05-04T00:00:00Z",
        )

        assert webhook.matches_event("tool.completed") is True
        assert webhook.matches_event("tool.failed") is True
        assert webhook.matches_event("job.queued") is False

    def test_webhook_matches_event_when_inactive(self):
        """Test that inactive webhooks don't match."""
        webhook = Webhook(
            webhook_id="wh_123",
            url="https://example.com/webhook",
            events=["tool.completed"],
            secret="my-secret",
            created_at="2026-05-04T00:00:00Z",
            active=False,
        )

        assert webhook.matches_event("tool.completed") is False

    def test_webhook_to_dict(self):
        """Test converting webhook to dict."""
        webhook = Webhook(
            webhook_id="wh_123",
            url="https://example.com/webhook",
            events=["tool.completed"],
            secret="my-secret",
            created_at="2026-05-04T00:00:00Z",
            success_count=5,
            failure_count=2,
        )

        data = webhook.to_dict()
        assert data["webhook_id"] == "wh_123"
        assert data["url"] == "https://example.com/webhook"
        assert data["success_count"] == 5
        assert data["failure_count"] == 2


class TestWebhookManager:
    """Test WebhookManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh webhook manager for each test."""
        return WebhookManager()

    @pytest.mark.asyncio
    async def test_register_webhook(self, manager):
        """Test registering a webhook."""
        webhook_id = await manager.register(
            url="https://example.com/webhook",
            events=["tool.completed"],
        )

        assert webhook_id
        webhook = await manager.get_webhook(webhook_id)
        assert webhook is not None
        assert webhook.url == "https://example.com/webhook"
        assert webhook.events == ["tool.completed"]
        assert webhook.secret is not None

    @pytest.mark.asyncio
    async def test_register_with_custom_secret(self, manager):
        """Test registering with a custom secret."""
        webhook_id = await manager.register(
            url="https://example.com/webhook",
            events=["tool.completed"],
            secret="my-custom-secret",
        )

        webhook = await manager.get_webhook(webhook_id)
        assert webhook.secret == "my-custom-secret"

    @pytest.mark.asyncio
    async def test_register_invalid_url(self, manager):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValueError):
            await manager.register(
                url="not-a-url",
                events=["tool.completed"],
            )

    @pytest.mark.asyncio
    async def test_register_invalid_event(self, manager):
        """Test that invalid events are rejected."""
        with pytest.raises(ValueError):
            await manager.register(
                url="https://example.com/webhook",
                events=["invalid.event"],
            )

    @pytest.mark.asyncio
    async def test_register_no_events(self, manager):
        """Test that empty event list is rejected."""
        with pytest.raises(ValueError):
            await manager.register(
                url="https://example.com/webhook",
                events=[],
            )

    @pytest.mark.asyncio
    async def test_unregister_webhook(self, manager):
        """Test unregistering a webhook."""
        webhook_id = await manager.register(
            url="https://example.com/webhook",
            events=["tool.completed"],
        )

        success = await manager.unregister(webhook_id)
        assert success is True

        webhook = await manager.get_webhook(webhook_id)
        assert webhook is None

    @pytest.mark.asyncio
    async def test_unregister_nonexistent(self, manager):
        """Test unregistering a nonexistent webhook."""
        success = await manager.unregister("nonexistent-id")
        assert success is False

    @pytest.mark.asyncio
    async def test_list_webhooks(self, manager):
        """Test listing webhooks."""
        webhook_id1 = await manager.register(
            url="https://example.com/webhook1",
            events=["tool.completed"],
            secret="secret1",
        )
        webhook_id2 = await manager.register(
            url="https://example.com/webhook2",
            events=["tool.failed"],
            secret="secret2",
        )

        webhooks = await manager.list_webhooks()
        assert len(webhooks) == 2
        assert webhooks[0]["webhook_id"] == webhook_id1
        assert webhooks[1]["webhook_id"] == webhook_id2
        # Secrets should be masked
        assert "***" in webhooks[0]["secret"]
        assert "***" in webhooks[1]["secret"]

    @pytest.mark.asyncio
    async def test_list_empty(self, manager):
        """Test listing when no webhooks exist."""
        webhooks = await manager.list_webhooks()
        assert webhooks == []

    @pytest.mark.asyncio
    async def test_get_webhook(self, manager):
        """Test getting a specific webhook."""
        webhook_id = await manager.register(
            url="https://example.com/webhook",
            events=["tool.completed"],
        )

        webhook = await manager.get_webhook(webhook_id)
        assert webhook is not None
        assert webhook.webhook_id == webhook_id

    @pytest.mark.asyncio
    async def test_get_webhook_nonexistent(self, manager):
        """Test getting a nonexistent webhook."""
        webhook = await manager.get_webhook("nonexistent-id")
        assert webhook is None

    @pytest.mark.asyncio
    async def test_notify_no_matching_webhooks(self, manager):
        """Test notifying when no webhooks match the event."""
        result = await manager.notify("tool.completed", {"tool_name": "test"})

        assert result["event"] == "tool.completed"
        assert result["total_webhooks"] == 0
        assert result["succeeded"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_notify_invalid_event(self, manager):
        """Test notifying with an invalid event."""
        with pytest.raises(ValueError):
            await manager.notify("invalid.event", {})

    @pytest.mark.asyncio
    async def test_hmac_signature_generation(self, manager):
        """Test HMAC-SHA256 signature generation."""
        webhook_id = await manager.register(
            url="https://example.com/webhook",
            events=["tool.completed"],
            secret="test-secret",
        )

        webhook = await manager.get_webhook(webhook_id)
        body = '{"test": "data"}'

        expected_sig = hmac.new(
            webhook.secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        assert expected_sig == f"sha256={expected_sig}".split("=")[1]

    @pytest.mark.asyncio
    async def test_send_notification_success(self, manager):
        """Test successful notification delivery."""
        webhook_id = await manager.register(
            url="https://example.com/webhook",
            events=["tool.completed"],
            secret="test-secret",
        )

        # Mock httpx client
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(manager, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            webhook = await manager.get_webhook(webhook_id)
            result = await manager._send_notification(
                webhook,
                "tool.completed",
                {"tool_name": "test", "success": True},
            )

            assert result["status"] == "success"
            assert result["webhook_id"] == webhook_id
            assert result["retries"] == 0
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_send_notification_timeout(self, manager):
        """Test notification timeout with retries."""
        webhook_id = await manager.register(
            url="https://example.com/webhook",
            events=["tool.completed"],
            secret="test-secret",
        )

        # Mock httpx client to timeout
        with patch.object(manager, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=asyncio.TimeoutError())

            webhook = await manager.get_webhook(webhook_id)
            result = await manager._send_notification(
                webhook,
                "tool.completed",
                {"tool_name": "test"},
            )

            assert result["status"] == "failed"
            assert result["retries"] == 3
            assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_notify_concurrent_delivery(self, manager):
        """Test concurrent delivery to multiple webhooks."""
        webhook_id1 = await manager.register(
            url="https://example.com/webhook1",
            events=["tool.completed"],
        )
        webhook_id2 = await manager.register(
            url="https://example.com/webhook2",
            events=["tool.completed"],
        )

        # Mock successful delivery
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(manager, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await manager.notify(
                "tool.completed",
                {"tool_name": "test"},
            )

            assert result["total_webhooks"] == 2
            assert result["succeeded"] == 2
            assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_send_test_notification(self, manager):
        """Test sending a test notification."""
        webhook_id = await manager.register(
            url="https://example.com/webhook",
            events=["tool.completed"],
        )

        # Mock successful delivery
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(manager, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            result = await manager.send_test_notification(webhook_id)

            assert result["status"] == "success"
            assert result["webhook_id"] == webhook_id

    @pytest.mark.asyncio
    async def test_send_test_notification_not_found(self, manager):
        """Test sending test notification to nonexistent webhook."""
        with pytest.raises(ValueError):
            await manager.send_test_notification("nonexistent-id")

    @pytest.mark.asyncio
    async def test_webhook_metadata_tracking(self, manager):
        """Test that webhook success/failure counts are tracked."""
        webhook_id = await manager.register(
            url="https://example.com/webhook",
            events=["tool.completed"],
        )

        webhook = await manager.get_webhook(webhook_id)
        assert webhook.success_count == 0
        assert webhook.failure_count == 0

        # Mock successful delivery
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(manager, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            await manager._send_notification(
                webhook,
                "tool.completed",
                {"tool_name": "test"},
            )

        webhook = await manager.get_webhook(webhook_id)
        assert webhook.success_count == 1
        assert webhook.failure_count == 0

    @pytest.mark.asyncio
    async def test_supported_events_constant(self):
        """Test that all supported events are defined."""
        expected_events = {
            "tool.completed",
            "tool.failed",
            "job.queued",
            "job.finished",
            "alert.error",
        }

        assert SUPPORTED_EVENTS == expected_events


class TestWebhookGlobal:
    """Test global webhook manager instance."""

    @pytest.mark.asyncio
    async def test_get_webhook_manager_singleton(self):
        """Test that get_webhook_manager returns a singleton."""
        manager1 = get_webhook_manager()
        manager2 = get_webhook_manager()

        assert manager1 is manager2
