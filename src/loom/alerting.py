"""Error alerting system for critical server errors.

Provides centralized alerting to webhook and email on critical errors.
Integrates with WebhookManager and email_report tool.

Alert levels:
- info: Informational messages (no alert sent)
- warning: Warning messages (sent to email if configured)
- error: Error messages (sent to webhook and email)
- critical: Critical errors (sent to webhook and email, logged at critical level)
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("loom.alerting")

# Alert severity levels
ALERT_LEVELS = {"info", "warning", "error", "critical"}


async def send_alert(
    level: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Send an alert via webhook and/or email on critical errors.

    Determines alert routing based on severity level:
    - info: Log only, no external notification
    - warning: Log and send email if configured
    - error: Send webhook (if registered for "alert.error") and email
    - critical: Send webhook and email, log at critical level

    Args:
        level: Alert severity ("info", "warning", "error", "critical")
        message: Human-readable alert message
        details: Additional context dict (tool, error, timestamp, etc.)

    Returns:
        Dict with keys:
        - status: "sent", "skipped", or "failed"
        - level: Alert level used
        - message: The alert message
        - webhook_notified: bool (True if webhook was sent)
        - email_notified: bool (True if email was sent)
        - error: Optional error message if something failed
    """
    if level not in ALERT_LEVELS:
        logger.warning("invalid_alert_level level=%s", level)
        return {
            "status": "failed",
            "level": level,
            "message": message,
            "error": f"invalid alert level: {level}",
            "webhook_notified": False,
            "email_notified": False,
        }

    details = details or {}
    timestamp = datetime.now(UTC).isoformat()

    # Build alert payload
    alert_payload = {
        "level": level,
        "message": message,
        "timestamp": timestamp,
        **details,
    }

    webhook_notified = False
    email_notified = False
    webhook_error = None
    email_error = None

    # Log based on level
    if level == "critical":
        logger.critical("alert_critical message=%s details=%s", message, details)
    elif level == "error":
        logger.error("alert_error message=%s details=%s", message, details)
    elif level == "warning":
        logger.warning("alert_warning message=%s details=%s", message, details)
    else:  # info
        logger.info("alert_info message=%s details=%s", message, details)

    # Send webhook notification for error and critical levels
    if level in ("error", "critical"):
        try:
            from loom.webhooks import get_webhook_manager

            webhook_manager = get_webhook_manager()
            result = await webhook_manager.notify("alert.error", alert_payload)

            webhook_notified = result.get("succeeded", 0) > 0
            if not webhook_notified:
                webhook_error = f"No webhooks received notification (total={result.get('total_webhooks', 0)})"
            else:
                logger.info(
                    "webhook_alert_sent level=%s message=%s webhooks=%d",
                    level,
                    message,
                    result.get("succeeded", 0),
                )
        except Exception as e:
            webhook_error = f"webhook_notify_failed: {str(e)[:100]}"
            logger.error("webhook_alert_failed level=%s error=%s", level, webhook_error)

    # Send email notification for warning, error, and critical levels
    if level in ("warning", "error", "critical"):
        alert_email = os.environ.get("LOOM_ALERT_EMAIL", "").strip()
        if alert_email:
            try:
                from loom.tools.infrastructure.email_report import research_email_report

                # Format email subject and body
                subject = f"[Loom Alert - {level.upper()}] {message[:100]}"
                body_lines = [
                    f"Alert Level: {level.upper()}",
                    f"Timestamp: {timestamp}",
                    f"Message: {message}",
                    "",
                    "Details:",
                ]

                # Add details to body
                for key, value in details.items():
                    if key != "timestamp":  # Skip duplicate timestamp
                        value_str = str(value)[:500]  # Cap detail values
                        body_lines.append(f"  {key}: {value_str}")

                body = "\n".join(body_lines)

                result = await research_email_report(
                    to=alert_email,
                    subject=subject,
                    body=body,
                    html=False,
                )

                if result.get("status") == "sent":
                    email_notified = True
                    logger.info(
                        "email_alert_sent level=%s to=%s subject=%s",
                        level,
                        alert_email,
                        subject[:50],
                    )
                else:
                    email_error = result.get("error", "unknown email error")
                    logger.warning("email_alert_failed level=%s error=%s", level, email_error)

            except Exception as e:
                email_error = f"email_notify_failed: {str(e)[:100]}"
                logger.error("email_alert_failed level=%s error=%s", level, email_error)

    # Determine overall status
    status = "sent" if (webhook_notified or email_notified) else "skipped"
    if webhook_error or email_error:
        status = "failed"

    return {
        "status": status,
        "level": level,
        "message": message,
        "timestamp": timestamp,
        "webhook_notified": webhook_notified,
        "email_notified": email_notified,
        "webhook_error": webhook_error,
        "email_error": email_error,
    }


def _is_critical_error(error: Exception | str) -> bool:
    """Check if an error should be classified as critical.

    Critical errors:
    - CircuitBreakerOpen: Rate limiter circuit breaker opened
    - SecurityError/SSRFError: Security policy violations
    - AuthenticationError: Authentication failures
    - RuntimeError with "circuit" or "timeout" in message

    Args:
        error: Exception or error string to classify

    Returns:
        True if error is critical, False otherwise
    """
    error_str = str(error).lower()

    critical_keywords = {
        "circuitbreaker",
        "circuit_breaker",
        "ssrf",
        "authentication",
        "authorization",
        "forbidden",
        "security",
        "secret_manager",
        "key_rotation",
    }

    for keyword in critical_keywords:
        if keyword in error_str:
            return True

    return False


async def handle_tool_error(
    tool_name: str,
    error: Exception,
    execution_time_ms: float | None = None,
) -> None:
    """Handle a tool execution error by determining criticality and sending alerts.

    Classifies error severity and sends alerts via webhook/email as appropriate.
    Always logs the error; only sends external alerts for critical errors.

    Args:
        tool_name: Name of the tool that failed
        error: The exception that was raised
        execution_time_ms: Optional execution duration before failure
    """
    error_type = type(error).__name__
    is_critical = _is_critical_error(error)

    # Build details dict
    details = {
        "tool": tool_name,
        "error_type": error_type,
        "error_message": str(error)[:500],
    }

    if execution_time_ms is not None:
        details["execution_time_ms"] = execution_time_ms

    # Send alert if critical
    if is_critical:
        await send_alert(
            level="critical",
            message=f"Critical error in tool {tool_name}: {error_type}",
            details=details,
        )
    else:
        # Log non-critical errors without sending alert
        logger.warning(
            "tool_error_non_critical tool=%s error_type=%s",
            tool_name,
            error_type,
        )
