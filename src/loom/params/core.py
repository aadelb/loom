"""Pydantic parameter models for core tools."""

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
    "BotasaurusParams",
    "CamoufoxParams",
    "CommitAnalyzerParams",
    "ContentAuthenticityParams",
    "DeadContentParams",
    "DeepParams",
    "DeepfakeCheckerParams",
    "ExploitSearchParams",
    "FetchParams",
    "GitHubParams",
    "GitHubSearchParams",
    "InvisibleWebParams",
    "JSIntelParams",
    "LightpandaFetchParams",
    "MarkdownParams",
    "MultiSearchParams",
    "NodriverFetchParams",
    "PDFSearchParams",
    "PolyglotSearchParams",
    "PropagandaDetectorParams",
    "RSSFetchParams",
    "RSSSearchParams",
    "RefusalDetectorParams",
    "RegistryGraveyardParams",
    "ScraperEngineFetchParams",
    "SearchDiscrepancyParams",
    "SearchParams",
    "SpiderParams",
    "SubdomainTemporalParams",
    "WaybackParams",
    "ZenFetchParams",
]


class BotasaurusParams(BaseModel):
    """Parameters for research_botasaurus tool."""

    url: str
    max_chars: int = 20000
    wait_time: int = 5
    timeout: int = 30
    javascript_enabled: bool = True

    model_config = {"extra": "ignore", "strict": True}

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




class CamoufoxParams(BaseModel):
    """Parameters for research_camoufox tool."""

    url: str
    max_chars: int = 20000
    wait_time: int = 5
    timeout: int = 30
    return_format: Literal["text", "screenshot", "html"] = "text"

    model_config = {"extra": "ignore", "strict": True}

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




class CommitAnalyzerParams(BaseModel):
    """Parameters for research_commit_analyzer tool."""

    repo: str
    days_back: int = 30

    model_config = {"extra": "ignore", "strict": True}

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



class ContentAuthenticityParams(BaseModel):
    """Parameters for research_content_authenticity tool."""

    url: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)




class DeadContentParams(BaseModel):
    """Parameters for research_dead_content tool."""

    url: str
    include_snapshots: bool = True
    max_sources: int = 12

    model_config = {"extra": "ignore", "strict": True}

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




class DeepParams(BaseModel):
    """Parameters for research_deep tool."""

    query: str
    max_results: int = 20
    include_community: bool = True
    include_citations: bool = True
    mode: Literal["fast", "thorough"] = "thorough"

    model_config = {"extra": "ignore", "strict": True}

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




