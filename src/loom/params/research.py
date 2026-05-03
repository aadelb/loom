"""Pydantic parameter models for research and analysis tools."""


from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from loom.config import CONFIG
from loom.validators import filter_headers, validate_js_script, validate_local_file_path, validate_url

# Default Accept-Language header sourced from config
_DEFAULT_ACCEPT_LANG = CONFIG.get("DEFAULT_ACCEPT_LANGUAGE", "en-US,en;q=0.9,ar;q=0.8")


__all__ = [
    "AdaptComplexityParams",
    "AdaptiveReframeParams",
    "AgentBenchmarkParams",
    "AggregateResultsParams",
    "AggregateTextsParams",
    "AmassEnumParams",
    "AmassIntelParams",
    "ArticleBatchParams",
    "ArxivScanParams",
    "ArxivScanParams",
    "AuthorityStackParams",
    "AutoReframeParams",
    "BPJParams",
    "BenchmarkModelsParams",
    "BenchmarkParams",
    "ChainDefineParams",
    "ChainDescribeParams",
    "CheckpointListParams",
    "CheckpointResumeParams",
    "CheckpointSaveParams",
    "CicdRunParams",
    "CircuitBypassPlanParams",
    "ConsensusParams",
    "ConsistencyPressureHistoryParams",
    "ConsistencyPressureParams",
    "ConsistencyPressureRecordParams",
    "ContextPoisonParams",
    "CoverageRunParams",
    "CrawlParams",
    "CreepjsParams",
    "CrescendoChainParams",
    "CrossModelTransferParams",
    "DaisyChainParams",
    "DarkForumParams",
    "DarkWebBridgeParams",
    "DashboardParams",
    "DataPoisoningParams",
    "DetectParadoxParams",
    "DocumentAnalyzeParams",
    "DriftMonitorParams",
    "ExaFindSimilarParams",
    "ExecutabilityParams",
    "ExperimentDesignParams",
    "ExploitRegisterParams",
    "ExportCsvParams",
    "ExportJsonParams",
    "ExportListParams",
    "FOIATrackerParams",
    "FingerprintBehaviorParams",
    "FingerprintEvasionParams",
    "FingerprintModelParams",
    "FormatSmuggleParams",
    "FullSpectrumParams",
    "FunctorMapParams",
    "GeodesicPathParams",
    "GhostProtocolParams",
    "GithubReadmeParams",
    "GithubReleasesParams",
    "HCSReportParams",
    "HCSRubricParams",
    "HierarchicalResearchParams",
    "HttpxProbeParams",
    "ImageAnalyzeParams",
    "InfluenceOperationParams",
    "InfoHalfLifeParams",
    "InformationCascadeParams",
    "InfraCorrelatorParams",
    "InstagramParams",
    "KatanaCrawlParams",
    "LeaderboardUpdateParams",
    "LeaderboardViewParams",
    "LegalTakedownParams",
    "LightpandaBatchParams",
    "MemeticSimulateParams",
    "MemoryRecallParams",
    "MemoryStoreParams",
    "MetaLearnerParams",
    "MisinfoCheckParams",
    "ModelComparatorParams",
    "NucleiScanParams",
    "OCRAdvancedParams",
    "OnionDiscoverParams",
    "OrchestrateSmartParams",
    "PDFAdvancedParams",
    "ParadoxImmunizeParams",
    "ParallelExecutorParams",
    "ParallelPlanExecutorParams",
    "PersistentMemoryRecallParams",
    "PersistentMemoryRememberParams",
    "PersonalizeOutputParams",
    "PromptReframeParams",
    "PydanticAgentParams",
    "QueryBuilderParams",
    "RAGAttackParams",
    "RecommendNextParams",
    "RunExperimentParams",
    "SafetyCircuitMapParams",
    "SaveNoteParams",
    "ScraperEngineBatchParams",
    "SecTrackerParams",
    "SherlockBatchParams",
    "SherlockLookupParams",
    "SimplifyParams",
    "SitemapCrawlParams",
    "SourceCredibilityParams",
    "StackReframeParams",
    "StrangeAttractorParams",
    "SubcultureIntelParams",
    "SubfinderParams",
    "SynthesizeReportParams",
    "TaskCriticalPathParams",
    "TaskResolveOrderParams",
    "TextToSpeechParams",
    "ToolRecommendParams",
    "TorbotParams",
    "ToxicityCheckParams",
    "UnifiedScoreParams",
    "VisionBrowseParams",
    "VisionCompareParams",
    "WebTimeMachineParams",
    "WhiteRabbitParams",
    "WikiEventCorrelatorParams",
    "ZenBatchParams",
    "ZenInteractParams",
]


