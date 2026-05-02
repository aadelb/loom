"""Metric alerting rules engine for Loom — create, check, and manage alert rules."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

logger = logging.getLogger("loom.tools.metric_alerts")

METRICS = {"error_rate", "latency_p95", "memory_mb", "queue_depth", "cache_hit_rate"}
CONDITIONS = {"gt", "lt", "eq", "gte", "lte"}
ACTIONS = {"log", "notify", "circuit_break"}


def _get_rules_path() -> Path:
    """Get alert rules file path."""
    rules_dir = Path.home() / ".loom"
    rules_dir.mkdir(exist_ok=True)
    return rules_dir / "alert_rules.json"


def _load_rules() -> dict[str, Any]:
    """Load alert rules from disk."""
    path = _get_rules_path()
    if not path.exists():
        return {"rules": {}, "triggers": {}}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load rules: %s", e)
        return {"rules": {}, "triggers": {}}


def _save_rules(data: dict[str, Any]) -> None:
    """Save alert rules to disk."""
    path = _get_rules_path()
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        logger.error("Failed to save rules: %s", e)


def _check_condition(value: float, condition: str, threshold: float) -> bool:
    """Evaluate condition: value <condition> threshold."""
    if condition == "gt":
        return value > threshold
    if condition == "lt":
        return value < threshold
    if condition == "eq":
        return value == threshold
    if condition == "gte":
        return value >= threshold
    if condition == "lte":
        return value <= threshold
    return False


async def research_alert_create(
    name: str,
    metric: str,
    condition: str,
    threshold: float,
    action: str = "log",
) -> dict[str, Any]:
    """Create an alerting rule.

    Args:
        name: Rule name (unique identifier)
        metric: One of error_rate, latency_p95, memory_mb, queue_depth, cache_hit_rate
        condition: One of gt, lt, eq, gte, lte
        threshold: Numeric threshold value
        action: One of log, notify, circuit_break

    Returns:
        Dict with rule_id, name, metric, condition, threshold, action, created
    """
    if metric not in METRICS:
        return {"error": f"Invalid metric. Must be one of: {METRICS}"}
    if condition not in CONDITIONS:
        return {"error": f"Invalid condition. Must be one of: {CONDITIONS}"}
    if action not in ACTIONS:
        return {"error": f"Invalid action. Must be one of: {ACTIONS}"}

    data = _load_rules()
    rule_id = str(uuid4())[:8]

    rule = {
        "id": rule_id,
        "name": name,
        "metric": metric,
        "condition": condition,
        "threshold": threshold,
        "action": action,
        "created": datetime.now(UTC).isoformat(),
        "triggers_count": 0,
    }

    data["rules"][rule_id] = rule
    _save_rules(data)

    logger.info("alert_rule_created rule_id=%s name=%s", rule_id, name)
    return rule


async def research_alert_check(metric_values: dict[str, float] | None = None) -> dict[str, Any]:
    """Evaluate all rules against current metric values.

    Args:
        metric_values: Dict mapping metric names to current values.
                      If None, uses defaults (all 0.0).

    Returns:
        Dict with rules_checked, alerts_triggered, all_clear
    """
    if metric_values is None:
        metric_values = {m: 0.0 for m in METRICS}

    data = _load_rules()
    rules = data.get("rules", {})
    alerts_triggered = []

    for rule_id, rule in rules.items():
        metric = rule.get("metric")
        value = metric_values.get(metric, 0.0)
        condition = rule.get("condition")
        threshold = rule.get("threshold", 0)

        if _check_condition(value, condition, threshold):
            alerts_triggered.append({
                "rule_name": rule.get("name"),
                "metric": metric,
                "value": value,
                "threshold": threshold,
                "action": rule.get("action"),
            })
            rule["triggers_count"] = rule.get("triggers_count", 0) + 1

    _save_rules(data)

    return {
        "rules_checked": len(rules),
        "alerts_triggered": alerts_triggered,
        "all_clear": len(alerts_triggered) == 0,
    }


async def research_alert_list() -> dict[str, Any]:
    """List all alert rules.

    Returns:
        Dict with rules list and total count
    """
    data = _load_rules()
    rules = list(data.get("rules", {}).values())
    return {
        "rules": rules,
        "total": len(rules),
    }
