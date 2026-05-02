"""Notification system for alerting on important events."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger("loom.tools.notifications")

NOTIFICATIONS_DIR = Path.home() / ".loom"
NOTIFICATIONS_DIR.mkdir(parents=True, exist_ok=True)
NOTIFICATIONS_FILE = NOTIFICATIONS_DIR / "notifications.jsonl"
RULES_FILE = NOTIFICATIONS_DIR / "notification_rules.json"


async def research_notify_send(
    channel: str = "log",
    title: str = "",
    message: str = "",
    severity: str = "info",
) -> dict[str, Any]:
    """Send a notification to a channel.

    Args:
        channel: "log", "email", or "slack"
        title: notification title
        message: notification message
        severity: "info", "warning", "error", "critical"

    Returns:
        Dict with keys: sent, channel, notification_id, timestamp
    """
    notification_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now(UTC).isoformat()

    notification = {
        "id": notification_id,
        "channel": channel,
        "title": title,
        "message": message,
        "severity": severity,
        "timestamp": timestamp,
    }

    if channel == "log":
        try:
            with open(NOTIFICATIONS_FILE, "a") as f:
                f.write(json.dumps(notification) + "\n")
            logger.info(f"Notification sent to log: {notification_id}")
        except Exception as e:
            logger.error(f"Failed to write notification: {e}")
            return {"sent": False, "error": str(e)}
    elif channel == "email":
        payload = {
            "to": "",  # Caller provides recipient
            "subject": f"[{severity.upper()}] {title}",
            "body": message,
        }
        notification["payload"] = payload
    elif channel == "slack":
        payload = {
            "text": title,
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"*{title}*\n{message}"}}
            ],
            "color": {"info": "#36a64f", "warning": "#ff9900", "error": "#dd0000", "critical": "#990000"}.get(
                severity, "#808080"
            ),
        }
        notification["payload"] = payload

    return {"sent": True, "channel": channel, "notification_id": notification_id, "timestamp": timestamp}


async def research_notify_history(
    limit: int = 50,
    severity: str = "all",
) -> dict[str, Any]:
    """Retrieve notification history from JSONL file.

    Args:
        limit: max notifications to return
        severity: filter by "info", "warning", "error", "critical", or "all"

    Returns:
        Dict with keys: notifications, total
    """
    notifications = []
    if not NOTIFICATIONS_FILE.exists():
        return {"notifications": [], "total": 0}

    try:
        with open(NOTIFICATIONS_FILE) as f:
            for line in f:
                if line.strip():
                    notif = json.loads(line)
                    if severity == "all" or notif.get("severity") == severity:
                        notifications.append(
                            {
                                "id": notif["id"],
                                "channel": notif["channel"],
                                "title": notif["title"],
                                "severity": notif["severity"],
                                "timestamp": notif["timestamp"],
                            }
                        )
    except Exception as e:
        logger.error(f"Failed to read notifications: {e}")
        return {"notifications": [], "total": 0}

    return {"notifications": notifications[-limit:], "total": len(notifications)}


async def research_notify_rules(
    action: str = "list",
    rule: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Manage notification rules for auto-alerts.

    Args:
        action: "list" or "add"
        rule: rule dict with keys: event, channel, severity

    Returns:
        Dict with keys: rules, total
    """
    rules = []
    if RULES_FILE.exists():
        try:
            with open(RULES_FILE) as f:
                rules = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")

    if action == "list":
        return {"rules": rules, "total": len(rules)}
    elif action == "add" and rule:
        if all(k in rule for k in ["event", "channel", "severity"]):
            rules.append({**rule, "id": str(uuid.uuid4())[:8]})
            try:
                with open(RULES_FILE, "w") as f:
                    json.dump(rules, f, indent=2)
                logger.info(f"Rule added: {rule.get('event')}")
            except Exception as e:
                logger.error(f"Failed to save rules: {e}")
                return {"error": str(e)}
        return {"rules": rules, "total": len(rules)}
    return {"rules": rules, "total": len(rules)}
