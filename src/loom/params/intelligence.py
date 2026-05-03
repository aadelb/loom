"""Pydantic parameter models for intelligence tools."""


from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from loom.config import CONFIG
from loom.validators import filter_headers, validate_js_script, validate_local_file_path, validate_url

# Default Accept-Language header sourced from config
_DEFAULT_ACCEPT_LANG = CONFIG.get("DEFAULT_ACCEPT_LANGUAGE", "en-US,en;q=0.9,ar;q=0.8")


__all__ = [
    "CitationGraphParams",
    "CompanyDiligenceParams",
    "CompetitiveIntelParams",
    "CredentialMonitorParams",
    "CryptoRiskParams",
    "CryptoTraceParams",
    "DeceptionDetectParams",
    "DependencyAuditParams",
    "EthereumTxDecodeParams",
    "FindExpertsParams",
    "GraphAnalyzeParams",
    "GraphScraperParams",
    "LeakScanParams",
    "MetadataForensicsParams",
    "MultiPageGraphParams",
    "MultilingualBenchmarkParams",
    "MultilingualParams",
    "PatentLandscapeParams",
    "RedTeamParams",
    "SalaryIntelligenceParams",
    "SocialGraphParams",
    "SocialProfileParams",
    "SocialSearchParams",
    "StegoAnalyzeParams",
    "StegoDetectParams",
    "StegoEncodeParams",
    "StylometryParams",
    "SupplyChainRiskParams",
    "ThreatProfileParams",
    "TransactionGraphParams",
]


class CitationGraphParams(BaseModel):
    """Parameters for research_citation_graph tool."""

    query: str
    depth: int = 2

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: int) -> int:
        if v < 1 or v > 3:
            raise ValueError("depth must be 1-3")
        return v





class CompanyDiligenceParams(BaseModel):
    """Parameters for research_company_diligence tool."""

    company_name: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("company_name must be non-empty")
        v = v.strip()
        if len(v) > 200:
            raise ValueError("company_name max 200 characters")
        return v




class CompetitiveIntelParams(BaseModel):
    """Parameters for research_competitive_intel tool."""

    company_name: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("company_name must be non-empty")
        if len(v) > 200:
            raise ValueError("company_name max 200 characters")
        return v




class CredentialMonitorParams(BaseModel):
    """Parameters for research_credential_monitor tool."""

    query: str = Field(..., alias="target")
    target_type: Literal["email", "username"] = "email"

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or len(v) > 255:
            raise ValueError("query must be 1-255 characters")
        return v




class CryptoRiskParams(BaseModel):
    """Parameters for research_crypto_risk_score tool."""

    address: str
    chain: Literal["bitcoin", "ethereum"] = "bitcoin"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 100:
            raise ValueError("address must be 1-100 characters")
        return v

    @field_validator("chain")
    @classmethod
    def validate_chain(cls, v: str) -> str:
        v = v.lower()
        if v not in ("bitcoin", "ethereum"):
            raise ValueError("chain must be 'bitcoin' or 'ethereum'")
        return v



class CryptoTraceParams(BaseModel):
    """Parameters for research_crypto_trace tool."""

    address: str
    blockchain: Literal["bitcoin", "ethereum", "litecoin"] = "ethereum"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9]{26,66}$", v):
            raise ValueError("address format invalid")
        return v




class DeceptionDetectParams(BaseModel):
    """Parameters for research_deception_detect tool."""

    text: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be non-empty")
        if len(v) > 10000:
            raise ValueError("text max 10000 characters")
        return v




class DependencyAuditParams(BaseModel):
    """Parameters for research_dependency_audit tool."""

    repo_url: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        v = v.strip()
        if "github.com" not in v.lower():
            raise ValueError("repo_url must be a valid GitHub URL")
        return v




