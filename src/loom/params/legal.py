"""Pydantic parameter models for UAE/Dubai legal compliance tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "UaeCommercialLawParams",
    "UaeCustomsParams",
    "UaeFoodSafetyParams",
    "UaeLaborLawParams",
    "UaeReraParams",
    "UaeTaxComplianceParams",
    "UaeTradeLicenseParams",
    "UaeVisaRulesParams",
]


class UaeLaborLawParams(BaseModel):
    """Parameters for research_uae_labor_law tool."""

    model_config = {"extra": "forbid", "strict": True}

    query: str = Field(
        ..., min_length=1, max_length=500, description="Specific legal question about UAE labor law"
    )
    topic: Literal[
        "general",
        "termination",
        "salary",
        "leave",
        "gratuity",
        "visa_cancellation",
        "part_time",
        "probation",
        "discrimination",
        "work_hours",
    ] = Field("general", description="Topic area (default: general overview)")


class UaeTradeLicenseParams(BaseModel):
    """Parameters for research_uae_trade_license tool."""

    model_config = {"extra": "forbid", "strict": True}

    business_type: Literal["commercial", "professional", "industrial"] = Field(
        ..., description="Type of business license"
    )
    emirate: Literal["dubai", "ajman", "sharjah"] = Field(
        "ajman", description="Emirate for license (default: ajman)"
    )
    free_zone: bool = Field(False, description="Include free zone licensing options")


class UaeFoodSafetyParams(BaseModel):
    """Parameters for research_uae_food_safety tool."""

    model_config = {"extra": "forbid", "strict": True}

    query: str = Field(
        ..., min_length=1, max_length=500, description="Specific food safety compliance question"
    )
    business_type: Literal["supermarket", "restaurant", "food_manufacturing"] = Field(
        "supermarket", description="Type of food business (default: supermarket)"
    )


class UaeVisaRulesParams(BaseModel):
    """Parameters for research_uae_visa_rules tool."""

    model_config = {"extra": "forbid", "strict": True}

    visa_type: Literal[
        "employment", "investor", "golden", "green", "tourist", "family", "domestic_worker"
    ] = Field("employment", description="Type of UAE visa (default: employment)")
    nationality: str = Field(
        "", max_length=100, description="Applicant nationality (optional, for context)"
    )
    query: str = Field("", max_length=500, description="Specific visa-related question (optional)")


class UaeCommercialLawParams(BaseModel):
    """Parameters for research_uae_commercial_law tool."""

    model_config = {"extra": "forbid", "strict": True}

    query: str = Field(
        ..., min_length=1, max_length=500, description="Specific commercial law question"
    )
    topic: Literal[
        "general",
        "company_formation",
        "partnerships",
        "llc",
        "free_zone",
        "foreign_ownership",
        "anti_competition",
        "commercial_agency",
        "bankruptcy",
        "intellectual_property",
    ] = Field("general", description="Commercial law topic (default: general)")


class UaeCustomsParams(BaseModel):
    """Parameters for research_uae_customs tool."""

    model_config = {"extra": "forbid", "strict": True}

    product_category: Literal["food", "electronics", "cosmetics", "textiles", "machinery"] = Field(
        ..., description="Product category for customs rules"
    )
    origin_country: str = Field("", max_length=100, description="Country of origin (optional)")
    query: str = Field("", max_length=500, description="Specific customs question (optional)")


class UaeReraParams(BaseModel):
    """Parameters for research_uae_rera tool."""

    model_config = {"extra": "forbid", "strict": True}

    query: str = Field(
        ..., min_length=1, max_length=500, description="Specific RERA/real estate question"
    )
    transaction_type: Literal["rent", "buy", "off_plan", "commercial_lease"] = Field(
        "rent", description="Type of real estate transaction (default: rent)"
    )


class UaeTaxComplianceParams(BaseModel):
    """Parameters for research_uae_tax_compliance tool."""

    model_config = {"extra": "forbid", "strict": True}

    query: str = Field(
        ..., min_length=1, max_length=500, description="Specific tax compliance question"
    )
    tax_type: Literal["vat", "corporate_tax", "excise_tax", "customs_duty"] = Field(
        "vat", description="Type of tax (default: vat)"
    )
