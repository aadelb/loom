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
    include_domains: list[str] | None = None
    exclude_domains: list[str] | None = None
    start_date: str | None = None
    end_date: str | None = None
    provider_config: dict[str, Any] | None = None
    language: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        return v.strip()

    @field_validator("n")
    @classmethod
    def validate_n(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("n must be 1-50")
        return v


class DeepParams(BaseModel):
    """Parameters for research_deep tool."""

    query: str
    depth: int = 2
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
    search_providers: list[str] | None = None
    expand_queries: bool = True
    extract: bool = True
    synthesize: bool = True
    include_github: bool = True
    include_community: bool = False
    include_red_team: bool = False
    include_misinfo_check: bool = False
    max_cost_usd: float = 0.50

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("depth")
    @classmethod
    def validate_depth(cls, v: int) -> int:
        if v < 1 or v > 10:
            raise ValueError("depth must be 1-10")
        return v

    @field_validator("max_cost_usd")
    @classmethod
    def validate_max_cost(cls, v: float) -> float:
        if v < 0.0 or v > 10.0:
            raise ValueError("max_cost_usd must be 0.0-10.0")
        return v


class GitHubSearchParams(BaseModel):
    """Parameters for research_github tool."""

    kind: Literal["repos", "code", "issues"]
    query: str
    limit: int = 20
    sort: Literal["best-match", "stars", "forks", "updated"] = "best-match"
    order: Literal["desc", "asc"] = "desc"
    language: str | None = None
    owner: str | None = None
    repo: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 512:
            raise ValueError("query max 512 chars")
        if v.lstrip().startswith("-"):
            raise ValueError("query cannot start with '-'")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("limit must be 1-100")
        return v


class CamoufoxParams(BaseModel):
    """Parameters for research_camoufox tool."""

    url: str
    max_chars: int = 20000
    session: str | None = None
    wait_for: str | None = None
    screenshot: bool = False
    extract_selector: str | None = None
    js_before_scrape: str | None = None
    timeout: int | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("js_before_scrape")
    @classmethod
    def validate_js(cls, v: str | None) -> str | None:
        if v is not None:
            if len(v) > 2048:
                raise ValueError("js_before_scrape max 2 KB")
            validate_js_script(v)
        return v


class BotasaurusParams(BaseModel):
    """Parameters for research_botasaurus tool."""

    url: str
    max_chars: int = 20000
    session: str | None = None
    wait_for: str | None = None
    screenshot: bool = False
    extract_selector: str | None = None
    js_before_scrape: str | None = None
    timeout: int | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("js_before_scrape")
    @classmethod
    def validate_js(cls, v: str | None) -> str | None:
        if v is not None:
            if len(v) > 2048:
                raise ValueError("js_before_scrape max 2 KB")
            validate_js_script(v)
        return v


class SessionOpenParams(BaseModel):
    """Parameters for research_session_open tool."""

    name: str
    browser: Literal["camoufox", "playwright", "patchright"] = "camoufox"
    headless: bool = True
    accept_language: str = "en-US,en;q=0.9,ar;q=0.8"
    login_url: str | None = None
    login_script: str | None = None
    initial_cookies: dict[str, str] | None = None
    ttl_seconds: int = 3600

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        import re

        if not re.match(r"^[a-z0-9_-]{1,32}$", v):
            raise ValueError("session name must match ^[a-z0-9_-]{1,32}$")
        return v

    @field_validator("login_url", mode="before")
    @classmethod
    def validate_login_url(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_url(v)
        return v

    @field_validator("login_script")
    @classmethod
    def validate_login_script(cls, v: str | None) -> str | None:
        if v is not None:
            if len(v) > 2048:
                raise ValueError("login_script max 2 KB")
            validate_js_script(v)
        return v

    @field_validator("ttl_seconds")
    @classmethod
    def validate_ttl(cls, v: int) -> int:
        if v < 60 or v > 86400:
            raise ValueError("ttl_seconds must be 60-86400")
        return v


class ConfigSetParams(BaseModel):
    """Parameters for research_config_set tool."""

    key: str
    value: Any

    model_config = {"extra": "forbid", "strict": True}


class LLMChatParams(BaseModel):
    """Parameters for research_llm_chat tool."""

    messages: list[dict[str, str]]
    provider: str = "openai"
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if v < 0.0 or v > 2.0:
            raise ValueError("temperature must be 0.0-2.0")
        return v


class LLMSummarizeParams(BaseModel):
    """Parameters for research_llm_summarize tool."""

    text: str
    max_length: int = 500
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("max_length")
    @classmethod
    def validate_max_length(cls, v: int) -> int:
        if v < 50 or v > 5000:
            raise ValueError("max_length must be 50-5000")
        return v


class LLMExtractParams(BaseModel):
    """Parameters for research_llm_extract tool."""

    text: str
    schema_def: dict[str, Any] = Field(alias="schema")
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True, "populate_by_name": True}


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
    source_lang: str
    target_lang: str
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}


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
