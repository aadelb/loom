"""Email research results via Gmail SMTP.

Tool:
- research_email_report: Send research findings via email
"""
from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from loom.input_validators import validate_email, ValidationError
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.email_report")

# Constraints
MAX_SUBJECT_CHARS = 200
MAX_BODY_CHARS = 50000
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


def _sanitize_header(value: str) -> str:
    """Remove newline/carriage return characters from email headers.

    Prevents email header injection via CRLF.
    """
    return value.replace("\r", "").replace("\n", "").replace("\x00", "")


@handle_tool_errors("research_email_report")
async def research_email_report(
    to: str,
    subject: str,
    body: str,
    html: bool = False,
) -> dict[str, Any]:
    """Send research results via Gmail SMTP.

    Sends email via Gmail SMTP (smtp.gmail.com:587, TLS).
    Credentials come from environment variables:
    - SMTP_USER and SMTP_APP_PASSWORD (preferred)
    - GMAIL_USER and GMAIL_APP_PASSWORD (fallback)

    Args:
        to: recipient email address
        subject: email subject (max 200 chars)
        body: email body/content (max 50000 chars)
        html: if True, body is HTML; if False, plain text

    Returns:
        Dict with ``status``, ``to``, and ``subject`` on success,
        or ``error`` on failure.
    """
    # Validate email address
    try:
        validate_email(to)
    except ValidationError:
        return {
            "error": "invalid recipient email format",
            "to": to,
            "status": "failed",
        }

    # Validate and sanitize subject
    subject = _sanitize_header(subject)
    if len(subject) > MAX_SUBJECT_CHARS:
        return {
            "error": f"subject exceeds {MAX_SUBJECT_CHARS} chars",
            "to": to,
            "status": "failed",
        }

    # Validate body length (no sanitization needed for body content)
    if len(body) > MAX_BODY_CHARS:
        return {
            "error": f"body exceeds {MAX_BODY_CHARS} chars",
            "to": to,
            "status": "failed",
        }

    # Get SMTP credentials from environment
    smtp_user = os.environ.get("SMTP_USER") or os.environ.get("GMAIL_USER")
    smtp_password = os.environ.get("SMTP_APP_PASSWORD") or os.environ.get(
        "GMAIL_APP_PASSWORD"
    )

    if not smtp_user or not smtp_password:
        return {
            "error": "SMTP credentials not configured (set SMTP_USER and SMTP_APP_PASSWORD)",
            "to": to,
            "status": "failed",
        }

    try:
        # Run SMTP operation in executor to avoid blocking
        def _send_email():
            msg = MIMEMultipart("alternative")
            msg["From"] = smtp_user
            msg["To"] = to
            msg["Subject"] = subject

            # Attach body (plain text or HTML)
            if html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))

            # Connect to Gmail SMTP server
            server = smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
            server.quit()

        await asyncio.to_thread(_send_email)

        logger.info("email_report_sent to=%s", to)
        return {
            "status": "sent",
            "to": to,
            "subject": subject,
        }

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed")
        return {
            "error": "SMTP authentication failed (check credentials)",
            "to": to,
            "status": "failed",
        }
    except smtplib.SMTPException as exc:
        logger.error("SMTP error: %s", exc)
        return {
            "error": f"SMTP error: {str(exc)}",
            "to": to,
            "status": "failed",
        }
    except Exception as exc:
        logger.exception("email_report_failed")
        return {
            "error": f"email report failed: {str(exc)}",
            "to": to,
            "status": "failed",
        }
