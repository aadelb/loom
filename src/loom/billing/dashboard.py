"""Usage dashboard — customer usage stats and analytics.

Provides:
- Comprehensive usage statistics for a customer
- Credit usage breakdown by tool
- Usage alerts at defined thresholds (50%, 80%, 100%)
"""

from __future__ import annotations

from typing import Any

from loom.billing.customers import _load_customers
from loom.billing.meter import get_top_tools, get_usage


def get_dashboard(customer_id: str, date: str | None = None) -> dict[str, Any]:
    """Get comprehensive usage dashboard for a customer.

    Aggregates customer tier information, credit balance, usage statistics,
    and top tools by credit consumption for a given date.

    Args:
        customer_id: Customer identifier
        date: Date in YYYY-MM-DD format (defaults to today UTC)

    Returns:
        Dict with:
        - customer_id: Customer identifier
        - tier: Customer tier (free, pro, team, enterprise)
        - credits_total: Total credits available
        - credits_used: Total credits consumed today
        - credits_remaining: Available credits (total - used)
        - usage_percent: Percentage of credits used (0-100)
        - calls_today: Number of tool calls made today
        - top_tools: List of top 10 tools by credit usage
        - by_tool: Dict mapping tool names to total credits used
        - date: Date queried
        - error: Error message if customer not found (mutually exclusive with above)
    """
    customers = _load_customers()
    customer = customers.get(customer_id)

    if not customer:
        return {"error": "customer_not_found", "customer_id": customer_id}

    usage = get_usage(customer_id, date)
    top = get_top_tools(customer_id, date, limit=10)

    credits_total = customer.get("credits", 0)
    credits_used = usage.get("total_credits", 0)
    credits_remaining = max(0, credits_total - credits_used)

    # Avoid division by zero
    usage_percent = round(
        credits_used / max(credits_total, 1) * 100, 1
    )

    return {
        "customer_id": customer_id,
        "tier": customer.get("tier", "free"),
        "credits_total": credits_total,
        "credits_used": credits_used,
        "credits_remaining": credits_remaining,
        "usage_percent": usage_percent,
        "calls_today": usage.get("total_calls", 0),
        "top_tools": top,
        "by_tool": usage.get("by_tool", {}),
        "date": usage.get("date", ""),
    }


def get_usage_alerts(customer_id: str) -> list[dict[str, Any]]:
    """Check for usage alerts based on credit consumption thresholds.

    Returns alerts at 50%, 80%, and 100% of credit limits.
    Higher severity alerts (critical > warning > info) take precedence.

    Args:
        customer_id: Customer identifier

    Returns:
        List of alert dicts with:
        - level: "info" (50%), "warning" (80%), or "critical" (100%)
        - message: Human-readable alert message
        - percent: Current usage percentage
    """
    dashboard = get_dashboard(customer_id)

    # Return empty list if customer not found
    if "error" in dashboard:
        return []

    alerts = []
    pct = dashboard["usage_percent"]

    if pct >= 100:
        alerts.append({
            "level": "critical",
            "message": "Credit limit reached",
            "percent": pct,
        })
    elif pct >= 80:
        alerts.append({
            "level": "warning",
            "message": "80% of credits used",
            "percent": pct,
        })
    elif pct >= 50:
        alerts.append({
            "level": "info",
            "message": "50% of credits used",
            "percent": pct,
        })

    return alerts
