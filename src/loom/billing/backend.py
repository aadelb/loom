"""Billing backend initialization and configuration.

Manages the selection and initialization of the billing backend (PostgreSQL or JSON).
Provides a single initialization function to be called on server startup.
"""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

# Supported backends
SUPPORTED_BACKENDS = ("postgres", "json")
DEFAULT_BACKEND = "json"


def get_configured_backend() -> str:
    """Get the configured billing backend from environment.

    Reads LOOM_BILLING_BACKEND env var. Defaults to "json" if not set.

    Returns:
        Backend name: "postgres" or "json"
    """
    backend = os.environ.get("LOOM_BILLING_BACKEND", DEFAULT_BACKEND).lower()
    if backend not in SUPPORTED_BACKENDS:
        log.warning(f"Invalid LOOM_BILLING_BACKEND={backend}, defaulting to {DEFAULT_BACKEND}")
        return DEFAULT_BACKEND
    return backend


async def initialize_billing() -> dict[str, Any]:
    """Initialize the billing system.

    - Detects configured backend from LOOM_BILLING_BACKEND env var
    - For PostgreSQL: Creates tables via pg_store.ensure_schema()
    - For JSON: Ensures directory exists
    - Falls back to JSON if PostgreSQL init fails
    - Always succeeds (guaranteed to have a working backend)

    Returns:
        Dict with:
        - backend: str (postgres or json)
        - status: str (initialized, fallback, or error)
        - message: str (details about initialization)
    """
    from loom.billing.customers import initialize_billing_backend

    result = await initialize_billing_backend()
    log.info(f"Billing system initialized: {result['backend']}")
    return result


async def verify_backend() -> dict[str, Any]:
    """Verify the billing backend is operational.

    Performs a basic health check of the configured backend.

    Returns:
        Dict with:
        - backend: str (postgres or json)
        - status: str (healthy, degraded, or error)
        - details: dict (backend-specific status info)
    """
    backend = get_configured_backend()

    if backend == "postgres":
        try:
            from loom.pg_store import research_pg_status
            status_result = await research_pg_status()
            return {
                "backend": "postgres",
                "status": "healthy" if status_result.get("status") == "connected" else "degraded",
                "details": status_result,
            }
        except Exception as e:
            log.error(f"Failed to verify PostgreSQL backend: {e}")
            return {
                "backend": "postgres",
                "status": "error",
                "details": {"error": str(e)},
            }
    else:
        # JSON backend is always available
        from loom.billing.meter import _METER_DIR
        from loom.billing.customers import _CUSTOMERS_FILE

        return {
            "backend": "json",
            "status": "healthy",
            "details": {
                "customers_file": str(_CUSTOMERS_FILE),
                "customers_file_exists": _CUSTOMERS_FILE.exists(),
                "meter_dir": str(_METER_DIR),
                "meter_dir_exists": _METER_DIR.exists(),
            },
        }


# ===== Billing backend info =====


BACKEND_INFO = {
    "postgres": {
        "name": "PostgreSQL",
        "description": "Full ACID compliance, audit trail, scaling for enterprise",
        "tables": ["customers", "credits_ledger", "usage_meter", "audit_log"],
        "env_var": "DATABASE_URL",
        "env_default": "postgresql://loom:loom_secure_2026@localhost:5432/loom_db",
        "features": [
            "Transactional credit updates",
            "Comprehensive audit logging",
            "Scalable for high throughput",
            "Automatic table creation",
        ],
    },
    "json": {
        "name": "JSON File",
        "description": "Zero external dependencies, suitable for dev/small deployments",
        "files": ["~/.loom/customers.json", "~/.loom/meters/"],
        "features": [
            "No database setup required",
            "File-based audit trail (JSONL)",
            "Simple backup/restore",
            "Limited to single-machine deployments",
        ],
    },
}


def describe_backends() -> dict[str, Any]:
    """Get detailed information about available backends.

    Returns:
        Dict mapping backend names to configuration details
    """
    return BACKEND_INFO
