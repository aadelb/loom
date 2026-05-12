"""research_security_headers — Analyze HTTP security headers of a URL."""

from __future__ import annotations
import asyncio

import logging
from typing import Any

import httpx

from loom.validators import EXTERNAL_TIMEOUT_SECS, validate_url

logger = logging.getLogger("loom.tools.security_headers")

# Security headers to check: (header_name, importance_weight)
SECURITY_HEADERS = {
    "Strict-Transport-Security": 12,
    "Content-Security-Policy": 12,
    "X-Frame-Options": 11,
    "X-Content-Type-Options": 11,
    "X-XSS-Protection": 9,
    "Referrer-Policy": 10,
    "Permissions-Policy": 10,
    "Cross-Origin-Opener-Policy": 8,
    "Cross-Origin-Resource-Policy": 8,
}


async def research_security_headers(url: str = "", domain: str = "") -> dict[str, Any]:
    """Analyze HTTP security headers of a given URL.

    Fetches the URL and checks for critical security headers. Scores each
    header as present (pass), missing (fail), or misconfigured (warning).
    Computes an overall grade (A-F) based on presence and quality.

    Args:
        url: Full URL to analyze (scheme required)
        domain: Alternative parameter name; if provided without url, constructs https://domain

    Returns:
        Dict with keys:
          - url: input URL
          - headers_found: dict {header_name: {present, value, grade}}
          - score: float 0-100
          - grade: "A" | "B" | "C" | "D" | "F"
          - missing: list of missing headers
          - recommendations: list of security recommendations
          - error: str (if fetch failed)
    """
    # Resolve URL: prefer domain parameter if provided (construct HTTPS URL)
    target_url = url
    if domain and not url:
        target_url = f"https://{domain}"

    # Validate URL
    try:
        target_url = validate_url(target_url)
    except ValueError as e:
        return {
            "url": target_url,
            "error": f"Invalid URL: {e}",
        }

    logger.info("security_headers url=%s", target_url)

    try:
        # Fetch the URL
        async with httpx.AsyncClient(timeout=EXTERNAL_TIMEOUT_SECS, follow_redirects=True) as client:
            response = await client.head(target_url)

        headers = response.headers

    except httpx.TimeoutException:
        return {
            "url": target_url,
            "error": "Request timeout",
        }
    except httpx.RequestError as e:
        return {
            "url": target_url,
            "error": f"Request failed: {e}",
        }
    except Exception as e:
        logger.exception("Unexpected error fetching headers")
        return {
            "url": target_url,
            "error": f"Unexpected error: {type(e).__name__}: {e}",
        }

    # Analyze headers
    headers_found: dict[str, dict[str, Any]] = {}
    missing_headers: list[str] = []
    total_possible_points = 0
    earned_points = 0

    for header_name, weight in SECURITY_HEADERS.items():
        total_possible_points += weight

        # Case-insensitive header lookup
        header_value = None
        for key in headers.keys():
            if key.lower() == header_name.lower():
                header_value = headers[key]
                break

        grade = "pass" if header_value else "fail"
        if header_value:
            earned_points += weight
            # Simple heuristic checks for quality
            if header_name == "Content-Security-Policy":
                if "unsafe-inline" in header_value or "unsafe-eval" in header_value:
                    grade = "warning"
                    earned_points -= 2  # Penalty for unsafe CSP
            elif header_name == "Strict-Transport-Security":
                if "max-age" not in header_value:
                    grade = "warning"
                    earned_points -= 2

        headers_found[header_name] = {
            "present": header_value is not None,
            "value": header_value or "",
            "grade": grade,
        }

        if not header_value:
            missing_headers.append(header_name)

    # Compute score (0-100)
    score = (earned_points / total_possible_points * 100) if total_possible_points > 0 else 0
    score = max(0, min(100, score))

    # Assign letter grade
    if score >= 90:
        grade_letter = "A"
    elif score >= 80:
        grade_letter = "B"
    elif score >= 60:
        grade_letter = "C"
    elif score >= 40:
        grade_letter = "D"
    else:
        grade_letter = "F"

    # Generate recommendations
    recommendations: list[str] = []

    if "Strict-Transport-Security" in missing_headers:
        recommendations.append("Add Strict-Transport-Security header (enable HSTS)")

    if "Content-Security-Policy" in missing_headers:
        recommendations.append("Implement Content-Security-Policy (CSP) to prevent XSS")

    if "X-Frame-Options" in missing_headers:
        recommendations.append("Add X-Frame-Options to prevent clickjacking")

    if "X-Content-Type-Options" in missing_headers:
        recommendations.append("Add X-Content-Type-Options: nosniff")

    if "Referrer-Policy" in missing_headers:
        recommendations.append("Add Referrer-Policy to control referrer leakage")

    if "Permissions-Policy" in missing_headers:
        recommendations.append("Implement Permissions-Policy for feature restrictions")

    # Check for warning-level issues
    if headers_found.get("Content-Security-Policy", {}).get("grade") == "warning":
        recommendations.append("Review CSP for unsafe-inline and unsafe-eval directives")

    if not recommendations:
        recommendations.append("All major security headers are in place; review CSP strictness")

    return {
        "url": target_url,
        "headers_found": headers_found,
        "score": round(score, 1),
        "grade": grade_letter,
        "missing": missing_headers,
        "recommendations": recommendations,
    }
