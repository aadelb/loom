"""research_browser_fingerprint — Analyze browser fingerprinting vectors on webpages."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.fingerprint_backend")

# Known fingerprinting libraries (by script URL patterns and names)
_FINGERPRINTING_LIBS = {
    "fingerprintjs": {
        "names": ["fingerprintjs", "fingerprintjs2", "fingerprintjs3"],
        "urls": [
            "fingerprintjs.com",
            "fingerprint2.js",
            "fingerprint.js",
            "fingerprinting",
        ],
    },
    "clientjs": {
        "names": ["clientjs", "client.js"],
        "urls": ["clientjs.com", "client.js"],
    },
    "evercookie": {
        "names": ["evercookie"],
        "urls": ["evercookie", "evercookie.js"],
    },
    "MaxMind": {
        "names": ["maxmind", "geoip"],
        "urls": ["maxmind.com", "geoip"],
    },
    "Crowd Control": {
        "names": ["crowd-control", "crowd_control"],
        "urls": ["crowdcontrol.live"],
    },
}

# Fingerprinting API patterns (with word boundaries to reduce false positives)
_FINGERPRINTING_APIS = [
    ("canvas", r"\b(?:canvas|canvasContext|getImageData)\b"),
    ("webgl", r"\b(?:webgl|WebGLRenderingContext|getParameter|UNMASKED_RENDERER_WEBGL)\b"),
    ("audio", r"\b(?:OfflineAudioContext|OscillatorNode|createAnalyser|getByteTimeDomainData)\b"),
    ("font_enumeration", r"\b(?:measureText|getFontHeight|fontWidth|fontDetect)\b"),
    ("screen_resolution", r"screen\.(?:width|height|availWidth|availHeight)\b"),
    ("timezone", r"\b(?:getTimezoneOffset|DateTimeFormat)\b"),
    ("language", r"navigator\.languages?\b"),
    ("user_agent", r"navigator\.userAgent\b"),
    ("cpu_cores", r"navigator\.hardwareConcurrency\b"),
    ("memory", r"navigator\.deviceMemory\b"),
    ("plugins", r"navigator\.plugins\b|MimeType"),
    ("geolocation", r"navigator\.geolocation\b|getCurrentPosition"),
    ("camera_microphone", r"\b(?:getUserMedia|enumerateDevices)\b"),
    ("battery", r"navigator\.battery\b|getBattery"),
]


def _detect_fingerprinting_libraries(html: str) -> dict[str, Any]:
    """Detect known fingerprinting libraries in HTML/JS.

    Args:
        html: HTML content of webpage

    Returns:
        Dict mapping library name to detection details (list of all matched patterns)
    """
    detected = {}

    for lib_name, lib_info in _FINGERPRINTING_LIBS.items():
        library_patterns = lib_info.get("names", []) + lib_info.get("urls", [])
        matched_patterns = []

        for pattern in library_patterns:
            # Case-insensitive search
            if re.search(re.escape(pattern), html, re.IGNORECASE):
                matched_patterns.append(pattern)

        if matched_patterns:
            detected[lib_name] = {
                "detected": True,
                "patterns": matched_patterns,  # Changed from "pattern" (singular) to "patterns" (plural)
            }

    return detected


def _detect_fingerprinting_apis(html: str) -> dict[str, bool]:
    """Detect browser fingerprinting APIs used in JavaScript.

    Args:
        html: HTML content of webpage

    Returns:
        Dict mapping API category to whether it's potentially used
    """
    detected = {}

    for api_name, pattern in _FINGERPRINTING_APIS:
        # Look for the API pattern in script tags
        if re.search(pattern, html, re.IGNORECASE):
            detected[api_name] = True
        else:
            detected[api_name] = False

    return detected


def _calculate_tracking_score(
    libraries: dict[str, Any],
    apis: dict[str, bool],
) -> int:
    """Calculate fingerprinting risk score 0-100.

    Scoring logic:
    - Each detected library: +10 points
    - Each detected API: +5 points
    - Capped at 100 (max realistic score ~140 without cap)

    Args:
        libraries: Detected libraries
        apis: Detected APIs

    Returns:
        Risk score from 0 (no fingerprinting) to 100 (aggressive fingerprinting)
    """
    score = 0

    # Each detected library adds points
    score += len(libraries) * 10

    # Each detected API category adds points
    api_count = sum(1 for detected in apis.values() if detected)
    score += api_count * 5

    # Cap at 100 (preserves risk level thresholds)
    return min(score, 100)


@handle_tool_errors("research_browser_fingerprint")
def research_browser_fingerprint(
    url: str = "https://example.com",
    timeout: int = 30,
) -> dict[str, Any]:
    """Analyze browser fingerprinting vectors on a webpage.

    Detects:
    - Canvas fingerprinting
    - WebGL introspection
    - AudioContext fingerprinting
    - Font enumeration
    - Screen resolution tracking
    - Known fingerprinting libraries (FingerprintJS, ClientJS, EverCookie)

    Args:
        url: Website URL to analyze (default "https://example.com")
        timeout: HTTP request timeout in seconds (default 30)

    Returns:
        Dict with keys:
        - url: Analyzed URL
        - success: Boolean indicating if analysis completed
        - fingerprint_vectors: Dict of detected fingerprinting methods
        - libraries_detected: List of known fingerprinting libraries found
        - api_detections: Dict mapping API category to boolean (detected)
        - tracking_score: Risk score 0-100
        - risk_level: String ("none", "low", "medium", "high", "critical")
        - recommendations: List of privacy recommendations
        - error: Error message if failed
    """
    result: dict[str, Any] = {
        "url": url,
        "success": False,
        "fingerprint_vectors": {},
        "libraries_detected": [],
        "api_detections": {},
        "tracking_score": 0,
        "risk_level": "none",
        "recommendations": [],
        "error": None,
    }

    # Basic URL validation
    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "Invalid URL — must start with http:// or https://"
        return result

    try:
        # Fetch webpage with reasonable timeout
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(
                url,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
            )
            resp.raise_for_status()
            html_content = resp.text

    except httpx.HTTPError as exc:
        result["error"] = f"Failed to fetch URL: {exc!s}"
        logger.warning("fingerprint_fetch_failed url=%s: %s", url, exc)
        return result
    except Exception as exc:
        result["error"] = f"Unexpected error: {exc!s}"
        logger.error("fingerprint_analysis_exception url=%s: %s", url, exc, exc_info=True)
        return result

    # Detect libraries
    libraries = _detect_fingerprinting_libraries(html_content)
    result["libraries_detected"] = list(libraries.keys())

    # Detect APIs
    apis = _detect_fingerprinting_apis(html_content)
    result["api_detections"] = apis

    # Calculate tracking score
    score = _calculate_tracking_score(libraries, apis)
    result["tracking_score"] = score

    # Determine risk level (calibrated to practical fingerprinting intensity)
    # 0 = no detection; 1-20 = light (mostly device-info APIs); 21-50 = moderate;
    # 51-80 = aggressive (multiple libraries or heavy API use); 81+ = critical
    if score == 0:
        result["risk_level"] = "none"
    elif score <= 20:
        result["risk_level"] = "low"
    elif score <= 50:
        result["risk_level"] = "medium"
    elif score <= 80:
        result["risk_level"] = "high"
    else:
        result["risk_level"] = "critical"

    # Build recommendations
    recommendations = []

    # Check detected APIs efficiently
    if apis.get("canvas", False):
        recommendations.append(
            "Canvas fingerprinting detected. Use browser extension to block canvas access."
        )

    if apis.get("webgl", False):
        recommendations.append(
            "WebGL fingerprinting detected. Disable WebGL in browser or use privacy extension."
        )

    if apis.get("audio", False):
        recommendations.append(
            "AudioContext fingerprinting detected. Limit audio API access via browser settings."
        )

    if libraries:
        recommendations.append(
            f"Known fingerprinting libraries detected: {', '.join(libraries.keys())}. "
            "Consider using privacy-focused browser or extensions."
        )

    if not recommendations:
        recommendations.append("No aggressive fingerprinting detected. Website appears privacy-friendly.")

    result["recommendations"] = recommendations

    # Prepare detailed fingerprint vectors
    vectors = {}
    for api_name, detected in apis.items():
        if detected:
            vectors[api_name] = {"detected": True}

    for lib_name, lib_data in libraries.items():
        vectors[f"library_{lib_name}"] = lib_data

    result["fingerprint_vectors"] = vectors
    result["success"] = True

    logger.info(
        "fingerprint_analysis_complete url=%s risk_level=%s score=%d",
        url,
        result["risk_level"],
        score,
    )

    return result
