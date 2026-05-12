"""IntelOwl threat intelligence orchestration backend — 100+ analyzer integration."""

from __future__ import annotations
from loom.error_responses import handle_tool_errors

import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger("loom.tools.intelowl_backend")


def _detect_observable_type(observable: str) -> str:
    """Auto-detect observable type from value.

    Supports: IPv4, IPv6, domain, URL, email, MD5/SHA1/SHA256 hash, file path.

    Args:
        observable: The observable value to classify

    Returns:
        One of: 'ip', 'domain', 'url', 'email', 'hash', 'file', or 'unknown'
    """
    # IPv4
    if re.match(r"^(\d{1,3}\.){3}\d{1,3}$", observable):
        return "ip"

    # IPv6
    if ":" in observable and re.match(r"^[0-9a-fA-F:]+$", observable):
        return "ip"

    # URL
    if re.match(r"^https?://", observable):
        return "url"

    # Email
    if re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", observable):
        return "email"

    # Hash (MD5, SHA1, SHA256)
    if re.match(r"^[a-fA-F0-9]{32}$", observable):
        return "hash"
    if re.match(r"^[a-fA-F0-9]{40}$", observable):
        return "hash"
    if re.match(r"^[a-fA-F0-9]{64}$", observable):
        return "hash"

    # Domain (basic check)
    if "." in observable and "/" not in observable:
        return "domain"

    # File path
    if "/" in observable or "\\" in observable:
        return "file"

    return "unknown"


@handle_tool_errors("research_intelowl_analyze")
def research_intelowl_analyze(
    observable: str,
    observable_type: str = "auto",
    analyzers: list[str] | None = None,
) -> dict[str, Any]:
    """Analyze observable using IntelOwl's 100+ threat intelligence analyzers.

    IntelOwl is an open-source orchestration platform that aggregates threat
    intelligence from 100+ analyzers (VirusTotal, AbuseIPDB, URLhaus, etc.).

    Args:
        observable: The IOC to analyze (IP, domain, URL, email, hash, etc.)
        observable_type: Type hint: 'auto' (detect), 'ip', 'domain', 'url',
                        'email', 'hash', 'file'. Defaults to auto-detection.
        analyzers: List of specific analyzer names to run. If None, runs
                  IntelOwl's default analyzer set for the type.

    Returns:
        Dict with keys:
        - observable: The analyzed value
        - observable_type: Detected or provided type
        - job_id: IntelOwl job ID for status tracking
        - analyzers_run: List of analyzers executed
        - results: Dict mapping analyzer name to results
        - tags: Tags assigned by analyzers (e.g., 'malware', 'phishing')
        - risk_score: Overall risk score (0-100 if available)
        - error: Error message if analysis failed
    """
    # Get IntelOwl URL and API key from environment
    intelowl_url = os.environ.get("INTELOWL_URL", "http://localhost:8000")
    intelowl_key = os.environ.get("INTELOWL_API_KEY", "")

    result: dict[str, Any] = {
        "observable": observable,
        "observable_type": observable_type,
        "job_id": None,
        "analyzers_run": [],
        "results": {},
        "tags": [],
        "risk_score": None,
    }

    # Check if IntelOwl is configured
    if not intelowl_key:
        result["error"] = (
            "INTELOWL_API_KEY not set. Configure IntelOwl API key in environment."
        )
        logger.warning("intelowl_not_configured: missing API key")
        return result

    # Auto-detect type if requested
    if observable_type == "auto":
        observable_type = _detect_observable_type(observable)
        result["observable_type"] = observable_type

    # Prepare request headers
    headers = {
        "Authorization": f"Bearer {intelowl_key}",
        "Content-Type": "application/json",
    }

    # Build API request payload
    payload: dict[str, Any] = {
        "observable_name": observable,
        "observable_classification": observable_type,
    }

    # If specific analyzers provided, include them
    if analyzers:
        payload["analyzers"] = analyzers

    api_endpoint = f"{intelowl_url}/api/v2/scan"

    try:
        with httpx.Client(timeout=30.0) as client:
            # Submit analysis job
            resp = client.post(
                api_endpoint,
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            response_data = resp.json()

        # Extract job ID
        job_id = response_data.get("job_id")
        if not job_id:
            result["error"] = "No job ID returned from IntelOwl"
            logger.warning("intelowl_no_job_id observable=%s", observable)
            return result

        result["job_id"] = job_id

        # Fetch job results (may still be pending)
        result_endpoint = f"{intelowl_url}/api/v2/scan/{job_id}"
        result_resp = client.get(
            result_endpoint,
            headers=headers,
        )
        result_resp.raise_for_status()
        job_results = result_resp.json()

        # Status: 'pending', 'running', 'succeeded', 'failed'
        status = job_results.get("status")
        result["status"] = status

        # Collect analyzer results
        results_dict = job_results.get("results", {})
        if results_dict:
            for analyzer_name, analyzer_result in results_dict.items():
                if isinstance(analyzer_result, dict):
                    result["results"][analyzer_name] = analyzer_result
                    # Collect all unique analyzer names
                    if analyzer_name not in result["analyzers_run"]:
                        result["analyzers_run"].append(analyzer_name)

        # Extract tags from results (common pattern in analyzers)
        tags_set = set()
        for analyzer_result in result["results"].values():
            if isinstance(analyzer_result, dict):
                # Check for tags key
                if "tags" in analyzer_result and isinstance(analyzer_result["tags"], list):
                    tags_set.update(analyzer_result["tags"])
                # Check for report key (VirusTotal format)
                report = analyzer_result.get("report")
                if isinstance(report, dict) and "tags" in report and isinstance(report["tags"], list):
                    tags_set.update(report["tags"])

        result["tags"] = sorted(tags_set)

        # Try to calculate risk score (heuristic: % of detections)
        detection_count = 0
        total_analyzers = len(result["results"])
        for analyzer_result in result["results"].values():
            if isinstance(analyzer_result, dict):
                # VirusTotal-style detection
                if analyzer_result.get("detected") or analyzer_result.get("malicious"):
                    detection_count += 1
                # Generic detection flag
                report = analyzer_result.get("report", {})
                if isinstance(report, dict) and report.get("detected"):
                    detection_count += 1

        if total_analyzers > 0:
            result["risk_score"] = int((detection_count / total_analyzers) * 100)

        logger.info(
            "intelowl_analysis_complete observable=%s job_id=%s analyzers=%d",
            observable,
            job_id,
            len(result["analyzers_run"]),
        )

    except httpx.HTTPStatusError as exc:
        result["error"] = (
            f"IntelOwl API error ({exc.response.status_code}): {exc.response.text}"
        )
        logger.error(
            "intelowl_http_error observable=%s status=%d",
            observable,
            exc.response.status_code,
        )
    except httpx.RequestError as exc:
        result["error"] = f"IntelOwl connection error: {exc!s}"
        logger.error("intelowl_connection_error observable=%s: %s", observable, exc)
    except (json.JSONDecodeError, KeyError) as exc:
        result["error"] = f"IntelOwl response parse error: {exc!s}"
        logger.error("intelowl_parse_error observable=%s: %s", observable, exc)
    except Exception as exc:
        result["error"] = f"Unexpected error: {exc!s}"
        logger.error("intelowl_unexpected_error observable=%s: %s", observable, exc)

    return result
