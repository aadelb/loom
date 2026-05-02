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
    """Send notification to log/email/slack channel.

    Args: channel: "log"|"email"|"slack", title, message, severity: "info"|"warning"|"error"|"critical"
    Returns: {sent: bool, channel, notification_id, timestamp}
    """
    notification_id, timestamp = str(uuid.uuid4())[:8], datetime.now(UTC).isoformat()
    notification = {"id": notification_id, "channel": channel, "title": title, "message": message, "severity": severity, "timestamp": timestamp}

    if channel == "log":
        try:
            with open(NOTIFICATIONS_FILE, "a") as f:
                f.write(json.dumps(notification) + "\n")
        except Exception as e:
            return {"sent": False, "error": str(e)}
    elif channel == "email":
        notification["payload"] = {"subject": f"[{severity.upper()}] {title}", "body": message}
    elif channel == "slack":
        notification["payload"] = {
            "text": title,
            "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": f"*{title}*\n{message}"}}],
            "color": {"info": "#36a64f", "warning": "#ff9900", "error": "#dd0000", "critical": "#990000"}.get(severity, "#808080"),
        }
    return {"sent": True, "channel": channel, "notification_id": notification_id, "timestamp": timestamp}


async def research_notify_history(
    limit: int = 50,
    severity: str = "all",
) -> dict[str, Any]:
    """Retrieve notification history from JSONL file.

    Args: limit (max returned), severity: filter by level or "all"
    Returns: {notifications: list, total: int}
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
                        notifications.append({
                            "id": notif["id"],
                            "channel": notif["channel"],
                            "title": notif["title"],
                            "severity": notif["severity"],
                            "timestamp": notif["timestamp"],
                        })
    except Exception:
        return {"notifications": [], "total": 0}
    return {"notifications": notifications[-limit:], "total": len(notifications)}


async def research_notify_rules(
    action: str = "list",
    rule: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Manage notification rules for auto-alerts.

    Args: action: "list"|"add", rule: {event, channel, severity}
    Returns: {rules: list, total: int}
    """
    rules = []
    if RULES_FILE.exists():
        try:
            with open(RULES_FILE) as f:
                rules = json.load(f)
        except Exception:
            pass

    if action == "list":
        return {"rules": rules, "total": len(rules)}
    elif action == "add" and rule and all(k in rule for k in ["event", "channel", "severity"]):
        rule_id = str(uuid.uuid4())[:8]
        rules.append({**rule, "id": rule_id})
        try:
            with open(RULES_FILE, "w") as f:
                json.dump(rules, f, indent=2)
        except Exception as e:
            return {"error": str(e)}
    return {"rules": rules, "total": len(rules)}