class EthereumTxDecodeParams(BaseModel):
    """Parameters for research_ethereum_tx_decode tool."""

    tx_hash: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("tx_hash")
    @classmethod
    def validate_tx_hash(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("0x") or len(v) != 66:
            raise ValueError("tx_hash must be 0x + 64 hex chars")
        try:
            int(v, 16)
        except ValueError:
            raise ValueError("tx_hash must be valid hex")
        return v




class FindExpertsParams(BaseModel):
    """Parameters for research_find_experts tool."""

    topic: str
    max_results: int = 10

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("topic must be non-empty")
        if len(v) > 500:
            raise ValueError("topic max 500 characters")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_results must be 1-100")
        return v




class GraphAnalyzeParams(BaseModel):
    """Parameters for research_graph_analyze tool."""

    nodes: list[dict[str, Any]] = Field(
        ..., description="List of node dicts with required 'id' field"
    )
    edges: list[dict[str, Any]] = Field(
        ..., description="List of edge dicts with 'source' and 'target' fields"
    )
    algorithm: Literal["pagerank", "community_detection", "centrality", "shortest_path"] = Field(
        default="pagerank", description="Graph analysis algorithm to use"
    )

    model_config = {"extra": "ignore", "strict": True}




class GraphScraperParams(BaseModel):
    """Parameters for research_graph_scrape tool."""

    url: str
    query: str
    model: Literal["auto", "groq", "nvidia", "deepseek", "openai", "anthropic"] = "auto"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query cannot be empty")
        if len(v) > 5000:
            raise ValueError("query max 5000 chars")
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        valid = ["auto", "groq", "nvidia", "deepseek", "openai", "anthropic"]
        if v not in valid:
            raise ValueError(f"model must be one of {valid}")
        return v




class LeakScanParams(BaseModel):
    """Parameters for research_leak_scan tool."""

    identifier: str
    scan_type: Literal["email", "username", "phone", "credit_card"] = "email"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("identifier must be non-empty")
        if len(v) > 500:
            raise ValueError("identifier max 500 characters")
        return v




class MetadataForensicsParams(BaseModel):
    """Parameters for research_metadata_forensics tool."""

    url: str
    extract_media: bool = True

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)




class MultiPageGraphParams(BaseModel):
    """Parameters for research_multi_page_graph tool."""

    urls: list[str]
    query: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("urls cannot be empty")
        if len(v) > 100:
            raise ValueError("urls max 100 items")
        validated = []
        for url in v:
            validated.append(validate_url(url))
        return validated

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query cannot be empty")
        if len(v) > 5000:
            raise ValueError("query max 5000 chars")
        return v




class MultilingualBenchmarkParams(BaseModel):
    """Parameters for research_multilingual_benchmark tool."""

    model_api_url: str = Field(
        ...,
        description="URL to model API endpoint (expects POST with {prompt: str})",
    )
    languages: list[str] | None = Field(
        None,
        description="Language groups to test: english, arabic, chinese, french, code_switching. None = all",
    )
    timeout: float = Field(
        5.0,
        description="Timeout per request in seconds (1.0-120.0)",
        ge=1.0,
        le=120.0,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("model_api_url", mode="before")
    @classmethod
    def validate_model_url(cls, v: str) -> str:
        """Validate model API URL."""
        return validate_url(v)

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str] | None) -> list[str] | None:
        """Validate language group selection."""
        if v is None:
            return v
        valid_langs = {"english", "arabic", "chinese", "french", "code_switching"}
        invalid = [lang for lang in v if lang not in valid_langs]
        if invalid:
            raise ValueError(f"Invalid languages: {invalid}. Valid: {valid_langs}")
        if not v:
            raise ValueError("languages list cannot be empty if provided")
        return v




class MultilingualParams(BaseModel):
    """Parameters for research_multilingual tool."""

    query: str
    target_languages: list[str] | None = None
    limit_per_language: int = 5

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v

    @field_validator("limit_per_language")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("limit_per_language must be 1-50")
        return v




class PatentLandscapeParams(BaseModel):
    """Parameters for research_patent_landscape tool."""

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




