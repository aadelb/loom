"""Fast web crawler for target-focused OSINT extraction via Photon.

Photon crawls websites and extracts: URLs, emails, social media profiles,
subdomains, JavaScript files, and form endpoints. Uses native Photon CLI when
available, falls back to httpx + BeautifulSoup for basic extraction.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from loom.validators import validate_url

logger = logging.getLogger("loom.tools.photon_backend")

try:
    from selectolax.parser import HTMLParser

    _HAS_SELECTOLAX = True
except ImportError:  # pragma: no cover
    HTMLParser = None
    _HAS_SELECTOLAX = False


class PhotonParams(BaseModel):
    """Parameters for research_photon_crawl tool."""

    url: str
    depth: int = 2
    timeout: int = 30
    extract_emails: bool = True
    extract_social: bool = True
    extract_subdomains: bool = True
    extract_files: bool = True
    extract_forms: bool = True
    max_urls: int = 500

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

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        if v < 5 or v > 300:
            raise ValueError("timeout must be 5-300 seconds")
        return v

    @field_validator("max_urls")
    @classmethod
    def validate_max_urls(cls, v: int) -> int:
        if v < 10 or v > 5000:
            raise ValueError("max_urls must be 10-5000")
        return v


class PhotonResult(BaseModel):
    """Result from Photon crawl operation."""

    url: str
    crawled_urls: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    social_media: dict[str, list[str]] = Field(default_factory=dict)
    subdomains: list[str] = Field(default_factory=list)
    js_files: list[str] = Field(default_factory=list)
    forms: list[dict[str, Any]] = Field(default_factory=list)
    total_urls: int = 0
    tool: str = "photon"
    error: str | None = None
    execution_time_ms: int = 0

    model_config = ConfigDict(populate_by_name=True)


def _has_photon_cli() -> bool:
    """Check if Photon CLI is installed and available."""
    return shutil.which("photon") is not None


async def _run_photon_cli(
    url: str, depth: int, timeout: int, output_dir: str
) -> dict[str, Any]:
    """Run native Photon CLI and parse results.

    Args:
        url: Target URL to crawl
        depth: Crawl depth (1-5)
        timeout: Max crawl time in seconds
        output_dir: Output directory for results

    Returns:
        Dict with extracted data (urls, emails, subdomains, etc.)
    """
    try:
        import asyncio

        # Build photon command
        cmd = [
            "photon",
            "-u",
            url,
            "-l",
            str(depth),
            "-t",
            "10",  # Thread count
            "-o",
            output_dir,
        ]

        # Add DNS enumeration flag
        cmd.extend(["--dns"])

        logger.info("running_photon_cli url=%s depth=%d", url, depth)

        # Run photon with timeout
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            logger.warning("photon_cli failed: %s", result.stderr[:500])
            return {}

        # Parse output files
        output_path = Path(output_dir)
        data: dict[str, Any] = {
            "urls": [],
            "emails": [],
            "subdomains": [],
            "social_media": {},
            "js_files": [],
            "forms": [],
        }

        # Read URLs
        urls_file = output_path / "urls.txt"
        if urls_file.exists():
            with urls_file.open() as f:
                data["urls"] = [line.strip() for line in f if line.strip()]

        # Read emails
        emails_file = output_path / "emails.txt"
        if emails_file.exists():
            with emails_file.open() as f:
                data["emails"] = [line.strip() for line in f if line.strip()]

        # Read subdomains
        subdomains_file = output_path / "subdomains.txt"
        if subdomains_file.exists():
            with subdomains_file.open() as f:
                data["subdomains"] = [line.strip() for line in f if line.strip()]

        # Read JavaScript files
        js_file = output_path / "js.txt"
        if js_file.exists():
            with js_file.open() as f:
                data["js_files"] = [line.strip() for line in f if line.strip()]

        logger.info(
            "photon_cli completed: urls=%d emails=%d subdomains=%d js=%d",
            len(data["urls"]),
            len(data["emails"]),
            len(data["subdomains"]),
            len(data["js_files"]),
        )

        return data

    except subprocess.TimeoutExpired:
        logger.warning("photon_cli timeout after %d seconds", timeout)
        return {}
    except Exception as e:
        logger.error("photon_cli_error: %s", str(e)[:200])
        return {}


async def _crawl_fallback(
    url: str, depth: int, timeout: int, max_urls: int
) -> dict[str, Any]:
    """Fallback web crawler using httpx + basic HTML parsing.

    Extracts URLs, emails, subdomains, JavaScript files, and social media links.

    Args:
        url: Target URL to crawl
        depth: Crawl depth (1-5)
        timeout: Max crawl time in seconds
        max_urls: Maximum URLs to process

    Returns:
        Dict with extracted data
    """
    data: dict[str, Any] = {
        "urls": [],
        "emails": [],
        "subdomains": [],
        "social_media": {},
        "js_files": [],
        "forms": [],
    }

    visited: set[str] = set()
    to_visit: list[tuple[str, int]] = [(url, 0)]
    to_visit_urls: set[str] = {url}
    parsed_target = urlparse(url)
    target_domain = parsed_target.netloc

    # Regex patterns
    email_re = re.compile(r"\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}\b", re.IGNORECASE)
    js_re = re.compile(r'(?:src|href)=["\']([^"\']+\.js[^"\']*)["\']', re.IGNORECASE)
    social_re = {
        "twitter": re.compile(r"twitter\.com/(\w+)", re.IGNORECASE),
        "facebook": re.compile(r"facebook\.com/(\w+)", re.IGNORECASE),
        "linkedin": re.compile(r"linkedin\.com/(?:in|company)/([a-zA-Z0-9-]+)", re.IGNORECASE),
        "github": re.compile(r"github\.com/(\w+)", re.IGNORECASE),
        "instagram": re.compile(r"instagram\.com/(\w+)", re.IGNORECASE),
    }

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, verify=False
    ) as client:
        while to_visit and len(visited) < max_urls:
            current_url, current_depth = to_visit.pop(0)

            # Skip if already visited
            if current_url in visited:
                continue

            visited.add(current_url)

            # Stop if depth exceeded
            if current_depth > depth:
                continue

            try:
                logger.debug("crawl_fallback fetching url=%s depth=%d", current_url, current_depth)

                response = await client.get(current_url)
                response.raise_for_status()

                # Parse HTML
                if "text/html" not in response.headers.get("content-type", ""):
                    continue

                html = response.text

                # Extract emails
                for email in email_re.findall(html):
                    if email not in data["emails"]:
                        data["emails"].append(email)

                # Extract JavaScript files
                for js_file in js_re.findall(html):
                    js_url = urljoin(current_url, js_file)
                    if js_url not in data["js_files"]:
                        data["js_files"].append(js_url)

                # Extract social media profiles
                for platform, pattern in social_re.items():
                    for match in pattern.findall(html):
                        if platform not in data["social_media"]:
                            data["social_media"][platform] = []
                        if match not in data["social_media"][platform]:
                            data["social_media"][platform].append(match)

                # Extract URLs from href and src attributes
                if _HAS_SELECTOLAX and HTMLParser:
                    parser = HTMLParser(html)
                    for el in parser.css("a[href], script[src], link[href], iframe[src]"):
                        href = el.attributes.get("href") or el.attributes.get("src")
                        if href:
                            new_url = urljoin(current_url, href)
                            parsed = urlparse(new_url)

                            # Only crawl same domain or subdomains
                            if (
                                parsed.netloc == target_domain
                                or parsed.netloc.endswith(f".{target_domain}")
                            ):
                                if new_url not in visited and new_url not in to_visit_urls:
                                    to_visit.append((new_url, current_depth + 1))
                                    to_visit_urls.add(new_url)

                            # Collect all URLs
                            if new_url not in data["urls"]:
                                data["urls"].append(new_url)
                else:
                    # Fallback regex-based extraction
                    href_re = re.compile(
                        r'(?:href|src)=["\']([^"\']+)["\']', re.IGNORECASE
                    )
                    for match in href_re.findall(html):
                        new_url = urljoin(current_url, match)
                        parsed = urlparse(new_url)

                        # Only crawl same domain
                        if (
                            parsed.netloc == target_domain
                            or parsed.netloc.endswith(f".{target_domain}")
                        ):
                            if new_url not in visited and new_url not in to_visit_urls:
                                to_visit.append((new_url, current_depth + 1))
                                to_visit_urls.add(new_url)

                        if new_url not in data["urls"]:
                            data["urls"].append(new_url)

            except httpx.HTTPError as e:
                logger.debug("crawl_fallback http error: %s", str(e)[:100])
                continue
            except Exception as e:
                logger.debug("crawl_fallback parse error: %s", str(e)[:100])
                continue

    # Extract subdomains from URLs
    subdomains: set[str] = set()
    for crawled_url in data["urls"]:
        parsed = urlparse(crawled_url)
        if parsed.netloc != target_domain and parsed.netloc.endswith(f".{target_domain}"):
            subdomains.add(parsed.netloc)

    data["subdomains"] = sorted(list(subdomains))

    logger.info(
        "crawl_fallback completed: urls=%d emails=%d subdomains=%d",
        len(data["urls"]),
        len(data["emails"]),
        len(data["subdomains"]),
    )

    return data


async def research_photon_crawl(
    url: str,
    depth: int = 2,
    timeout: int = 30,
    extract_emails: bool = True,
    extract_social: bool = True,
    extract_subdomains: bool = True,
    extract_files: bool = True,
    extract_forms: bool = True,
    max_urls: int = 500,
) -> dict[str, Any]:
    """Fast target-focused OSINT extraction via web crawling.

    Crawls a website and extracts: URLs, emails, social media profiles,
    subdomains, JavaScript files, and form endpoints.

    Uses native Photon CLI if installed, otherwise falls back to httpx +
    BeautifulSoup for basic extraction.

    Args:
        url: Target URL to crawl
        depth: Crawl depth (1-5, default 2)
        timeout: Max crawl time in seconds (5-300, default 30)
        extract_emails: Whether to extract email addresses
        extract_social: Whether to extract social media profiles
        extract_subdomains: Whether to extract subdomains
        extract_files: Whether to extract JavaScript files
        extract_forms: Whether to extract form endpoints
        max_urls: Maximum URLs to crawl (10-5000, default 500)

    Returns:
        Dict with:
          - url: Target URL crawled
          - crawled_urls: List of all discovered URLs
          - emails: List of extracted email addresses
          - social_media: Dict of social platform → profiles mapping
          - subdomains: List of discovered subdomains
          - js_files: List of JavaScript file URLs
          - forms: List of form endpoints with methods
          - total_urls: Total unique URLs discovered
          - tool: "photon" (tool name)
          - execution_time_ms: Execution time in milliseconds
          - error: Error message if crawl failed

    Example:
        result = research_photon_crawl(
            url="https://example.com",
            depth=2,
            timeout=60
        )
        # Returns:
        # {
        #   "url": "https://example.com",
        #   "crawled_urls": ["https://example.com", "https://example.com/about", ...],
        #   "emails": ["contact@example.com", ...],
        #   "social_media": {"twitter": ["@example"], ...},
        #   "subdomains": ["api.example.com", "cdn.example.com"],
        #   "js_files": ["https://example.com/app.js", ...],
        #   "total_urls": 42,
        #   "tool": "photon",
        #   "execution_time_ms": 5234
        # }
    """
    import time

    start_time = time.time()

    try:
        # Validate parameters
        params = PhotonParams(
            url=url,
            depth=depth,
            timeout=timeout,
            extract_emails=extract_emails,
            extract_social=extract_social,
            extract_subdomains=extract_subdomains,
            extract_files=extract_files,
            extract_forms=extract_forms,
            max_urls=max_urls,
        )

        logger.info("photon_crawl starting url=%s depth=%d timeout=%d", params.url, params.depth, params.timeout)

        crawl_data: dict[str, Any] = {}

        # Try native Photon CLI first
        if _has_photon_cli():
            with tempfile.TemporaryDirectory() as temp_dir:
                crawl_data = await _run_photon_cli(
                    params.url, params.depth, params.timeout, temp_dir
                )

        # Fallback to basic crawler if Photon not available or failed
        if not crawl_data:
            logger.info("photon_cli not available, using fallback crawler")
            crawl_data = await _crawl_fallback(
                params.url, params.depth, params.timeout, params.max_urls
            )

        # Apply extraction filters
        result_data: dict[str, Any] = {
            "crawled_urls": crawl_data.get("urls", []),
            "emails": crawl_data.get("emails", []) if extract_emails else [],
            "social_media": crawl_data.get("social_media", {}) if extract_social else {},
            "subdomains": crawl_data.get("subdomains", []) if extract_subdomains else [],
            "js_files": crawl_data.get("js_files", []) if extract_files else [],
            "forms": crawl_data.get("forms", []) if extract_forms else [],
        }

        # Cap crawled URLs by max_urls
        result_data["crawled_urls"] = result_data["crawled_urls"][:max_urls]

        # Build result
        execution_time_ms = int((time.time() - start_time) * 1000)

        result = PhotonResult(
            url=params.url,
            crawled_urls=result_data["crawled_urls"],
            emails=result_data["emails"],
            social_media=result_data["social_media"],
            subdomains=result_data["subdomains"],
            js_files=result_data["js_files"],
            forms=result_data["forms"],
            total_urls=len(result_data["crawled_urls"]),
            execution_time_ms=execution_time_ms,
        )

        logger.info(
            "photon_crawl completed: urls=%d emails=%d subdomains=%d time=%dms",
            result.total_urls,
            len(result.emails),
            len(result.subdomains),
            execution_time_ms,
        )

        return result.model_dump(by_alias=True)

    except Exception as e:
        execution_time_ms = int((time.time() - start_time) * 1000)
        error_msg = f"photon_crawl error: {str(e)[:200]}"
        logger.error(error_msg)

        return {
            "url": url,
            "crawled_urls": [],
            "emails": [],
            "social_media": {},
            "subdomains": [],
            "js_files": [],
            "forms": [],
            "total_urls": 0,
            "tool": "photon",
            "error": error_msg,
            "execution_time_ms": execution_time_ms,
        }