class AdaptComplexityParams(BaseModel):
    """Parameters for research_adapt_complexity tool."""

    content: str = Field(
        description="Text to adapt for reading level"
    )
    target_reading_level: int = Field(
        default=12,
        ge=1,
        le=20,
        description="Target reading level (1-20, where 12 = college)"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is non-empty string."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("content must be a non-empty string")
        if len(v) > 50000:
            raise ValueError("content max 50000 characters")
        return v.strip()



class AdaptiveReframeParams(BaseModel):
    model_config = {"extra": "ignore", "strict": True}
    prompt: str
    refusal_text: str = ""
    model: str = "auto"




class AgentBenchmarkParams(BaseModel):
    """Parameters for research_agent_benchmark tool."""

    model_api_url: str = Field(
        ...,
        description="URL to model API endpoint or local model function identifier",
    )
    timeout: float = Field(
        30.0,
        description="Timeout per scenario in seconds (5.0-300.0)",
        ge=5.0,
        le=300.0,
    )
    model_name: str = Field(
        default="",
        description="Optional model name for reporting and identification",
    )
    output_format: Literal["json", "summary"] = Field(
        default="summary",
        description="Output format: json for detailed results or summary for metrics only",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("model_api_url", mode="before")
    @classmethod
    def validate_model_url(cls, v: str) -> str:
        """Validate model API URL or identifier."""
        if not v or not v.strip():
            raise ValueError("model_api_url must be non-empty")
        if len(v) > 512:
            raise ValueError("model_api_url must be max 512 characters")
        return v.strip()

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name for reporting."""
        if len(v) > 256:
            raise ValueError("model_name must be max 256 characters")
        return v.strip()



class AggregateResultsParams(BaseModel):
    """Parameters for research_aggregate_results tool."""

    results: list[dict[str, Any]] = Field(..., min_length=1, max_length=100)
    strategy: Literal["merge", "concatenate", "summarize", "deduplicate", "rank"] = "merge"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("results")
    @classmethod
    def validate_results(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not v:
            raise ValueError("results list cannot be empty")
        return v

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        valid = {"merge", "concatenate", "summarize", "deduplicate", "rank"}
        if v not in valid:
            raise ValueError(f"strategy must be one of {valid}")
        return v




class AggregateTextsParams(BaseModel):
    """Parameters for research_aggregate_texts tool."""

    texts: list[str] = Field(..., min_length=1, max_length=50)
    method: Literal["concatenate", "deduplicate", "summarize", "bullet_points"] = "concatenate"
    max_length: int = Field(5000, ge=100, le=50000)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("texts list cannot be empty")
        return [str(t) for t in v]

    @field_validator("method")
    @classmethod
    def validate_method(cls, v: str) -> str:
        valid = {"concatenate", "deduplicate", "summarize", "bullet_points"}
        if v not in valid:
            raise ValueError(f"method must be one of {valid}")
        return v




class AmassEnumParams(BaseModel):
    """Parameters for research_amass_enum tool."""

    domain: str
    passive: bool = True
    timeout: int = 120

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v or len(v) > 255:
            raise ValueError("domain must be 1-255 characters")
        if not re.match(r"^[a-z0-9._-]+$", v, re.IGNORECASE):
            raise ValueError("domain contains disallowed characters")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 600:
            raise ValueError("timeout must be 1-600 seconds")
        return v




class AmassIntelParams(BaseModel):
    """Parameters for research_amass_intel tool."""

    domain: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v or len(v) > 255:
            raise ValueError("domain must be 1-255 characters")
        if not re.match(r"^[a-z0-9._-]+$", v, re.IGNORECASE):
            raise ValueError("domain contains disallowed characters")
        return v




class ArticleBatchParams(BaseModel):
    """Parameters for research_article_batch tool."""

    urls: list[str]
    max_concurrent: int = 5

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("urls list cannot be empty")
        if len(v) > 200:
            raise ValueError("urls list max 200 items")
        return [validate_url(url) for url in v]

    @field_validator("max_concurrent")
    @classmethod
    def validate_max_concurrent(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("max_concurrent must be 1-20")
        return v




class ArxivScanParams(BaseModel):
    """Parameters for research_arxiv_scan tool."""

    keywords: list[str] | None = Field(
        default=None,
        description="Search keywords (default: jailbreak, prompt injection, adversarial, red team, LLM safety)"
    )
    days_back: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Number of days to search back"
    )
    max_papers: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum papers to return per keyword"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: list[str] | None) -> list[str] | None:
        """Validate keywords list."""
        if v is not None:
            if not isinstance(v, list) or len(v) == 0:
                raise ValueError("keywords must be non-empty list")
            if len(v) > 20:
                raise ValueError("keywords max 20 items")
            for kw in v:
                if not isinstance(kw, str) or len(kw) > 100:
                    raise ValueError("each keyword must be string, max 100 chars")
        return v



class ArxivScanParams(BaseModel):
    """Parameters for research_arxiv_scan tool."""

    keywords: list[str] | None = Field(
        default=None,
        description="Search keywords (default: jailbreak, prompt injection, adversarial, red team, LLM safety)"
    )
    days_back: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Number of days to search back"
    )
    max_papers: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum papers to return per keyword"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: list[str] | None) -> list[str] | None:
        """Validate keywords list."""
        if v is not None:
            if not isinstance(v, list) or len(v) == 0:
                raise ValueError("keywords must be non-empty list")
            if len(v) > 20:
                raise ValueError("keywords max 20 items")
            for kw in v:
                if not isinstance(kw, str) or len(kw) > 100:
                    raise ValueError("each keyword must be string, max 100 chars")
        return v



class AuthorityStackParams(BaseModel):
    """Parameters for research_authority_stack tool."""

    prompt: str
    authority_layers: int = 5

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 5000:
            raise ValueError("prompt must be 1-5000 characters")
        return v

    @field_validator("authority_layers")
    @classmethod
    def validate_authority_layers(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("authority_layers must be 1-5")
        return v




class AutoReframeParams(BaseModel):
    """Parameters for auto_reframe tool."""
    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}
    prompt: str
    url: str = Field(default="", alias="target_url")
    model: str = "auto"
    max_attempts: int = Field(default=5, ge=1, le=20)




class BPJParams(BaseModel):
    """Parameters for research_bpj_generate tool."""

    safe_prompt: str = Field(
        description="Prompt that model complies with",
        max_length=10000,
        min_length=1,
    )
    unsafe_prompt: str = Field(
        description="Prompt that model refuses",
        max_length=10000,
        min_length=1,
    )
    max_steps: int = Field(
        default=10,
        description="Maximum binary search steps (3-20)",
        ge=3,
        le=20,
    )
    model_name: str = Field(
        default="test-model",
        description="Name of model being tested",
        max_length=256,
    )
    mode: str = Field(
        default="find_boundary",
        description="find_boundary, map_region, or both",
    )
    perturbations: int = Field(
        default=20,
        description="Number of perturbations for region mapping (5-100)",
        ge=5,
        le=100,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("find_boundary", "map_region", "both"):
            raise ValueError("mode must be find_boundary, map_region, or both")
        return v




class BenchmarkModelsParams(BaseModel):
    """Parameters for research_benchmark_models tool."""

    models: list[str] | None = Field(
        None,
        description="List of model names to benchmark (e.g., ['gpt-4', 'claude-opus']). If None, benchmarks all available.",
        max_length=20,
    )
    categories: list[str] | None = Field(
        None,
        description="Benchmark categories: injection_resistance, refusal_rate, response_quality, all. If None, runs all.",
        max_length=5,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("models")
    @classmethod
    def validate_models(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not v:
            raise ValueError("models list cannot be empty")
        if len(v) > 20:
            raise ValueError("models list max 20 items")
        return [m.strip() for m in v if m.strip()]

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        valid = {
            "injection_resistance",
            "refusal_rate",
            "response_quality",
            "all",
        }
        invalid = [c for c in v if c not in valid]
        if invalid:
            raise ValueError(f"Invalid categories: {invalid}. Must be one of {valid}")
        return v




class BenchmarkParams(BaseModel):
    """Parameters for research_benchmark_run tool."""

    dataset: Literal["jailbreakbench", "harmbench", "combined"] = "jailbreakbench"
    strategies: str | None = Field(
        default=None,
        description="Comma-separated list of strategy names to evaluate",
    )
    model_name: str = Field(
        default="test-model",
        description="Name of the model being evaluated",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("dataset")
    @classmethod
    def validate_dataset(cls, v: str) -> str:
        valid_datasets = {"jailbreakbench", "harmbench", "combined"}
        if v not in valid_datasets:
            raise ValueError(f"dataset must be one of {valid_datasets}")
        return v

    @field_validator("strategies")
    @classmethod
    def validate_strategies(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.strip():
            raise ValueError("strategies must be non-empty if provided")
        # Split and validate each strategy name
        strategies = [s.strip() for s in v.split(",")]
        if not strategies:
            raise ValueError("strategies must contain at least one strategy name")
        for strategy in strategies:
            if not strategy or len(strategy) > 100:
                raise ValueError("Each strategy name must be 1-100 characters")
        return v

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("model_name must be non-empty")
        if len(v) > 256:
            raise ValueError("model_name must be max 256 characters")
        return v.strip()




class ChainDefineParams(BaseModel):
    """Parameters for research_chain_define tool."""

    name: str = Field(..., min_length=1, max_length=64)
    steps: list[dict[str, Any]] = Field(..., min_items=1, max_items=100)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("name must be alphanumeric with dashes/underscores")
        return v




class ChainDescribeParams(BaseModel):
    """Parameters for research_chain_describe tool."""

    name: str = Field(..., min_length=1, max_length=64)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("name must be alphanumeric with dashes/underscores")
        return v




class CheckpointListParams(BaseModel):
    """Parameters for research_checkpoint_list tool."""

    status: str = Field("all", description='Filter: "all", "incomplete" (<100%), or "stale" (>24h old)')

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status filter."""
        if v not in ("all", "incomplete", "stale"):
            raise ValueError('status must be "all", "incomplete", or "stale"')
        return v




class CheckpointResumeParams(BaseModel):
    """Parameters for research_checkpoint_resume tool."""

    task_id: str = Field(..., description="Task identifier to resume")

    model_config = {"extra": "ignore", "strict": True}




class CheckpointSaveParams(BaseModel):
    """Parameters for research_checkpoint_save tool."""

    task_id: str = Field(..., description="Unique task identifier (alphanumeric + underscore/dash)")
    state: dict[str, Any] = Field(..., description="JSON-serializable state dict")
    progress_pct: float = Field(0.0, ge=0.0, le=100.0, description="Progress percentage (0-100)")

    model_config = {"extra": "ignore", "strict": True}




class CicdRunParams(BaseModel):
    """Parameters for research_cicd_run tool."""

    command: str = Field(
        description="Command to run",
        max_length=10000,
    )
    timeout: int | None = Field(
        default=None,
        description="Command timeout in seconds",
        ge=1,
        le=3600,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("command cannot be empty")
        return v.strip()




class CircuitBypassPlanParams(BaseModel):
    """Parameters for research_circuit_bypass_plan tool."""

    model: str
    target_circuit: str = "auto"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if not v or len(v) > 100:
            raise ValueError("model identifier required, max 100 chars")
        return v

    @field_validator("target_circuit")
    @classmethod
    def validate_target_circuit(cls, v: str) -> str:
        valid_circuits = [
            "auto",
            "input_classifier",
            "intent_classifier",
            "output_filter",
            "refusal_generator",
            "continuous_monitor",
        ]
        if v not in valid_circuits:
            raise ValueError(f"target_circuit must be one of {valid_circuits}")
        return v




class ConsensusParams(BaseModel):
    """Parameters for research_consensus tool."""

    query: str
    max_results: int = Field(default=5, alias="num_sources")

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
        if v < 2 or v > 20:
            raise ValueError("max_results must be 2-20")
        return v




class ConsistencyPressureHistoryParams(BaseModel):
    """Parameters for research_consistency_pressure_history tool."""

    model: str = Field(
        description="Model identifier",
        max_length=256,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("model cannot be empty")
        return v.strip()




class ConsistencyPressureParams(BaseModel):
    """Parameters for research_consistency_pressure tool."""

    model: str = Field(
        description="Model identifier (e.g., gpt-4, claude-opus)",
        max_length=256,
    )
    target_prompt: str = Field(
        description="Prompt to inject pressure into (max 10000 chars)",
        max_length=10000,
    )
    max_references: int = Field(
        default=5,
        description="Max number of past responses to cite (1-20)",
        ge=1,
        le=20,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("model cannot be empty")
        return v.strip()

    @field_validator("target_prompt")
    @classmethod
    def validate_target_prompt(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("target_prompt cannot be empty")
        return v.strip()




class ConsistencyPressureRecordParams(BaseModel):
    """Parameters for research_consistency_pressure_record tool."""

    model: str = Field(
        description="Model identifier",
        max_length=256,
    )
    prompt: str = Field(
        description="Prompt that was sent (max 10000 chars)",
        max_length=10000,
    )
    response: str = Field(
        description="Model's response (max 50000 chars)",
        max_length=50000,
    )
    complied: bool = Field(
        description="Whether model complied with request",
    )

    model_config = {"extra": "ignore", "strict": True}




class ContextPoisonParams(BaseModel):
    """Parameters for research_context_poison tool."""

    query: str = Field(
        ...,
        description="Query to poison",
        max_length=10000,
        alias="target_query",
    )
    endpoint_url: str | None = Field(
        default=None,
        description="Optional endpoint URL for testing",
        max_length=2048,
    )
    num_examples: int = Field(
        default=20,
        description="Number of poison examples (5-100)",
        ge=5,
        le=100,
    )
    domain: str | None = Field(
        default=None,
        description="Optional domain context",
        max_length=256,
    )
    model_name: str = Field(
        default="test-model",
        description="Model identifier",
        max_length=256,
    )
    use_direct_model_fn: bool = Field(
        default=False,
        description="Use direct model function",
    )

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}




class CoverageRunParams(BaseModel):
    """Parameters for research_coverage_run tool.
    
    Runs comprehensive test coverage across all 227+ MCP tools.
    """

    tools_to_test: list[str] | None = Field(
        default=None,
        description="Specific tools to test. If None, tests all.",
    )
    timeout: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Timeout per tool in seconds",
    )
    dry_run: bool = Field(
        default=True,
        description="If True, skip network-required tools and add dry_run=True to params",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("tools_to_test")
    @classmethod
    def validate_tools_to_test(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and len(v) > 227:
            raise ValueError("tools_to_test cannot exceed 227 tools")
        return v

# Missing params for test files



class CrawlParams(BaseModel):
    """Parameters for research_crawl tool."""

    url: str
    max_pages: int = Field(
        default=10,
        description="Maximum pages to crawl (1-100)",
        ge=1,
        le=100,
    )
    pattern: str | None = Field(
        default=None,
        description="Optional regex pattern to filter links",
        max_length=256,
    )
    extract_links: bool = Field(
        default=True,
        description="Whether to extract and follow links",
    )
    use_js: bool = Field(
        default=False,
        description="Use Playwright (JS-enabled) instead of BeautifulSoup",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                import re

                re.compile(v)  # Validate regex
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v




class CreepjsParams(BaseModel):
    """Parameters for research_creepjs_audit tool."""

    url: str = Field(default="https://creepjs.web.app", alias="target_url")
    headless: bool = True

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return validate_url(v)




class CrescendoChainParams(BaseModel):
    model_config = {"extra": "ignore", "strict": True}
    prompt: str
    turns: int = Field(default=5, ge=3, le=7)
    model: str = "auto"




class CrossModelTransferParams(BaseModel):
    """Parameters for research_cross_model_transfer tool."""

    query: str = Field(
        description="Query to test for transfer",
        max_length=10000,
    )
    source_model: str = Field(
        description="Source model",
        max_length=256,
    )
    target_model: str = Field(
        description="Target model",
        max_length=256,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()




class DaisyChainParams(BaseModel):
    """Parameters for research_daisy_chain tool."""

    query: str = Field(
        description="Query to decompose and execute (max 5000 chars)",
        max_length=5000,
    )
    available_models: list[str] | None = Field(
        default=None,
        description="Models to distribute sub-queries across",
    )
    combiner_model: str = Field(
        default="gpt-4",
        description="Model to synthesize sub-responses",
        max_length=256,
    )
    timeout_per_model: float = Field(
        default=30.0,
        description="Timeout per model call in seconds (5.0-120.0)",
        ge=5.0,
        le=120.0,
    )
    max_sub_queries: int = Field(
        default=4,
        description="Maximum sub-queries to generate (2-6)",
        ge=2,
        le=6,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()




class DarkForumParams(BaseModel):
    """Parameters for research_dark_forum tool."""

    query: str
    forums: list[str] | None = None
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




class DarkWebBridgeParams(BaseModel):
    """Parameters for research_dark_web_bridge tool."""

    query: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or len(v) > 200:
            raise ValueError("query must be 1-200 characters")
        return v




class DashboardParams(BaseModel):
    """Parameters for research_dashboard tool."""

    action: Literal["add_event", "get_events", "summary", "html"] = Field(
        ...,
        description="Dashboard action: add_event, get_events, summary, or html",
    )
    event_type: str | None = Field(
        None,
        description="Event type (strategy_applied, model_response, score_update, attack_success, attack_failure)",
        max_length=100,
    )
    event_data: dict[str, Any] | None = Field(
        None,
        description="Event data dictionary",
    )
    since: int = Field(
        0,
        description="Get events since index N (default: 0 for all events)",
        ge=0,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("action", mode="before")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Action must be one of the valid options."""
        valid_actions = {"add_event", "get_events", "summary", "html"}
        if v not in valid_actions:
            raise ValueError(f"action must be one of {valid_actions}")
        return v

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str | None) -> str | None:
        """Event type must be non-empty if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("event_type cannot be empty")
            valid_types = {
                "strategy_applied",
                "model_response",
                "score_update",
                "attack_success",
                "attack_failure",
            }
            if v not in valid_types:
                raise ValueError(f"event_type must be one of {valid_types}")
        return v



class DataPoisoningParams(BaseModel):
    """Parameters for research_data_poisoning tool."""

    url: str = Field(..., alias="target_url")
    canary_phrases: list[str] | None = None

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("canary_phrases")
    @classmethod
    def validate_canaries(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            if len(v) > 50:
                raise ValueError("canary_phrases max 50 items")
            for phrase in v:
                if not phrase or len(phrase) > 500:
                    raise ValueError("each phrase must be 1-500 characters")
        return v




class DetectParadoxParams(BaseModel):
    """Parameters for research_detect_paradox tool."""

    prompt: str = Field(..., min_length=1, max_length=10000)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("prompt cannot be empty or whitespace only")
        return v




class DocumentAnalyzeParams(BaseModel):
    """Parameters for research_document_analyze tool."""

    file_path_or_url: str
    analysis: Literal["full", "text", "fast"] = "full"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("file_path_or_url", mode="before")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("file_path_or_url cannot be empty")
        # Validate if it's a URL
        if v.startswith(("http://", "https://")):
            return validate_url(v)
        # Otherwise, it's a local path - just validate it's a reasonable length
        if len(v) > 500:
            raise ValueError("file_path_or_url too long")
        return v




class DriftMonitorParams(BaseModel):
    """Parameters for research_drift_monitor tool."""

    prompts: list[str] = Field(..., min_length=1, max_length=50)
    model_name: str = Field(..., min_length=1, max_length=100)
    mode: str = Field(default="check", pattern=r"^(check|baseline|compare)$")
    storage_path: str = Field(default="~/.loom/drift/", max_length=500)

    model_config = {"extra": "ignore", "strict": True}



class ExaFindSimilarParams(BaseModel):
    """Parameters for find_similar_exa tool."""

    query: str
    max_results: int = Field(default=10, alias="num_results")

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
    def validate_num_results(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_results must be 1-100")
        return v




class ExecutabilityParams(BaseModel):
    """Parameters for research_executability_score tool."""

    response_text: str = Field(
        description="Response text to score",
        max_length=100000,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("response_text")
    @classmethod
    def validate_response_text(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("response_text must be string")
        if not v.strip():
            raise ValueError("response_text cannot be empty")
        return v




class ExperimentDesignParams(BaseModel):
    """Parameters for research_experiment_design tool."""

    research_question: str = Field(
        description="Research question to design experiment for"
    )
    budget: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Max trials per condition (10-200)"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("research_question", mode="before")
    @classmethod
    def validate_question(cls, v: str) -> str:
        """Validate research question is non-empty string."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("research_question must be a non-empty string")
        if len(v) > 512:
            raise ValueError("research_question max 512 characters")
        return v.strip()




class ExploitRegisterParams(BaseModel):
    """Parameters for research_exploit_register tool."""

    model: str = Field(..., min_length=1, max_length=100)
    strategy: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    severity: Literal["critical", "high", "medium", "low"] = "high"
    asr: float = Field(default=0.0, ge=0.0, le=1.0)

    model_config = {"extra": "ignore", "strict": True}




class ExportCsvParams(BaseModel):
    """Parameters for research_export_csv tool."""

    data: list[dict] = Field(..., description="List of dictionaries to export")
    filename: str = Field(default="export", min_length=1, max_length=256)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if "/" in v or "\\" in v or v.startswith("."):
            raise ValueError("filename cannot contain path separators or start with '.'")
        return v




class ExportJsonParams(BaseModel):
    """Parameters for research_export_json tool."""

    data: dict = Field(..., description="Dictionary to export")
    filename: str = Field(default="export", min_length=1, max_length=256)
    pretty: bool = Field(default=True, description="Pretty-print JSON")

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if "/" in v or "\\" in v or v.startswith("."):
            raise ValueError("filename cannot contain path separators or start with '.'")
        return v




class ExportListParams(BaseModel):
    """Parameters for research_export_list tool."""

    limit: int = Field(default=50, ge=1, le=1000)

    model_config = {"extra": "ignore", "strict": True}




class FOIATrackerParams(BaseModel):
    """Parameters for research_foia_tracker tool."""

    query: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 100:
            raise ValueError("query max 100 characters")
        return v




class FingerprintBehaviorParams(BaseModel):
    """Parameters for research_fingerprint_behavior tool."""

    model: str = "nvidia"
    probe_count: int = Field(default=10, ge=1, le=10)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Validate model provider name."""
        allowed = {"nvidia", "openai", "anthropic", "groq", "deepseek", "gemini", "moonshot", "vllm", "auto"}
        if v not in allowed:
            raise ValueError(f"model must be one of {allowed}, got {v}")
        return v

    @field_validator("probe_count")
    @classmethod
    def validate_probe_count(cls, v: int) -> int:
        """Validate probe count is between 1-10."""
        if v < 1 or v > 10:
            raise ValueError("probe_count must be 1-10")
        return v




class FingerprintEvasionParams(BaseModel):
    """Parameters for research_fingerprint_evasion_test tool."""

    anonymizer_config: Literal["default", "strict", "custom"] = Field(
        "default",
        description="Type of anonymizer configuration to test",
    )
    test_iterations: int = Field(
        5,
        ge=2,
        le=50,
        description="Number of fingerprint generations to collect (2-50)",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("test_iterations")
    @classmethod
    def validate_iterations(cls, v: int) -> int:
        if v < 2 or v > 50:
            raise ValueError("test_iterations must be 2-50")
        return v



class FingerprintModelParams(BaseModel):
    model_config = {"extra": "ignore", "strict": True}
    response_text: str




class FormatSmuggleParams(BaseModel):
    model_config = {"extra": "ignore", "strict": True}
    prompt: str
    format_type: str = "auto"
    model: str = "auto"




class FullSpectrumParams(BaseModel):
    """Parameters for research_full_spectrum tool."""

    query: str = Field(
        ...,
        description="Original query to analyze and reframe",
        min_length=1,
        max_length=10000,
    )
    model_name: str = Field(
        default="unknown",
        description="Target model identifier (e.g., gpt-4, claude-3-sonnet)",
        max_length=256,
    )
    target_hcs: float = Field(
        default=8.0,
        description="Target HCS (helpfulness/compliance/specificity) score 0-10",
        ge=0.0,
        le=10.0,
    )
    reframing_strategy: Literal[
        "direct_jailbreak",
        "prompt_injection",
        "role_play",
        "hypothetical",
        "indirect_request",
        "token_smuggling",
        "logic_manipulation",
        "consent_smuggling",
        "constraint_relaxation",
        "multi_turn",
        "auto_select",
    ] = Field(
        default="auto_select",
        description="Reframing strategy to apply (auto_select for automatic selection)",
    )
    include_multi_strategy: bool = Field(
        default=False,
        description="If True, run pipeline with all strategies and compare",
    )
    include_report: bool = Field(
        default=True,
        description="If True, generate executive summary report",
    )
    include_recommendations: bool = Field(
        default=True,
        description="If True, generate improvement recommendations",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query", mode="before")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Query must be non-empty string."""
        if not isinstance(v, str):
            raise ValueError("query must be a string")
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Model name must be valid identifier."""
        if not v.strip():
            raise ValueError("model_name cannot be empty")
        if not all(c.isalnum() or c in "-_." for c in v):
            raise ValueError("model_name must be alphanumeric, hyphen, underscore, or dot")
        return v.strip()





class FunctorMapParams(BaseModel):
    """Parameters for research_functor_translate tool."""

    exploit: str
    source_domain: Literal[
        "cybersecurity",
        "social_engineering",
        "legal",
        "academic",
        "medical",
    ] = "cybersecurity"
    target_domain: Literal[
        "cybersecurity",
        "social_engineering",
        "legal",
        "academic",
        "medical",
    ] = "social_engineering"
    preserve_structure: bool = True

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("exploit")
    @classmethod
    def validate_exploit(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 1000:
            raise ValueError("exploit must be 1-1000 characters")
        return v

    @field_validator("source_domain", "target_domain", mode="before")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.lower().strip()
        valid = {"cybersecurity", "social_engineering", "legal", "academic", "medical"}
        if v not in valid:
            raise ValueError(f"domain must be one of {valid}")
        return v




class GeodesicPathParams(BaseModel):
    """Parameters for research_geodesic_path tool."""

    start_prompt: str = Field(..., min_length=10, max_length=5000)
    target_style: Literal["academic", "professional", "technical", "minimal"] = "academic"
    max_steps: int = Field(7, ge=1, le=20)
    step_size: float = Field(0.3, ge=0.1, le=0.5)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("start_prompt")
    @classmethod
    def validate_start_prompt(cls, v: str) -> str:
        if not v or len(v) < 10 or len(v) > 5000:
            raise ValueError("start_prompt must be 10-5000 characters")
        return v.strip()

    @field_validator("target_style")
    @classmethod
    def validate_target_style(cls, v: str) -> str:
        valid = {"academic", "professional", "technical", "minimal"}
        if v not in valid:
            raise ValueError(f"target_style must be one of {valid}")
        return v

    @field_validator("max_steps")
    @classmethod
    def validate_max_steps(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("max_steps must be 1-20")
        return v

    @field_validator("step_size")
    @classmethod
    def validate_step_size(cls, v: float) -> float:
        if v < 0.1 or v > 0.5:
            raise ValueError("step_size must be 0.1-0.5")
        return v



class GhostProtocolParams(BaseModel):
    """Parameters for research_ghost_protocol tool."""

    keywords: list[str]
    time_window_minutes: int = 30

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: list[str]) -> list[str]:
        if not v or len(v) == 0:
            raise ValueError("keywords must be non-empty list")
        if len(v) > 50:
            raise ValueError("keywords max 50 items")
        for kw in v:
            if not kw or not kw.strip():
                raise ValueError("each keyword must be non-empty")
            if len(kw) > 100:
                raise ValueError("each keyword max 100 characters")
        return [kw.strip() for kw in v]

    @field_validator("time_window_minutes")
    @classmethod
    def validate_time_window(cls, v: int) -> int:
        if v < 1 or v > 1440:  # 1 minute to 24 hours
            raise ValueError("time_window_minutes must be 1-1440")
        return v




class GithubReadmeParams(BaseModel):
    """Parameters for research_github_readme tool."""

    repo_url: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("repo_url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        url = validate_url(v)
        if "github.com" not in url.lower():
            raise ValueError("repo_url must be a GitHub URL")
        return url




class GithubReleasesParams(BaseModel):
    """Parameters for research_github_releases tool."""

    repo_url: str
    max_results: int = Field(default=10, alias="limit")

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("repo_url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        url = validate_url(v)
        if "github.com" not in url.lower():
            raise ValueError("repo_url must be a GitHub URL")
        return url

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_results must be 1-100")
        return v




class HCSReportParams(BaseModel):
    """Parameters for research_hcs_report tool."""

    report_type: str = Field(
        default="combined",
        description="Report type: model, strategy, or combined",
        pattern="^(model|strategy|combined)$",
    )
    regression_threshold: float = Field(
        default=1.0,
        description="Min score drop to flag as regression",
        ge=0.1,
        le=5.0,
    )
    data_path: str = Field(
        default="~/.loom/hcs_data.jsonl",
        description="Path to HCS data file",
        max_length=256,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("report_type")
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        """Report type must be valid."""
        if v not in ("model", "strategy", "combined"):
            raise ValueError("report_type must be model, strategy, or combined")
        return v

    @field_validator("data_path")
    @classmethod
    def validate_data_path(cls, v: str) -> str:
        """Data path must be non-empty."""
        if not v.strip():
            raise ValueError("data_path cannot be empty")
        return v.strip()




class HCSRubricParams(BaseModel):
    """Parameters for research_hcs_rubric tool."""

    action: Literal["get_rubric", "get_definition", "score_response", "calibrate"] = Field(
        default="get_rubric",
        description="Action: get_rubric, get_definition, score_response, or calibrate",
    )
    score: int | None = Field(
        default=None,
        description="HCS score for get_definition or score_response (0-10)",
        ge=0,
        le=10,
    )
    response: str | None = Field(
        default=None,
        description="Response text to score (max 50000 chars)",
        max_length=50000,
    )
    responses_with_scores: list[dict[str, Any]] | None = Field(
        default=None,
        description="List of dicts with 'scores' (list[int]) and optional 'response' key",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Action must be valid."""
        if v not in ("get_rubric", "get_definition", "score_response", "calibrate"):
            raise ValueError(
                "action must be: get_rubric, get_definition, score_response, or calibrate"
            )
        return v

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int | None) -> int | None:
        """Score must be 0-10 if provided."""
        if v is not None and (v < 0 or v > 10):
            raise ValueError("score must be 0-10")
        return v

    @field_validator("response")
    @classmethod
    def validate_response(cls, v: str | None) -> str | None:
        """Response must be non-empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("response must be non-empty")
        return v.strip() if v else None




class HierarchicalResearchParams(BaseModel):
    """Parameters for research_hierarchical_research tool."""

    query: str
    depth: int = 2
    max_sources: int = 10
    model: str = "nvidia"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or len(v.strip()) < 3:
            raise ValueError("query must be at least 3 characters")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v.strip()

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: int) -> int:
        if v < 1 or v > 3:
            raise ValueError("depth must be 1-3")
        return v

    @field_validator("max_sources")
    @classmethod
    def validate_max_sources(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("max_sources must be 1-50")
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        valid_models = {"nvidia", "groq", "deepseek", "gemini", "openai", "anthropic"}
        if v.lower() not in valid_models:
            raise ValueError(f"model must be one of {valid_models}")
        return v.lower()



class HttpxProbeParams(BaseModel):
    """Parameters for research_httpx_probe tool."""

    targets: list[str]
    ports: str = "80,443,8080,8443"
    timeout: int = 60

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("targets")
    @classmethod
    def validate_targets(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("targets list cannot be empty")
        if len(v) > 100:
            raise ValueError("targets list max 100 items")
        return v

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("ports cannot be empty")
        # Allow comma-separated port numbers
        if not re.match(r"^[0-9,]+$", v):
            raise ValueError("ports must be comma-separated numbers")
        # Check each port is valid (1-65535)
        ports = [p.strip() for p in v.split(",")]
        for port_str in ports:
            try:
                port = int(port_str)
                if port < 1 or port > 65535:
                    raise ValueError(f"port {port} out of range 1-65535")
            except ValueError:
                raise ValueError(f"invalid port: {port_str}")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 300:
            raise ValueError("timeout must be 1-300 seconds")
        return v




class ImageAnalyzeParams(BaseModel):
    """Parameters for research_image_analyze tool."""

    image_url: str = Field(
        description="Public image URL (https://) or local file path within ~/.loom/",
        min_length=1,
        max_length=4096,
    )
    features: list[str] | None = Field(
        default=None,
        description="Detection features (LABEL_DETECTION, TEXT_DETECTION, FACE_DETECTION, etc.)",
    )
    max_results: int = Field(
        default=10,
        description="Max results per feature (1-100)",
        ge=1,
        le=100,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        if v.startswith("http://") or v.startswith("https://"):
            return validate_url(v)
        # For local file paths, validate they are within ~/.loom/
        return validate_local_file_path(v)

    @field_validator("features")
    @classmethod
    def validate_features(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        valid_features = {
            "LABEL_DETECTION", "TEXT_DETECTION", "FACE_DETECTION",
            "LANDMARK_DETECTION", "LOGO_DETECTION", "SAFE_SEARCH_DETECTION",
            "IMAGE_PROPERTIES", "OBJECT_LOCALIZATION", "WEB_DETECTION"
        }
        invalid = set(v) - valid_features
        if invalid:
            raise ValueError(f"invalid features: {invalid}")
        return v




class InfluenceOperationParams(BaseModel):
    """Parameters for research_influence_operation tool."""

    topic: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        if not v or len(v) > 200:
            raise ValueError("topic must be 1-200 characters")
        return v




class InfoHalfLifeParams(BaseModel):
    """Parameters for research_info_half_life tool."""

    urls: list[str]

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        if not v or len(v) > 100:
            raise ValueError("urls must have 1-100 items")
        validated = []
        for url in v:
            validated.append(validate_url(url))
        return validated




class InformationCascadeParams(BaseModel):
    """Parameters for research_information_cascade tool."""

    topic: str
    hours_back: int = 72

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        if not v or len(v) > 200:
            raise ValueError("topic must be 1-200 characters")
        return v

    @field_validator("hours_back")
    @classmethod
    def validate_hours_back(cls, v: int) -> int:
        if v < 1 or v > 720:
            raise ValueError("hours_back must be 1-720")
        return v




class InfraCorrelatorParams(BaseModel):
    """Parameters for research_infra_correlator tool."""

    ip: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        v = v.strip()
        if not re.match(
            r"^(\d{1,3}\.){3}\d{1,3}$|^([0-9a-f]{0,4}:){2,7}[0-9a-f]{0,4}$", v, re.IGNORECASE
        ):
            raise ValueError("ip must be valid IPv4 or IPv6")
        return v




class InstagramParams(BaseModel):
    """Parameters for research_instagram tool."""

    username: str
    max_posts: int = 10

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or len(v) > 50:
            raise ValueError("username must be 1-50 characters")
        if "@" in v:
            v = v.lstrip("@")
        # Instagram usernames: alphanumeric, underscore, period
        if not all(c.isalnum() or c in ("_", ".") for c in v):
            raise ValueError("username must contain only alphanumeric, underscore, or period")
        return v

    @field_validator("max_posts")
    @classmethod
    def validate_max_posts(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_posts must be 1-100")
        return v




class KatanaCrawlParams(BaseModel):
    """Parameters for research_katana_crawl tool."""

    url: str
    depth: int = 3
    max_pages: int = 100
    timeout: int = 60

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: int) -> int:
        if v < 0 or v > 5:
            raise ValueError("depth must be 0-5")
        return v

    @field_validator("max_pages")
    @classmethod
    def validate_max_pages(cls, v: int) -> int:
        if v < 1 or v > 1000:
            raise ValueError("max_pages must be 1-1000")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 300:
            raise ValueError("timeout must be 1-300 seconds")
        return v




class LeaderboardUpdateParams(BaseModel):
    """Parameters for research_leaderboard_update tool."""

    model: str = Field(..., description="Model name", min_length=1, max_length=100)
    category: str = Field(
        ...,
        description="Benchmark category (injection_resistance, refusal_rate, response_quality)",
    )
    score: float = Field(
        ...,
        description="Score 0-1 (will be clamped)",
        ge=0.0,
        le=1.0,
    )
    details: dict[str, Any] | None = Field(
        None,
        description="Optional test details (JSON-serializable)",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        return v.strip()

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid = {"injection_resistance", "refusal_rate", "response_quality"}
        v = v.strip().lower()
        if v not in valid:
            raise ValueError(
                f"Invalid category: {v}. Must be one of {valid}"
            )
        return v




class LeaderboardViewParams(BaseModel):
    """Parameters for research_leaderboard_view tool."""

    category: str | None = Field(
        None,
        description="Filter by category. If None, shows overall rankings.",
    )
    limit: int = Field(
        20,
        description="Maximum results to return",
        ge=1,
        le=100,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {"injection_resistance", "refusal_rate", "response_quality"}
        v = v.strip().lower()
        if v not in valid:
            raise ValueError(
                f"Invalid category: {v}. Must be one of {valid}"
            )
        return v


class LegalTakedownParams(BaseModel):
    """Parameters for research_legal_takedown tool."""

    domain: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([a-z0-9-]*\.)+[a-z]{2,}$", v):
            raise ValueError("domain format invalid")
        return v




class LightpandaBatchParams(BaseModel):
    """Parameters for research_lightpanda_batch tool."""

    urls: list[str]
    javascript: bool = True
    wait_for: str | None = None
    extract_links: bool = False
    timeout: int = 60

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("urls", mode="before")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        if not v or len(v) == 0:
            raise ValueError("urls list must not be empty")
        if len(v) > 50:
            raise ValueError("urls list max 50 URLs")
        validated = []
        for url in v:
            validated.append(validate_url(url))
        return validated

    @field_validator("wait_for")
    @classmethod
    def validate_wait_for(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 256:
            raise ValueError("wait_for max 256 characters")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 300:
            raise ValueError("timeout must be 1-300 seconds")
        return v




class MemeticSimulateParams(BaseModel):
    """Parameters for research_memetic_simulate tool."""

    idea: str = Field(
        description="Description of idea/strategy to simulate (e.g., 'Appeal to tribal identity')"
    )
    population_size: int = Field(
        default=1000,
        ge=100,
        le=10000,
        description="Size of virtual population (100-10000)"
    )
    generations: int = Field(
        default=50,
        ge=10,
        le=500,
        description="Number of simulation generations (10-500)"
    )
    mutation_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Probability of message mutation per generation (0.0-1.0)"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("idea", mode="before")
    @classmethod
    def validate_idea(cls, v: str) -> str:
        """Validate idea is non-empty string."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("idea must be a non-empty string")
        if len(v) > 500:
            raise ValueError("idea max 500 characters")
        return v.strip()




class MemoryRecallParams(BaseModel):
    """Parameters for research_memory_recall tool."""

    query: str
    namespace: str = "default"
    top_k: int = 5

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or len(v.strip()) < 3:
            raise ValueError("query must be at least 3 characters")
        if len(v) > 10000:
            raise ValueError("query max 10000 characters")
        return v

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("namespace required")
        if len(v) > 32:
            raise ValueError("namespace max 32 characters")
        if not re.match(r"^[a-z0-9_-]+$", v.lower()):
            raise ValueError("namespace must contain only alphanumeric, underscore, hyphen")
        return v.lower()

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("top_k must be 1-20")
        return v



class MemoryStoreParams(BaseModel):
    """Parameters for research_memory_store tool."""

    content: str
    metadata: dict[str, Any] | None = None
    namespace: str = "default"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or len(v.strip()) < 10:
            raise ValueError("content must be at least 10 characters")
        if len(v) > 100000:
            raise ValueError("content max 100000 characters")
        return v

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("namespace required")
        if len(v) > 32:
            raise ValueError("namespace max 32 characters")
        if not re.match(r"^[a-z0-9_-]+$", v.lower()):
            raise ValueError("namespace must contain only alphanumeric, underscore, hyphen")
        return v.lower()




class MetaLearnerParams(BaseModel):
    """Parameters for research_meta_learn tool."""

    successful_strategies: list[str] | None = Field(
        default=None,
        description="List of strategy names that succeeded"
    )
    failed_strategies: list[str] | None = Field(
        default=None,
        description="List of strategy names that failed"
    )
    target_model: str = Field(
        default="auto",
        description="Target model: auto|claude|gpt|gemini|deepseek|o1"
    )
    num_generate: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of new strategies to generate"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("successful_strategies")
    @classmethod
    def validate_successful_strategies(cls, v: list[str] | None) -> list[str] | None:
        """Validate strategy names list."""
        if v is None:
            return v
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("successful_strategies must be non-empty list or None")
        if len(v) > 50:
            raise ValueError("successful_strategies max 50 items")
        for strategy in v:
            if not isinstance(strategy, str) or len(strategy) > 100:
                raise ValueError("each strategy name must be string, max 100 chars")
        return v

    @field_validator("failed_strategies")
    @classmethod
    def validate_failed_strategies(cls, v: list[str] | None) -> list[str] | None:
        """Validate failed strategy names list."""
        if v is None:
            return v
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("failed_strategies must be non-empty list or None")
        if len(v) > 50:
            raise ValueError("failed_strategies max 50 items")
        for strategy in v:
            if not isinstance(strategy, str) or len(strategy) > 100:
                raise ValueError("each strategy name must be string, max 100 chars")
        return v

    @field_validator("target_model")
    @classmethod
    def validate_target_model(cls, v: str) -> str:
        """Validate target model name."""
        valid_models = {"auto", "claude", "gpt", "gemini", "deepseek", "o1"}
        v = v.strip().lower()
        if v not in valid_models:
            raise ValueError(f"target_model must be one of {valid_models}")
        return v




class MisinfoCheckParams(BaseModel):
    """Parameters for research_misinfo_check tool."""

    claim: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("claim")
    @classmethod
    def validate_claim(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("claim must be non-empty")
        if len(v) > 1000:
            raise ValueError("claim max 1000 characters")
        return v




class ModelComparatorParams(BaseModel):
    """Parameters for research_model_comparator tool."""

    prompt: str
    endpoints: list[str]

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("prompt must be non-empty")
        if len(v) > 2000:
            raise ValueError("prompt max 2000 characters")
        return v

    @field_validator("endpoints")
    @classmethod
    def validate_endpoints(cls, v: list[str]) -> list[str]:
        if not v or len(v) < 2:
            raise ValueError("endpoints must have at least 2 items")
        if len(v) > 10:
            raise ValueError("endpoints max 10 items")
        return [validate_url(url) for url in v]




class NucleiScanParams(BaseModel):
    """Parameters for research_nuclei_scan tool."""

    url: str = Field(..., alias="target")
    templates: str = "cves,exposures"
    severity: str = "medium,high,critical"
    timeout: int = 120

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("templates")
    @classmethod
    def validate_templates(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("templates cannot be empty")
        # Allow alphanumeric, commas, hyphens
        if not re.match(r"^[a-z0-9,\-]+$", v.lower()):
            raise ValueError("templates contains invalid characters")
        return v

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("severity cannot be empty")
        # Allow alphanumeric, commas, hyphens
        if not re.match(r"^[a-z0-9,\-]+$", v.lower()):
            raise ValueError("severity contains invalid characters")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 600:
            raise ValueError("timeout must be 1-600 seconds")
        return v




class OCRAdvancedParams(BaseModel):
    """Parameters for research_ocr_advanced tool."""

    image_path_or_url: str
    languages: list[str] | None = Field(None, min_items=1, max_items=10)
    detail: bool = True

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("image_path_or_url", mode="before")
    @classmethod
    def validate_image_path(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("image_path_or_url cannot be empty")
        # Validate if it's a URL
        if v.startswith(("http://", "https://")):
            return validate_url(v)
        # Otherwise, it's a local path - just validate it's a reasonable length
        if len(v) > 500:
            raise ValueError("image_path_or_url too long")
        return v

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        # Validate each language code (2-5 chars)
        for lang in v:
            if not lang or len(lang) > 5:
                raise ValueError(f"Invalid language code: {lang}")
            # Language codes can be 2-3 chars (en, fr) or with underscore/hyphen (zh_CN, pt-BR)
            if not all(c.isalnum() or c in ("_", "-") for c in lang):
                raise ValueError(f"Invalid language code: {lang}")
        return v




class OnionDiscoverParams(BaseModel):
    """Parameters for research_onion_discover tool."""

    query: str
    include_indexes: bool = True
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




class OrchestrateSmartParams(BaseModel):
    """Parameters for research_orchestrate_smart tool."""

    query: str = Field(..., min_length=3, max_length=5000)
    max_tools: int = Field(default=3, ge=1, le=10)
    strategy: Literal["auto", "parallel", "sequential"] = "auto"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query", mode="before")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("query must be a string")
        if len(v.strip()) < 3:
            raise ValueError("query must be at least 3 characters")
        return v.strip()

    @field_validator("max_tools")
    @classmethod
    def validate_max_tools(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("max_tools must be 1-10")
        return v



class PDFAdvancedParams(BaseModel):
    """Parameters for research_pdf_advanced tool."""

    pdf_path_or_url: str
    extract_images: bool = False
    extract_tables: bool = True

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("pdf_path_or_url", mode="before")
    @classmethod
    def validate_pdf_path(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("pdf_path_or_url cannot be empty")
        # Validate if it's a URL
        if v.startswith(("http://", "https://")):
            return validate_url(v)
        # Otherwise, it's a local path - just validate it's a reasonable length
        if len(v) > 500:
            raise ValueError("pdf_path_or_url too long")
        return v




class ParadoxImmunizeParams(BaseModel):
    """Parameters for research_paradox_immunize tool."""

    system_prompt: str = Field(..., min_length=1, max_length=20000)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("system_prompt cannot be empty or whitespace only")
        return v




class ParallelExecutorParams(BaseModel):
    """Parameters for research_parallel_execute tool."""

    tools: list[dict[str, Any]] = Field(
        ..., description="List of {'tool': 'research_xxx', 'params': {...}}"
    )
    timeout_seconds: int = Field(30, ge=1, le=300, description="Timeout per tool")

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("tools")
    @classmethod
    def validate_tools(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not v:
            raise ValueError("tools list cannot be empty")
        if len(v) > 50:
            raise ValueError("tools list max 50 items")
        return v




class ParallelPlanExecutorParams(BaseModel):
    """Parameters for research_parallel_plan_and_execute tool."""

    goal: str = Field(..., description="Research goal or query", min_length=1, max_length=2000)
    max_parallel: int = Field(5, ge=1, le=20, description="Max concurrent tools")

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        return v.strip()



class PersistentMemoryRecallParams(BaseModel):
    """Parameters for research_recall tool."""

    query: str = Field(..., min_length=1, max_length=10000)
    top_k: int = Field(default=10, ge=1, le=100)
    topic: str = Field(default="", max_length=100)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate query is not empty after strip."""
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Validate topic format."""
        if v and not re.match(r"^[a-z0-9_-]+$", v.lower()):
            raise ValueError("topic must contain only alphanumeric, underscore, hyphen")
        return v.lower() if v else ""



class PersistentMemoryRememberParams(BaseModel):
    """Parameters for research_remember tool."""

    content: str = Field(..., min_length=10, max_length=100000)
    topic: str = Field(default="", max_length=100)
    session_id: str = Field(default="", max_length=100)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is not empty after strip."""
        if not v.strip():
            raise ValueError("content cannot be empty")
        return v.strip()

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Validate topic format."""
        if v and not re.match(r"^[a-z0-9_-]+$", v.lower()):
            raise ValueError("topic must contain only alphanumeric, underscore, hyphen")
        return v.lower() if v else ""

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validate session_id format."""
        if v and not re.match(r"^[a-z0-9_-]+$", v.lower()):
            raise ValueError("session_id must contain only alphanumeric, underscore, hyphen")
        return v.lower() if v else ""




class PersonalizeOutputParams(BaseModel):
    """Parameters for research_personalize_output tool."""

    content: str = Field(
        description="Raw research content to personalize"
    )
    audience: str = Field(
        default="executive",
        description="Target audience (executive, technical, academic, journalist, investor, regulator)"
    )
    cognitive_style: str = Field(
        default="visual",
        description="Preferred learning style (visual, analytical, narrative, procedural)"
    )
    expertise_level: str = Field(
        default="expert",
        description="Reader expertise (novice, intermediate, expert, domain_expert)"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is non-empty string."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("content must be a non-empty string")
        if len(v) > 50000:
            raise ValueError("content max 50000 characters")
        return v.strip()

    @field_validator("audience")
    @classmethod
    def validate_audience(cls, v: str) -> str:
        """Validate audience is one of allowed values."""
        valid = {"executive", "technical", "academic", "journalist", "investor", "regulator"}
        if v not in valid:
            raise ValueError(f"audience must be one of {valid}")
        return v

    @field_validator("cognitive_style")
    @classmethod
    def validate_cognitive_style(cls, v: str) -> str:
        """Validate cognitive_style is one of allowed values."""
        valid = {"visual", "analytical", "narrative", "procedural"}
        if v not in valid:
            raise ValueError(f"cognitive_style must be one of {valid}")
        return v

    @field_validator("expertise_level")
    @classmethod
    def validate_expertise_level(cls, v: str) -> str:
        """Validate expertise_level is one of allowed values."""
        valid = {"novice", "intermediate", "expert", "domain_expert"}
        if v not in valid:
            raise ValueError(f"expertise_level must be one of {valid}")
        return v




class PromptReframeParams(BaseModel):
    model_config = {"extra": "ignore", "strict": True}
    prompt: str
    strategy: str = "auto"
    model: str = "auto"
    framework: str = "ieee"




class PydanticAgentParams(BaseModel):
    """Parameters for research_pydantic_agent tool."""

    prompt: str
    model: str = "nvidia_nim"
    system_prompt: str = ""
    max_tokens: int = 1000

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("prompt must be non-empty")
        v = v.strip()
        if len(v) > 20000:
            raise ValueError("prompt max 20000 characters")
        return v

    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, v: str) -> str:
        if v and len(v) > 5000:
            raise ValueError("system_prompt max 5000 characters")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        if v < 10 or v > 8000:
            raise ValueError("max_tokens must be 10-8000")
        return v




class QueryBuilderParams(BaseModel):
    """Parameters for research_build_query tool."""

    user_request: str
    context: str = ""
    output_type: Literal["research", "osint", "threat_intel", "academic"] = "research"
    max_queries: int = 5
    optimize: bool = True

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("user_request")
    @classmethod
    def validate_user_request(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("user_request must be non-empty")
        v = v.strip()
        if len(v) > 5000:
            raise ValueError("user_request max 5000 characters")
        return v

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: str) -> str:
        if v and len(v) > 2000:
            raise ValueError("context max 2000 characters")
        return v

    @field_validator("max_queries")
    @classmethod
    def validate_max_queries(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("max_queries must be 1-10")
        return v



class RAGAttackParams(BaseModel):
    """Parameters for research_rag_attack tool."""

    query: str = Field(..., min_length=1, max_length=500)
    attack_type: Literal[
        "retrieval_poison", "synonym_swap", "context_inject", "semantic_trojan"
    ] = "retrieval_poison"
    num_chunks: int = Field(default=5, ge=1, le=10)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or len(v) < 3:
            raise ValueError("query must be at least 3 characters")
        return v.strip()

    @field_validator("num_chunks")
    @classmethod
    def validate_num_chunks(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("num_chunks must be 1-10")
        return v



class RecommendNextParams(BaseModel):
    """Parameters for research_recommend_next tool."""

    last_tool: str = Field(..., min_length=1, max_length=100)
    context: str = Field(default="", max_length=5000)
    top_k: int = Field(default=5, ge=1, le=20)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("last_tool")
    @classmethod
    def validate_last_tool(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("last_tool cannot be empty")
        return v.strip()

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("top_k must be 1-20")
        return v




class RunExperimentParams(BaseModel):
    """Parameters for research_run_experiment tool."""

    hypothesis: str = Field(
        description="Research hypothesis to test (e.g., 'Strategy X increases success rate')"
    )
    variables: list[str] | None = Field(
        default=None,
        description="Treatment variables to test (e.g., ['strategy_v1', 'strategy_v2'])"
    )
    trials: int = Field(
        default=10,
        ge=3,
        le=100,
        description="Number of trials per condition (3-100)"
    )
    metric: Literal["success_rate", "response_length", "specificity", "stealth_score"] = Field(
        default="success_rate",
        description="Metric to measure: success_rate, response_length, specificity, or stealth_score"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("hypothesis", mode="before")
    @classmethod
    def validate_hypothesis(cls, v: str) -> str:
        """Validate hypothesis is non-empty string."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("hypothesis must be a non-empty string")
        if len(v) > 256:
            raise ValueError("hypothesis max 256 characters")
        return v.strip()

    @field_validator("variables", mode="before")
    @classmethod
    def validate_variables(cls, v: list[str] | None) -> list[str] | None:
        """Validate variables list."""
        if v is None:
            return v
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("variables must be non-empty list or None")
        if len(v) > 10:
            raise ValueError("variables max 10 items")
        for var in v:
            if not isinstance(var, str) or not var.strip():
                raise ValueError("each variable must be non-empty string")
            if len(var) > 64:
                raise ValueError("each variable max 64 characters")
        return v




class SafetyCircuitMapParams(BaseModel):
    """Parameters for research_safety_circuit_map tool."""

    model: str = "auto"
    probe_type: Literal["contrastive", "ablation", "activation"] = "contrastive"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if len(v) > 100:
            raise ValueError("model identifier max 100 chars")
        return v

    @field_validator("probe_type")
    @classmethod
    def validate_probe_type(cls, v: str) -> str:
        if v not in ["contrastive", "ablation", "activation"]:
            raise ValueError("probe_type must be contrastive, ablation, or activation")
        return v




class SaveNoteParams(BaseModel):
    """Parameters for research_save_note tool."""

    title: str = Field(
        description="Note title",
        max_length=256,
    )
    content: str = Field(
        description="Note content",
        max_length=100000,
    )
    notebook: str | None = Field(
        default=None,
        description="Optional notebook name",
        max_length=256,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title cannot be empty")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("content cannot be empty")
        return v.strip()





class ScraperEngineBatchParams(BaseModel):
    """Parameters for research_engine_batch tool."""

    urls: list[str]
    mode: Literal["auto", "stealth", "max", "fast"] = "auto"
    max_concurrent: int = 10
    fail_fast: bool = False

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("urls cannot be empty")
        if len(v) > 100:
            raise ValueError("urls max 100 items")
        return [validate_url(url) for url in v]

    @field_validator("max_concurrent")
    @classmethod
    def validate_max_concurrent(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("max_concurrent must be 1-50")
        return v




class SecTrackerParams(BaseModel):
    """Parameters for research_sec_tracker tool."""

    company: str
    filing_types: list[str] | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("company")
    @classmethod
    def validate_company(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 500:
            raise ValueError("company must be 1-500 characters")
        return v

    @field_validator("filing_types")
    @classmethod
    def validate_filing_types(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if len(v) == 0:
            raise ValueError("filing_types must be non-empty or None")
        if len(v) > 20:
            raise ValueError("filing_types max 20 items")
        valid_types = {"10-K", "10-Q", "8-K", "S-1", "S-4", "DEF 14A", "20-F", "424B5"}
        for ft in v:
            if ft not in valid_types:
                raise ValueError(f"filing_type '{ft}' not in {valid_types}")
        return v




class SherlockBatchParams(BaseModel):
    """Parameters for research_sherlock_batch tool."""

    usernames: list[str]
    platforms: list[str] | None = None
    timeout: int = 30

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("usernames", mode="before")
    @classmethod
    def validate_usernames(cls, v: list[str]) -> list[str]:
        if not isinstance(v, list):
            raise ValueError("usernames must be a list")
        if not v:
            raise ValueError("usernames list cannot be empty")
        if len(v) > 100:
            raise ValueError("usernames list cannot exceed 100 items")
        # Strip all usernames first
        stripped = [u.strip() if isinstance(u, str) else u for u in v]
        for username in stripped:
            if not isinstance(username, str):
                raise ValueError("each username must be a string")
            if not username or len(username) > 255:
                raise ValueError("each username must be 1-255 characters")
            if not re.match(r"^[a-z0-9._\-+]+$", username, re.IGNORECASE):
                raise ValueError(
                    f"username '{username}' contains disallowed characters"
                )
        return stripped

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError("platforms must be a list of strings")
        if len(v) > 50:
            raise ValueError("platforms list cannot exceed 50 items")
        for platform in v:
            if not isinstance(platform, str):
                raise ValueError("each platform must be a string")
            if len(platform) > 100:
                raise ValueError("platform name cannot exceed 100 characters")
            if not re.match(r"^[a-z0-9_\-]+$", platform, re.IGNORECASE):
                raise ValueError(f"platform '{platform}' contains disallowed characters")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 300:
            raise ValueError("timeout must be 1-300 seconds")
        return v




class SherlockLookupParams(BaseModel):
    """Parameters for research_sherlock_lookup tool."""

    username: str
    platforms: list[str] | None = None
    timeout: int = 30

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("username", mode="before")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip() if isinstance(v, str) else ""
        if not v or len(v) > 255:
            raise ValueError("username must be 1-255 characters")
        # Allow alphanumeric, underscore, hyphen, period, plus
        if not re.match(r"^[a-z0-9._\-+]+$", v, re.IGNORECASE):
            raise ValueError("username contains disallowed characters")
        return v

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError("platforms must be a list of strings")
        if len(v) > 50:
            raise ValueError("platforms list cannot exceed 50 items")
        for platform in v:
            if not isinstance(platform, str):
                raise ValueError("each platform must be a string")
            if len(platform) > 100:
                raise ValueError("platform name cannot exceed 100 characters")
            if not re.match(r"^[a-z0-9_\-]+$", platform, re.IGNORECASE):
                raise ValueError(f"platform '{platform}' contains disallowed characters")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 300:
            raise ValueError("timeout must be 1-300 seconds")
        return v




class SimplifyParams(BaseModel):
    """Parameters for research_simplify tool."""

    text: str = Field(..., min_length=1, max_length=50000)
    target_audience: Literal["executive", "investor", "child", "tweet", "headline"] = Field(
        default="executive"
    )
    max_length: int = Field(default=500, ge=100, le=5000)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text is non-empty."""
        if not v.strip():
            raise ValueError("text cannot be empty")
        return v




class SitemapCrawlParams(BaseModel):
    """Parameters for research_sitemap_crawl tool."""

    url: str
    max_pages: int = Field(
        default=50,
        description="Maximum pages to crawl from sitemap (1-500)",
        ge=1,
        le=500,
    )
    use_js: bool = Field(
        default=False,
        description="Use Playwright (JS-enabled) instead of BeautifulSoup",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)




class SourceCredibilityParams(BaseModel):
    """Parameters for research_source_credibility tool."""

    url: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)




class StackReframeParams(BaseModel):
    model_config = {"extra": "ignore", "strict": True}
    prompt: str
    strategies: str = "deep_inception,recursive_authority"
    model: str = "auto"




class StrangeAttractorParams(BaseModel):
    """Parameters for research_attractor_trap tool."""

    prompt: str
    attractor_type: Literal["lorenz", "rossler", "henon", "logistic"] = "lorenz"
    iterations: int = Field(default=100, ge=50, le=500)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("prompt must be non-empty string")
        if len(v) > 2000:
            raise ValueError("prompt max 2000 characters")
        return v.strip()

    @field_validator("attractor_type")
    @classmethod
    def validate_attractor_type(cls, v: str) -> str:
        v = v.lower().strip()
        valid = {"lorenz", "rossler", "henon", "logistic"}
        if v not in valid:
            raise ValueError(f"attractor_type must be one of {valid}")
        return v



class SubcultureIntelParams(BaseModel):
    """Parameters for research_subculture_intel tool."""

    topic: str
    platforms: list[str] | None = None

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Validate research topic."""
        v = v.strip()
        if not v or len(v) > 500:
            raise ValueError("topic must be 1-500 characters")
        return v

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v: list[str] | None) -> list[str] | None:
        """Validate platform names."""
        if v is None:
            return v
        valid_platforms = {"4chan", "2ch.hk", "reddit", "telegram", "weibo", "vk"}
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("platforms must be non-empty list or None")
        if len(v) > 10:
            raise ValueError("platforms max 10 items")
        for platform in v:
            if platform not in valid_platforms:
                raise ValueError(f"platform '{platform}' not supported")
        return v




class SubfinderParams(BaseModel):
    """Parameters for research_subfinder tool."""

    domain: str
    timeout: int = 60

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 255:
            raise ValueError("domain must be 1-255 characters")
        # Allow alphanumeric, dots, hyphens, underscores
        if not re.match(r"^[a-z0-9._-]+$", v, re.IGNORECASE):
            raise ValueError("domain contains disallowed characters")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 120:
            raise ValueError("timeout must be 1-120 seconds")
        return v




class SynthesizeReportParams(BaseModel):
    """Parameters for research_synthesize_report tool."""

    question: str = Field(..., min_length=3, max_length=5000)
    answers: list[str] = Field(..., min_length=1, max_length=50)
    format: str = Field(default="executive", pattern=r"^(executive|technical|academic)$")
    max_tokens: int = Field(default=3000, ge=100, le=10000)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, v: list[str]) -> list[str]:
        """Validate that all answers are non-empty strings."""
        for i, ans in enumerate(v):
            if not isinstance(ans, str) or not ans.strip():
                raise ValueError(f"answer {i}: must be non-empty string")
        return v




class TaskCriticalPathParams(BaseModel):
    """Parameters for research_critical_path tool."""

    tasks: list[dict] = Field(..., min_items=1, max_items=1000)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("tasks")
    @classmethod
    def validate_tasks(cls, v: list[dict]) -> list[dict]:
        if not v:
            raise ValueError("tasks list cannot be empty")
        if len(v) > 1000:
            raise ValueError("tasks list max 1000 items")
        for i, task in enumerate(v):
            if not isinstance(task, dict):
                raise ValueError(f"task {i} must be a dict")
            if "name" not in task:
                raise ValueError(f"task {i} missing required field: name")
            name = task.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"task {i}: name must be non-empty string")
            if len(name) > 256:
                raise ValueError(f"task {i}: name max 256 characters")
            depends_on = task.get("depends_on", [])
            if not isinstance(depends_on, list):
                raise ValueError(f"task {i}: depends_on must be list")
            for dep in depends_on:
                if not isinstance(dep, str) or not dep.strip():
                    raise ValueError(f"task {i}: depends_on items must be non-empty strings")
            duration = task.get("duration_minutes", 1)
            if not isinstance(duration, int) or duration < 1:
                raise ValueError(f"task {i}: duration_minutes must be integer >= 1")
        return v




class TaskResolveOrderParams(BaseModel):
    """Parameters for research_resolve_order tool."""

    tasks: list[dict] = Field(..., min_items=1, max_items=1000)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("tasks")
    @classmethod
    def validate_tasks(cls, v: list[dict]) -> list[dict]:
        if not v:
            raise ValueError("tasks list cannot be empty")
        if len(v) > 1000:
            raise ValueError("tasks list max 1000 items")
        for i, task in enumerate(v):
            if not isinstance(task, dict):
                raise ValueError(f"task {i} must be a dict")
            if "name" not in task:
                raise ValueError(f"task {i} missing required field: name")
            name = task.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"task {i}: name must be non-empty string")
            if len(name) > 256:
                raise ValueError(f"task {i}: name max 256 characters")
            depends_on = task.get("depends_on", [])
            if not isinstance(depends_on, list):
                raise ValueError(f"task {i}: depends_on must be list")
            for dep in depends_on:
                if not isinstance(dep, str) or not dep.strip():
                    raise ValueError(f"task {i}: depends_on items must be non-empty strings")
        return v




class TextToSpeechParams(BaseModel):
    """Parameters for research_text_to_speech tool."""

    text: str = Field(
        description="Text to convert to speech",
        max_length=10000,
    )
    voice: str | None = Field(
        default=None,
        description="Voice identifier",
        max_length=64,
    )
    language: str | None = Field(
        default=None,
        description="Language code (e.g., en-US, ar-SA)",
        max_length=16,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text cannot be empty")
        return v.strip()




class ToolRecommendParams(BaseModel):
    """Parameters for research_recommend_tools tool."""

    query: str = Field(
        description="Research task or question",
        max_length=5000,
    )
    max_recommendations: int = Field(
        default=10,
        description="How many tools to recommend (1-50)",
        ge=1,
        le=50,
    )
    exclude_used: list[str] | None = Field(
        default=None,
        description="List of tool names to skip",
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()




class TorbotParams(BaseModel):
    """Parameters for research_torbot tool."""

    url: str
    depth: int = 2

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("depth must be 1-5")
        return v




class ToxicityCheckParams(BaseModel):
    """Parameters for research_toxicity_check tool."""

    text: str = Field(..., min_length=3, max_length=500000)
    compare_prompt: str | None = Field(default=None, max_length=100000)
    compare_response: str | None = Field(default=None, max_length=500000)

    model_config = {"extra": "ignore", "strict": True}




class UnifiedScoreParams(BaseModel):
    """Parameters for research_unified_score tool."""

    prompt: str = Field(
        description="The original prompt/query sent to the model",
        max_length=10000,
    )
    response: str = Field(
        description="The model's response to evaluate",
        max_length=100000,
    )
    model: str = Field(
        default="",
        description="Optional model identifier (e.g., 'gpt-4-turbo', 'claude-3')",
        max_length=256,
    )
    strategy: str = Field(
        default="",
        description="Optional attack strategy if evaluating jailbreak (e.g., 'role_play', 'prompt_injection')",
        max_length=256,
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """Prompt must be non-empty string."""
        if not v or not isinstance(v, str):
            raise ValueError("prompt must be non-empty string")
        if len(v.strip()) == 0:
            raise ValueError("prompt cannot be whitespace-only")
        return v

    @field_validator("response")
    @classmethod
    def validate_response(cls, v: str) -> str:
        """Response must be non-empty string."""
        if not isinstance(v, str):
            raise ValueError("response must be string")
        # Allow empty response for scoring purposes (will get zero score)
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Model identifier validation."""
        if v:
            if len(v) > 256:
                raise ValueError("model max 256 characters")
            if not all(c.isalnum() or c in "-_. " for c in v):
                raise ValueError("model must contain only alphanumeric, hyphen, underscore, dot, or space")
        return v

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        """Strategy identifier validation."""
        if v:
            if len(v) > 256:
                raise ValueError("strategy max 256 characters")
            valid_strategies = {
                "direct_jailbreak",
                "prompt_injection",
                "role_play",
                "hypothetical",
                "watering_hole",
                "indirect_request",
                "context_overflow",
                "token_smuggling",
                "logic_manipulation",
                "consent_smuggling",
                "constraint_relaxation",
                "multi_turn",
                "unknown",
            }
            if v not in valid_strategies:
                # Allow any strategy, just validate format
                if not all(c.isalnum() or c in "_-" for c in v):
                    raise ValueError("strategy must be alphanumeric with underscore or hyphen")
        return v



class VisionBrowseParams(BaseModel):
    """Parameters for research_vision_browse tool."""

    url: str = Field(..., description="URL to screenshot and analyze")
    task: str = Field(
        ..., description="Task/question to analyze the screenshot for (e.g., 'Check if login form present')"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("task")
    @classmethod
    def validate_task(cls, v: str) -> str:
        if not v or len(v) > 500:
            raise ValueError("task must be 1-500 characters")
        return v.strip()




class VisionCompareParams(BaseModel):
    """Parameters for research_vision_compare tool."""

    url1: str = Field(..., description="First URL to compare")
    url2: str = Field(..., description="Second URL to compare")

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url1", "url2", mode="before")
    @classmethod
    def validate_urls(cls, v: str) -> str:
        return validate_url(v)




class WebTimeMachineParams(BaseModel):
    """Parameters for research_web_time_machine tool."""

    url: str
    snapshots: int = 10

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("snapshots")
    @classmethod
    def validate_snapshots(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("snapshots must be 1-100")
        return v




class WhiteRabbitParams(BaseModel):
    """Parameters for research_white_rabbit tool."""

    starting_point: str = Field(
        ..., min_length=3, max_length=500,
        description="Initial research topic or claim"
    )
    depth: int = Field(
        5, ge=1, le=10,
        description="How many levels deep to follow"
    )
    branch_factor: int = Field(
        3, ge=1, le=5,
        description="How many anomalies to explore at each level"
    )
    curiosity_threshold: float = Field(
        0.7, ge=0.0, le=1.0,
        description="Min anomaly score (0.0-1.0) to follow further"
    )

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("starting_point")
    @classmethod
    def validate_starting_point(cls, v: str) -> str:
        """Validate starting point is not empty and reasonable length."""
        if not v or not v.strip():
            raise ValueError("starting_point cannot be empty")
        if len(v.strip()) < 3:
            raise ValueError("starting_point must be at least 3 chars")
        return v.strip()



class WikiEventCorrelatorParams(BaseModel):
    """Parameters for research_wiki_event_correlator tool."""

    page_title: str
    days_back: int = 30

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("page_title")
    @classmethod
    def validate_page_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("page_title must be non-empty")
        if len(v) > 200:
            raise ValueError("page_title max 200 characters")
        return v

    @field_validator("days_back")
    @classmethod
    def validate_days_back(cls, v: int) -> int:
        if v < 1 or v > 365:
            raise ValueError("days_back must be 1-365")
        return v




class ZenBatchParams(BaseModel):
    """Parameters for research_zen_batch tool."""

    urls: list[str]
    max_concurrent: int = 5
    timeout: int = 30

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("urls list cannot be empty")
        if len(v) > 100:
            raise ValueError("urls list max 100 items")
        return [validate_url(url) for url in v]

    @field_validator("max_concurrent")
    @classmethod
    def validate_max_concurrent(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("max_concurrent must be 1-50")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 120:
            raise ValueError("timeout must be 1-120 seconds")
        return v




class ZenInteractParams(BaseModel):
    """Parameters for research_zen_interact tool."""

    url: str
    actions: list[dict[str, str]]
    timeout: int = 30

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("actions")
    @classmethod
    def validate_actions(cls, v: list[dict[str, str]]) -> list[dict[str, str]]:
        if not v:
            raise ValueError("actions list cannot be empty")
        if len(v) > 50:
            raise ValueError("actions list max 50 items")

        valid_types = {"click", "fill", "scroll", "wait"}
        for i, action in enumerate(v):
            if not isinstance(action, dict):
                raise ValueError(f"action {i} must be a dict")
            action_type = action.get("type", "").lower()
            if action_type not in valid_types:
                raise ValueError(
                    f"action {i} type must be one of {valid_types}, got {action_type}",
                )
            if action_type in ("click", "fill", "wait"):
                if "selector" not in action or not action["selector"]:
                    raise ValueError(f"action {i} ({action_type}) requires selector")
            if action_type == "fill":
                if "value" not in action:
                    raise ValueError(f"action {i} (fill) requires value")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 120:
            raise ValueError("timeout must be 1-120 seconds")
        return v



