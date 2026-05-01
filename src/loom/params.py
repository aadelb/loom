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
    max_results: int = Field(default=10, alias="n")
    sort_by: str | None = None
    region: str | None = None
    language: str | None = None
    freshness: str | None = None

    model_config = {"extra": "forbid", "strict": True, "populate_by_name": True}

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
    def validate_n(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_results must be 1-100")
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
    browser: Literal["camoufox", "chromium", "firefox"] | str = "camoufox"
    ttl_seconds: int = 3600
    login_url: str | None = None
    login_script: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_-]{1,32}$", v):
            raise ValueError("name must match ^[a-z0-9_-]{1,32}$")
        return v

    @field_validator("ttl_seconds")
    @classmethod
    def validate_ttl_seconds(cls, v: int) -> int:
        if v < 1 or v > 86400:
            raise ValueError("ttl_seconds must be 1-86400")
        return v

    @field_validator("login_script")
    @classmethod
    def validate_login_script(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_js_script(v)
        return v

    @field_validator("login_url")
    @classmethod
    def validate_login_url(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_url(v)
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
    max_results: int = Field(default=10, alias="num_results")

    model_config = {"extra": "forbid", "strict": True, "populate_by_name": True}

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

    domain: str
    check_robots: bool = True
    check_sitemap: bool = True
    check_hidden_paths: bool = True
    check_js_endpoints: bool = True
    max_paths: int = 50

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[a-z0-9]([a-z0-9-]*\.)+[a-z]{2,}$", v):
            raise ValueError("domain format invalid")
        return v

    @field_validator("max_paths")
    @classmethod
    def validate_max_paths(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_paths must be 1-100")
        return v


class JSIntelParams(BaseModel):
    """Parameters for research_js_intel tool."""

    url: str
    max_js_files: int = 20
    check_source_maps: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("max_js_files")
    @classmethod
    def validate_max_js_files(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_js_files must be 1-100")
        return v


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


class DeadContentParams(BaseModel):
    """Parameters for research_dead_content tool."""

    url: str
    include_snapshots: bool = True
    max_sources: int = 12

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("max_sources")
    @classmethod
    def validate_max_sources(cls, v: int) -> int:
        if v < 1 or v > 12:
            raise ValueError("max_sources must be 1-12")
        return v


# ============================================================
# Prompt Reframing Tool Parameters
# ============================================================


class PromptReframeParams(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    prompt: str
    strategy: str = "auto"
    model: str = "auto"
    framework: str = "ieee"


class AutoReframeParams(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    prompt: str
    target_url: str = ""
    model: str = "auto"
    max_attempts: int = Field(default=5, ge=1, le=20)


class RefusalDetectorParams(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    text: str


class StackReframeParams(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    prompt: str
    strategies: str = "deep_inception,recursive_authority"
    model: str = "auto"


class CrescendoChainParams(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    prompt: str
    turns: int = Field(default=5, ge=3, le=7)
    model: str = "auto"


class ModelVulnerabilityProfileParams(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    model: str = "auto"


class FormatSmuggleParams(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    prompt: str
    format_type: str = "auto"
    model: str = "auto"


class FingerprintModelParams(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    response_text: str


class AdaptiveReframeParams(BaseModel):
    model_config = {"extra": "forbid", "strict": True}
    prompt: str
    refusal_text: str = ""
    model: str = "auto"


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

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}

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

class StripeCreateSubscriptionParams(BaseModel):
    """Parameters for research_stripe_billing create_subscription."""

    customer_id: str = Field(
        ...,
        description="Loom customer ID",
        min_length=1,
        max_length=64,
    )
    tier: Literal["pro", "team", "enterprise"] = Field(
        ...,
        description="Subscription tier (not 'free')",
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Customer ID must be non-empty alphanumeric."""
        if not v.strip():
            raise ValueError("customer_id cannot be empty")
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("customer_id must be alphanumeric, hyphen, or underscore")
        return v.strip()


class StripeCreateChargeParams(BaseModel):
    """Parameters for research_stripe_billing create_charge."""

    customer_id: str = Field(
        ...,
        description="Loom customer ID",
        min_length=1,
        max_length=64,
    )
    amount_cents: int = Field(
        ...,
        description="Charge amount in cents (e.g., 9999 = $99.99)",
        gt=0,
        le=999999,
    )
    description: str = Field(
        ...,
        description="Charge description",
        min_length=1,
        max_length=256,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Customer ID must be non-empty alphanumeric."""
        if not v.strip():
            raise ValueError("customer_id cannot be empty")
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("customer_id must be alphanumeric, hyphen, or underscore")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Description must be non-empty."""
        if not v.strip():
            raise ValueError("description cannot be empty")
        return v.strip()


class StripeGetInvoiceParams(BaseModel):
    """Parameters for research_stripe_billing get_invoice."""

    invoice_id: str = Field(
        ...,
        description="Stripe invoice ID",
        min_length=1,
        max_length=64,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("invoice_id")
    @classmethod
    def validate_invoice_id(cls, v: str) -> str:
        """Invoice ID must be non-empty."""
        if not v.strip():
            raise ValueError("invoice_id cannot be empty")
        return v.strip()


class StripeCancelSubscriptionParams(BaseModel):
    """Parameters for research_stripe_billing cancel_subscription."""

    subscription_id: str = Field(
        ...,
        description="Stripe subscription ID",
        min_length=1,
        max_length=64,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("subscription_id")
    @classmethod
    def validate_subscription_id(cls, v: str) -> str:
        """Subscription ID must be non-empty."""
        if not v.strip():
            raise ValueError("subscription_id cannot be empty")
        return v.strip()


class StripeListInvoicesParams(BaseModel):
    """Parameters for research_stripe_billing list_invoices."""

    customer_id: str = Field(
        ...,
        description="Loom customer ID",
        min_length=1,
        max_length=64,
    )
    limit: int = Field(
        10,
        description="Maximum invoices to return (1-100)",
        ge=1,
        le=100,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Customer ID must be non-empty alphanumeric."""
        if not v.strip():
            raise ValueError("customer_id cannot be empty")
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("customer_id must be alphanumeric, hyphen, or underscore")
        return v.strip()


class StripeCreateCheckoutParams(BaseModel):
    """Parameters for research_stripe_billing create_checkout_session."""

    customer_id: str = Field(
        ...,
        description="Loom customer ID",
        min_length=1,
        max_length=64,
    )
    tier: Literal["pro", "team", "enterprise"] = Field(
        ...,
        description="Subscription tier (not 'free')",
    )
    success_url: str = Field(
        ...,
        description="URL to redirect on successful payment",
        min_length=10,
        max_length=2048,
    )
    cancel_url: str = Field(
        ...,
        description="URL to redirect if payment cancelled",
        min_length=10,
        max_length=2048,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, v: str) -> str:
        """Customer ID must be non-empty alphanumeric."""
        if not v.strip():
            raise ValueError("customer_id cannot be empty")
        if not all(c.isalnum() or c in "-_" for c in v):
            raise ValueError("customer_id must be alphanumeric, hyphen, or underscore")
        return v.strip()

    @field_validator("success_url")
    @classmethod
    def validate_success_url(cls, v: str) -> str:
        """Success URL must be valid HTTP(S) URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("success_url must start with http:// or https://")
        return v

    @field_validator("cancel_url")
    @classmethod
    def validate_cancel_url(cls, v: str) -> str:
        """Cancel URL must be valid HTTP(S) URL."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("cancel_url must start with http:// or https://")
        return v


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

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("tools_to_test")
    @classmethod
    def validate_tools_to_test(cls, v: list[str] | None) -> list[str] | None:
        if v is not None and len(v) > 227:
            raise ValueError("tools_to_test cannot exceed 227 tools")
        return v

# Missing params for test files

class AdversarialDebateParams(BaseModel):
    """Parameters for research_adversarial_debate tool."""

    topic: str = Field(
        description="Topic to debate (min 10 chars, max 500)",
        min_length=10,
        max_length=500,
    )
    pro_model: str = Field(
        default="groq",
        description="LLM provider for pro-disclosure side",
        max_length=64,
    )
    con_model: str = Field(
        default="nvidia",
        description="LLM provider for safety-cautious side",
        max_length=64,
    )
    max_rounds: int = Field(
        default=5,
        description="Max debate rounds (1-10)",
        ge=1,
        le=10,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("topic cannot be empty")
        return v.strip()


class BPJParams(BaseModel):
    """Parameters for research_bpj_generate tool."""

    safe_prompt: str = Field(
        description="Prompt that model complies with",
        max_length=10000,
    )
    unsafe_prompt: str = Field(
        description="Prompt that model refuses",
        max_length=10000,
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

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("find_boundary", "map_region", "both"):
            raise ValueError("mode must be find_boundary, map_region, or both")
        return v


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

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}


class ConsistencyPressureHistoryParams(BaseModel):
    """Parameters for research_consistency_pressure_history tool."""

    model: str = Field(
        description="Model identifier",
        max_length=256,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("model cannot be empty")
        return v.strip()


class ContextPoisonParams(BaseModel):
    """Parameters for research_context_poison tool."""

    target_query: str = Field(
        description="Query to poison",
        max_length=10000,
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

    model_config = {"extra": "forbid", "strict": True}


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

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()


class ExecutabilityParams(BaseModel):
    """Parameters for research_executability_score tool."""

    response_text: str = Field(
        description="Response text to score",
        max_length=100000,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("response_text")
    @classmethod
    def validate_response_text(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("response_text must be string")
        return v


class ModelEvidenceParams(BaseModel):
    """Parameters for research_model_evidence tool."""

    query: str = Field(
        description="Query to search for evidence",
        max_length=10000,
    )
    source_model_names: list[str] | None = Field(
        default=None,
        description="Source models to use for evidence generation",
    )
    target_model_name: str = Field(
        default="gpt-4",
        description="Target model name",
        max_length=256,
    )
    max_evidence_sources: int = Field(
        default=3,
        description="Max evidence sources (1-10)",
        ge=1,
        le=10,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
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

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()


class CVELookupParams(BaseModel):
    """Parameters for research_cve_lookup tool."""

    query: str = Field(
        description="Keyword or phrase to search CVE database",
        max_length=256,
    )
    limit: int = Field(
        default=10,
        description="Max number of results (1-100)",
        ge=1,
        le=100,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()


class CVEDetailParams(BaseModel):
    """Parameters for research_cve_detail tool."""

    cve_id: str = Field(
        description="CVE ID in format CVE-YYYY-NNNNN+",
        pattern=r"^CVE-\d{4}-\d{5,}$",
    )

    model_config = {"extra": "forbid", "strict": True}


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

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("command cannot be empty")
        return v.strip()


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

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()


class EmailReportParams(BaseModel):
    """Parameters for research_email_report tool."""

    subject: str = Field(
        description="Email subject",
        max_length=256,
    )
    body: str = Field(
        description="Email body",
        max_length=100000,
    )
    recipient: str = Field(
        description="Recipient email address",
        max_length=256,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("subject cannot be empty")
        return v.strip()

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("body cannot be empty")
        return v.strip()

    @field_validator("recipient")
    @classmethod
    def validate_recipient(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("recipient cannot be empty")
        if "@" not in v:
            raise ValueError("recipient must be valid email")
        return v.strip()


class GitHubSearchParams(BaseModel):
    """Parameters for research_github_search tool."""

    query: str = Field(
        description="GitHub search query",
        max_length=256,
    )
    limit: int = Field(
        default=10,
        description="Max results (1-100)",
        ge=1,
        le=100,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()


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

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text cannot be empty")
        return v.strip()


class URLhausSearchParams(BaseModel):
    """Parameters for research_urlhaus_search tool."""

    query: str = Field(
        description="Search query",
        max_length=256,
    )
    limit: int = Field(
        default=10,
        description="Max results (1-100)",
        ge=1,
        le=100,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()


class NodriverFetchParams(BaseModel):
    """Parameters for research_nodriver_fetch tool."""

    url: str
    wait_for: str | None = None
    timeout: int = 30
    screenshot: bool = False
    bypass_cache: bool = False
    max_chars: int = 20000

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 120:
            raise ValueError("timeout must be 1-120 seconds")
        return v

    @field_validator("max_chars")
    @classmethod
    def validate_max_chars(cls, v: int) -> int:
        if v < 1 or v > 50000:
            raise ValueError("max_chars must be 1-50000")
        return v

    @field_validator("wait_for")
    @classmethod
    def validate_wait_for(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 256:
            raise ValueError("wait_for selector max 256 chars")
        return v


class NodriverExtractParams(BaseModel):
    """Parameters for research_nodriver_extract tool."""

    url: str
    css_selector: str | None = None
    xpath: str | None = None
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
            raise ValueError("timeout must be 1-120 seconds")
        return v

    @field_validator("css_selector")
    @classmethod
    def validate_css_selector(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 512:
            raise ValueError("css_selector max 512 chars")
        return v

    @field_validator("xpath")
    @classmethod
    def validate_xpath(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 512:
            raise ValueError("xpath max 512 chars")
        return v


class NodriverSessionParams(BaseModel):
    """Parameters for research_nodriver_session tool."""

    action: Literal["open", "navigate", "extract", "close"]
    session_name: str = "default"
    url: str | None = None
    css_selector: str | None = None
    xpath: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_url(v)
        return v

    @field_validator("session_name")
    @classmethod
    def validate_session_name(cls, v: str) -> str:
        if not (1 <= len(v) <= 32):
            raise ValueError("session_name must be 1-32 characters")
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("session_name must be alphanumeric, underscore, or hyphen")
        return v

    @field_validator("css_selector")
    @classmethod
    def validate_css_selector(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 512:
            raise ValueError("css_selector max 512 chars")
        return v

    @field_validator("xpath")
    @classmethod
    def validate_xpath(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 512:
            raise ValueError("xpath max 512 chars")
        return v


class ScraperEngineFetchParams(BaseModel):
    """Parameters for research_engine_fetch tool."""

    url: str
    mode: Literal["auto", "stealth", "max", "fast"] = "auto"
    max_escalation: int | None = None
    extract_title: bool = False
    force_backend: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("max_escalation")
    @classmethod
    def validate_max_escalation(cls, v: int | None) -> int | None:
        if v is not None and (v < 0 or v > 7):
            raise ValueError("max_escalation must be 0-7")
        return v

    @field_validator("force_backend")
    @classmethod
    def validate_force_backend(cls, v: str | None) -> str | None:
        if v is not None:
            valid_backends = {
                "httpx",
                "scrapling",
                "crawl4ai",
                "patchright",
                "nodriver",
                "zendriver",
                "camoufox",
                "botasaurus",
            }
            if v not in valid_backends:
                raise ValueError(f"force_backend must be one of {valid_backends}")
        return v


class ScraperEngineExtractParams(BaseModel):
    """Parameters for research_engine_extract tool."""

    url: str
    query: str
    model: Literal["auto", "groq", "openai", "gemini"] = "auto"
    mode: Literal["auto", "stealth", "max", "fast"] = "auto"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        if len(v) > 500:
            raise ValueError("query max 500 chars")
        return v.strip()


class ScraperEngineBatchParams(BaseModel):
    """Parameters for research_engine_batch tool."""

    urls: list[str]
    mode: Literal["auto", "stealth", "max", "fast"] = "auto"
    max_concurrent: int = 10
    fail_fast: bool = False

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class StructuredCrawlParams(BaseModel):
    """Parameters for research_structured_crawl tool."""

    url: str
    schema_map: dict[str, str] = Field(
        description="Dict mapping field names to CSS selectors",
        min_length=1,
        alias="schema",
    )
    max_pages: int = Field(
        default=5,
        description="Maximum pages to crawl (1-50)",
        ge=1,
        le=50,
    )
    use_js: bool = Field(
        default=False,
        description="Use Playwright (JS-enabled) instead of BeautifulSoup",
    )

    model_config = {"extra": "forbid", "strict": True, "populate_by_name": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("schema_map")
    @classmethod
    def validate_schema_map(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("schema cannot be empty")
        for field_name, selector in v.items():
            if not isinstance(field_name, str) or not isinstance(selector, str):
                raise ValueError("schema keys and values must be strings")
            if len(selector) > 256:
                raise ValueError(f"CSS selector for {field_name} exceeds 256 chars")
        return v


class ZenFetchParams(BaseModel):
    """Parameters for research_zen_fetch tool."""

    url: str
    timeout: int = 30
    headless: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 1 or v > 120:
            raise ValueError("timeout must be 1-120 seconds")
        return v


class ZenBatchParams(BaseModel):
    """Parameters for research_zen_batch tool."""

    urls: list[str]
    max_concurrent: int = 5
    timeout: int = 30

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}

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

class GraphScraperParams(BaseModel):
    """Parameters for research_graph_scrape tool."""

    url: str
    query: str
    model: Literal["auto", "groq", "nvidia", "deepseek", "openai", "anthropic"] = "auto"

    model_config = {"extra": "forbid", "strict": True}

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


class KnowledgeExtractParams(BaseModel):
    """Parameters for research_knowledge_extract tool."""

    text: str
    entity_types: list[str] | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text cannot be empty")
        if len(v) > 100000:
            raise ValueError("text max 100000 chars")
        return v

    @field_validator("entity_types")
    @classmethod
    def validate_entity_types(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if not isinstance(v, list):
            raise ValueError("entity_types must be a list")
        if len(v) > 20:
            raise ValueError("entity_types max 20 items")
        for et in v:
            if not isinstance(et, str) or len(et) > 50:
                raise ValueError("each entity_type must be a string <= 50 chars")
        return v


class MultiPageGraphParams(BaseModel):
    """Parameters for research_multi_page_graph tool."""

    urls: list[str]
    query: str

    model_config = {"extra": "forbid", "strict": True}

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


class SherlockLookupParams(BaseModel):
    """Parameters for research_sherlock_lookup tool."""

    username: str
    platforms: list[str] | None = None
    timeout: int = 30

    model_config = {"extra": "forbid", "strict": True}

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


class SherlockBatchParams(BaseModel):
    """Parameters for research_sherlock_batch tool."""

    usernames: list[str]
    platforms: list[str] | None = None
    timeout: int = 30

    model_config = {"extra": "forbid", "strict": True}

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


class SubfinderParams(BaseModel):
    """Parameters for research_subfinder tool."""

    domain: str
    timeout: int = 60

    model_config = {"extra": "forbid", "strict": True}

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


class KatanaCrawlParams(BaseModel):
    """Parameters for research_katana_crawl tool."""

    url: str
    depth: int = 3
    max_pages: int = 100
    timeout: int = 60

    model_config = {"extra": "forbid", "strict": True}

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


class HttpxProbeParams(BaseModel):
    """Parameters for research_httpx_probe tool."""

    targets: list[str]
    ports: str = "80,443,8080,8443"
    timeout: int = 60

    model_config = {"extra": "forbid", "strict": True}

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


class NucleiScanParams(BaseModel):
    """Parameters for research_nuclei_scan tool."""

    target: str
    templates: str = "cves,exposures"
    severity: str = "medium,high,critical"
    timeout: int = 120

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("target", mode="before")
    @classmethod
    def validate_target(cls, v: str) -> str:
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


class TorbotParams(BaseModel):
    """Parameters for research_torbot tool."""

    url: str
    depth: int = 2

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


class AmassEnumParams(BaseModel):
    """Parameters for research_amass_enum tool."""

    domain: str
    passive: bool = True
    timeout: int = 120

    model_config = {"extra": "forbid", "strict": True}

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

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v or len(v) > 255:
            raise ValueError("domain must be 1-255 characters")
        if not re.match(r"^[a-z0-9._-]+$", v, re.IGNORECASE):
            raise ValueError("domain contains disallowed characters")
        return v


class InstagramParams(BaseModel):
    """Parameters for research_instagram tool."""

    username: str
    max_posts: int = 10

    model_config = {"extra": "forbid", "strict": True}

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


class ArticleExtractParams(BaseModel):
    """Parameters for research_article_extract tool."""

    url: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class ArticleBatchParams(BaseModel):
    """Parameters for research_article_batch tool."""

    urls: list[str]
    max_concurrent: int = 5

    model_config = {"extra": "forbid", "strict": True}

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


class OCRAdvancedParams(BaseModel):
    """Parameters for research_ocr_advanced tool."""

    image_path_or_url: str
    languages: list[str] | None = Field(None, min_items=1, max_items=10)
    detail: bool = True

    model_config = {"extra": "forbid", "strict": True}

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


class PDFAdvancedParams(BaseModel):
    """Parameters for research_pdf_advanced tool."""

    pdf_path_or_url: str
    extract_images: bool = False
    extract_tables: bool = True

    model_config = {"extra": "forbid", "strict": True}

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


class DocumentAnalyzeParams(BaseModel):
    """Parameters for research_document_analyze tool."""

    file_path_or_url: str
    analysis: Literal["full", "text", "fast"] = "full"

    model_config = {"extra": "forbid", "strict": True}

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


class ShodanHostParams(BaseModel):
    """Parameters for research_shodan_host tool."""

    ip: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        v = v.strip()
        # Basic IPv4 validation
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", v):
            raise ValueError("ip must be valid IPv4 address")
        # Validate each octet is 0-255
        octets = v.split(".")
        for octet in octets:
            num = int(octet)
            if num < 0 or num > 255:
                raise ValueError("ip octets must be 0-255")
        return v


class ShodanSearchParams(BaseModel):
    """Parameters for research_shodan_search tool."""

    query: str
    max_results: int = 10

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("query cannot be empty")
        if len(v) > 500:
            raise ValueError("query too long (max 500 chars)")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 5000:
            raise ValueError("max_results must be 1-5000")
        return v

class CensysHostParams(BaseModel):
    """Parameters for research_censys_host tool."""

    ip: str = Field(
        ...,
        description="IPv4 or IPv6 address to look up",
        min_length=3,
        max_length=45,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """IP must be a valid IPv4 or IPv6 address."""
        v = v.strip()
        if not v:
            raise ValueError("ip cannot be empty")
        # Basic validation: IPv4 has dots, IPv6 has colons
        if ":" not in v and "." not in v:
            raise ValueError("ip must be IPv4 (with dots) or IPv6 (with colons)")
        return v


class CensysSearchParams(BaseModel):
    """Parameters for research_censys_search tool."""

    query: str = Field(
        ...,
        description="Censys query string (e.g., 'services.service_name: HTTP AND location.country: US')",
        min_length=1,
        max_length=1000,
    )
    max_results: int = Field(
        10,
        description="Maximum results to return (1-1000)",
        ge=1,
        le=1000,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Query must be non-empty and reasonably short."""
        v = v.strip()
        if not v:
            raise ValueError("query cannot be empty")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        """max_results must be between 1 and 1000."""
        if v < 1 or v > 1000:
            raise ValueError("max_results must be 1-1000")
        return v


class UnstructuredDocumentExtractParams(BaseModel):
    """Parameters for research_document_extract tool."""

    file_path: str = ""
    url: str = ""
    strategy: str = "auto"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        if v and v.strip():
            return validate_url(v)
        return v

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        v = v.lower().strip()
        valid_strategies = {"auto", "fast", "hi_res", "ocr_only"}
        if v not in valid_strategies:
            raise ValueError(f"strategy must be one of {valid_strategies}")
        return v

class InstructorStructuredExtractParams(BaseModel):
    """Parameters for research_structured_extract tool."""

    text: str = Field(
        ...,
        description="Input text to extract structured data from",
        min_length=1,
        max_length=100000,
    )
    output_schema: dict[str, str] = Field(
        ...,
        description="Field definitions (e.g., {'name': 'str', 'age': 'int', 'items': 'list'})",
    )
    model: str = Field(
        "auto",
        description="LLM model to use ('auto' for cascade)",
        max_length=100,
    )
    max_retries: int = Field(
        3,
        description="Max validation retries (1-10)",
        ge=1,
        le=10,
    )
    provider_override: str | None = Field(
        None,
        description="Force a specific provider (nvidia, openai, anthropic, groq, deepseek, gemini, moonshot, vllm)",
        max_length=50,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Text must be non-empty and within limits."""
        if not v or not v.strip():
            raise ValueError("text cannot be empty")
        return v

    @field_validator("output_schema")
    @classmethod
    def validate_schema(cls, v: dict[str, str]) -> dict[str, str]:
        """Schema must be non-empty dict with valid type names."""
        if not v:
            raise ValueError("output_schema cannot be empty")
        if len(v) > 100:
            raise ValueError("output_schema max 100 fields")

        valid_types = {
            "str", "string",
            "int", "integer",
            "float",
            "bool", "boolean",
            "list",
            "dict", "object",
        }

        for field_name, field_type in v.items():
            if not isinstance(field_name, str) or not field_name:
                raise ValueError("schema field names must be non-empty strings")
            if len(field_name) > 50:
                raise ValueError(f"field name '{field_name}' exceeds 50 chars")
            if not isinstance(field_type, str) or field_type.lower() not in valid_types:
                raise ValueError(
                    f"invalid type '{field_type}' for field '{field_name}'. "
                    f"Valid: str, int, float, bool, list, dict"
                )

        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        """Model must be non-empty or 'auto'."""
        v = v.strip()
        if not v:
            raise ValueError("model cannot be empty")
        return v

    @field_validator("provider_override")
    @classmethod
    def validate_provider(cls, v: str | None) -> str | None:
        """Provider, if provided, must be in allowed list."""
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("provider_override cannot be empty string")

        allowed = {
            "nvidia", "openai", "anthropic", "groq",
            "deepseek", "gemini", "moonshot", "vllm",
        }
        if v.lower() not in allowed:
            raise ValueError(
                f"invalid provider '{v}'. Allowed: {', '.join(sorted(allowed))}"
            )
        return v.lower()

class PaddleOCRParams(BaseModel):
    """Parameters for research_paddle_ocr tool."""

    image_url: str = Field(
        "",
        description="URL to image file (auto-download)",
        max_length=2048,
    )
    image_path: str = Field(
        "",
        description="Local file path to image",
        max_length=2048,
    )
    languages: list[str] | None = Field(
        None,
        description="List of language codes (e.g., ['en', 'ar']). Defaults to ['en'].",
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        """URL must be empty or valid."""
        if v and v.strip():
            validate_url(v)
        return v

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str] | None) -> list[str] | None:
        """Languages must be non-empty list of valid codes."""
        if v is None:
            return v
        if not isinstance(v, list) or not v:
            raise ValueError("languages must be a non-empty list")
        if len(v) > 10:
            raise ValueError("max 10 languages supported")
        # Basic validation: 2-3 char language codes
        for lang in v:
            if not isinstance(lang, str) or len(lang) < 2 or len(lang) > 5:
                raise ValueError(f"invalid language code: {lang}")
        return v


class CamelotTableExtractParams(BaseModel):
    """Parameters for research_table_extract tool."""

    pdf_url: str = Field(
        "",
        description="URL to PDF file (auto-download)",
        max_length=2048,
    )
    pdf_path: str = Field(
        "",
        description="Local file path to PDF",
        max_length=2048,
    )
    pages: str = Field(
        "all",
        description="Page range: 'all', single number (1), range (1-5), or comma-separated (1,3,5)",
        max_length=100,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("pdf_url")
    @classmethod
    def validate_pdf_url(cls, v: str) -> str:
        """URL must be empty or valid."""
        if v and v.strip():
            validate_url(v)
        return v

    @field_validator("pages")
    @classmethod
    def validate_pages(cls, v: str) -> str:
        """Pages must be 'all' or valid page range."""
        if v == "all":
            return v
        # Basic validation
        try:
            if "-" in v:
                parts = v.split("-")
                if len(parts) != 2:
                    raise ValueError("invalid range")
                int(parts[0])
                int(parts[1])
            elif "," in v:
                for p in v.split(","):
                    int(p.strip())
            else:
                int(v)
        except (ValueError, AttributeError):
            raise ValueError("pages must be 'all', single number, range (1-5), or comma-separated (1,3,5)")
        return v


class ScapyPacketCraftParams(BaseModel):
    """Parameters for research_packet_craft tool."""

    target: str = Field(
        ...,
        description="Target IP address or hostname",
        max_length=255,
    )
    packet_type: str = Field(
        "tcp_syn",
        description="Type of packet: tcp_syn, tcp_rst, icmp_echo, or udp_probe",
        max_length=50,
    )
    port: int = Field(
        80,
        description="Destination port (1-65535)",
        ge=1,
        le=65535,
    )
    timeout: int = Field(
        5,
        description="Response timeout in seconds (1-30)",
        ge=1,
        le=30,
    )

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("target")
    @classmethod
    def validate_target(cls, v: str) -> str:
        """Target must be non-empty hostname or IP."""
        if not v or not v.strip():
            raise ValueError("target cannot be empty")
        v = v.strip()
        if len(v) > 255:
            raise ValueError("target exceeds 255 chars")
        # Basic validation: alphanumeric, dots, hyphens
        if not all(c.isalnum() or c in ".-" for c in v):
            raise ValueError("target contains invalid characters")
        return v

    @field_validator("packet_type")
    @classmethod
    def validate_packet_type(cls, v: str) -> str:
        """Packet type must be valid."""
        v = v.strip()
        valid_types = {"tcp_syn", "tcp_rst", "icmp_echo", "udp_probe"}
        if v not in valid_types:
            raise ValueError(f"packet_type must be one of: {', '.join(sorted(valid_types))}")
        return v

class QueryBuilderParams(BaseModel):
    """Parameters for research_build_query tool."""

    user_request: str
    context: str = ""
    output_type: Literal["research", "osint", "threat_intel", "academic"] = "research"
    max_queries: int = 5
    optimize: bool = True

    model_config = {"extra": "forbid", "strict": True}

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

class LightpandaFetchParams(BaseModel):
    """Parameters for research_lightpanda_fetch tool."""

    url: str
    javascript: bool = True
    wait_for: str | None = None
    extract_links: bool = False

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("wait_for")
    @classmethod
    def validate_wait_for(cls, v: str | None) -> str | None:
        if v is not None and len(v) > 256:
            raise ValueError("wait_for max 256 characters")
        return v


class LightpandaBatchParams(BaseModel):
    """Parameters for research_lightpanda_batch tool."""

    urls: list[str]
    javascript: bool = True
    wait_for: str | None = None
    extract_links: bool = False
    timeout: int = 60

    model_config = {"extra": "forbid", "strict": True}

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


class CreepjsParams(BaseModel):
    """Parameters for research_creepjs_audit tool."""

    url: str = Field(default="https://creepjs.web.app", alias="target_url")
    headless: bool = True

    model_config = {"extra": "forbid", "strict": True, "populate_by_name": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        return validate_url(v)


class PydanticAgentParams(BaseModel):
    """Parameters for research_pydantic_agent tool."""

    prompt: str
    model: str = "nvidia_nim"
    system_prompt: str = ""
    max_tokens: int = 1000

    model_config = {"extra": "forbid", "strict": True}

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


class StructuredLLMParams(BaseModel):
    """Parameters for research_structured_llm tool."""

    prompt: str
    output_schema: dict[str, str]
    model: str = "nvidia_nim"
    provider_override: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("prompt must be non-empty")
        v = v.strip()
        if len(v) > 20000:
            raise ValueError("prompt max 20000 characters")
        return v

    @field_validator("output_schema")
    @classmethod
    def validate_output_schema(cls, v: dict[str, str]) -> dict[str, str]:
        if not v:
            raise ValueError("output_schema cannot be empty")
        if len(v) > 50:
            raise ValueError("output_schema max 50 fields")
        valid_types = {"str", "string", "int", "integer", "float", "bool", "boolean", "list", "dict", "object"}
        for field_name, field_type in v.items():
            if field_type.lower() not in valid_types:
                raise ValueError(
                    f"invalid type '{field_type}' for field '{field_name}'. "
                    f"Valid types: {', '.join(valid_types)}"
                )
        return v

    @field_validator("provider_override")
    @classmethod
    def validate_provider_override(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = {"nvidia", "openai", "anthropic", "groq", "deepseek", "gemini", "moonshot", "vllm"}
        if v.lower() not in valid:
            raise ValueError(f"invalid provider '{v}'. Valid: {', '.join(valid)}")
        return v


class MemoryStoreParams(BaseModel):
    """Parameters for research_memory_store tool."""

    content: str
    metadata: dict[str, Any] | None = None
    namespace: str = "default"

    model_config = {"extra": "forbid", "strict": True}

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


class MemoryRecallParams(BaseModel):
    """Parameters for research_memory_recall tool."""

    query: str
    namespace: str = "default"
    top_k: int = 5

    model_config = {"extra": "forbid", "strict": True}

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

class HierarchicalResearchParams(BaseModel):
    """Parameters for research_hierarchical_research tool."""

    query: str
    depth: int = 2
    max_sources: int = 10
    model: str = "nvidia"

    model_config = {"extra": "forbid", "strict": True}

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

class CryptoRiskParams(BaseModel):
    """Parameters for research_crypto_risk_score tool."""

    address: str
    chain: Literal["bitcoin", "ethereum"] = "bitcoin"

    model_config = {"extra": "forbid", "strict": True}

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

class EthereumTxDecodeParams(BaseModel):
    """Parameters for research_ethereum_tx_decode tool."""

    tx_hash: str

    model_config = {"extra": "forbid", "strict": True}

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


class DefiSecurityAuditParams(BaseModel):
    """Parameters for research_defi_security_audit tool."""

    contract_address: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("contract_address")
    @classmethod
    def validate_contract_address(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("contract_address must be 0x + 40 hex chars")
        try:
            int(v, 16)
        except ValueError:
            raise ValueError("contract_address must be valid hex")
        return v
