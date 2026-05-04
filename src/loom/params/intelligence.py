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
    "ArtifactCleanupParams",
    "BrowserPrivacyScoreParams",
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
    "FingerprintAuditParams",
    "GraphAnalyzeParams",
    "GraphScraperParams",
    "LeakScanParams",
    "MetadataForensicsParams",
    "MetadataStripParams",
    "MultiPageGraphParams",
    "MultilingualBenchmarkParams",
    "MultilingualParams",
    "NetworkAnomalyParams",
    "PatentLandscapeParams",
    "PrivacyExposureParams",
    "RedTeamParams",
    "SalaryIntelligenceParams",
    "SocialGraphParams",
    "SocialProfileParams",
    "SocialSearchParams",
    "StegoAnalyzeParams",
    "StegoDecodeParams",
    "StegoDetectParams",
    "StegoEncodeParams",
    "StylometryParams",
    "SupplyChainRiskParams",
    "ThreatProfileParams",
    "TransactionGraphParams",
    "TrendForecastParams",
    "USBMonitorParams",
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


class GraphParams(BaseModel):
    """Unified parameters for research_graph tool with action-based dispatch."""

    action: Literal["extract", "query", "merge", "visualize"] = Field(
        default="extract", description="Graph operation: extract, query, merge, or visualize"
    )
    query: str | None = Field(
        default=None, description="Search query for extraction (action='extract')"
    )
    max_nodes: int = Field(
        default=100, ge=1, le=500, description="Max nodes to return (action='extract')"
    )
    sources: list[str] | None = Field(
        default=None, description="Graph sources: semantic_scholar, wikipedia, wikidata (action='extract')"
    )
    graphs: list[dict[str, Any]] | None = Field(
        default=None, description="Graphs to merge (action='merge')"
    )
    nodes: list[dict[str, Any]] | None = Field(
        default=None, description="Node list for visualization (action='visualize')"
    )
    edges: list[dict[str, Any]] | None = Field(
        default=None, description="Edge list for visualization (action='visualize')"
    )
    search_query: str | None = Field(
        default=None, description="Search query for graph lookup (action='query')"
    )
    max_depth: int = Field(
        default=2, ge=1, le=5, description="Traversal depth for query (action='query')"
    )
    format: Literal["dot", "mermaid"] = Field(
        default="mermaid", description="Visualization format (action='visualize')"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        valid = {"semantic_scholar", "wikipedia", "wikidata"}
        normalized = [s.lower().strip() for s in v if s]
        if not all(s in valid for s in normalized):
            raise ValueError(f"sources must be subset of {valid}")
        return normalized if normalized else None

class TrendForecastParams(BaseModel):
    """Parameters for research_trend_forecast tool."""

    topic: str
    timeframe: str = "6months"
    min_term_frequency: int = 2

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 200:
            raise ValueError("topic must be 1-200 characters")
        if not re.match(r"^[a-zA-Z0-9\s\-_.()&+]+$", v):
            raise ValueError("topic contains invalid characters")
        return v

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, v: str) -> str:
        allowed = {"3months", "6months", "1year"}
        if v not in allowed:
            raise ValueError(f"timeframe must be one of: {', '.join(allowed)}")
        return v

    @field_validator("min_term_frequency")
    @classmethod
    def validate_min_term_frequency(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("min_term_frequency must be 1-10")
        return v


class FingerprintAuditParams(BaseModel):
    """Parameters for research_fingerprint_audit tool."""

    url: str = "https://browserleaks.com/javascript"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)



