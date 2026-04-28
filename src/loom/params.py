"""Pydantic v2 parameter models for all MCP tool arguments.

Each tool has a dedicated model with field validators for URLs, headers,
proxies, etc. All models forbid extra fields and use strict mode.
"""

from __future__ import annotations

import re
import logging

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from loom.config import CONFIG
from loom.validators import filter_headers, validate_js_script, validate_url

# Default Accept-Language header sourced from config
_DEFAULT_ACCEPT_LANG = CONFIG.get("DEFAULT_ACCEPT_LANGUAGE", "en-US,en;q=0.9,ar;q=0.8")


logger = logging.getLogger("loom.params")


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
    ] = "exa"
    include_raw: bool = False
    num_results: int = 10
    include_raw_search_context: bool = False

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

    @field_validator("num_results")
    @classmethod
    def validate_num_results(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("num_results must be 1-100")
        return v


class DeepParams(BaseModel):
    """Parameters for research_deep tool."""

    query: str
    max_results: int = 10
    include_raw: bool = False

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


class GithubParams(BaseModel):
    """Parameters for research_github tool."""

    query: str
    search_type: Literal["repos", "code", "issues", "discussions", "users"] = "repos"
    max_results: int = 10
    language: str | None = None
    sort: Literal["stars", "forks", "updated", "best-match"] = "best-match"

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        from loom.validators import sanitize_github_query

        if not v or not v.strip():
            raise ValueError("query must be non-empty")
        v = v.strip()
        if len(v) > 500:
            raise ValueError("query max 500 characters")
        return sanitize_github_query(v)

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_results must be 1-100")
        return v


class StealthParams(BaseModel):
    """Parameters for research_camoufox and research_botasaurus tools."""

    url: str
    mode: Literal["camoufox", "botasaurus"] = "camoufox"
    max_chars: int = 20000
    timeout: int | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 300):
            raise ValueError("timeout must be 1-300 seconds")
        return v


class CacheStatsParams(BaseModel):
    """Parameters for research_cache_stats tool."""

    # No parameters needed
    pass

    model_config = {"extra": "forbid", "strict": True}


class CacheClearParams(BaseModel):
    """Parameters for research_cache_clear tool."""

    older_than_days: int = 30

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("older_than_days")
    @classmethod
    def validate_older_than_days(cls, v: int) -> int:
        if v < 1 or v > 730:
            raise ValueError("older_than_days must be 1-730")
        return v


class BreachCheckParams(BaseModel):
    """Parameters for research_breach_check tool."""

    email: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[1]:
            raise ValueError("email must be valid format")
        return v


class PasswordCheckParams(BaseModel):
    """Parameters for research_password_check tool."""

    password: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or len(v) < 1:
            raise ValueError("password must be non-empty")
        if len(v) > 256:
            raise ValueError("password max 256 characters")
        return v


class SessionOpenParams(BaseModel):
    """Parameters for research_session_open tool."""

    name: str
    headless: bool = True
    login_url: str | None = None
    login_script: str | None = None
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


class LLMExpandParams(BaseModel):
    """Parameters for research_llm_expand tool."""

    text: str
    max_length: int = 1000
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("max_length")
    @classmethod
    def validate_max_length(cls, v: int) -> int:
        if v < 100 or v > 10000:
            raise ValueError("max_length must be 100-10000")
        return v


class LLMAnswerParams(BaseModel):
    """Parameters for research_llm_answer tool."""

    question: str
    context: str = ""
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("question must be non-empty")
        return v.strip()


class LLMEmbedParams(BaseModel):
    """Parameters for research_llm_embed tool."""

    text: str
    provider: str = "openai"
    model: str | None = None

    model_config = {"extra": "forbid", "strict": True}


