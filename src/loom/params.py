"""Pydantic v2 parameter models for all MCP tool arguments.

Each tool has a dedicated model with field validators for URLs, headers,
proxies, etc. All models forbid extra fields and use strict mode.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from loom.config import CONFIG
from loom.validators import filter_headers, validate_js_script, validate_url

# Default Accept-Language header sourced from config
_DEFAULT_ACCEPT_LANG = CONFIG.get("DEFAULT_ACCEPT_LANGUAGE", "en-US,en;q=0.9,ar;q=0.8")


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
    accept_language: str = _DEFAULT_ACCEPT_LANG
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
    accept_language: str = _DEFAULT_ACCEPT_LANG
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
    accept_language: str = _DEFAULT_ACCEPT_LANG
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
        "onionsearch",
        "torcrawl",
        "darkweb_cti",
        "robin_osint",
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
        "onionsearch",
        "torcrawl",
        "darkweb_cti",
        "robin_osint",
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
    accept_language: str = _DEFAULT_ACCEPT_LANG
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


class StylometryParams(BaseModel):
    """Parameters for research_stylometry tool."""

    text: str
    compare_texts: list[str] | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if len(v) < 100:
            raise ValueError("text must be at least 100 characters")
        return v

    @field_validator("compare_texts")
    @classmethod
    def validate_compare_texts(cls, v: list[str] | None) -> list[str] | None:
        if v is not None:
            if len(v) < 1 or len(v) > 10:
                raise ValueError("compare_texts must have 1-10 items")
            for text in v:
                if len(text) < 100:
                    raise ValueError("each comparison text must be at least 100 characters")
        return v


class DeceptionDetectParams(BaseModel):
    """Parameters for research_deception_detect tool."""

    text: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if len(v) < 100:
            raise ValueError("text must be at least 100 characters")
        return v


class SentimentDeepParams(BaseModel):
    """Parameters for research_sentiment_deep tool."""

    text: str
    language: str = "en"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("text must be at least 10 characters")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 5:
            raise ValueError("language must be 2-5 character ISO 639-1 code")
        return v


class NetworkPersonaParams(BaseModel):
    """Parameters for research_network_persona tool."""

    posts: list[dict[str, Any]]
    min_interactions: int = 2

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("posts")
    @classmethod
    def validate_posts(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(v) < 3:
            raise ValueError("posts list must have at least 3 items")
        if len(v) > 10000:
            raise ValueError("posts list limited to 10000 items")
        return v

    @field_validator("min_interactions")
    @classmethod
    def validate_min_interactions(cls, v: int) -> int:
        if v < 0 or v > 100:
            raise ValueError("min_interactions must be 0-100")
        return v

class PersonaProfileParams(BaseModel):
    """Parameters for research_persona_profile tool."""

    texts: list[str]
    metadata: dict[str, Any] | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: list[str]) -> list[str]:
        if not v or not isinstance(v, list):
            raise ValueError("texts must be a non-empty list")
        if len(v) > 100:
            raise ValueError("texts limited to 100 samples")
        for i, text in enumerate(v):
            if not isinstance(text, str):
                raise ValueError(f"texts[{i}] must be a string")
            if len(text.strip()) < 50:
                raise ValueError(f"texts[{i}] must be at least 50 characters")
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("metadata must be a dict or None")
        if "timestamps" in v:
            if not isinstance(v["timestamps"], list):
                raise ValueError("metadata['timestamps'] must be a list")
        return v


class RadicalizationDetectParams(BaseModel):
    """Parameters for research_radicalization_detect tool."""

    text: str
    context: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("text must be a string")
        if len(v.strip()) < 50:
            raise ValueError("text must be at least 50 characters")
        if len(v) > 100000:
            raise ValueError("text limited to 100000 characters")
        return v

    @field_validator("context")
    @classmethod
    def validate_context(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("context must be a string or None")
        if len(v) > 5000:
            raise ValueError("context limited to 5000 characters")
        return v

class WhoisParams(BaseModel):
    """Parameters for research_whois tool."""

    domain: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v or len(v) > 255:
            raise ValueError("domain must be 1-255 characters")
        if not all(c.isalnum() or c in "._-" for c in v):
            raise ValueError("domain contains disallowed characters")
        return v


class DnsLookupParams(BaseModel):
    """Parameters for research_dns_lookup tool."""

    domain: str
    record_types: list[str] | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v or len(v) > 255:
            raise ValueError("domain must be 1-255 characters")
        if not all(c.isalnum() or c in "._-" for c in v):
            raise ValueError("domain contains disallowed characters")
        return v

    @field_validator("record_types")
    @classmethod
    def validate_record_types(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not v or len(v) > 20:
            raise ValueError("record_types must be 1-20 items")
        valid_types = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "PTR", "SOA", "SRV"}
        for rt in v:
            if rt.upper() not in valid_types:
                raise ValueError(f"invalid record type: {rt}")
        return [rt.upper() for rt in v]


class NmapScanParams(BaseModel):
    """Parameters for research_nmap_scan tool."""

    target: str
    ports: str = "80,443,8080,8443"
    scan_type: Literal["basic", "service"] = "basic"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        if not v or len(v) > 255:
            raise ValueError("target must be 1-255 characters")
        if not all(c.isalnum() or c in ".-:" for c in v):
            raise ValueError("target contains disallowed characters")
        return v

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, v: str) -> str:
        if not v or len(v) > 100:
            raise ValueError("ports must be 1-100 characters")
        if not all(c.isdigit() or c in ",-" for c in v):
            raise ValueError("ports must be comma-separated or ranges")
        return v


class PdfExtractParams(BaseModel):
    """Parameters for research_pdf_extract tool."""

    url: str
    pages: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("pages")
    @classmethod
    def validate_pages(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.strip():
            return None
        if len(v) > 20:
            raise ValueError("pages format too long")
        if not all(c.isdigit() or c == "-" for c in v):
            raise ValueError("pages must be 'N' or 'N-M'")
        return v


class PdfSearchParams(BaseModel):
    """Parameters for research_pdf_search tool."""

    url: str
    query: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or len(v) > 1000:
            raise ValueError("query must be 1-1000 characters")
        return v

class RssMonitorFetchParams(BaseModel):
    """Parameters for research_rss_fetch tool."""

    url: str
    max_items: int = 20

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("max_items")
    @classmethod
    def validate_max_items(cls, v: int) -> int:
        if v < 1 or v > 500:
            raise ValueError("max_items must be 1-500")
        return v


class RssMonitorSearchParams(BaseModel):
    """Parameters for research_rss_search tool."""

    urls: list[str]
    query: str
    max_results: int = 20

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        if not v or len(v) > 50:
            raise ValueError("urls must be 1-50 items")
        return [validate_url(url) for url in v]

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v.strip()

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 500:
            raise ValueError("max_results must be 1-500")
        return v


class SocialSearchParams(BaseModel):
    """Parameters for research_social_search tool."""

    username: str
    platforms: list[str] | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or len(v) > 255:
            raise ValueError("username must be 1-255 characters")
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("username must contain only alphanumeric, underscore, or hyphen")
        return v

    @field_validator("platforms")
    @classmethod
    def validate_platforms(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not v or len(v) > 20:
            raise ValueError("platforms must be 1-20 items")
        valid = {
            "github", "twitter", "reddit", "hackernews",
            "linkedin", "medium", "dev.to", "keybase"
        }
        for p in v:
            if p not in valid:
                raise ValueError(f"unknown platform: {p}")
        return v


class SocialProfileParams(BaseModel):
    """Parameters for research_social_profile tool."""

    url: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

class IPReputationParams(BaseModel):
    """Parameters for research_ip_reputation tool."""

    ip: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("ip must be non-empty")
        return v.strip()


class IPGeolocationParams(BaseModel):
    """Parameters for research_ip_geolocation tool."""

    ip: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("ip must be non-empty")
        return v.strip()


class CVELookupParams(BaseModel):
    """Parameters for research_cve_lookup tool."""

    query: str
    limit: int = 10

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        return v.strip()

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("limit must be 1-100")
        return v


class CVEDetailParams(BaseModel):
    """Parameters for research_cve_detail tool."""

    cve_id: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("cve_id")
    @classmethod
    def validate_cve_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("cve_id must be non-empty")
        return v.strip().upper()


class URLHausCheckParams(BaseModel):
    """Parameters for research_urlhaus_check tool."""

    url: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class URLHausSearchParams(BaseModel):
    """Parameters for research_urlhaus_search tool."""

    query: str
    search_type: Literal["tag", "signature", "hash"] = "tag"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        return v.strip()


class CertAnalyzeParams(BaseModel):
    """Parameters for research_cert_analyze tool."""

    hostname: str
    port: int = 443

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("hostname must be non-empty string")
        # Allow alphanumeric, dots, hyphens only
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
        if not all(c in allowed for c in v):
            raise ValueError("hostname must contain only alphanumeric, dots, hyphens")
        if v.startswith("-") or v.endswith("-") or v.startswith(".") or v.endswith("."):
            raise ValueError("hostname cannot start or end with hyphen or dot")
        if len(v) > 255:
            raise ValueError("hostname max 255 characters")
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if v < 1 or v > 65535:
            raise ValueError("port must be 1-65535")
        return v


class SecurityHeadersParams(BaseModel):
    """Parameters for research_security_headers tool."""

    url: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class BreachCheckParams(BaseModel):
    """Parameters for research_breach_check tool."""

    email: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        import re
        if not v or not isinstance(v, str):
            raise ValueError("email must be non-empty string")
        if len(v) > 254:
            raise ValueError("email max 254 characters")
        # Basic email pattern
        pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(pattern, v.strip()):
            raise ValueError("email must be valid format")
        return v.strip()


class PasswordCheckParams(BaseModel):
    """Parameters for research_password_check tool."""

    password: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("password must be non-empty string")
        if len(v) > 256:
            raise ValueError("password max 256 characters")
        return v


class GeoIPLocalParams(BaseModel):
    """Parameters for research_geoip_local tool."""

    ip: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("ip must be non-empty string")
        v = v.strip()
        if len(v) > 45:  # Max IPv6 length
            raise ValueError("ip max 45 characters")
        return v


class ExifExtractParams(BaseModel):
    """Parameters for research_exif_extract tool."""

    url_or_path: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url_or_path")
    @classmethod
    def validate_url_or_path(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("url_or_path must be non-empty string")
        v = v.strip()
        if len(v) > 2048:
            raise ValueError("url_or_path max 2048 characters")
        # Validate if it's a URL
        if v.startswith(("http://", "https://")):
            return validate_url(v)
        return v


class OCRExtractParams(BaseModel):
    """Parameters for research_ocr_extract tool."""

    url_or_path: str
    language: str = "eng"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url_or_path")
    @classmethod
    def validate_url_or_path(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("url_or_path must be non-empty string")
        v = v.strip()
        if len(v) > 2048:
            raise ValueError("url_or_path max 2048 characters")
        # Validate if it's a URL
        if v.startswith(("http://", "https://")):
            return validate_url(v)
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if not v or not isinstance(v, str):
            raise ValueError("language must be non-empty string")
        v = v.strip().lower()
        if len(v) > 10:
            raise ValueError("language max 10 characters")
        return v

class JobSearchParams(BaseModel):
    """Parameters for research_job_search tool."""

    query: str
    location: str | None = None
    remote_only: bool = False
    limit: int = 20

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        v = v.strip()
        if len(v) > 200:
            raise ValueError("query max 200 characters")
        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 100:
            raise ValueError("location max 100 characters")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("limit must be 1-100")
        return v


class JobMarketParams(BaseModel):
    """Parameters for research_job_market tool."""

    role: str
    location: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("role must be non-empty")
        v = v.strip()
        if len(v) > 200:
            raise ValueError("role max 200 characters")
        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 100:
            raise ValueError("location max 100 characters")
        return v

class CompanyDiligenceParams(BaseModel):
    """Parameters for research_company_diligence tool."""

    company_name: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("company_name must be non-empty")
        v = v.strip()
        if len(v) > 200:
            raise ValueError("company_name max 200 characters")
        return v


class SalaryIntelligenceParams(BaseModel):
    """Parameters for research_salary_intelligence tool."""

    role: str
    location: str | None = None
    experience_years: int = 0

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("role must be non-empty")
        v = v.strip()
        if len(v) > 200:
            raise ValueError("role max 200 characters")
        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 100:
            raise ValueError("location max 100 characters")
        return v

    @field_validator("experience_years")
    @classmethod
    def validate_experience_years(cls, v: int) -> int:
        if v < 0 or v > 70:
            raise ValueError("experience_years must be 0-70")
        return v

class OptimizeResumeParams(BaseModel):
    """Parameters for research_optimize_resume tool."""

    resume_text: str
    job_description: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("resume_text")
    @classmethod
    def validate_resume(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("resume_text must be non-empty")
        if len(v.strip()) < 100:
            raise ValueError("resume_text must be at least 100 characters")
        if len(v) > 50000:
            raise ValueError("resume_text max 50000 characters")
        return v

    @field_validator("job_description")
    @classmethod
    def validate_jd(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("job_description must be non-empty")
        if len(v.strip()) < 50:
            raise ValueError("job_description must be at least 50 characters")
        if len(v) > 30000:
            raise ValueError("job_description max 30000 characters")
        return v


class InterviewPrepParams(BaseModel):
    """Parameters for research_interview_prep tool."""

    job_description: str
    company: str | None = None
    interview_type: str = "behavioral"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("job_description")
    @classmethod
    def validate_jd(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("job_description must be non-empty")
        if len(v.strip()) < 100:
            raise ValueError("job_description must be at least 100 characters")
        if len(v) > 30000:
            raise ValueError("job_description max 30000 characters")
        return v

    @field_validator("company")
    @classmethod
    def validate_company(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.strip():
            return None
        v = v.strip()
        if len(v) > 200:
            raise ValueError("company max 200 characters")
        return v

    @field_validator("interview_type")
    @classmethod
    def validate_interview_type(cls, v: str) -> str:
        valid_types = ["behavioral", "technical", "mixed"]
        if v.lower() not in valid_types:
            raise ValueError(f"interview_type must be one of {valid_types}")
        return v.lower()

class CompetitiveIntelParams(BaseModel):
    """Parameters for research_competitive_intel tool."""

    company: str
    domain: str | None = None
    github_org: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("company")
    @classmethod
    def validate_company(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("company must be provided")
        v = v.strip()
        if len(v) > 256:
            raise ValueError("company max 256 characters")
        return v

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 255:
            raise ValueError("domain max 255 characters")
        if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", v.lower()):
            raise ValueError("domain must be a valid domain format")
        return v

    @field_validator("github_org")
    @classmethod
    def validate_github_org(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 100:
            raise ValueError("github_org max 100 characters")
        if not re.match(r"^[a-z0-9-]+$", v.lower()):
            raise ValueError("github_org must be alphanumeric and hyphens only")
        return v

class OnionDiscoverParams(BaseModel):
    """Parameters for research_onion_discover tool."""

    query: str
    max_results: int = 50

    model_config = {"extra": "forbid", "strict": True}

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
