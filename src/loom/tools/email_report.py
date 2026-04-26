"""Email research results via Gmail SMTP.

Tool:
- research_email_report: Send research findings via email
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger("loom.tools.email_report")

# Email validation regex (basic RFC 5322 pattern)
_EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

# Constraints
MAX_SUBJECT_CHARS = 200
MAX_BODY_CHARS = 50000
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


def _validate_email(email: str) -> bool:
    """Validate email format."""
    return bool(_EMAIL_REGEX.match(email))


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
    if not _validate_email(to):
        return {
            "error": "invalid recipient email format",
            "to": to,
            "status": "failed",
        }

    # Validate subject length
    if len(subject) > MAX_SUBJECT_CHARS:
        return {
            "error": f"subject exceeds {MAX_SUBJECT_CHARS} chars",
            "to": to,
            "status": "failed",
        }

    # Validate body length
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
            "error": "missing SMTP credentials (SMTP_USER/SMTP_APP_PASSWORD or GMAIL_USER/GMAIL_APP_PASSWORD)",
            "to": to,
            "status": "failed",
        }

    # Validate sender email
    if not _validate_email(smtp_user):
        return {
            "error": "invalid sender email in credentials",
            "to": to,
            "status": "failed",
        }

    loop = asyncio.get_running_loop()

    def _send_email() -> tuple[bool, str]:
        """Synchronous SMTP send operation."""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = to

            # Attach body
            msg.attach(
                MIMEText(body, "html" if html else "plain", _charset="utf-8")
            )

            # Connect and send
            with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=30) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, to, msg.as_string())

            return True, "email sent successfully"

        except smtplib.SMTPAuthenticationError:
            return False, "SMTP authentication failed (invalid credentials)"
        except smtplib.SMTPException as exc:
            return False, f"SMTP error: {exc!s}"
        except TimeoutError:
            return False, "SMTP connection timeout"
        except Exception as exc:
            return False, f"unexpected error: {exc!s}"

    success, message = await loop.run_in_executor(None, _send_email)

    if success:
        logger.info("email_sent to=%s subject=%s", to, subject[:50])
        return {
            "status": "sent",
            "to": to,
            "subject": subject,
        }
    else:
        logger.warning("email_failed to=%s error=%s", to, message)
        return {
            "status": "failed",
            "to": to,
            "error": message,
        }
