"""Overage handling — hard stop or auto top-up when credits exhausted.

Implements two modes for handling credit insufficiency:
- hard_stop: Return error (402 Payment Required)
- auto_topup: Automatically add $20 (2000 credits) and proceed

Configuration is per-customer, stored in customer profile.
"""

from __future__ import annotations

from typing import Any

from loom.errors import LoomError

# Top-up amounts (fixed)
TOPUP_AMOUNT_USD = 20  # USD
TOPUP_CREDITS = 2000  # Credits per $20

# Default mode for customers without explicit configuration
DEFAULT_OVERAGE_MODE = "hard_stop"


def check_overage(
    credits_remaining: int,
    tool_cost: int,
    overage_mode: str = DEFAULT_OVERAGE_MODE,
    tool_name: str = "unknown",
) -> dict[str, Any]:
    """Check if customer can proceed, handle overage with hard stop or auto top-up.

    When credits are sufficient, allows execution immediately.
    When credits are insufficient:
    - hard_stop mode: Returns error response (402-like)
    - auto_topup mode: Returns success with topup action and adjusted balance

    Args:
        credits_remaining: Current credit balance (non-negative integer)
        tool_cost: Cost of the requested tool (positive integer)
        overage_mode: "hard_stop" or "auto_topup" (default: hard_stop)
        tool_name: Name of tool being executed (for error messages)

    Returns:
        Dict with decision and metadata:
        - On success: {"allowed": True, "action": "proceed", "remaining": int}
        - On topup: {"allowed": True, "action": "topup", "topup_amount_usd": 20,
                     "topup_credits": 2000, "remaining": int, "message": str}
        - On hard stop: LoomError.insufficient_credits() response dict
    """
    # Sufficient credits: allow immediately
    if credits_remaining >= tool_cost:
        return {
            "allowed": True,
            "action": "proceed",
            "remaining": credits_remaining - tool_cost,
        }

    # Insufficient credits with auto_topup: add credits and allow
    if overage_mode == "auto_topup":
        new_balance = credits_remaining + TOPUP_CREDITS
        return {
            "allowed": True,
            "action": "topup",
            "topup_amount_usd": TOPUP_AMOUNT_USD,
            "topup_credits": TOPUP_CREDITS,
            "remaining": new_balance - tool_cost,
            "message": f"Auto top-up: +{TOPUP_CREDITS} credits (${TOPUP_AMOUNT_USD})",
        }

    # Insufficient credits with hard_stop: return error
    return LoomError.insufficient_credits(
        tool_name=tool_name,
        required=tool_cost,
        available=credits_remaining,
    )


def get_overage_mode(customer_config: dict[str, Any] | None) -> str:
    """Get customer's overage mode preference.

    Looks for "overage_mode" key in customer config, falls back to default.

    Args:
        customer_config: Customer configuration dict (can be None or empty)

    Returns:
        "hard_stop" or "auto_topup"
    """
    if not customer_config:
        return DEFAULT_OVERAGE_MODE

    mode_value = customer_config.get("overage_mode", DEFAULT_OVERAGE_MODE)
    # Ensure mode_value is a string and validate it
    mode = str(mode_value) if mode_value is not None else DEFAULT_OVERAGE_MODE

    # Validate mode is one of the allowed values
    if mode not in ("hard_stop", "auto_topup"):
        return DEFAULT_OVERAGE_MODE

    return mode


def apply_topup(
    credits_remaining: int,
    topup_credits: int = TOPUP_CREDITS,
) -> tuple[int, int]:
    """Apply a credit top-up to a customer's balance.

    Returns new balance and amount added.

    Args:
        credits_remaining: Current credit balance
        topup_credits: Amount of credits to add (default: TOPUP_CREDITS)

    Returns:
        Tuple of (new_balance, amount_added)
    """
    new_balance = credits_remaining + topup_credits
    return new_balance, topup_credits
