"""Tests for error alerting system."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, Mock, patch
from loom.alerting import send_alert, handle_tool_error, _is_critical_error, ALERT_LEVELS


class TestAlertLevels:
    """Test alert level constants."""

    def test_alert_levels_defined(self) -> None:
        """Verify alert levels are properly defined."""
        assert ALERT_LEVELS == {"info", "warning", "error", "critical"}


class TestIsCriticalError:
    """Test error criticality classification."""

    def test_circuit_breaker_is_critical(self) -> None:
        """CircuitBreaker errors are critical."""
        error = RuntimeError("CircuitBreakerOpen: rate limit exceeded")
        assert _is_critical_error(error) is True

    def test_ssrf_is_critical(self) -> None:
        """SSRF errors are critical."""
        error = RuntimeError("SSRF_DETECTED: invalid url")
        assert _is_critical_error(error) is True

    def test_authentication_error_is_critical(self) -> None:
        """Authentication errors are critical."""
        error = RuntimeError("Authentication failed: invalid token")
        assert _is_critical_error(error) is True

    def test_normal_error_not_critical(self) -> None:
        """Normal errors are not critical."""
        error = ValueError("invalid input")
        assert _is_critical_error(error) is False

    def test_error_string_classification(self) -> None:
        """String-based error classification works."""
        assert _is_critical_error("circuit_breaker timeout") is True
        assert _is_critical_error("authorization denied") is True
        assert _is_critical_error("normal error message") is False


@pytest.mark.asyncio
class TestSendAlert:
    """Test send_alert function."""

    async def test_send_alert_invalid_level(self) -> None:
        """Invalid alert level returns failed status."""
        result = await send_alert("invalid", "test message")
        assert result["status"] == "failed"
        assert result["level"] == "invalid"
        assert "invalid alert level" in result["error"]

    async def test_send_alert_info_no_notification(self) -> None:
        """Info level alerts don't send webhooks or emails."""
        with patch("loom.alerting.logger") as mock_logger:
            result = await send_alert("info", "test info")
            assert result["level"] == "info"
            assert result["webhook_notified"] is False
            assert result["email_notified"] is False
            mock_logger.info.assert_called()

    async def test_send_alert_critical_with_webhook(self) -> None:
        """Critical level alerts send webhooks."""
        mock_manager = AsyncMock()
        mock_manager.notify.return_value = {
            "succeeded": 1,
            "total_webhooks": 1,
            "results": [],
        }

        with patch("loom.webhooks.get_webhook_manager", return_value=mock_manager):
            with patch("loom.alerting.logger"):
                result = await send_alert(
                    "critical",
                    "critical error",
                    details={"tool": "test_tool"},
                )

        assert result["level"] == "critical"
        mock_manager.notify.assert_called_once()

        # Verify notify was called with alert.error event
        call_args = mock_manager.notify.call_args
        assert call_args[0][0] == "alert.error"
        assert call_args[0][1]["level"] == "critical"

    async def test_send_alert_error_with_email(self, monkeypatch) -> None:
        """Error level alerts send emails if configured."""
        monkeypatch.setenv("LOOM_ALERT_EMAIL", "admin@example.com")

        mock_email_func = AsyncMock(
            return_value={"status": "sent", "to": "admin@example.com"}
        )

        with patch("loom.alerting.research_email_report", mock_email_func):
            with patch("loom.alerting.logger"):
                result = await send_alert(
                    "error",
                    "error message",
                    details={"tool": "test_tool", "error_type": "ValueError"},
                )

        assert result["level"] == "error"
        assert result["email_notified"] is True
        mock_email_func.assert_called_once()

        # Verify email parameters
        call_kwargs = mock_email_func.call_args[1]
        assert call_kwargs["to"] == "admin@example.com"
        assert "ERROR" in call_kwargs["subject"]
        assert "error message" in call_kwargs["body"]

    async def test_send_alert_warning_with_email_only(self, monkeypatch) -> None:
        """Warning level alerts send emails but not webhooks."""
        monkeypatch.setenv("LOOM_ALERT_EMAIL", "admin@example.com")

        mock_email_func = AsyncMock(
            return_value={"status": "sent", "to": "admin@example.com"}
        )

        with patch("loom.alerting.research_email_report", mock_email_func):
            with patch("loom.alerting.logger"):
                result = await send_alert("warning", "warning message")

        assert result["level"] == "warning"
        assert result["email_notified"] is True
        assert result["webhook_notified"] is False

    async def test_send_alert_email_not_configured(self) -> None:
        """If LOOM_ALERT_EMAIL not set, email is skipped."""
        import os
        os.environ.pop("LOOM_ALERT_EMAIL", None)

        with patch("loom.alerting.logger"):
            result = await send_alert("warning", "test warning")

        assert result["email_notified"] is False
        assert result["status"] == "skipped"

    async def test_send_alert_includes_details(self) -> None:
        """Alert payload includes all provided details."""
        mock_manager = AsyncMock()
        mock_manager.notify.return_value = {"succeeded": 1, "total_webhooks": 1}

        with patch("loom.webhooks.get_webhook_manager", return_value=mock_manager):
            with patch("loom.alerting.logger"):
                details = {
                    "tool": "research_fetch",
                    "error_type": "TimeoutError",
                    "execution_time_ms": 60000,
                }
                await send_alert("error", "test error", details=details)

        # Check that details were included in webhook payload
        call_args = mock_manager.notify.call_args
        payload = call_args[0][1]
        assert payload["tool"] == "research_fetch"
        assert payload["error_type"] == "TimeoutError"
        assert payload["execution_time_ms"] == 60000


