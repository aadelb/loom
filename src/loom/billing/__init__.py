"""Billing and credit management system for Loom."""

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
from loom.billing.isolation import (
    get_customer_audit_dir,
    get_customer_cache_dir,
    get_customer_session_dir,
    verify_isolation,
)
from loom.billing.meter import get_top_tools, get_usage, record_usage
from loom.billing.overage import (
    TOPUP_AMOUNT_USD,
    TOPUP_CREDITS,
    apply_topup,
    check_overage,
    get_overage_mode,
)
from loom.billing.tiers import (
    TIERS,
    Tier,
    can_access_tool,
    check_upgrade_path,
    get_tier,
)

__all__ = [
    "TIERS",
    "Tier",
    "can_access_tool",
    "check_upgrade_path",
    "get_tier",
    "get_top_tools",
    "get_usage",
    "record_usage",
    "LLM_PROVIDER_COSTS",
    "SEARCH_PROVIDER_COSTS",
    "REVENUE_PER_CREDIT",
    "estimate_call_cost",
    "estimate_revenue",
    "compute_margin",
    "aggregate_provider_costs",
    "check_margin_health",
    "get_customer_cache_dir",
    "get_customer_audit_dir",
    "get_customer_session_dir",
    "verify_isolation",
    "TOPUP_AMOUNT_USD",
    "TOPUP_CREDITS",
    "check_overage",
    "get_overage_mode",
    "apply_topup",
]
