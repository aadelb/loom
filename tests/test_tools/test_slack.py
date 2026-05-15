"""Unit tests for research_slack_notify — Slack message delivery."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import Response

from loom.tools.infrastructure.slack import research_slack_notify, _validate_channel


class TestSlackValidation:
    """Slack channel validation tests."""

    def test_validate_channel_public(self) -> None:
        """Validation accepts public channel format."""
        assert _validate_channel("#general") is True
        assert _validate_channel("#my-channel") is True
        assert _validate_channel("#channel_name") is True

    def test_validate_channel_id(self) -> None:
        """Validation accepts Slack channel IDs."""
        assert _validate_channel("C1234567890") is True
        assert _validate_channel("CABCDEFGH") is True

    def test_validate_channel_invalid(self) -> None:
        """Validation rejects invalid channel formats."""
        assert _validate_channel("") is False
        assert _validate_channel("channel-no-hash") is False
        assert _validate_channel("@user") is False
        assert _validate_channel("#") is False


class TestSlackNotify:
    """research_slack_notify sends messages to Slack."""

    @pytest.mark.asyncio
    async def test_slack_notify_invalid_channel(self) -> None:
        """Rejects invalid channel format."""
        result = await research_slack_notify(channel="invalid", text="Hello")

        assert result["status"] == "failed"
        assert "invalid channel format" in result["error"]

    @pytest.mark.asyncio
    async def test_slack_notify_missing_token(self) -> None:
        """Rejects when SLACK_BOT_TOKEN not set."""
        # Clear token
        old_token = os.environ.pop("SLACK_BOT_TOKEN", None)

        try:
            result = await research_slack_notify(channel="#general", text="Hello")

            assert result["status"] == "failed"
            assert "missing SLACK_BOT_TOKEN" in result["error"]
        finally:
            if old_token:
                os.environ["SLACK_BOT_TOKEN"] = old_token

    @pytest.mark.asyncio
    async def test_slack_notify_invalid_token_format(self) -> None:
        """Rejects tokens not starting with xoxb-."""
        os.environ["SLACK_BOT_TOKEN"] = "invalid-token-format"

        try:
            result = await research_slack_notify(channel="#general", text="Hello")

            assert result["status"] == "failed"
            assert "invalid token format" in result["error"]
        finally:
            os.environ.pop("SLACK_BOT_TOKEN", None)

    @pytest.mark.asyncio
    async def test_slack_notify_text_too_long(self) -> None:
        """Rejects text exceeding 4000 characters."""
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-validtoken"

        try:
            long_text = "x" * 5000
            result = await research_slack_notify(channel="#general", text=long_text)

            assert result["status"] == "failed"
            assert "exceeds" in result["error"]
        finally:
            os.environ.pop("SLACK_BOT_TOKEN", None)

    @pytest.mark.asyncio
    async def test_slack_notify_no_text_or_blocks(self) -> None:
        """Rejects when neither text nor blocks provided."""
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-validtoken"

        try:
            result = await research_slack_notify(channel="#general", text="")

            assert result["status"] == "failed"
            assert "must be provided" in result["error"]
        finally:
            os.environ.pop("SLACK_BOT_TOKEN", None)

    @pytest.mark.asyncio
    async def test_slack_notify_success_with_text(self) -> None:
        """Successfully sends text message to Slack."""
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-validtoken"

        try:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(
                    return_value={"ok": True, "ts": "1234567890.123456"}
                )

                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                result = await research_slack_notify(
                    channel="#general", text="Hello Slack"
                )

                assert result["status"] == "sent"
                assert result["ts"] == "1234567890.123456"
                assert result["channel"] == "#general"
        finally:
            os.environ.pop("SLACK_BOT_TOKEN", None)

    @pytest.mark.asyncio
    async def test_slack_notify_success_with_blocks(self) -> None:
        """Successfully sends Block Kit formatted message."""
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-validtoken"

        try:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(
                    return_value={"ok": True, "ts": "9876543210.654321"}
                )

                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                blocks = [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": "Hello *World*"},
                    }
                ]

                result = await research_slack_notify(
                    channel="C1234567890", blocks=blocks
                )

                assert result["status"] == "sent"
                assert result["ts"] == "9876543210.654321"
        finally:
            os.environ.pop("SLACK_BOT_TOKEN", None)

    @pytest.mark.asyncio
    async def test_slack_notify_thread_reply(self) -> None:
        """Sends message to thread correctly."""
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-validtoken"

        try:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(
                    return_value={"ok": True, "ts": "1111111111.111111"}
                )

                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                result = await research_slack_notify(
                    channel="#general",
                    text="Thread reply",
                    thread_ts="1234567890.123456",
                )

                assert result["status"] == "sent"
                # Verify thread_ts was passed to API
                call_args = mock_client.post.call_args
                assert call_args[1]["json"]["thread_ts"] == "1234567890.123456"
        finally:
            os.environ.pop("SLACK_BOT_TOKEN", None)

    @pytest.mark.asyncio
    async def test_slack_notify_channel_not_found(self) -> None:
        """Handles channel_not_found error."""
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-validtoken"

        try:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(
                    return_value={"ok": False, "error": "channel_not_found"}
                )

                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                result = await research_slack_notify(channel="#deleted", text="Hi")

                assert result["status"] == "failed"
                assert "channel not found" in result["error"]
        finally:
            os.environ.pop("SLACK_BOT_TOKEN", None)

    @pytest.mark.asyncio
    async def test_slack_notify_no_permission(self) -> None:
        """Handles no_permission error."""
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-validtoken"

        try:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(
                    return_value={"ok": False, "error": "no_permission"}
                )

                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                result = await research_slack_notify(channel="#general", text="Hi")

                assert result["status"] == "failed"
                assert "no permission" in result["error"].lower()
        finally:
            os.environ.pop("SLACK_BOT_TOKEN", None)

    @pytest.mark.asyncio
    async def test_slack_notify_rate_limited(self) -> None:
        """Handles rate_limited error with retry_after."""
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-validtoken"

        try:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json = MagicMock(
                    return_value={
                        "ok": False,
                        "error": "rate_limited",
                        "retry_after": 30,
                    }
                )

                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                result = await research_slack_notify(channel="#general", text="Hi")

                assert result["status"] == "failed"
                assert "rate limited" in result["error"]
                assert "30" in result["details"]
        finally:
            os.environ.pop("SLACK_BOT_TOKEN", None)

    @pytest.mark.asyncio
    async def test_slack_notify_http_timeout(self) -> None:
        """Handles HTTP timeout."""
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-validtoken"

        try:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                from httpx import TimeoutException

                mock_client.post = AsyncMock(side_effect=TimeoutException("timeout"))
                mock_client_class.return_value.__aenter__.return_value = mock_client

                result = await research_slack_notify(channel="#general", text="Hi")

                assert result["status"] == "failed"
                assert "timeout" in result["error"].lower()
        finally:
            os.environ.pop("SLACK_BOT_TOKEN", None)

    @pytest.mark.asyncio
    async def test_slack_notify_http_error_response(self) -> None:
        """Handles HTTP errors."""
        os.environ["SLACK_BOT_TOKEN"] = "xoxb-validtoken"

        try:
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_response = MagicMock()
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"

                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client_class.return_value.__aenter__.return_value = mock_client

                result = await research_slack_notify(channel="#general", text="Hi")

                assert result["status"] == "failed"
                assert "HTTP 500" in result["error"]
        finally:
            os.environ.pop("SLACK_BOT_TOKEN", None)
