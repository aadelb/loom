"""Brain type definitions — Pydantic models and enumerations."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QualityMode(str, Enum):
    MAX = "max"
    AUTO = "auto"
    ECONOMY = "economy"


class ToolMeta(BaseModel):
    """Metadata for a single registered tool."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=dict)
    categories: list[str] = Field(default_factory=list)
    is_async: bool = True
    quality_tier: str = "free"

    class Config:
        extra = "ignore"


class ToolMatch(BaseModel):
    """A tool matched by the reasoning layer with confidence score."""

    tool_name: str
    confidence: float = 0.0
    match_source: str = "keyword"
    inferred_params: dict[str, Any] = Field(default_factory=dict)


class PlanStep(BaseModel):
    """A single step in a multi-tool execution plan."""

    tool_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    timeout: float = 30.0


class ExecutionPlan(BaseModel):
    """Ordered execution plan produced by the reasoning layer."""

    steps: list[PlanStep] = Field(default_factory=list)
    quality_mode: QualityMode = QualityMode.AUTO
    estimated_cost: float = 0.0


class SmartCallResult(BaseModel):
    """Result returned by research_smart_call."""

    success: bool = False
    matched_tools: list[str] = Field(default_factory=list)
    plan_steps: list[str] = Field(default_factory=list)
    final_output: Any = None
    iterations: int = 0
    quality_mode: QualityMode = QualityMode.AUTO
    error: str | None = None
    elapsed_ms: int = 0
