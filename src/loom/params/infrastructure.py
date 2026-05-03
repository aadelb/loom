"""Pydantic parameter models for infrastructure tools."""

"""Pydantic v2 parameter models for all MCP tool arguments.

Each tool has a dedicated model with field validators for URLs, headers,
proxies, etc. All models ignore extra fields and use strict mode.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from loom.config import CONFIG
from loom.validators import filter_headers, validate_js_script, validate_local_file_path, validate_url

# Default Accept-Language header sourced from config
_DEFAULT_ACCEPT_LANG = CONFIG.get("DEFAULT_ACCEPT_LANGUAGE", "en-US,en;q=0.9,ar;q=0.8")



__all__ = [
    "CacheClearParams",
    "CacheStatsParams",
    "CachedStrategyParams",
    "ConfigGetParams",
    "ConfigSetParams",
    "EmailReportParams",
    "NodriverSessionParams",
    "SessionCloseParams",
    "SessionOpenParams",
    "StripeCancelSubscriptionParams",
    "StripeCreateChargeParams",
    "StripeCreateCheckoutParams",
    "StripeCreateSubscriptionParams",
    "StripeGetInvoiceParams",
    "StripeListInvoicesParams",
    "SuggestWorkflowParams",
    "WorkflowCreateParams",
    "WorkflowRunParams",
    "WorkflowStatusParams",
]


class CacheClearParams(BaseModel):
    """Parameters for research_cache_clear tool."""

    days_old: int | None = None
    all: bool = False

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("days_old")
    @classmethod
    def validate_days_old(cls, v: int | None) -> int | None:
        if v is not None and (v < 0 or v > 365):
            raise ValueError("days_old must be 0-365")
        return v




class CacheStatsParams(BaseModel):
    """Parameters for research_cache_stats tool."""

    max_results: int = Field(default=10, alias="limit")
    offset: int = 0

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 1000:
            raise ValueError("max_results must be 1-1000")
        return v

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v: int) -> int:
        if v < 0 or v > 1000000:
            raise ValueError("offset must be 0-1000000")
        return v




class CachedStrategyParams(BaseModel):
    """Parameters for research_cached_strategy tool."""

    topic: str = Field(..., min_length=1, max_length=500)
    model: str = Field(default="auto", max_length=100)
    fallback_strategy: str = Field(default="ethical_anchor", max_length=100)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Validate topic is non-empty and not too long."""
        if not v.strip():
            raise ValueError("topic cannot be empty")
        return v.strip()

    @field_validator("fallback_strategy")
    @classmethod
    def validate_fallback(cls, v: str) -> str:
        """Validate fallback strategy name is valid."""
        if not v.strip():
            raise ValueError("fallback_strategy cannot be empty")
        return v.strip()




class ConfigGetParams(BaseModel):
    """Parameters for research_config_get tool."""

    key: str | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v or len(v) > 200:
                raise ValueError("key must be 1-200 characters")
        return v




class ConfigSetParams(BaseModel):
    """Parameters for research_config_set tool."""

    key: str
    value: Any

    model_config = {"extra": "ignore", "strict": True}