class HarvestParams(BaseModel):
    """Parameters for research_harvest tool."""

    domain: str
    sources: str = "all"
    limit: int = 100

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or len(v) > 255:
            raise ValueError("domain must be 1-255 characters")
        if not re.match(r"^[a-z0-9.-]+$", v):
            raise ValueError("domain contains disallowed characters")
        return v

    @field_validator("sources")
    @classmethod
    def validate_sources(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or len(v) > 255:
            raise ValueError("sources must be 1-255 characters")
        if not re.match(r"^[a-z0-9,\-]+$", v):
            raise ValueError("sources contains disallowed characters")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if not isinstance(v, int):
            raise ValueError("limit must be an integer")
        if v < 1 or v > 10000:
            raise ValueError("limit must be 1-10000")
        return v

class PrivacyExposureParams(BaseModel):
    """Parameters for research_privacy_exposure tool."""

    target_url: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("target_url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class ArtifactCleanupParams(BaseModel):
    """Parameters for research_artifact_cleanup tool."""

    target_paths: list[str]
    dry_run: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("target_paths")
    @classmethod
    def validate_paths(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("target_paths list cannot be empty")
        if len(v) > 20:
            raise ValueError("target_paths max 20 items")
        return v

    @field_validator("dry_run")
    @classmethod
    def validate_dry_run(cls, v: bool) -> bool:
        if not isinstance(v, bool):
            raise ValueError("dry_run must be boolean")
        return v


class StegoEncodeParams(BaseModel):
    """Parameters for research_stego_encode tool."""

    input_text: str
    cover_message: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("input_text")
    @classmethod
    def validate_input_text(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("input_text must be non-empty string")
        if len(v) > 256:
            raise ValueError("input_text max 256 characters")
        return v

    @field_validator("cover_message")
    @classmethod
    def validate_cover_message(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("cover_message must be non-empty string")
        if len(v) > 5000:
            raise ValueError("cover_message max 5000 characters")
        return v


class StegoDecodeParams(BaseModel):
    """Parameters for research_stego_decode tool."""

    encoded_message: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("encoded_message")
    @classmethod
    def validate_encoded_message(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("encoded_message must be non-empty string")
        return v


class BrowserPrivacyScoreParams(BaseModel):
    """Parameters for research_browser_privacy_score tool."""

    browser: Literal["chromium", "firefox", "safari", "edge"] = "chromium"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("browser")
    @classmethod
    def validate_browser(cls, v: str) -> str:
        valid = {"chromium", "firefox", "safari", "edge"}
        if v not in valid:
            raise ValueError(f"browser must be one of {valid}")
        return v


class USBMonitorParams(BaseModel):
    """Parameters for research_usb_monitor tool."""

    dry_run: bool = True

    model_config = {"extra": "ignore", "strict": True}


class NetworkAnomalyParams(BaseModel):
    """Parameters for research_network_anomaly tool."""

    interface: str = "eth0"
    duration_sec: int = Field(default=5, ge=1, le=60)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("interface")
    @classmethod
    def validate_interface(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("interface must be non-empty")
        if len(v) > 50:
            raise ValueError("interface max 50 characters")
        return v


class MetadataStripParams(BaseModel):
    """Parameters for research_metadata_strip tool."""

    file_path: str
    strip_type: Literal["all", "exif", "xmp", "iptc"] = "all"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("file_path must be non-empty")
        if len(v) > 1000:
            raise ValueError("file_path max 1000 characters")
        return v


class MispLookupParams(BaseModel):
    """Parameters for research_misp_lookup tool."""

    indicator: str
    indicator_type: str | Literal["auto", "ip", "domain", "hash", "email"] = "auto"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("indicator")
    @classmethod
    def validate_indicator(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("indicator must be non-empty")
        if len(v) > 500:
            raise ValueError("indicator max 500 characters")
        return v

    @field_validator("indicator_type")
    @classmethod
    def validate_indicator_type(cls, v: str) -> str:
        valid = {"auto", "ip", "domain", "hash", "email", "unknown"}
        if v not in valid:
            raise ValueError(f"indicator_type must be one of {valid}")
        return v


class SocialAnalyzerParams(BaseModel):
    """Parameters for research_social_analyze tool."""

    username: str
    platforms: list[str] | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("username must be non-empty")
        if len(v) > 100:
            raise ValueError("username max 100 characters")
        return v

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v: list[str] | None) -> list[str] | None:
        if v:
            if len(v) > 50:
                raise ValueError("platforms list max 50 items")
            return [p.strip().lower() for p in v if p.strip()]
        return v
