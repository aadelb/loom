"""Pydantic parameter models for academic tools."""

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
    "CitationAnalysisParams",
    "OpenAccessParams",
    "PredatoryJournalCheckParams",
    "RetractionCheckParams",
    "SubdomainTemporalParams",
    "TemporalAnomalyParams",
    "TemporalDiffParams",
]


class CitationAnalysisParams(BaseModel):
    """Parameters for research_citation_analysis tool."""

    paper_id: str
    depth: int = 2

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("paper_id")
    @classmethod
    def validate_paper_id(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 100:
            raise ValueError("paper_id must be 1-100 characters")
        return v

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: int) -> int:
        if v < 1 or v > 3:
            raise ValueError("depth must be 1-3")
        return v



class OpenAccessParams(BaseModel):
    """Parameters for research_open_access tool."""

    doi: str = ""
    title: str = ""

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("doi")
    @classmethod
    def validate_doi(cls, v: str) -> str:
        v = v.strip()
        if v and not re.match(r"^10\.\d+/", v):
            raise ValueError("DOI must start with 10.")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 500:
            raise ValueError("title max 500 characters")
        return v




class PredatoryJournalCheckParams(BaseModel):
    """Parameters for research_predatory_journal_check tool."""

    journal_name: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("journal_name")
    @classmethod
    def validate_journal_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 500:
            raise ValueError("journal_name must be 1-500 characters")
        return v




class RetractionCheckParams(BaseModel):
    """Parameters for research_retraction_check tool."""

    query: str
    max_results: int = 20

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        v = v.strip()
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_results must be 1-100")
        return v




class SubdomainTemporalParams(BaseModel):
    """Parameters for research_subdomain_temporal tool."""

    domain: str
    days_back: int = 90

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v or len(v) > 255:
            raise ValueError("domain must be 1-255 characters")
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("domain contains disallowed characters")
        return v

    @field_validator("days_back")
    @classmethod
    def validate_days_back(cls, v: int) -> int:
        if v < 1 or v > 365:
            raise ValueError("days_back must be 1-365")
        return v




class TemporalAnomalyParams(BaseModel):
    """Parameters for research_temporal_anomaly tool."""

    domain: str
    check_type: Literal["all", "certs", "dns", "clock"] = "all"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("domain", mode="before")
    @classmethod
    def validate_domain_field(cls, v: str) -> str:
        return validate_url(f"https://{v}")

    @field_validator("check_type")
    @classmethod
    def validate_check_type(cls, v: str) -> str:
        if v not in ("all", "certs", "dns", "clock"):
            raise ValueError("check_type must be 'all', 'certs', 'dns', or 'clock'")
        return v




class TemporalDiffParams(BaseModel):
    """Parameters for research_temporal_diff tool."""

    query: str
    days_between: int = 30

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v

    @field_validator("days_between")
    @classmethod
    def validate_days_between(cls, v: int) -> int:
        if v < 1 or v > 365:
            raise ValueError("days_between must be 1-365")
        return v