@pytest.mark.asyncio
class TestHandleToolError:
    """Test handle_tool_error function."""

    async def test_handle_tool_error_critical(self) -> None:
        """Critical errors trigger alerts."""
        mock_alert = AsyncMock()

        with patch("loom.alerting.send_alert", mock_alert):
            with patch("loom.alerting.logger"):
                error = RuntimeError("CircuitBreakerOpen: rate limit")
                await handle_tool_error("research_fetch", error, 100.0)

        mock_alert.assert_called_once()
        call_args = mock_alert.call_args
        assert call_args[1]["level"] == "critical"
        assert "research_fetch" in call_args[1]["message"]

    async def test_handle_tool_error_non_critical(self) -> None:
        """Non-critical errors only log, no alert."""
        mock_alert = AsyncMock()

        with patch("loom.alerting.send_alert", mock_alert):
            with patch("loom.alerting.logger") as mock_logger:
                error = ValueError("invalid input")
                await handle_tool_error("research_fetch", error)

        # No alert should be sent
        mock_alert.assert_not_called()
        # But should log warning
        mock_logger.warning.assert_called()

    async def test_handle_tool_error_includes_context(self) -> None:
        """Tool error handling includes execution context."""
        mock_alert = AsyncMock()

        with patch("loom.alerting.send_alert", mock_alert):
            with patch("loom.alerting.logger"):
                error = RuntimeError("SSRF_DETECTED: blocked url")
                await handle_tool_error("research_fetch", error, 500.0)

        call_args = mock_alert.call_args
        details = call_args[1]["details"]
        assert details["tool"] == "research_fetch"
        assert details["error_type"] == "RuntimeError"
        assert details["execution_time_ms"] == 500.0

    async def test_handle_tool_error_truncates_message(self) -> None:
        """Very long error messages are truncated."""
        mock_alert = AsyncMock()

        with patch("loom.alerting.send_alert", mock_alert):
            with patch("loom.alerting.logger"):
                long_error_msg = "x" * 1000
                error = RuntimeError(f"SSRF: {long_error_msg}")
                await handle_tool_error("test_tool", error)

        call_args = mock_alert.call_args
        details = call_args[1]["details"]
        # Message should be capped at 500 chars
        assert len(details["error_message"]) <= 500


@pytest.mark.asyncio
async def test_alerting_integration():
    """Integration test: error in tool triggers alert."""
    from loom.alerting import handle_tool_error

    # Simulate a critical error
    mock_webhook = AsyncMock()
    mock_webhook.notify.return_value = {"succeeded": 1, "total_webhooks": 1}

    with patch("loom.webhooks.get_webhook_manager", return_value=mock_webhook):
        with patch("loom.alerting.logger"):
            error = RuntimeError("circuit_breaker timeout")
            await handle_tool_error("research_deep", error, 45000.0)

    # Verify webhook was called
    assert mock_webhook.notify.called
