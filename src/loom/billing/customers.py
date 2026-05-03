"""Customer and API key management.

Provides:
- Create customers with unique API keys (prefix: loom_live_, loom_test_)
- Validate API keys on request
- Revoke and rotate keys
- Store customer data in ~/.loom/customers.json
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import logging
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_CUSTOMERS_FILE = Path.home() / ".loom" / "customers.json"


def _load_customers() -> dict[str, Any]:
    """Load customers database from file."""
    if _CUSTOMERS_FILE.exists():
        try:
            return json.loads(_CUSTOMERS_FILE.read_text())
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"Failed to load customers.json: {e}, returning empty dict")
            return {}
    return {}


def _save_customers(data: dict[str, Any]) -> None:
    """Atomically save customers database to file."""
    _CUSTOMERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Use tmp + replace pattern for atomicity
    tmp_file = _CUSTOMERS_FILE.parent / f".customers-{secrets.token_hex(4)}.tmp"
    tmp_file.write_text(json.dumps(data, indent=2))
    # Restrict file permissions to owner only before atomically replacing
    os.chmod(tmp_file, 0o600)
    tmp_file.replace(_CUSTOMERS_FILE)


def create_customer(
    name: str, email: str, tier: str = "free"
) -> dict[str, str]:
    """Create a new customer with a unique API key.

    Args:
        name: Customer name
        email: Customer email
        tier: One of 'free', 'pro', 'team', 'enterprise'

    Returns:
        Dict with customer_id, api_key, and tier
    """
    if tier not in ("free", "pro", "team", "enterprise"):
        raise ValueError(f"Invalid tier: {tier}")

    customers = _load_customers()

    # Generate unique customer ID
    customer_id = hashlib.sha256(
        f"{name}{email}{secrets.token_hex(8)}".encode()
    ).hexdigest()[:16]

    # Generate API key and hash it for storage
    api_key = f"loom_live_{secrets.token_hex(24)}"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    # Credit limits per tier
    credit_limits = {
        "free": 500,
        "pro": 10_000,
        "team": 50_000,
        "enterprise": 200_000,
    }

    customers[customer_id] = {
        "name": name,
        "email": email,
        "tier": tier,
        "api_key": api_key_hash,
        "credits": credit_limits[tier],
        "created_at": datetime.now(UTC).isoformat(),
        "active": True,
    }

    _save_customers(customers)
    log.info(f"Created customer: {customer_id}, tier={tier}, email={email}")

    return {
        "customer_id": customer_id,
        "api_key": api_key,
        "tier": tier,
    }


def validate_key(api_key: str) -> dict[str, Any] | None:
    """Validate an API key and return customer info if valid.

    Args:
        api_key: The API key to validate

    Returns:
        Dict with customer_id and customer info if valid, None otherwise
    """
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    customers = _load_customers()

    for customer_id, info in customers.items():
        if info.get("api_key") == key_hash and info.get("active"):
            return {"customer_id": customer_id, **info}

    return None


def revoke_key(customer_id: str) -> bool:
    """Revoke a customer's API key (mark inactive).

    Args:
        customer_id: The customer ID to revoke

    Returns:
        True if revoked, False if customer not found
    """
    customers = _load_customers()

    if customer_id not in customers:
        return False

    customers[customer_id]["active"] = False
    _save_customers(customers)
    log.info(f"Revoked API key for customer: {customer_id}")

    return True


def rotate_key(customer_id: str) -> dict[str, str] | None:
    """Rotate a customer's API key (generate new, revoke old).

    Args:
        customer_id: The customer ID to rotate

    Returns:
        Dict with new api_key and customer_id, or None if customer not found
    """
    customers = _load_customers()

    if customer_id not in customers:
        return None

    info = customers[customer_id]

    # Generate new API key
    new_api_key = f"loom_live_{secrets.token_hex(24)}"
    new_api_key_hash = hashlib.sha256(new_api_key.encode()).hexdigest()

    # Update customer record
    info["api_key"] = new_api_key_hash
    info["rotated_at"] = datetime.now(UTC).isoformat()

    _save_customers(customers)
    log.info(f"Rotated API key for customer: {customer_id}")

    return {
        "customer_id": customer_id,
        "api_key": new_api_key,
    }


def get_customer(customer_id: str) -> dict[str, Any] | None:
    """Get customer info by ID.

    Args:
        customer_id: The customer ID

    Returns:
        Customer info dict or None if not found
    """
    customers = _load_customers()
    return customers.get(customer_id)


def update_credits(customer_id: str, amount: int) -> bool:
    """Update a customer's credit balance.

    Args:
        customer_id: The customer ID
        amount: Amount to change by (can be negative)

    Returns:
        True if updated, False if customer not found
    """
    lock_path = _CUSTOMERS_FILE.with_suffix(".lock")
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            customers = _load_customers()

            if customer_id not in customers:
                return False

            current = customers[customer_id].get("credits", 0)
            new_balance = max(0, current + amount)
            customers[customer_id]["credits"] = new_balance

            _save_customers(customers)
            log.info(
                f"Updated credits for {customer_id}: {current} -> {new_balance} "
                f"(delta={amount})"
            )

            return True
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def list_customers() -> list[dict[str, Any]]:
    """List all customers (excluding api_key hash for security).

    Returns:
        List of customer info dicts
    """
    customers = _load_customers()
    result = []

    for customer_id, info in customers.items():
        safe_info = {
            "customer_id": customer_id,
            "name": info.get("name"),
            "email": info.get("email"),
            "tier": info.get("tier"),
            "credits": info.get("credits"),
            "active": info.get("active"),
            "created_at": info.get("created_at"),
        }
        result.append(safe_info)

    return result