class EmailReportParams(BaseModel):
    """Parameters for research_email_report tool."""

    subject: str = Field(
        description="Email subject",
        max_length=256,
    )
    body: str = Field(
        description="Email body",
        max_length=100000,
    )
    recipient: str = Field(
        description="Recipient email address",
        max_length=256,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("subject cannot be empty")
        return v.strip()

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("body cannot be empty")
        return v.strip()

    @field_validator("recipient")
    @classmethod
    def validate_recipient(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("recipient cannot be empty")
        if "@" not in v:
            raise ValueError("recipient must be valid email")
        return v.strip()




class NodriverSessionParams(BaseModel):
    """Parameters for research_nodriver_session tool."""

    action: Literal["open", "navigate", "extract", "close"]
    session_name: str = "default"
    url: str | None = None
    css_selector: str | None = None
    xpath: str | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_url(v)
        return v

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        if not (1 <= len(v) <= 32):
            raise ValueError("session_name must be 1-32 characters")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("session_name must be alphanumeric, underscore, or hyphen")
        return v

    @field_validator("css_selector")
    @classmethod
    def validate_css_selector(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 512:
            raise ValueError("css_selector max 512 chars")
        return v

    @field_validator("xpath")
    @classmethod
    def validate_xpath(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 512:
            raise ValueError("xpath max 512 chars")
        return v




class SessionCloseParams(BaseModel):
    """Parameters for research_session_close tool."""

    name: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_-]{1,32}$", v):
            raise ValueError("name must match ^[a-z0-9_-]{1,32}$")
        return v




class SessionOpenParams(BaseModel):
    """Parameters for research_session_open tool."""

    name: str
    browser: Literal["camoufox", "chromium", "firefox"] | str = "camoufox"
    ttl_seconds: int = 3600
    login_url: str | None = None
    login_script: str | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_-]{1,32}$", v):
            raise ValueError("name must match ^[a-z0-9_-]{1,32}$")
        return v

    @field_validator("ttl_seconds")
    @classmethod
    def validate_ttl_seconds(cls, v: int) -> int:
        if v < 1 or v > 86400:
            raise ValueError("ttl_seconds must be 1-86400")
        return v

    @field_validator("login_script")
    @classmethod
    def validate_login_script(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_js_script(v)
        return v

    @field_validator("login_url")
    @classmethod
    def validate_login_url(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_url(v)
        return v




class StripeCancelSubscriptionParams(BaseModel):
    """Parameters for research_stripe_billing cancel_subscription."""

    subscription_id: str = Field(
        ...,
        description="Stripe subscription ID",
        min_length=1,
        max_length=64,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("subscription_id")
    @classmethod
    def validate_subscription_id(cls, v: str) -> str:
        """Subscription ID must be non-empty."""
        if not v.strip():
            raise ValueError("subscription_id cannot be empty")
        return v.strip()




class StripeCreateChargeParams(BaseModel):
    """Parameters for research_stripe_billing create_charge."""

    customer_id: str = Field(
        ...,
        description="Loom customer ID",
        min_length=1,
        max_length=64,
    )
    amount_cents: int = Field(
        ...,
        description="Charge amount in cents (e.g., 9999 = $99.99)",
        gt=0,
        le=999999,
    )
    description: str = Field(
        ...,
        description="Charge description",
        min_length=1,
        max_length=256,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Customer ID must be non-empty alphanumeric."""
        if not v.strip():
            raise ValueError("customer_id cannot be empty")
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("customer_id must be alphanumeric, hyphen, or underscore")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Description must be non-empty."""
        if not v.strip():
            raise ValueError("description cannot be empty")
        return v.strip()




class StripeCreateCheckoutParams(BaseModel):
    """Parameters for research_stripe_billing create_checkout_session."""

    customer_id: str = Field(
        ...,
        description="Loom customer ID",
        min_length=1,
        max_length=64,
    )
    tier: Literal["pro", "team", "enterprise"] = Field(
        ...,
        description="Subscription tier (not 'free')",
    )
    success_url: str = Field(
        ...,
        description="URL to redirect on successful payment",
        min_length=10,
        max_length=2048,
    )
    cancel_url: str = Field(
        ...,
        description="URL to redirect if payment cancelled",
        min_length=10,
        max_length=2048,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Customer ID must be non-empty alphanumeric."""
        if not v.strip():
            raise ValueError("customer_id cannot be empty")
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("customer_id must be alphanumeric, hyphen, or underscore")
        return v.strip()

    @field_validator("success_url")
    @classmethod
    def validate_success_url(cls, v: str) -> str:
        """Success URL must be valid HTTP(S) URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("success_url must start with http:// or https://")
        return v

    @field_validator("cancel_url")
    @classmethod
    def validate_cancel_url(cls, v: str) -> str:
        """Cancel URL must be valid HTTP(S) URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("cancel_url must start with http:// or https://")
        return v




class StripeCreateSubscriptionParams(BaseModel):
    """Parameters for research_stripe_billing create_subscription."""

    customer_id: str = Field(
        ...,
        description="Loom customer ID",
        min_length=1,
        max_length=64,
    )
    tier: Literal["pro", "team", "enterprise"] = Field(
        ...,
        description="Subscription tier (not 'free')",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Customer ID must be non-empty alphanumeric."""
        if not v.strip():
            raise ValueError("customer_id cannot be empty")
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("customer_id must be alphanumeric, hyphen, or underscore")
        return v.strip()




class StripeGetInvoiceParams(BaseModel):
    """Parameters for research_stripe_billing get_invoice."""

    invoice_id: str = Field(
        ...,
        description="Stripe invoice ID",
        min_length=1,
        max_length=64,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("invoice_id")
    @classmethod
    def validate_invoice_id(cls, v: str) -> str:
        """Invoice ID must be non-empty."""
        if not v.strip():
            raise ValueError("invoice_id cannot be empty")
        return v.strip()




class StripeListInvoicesParams(BaseModel):
    """Parameters for research_stripe_billing list_invoices."""

    customer_id: str = Field(
        ...,
        description="Loom customer ID",
        min_length=1,
        max_length=64,
    )
    max_results: int = Field(
        10,
        description="Maximum invoices to return (1-100)",
        ge=1,
        le=100,
        alias="limit",
    )

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Customer ID must be non-empty alphanumeric."""
        if not v.strip():
            raise ValueError("customer_id cannot be empty")
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("customer_id must be alphanumeric, hyphen, or underscore")
        return v.strip()




class SuggestWorkflowParams(BaseModel):
    """Parameters for research_suggest_workflow tool."""

    tools_used: list[str] = Field(..., min_items=1, max_items=50)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("tools_used")
    @classmethod
    def validate_tools_used(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("tools_used cannot be empty")
        if len(v) > 50:
            raise ValueError("tools_used max 50 items")
        # Remove duplicates
        return list(set(t.strip() for t in v if t.strip()))




class WorkflowCreateParams(BaseModel):
    """Parameters for research_workflow_create tool."""

    name: str = Field(..., min_length=1, max_length=255)
    steps: list[dict[str, Any]]

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 255:
            raise ValueError("name 1-255 chars")
        return v

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not v or len(v) > 100:
            raise ValueError("1-100 steps")
        for i, s in enumerate(v):
            if "tool" not in s or "params" not in s:
                raise ValueError(f"step {i}: missing tool/params")
        return v




class WorkflowRunParams(BaseModel):
    """Parameters for research_workflow_run tool."""

    workflow_id: str = Field(..., min_length=1)
    dry_run: bool = False

    model_config = {"extra": "ignore", "strict": True}




class WorkflowStatusParams(BaseModel):
    """Parameters for research_workflow_status tool."""

    workflow_id: str = Field(..., min_length=1)

    model_config = {"extra": "ignore", "strict": True}