class DeepfakeCheckerParams(BaseModel):
    """Parameters for research_deepfake_checker tool."""

    image_url: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("image_url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        url = validate_url(v)
        # Allow common image extensions
        allowed_exts = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff")
        if not url.lower().endswith(allowed_exts):
            raise ValueError("image_url must point to an image file")
        return url




class ExploitSearchParams(BaseModel):
    """Parameters for research_exploit_search tool."""

    model: str = Field(default="", max_length=100)
    severity: str = Field(default="", max_length=20)
    query: str = Field(default="", max_length=500)

    model_config = {"extra": "ignore", "strict": True}



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

    model_config = {"extra": "ignore", "strict": True}

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




class GitHubParams(BaseModel):
    """Parameters for research_github tool."""

    query: str
    language: str | None = None
    sort_by: Literal["stars", "forks", "updated", "best-match"] = "stars"
    per_page: int = 10
    code_search: bool = False

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

    @field_validator("per_page")
    @classmethod
    def validate_per_page(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError("per_page must be 1-100")
        return v




class GitHubSearchParams(BaseModel):
    """Parameters for research_github_search tool."""

    query: str = Field(
        description="GitHub search query",
        max_length=256,
    )
    max_results: int = Field(
        default=10,
        description="Max results (1-100)",
        ge=1,
        le=100,
        alias="limit",
    )

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v.strip()




class InvisibleWebParams(BaseModel):
    """Parameters for research_invisible_web tool."""

    domain: str
    check_robots: bool = True
    check_sitemap: bool = True
    check_hidden_paths: bool = True
    check_js_endpoints: bool = True
    max_paths: int = 50

    model_config = {"extra": "ignore", "strict": True}

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

    model_config = {"extra": "ignore", "strict": True}

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




class LightpandaFetchParams(BaseModel):
    """Parameters for research_lightpanda_fetch tool."""

    url: str
    javascript: bool = True
    wait_for: str | None = None
    extract_links: bool = False

    model_config = {"extra": "ignore", "strict": True}

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

    model_config = {"extra": "ignore", "strict": True}

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




class MultiSearchParams(BaseModel):
    """Parameters for research_multi_search tool."""

    query: str
    providers: list[str] | None = None
    limit_per_provider: int = 5

    model_config = {"extra": "ignore", "strict": True}

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




class NodriverFetchParams(BaseModel):
    """Parameters for research_nodriver_fetch tool."""

    url: str
    wait_for: str | None = None
    timeout: int = 30
    screenshot: bool = False
    bypass_cache: bool = False
    max_chars: int = 20000

    model_config = {"extra": "ignore", "strict": True}

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




class PDFSearchParams(BaseModel):
    """Parameters for research_pdf_search tool."""

    url: str
    query: str

    model_config = {"extra": "ignore", "strict": True}

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




class PolyglotSearchParams(BaseModel):
    """Parameters for research_polyglot_search tool."""

    query: str
    languages: list[str] | None = None
    max_results: int = Field(default=10, ge=1, le=100)

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate search query."""
        v = v.strip()
        if not v or len(v) > 500:
            raise ValueError("query must be 1-500 characters")
        return v

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, v: list[str] | None) -> list[str] | None:
        """Validate language codes."""
        if v is None:
            return v
        valid_langs = {"ar", "zh", "ru", "fa", "tr", "ko", "ja", "de", "pt", "es"}
        if not isinstance(v, list) or len(v) == 0:
            raise ValueError("languages must be non-empty list or None")
        if len(v) > 10:
            raise ValueError("languages max 10 items")
        for lang in v:
            if lang not in valid_langs:
                raise ValueError(f"language '{lang}' not supported")
        return v




class PropagandaDetectorParams(BaseModel):
    """Parameters for research_propaganda_detector tool."""

    text: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or len(v) > 100000:
            raise ValueError("text must be 1-100000 characters")
        return v




class RSSFetchParams(BaseModel):
    """Parameters for research_rss_fetch tool."""

    feed_url: str
    max_results: int = Field(default=20, alias="limit")
    parse_content: bool = False

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

    @field_validator("feed_url", mode="before")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        return validate_url(v)

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > 500:
            raise ValueError("max_results must be 1-500")
        return v




class RSSSearchParams(BaseModel):
    """Parameters for research_rss_search tool."""

    query: str
    max_results: int = Field(default=10, alias="limit")

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




class RefusalDetectorParams(BaseModel):
    model_config = {"extra": "ignore", "strict": True}
    text: str




class RegistryGraveyardParams(BaseModel):
    """Parameters for research_registry_graveyard tool."""

    package_name: str
    ecosystem: Literal["pypi", "npm", "rubygems"] = "pypi"

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("package_name")
    @classmethod
    def validate_package_name(cls, v: str) -> str:
        if not v or len(v) > 255:
            raise ValueError("package_name must be 1-255 characters")
        # Allow alphanumeric, hyphens, underscores, dots
        if not re.match(r"^[a-zA-Z0-9_.-]+$", v):
            raise ValueError("package_name contains disallowed characters")
        return v




class ScraperEngineFetchParams(BaseModel):
    """Parameters for research_engine_fetch tool."""

    url: str
    mode: Literal["auto", "stealth", "max", "fast"] = "auto"
    max_escalation: int | None = None
    extract_title: bool = False
    force_backend: str | None = None

    model_config = {"extra": "ignore", "strict": True}

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




class SearchDiscrepancyParams(BaseModel):
    """Parameters for research_search_discrepancy tool."""

    query: str

    model_config = {"extra": "ignore", "strict": True}

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or len(v) > 200:
            raise ValueError("query must be 1-200 characters")
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

    model_config = {"extra": "ignore", "strict": True, "populate_by_name": True}

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

    model_config = {"extra": "ignore", "strict": True}

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




class WaybackParams(BaseModel):
    """Parameters for research_wayback tool."""

    url: str
    year: int | None = None

    model_config = {"extra": "ignore", "strict": True}

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




class ZenFetchParams(BaseModel):
    """Parameters for research_zen_fetch tool."""

    url: str
    timeout: int = 30
    headless: bool = True

    model_config = {"extra": "ignore", "strict": True}

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




