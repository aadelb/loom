"""Pydantic parameter models for operational and monitoring tools."""

from __future__ import annotations


from pydantic import BaseModel, Field, field_validator

__all__ = [
    "AuditQueryParams",
    "AuditStatsParams",
    "DataExportCacheParams",
    "DataExportConfigParams",
    "DataExportStrategiesParams",
    "DLQClearFailedParams",
    "DLQListParams",
    "DLQRetryNowParams",
    "DLQStatsParams",
    "HealthDeepParams",
    "LatencyReportParams",
    "LoaderStatsParams",
    "QuotaStatusParams",
    "SecurityAuditParams",
]


class SecurityAuditParams(BaseModel):
    """Parameters for research_security_audit tool.

    No parameters required; runs 15 security checks and returns pass/fail report.
    """

    model_config = {"extra": "ignore", "strict": True}


class DataExportConfigParams(BaseModel):
    """Parameters for research_export_config tool.

    No parameters required; exports current server configuration as JSON.
    """

    model_config = {"extra": "ignore", "strict": True}


class DataExportStrategiesParams(BaseModel):
    """Parameters for research_export_strategies tool."""

    format: str = Field(default="json", description="Export format: json, yaml, csv")

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in ("json", "yaml", "csv"):
            raise ValueError("format must be one of: json, yaml, csv")
        return v.lower()


class DataExportCacheParams(BaseModel):
    """Parameters for research_export_cache tool."""

    limit: int = Field(default=50, ge=1, le=1000, description="Max cache entries to export")

    model_config = {"extra": "ignore", "strict": True}


class HealthDeepParams(BaseModel):
    """Parameters for research_health_deep tool.

    No parameters required; performs deep diagnostics on all Loom subsystems.
    """

    model_config = {"extra": "ignore", "strict": True}


class LatencyReportParams(BaseModel):
    """Parameters for research_latency_report tool."""

    tool_name: str = Field(default="", description="Specific tool name (e.g., 'research_fetch'). Empty returns all tools.")

    model_config = {"extra": "ignore", "strict": True}


class DLQStatsParams(BaseModel):
    """Parameters for research_dlq_stats tool.

    No parameters required; returns deadletter queue statistics.
    """

    model_config = {"extra": "ignore", "strict": True}


class DLQRetryNowParams(BaseModel):
    """Parameters for research_dlq_retry_now tool."""

    dlq_id: int = Field(ge=1, description="ID of the DLQ item to retry")

    model_config = {"extra": "ignore", "strict": True}


class DLQListParams(BaseModel):
    """Parameters for research_dlq_list tool."""

    tool_name: str | None = Field(default=None, description="Optional filter by tool name")
    include_failed: bool = Field(default=False, description="If True, include permanently failed items")

    model_config = {"extra": "ignore", "strict": True}


class DLQClearFailedParams(BaseModel):
    """Parameters for research_dlq_clear_failed tool."""

    days: int = Field(default=30, ge=1, le=3650, description="Remove failed items older than this many days")

    model_config = {"extra": "ignore", "strict": True}


class AuditQueryParams(BaseModel):
    """Parameters for research_audit_query tool."""

    tool_name: str = Field(default="", description="Filter by tool name (empty = all tools)")
    hours: int = Field(default=24, ge=1, le=720, description="Look back N hours (1-720, default 24)")
    limit: int = Field(default=100, ge=1, le=1000, description="Maximum entries to return (1-1000, default 100)")

    model_config = {"extra": "ignore", "strict": True}


class AuditStatsParams(BaseModel):
    """Parameters for research_audit_stats tool."""

    hours: int = Field(default=24, ge=1, le=720, description="Look back N hours (1-720, default 24)")

    model_config = {"extra": "ignore", "strict": True}


class LoaderStatsParams(BaseModel):
    """Parameters for research_loader_stats tool.

    No parameters required; returns lazy tool loader statistics.
    """

    model_config = {"extra": "ignore", "strict": True}


class QuotaStatusParams(BaseModel):
    """Parameters for research_quota_status tool."""

    provider: str | None = Field(
        default=None,
        description="Optional provider name (groq, nvidia_nim, gemini). If None, returns all providers.",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str | None) -> str | None:
        if v is not None:
            valid_providers = ("groq", "nvidia_nim", "gemini", "deepseek", "moonshot", "openai", "anthropic")
            if v.lower() not in valid_providers:
                raise ValueError(f"provider must be one of: {', '.join(valid_providers)}")
            return v.lower()
        return v
