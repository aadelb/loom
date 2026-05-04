"""Billing and credit management system for Loom.

Supports PostgreSQL backend (LOOM_BILLING_BACKEND=postgres) with graceful
fallback to JSON/JSONL storage.
"""

from loom.billing.cost_tracker import (
    LLM_PROVIDER_COSTS,
    REVENUE_PER_CREDIT,
    SEARCH_PROVIDER_COSTS,
    aggregate_provider_costs,
    check_margin_health,
    compute_margin,
    estimate_call_cost,
    estimate_revenue,
)
from loom.billing.customers import (
    create_customer,
    get_customer,
    initialize_billing_backend,
    list_customers,
    revoke_key,
    rotate_key,
    update_credits,
    validate_key,
)
from loom.billing.credits import (
    CREDIT_WEIGHTS,
    DEFAULT_WEIGHT,
    check_balance,
    deduct,
    deduct_with_idempotency,
    get_credit_ledger,
    get_tool_cost,
)
from loom.billing.isolation import (
    get_customer_audit_dir,
    get_customer_cache_dir,
    get_customer_session_dir,
    verify_isolation,
)
from loom.billing.meter import (
    get_top_tools,
    get_usage,
    record_usage,
    record_usage_idempotent,
)
from loom.billing.overage import (
    TOPUP_AMOUNT_USD,
    TOPUP_CREDITS,
    apply_topup,
    check_overage,
    get_overage_mode,
)
from loom.billing.stripe_integration import StripeIntegration
from loom.billing.tiers import (
    TIERS,
    Tier,
    can_access_tool,
    check_upgrade_path,
    get_tier,
)
from loom.billing.tier_gating import requires_tier
from loom.billing.token_economy import (
    TOOL_COSTS,
    DEFAULT_COST,
    check_balance as check_balance_token,
    deduct_credits,
    get_balance,
    get_tool_cost as get_tool_cost_token,
)

__all__ = [
    # Backend initialization
    "initialize_billing_backend",
    # Customer management
    "create_customer",
    "get_customer",
    "validate_key",
    "revoke_key",
    "rotate_key",
    "update_credits",
    "list_customers",
    # Credits and tiers
    "CREDIT_WEIGHTS",
    "DEFAULT_WEIGHT",
    "get_tool_cost",
    "check_balance",
    "deduct",
    "deduct_with_idempotency",
    "get_credit_ledger",
    # Metering
    "record_usage",
    "record_usage_idempotent",
    "get_usage",
    "get_top_tools",
    # Tiers
    "TIERS",
    "Tier",
    "can_access_tool",
    "check_upgrade_path",
    "get_tier",
    "requires_tier",
    # Cost tracking
    "LLM_PROVIDER_COSTS",
    "SEARCH_PROVIDER_COSTS",
    "REVENUE_PER_CREDIT",
    "estimate_call_cost",
    "estimate_revenue",
    "compute_margin",
    "aggregate_provider_costs",
    "check_margin_health",
    # Isolation
    "get_customer_cache_dir",
    "get_customer_audit_dir",
    "get_customer_session_dir",
    "verify_isolation",
    # Overage
    "TOPUP_AMOUNT_USD",
    "TOPUP_CREDITS",
    "check_overage",
    "get_overage_mode",
    "apply_topup",
    # Stripe
    "StripeIntegration",
    # Token economy
    "TOOL_COSTS",
    "DEFAULT_COST",
    "check_balance_token",
    "deduct_credits",
    "get_balance",
    "get_tool_cost_token",
]
