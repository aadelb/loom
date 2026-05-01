"""Access and content authenticity tools — legal monitoring, open access, content verification."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any
from urllib.parse import urlparse, urljoin

import httpx
from PIL import Image
from PIL.ExifTags import TAGS
from io import BytesIO

logger = logging.getLogger("loom.tools.access_tools")

_LUMEN_API = "https://lumendatabase.org/notices/search.json"
_GITHUB_DMCA_SEARCH = "https://api.github.com/search/code"
_UNPAYWALL_API = "https://api.unpaywall.org/v2"
_CORE_API = "https://core.ac.uk/api-v2/search"
_SEMANTIC_SCHOLAR_OA = "https://api.semanticscholar.org/graph/v1/paper"
_HIBP_API = "https://haveibeenpwned.com/api/v3"
_CDX_API = "https://web.archive.org/cdx/search/cdx"
_WAYBACK_SNAPSHOT = "https://web.archive.org/web"


async def _get_json(
    client: httpx.AsyncClient, url: str, timeout: float = 20.0, headers: dict[str, str] | None = None
) -> Any:
    """Safely fetch JSON from external API."""
    try:
        req_headers = {"User-Agent": "Loom-Research/1.0"}
        if headers:
            req_headers.update(headers)
        resp = await client.get(url, timeout=timeout, headers=req_headers)
        if resp.status_code == 200:
            return resp.json()
    except Exception as exc:
        logger.debug("access_tools JSON fetch failed: %s", exc)
    return None


async def _get_text(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0, headers: dict[str, str] | None = None
) -> str:
    """Safely fetch text from external source."""
    try:
        req_headers = {"User-Agent": "Loom-Research/1.0"}
        if headers:
            req_headers.update(headers)
        resp = await client.get(url, timeout=timeout, headers=req_headers)
        if resp.status_code == 200:
            return resp.text
    except Exception as exc:
        logger.debug("access_tools text fetch failed: %s", exc)
    return ""


async def _get_bytes(
    client: httpx.AsyncClient, url: str, timeout: float = 15.0
) -> bytes:
    """Safely fetch binary data from external source."""
    try:
        resp = await client.get(url, timeout=timeout, headers={"User-Agent": "Loom-Research/1.0"})
        if resp.status_code == 200:
            return resp.content
    except Exception as exc:
        logger.debug("access_tools binary fetch failed: %s", exc)
    return b""


def _extract_exif(image_data: bytes) -> dict[str, Any]:
    """Extract EXIF metadata from image bytes."""
    exif_info: dict[str, Any] = {}
    try:
        image = Image.open(BytesIO(image_data))
        exif_data = image._getexif() if hasattr(image, '_getexif') else None
        if exif_data:
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                exif_info[tag_name] = str(value)[:100]  # Cap value length
    except Exception as exc:
        logger.debug("EXIF extraction failed: %s", exc)
    return exif_info


def _compute_ela(original_bytes: bytes, quality: int = 95) -> dict[str, Any]:
    """Compute Error Level Analysis on image.

    Saves image at lower quality and compares to original to detect editing.
    Returns dict with suspicious_regions_count and error_level_score.
    """
    result: dict[str, Any] = {"suspicious_regions_count": 0, "error_level_score": 0.0}
    try:
        original_img = Image.open(BytesIO(original_bytes))
        if original_img.mode != "RGB":
            original_img = original_img.convert("RGB")

        # Recompress at lower quality
        recompressed_io = BytesIO()
        original_img.save(recompressed_io, format="JPEG", quality=quality)
        recompressed_io.seek(0)
        recompressed_img = Image.open(recompressed_io)

        # Compute difference
        original_data = original_img.tobytes()
        recompressed_data = recompressed_img.tobytes()

        if len(original_data) == len(recompressed_data):
            differences = sum(
                abs(a - b) for a, b in zip(original_data, recompressed_data)
            )
            total_pixels = len(original_data) // 3 if len(original_data) % 3 == 0 else len(original_data)
            error_level = differences / (total_pixels + 1) if total_pixels > 0 else 0.0

            result["error_level_score"] = min(100.0, error_level)
            result["suspicious_regions_count"] = 1 if error_level > 5.0 else 0

    except Exception as exc:
        logger.debug("ELA computation failed: %s", exc)

    return result


async def research_legal_takedown(domain: str) -> dict[str, Any]:
    """Monitor legal takedowns against a domain.

    Queries Lumen Database (lumendatabase.org) for takedown notices and
    searches GitHub's DMCA notices for mentions of the domain.

    Args:
        domain: target domain (e.g., "example.com")

    Returns:
        Dict with domain, takedown_notices (list of {title, date, status}),
        total_found, sources.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            takedowns: list[dict[str, Any]] = []
            sources_checked: list[str] = []

            # Query Lumen Database
            lumen_url = f"{_LUMEN_API}?term={domain}&per_page=10"
            lumen_data = await _get_json(client, lumen_url, timeout=20.0)
            if lumen_data and isinstance(lumen_data, dict):
                sources_checked.append("Lumen Database")
                results = lumen_data.get("results", [])
                for notice in results[:10]:
                    takedowns.append({
                        "title": notice.get("title", "")[:200],
                        "date": notice.get("date_sent", ""),
                        "status": notice.get("status", "unknown"),
                        "source": "Lumen Database",
                    })

            # Search GitHub DMCA via API (public code search)
            github_url = f"{_GITHUB_DMCA_SEARCH}?q=repo:github/dmca+{domain}"
            github_data = await _get_json(client, github_url, timeout=20.0)
            if github_data and isinstance(github_data, dict):
                sources_checked.append("GitHub DMCA")
                items = github_data.get("items", [])
                for item in items[:5]:
                    takedowns.append({
                        "title": item.get("name", "")[:200],
                        "date": item.get("created_at", ""),
                        "status": "filed",
                        "source": "GitHub DMCA",
                    })

            return {
                "domain": domain,
                "takedown_notices": takedowns,
                "total_found": len(takedowns),
                "sources": sources_checked,
            }

    return await _run()


