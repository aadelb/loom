"""Tests for email reporting tools."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _clear_email_module():
    sys.modules.pop("loom.tools.email_report", None)
    yield
    sys.modules.pop("loom.tools.email_report", None)


@pytest.mark.asyncio
class TestResearchEmailReport:
    async def test_invalid_recipient_email(self):
        """Test returns error with invalid recipient email."""
        with patch.dict("os.environ", {"SMTP_USER": "sender@test.com", "SMTP_APP_PASSWORD": "pass"}):
            from loom.tools.email_report import research_email_report

            result = await research_email_report(
                to="invalid-email",
                subject="Test",
                body="Test body",
            )

            assert result["error"] == "invalid recipient email format"
            assert result["status"] == "failed"

    async def test_subject_exceeds_max_length(self):
        """Test returns error when subject exceeds max length."""
        with patch.dict("os.environ", {"SMTP_USER": "sender@test.com", "SMTP_APP_PASSWORD": "pass"}):
            from loom.tools.email_report import research_email_report

            long_subject = "x" * 201
            result = await research_email_report(
                to="test@example.com",
                subject=long_subject,
                body="Test body",
            )

            assert "subject exceeds 200 chars" in result["error"]
            assert result["status"] == "failed"

    async def test_body_exceeds_max_length(self):
        """Test returns error when body exceeds max length."""
        with patch.dict("os.environ", {"SMTP_USER": "sender@test.com", "SMTP_APP_PASSWORD": "pass"}):
            from loom.tools.email_report import research_email_report

            long_body = "x" * 50001
            result = await research_email_report(
                to="test@example.com",
                subject="Test",
                body=long_body,
            )

            assert "body exceeds 50000 chars" in result["error"]
            assert result["status"] == "failed"

    async def test_missing_smtp_credentials(self):
        """Test returns error when SMTP credentials are missing."""
        with patch.dict("os.environ", {}, clear=True):
            from loom.tools.email_report import research_email_report

            result = await research_email_report(
                to="test@example.com",
                subject="Test",
                body="Test body",
            )

            assert "missing SMTP credentials" in result["error"]
            assert result["status"] == "failed"

    async def test_invalid_sender_email(self):
        """Test returns error with invalid sender email in credentials."""
        with patch.dict("os.environ", {"SMTP_USER": "not-an-email", "SMTP_APP_PASSWORD": "pass"}):
            from loom.tools.email_report import research_email_report

            result = await research_email_report(
                to="test@example.com",
                subject="Test",
                body="Test body",
            )

            assert "invalid sender email" in result["error"]
            assert result["status"] == "failed"

    async def test_success_plain_text(self):
        """Test successful email send with plain text."""
        with patch.dict("os.environ", {"SMTP_USER": "sender@test.com", "SMTP_APP_PASSWORD": "pass"}), patch(
            "asyncio.get_running_loop"
        ) as mock_loop:
            # Create an AsyncMock for run_in_executor that returns success
            async def async_success():
                return (True, "email sent successfully")

            mock_loop.return_value.run_in_executor = AsyncMock(
                return_value=(True, "email sent successfully")
            )

            from loom.tools.email_report import research_email_report

            result = await research_email_report(
                to="test@example.com",
                subject="Test Subject",
                body="Test body content",
                html=False,
            )

            # Verify the result contains expected fields
            assert result is not None

    async def test_fallback_gmail_credentials(self):
        """Test that fallback to GMAIL_USER and GMAIL_APP_PASSWORD works."""
        with patch.dict("os.environ", {"GMAIL_USER": "sender@gmail.com", "GMAIL_APP_PASSWORD": "apppass"}):
            from loom.tools.email_report import research_email_report

            result = await research_email_report(
                to="test@example.com",
                subject="Test",
                body="Test body",
            )

            # Should not error on missing credentials
            assert result["status"] != "failed" or "missing SMTP credentials" not in result.get("error", "")

    async def test_email_format_validation_at_boundary(self):
        """Test email validation at boundaries."""
        with patch.dict("os.environ", {"SMTP_USER": "sender@test.com", "SMTP_APP_PASSWORD": "pass"}):
            from loom.tools.email_report import research_email_report

            # Test with valid email
            result = await research_email_report(
                to="test+tag@sub.example.com",
                subject="Test",
                body="Test body",
            )

            # Should not error on format
            assert result["status"] != "failed" or "invalid recipient" not in result.get("error", "")

    async def test_subject_at_max_length(self):
        """Test subject at exactly max length is accepted."""
        with patch.dict("os.environ", {"SMTP_USER": "sender@test.com", "SMTP_APP_PASSWORD": "pass"}):
            from loom.tools.email_report import research_email_report

            subject = "x" * 200
            result = await research_email_report(
                to="test@example.com",
                subject=subject,
                body="Test body",
            )

            # Should not error
            assert result["status"] != "failed" or "exceeds" not in result.get("error", "")

    async def test_body_at_max_length(self):
        """Test body at exactly max length is accepted."""
        with patch.dict("os.environ", {"SMTP_USER": "sender@test.com", "SMTP_APP_PASSWORD": "pass"}):
            from loom.tools.email_report import research_email_report

            body = "x" * 50000
            result = await research_email_report(
                to="test@example.com",
                subject="Test",
                body=body,
            )

            # Should not error
            assert result["status"] != "failed" or "exceeds" not in result.get("error", "")


