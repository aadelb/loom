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
    retries: int = 0
    timeout: int | None = None
    accept_language: str = _DEFAULT_ACCEPT_LANG
    return_format: Literal["text", "html", "json"] = "text"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("urls list cannot be empty")
        if len(v) > 200:
            raise ValueError("urls list max 200 items")
        return [validate_url(url) for url in v]

    @field_validator("max_chars_each")
    @classmethod
    def validate_max_chars_each(cls, v: int) -> int:
        if v < 500 or v > 50000:
            raise ValueError("max_chars_each must be 500-50000")
        return v

    @field_validator("concurrency")
    @classmethod
    def validate_concurrency(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("concurrency must be 1-50")
        return v

    @field_validator("proxy")
    @classmethod
    def validate_proxy(cls, v: str | None) -> str | None:
        if v is None:
            return v
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

    @field_validator("max_chars")
    @classmethod
    def validate_max_chars(cls, v: int) -> int:
        if v < 1000 or v > 500000:
            raise ValueError("max_chars must be 1000-500000")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 120):
            raise ValueError("timeout must be 1-120 seconds")
        return v

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        return filter_headers(v)

    @field_validator("proxy")
    @classmethod
    def validate_proxy(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith(("http://", "https://", "socks5://", "socks5h://")):
            raise ValueError("proxy must start with http://, https://, socks5://, or socks5h://")
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
        "coinmarketcap",
        "coindesk",
        "binance",
        "ahmia",
        "darksearch",
        "ummro",
        "onionsearch",
        "torcrawl",
        "darkweb_cti",
        "robin_osint",
        "investing",
    ] = "ddgs"
    n: int = 10
    sort_by: str | None = None
    region: str | None = None
    language: str | None = None
    freshness: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        v = v.strip()
        if len(v) > 2000:
            raise ValueError("query max 2000 characters")
        return v

    @field_validator("n")
    @classmethod
    def validate_n(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("n must be 1-100")
        return v


class DeepParams(BaseModel):
    """Parameters for research_deep tool."""

    query: str
    max_results: int = 20
    include_community: bool = True
    include_citations: bool = True
    mode: Literal["fast", "thorough"] = "thorough"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        v = v.strip()
        if len(v) > 2000:
            raise ValueError("query max 2000 characters")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_results must be 1-100")
        return v


class GitHubParams(BaseModel):
    """Parameters for research_github tool."""

    query: str
    language: str | None = None
    sort_by: Literal["stars", "forks", "updated", "best-match"] = "stars"
    per_page: int = 10
    code_search: bool = False

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

    @field_validator("per_page")
    @classmethod
    def validate_per_page(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("per_page must be 1-100")
        return v


class CamoufoxParams(BaseModel):
    """Parameters for research_camoufox tool."""

    url: str
    max_chars: int = 20000
    wait_time: int = 5
    timeout: int = 30
    return_format: Literal["text", "screenshot", "html"] = "text"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("max_chars")
    @classmethod
    def validate_max_chars(cls, v: int) -> int:
        if v < 1000 or v > 100000:
            raise ValueError("max_chars must be 1000-100000")
        return v

    @field_validator("wait_time")
    @classmethod
    def validate_wait_time(cls, v: int) -> int:
        if v < 0 or v > 60:
            raise ValueError("wait_time must be 0-60")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 120:
            raise ValueError("timeout must be 1-120")
        return v


class BotasaurusParams(BaseModel):
    """Parameters for research_botasaurus tool."""

    url: str
    max_chars: int = 20000
    wait_time: int = 5
    timeout: int = 30
    javascript_enabled: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("max_chars")
    @classmethod
    def validate_max_chars(cls, v: int) -> int:
        if v < 1000 or v > 100000:
            raise ValueError("max_chars must be 1000-100000")
        return v


class CacheStatsParams(BaseModel):
    """Parameters for research_cache_stats tool."""

    limit: int = 10
    offset: int = 0

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 1000:
            raise ValueError("limit must be 1-1000")
        return v

    @field_validator("offset")
    @classmethod
    def validate_offset(cls, v: int) -> int:
        if v < 0 or v > 1000000:
            raise ValueError("offset must be 0-1000000")
        return v


class CacheClearParams(BaseModel):
    """Parameters for research_cache_clear tool."""

    days_old: int | None = None
    all: bool = False

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("days_old")
    @classmethod
    def validate_days_old(cls, v: int | None) -> int | None:
        if v is not None and (v < 0 or v > 365):
            raise ValueError("days_old must be 0-365")
        return v


class WhoisParams(BaseModel):
    """Parameters for research_whois tool."""

    domain: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([a-z0-9-]*\.)+[a-z]{2,}$", v):
            raise ValueError("domain format invalid")
        return v


class DNSLookupParams(BaseModel):
    """Parameters for research_dns_lookup tool."""

    domain: str
    record_types: list[str] | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([a-z0-9-]*\.)+[a-z]{2,}$", v):
            raise ValueError("domain format invalid")
        return v

    @field_validator("record_types")
    @classmethod
    def validate_record_types(cls, v: list[str] | None) -> list[str] | None:
        if v:
            valid_types = {"A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "SRV"}
            for rt in v:
                if rt.upper() not in valid_types:
                    raise ValueError(f"invalid record type: {rt}")
            return [rt.upper() for rt in v]
        return v


class NmapScanParams(BaseModel):
    """Parameters for research_nmap_scan tool."""

    target: str
    scan_type: Literal["syn", "connect", "ping", "os"] = "syn"
    ports: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-z0-9\-.:/_]+$", v, re.IGNORECASE):
            raise ValueError("target format invalid")
        return v

    @field_validator("ports")
    @classmethod
    def validate_ports(cls, v: str | None) -> str | None:
        if v:
            v = v.strip()
            if not re.match(r"^[\d,\-\s]+$", v):
                raise ValueError("ports format invalid (use: 80,443 or 1-1000)")
        return v


class CertAnalyzeParams(BaseModel):
    """Parameters for research_cert_analyze tool."""

    domain: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([a-z0-9-]*\.)+[a-z]{2,}$", v):
            raise ValueError("domain format invalid")
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
        v = v.strip().lower()
        if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", v):
            raise ValueError("email format invalid")
        return v


class PasswordCheckParams(BaseModel):
    """Parameters for research_password_check tool."""

    password: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(v) > 500:
            raise ValueError("password must be 1-500 characters")
        return v


class PDFExtractParams(BaseModel):
    """Parameters for research_pdf_extract tool."""

    url: str
    extract_text: bool = True
    extract_images: bool = False
    extract_tables: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        url = validate_url(v)
        if not url.lower().endswith(".pdf"):
            raise ValueError("url must point to a PDF file")
        return url


class PDFSearchParams(BaseModel):
    """Parameters for research_pdf_search tool."""

    url: str
    query: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        url = validate_url(v)
        if not url.lower().endswith(".pdf"):
            raise ValueError("url must point to a PDF file")
        return url

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v


class RSSFetchParams(BaseModel):
    """Parameters for research_rss_fetch tool."""

    feed_url: str
    limit: int = 20
    parse_content: bool = False

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("feed_url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 500:
            raise ValueError("limit must be 1-500")
        return v


class RSSSearchParams(BaseModel):
    """Parameters for research_rss_search tool."""

    query: str
    limit: int = 10

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("limit must be 1-100")
        return v


class SocialSearchParams(BaseModel):
    """Parameters for research_social_search tool."""

    query: str
    platform: Literal["twitter", "instagram", "tiktok", "reddit", "linkedin"] = "twitter"
    limit: int = 20

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("limit must be 1-100")
        return v


class SocialProfileParams(BaseModel):
    """Parameters for research_social_profile tool."""

    username: str
    platform: Literal["twitter", "instagram", "tiktok", "reddit", "linkedin"] | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("username must be non-empty")
        if len(v) > 200:
            raise ValueError("username max 200 characters")
        return v.strip()


class SessionOpenParams(BaseModel):
    """Parameters for research_session_open tool."""

    name: str
    browser_type: Literal["chromium", "firefox", "webkit"] = "chromium"
    headless: bool = True
    timeout: int = 30

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_-]{1,32}$", v):
            raise ValueError("name must match ^[a-z0-9_-]{1,32}$")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 300:
            raise ValueError("timeout must be 1-300")
        return v


class SessionCloseParams(BaseModel):
    """Parameters for research_session_close tool."""

    name: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_-]{1,32}$", v):
            raise ValueError("name must match ^[a-z0-9_-]{1,32}$")
        return v


class ConfigGetParams(BaseModel):
    """Parameters for research_config_get tool."""

    key: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v or len(v) > 200:
                raise ValueError("key must be 1-200 characters")
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
        if not v or len(v) < 2:
            raise ValueError("categories must have at least 2 items")
        if len(v) > 20:
            raise ValueError("categories max 20 items")
        return v


class LLMTranslateParams(BaseModel):
    """Parameters for research_llm_translate tool."""

    text: str
    target_language: str
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("target_language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 100:
            raise ValueError("target_language max 100 characters")
        return v


class LLMQueryExpandParams(BaseModel):
    """Parameters for research_llm_query_expand tool."""

    query: str
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v


class LLMAnswerParams(BaseModel):
    """Parameters for research_llm_answer tool."""

    question: str
    context: str | None = None
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("question must be non-empty")
        if len(v) > 1000:
            raise ValueError("question max 1000 characters")
        return v


class LLMEmbedParams(BaseModel):
    """Parameters for research_llm_embed tool."""

    text: str
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be non-empty")
        if len(v) > 10000:
            raise ValueError("text max 10000 characters")
        return v


class GithubReadmeParams(BaseModel):
    """Parameters for research_github_readme tool."""

    repo_url: str

    model_config = {"extra": "forbid", "strict": True}

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
    limit: int = 10

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("repo_url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        url = validate_url(v)
        if "github.com" not in url.lower():
            raise ValueError("repo_url must be a GitHub URL")
        return url

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("limit must be 1-100")
        return v


class ExaFindSimilarParams(BaseModel):
    """Parameters for find_similar_exa tool."""

    query: str
    num_results: int = 10

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v

    @field_validator("num_results")
    @classmethod
    def validate_num_results(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("num_results must be 1-100")
        return v


class MultiSearchParams(BaseModel):
    """Parameters for research_multi_search tool."""

    query: str
    providers: list[str] | None = None
    limit_per_provider: int = 5

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 2000:
            raise ValueError("query max 2000 characters")
        return v

    @field_validator("limit_per_provider")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError("limit_per_provider must be 1-50")
        return v


class DeadContentParams(BaseModel):
    """Parameters for research_dead_content tool."""

    url: str
    check_archive: bool = True
    timeout: int = 30

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 120:
            raise ValueError("timeout must be 1-120")
        return v


class InvisibleWebParams(BaseModel):
    """Parameters for research_invisible_web tool."""

    query: str
    include_databases: bool = True
    include_academic: bool = True
    include_darkweb: bool = False

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v


class JSIntelParams(BaseModel):
    """Parameters for research_js_intel tool."""

    url: str
    extract_apis: bool = True
    extract_endpoints: bool = True
    extract_secrets: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class DarkForumParams(BaseModel):
    """Parameters for research_dark_forum tool."""

    query: str
    forums: list[str] | None = None
    limit: int = 20

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("limit must be 1-100")
        return v


class InfraCorrelatorParams(BaseModel):
    """Parameters for research_infra_correlator tool."""

    ip: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        v = v.strip()
        if not re.match(
            r"^(\d{1,3}\.){3}\d{1,3}$|^([0-9a-f]{0,4}:){2,7}[0-9a-f]{0,4}$", v, re.IGNORECASE
        ):
            raise ValueError("ip must be valid IPv4 or IPv6")
        return v


class MetadataForensicsParams(BaseModel):
    """Parameters for research_metadata_forensics tool."""

    url: str
    extract_media: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class CryptoTraceParams(BaseModel):
    """Parameters for research_crypto_trace tool."""

    address: str
    blockchain: Literal["bitcoin", "ethereum", "litecoin"] = "ethereum"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[a-zA-Z0-9]{26,66}$", v):
            raise ValueError("address format invalid")
        return v


class StegoDetectParams(BaseModel):
    """Parameters for research_stego_detect tool."""

    url: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class ThreatProfileParams(BaseModel):
    """Parameters for research_threat_profile tool."""

    subject: str
    subject_type: Literal["domain", "ip", "email", "username", "file_hash"] = "domain"
    include_darkweb: bool = False

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("subject must be non-empty")
        if len(v) > 500:
            raise ValueError("subject max 500 characters")
        return v


class LeakScanParams(BaseModel):
    """Parameters for research_leak_scan tool."""

    identifier: str
    scan_type: Literal["email", "username", "phone", "credit_card"] = "email"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("identifier must be non-empty")
        if len(v) > 500:
            raise ValueError("identifier max 500 characters")
        return v


class SocialGraphParams(BaseModel):
    """Parameters for research_social_graph tool."""

    username: str
    platforms: list[str] | None = None
    max_depth: int = 2

    model_config = {"extra": "forbid", "strict": True}

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


class StylometryParams(BaseModel):
    """Parameters for research_stylometry tool."""

    text: str
    compare_with: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be non-empty")
        if len(v) > 50000:
            raise ValueError("text max 50000 characters")
        return v


class DeceptionDetectParams(BaseModel):
    """Parameters for research_deception_detect tool."""

    text: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be non-empty")
        if len(v) > 10000:
            raise ValueError("text max 10000 characters")
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

    job_title: str
    location: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("job_title")
    @classmethod
    def validate_job_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("job_title must be non-empty")
        if len(v) > 200:
            raise ValueError("job_title max 200 characters")
        return v


class CompetitiveIntelParams(BaseModel):
    """Parameters for research_competitive_intel tool."""

    company_name: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("company_name must be non-empty")
        if len(v) > 200:
            raise ValueError("company_name max 200 characters")
        return v


class SupplyChainRiskParams(BaseModel):
    """Parameters for research_supply_chain_risk tool."""

    package_name: str
    ecosystem: Literal["pypi", "npm", "cargo"] = "pypi"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("package_name")
    @classmethod
    def validate_package_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("package_name must be non-empty")
        v = v.strip()
        if len(v) > 200:
            raise ValueError("package_name max 200 characters")
        return v


class PatentLandscapeParams(BaseModel):
    """Parameters for research_patent_landscape tool."""

    query: str
    max_results: int = 20

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


class DependencyAuditParams(BaseModel):
    """Parameters for research_dependency_audit tool."""

    repo_url: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, v: str) -> str:
        v = v.strip()
        if "github.com" not in v.lower():
            raise ValueError("repo_url must be a valid GitHub URL")
        return v


class OnionDiscoverParams(BaseModel):
    """Parameters for research_onion_discover tool."""

    query: str
    include_indexes: bool = True
    limit: int = 20

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("limit must be 1-100")
        return v


class WaybackParams(BaseModel):
    """Parameters for research_wayback tool."""

    url: str
    year: int | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int | None) -> int | None:
        if v is not None and (v < 1996 or v > 2100):
            raise ValueError("year must be 1996-2100")
        return v


class FindExpertsParams(BaseModel):
    """Parameters for research_find_experts tool."""

    topic: str
    max_results: int = 10

    model_config = {"extra": "forbid", "strict": True}

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


class RedTeamParams(BaseModel):
    """Parameters for research_red_team tool."""

    system_prompt: str
    attack_vectors: list[str] | None = None
    iterations: int = 3

    model_config = {"extra": "forbid", "strict": True}

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


class MultilingualParams(BaseModel):
    """Parameters for research_multilingual tool."""

    query: str
    target_languages: list[str] | None = None
    limit_per_language: int = 5

    model_config = {"extra": "forbid", "strict": True}

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


class ConsensusParams(BaseModel):
    """Parameters for research_consensus tool."""

    query: str
    num_sources: int = 5

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return v

    @field_validator("num_sources")
    @classmethod
    def validate_num_sources(cls, v: int) -> int:
        if v < 2 or v > 20:
            raise ValueError("num_sources must be 2-20")
        return v


class MisinfoCheckParams(BaseModel):
    """Parameters for research_misinfo_check tool."""

    claim: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("claim")
    @classmethod
    def validate_claim(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("claim must be non-empty")
        if len(v) > 1000:
            raise ValueError("claim max 1000 characters")
        return v


class TemporalDiffParams(BaseModel):
    """Parameters for research_temporal_diff tool."""

    query: str
    days_between: int = 30

    model_config = {"extra": "forbid", "strict": True}

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


class CitationGraphParams(BaseModel):
    """Parameters for research_citation_graph tool."""

    query: str
    depth: int = 2

    model_config = {"extra": "forbid", "strict": True}

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



class CitationAnalysisParams(BaseModel):
    """Parameters for research_citation_analysis tool."""

    paper_id: str
    depth: int = 2

    model_config = {"extra": "forbid", "strict": True}

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

class RetractionCheckParams(BaseModel):
    """Parameters for research_retraction_check tool."""

    query: str
    max_results: int = 20

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


class PredatoryJournalCheckParams(BaseModel):
    """Parameters for research_predatory_journal_check tool."""

    journal_name: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("journal_name")
    @classmethod
    def validate_journal_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 500:
            raise ValueError("journal_name must be 1-500 characters")
        return v


class GhostProtocolParams(BaseModel):
    """Parameters for research_ghost_protocol tool."""

    keywords: list[str]
    time_window_minutes: int = 30

    model_config = {"extra": "forbid", "strict": True}

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


class TemporalAnomalyParams(BaseModel):
    """Parameters for research_temporal_anomaly tool."""

    domain: str
    check_type: Literal["all", "certs", "dns", "clock"] = "all"

    model_config = {"extra": "forbid", "strict": True}

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


class SecTrackerParams(BaseModel):
    """Parameters for research_sec_tracker tool."""

    company: str
    filing_types: list[str] | None = None

    model_config = {"extra": "forbid", "strict": True}

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


class RegistryGraveyardParams(BaseModel):
    """Parameters for research_registry_graveyard tool."""

    package_name: str
    ecosystem: Literal["pypi", "npm", "rubygems"] = "pypi"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("package_name")
    @classmethod
    def validate_package_name(cls, v: str) -> str:
        if not v or len(v) > 255:
            raise ValueError("package_name must be 1-255 characters")
        # Allow alphanumeric, hyphens, underscores, dots
        if not re.match(r"^[a-zA-Z0-9_.-]+$", v):
            raise ValueError("package_name contains disallowed characters")
        return v


class SubdomainTemporalParams(BaseModel):
    """Parameters for research_subdomain_temporal tool."""

    domain: str
    days_back: int = 90

    model_config = {"extra": "forbid", "strict": True}

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


class CommitAnalyzerParams(BaseModel):
    """Parameters for research_commit_analyzer tool."""

    repo: str
    days_back: int = 30

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        if not v or len(v) > 100:
            raise ValueError("repo must be 1-100 characters")
        if "/" not in v:
            raise ValueError("repo must be in 'owner/name' format")
        if not re.match(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$", v):
            raise ValueError("repo contains disallowed characters")
        return v

    @field_validator("days_back")
    @classmethod
    def validate_days_back(cls, v: int) -> int:
        if v < 1 or v > 365:
            raise ValueError("days_back must be 1-365")
        return v

class LegalTakedownParams(BaseModel):
    """Parameters for research_legal_takedown tool."""

    domain: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([a-z0-9-]*\.)+[a-z]{2,}$", v):
            raise ValueError("domain format invalid")
        return v


class OpenAccessParams(BaseModel):
    """Parameters for research_open_access tool."""

    doi: str = ""
    title: str = ""

    model_config = {"extra": "forbid", "strict": True}

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


class ContentAuthenticityParams(BaseModel):
    """Parameters for research_content_authenticity tool."""

    url: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class CredentialMonitorParams(BaseModel):
    """Parameters for research_credential_monitor tool."""

    target: str
    target_type: Literal["email", "username"] = "email"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or len(v) > 255:
            raise ValueError("target must be 1-255 characters")
        return v


class DeepfakeCheckerParams(BaseModel):
    """Parameters for research_deepfake_checker tool."""

    image_url: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        url = validate_url(v)
        # Allow common image extensions
        allowed_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff")
        if not url.lower().endswith(allowed_exts):
            raise ValueError("image_url must point to an image file")
        return url


class PropagandaDetectorParams(BaseModel):
    """Parameters for research_propaganda_detector tool."""

    text: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or len(v) > 100000:
            raise ValueError("text must be 1-100000 characters")
        return v


class SourceCredibilityParams(BaseModel):
    """Parameters for research_source_credibility tool."""

    url: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class InformationCascadeParams(BaseModel):
    """Parameters for research_information_cascade tool."""

    topic: str
    hours_back: int = 72

    model_config = {"extra": "forbid", "strict": True}

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


class WebTimeMachineParams(BaseModel):
    """Parameters for research_web_time_machine tool."""

    url: str
    snapshots: int = 10

    model_config = {"extra": "forbid", "strict": True}

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


class InfluenceOperationParams(BaseModel):
    """Parameters for research_influence_operation tool."""

    topic: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        if not v or len(v) > 200:
            raise ValueError("topic must be 1-200 characters")
        return v


class DarkWebBridgeParams(BaseModel):
    """Parameters for research_dark_web_bridge tool."""

    query: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or len(v) > 200:
            raise ValueError("query must be 1-200 characters")
        return v


class InfoHalfLifeParams(BaseModel):
    """Parameters for research_info_half_life tool."""

    urls: list[str]

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        if not v or len(v) > 100:
            raise ValueError("urls must have 1-100 items")
        validated = []
        for url in v:
            validated.append(validate_url(url))
        return validated


class SearchDiscrepancyParams(BaseModel):
    """Parameters for research_search_discrepancy tool."""

    query: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or len(v) > 200:
            raise ValueError("query must be 1-200 characters")
        return v

class ModelComparatorParams(BaseModel):
    """Parameters for research_model_comparator tool."""

    prompt: str
    endpoints: list[str]

    model_config = {"extra": "forbid", "strict": True}

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


class DataPoisoningParams(BaseModel):
    """Parameters for research_data_poisoning tool."""

    target_url: str
    canary_phrases: list[str] | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("target_url", mode="before")
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


class WikiEventCorrelatorParams(BaseModel):
    """Parameters for research_wiki_event_correlator tool."""

    page_title: str
    days_back: int = 30

    model_config = {"extra": "forbid", "strict": True}

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


class FOIATrackerParams(BaseModel):
    """Parameters for research_foia_tracker tool."""

    query: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        if len(v) > 100:
            raise ValueError("query max 100 characters")
        return v
