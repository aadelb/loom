"""Pydantic parameter models for feature flags tools."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = ["FeatureFlagsParams"]


class FeatureFlagsParams(BaseModel):
    """Parameters for research_feature_flags tool."""

    action: Literal["list", "enable", "disable"] = Field(
        default="list",
        description="Action to perform on feature flags",
    )
    flag: str | None = Field(
        default=None,
        description="Flag name (required for enable/disable actions)",
        min_length=1,
        max_length=100,
    )

    model_config = {"extra": "forbid", "strict": True}