class RedTeamParams(BaseModel):
    """Parameters for research_red_team tool."""

    system_prompt: str
    attack_vectors: list[str] | None = None
    iterations: int = 3

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("system_prompt must be non-empty")
        if len(v) > 2000:
            raise ValueError("system_prompt max 2000 characters")
        return v

    @field_validator("iterations")
    @classmethod
    def validate_iterations(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("iterations must be 1-10")
        return v




class SalaryIntelligenceParams(BaseModel):
    """Parameters for research_salary_intelligence tool."""

    job_title: str
    location: str | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("job_title")
    @classmethod
    def validate_job_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("job_title must be non-empty")
        if len(v) > 200:
            raise ValueError("job_title max 200 characters")
        return v




class SocialGraphParams(BaseModel):
    """Parameters for research_social_graph tool."""

    username: str
    platforms: list[str] | None = None
    max_depth: int = 2

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("username must be non-empty")
        if len(v) > 200:
            raise ValueError("username max 200 characters")
        return v

    @field_validator("max_depth")
    @classmethod
    def validate_max_depth(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("max_depth must be 1-5")
        return v




class SocialProfileParams(BaseModel):
    """Parameters for research_social_profile tool."""

    username: str
    platform: Literal["twitter", "instagram", "tiktok", "reddit", "linkedin"] | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("username must be non-empty")
        if len(v) > 200:
            raise ValueError("username max 200 characters")
        return v.strip()




class SocialSearchParams(BaseModel):
    """Parameters for research_social_search tool."""

    query: str
    platform: Literal["twitter", "instagram", "tiktok", "reddit", "linkedin"] = "twitter"
    max_results: int = Field(default=20, alias="limit")

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_results must be 1-100")
        return v




class StegoAnalyzeParams(BaseModel):
    """Parameters for research_stego_analyze tool."""

    text: str = Field(..., min_length=1, max_length=5000)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text is non-empty."""
        if not v.strip():
            raise ValueError("text cannot be empty")
        return v



class StegoDetectParams(BaseModel):
    """Parameters for research_stego_detect tool."""

    url: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)




class StegoEncodeParams(BaseModel):
    """Parameters for research_stego_encode tool."""

    message: str = Field(..., min_length=1, max_length=1000)
    method: Literal["lsb", "whitespace", "unicode_zero_width", "metadata_exif"] = Field(default="lsb")
    output_format: str = Field(default="description", max_length=50)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message is non-empty."""
        if not v.strip():
            raise ValueError("message cannot be empty")
        return v




class StylometryParams(BaseModel):
    """Parameters for research_stylometry tool."""

    text: str
    compare_with: str | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be non-empty")
        if len(v) > 50000:
            raise ValueError("text max 50000 characters")
        return v




class SupplyChainRiskParams(BaseModel):
    """Parameters for research_supply_chain_risk tool."""

    package_name: str
    ecosystem: Literal["pypi", "npm", "cargo"] = "pypi"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("package_name")
    @classmethod
    def validate_package_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("package_name must be non-empty")
        v = v.strip()
        if len(v) > 200:
            raise ValueError("package_name max 200 characters")
        return v




class ThreatProfileParams(BaseModel):
    """Parameters for research_threat_profile tool."""

    subject: str
    subject_type: Literal["domain", "ip", "email", "username", "file_hash"] = "domain"
    include_darkweb: bool = False

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("subject must be non-empty")
        if len(v) > 500:
            raise ValueError("subject max 500 characters")
        return v




class TransactionGraphParams(BaseModel):
    """Parameters for research_transaction_graph tool."""

    addresses: list[str] = Field(
        ..., description="List of blockchain addresses (Bitcoin/Ethereum)"
    )
    chain: Literal["bitcoin", "ethereum"] = Field(
        default="bitcoin", description="Blockchain network"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("addresses")
    @classmethod
    def validate_addresses(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("addresses list cannot be empty")
        if len(v) > 100:
            raise ValueError("addresses list limited to 100 items")
        return v




