"""Customer data isolation — namespace cache, sessions, and audit by customer.

Provides:
- Separate cache directories per customer
- Separate audit directories per customer
- Separate session directories per customer
- ID sanitization for safe filesystem use
- Isolation verification to ensure no cross-customer data leakage
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _sanitize_id(customer_id: str) -> str:
    """Sanitize customer ID for filesystem use.

    Removes special characters, prevents path traversal, and enforces length limits.
    Non-alphanumeric characters (except hyphen and underscore) are replaced with underscores.
    This prevents directory traversal and hidden file attacks.

    Args:
        customer_id: Raw customer ID (may contain special chars)

    Returns:
        Safe filesystem-friendly ID (max 64 chars)

    Raises:
        ValueError: if customer_id is empty or becomes empty after sanitization
    """
    if not customer_id or not isinstance(customer_id, str):
        raise ValueError("customer_id must be a non-empty string")

    # Replace non-alphanumeric chars (except hyphen and underscore) with underscore
    # This neutralizes: . / \ : | ? * < > and other special chars
    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", customer_id)

    # If result is empty after sanitization, raise error
    if not safe:
        raise ValueError(f"customer_id became empty after sanitization: {customer_id}")

    # Enforce max length
    return safe[:64]


def get_customer_cache_dir(base_dir: Path, customer_id: str) -> Path:
    """Get customer-specific cache directory.

    Creates a namespaced directory under base_dir/customers/{sanitized_id}
    to isolate all cached responses for this customer.

    Args:
        base_dir: Base cache directory (e.g., ~/.cache/loom)
        customer_id: Customer ID to isolate

    Returns:
        Path to customer's cache directory (created if not exists)

    Raises:
        ValueError: if customer_id is invalid
    """
    safe_id = _sanitize_id(customer_id)
    customer_dir = base_dir / "customers" / safe_id
    customer_dir.mkdir(parents=True, exist_ok=True)
    return customer_dir


def get_customer_audit_dir(base_dir: Path, customer_id: str) -> Path:
    """Get customer-specific audit directory.

    Creates a namespaced directory under base_dir/audit/{sanitized_id}
    to isolate all audit logs and request records for this customer.

    Args:
        base_dir: Base audit directory (e.g., ~/.loom)
        customer_id: Customer ID to isolate

    Returns:
        Path to customer's audit directory (created if not exists)

    Raises:
        ValueError: if customer_id is invalid
    """
    safe_id = _sanitize_id(customer_id)
    audit_dir = base_dir / "audit" / safe_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    return audit_dir


def get_customer_session_dir(base_dir: Path, customer_id: str) -> Path:
    """Get customer-specific session directory.

    Creates a namespaced directory under base_dir/sessions/{sanitized_id}
    to isolate all persistent browser sessions for this customer.

    Args:
        base_dir: Base session directory (e.g., ~/.loom)
        customer_id: Customer ID to isolate

    Returns:
        Path to customer's session directory (created if not exists)

    Raises:
        ValueError: if customer_id is invalid
    """
    safe_id = _sanitize_id(customer_id)
    session_dir = base_dir / "sessions" / safe_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def verify_isolation(
    base_dir: Path, customer_a: str, customer_b: str
) -> dict[str, Any]:
    """Verify two customers have completely separate data paths.

    Checks that:
    - Cache directories are different
    - Audit directories are different
    - Session directories are different
    - No path is a prefix of another (no containment)

    Args:
        base_dir: Base directory used by both customers
        customer_a: First customer ID
        customer_b: Second customer ID

    Returns:
        Dict with 'isolated' (bool), 'paths_a', and 'paths_b' path mappings

    Raises:
        ValueError: if either customer_id is invalid
    """
    dirs_a = {
        "cache": get_customer_cache_dir(base_dir, customer_a),
        "audit": get_customer_audit_dir(base_dir, customer_a),
        "session": get_customer_session_dir(base_dir, customer_a),
    }
    dirs_b = {
        "cache": get_customer_cache_dir(base_dir, customer_b),
        "audit": get_customer_audit_dir(base_dir, customer_b),
        "session": get_customer_session_dir(base_dir, customer_b),
    }

    # Check that all directories are different
    isolated = all(dirs_a[k] != dirs_b[k] for k in dirs_a)

    # Check for path containment (no prefix relationships)
    no_overlap = all(
        not str(dirs_a[k]).startswith(str(dirs_b[k]))
        and not str(dirs_b[k]).startswith(str(dirs_a[k]))
        for k in dirs_a
    )

    return {
        "isolated": isolated and no_overlap,
        "paths_a": {k: str(v) for k, v in dirs_a.items()},
        "paths_b": {k: str(v) for k, v in dirs_b.items()},
    }
