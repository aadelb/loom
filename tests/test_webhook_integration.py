"""Integration tests for webhook system with tools."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from loom.tools.infrastructure.webhooks import (
    research_webhook_register,
    research_webhook_list,
    research_webhook_unregister,
    research_webhook_test,
)


class TestWebhookTools:
    """Test webhook management tools."""

    @pytest.mark.asyncio
    async def test_register_and_list_webhooks(self):
        """Test registering and listing webhooks."""
        # Register a webhook
        result = await research_webhook_register(
            url="https://example.com/webhook",
            events=["tool.completed", "tool.failed"],
        )

        assert "webhook_id" in result
        assert result["url"] == "https://example.com/webhook"
        assert result["events"] == ["tool.completed", "tool.failed"]
        webhook_id = result["webhook_id"]

        # List webhooks
        list_result = await research_webhook_list()
        assert "webhooks" in list_result
        assert list_result["total"] >= 1
        assert any(w["webhook_id"] == webhook_id for w in list_result["webhooks"])

    @pytest.mark.asyncio
    async def test_register_with_secret(self):
        """Test registering with a custom secret."""
        result = await research_webhook_register(
            url="https://example.com/webhook",
            events=["tool.completed"],
            secret="my-custom-secret-123",
        )

        assert result["webhook_id"]
        # Secret should be returned on registration
        assert result["secret"] == "my-custom-secret-123"

    @pytest.mark.asyncio
    async def test_register_invalid_url(self):
        """Test that invalid URLs are rejected."""
        with pytest.raises(ValueError):
            await research_webhook_register(
                url="not-a-url",
                events=["tool.completed"],
            )

    @pytest.mark.asyncio
    async def test_register_invalid_event(self):
        """Test that invalid events are rejected."""
        with pytest.raises(ValueError):
            await research_webhook_register(
                url="https://example.com/webhook",
                events=["invalid.event"],
            )

    @pytest.mark.asyncio
    async def test_unregister_webhook(self):
        """Test unregistering a webhook."""
        # Register a webhook
        reg_result = await research_webhook_register(
            url="https://example.com/webhook",
            events=["tool.completed"],
        )
        webhook_id = reg_result["webhook_id"]

        # Unregister it
        unreg_result = await research_webhook_unregister(webhook_id)
        assert unreg_result["success"] is True
        assert unreg_result["webhook_id"] == webhook_id

        # Verify it's gone from the list
        list_result = await research_webhook_list()
        assert not any(w["webhook_id"] == webhook_id for w in list_result["webhooks"])

    @pytest.mark.asyncio
    async def test_unregister_nonexistent(self):
        """Test unregistering a nonexistent webhook."""
        result = await research_webhook_unregister("nonexistent-id")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_test_webhook_success(self):
        """Test sending a test notification."""
        # Register a webhook
        reg_result = await research_webhook_register(
            url="https://example.com/webhook",
            events=["tool.completed"],
        )
        webhook_id = reg_result["webhook_id"]

        # Mock successful delivery
        mock_response = MagicMock()
        mock_response.status_code = 200

        from loom.webhooks import get_webhook_manager

        manager = get_webhook_manager()

        with patch.object(manager, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            # Send test notification
            result = await research_webhook_test(webhook_id)

            assert result["status"] == "success"
            assert result["webhook_id"] == webhook_id
            assert "message" in result

    @pytest.mark.asyncio
    async def test_test_webhook_not_found(self):
        """Test testing a nonexistent webhook."""
        with pytest.raises(ValueError):
            await research_webhook_test("nonexistent-id")

    @pytest.mark.asyncio
    async def test_webhook_full_lifecycle(self):
        """Test complete webhook lifecycle."""
        # 1. Register
        reg_result = await research_webhook_register(
            url="https://example.com/webhook",
            events=["tool.completed"],
            secret="test-secret-123",
        )
        webhook_id = reg_result["webhook_id"]
        assert reg_result["active"] is True

        # 2. List (verify it exists)
        list_result = await research_webhook_list()
        webhook_data = next(
            (w for w in list_result["webhooks"] if w["webhook_id"] == webhook_id),
            None
        )
        assert webhook_data is not None
        assert webhook_data["url"] == "https://example.com/webhook"
        # Secret should be masked in list
        assert "***" in webhook_data["secret"]

        # 3. Test
        mock_response = MagicMock()
        mock_response.status_code = 200

        from loom.webhooks import get_webhook_manager

        manager = get_webhook_manager()

        with patch.object(manager, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.post = AsyncMock(return_value=mock_response)

            test_result = await research_webhook_test(webhook_id)
            assert test_result["status"] == "success"

        # 4. Unregister
        unreg_result = await research_webhook_unregister(webhook_id)
        assert unreg_result["success"] is True

        # 5. Verify it's gone
        final_list = await research_webhook_list()
        assert not any(w["webhook_id"] == webhook_id for w in final_list["webhooks"])


class TestWebhookPayloads:
    """Test webhook event payloads."""

    @pytest.mark.asyncio
    async def test_event_payload_format(self):
        """Test that webhook payloads have correct format."""
        from loom.webhooks import get_webhook_manager

        manager = get_webhook_manager()

        # Register webhook
        webhook_id = await manager.register(
            url="https://example.com/webhook",
            events=["tool.completed"],
            secret="test-secret",
        )

        # Mock client to capture POST data
        mock_response = MagicMock()
        mock_response.status_code = 200

        captured_requests = []

        async def capture_post(*args, **kwargs):
            captured_requests.append({
                "url": args[0] if args else kwargs.get("url"),
                "body": kwargs.get("content"),
                "headers": kwargs.get("headers", {}),
            })
            return mock_response

        with patch.object(manager, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.post = capture_post

            # Send a notification
            await manager.notify("tool.completed", {
                "tool_name": "research_fetch",
                "duration": 2.5,
                "success": True,
            })

        # Verify captured request
        assert len(captured_requests) == 1
        request = captured_requests[0]

        # Parse body
        body = json.loads(request["body"])
        assert body["event"] == "tool.completed"
        assert "timestamp" in body
        assert body["webhook_id"] == webhook_id
        assert body["payload"]["tool_name"] == "research_fetch"
        assert body["payload"]["duration"] == 2.5
        assert body["payload"]["success"] is True

        # Verify headers
        headers = request["headers"]
        assert headers["Content-Type"] == "application/json"
        assert "X-Loom-Signature" in headers
        assert headers["X-Loom-Event"] == "tool.completed"
        assert headers["X-Loom-Webhook-ID"] == webhook_id
        assert headers["User-Agent"] == "Loom/1.0"