async def research_open_access(doi: str = "", title: str = "") -> dict[str, Any]:
    """Find free/open-access versions of academic papers.

    Queries Unpaywall, CORE, and Semantic Scholar APIs to locate open-access
    mirrors and preprints of papers identified by DOI or title.

    Args:
        doi: Digital Object Identifier (optional)
        title: Paper title (required if doi not provided)

    Returns:
        Dict with query, open_access_url, sources_checked, alternatives (list).
    """

    async def _run() -> dict[str, Any]:
        if not doi and not title:
            return {
                "query": "",
                "open_access_url": "",
                "sources_checked": [],
                "alternatives": [],
                "error": "Provide either DOI or title",
            }

        async with httpx.AsyncClient(follow_redirects=True) as client:
            sources: list[str] = []
            alternatives: list[dict[str, Any]] = []
            primary_oa_url = ""

            # Try Unpaywall with DOI
            if doi:
                unpaywall_url = f"{_UNPAYWALL_API}/{doi}?email=loom@research.org"
                unpaywall_data = await _get_json(client, unpaywall_url, timeout=20.0)
                if unpaywall_data and isinstance(unpaywall_data, dict):
                    sources.append("Unpaywall")
                    if unpaywall_data.get("is_oa"):
                        oa_location = unpaywall_data.get("oa_locations", [{}])[0]
                        primary_oa_url = oa_location.get("url_for_pdf", "") or oa_location.get("url", "")
                        alternatives.append({
                            "url": primary_oa_url,
                            "source": "Unpaywall",
                            "version": unpaywall_data.get("oa_status", ""),
                        })

            # Try CORE API with title
            if title and not primary_oa_url:
                core_url = f"{_CORE_API}?q={title}&limit=5"
                core_data = await _get_json(client, core_url, timeout=20.0)
                if core_data and isinstance(core_data, dict):
                    sources.append("CORE")
                    results = core_data.get("results", [])
                    for result in results[:3]:
                        if result.get("downloadUrl"):
                            alternatives.append({
                                "url": result.get("downloadUrl", ""),
                                "source": "CORE",
                                "version": result.get("type", ""),
                            })
                            if not primary_oa_url:
                                primary_oa_url = result.get("downloadUrl", "")

            # Try Semantic Scholar with title
            if title:
                ss_url = f"{_SEMANTIC_SCHOLAR_OA}/search?query={title}"
                ss_data = await _get_json(client, ss_url, timeout=20.0)
                if ss_data and isinstance(ss_data, dict):
                    sources.append("Semantic Scholar")
                    papers = ss_data.get("data", [])
                    for paper in papers[:2]:
                        if paper.get("openAccessPdf"):
                            oa_url = paper.get("openAccessPdf", {}).get("url", "")
                            alternatives.append({
                                "url": oa_url,
                                "source": "Semantic Scholar",
                                "version": "open-access",
                            })
                            if not primary_oa_url:
                                primary_oa_url = oa_url

            query = doi or title
            return {
                "query": query,
                "open_access_url": primary_oa_url,
                "sources_checked": sources,
                "alternatives": alternatives,
            }

    return await _run()


