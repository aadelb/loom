"""Billing and usage tracking tools for API monetization.

Tools:
- research_usage_report: Aggregate LLM usage and costs over a period
- research_stripe_balance: Get Stripe account balance
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from loom.error_responses import handle_tool_errors
from loom.http_helpers import fetch_json

logger = logging.getLogger("loom.tools.billing")

_STRIPE_API_BASE = "https://api.stripe.com/v1"


def _read_billing_logs(cache_dir: Path, cutoff_date: datetime) -> tuple[float, dict[str, dict[str, Any]], dict[str, float], dict[str, float], int]:
    """Read and aggregate billing logs (blocking I/O).

    Args:
        cache_dir: Path to cache directory
        cutoff_date: Earliest timestamp to include

    Returns:
        Tuple of (total_cost, calls_by_provider, calls_by_day, model_costs, call_count)
    """
    total_cost = 0.0
    calls_by_provider: dict[str, dict[str, Any]] = {}
    calls_by_day: dict[str, float] = {}
    model_costs: dict[str, float] = {}
    call_count = 0

    for log_file in sorted(cache_dir.glob("llm_cost_*.json")):
        try:
            file_stat = log_file.stat()
            file_time = datetime.fromtimestamp(file_stat.st_mtime)

            if file_time < cutoff_date:
                continue

            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if not entry:
                            continue

                        cost = entry.get("cost_usd", 0.0)
                        provider = entry.get("provider", "unknown")
                        model = entry.get("model", "unknown")
                        timestamp = entry.get("timestamp", "")

                        total_cost += cost
                        call_count += 1

                        # Track by provider
                        if provider not in calls_by_provider:
                            calls_by_provider[provider] = {
                                "count": 0,
                                "total_cost": 0.0,
                            }
                        calls_by_provider[provider]["count"] += 1
                        calls_by_provider[provider]["total_cost"] += cost

                        # Track by day
                        day = timestamp[:10] if timestamp else "unknown"
                        calls_by_day[day] = calls_by_day.get(day, 0.0) + cost

                        # Track top models
                        model_costs[model] = model_costs.get(model, 0.0) + cost

                    except (json.JSONDecodeError, ValueError):
                        continue
        except Exception as e:
            logger.warning("usage_report_file_error file=%s: %s", log_file.name, e)
            continue

    return total_cost, calls_by_provider, calls_by_day, model_costs, call_count


@handle_tool_errors("research_usage_report")
async def research_usage_report(days: int = 7) -> dict[str, Any]:
    """Aggregate LLM usage and costs from local cost tracker logs.

    Reads cost tracker JSON files from ~/.cache/loom/logs/llm_cost_*.json
    and summarizes total cost, calls by provider, calls by day, and top models.

    Args:
        days: number of days to include in report (default 7)

    Returns:
        Dict with 'total_cost', 'calls_by_provider', 'calls_by_day',
        'top_models', 'report_period'.
    """
    cache_dir = Path.home() / ".cache" / "loom" / "logs"
    if not cache_dir.exists():
        return {
            "total_cost": 0.0,
            "calls_by_provider": {},
            "calls_by_day": {},
            "top_models": [],
            "report_period_days": days,
            "error": "no logs directory found",
        }

    cutoff_date = datetime.now() - timedelta(days=days)

    try:
        # Run blocking I/O in executor
        total_cost, calls_by_provider, calls_by_day, model_costs, call_count = await asyncio.to_thread(
            _read_billing_logs, cache_dir, cutoff_date
        )

        # Sort models by cost
        top_models = sorted(model_costs.items(), key=lambda x: x[1], reverse=True)[:10]

        logger.info(
            "usage_report days=%d total_cost=%.4f calls=%d",
            days,
            total_cost,
            call_count,
        )

        return {
            "total_cost": round(total_cost, 4),
            "calls_by_provider": calls_by_provider,
            "calls_by_day": {k: round(v, 4) for k, v in sorted(calls_by_day.items())},
            "top_models": [{"model": m, "cost": round(c, 4)} for m, c in top_models],
            "total_calls": call_count,
            "report_period_days": days,
        }

    except Exception as e:
        logger.warning("usage_report_failed: %s", e)
        return {
            "total_cost": 0.0,
            "calls_by_provider": {},
            "calls_by_day": {},
            "top_models": [],
            "report_period_days": days,
            "error": str(e),
        }


@handle_tool_errors("research_stripe_balance")
async def research_stripe_balance() -> dict[str, Any]:
    """Get Stripe account balance.

    Args:
        None

    Returns:
        Dict with 'available' (available balance in cents), 'pending'
        (pending balance in cents), or 'error' key if request fails.
    """
    api_key = os.environ.get("STRIPE_LIVE_KEY")
    if not api_key:
        return {
            "error": "STRIPE_LIVE_KEY environment variable not set",
            "available": 0,
            "pending": 0,
        }

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            data = await fetch_json(client,
                f"{_STRIPE_API_BASE}/balance",
                headers=headers,
            )
            if not data:
                raise ValueError("Empty response from Stripe API")

            available = 0
            pending = 0

            for bal in data.get("available", []):
                if bal.get("currency") == "usd":
                    available = bal.get("amount", 0)

            for bal in data.get("pending", []):
                if bal.get("currency") == "usd":
                    pending = bal.get("amount", 0)

            logger.info(
                "stripe_balance available=%d pending=%d",
                available,
                pending,
            )

            return {
                "available": available,
                "pending": pending,
                "available_usd": round(available / 100.0, 2),
                "pending_usd": round(pending / 100.0, 2),
            }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return {
                "error": "Invalid STRIPE_LIVE_KEY",
                "available": 0,
                "pending": 0,
            }
        logger.warning("stripe_api_error status=%d", e.response.status_code)
        return {
            "error": f"API error: {e.response.status_code}",
            "available": 0,
            "pending": 0,
        }
    except Exception as e:
        logger.warning("stripe_balance_failed: %s", e)
        return {
            "error": str(e),
            "available": 0,
            "pending": 0,
        }
