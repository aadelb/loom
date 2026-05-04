"""Credit-based billing system for tools with PostgreSQL backend.

Provides:
- Credit weights per tool (light, medium, heavy)
- Balance checking before execution
- Credit deduction tracking with idempotency
- PostgreSQL-backed credit ledger (with JSON fallback)

Backend selection:
- LOOM_BILLING_BACKEND env var: "postgres", "json" (default)
- If PostgreSQL unavailable, automatically falls back to JSON
"""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

# Backend selection
_BILLING_BACKEND = os.environ.get("LOOM_BILLING_BACKEND", "json").lower()

# Lazy import pg_store
_pg_store = None


async def _get_pg_store():
    """Lazy-load and return PgStore instance, or None if unavailable."""
    global _pg_store
    if _pg_store is None:
        try:
            from loom.pg_store import get_store
            _pg_store = await get_store()
        except Exception as e:
            log.warning(f"pg_store unavailable for credits: {e}")
            _pg_store = False  # Mark as permanently unavailable
    return _pg_store if _pg_store is not False else None


# Credit weights per tool (after stripping research_ prefix)
CREDIT_WEIGHTS: dict[str, int] = {
    # Light tools (1 credit)
    "search": 1,
    "text_analyze": 1,
    "detect_language": 1,
    "llm_classify": 1,
    "sentiment_deep": 1,
    "stylometry": 1,
    "geoip_local": 1,
    "fact_checker": 1,
    "llm_embed": 1,
    "llm_extract": 1,
    # Medium tools (3 credits)
    "fetch": 3,
    "spider": 3,
    "markdown": 3,
    "whois": 3,
    "dns_lookup": 3,
    "screenshot": 3,
    "github": 3,
    "cert_analyze": 3,
    "security_headers": 3,
    "breach_check": 3,
    "pdf_extract": 3,
    "rss_fetch": 3,
    "social_search": 3,
    "metadata_forensics": 3,
    "passive_recon": 3,
    "ip_reputation": 3,
    "cve_lookup": 3,
    # Heavy tools (10 credits)
    "deep": 10,
    "dark_forum": 10,
    "ask_all_models": 10,
    "prompt_reframe": 10,
    "auto_reframe": 10,
    "adaptive_reframe": 10,
    "camoufox": 10,
    "botasaurus": 10,
    "onion_discover": 10,
    "multi_search": 10,
    "infra_correlator": 10,
    "dead_content": 10,
    "invisible_web": 10,
    "js_intel": 10,
    "knowledge_graph": 10,
}

DEFAULT_WEIGHT = 2  # Unknown tools cost 2 credits


def get_tool_cost(tool_name: str) -> int:
    """Get credit cost for a tool.

    Strips research_ prefix and looks up in CREDIT_WEIGHTS table.
    Falls back to DEFAULT_WEIGHT for unknown tools.

    Args:
        tool_name: Tool name (with or without research_ prefix)

    Returns:
        Credit cost (1, 2, 3, or 10)
    """
    clean = tool_name.replace("research_", "", 1)
    return CREDIT_WEIGHTS.get(clean, DEFAULT_WEIGHT)


def check_balance(credits: int, tool_name: str) -> bool:
    """Check if customer has sufficient credits for a tool.

    Args:
        credits: Current credit balance
        tool_name: Tool name to check cost for

    Returns:
        True if credits >= cost, False otherwise
    """
    cost = get_tool_cost(tool_name)
    return credits >= cost


def deduct(credits: int, tool_name: str) -> tuple[int, int]:
    """Deduct credits for a tool execution.

    Args:
        credits: Current credit balance
        tool_name: Tool name being executed

    Returns:
        Tuple of (remaining_credits, cost_charged)
        remaining_credits will be at least 0 (no negative balances)
    """
    cost = get_tool_cost(tool_name)
    remaining = max(0, credits - cost)
    return remaining, cost


async def deduct_with_idempotency(
    customer_id: str,
    tool_name: str,
    current_credits: int,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Deduct credits with idempotency protection.

    Prevents duplicate credit deductions by checking the idempotency key.
    If the operation was already performed, returns the cached result.

    Uses PostgreSQL credit ledger (if configured) for audit trail.

    Args:
        customer_id: Customer identifier
        tool_name: Tool name to deduct credits for
        current_credits: Current credit balance
        idempotency_key: Optional idempotency key (auto-generated if not provided)

    Returns:
        Dict with:
        - remaining_credits: Credit balance after deduction
        - cost_charged: Number of credits deducted
        - idempotency_key: The key used (for reference)
        - is_duplicate: True if this was a cached result from previous request
        - success: True if deduction succeeded
    """
    from loom.billing.idempotency import (
        generate_idempotency_key,
        get_idempotency_manager,
    )

    # Generate key if not provided
    if idempotency_key is None:
        idempotency_key = generate_idempotency_key(
            customer_id,
            "credit_deduct",
            {"tool_name": tool_name, "credits_before": current_credits},
        )

    # Check if operation already performed
    manager = await get_idempotency_manager()
    cached_result = await manager.check_and_store(idempotency_key)

    if cached_result is not None:
        # Return cached result from previous execution
        return {
            "remaining_credits": cached_result["remaining_credits"],
            "cost_charged": cached_result["cost_charged"],
            "idempotency_key": idempotency_key,
            "is_duplicate": True,
            "success": True,
        }

    # Perform deduction
    remaining, cost_charged = deduct(current_credits, tool_name)

    # Log to PostgreSQL ledger if available
    if _BILLING_BACKEND == "postgres":
        store = await _get_pg_store()
        if store:
            try:
                await store.update_credits(
                    customer_id=customer_id,
                    amount=-cost_charged,
                    reason=f"tool_usage_{tool_name}"
                )
                log.debug(f"Recorded credit deduction in PG: customer={customer_id}, tool={tool_name}, cost={cost_charged}")
            except Exception as e:
                log.error(f"Failed to log deduction in PG: {e}")

    # Store result for future idempotent checks
    operation_result = {
        "remaining_credits": remaining,
        "cost_charged": cost_charged,
        "customer_id": customer_id,
        "tool_name": tool_name,
    }
    await manager.check_and_store(idempotency_key, operation_result)

    return {
        "remaining_credits": remaining,
        "cost_charged": cost_charged,
        "idempotency_key": idempotency_key,
        "is_duplicate": False,
        "success": True,
    }


async def get_credit_ledger(customer_id: str) -> list[dict[str, Any]]:
    """Get credit ledger for a customer.

    Retrieves all credit adjustments from PostgreSQL (if configured).

    Args:
        customer_id: Customer identifier

    Returns:
        List of ledger entries with amount, reason, timestamp
    """
    if _BILLING_BACKEND == "postgres":
        store = await _get_pg_store()
        if store:
            try:
                # Query credits_ledger table
                from loom.pg_store import get_pool
                pool = await get_pool()
                async with pool.acquire() as conn:
                    rows = await conn.fetch(
                        "SELECT * FROM credits_ledger WHERE customer_id = $1 ORDER BY created_at DESC",
                        customer_id
                    )
                    return [dict(row) for row in rows]
            except Exception as e:
                log.error(f"Failed to get ledger from PG: {e}")

    return []