async def research_content_authenticity(url: str) -> dict[str, Any]:
    """Verify that content hasn't been modified using Wayback Machine.

    Compares current version of a URL against its earliest Wayback Machine
    snapshot, computing content hashes to detect modifications.

    Args:
        url: target URL to verify

    Returns:
        Dict with url, earliest_snapshot, current_hash, original_hash,
        modified (bool), diff_summary.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            current_hash = ""
            original_hash = ""
            earliest_snapshot = ""
            modified = False
            diff_summary = ""

            # Fetch current content
            current_text = await _get_text(client, url, timeout=20.0)
            if current_text:
                current_hash = hashlib.sha256(current_text.encode()).hexdigest()

            # Query CDX API for earliest snapshot
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            cdx_url = f"{_CDX_API}?url={url}&output=json&filter=statuscode:200&collapse=urlkey&sort=timestamp:asc&limit=1"
            cdx_data = await _get_json(client, cdx_url, timeout=20.0)

            if cdx_data and isinstance(cdx_data, list) and len(cdx_data) > 1:
                # cdx_data[0] is header, cdx_data[1:] are results
                if len(cdx_data) > 1:
                    first_result = cdx_data[1]
                    timestamp = first_result[1] if len(first_result) > 1 else ""
                    if timestamp:
                        earliest_snapshot = f"{_WAYBACK_SNAPSHOT}/{timestamp}/{url}"

                        # Fetch earliest snapshot
                        original_text = await _get_text(client, earliest_snapshot, timeout=20.0)
                        if original_text:
                            original_hash = hashlib.sha256(original_text.encode()).hexdigest()
                            modified = current_hash != original_hash

                            # Create diff summary
                            if modified:
                                current_len = len(current_text)
                                original_len = len(original_text)
                                diff_summary = f"Content length changed: {original_len} → {current_len} chars"

            return {
                "url": url,
                "earliest_snapshot": earliest_snapshot,
                "current_hash": current_hash,
                "original_hash": original_hash,
                "modified": modified,
                "diff_summary": diff_summary,
            }

    return await _run()


async def research_credential_monitor(target: str, target_type: str = "email") -> dict[str, Any]:
    """Check if credentials have been exposed in known data breaches.

    Queries HIBP (HaveIBeenPwned) API to find breach records for an email
    address or username, and searches public breach databases.

    Args:
        target: email address or username to check
        target_type: "email" or "username" (default: "email")

    Returns:
        Dict with target, breaches_found (list of {name, date, data_types}),
        total_exposed.
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            breaches: list[dict[str, Any]] = []

            # Query HIBP API (requires User-Agent, no API key for basic lookup)
            hibp_url = f"{_HIBP_API}/breachedaccount/{target}"
            hibp_headers = {
                "User-Agent": "Loom-Research/1.0",
                "Accept": "application/vnd.api+json",
            }

            hibp_data = await _get_json(client, hibp_url, timeout=20.0, headers=hibp_headers)
            if hibp_data and isinstance(hibp_data, list):
                for breach in hibp_data[:20]:
                    breaches.append({
                        "name": breach.get("Name", ""),
                        "date": breach.get("BreachDate", ""),
                        "data_types": breach.get("DataClasses", []),
                        "is_sensitive": breach.get("IsSensitive", False),
                    })

            return {
                "target": target,
                "target_type": target_type,
                "breaches_found": breaches,
                "total_exposed": len(breaches),
            }

    return await _run()


async def research_deepfake_checker(image_url: str) -> dict[str, Any]:
    """Check image authenticity using EXIF analysis and Error Level Analysis.

    Downloads image, extracts EXIF metadata (detects editing software),
    and performs Error Level Analysis (ELA) by recompressing and comparing.

    Args:
        image_url: URL of image to analyze

    Returns:
        Dict with image_url, exif_analysis (dict), editing_software_detected (bool),
        ela_suspicious_regions, authenticity_score (0-100).
    """

    async def _run() -> dict[str, Any]:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            exif_data: dict[str, Any] = {}
            editing_software_detected = False
            ela_result: dict[str, Any] = {"suspicious_regions_count": 0, "error_level_score": 0.0}
            authenticity_score = 100.0

            # Download image
            image_bytes = await _get_bytes(client, image_url, timeout=20.0)
            if not image_bytes:
                return {
                    "image_url": image_url,
                    "exif_analysis": {},
                    "editing_software_detected": False,
                    "ela_suspicious_regions": 0,
                    "authenticity_score": 0.0,
                    "error": "Failed to download image",
                }

            # Extract EXIF
            exif_data = _extract_exif(image_bytes)

            # Check for editing software in EXIF
            editing_indicators = [
                "photoshop", "lightroom", "gimp", "capture one", "affinity",
                "corel", "paint.net", "pixlr", "photopea", "canva",
            ]
            exif_str = json.dumps(exif_data).lower()
            editing_software_detected = any(sw in exif_str for sw in editing_indicators)

            # Compute ELA
            ela_result = _compute_ela(image_bytes, quality=95)

            # Calculate authenticity score
            authenticity_score = 100.0
            if editing_software_detected:
                authenticity_score -= 20.0
            if ela_result.get("suspicious_regions_count", 0) > 0:
                authenticity_score -= 30.0
            if ela_result.get("error_level_score", 0.0) > 5.0:
                authenticity_score -= 20.0
            authenticity_score = max(0.0, authenticity_score)

            return {
                "image_url": image_url,
                "exif_analysis": exif_data,
                "editing_software_detected": editing_software_detected,
                "ela_suspicious_regions": ela_result.get("suspicious_regions_count", 0),
                "ela_error_level_score": ela_result.get("error_level_score", 0.0),
                "authenticity_score": authenticity_score,
            }

    return await _run()
