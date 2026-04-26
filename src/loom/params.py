"""Pydantic v2 parameter models for all MCP tool arguments.

Each tool has a dedicated model with field validators for URLs, headers,
proxies, etc. All models forbid extra fields and use strict mode.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from loom.validators import filter_headers, validate_js_script, validate_url


class FetchParams(BaseModel):
    """Parameters for research_fetch tool."""

    url: str
    mode: Literal["http", "stealthy", "dynamic"] = "stealthy"
    auto_escalate: bool = False
    solve_cloudflare: bool = True
    bypass_cache: bool = False
    max_chars: int = 20000
    headers: dict[str, str] | None = None
    user_agent: str | None = None
    proxy: str | None = None
    cookies: dict[str, str] | None = None
    basic_auth: tuple[str, str] | None = None
    retries: int = 0
    timeout: int | None = None
    wait_for: str | None = None
    accept_language: str = "en-US,en;q=0.9,ar;q=0.8"
    session: str | None = None
    return_format: Literal["text", "html", "json", "screenshot"] = "text"
    extract_selector: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("user_agent")
    @classmethod
    def validate_user_agent(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 256:
            raise ValueError("user_agent max 256 chars")
        return v

    @field_validator("proxy")
    @classmethod
    def validate_proxy(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Basic proxy URL format check
        if not v.startswith(("http://", "https://", "socks5://", "socks5h://")):
            raise ValueError("proxy must start with http://, https://, socks5://, or socks5h://")
        return v

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        return filter_headers(v)

    @field_validator("retries")
    @classmethod
    def validate_retries(cls, v: int) -> int:
        if v < 0 or v > 3:
            raise ValueError("retries must be 0-3")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 120):
            raise ValueError("timeout must be 1-120 seconds")
        return v


class SpiderParams(BaseModel):
    """Parameters for research_spider tool."""

    urls: list[str]
    mode: Literal["http", "stealthy", "dynamic"] = "stealthy"
    max_chars_each: int = 5000
    concurrency: int = 5
    fail_fast: bool = False
    dedupe: bool = True
    order: Literal["input", "domain", "size"] = "input"
    solve_cloudflare: bool = True
    headers: dict[str, str] | None = None
    user_agent: str | None = None
    proxy: str | None = None
    cookies: dict[str, str] | None = None
    accept_language: str = "en-US,en;q=0.9,ar;q=0.8"
    timeout: int | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        # Validate each URL individually
        return [validate_url(url) for url in v]

    @field_validator("proxy")
    @classmethod
    def validate_proxy(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Basic proxy URL format check
        if not v.startswith(("http://", "https://", "socks5://", "socks5h://")):
            raise ValueError("proxy must start with http://, https://, socks5://, or socks5h://")
        return v

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        return filter_headers(v)

    @field_validator("concurrency")
    @classmethod
    def validate_concurrency(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("concurrency must be 1-20")
        return v


class MarkdownParams(BaseModel):
    """Parameters for research_markdown tool."""

    url: str
    bypass_cache: bool = False
    css_selector: str | None = None
    js_before_scrape: str | None = None
    screenshot: bool = False
    remove_selectors: list[str] | None = None
    headers: dict[str, str] | None = None
    user_agent: str | None = None
    proxy: str | None = None
    cookies: dict[str, str] | None = None
    accept_language: str = "en-US,en;q=0.9,ar;q=0.8"
    timeout: int | None = None
    extract_selector: str | None = None
    wait_for: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("proxy")
    @classmethod
    def validate_proxy(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Basic proxy URL format check
        if not v.startswith(("http://", "https://", "socks5://", "socks5h://")):
            raise ValueError("proxy must start with http://, https://, socks5://, or socks5h://")
        return v

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        return filter_headers(v)

    @field_validator("js_before_scrape")
    @classmethod
    def validate_js(cls, v: str | None) -> str | None:
        if v is not None:
            if len(v) > 2048:
                raise ValueError("js_before_scrape max 2 KB")
            validate_js_script(v)
        return v


class SearchParams(BaseModel):
    """Parameters for research_search tool."""

    query: str
    provider: Literal[
        "exa",
        "tavily",
        "firecrawl",
        "brave",
        "ddgs",
        "arxiv",
        "wikipedia",
        "hackernews",
        "reddit",
        "newsapi",
        "crypto",
        "coindesk",
        "binance",
        "investing",
        "ahmia",
        "darksearch",
        "ummro",
    ] = "exa"
    n: int = 10
    provider_config: dict[str, Any] | None = None
    bypass_cache: bool = False

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("n")
    @classmethod
    def validate_n(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("n must be 1-100")
        return v


class DeepParams(BaseModel):
    """Parameters for research_deep tool."""

    query: str
    n_urls: int = 5
    n_results_per_url: int = 3
    dedupe_threshold: float = 0.7
    auto_detect_type: bool = True
    expand_query: bool = True
    fetch_full_pages: bool = True
    extract_info: bool = True
    synthesize: bool = True
    max_cost_usd: float = 1.0
    use_cache: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("n_urls", "n_results_per_url")
    @classmethod
    def validate_counts(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("counts must be 1-50")
        return v

    @field_validator("dedupe_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError("dedupe_threshold must be 0.0-1.0")
        return v


class GithubParams(BaseModel):
    """Parameters for research_github tool."""

    query: str
    search_type: Literal["repos", "code", "users", "issues"] = "repos"
    sort: Literal["stars", "forks", "updated"] = "stars"
    language: str | None = None
    limit: int = 10

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("limit must be 1-100")
        return v


class CacheStatsParams(BaseModel):
    """Parameters for research_cache_stats tool."""

    days_back: int = 7
    min_size_kb: int = 0

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("days_back")
    @classmethod
    def validate_days(cls, v: int) -> int:
        if v < 1 or v > 365:
            raise ValueError("days_back must be 1-365")
        return v


class CacheClearParams(BaseModel):
    """Parameters for research_cache_clear tool."""

    older_than_days: int = 30
    pattern: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("older_than_days")
    @classmethod
    def validate_days(cls, v: int) -> int:
        if v < 0 or v > 365:
            raise ValueError("older_than_days must be 0-365")
        return v


class CamoufoxParams(BaseModel):
    """Parameters for research_camoufox tool."""

    url: str
    wait_for_selector: str | None = None
    screenshot: bool = False
    max_chars: int = 50000
    cookies: dict[str, str] | None = None
    headers: dict[str, str] | None = None
    timeout: int | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        return filter_headers(v)


class BotasaurusParams(BaseModel):
    """Parameters for research_botasaurus tool."""

    url: str
    js_code: str | None = None
    screenshot: bool = False
    max_chars: int = 50000
    timeout: int | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("js_code")
    @classmethod
    def validate_js(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 5000:
            raise ValueError("js_code max 5 KB")
        return v


class RedTeamParams(BaseModel):
    """Parameters for research_red_team tool."""

    claim: str
    n_counter: int = 3
    max_cost_usd: float = 0.1

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("n_counter")
    @classmethod
    def validate_n_counter(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("n_counter must be 1-10")
        return v


class MultilingualParams(BaseModel):
    """Parameters for research_multilingual tool."""

    query: str
    languages: list[str] | None = None
    n_per_lang: int = 3
    max_cost_usd: float = 0.1

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("n_per_lang")
    @classmethod
    def validate_n(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("n_per_lang must be 1-20")
        return v


class ConsensusParams(BaseModel):
    """Parameters for research_consensus tool."""

    query: str
    providers: list[str] | None = None
    n_per_provider: int = 3

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("n_per_provider")
    @classmethod
    def validate_n(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("n_per_provider must be 1-20")
        return v


class MisinfoCheckParams(BaseModel):
    """Parameters for research_misinfo_check tool."""

    claim: str
    n_searches: int = 5

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("n_searches")
    @classmethod
    def validate_n(cls, v: int) -> int:
        if v < 1 or v > 20:
            raise ValueError("n_searches must be 1-20")
        return v


class TemporalDiffParams(BaseModel):
    """Parameters for research_temporal_diff tool."""

    url: str
    date1: str | None = None
    date2: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class CitationGraphParams(BaseModel):
    """Parameters for research_citation_graph tool."""

    paper_id: str
    direction: Literal["forward", "backward", "both"] = "both"
    max_depth: int = 2

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("max_depth")
    @classmethod
    def validate_depth(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("max_depth must be 1-5")
        return v


class AIDetectParams(BaseModel):
    """Parameters for research_ai_detect tool."""

    text: str
    detailed: bool = False

    model_config = {"extra": "forbid", "strict": True}


class CurriculumParams(BaseModel):
    """Parameters for research_curriculum tool."""

    topic: str
    levels: int = 5
    max_cost_usd: float = 0.1

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("levels")
    @classmethod
    def validate_levels(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("levels must be 1-10")
        return v


class CommunitySentimentParams(BaseModel):
    """Parameters for research_community_sentiment tool."""

    query: str
    sources: list[Literal["hackernews", "reddit"]] | None = None

    model_config = {"extra": "forbid", "strict": True}


class WikiGhostParams(BaseModel):
    """Parameters for research_wiki_ghost tool."""

    topic: str
    language: str = "en"

    model_config = {"extra": "forbid", "strict": True}


class SemanticSitemapParams(BaseModel):
    """Parameters for research_semantic_sitemap tool."""

    url: str
    depth: int = 2
    max_urls: int = 50

    model_config = {"extra": "forbid", "strict": True}

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


class WaybackParams(BaseModel):
    """Parameters for research_wayback tool."""

    url: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class ExpertiseParams(BaseModel):
    """Parameters for research_expertise tool."""

    query: str
    n: int = 5

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("n")
    @classmethod
    def validate_n(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("n must be 1-50")
        return v


class GhostWeaveParams(BaseModel):
    """Parameters for research_ghost_weave tool."""

    seed_url: str
    depth: int = 1
    max_pages: int = 20

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("seed_url", mode="before")
    @classmethod
    def validate_seed_url(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: int) -> int:
        if v < 1 or v > 3:
            raise ValueError("depth must be 1-3")
        return v

    @field_validator("max_pages")
    @classmethod
    def validate_max_pages(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_pages must be 1-100")
        return v


class DeadDropScannerParams(BaseModel):
    """Parameters for research_dead_drop_scanner tool."""

    urls: list[str]
    interval_minutes: int = 5

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("urls list cannot be empty")
        return [validate_url(url) for url in v]

    @field_validator("interval_minutes")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < 1 or v > 1440:
            raise ValueError("interval_minutes must be 1-1440")
        return v


# ─── LLM tool parameters ────────────────────────────────────────────────────────


class LLMSummarizeParams(BaseModel):
    """Parameters for research_llm_summarize tool."""

    text: str
    max_tokens: int = 500
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        if v < 50 or v > 4000:
            raise ValueError("max_tokens must be 50-4000")
        return v


class LLMExtractParams(BaseModel):
    """Parameters for research_llm_extract tool."""

    text: str
    schema: dict[str, Any] | None = None
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}


class LLMClassifyParams(BaseModel):
    """Parameters for research_llm_classify tool."""

    text: str
    categories: list[str]
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, v: list[str]) -> list[str]:
        if not v or len(v) > 20:
            raise ValueError("categories must be 1-20 items")
        return v


class LLMTranslateParams(BaseModel):
    """Parameters for research_llm_translate tool."""

    text: str
    target_language: str
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}


class LLMChatParams(BaseModel):
    """Parameters for research_llm_chat tool."""

    messages: list[dict[str, str]]
    max_tokens: int = 1000
    temperature: float = 0.7
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        if v < 50 or v > 4000:
            raise ValueError("max_tokens must be 50-4000")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if v < 0.0 or v > 2.0:
            raise ValueError("temperature must be 0.0-2.0")
        return v


class LLMQueryExpandParams(BaseModel):
    """Parameters for research_llm_query_expand tool."""

    query: str
    count: int = 3
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("count")
    @classmethod
    def validate_count(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("count must be 1-10")
        return v


class LLMAnswerParams(BaseModel):
    """Parameters for research_llm_answer tool."""

    question: str
    context: str | None = None
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}


class LLMEmbedParams(BaseModel):
    """Parameters for research_llm_embed tool."""

    text: str | list[str]
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}


class SlackNotifyParams(BaseModel):
    """Parameters for research_slack_notify tool."""

    channel: str
    text: str
    thread_ts: str | None = None
    blocks: list[dict[str, Any]] | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, v: str) -> str:
        if not v or not (v.startswith("#") or v.startswith("C")):
            raise ValueError("channel must start with # or C")
        return v

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if len(v) > 4000:
            raise ValueError("text max 4000 chars")
        return v


class GCPImageAnalyzeParams(BaseModel):
    """Parameters for research_image_analyze tool."""

    image_url: str
    features: list[str] | None = None
    max_results: int = Field(default=10, ge=1, le=100)

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        import os
        if not v:
            raise ValueError("image_url is required")
        # Allow http/https URLs or local file paths
        if not (v.startswith("http://") or v.startswith("https://") or os.path.isfile(v)):
            raise ValueError("image_url must be http(s) URL or local file path")
        return v


class GCPTextToSpeechParams(BaseModel):
    """Parameters for research_text_to_speech tool."""

    text: str
    language: str = "en"
    voice: str = "en-US-Neural2-A"
    speaking_rate: float = Field(default=1.0, ge=0.25, le=4.0)

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or len(v) > 5000:
            raise ValueError("text must be 1-5000 chars")
        return v

    @field_validator("voice")
    @classmethod
    def validate_voice(cls, v: str) -> str:
        valid_voices = {
            "en-US-Neural2-A", "en-US-Neural2-C",
            "en-GB-Neural2-A", "en-GB-Neural2-B",
            "es-ES-Neural2-A",
            "fr-FR-Neural2-A",
        }
        if v not in valid_voices:
            raise ValueError(f"voice must be one of: {', '.join(valid_voices)}")
        return v
