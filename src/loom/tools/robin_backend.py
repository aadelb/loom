"""research_robin_scan — AI-powered dark web OSINT using robin tool.

Robin is a dark web reconnaissance tool that aggregates threat actor activity,
darkweb mentions, and infrastructure correlations. This module provides wrappers
for keyword-based searches, threat actor profiling, and continuous monitoring
of dark web activity.
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.robin_backend")

# Fallback APIs for dark web search (robin unavailable)
AHMIA_API_URL = "https://ahmia.fi/search/"
DARKSEARCH_API_URL = "https://darksearch.io/api/search"


def _validate_query(query: str) -> str:
    """Validate dark web search query.

    Args:
        query: Search query (keyword, actor name, etc.)

    Returns:
        The validated query

    Raises:
        ValueError: if query is invalid
    """
    query = query.strip() if isinstance(query, str) else ""

    if not query or len(query) > 500:
        raise ValueError("query must be 1-500 characters")

    # Allow alphanumeric, spaces, basic punctuation
    # Prevent shell injection
    if any(char in query for char in [";", "|", "&", "`", "$", "\n", "\r"]):
        raise ValueError("query contains disallowed shell characters")

    return query


def _validate_scan_type(scan_type: str) -> str:
    """Validate scan type.

    Args:
        scan_type: Type of scan (search, profile, monitor)

    Returns:
        The validated scan_type

    Raises:
        ValueError: if scan_type is invalid
    """
    valid_types = {"search", "profile", "monitor"}
    if scan_type not in valid_types:
        raise ValueError(f"scan_type must be one of {valid_types}")
    return scan_type


def _validate_timeout(timeout: int) -> int:
    """Validate timeout parameter.

    Args:
        timeout: Timeout in seconds

    Returns:
        The validated timeout

    Raises:
        ValueError: if timeout is invalid
    """
    if not isinstance(timeout, int) or timeout < 10 or timeout > 300:
        raise ValueError("timeout must be an integer between 10 and 300 seconds")
    return timeout


def _check_robin_available() -> tuple[bool, str]:
    """Check if robin tool is available.

    Returns:
        Tuple of (available: bool, message: str)
    """
    if shutil.which("robin"):
        return True, "robin CLI tool found"
    return False, "robin CLI tool not installed. Install from: https://github.com/robin-io/robin"


async def _run_robin_subprocess(
    query: str,
    scan_type: str,
    timeout: int,
) -> dict[str, Any]:
    """Run robin CLI tool via subprocess.

    Args:
        query: Search query
        scan_type: Type of scan
        timeout: Command timeout in seconds

    Returns:
        Dict with robin output and metadata
    """
    try:
        # Build robin command based on scan_type
        if scan_type == "search":
            cmd = ["robin", "search", query]
        elif scan_type == "profile":
            cmd = ["robin", "profile", query]
        else:  # monitor
            cmd = ["robin", "monitor", query, "--json"]

        # Run robin in subprocess with timeout
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

        if result.returncode != 0:
            logger.warning("robin_subprocess_failed returncode=%d stderr=%s", result.returncode, result.stderr)
            return {
                "success": False,
                "error": f"robin exited with code {result.returncode}",
                "stderr": result.stderr[:500],
            }

        # Try to parse JSON output (monitor mode)
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            # Fall back to plain text output
            output = {"raw_output": result.stdout}

        return {
            "success": True,
            "source": "robin_cli",
            "output": output,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "robin subprocess timeout",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "error": "robin CLI not found in PATH",
        }
    except Exception as e:
        logger.exception("robin_subprocess_error")
        return {
            "success": False,
            "error": f"subprocess error: {type(e).__name__}: {e}",
        }


async def _search_ahmia(query: str, timeout_secs: int) -> dict[str, Any]:
    """Search Ahmia dark web index.

    Args:
        query: Search query
        timeout_secs: Request timeout in seconds

    Returns:
        Dict with search results
    """
    try:
        async with httpx.AsyncClient(timeout=float(timeout_secs)) as client:
            params = {
                "q": query,
                "format": "json",
            }

            resp = await client.get(AHMIA_API_URL, params=params)

            if resp.status_code != 200:
                logger.warning("ahmia_search_failed status=%d", resp.status_code)
                return {
                    "success": False,
                    "error": f"Ahmia API returned {resp.status_code}",
                }

            data = resp.json()
            results = data.get("results", [])

            return {
                "success": True,
                "source": "ahmia",
                "query": query,
                "result_count": len(results),
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "description": r.get("description", "")[:300],
                    }
                    for r in results[:20]
                ],
            }

    except httpx.TimeoutException:
        return {"success": False, "error": "Ahmia search timeout"}
    except Exception as e:
        logger.warning("ahmia_search_error: %s", e)
        return {
            "success": False,
            "error": f"Ahmia search failed: {type(e).__name__}",
        }


async def _search_darksearch(query: str, timeout_secs: int) -> dict[str, Any]:
    """Search DarkSearch API.

    Args:
        query: Search query
        timeout_secs: Request timeout in seconds

    Returns:
        Dict with search results
    """
    try:
        async with httpx.AsyncClient(timeout=float(timeout_secs)) as client:
            params = {"query": query}

            resp = await client.get(DARKSEARCH_API_URL, params=params)

            if resp.status_code != 200:
                logger.warning("darksearch_failed status=%d", resp.status_code)
                return {
                    "success": False,
                    "error": f"DarkSearch API returned {resp.status_code}",
                }

            data = resp.json()
            results = data.get("data", [])

            return {
                "success": True,
                "source": "darksearch",
                "query": query,
                "result_count": len(results),
                "results": [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "description": r.get("description", "")[:300],
                    }
                    for r in results[:20]
                ],
            }

    except httpx.TimeoutException:
        return {"success": False, "error": "DarkSearch timeout"}
    except Exception as e:
        logger.warning("darksearch_error: %s", e)
        return {
            "success": False,
            "error": f"DarkSearch search failed: {type(e).__name__}",
        }


async def research_robin_scan(
    query: str,
    scan_type: str = "search",
    timeout: int = 60,
) -> dict[str, Any]:
    """Scan dark web for threat actors, mentions, and OSINT via robin.

    Performs AI-powered dark web reconnaissance using the robin tool (if available)
    or falls back to public dark web search APIs (Ahmia, DarkSearch). Supports
    keyword searches, threat actor profiling, and continuous monitoring.

    Args:
        query: Search query (keyword, actor name, etc.). Max 500 chars.
        scan_type: Type of scan: "search" (keyword), "profile" (threat actor),
                   or "monitor" (continuous). Default "search".
        timeout: Request timeout in seconds (10-300). Default 60.

    Returns:
        Dict with keys:
        - query: the input query
        - scan_type: type of scan performed
        - success: whether the scan succeeded
        - source: "robin_cli", "ahmia", "darksearch"
        - findings: list of matched darkweb pages/mentions
        - threat_actors: list of identified threat actors (if profile/monitor)
        - darkweb_mentions: list of direct mentions
        - sources_checked: list of data sources queried
        - error: error message if scan failed (optional)
    """
    # Validate inputs (store originals for error response)
    original_query = query
    original_scan_type = scan_type
    try:
        query = _validate_query(query)
        scan_type = _validate_scan_type(scan_type)
        timeout = _validate_timeout(timeout)
    except ValueError as e:
        return {
            "query": original_query,
            "scan_type": original_scan_type,
            "success": False,
            "error": str(e),
            "sources_checked": [],
        }

    logger.info("robin_scan query=%s scan_type=%s", query, scan_type)

    # Check if robin is available
    robin_available, robin_msg = _check_robin_available()

    # Try robin first if available
    if robin_available:
        robin_result = await _run_robin_subprocess(query, scan_type, timeout)
        if robin_result.get("success"):
            return {
                "query": query,
                "scan_type": scan_type,
                "success": True,
                "source": "robin_cli",
                "findings": robin_result.get("output", {}).get("results", []),
                "threat_actors": robin_result.get("output", {}).get("actors", []),
                "darkweb_mentions": robin_result.get("output", {}).get("mentions", []),
                "sources_checked": ["robin_cli"],
            }

    # Fallback to Ahmia and DarkSearch APIs
    logger.info("robin_not_available or failed, using fallback APIs")

    # Run both searches in parallel
    ahmia_task = _search_ahmia(query, timeout)
    darksearch_task = _search_darksearch(query, timeout)

    results = await asyncio.gather(ahmia_task, darksearch_task, return_exceptions=True)
    ahmia_result = results[0] if isinstance(results[0], dict) else {"success": False, "error": str(results[0])}
    darksearch_result = results[1] if isinstance(results[1], dict) else {"success": False, "error": str(results[1])}

    # Aggregate results
    findings = []
    sources_checked = []

    if ahmia_result.get("success"):
        findings.extend(ahmia_result.get("results", []))
        sources_checked.append("ahmia")

    if darksearch_result.get("success"):
        findings.extend(darksearch_result.get("results", []))
        sources_checked.append("darksearch")

    if not sources_checked:
        # Both APIs failed
        return {
            "query": query,
            "scan_type": scan_type,
            "success": False,
            "error": "All search sources failed",
            "sources_checked": sources_checked,
        }

    # Extract threat actors and mentions based on scan_type
    threat_actors = []
    darkweb_mentions = []

    if scan_type == "profile":
        # Look for actor names in descriptions
        threat_actors = [
            f.get("title", "")
            for f in findings
            if "profile" in f.get("description", "").lower() or "actor" in f.get("description", "").lower()
        ]

    darkweb_mentions = [f.get("url", "") for f in findings if f.get("url")]

    return {
        "query": query,
        "scan_type": scan_type,
        "success": True,
        "source": "fallback_apis",
        "findings": findings[:50],  # Cap at 50 findings
        "threat_actors": threat_actors,
        "darkweb_mentions": darkweb_mentions,
        "sources_checked": sources_checked,
        "robin_available": robin_available,
        "robin_message": robin_msg if not robin_available else None,
    }