class PdfExtractParams(BaseModel):
    """Parameters for research_pdf_extract tool."""

    pdf_url: str
    extract_text: bool = True
    extract_metadata: bool = True
    extract_images: bool = False
    max_pages: int | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("pdf_url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        url = validate_url(v)
        if not url.lower().endswith(".pdf") and "pdf" not in url.lower():
            raise ValueError("pdf_url must point to a PDF file")
        return url

    @field_validator("max_pages")
    @classmethod
    def validate_max_pages(cls, v: int | None) -> int | None:
        if v is not None and (v < 1 or v > 500):
            raise ValueError("max_pages must be 1-500")
        return v


class RssMonitorParams(BaseModel):
    """Parameters for research_rss_fetch and research_rss_search tools."""

    feed_url: str
    max_results: int = 20
    include_summaries: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("feed_url", mode="before")
    @classmethod
    def validate_feed_url(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_results must be 1-100")
        return v


class TextAnalyzeParams(BaseModel):
    """Parameters for research_text_analyze tool."""

    text: str
    analyze_sentiment: bool = True
    extract_entities: bool = True
    extract_keywords: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be non-empty")
        return v.strip()


class ScreenshotParams(BaseModel):
    """Parameters for research_screenshot tool."""

    url: str
    viewport_width: int = 1920
    viewport_height: int = 1080
    wait_for: str | None = None
    timeout: int | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("viewport_width", "viewport_height")
    @classmethod
    def validate_viewport(cls, v: int) -> int:
        if v < 640 or v > 7680:
            raise ValueError("viewport dimensions must be 640-7680")
        return v


class DomainIntelParams(BaseModel):
    """Parameters for domain intelligence tools."""

    domain: str
    include_dns: bool = True
    include_whois: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 255:
            raise ValueError("domain max 255 characters")
        if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", v.lower()):
            raise ValueError("domain must be a valid domain format")
        return v


class CompanyIntelParams(BaseModel):
    """Parameters for company intelligence tools."""

    company_name: str
    include_financials: bool = False
    include_leadership: bool = True
    include_news: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 500:
            raise ValueError("company_name must be 1-500 characters")
        return v


class ResumeIntelParams(BaseModel):
    """Parameters for research_resume_intel tool."""

    name: str
    location: str | None = None
    industry: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 255:
            raise ValueError("name must be 1-255 characters")
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


class CareerIntelParams(BaseModel):
    """Parameters for career intelligence tools."""

    job_title: str
    company: str | None = None
    industry: str | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("job_title")
    @classmethod
    def validate_job_title(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 255:
            raise ValueError("job_title must be 1-255 characters")
        return v


class JobResearchParams(BaseModel):
    """Parameters for research_job_research tool."""

    job_title: str
    location: str | None = None
    company: str | None = None
    max_results: int = 20

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("job_title")
    @classmethod
    def validate_job_title(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 255:
            raise ValueError("job_title must be 1-255 characters")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_results must be 1-100")
        return v


class UrlhausCheckParams(BaseModel):
    """Parameters for research_urlhaus_check and research_urlhaus_search tools."""

    query: str
    search_type: Literal["url", "domain", "hash"] = "url"
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


class CveLookupParams(BaseModel):
    """Parameters for research_cve_lookup and research_cve_detail tools."""

    cve_id: str
    include_metadata: bool = True
    include_references: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("cve_id")
    @classmethod
    def validate_cve_id(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^CVE-\d{4}-\d{4,}$", v):
            raise ValueError("cve_id must match pattern CVE-YYYY-XXXX")
        return v


class IpIntelParams(BaseModel):
    """Parameters for IP intelligence tools."""

    ip_address: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        v = v.strip()
        # Basic IPv4 and IPv6 validation
        import ipaddress
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("ip_address must be a valid IPv4 or IPv6 address")
        return v


class ImageIntelParams(BaseModel):
    """Parameters for image intelligence tools."""

    image_url: str
    extract_exif: bool = True
    extract_text: bool = False

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_image_url(cls, v: str) -> str:
        url = validate_url(v)
        # Check if URL looks like an image
        image_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
        if not url.lower().endswith(image_exts) and "image" not in url.lower():
            logger.warning("image_url may not point to image: %s", url)
        return url


class GeoipLocalParams(BaseModel):
    """Parameters for research_geoip_local tool."""

    ip_address: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        v = v.strip()
        import ipaddress
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("ip_address must be a valid IPv4 or IPv6 address")
        return v


class CertAnalyzerParams(BaseModel):
    """Parameters for research_cert_analyze tool."""

    domain: str
    port: int = 443

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 255:
            raise ValueError("domain max 255 characters")
        if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", v.lower()):
            raise ValueError("domain must be a valid domain format")
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
    include_recommendations: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)


class StylometryParams(BaseModel):
    """Parameters for research_stylometry tool."""

    text: str
    reference_texts: list[str] | None = None

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be non-empty")
        return v.strip()


class DeceptionDetectParams(BaseModel):
    """Parameters for research_deception_detect tool."""

    text: str

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("text must be non-empty")
        return v.strip()


class PassiveReconParams(BaseModel):
    """Parameters for research_passive_recon tool."""

    domain: str
    include_shodan: bool = True
    include_reverse_ip: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 255:
            raise ValueError("domain max 255 characters")
        if not re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", v.lower()):
            raise ValueError("domain must be a valid domain format")
        return v


class WaybackParams(BaseModel):
    """Parameters for research_wayback tool."""

    url: str
    max_snapshots: int = 50

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("max_snapshots")
    @classmethod
    def validate_max_snapshots(cls, v: int) -> int:
        if v < 1 or v > 500:
            raise ValueError("max_snapshots must be 1-500")
        return v


class ExpertiseParams(BaseModel):
    """Parameters for research_expertise tool."""

    person_name: str
    field: str | None = None
    max_results: int = 20

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("person_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 255:
            raise ValueError("person_name must be 1-255 characters")
        return v

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("max_results must be 1-100")
        return v


class MultiSearchParams(BaseModel):
    """Parameters for research_multi_search tool."""

    query: str
    providers: list[str] | None = None
    max_results_per_provider: int = 10

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


class CompetitiveIntelParams(BaseModel):
    """Parameters for competitive intelligence tools."""

    company_name: str
    competitors: list[str] | None = None
    include_market: bool = True
    include_pricing: bool = True
    include_products: bool = True

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 500:
            raise ValueError("company_name must be 1-500 characters")
        return v


class ChangeMonitorParams(BaseModel):
    """Parameters for research_change_monitor tool."""

    url: str
    check_interval_hours: int = 24
    history_days: int = 30

    model_config = {"extra": "forbid", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("check_interval_hours")
    @classmethod
    def validate_interval(cls, v: int) -> int:
        if v < 1 or v > 720:
            raise ValueError("check_interval_hours must be 1-720")
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
