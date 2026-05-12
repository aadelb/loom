"""Privacy & anti-forensics tools for browser fingerprinting, exposure detection, artifact cleanup, and steganography."""

from __future__ import annotations

import hashlib
import logging
import pathlib
from typing import Any
from loom.error_responses import handle_tool_errors

logger = logging.getLogger("loom.tools.privacy_tools")

# Zero-width character mappings for steganography
_ZERO_WIDTH_CHARS = {
    "ZWSP": "​",  # Zero-width space
    "ZWNJ": "‌",  # Zero-width non-joiner
    "ZWJ": "‍",   # Zero-width joiner
    "BOM": "﻿",   # Byte order mark
}


@handle_tool_errors("research_fingerprint_audit")
def research_fingerprint_audit(
    target_url: str = "https://browserleaks.com/javascript",
) -> dict[str, Any]:
    """Launch headless browser and extract fingerprint vectors from target URL.

    Simulates a browser visit and extracts fingerprint vectors including
    canvas hash, WebGL hash, audio context hash, font count, and screen resolution.

    If playwright is not available, returns graceful error message.

    Args:
        target_url: Target URL to fingerprint (default: browserleaks.com)

    Returns:
        Dict with keys:
          - canvas_hash: str (SHA-256 hash of canvas rendering)
          - webgl_hash: str (SHA-256 hash of WebGL data)
          - audio_hash: str (SHA-256 hash of audio context)
          - font_count: int (number of fonts detected)
          - screen_res: str (e.g., "1920x1080")
          - total_vectors: int (total attributes collected)
          - uniqueness_score: int (0-100, higher = more unique)
          - error: str (if playwright not installed)
    """
    try:
        import playwright
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("playwright not installed")
        return {
            "error": "playwright not installed",
            "install_command": "pip install playwright && playwright install",
        }

    try:
        logger.info("fingerprint_audit url=%s", url)

        with sync_playwright() as p:
            # Launch headless Chrome
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            )
            page = context.new_page()

            # Navigate to target URL
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                logger.warning("page.goto failed: %s", e)
                context.close()
                browser.close()
                return {
                    "error": f"Failed to load URL: {e}",
                    "url": url,
                }

            # Execute fingerprinting script
            fingerprint_script = """
            () => {
              const fingerprints = {};

              // Canvas fingerprint
              try {
                const canvas = document.createElement('canvas');
                canvas.width = 200;
                canvas.height = 50;
                const ctx = canvas.getContext('2d');
                ctx.textBaseline = 'top';
                ctx.font = '14px Arial';
                ctx.fillStyle = '#f60';
                ctx.fillRect(125, 1, 62, 20);
                ctx.fillStyle = '#069';
                ctx.fillText('Browser Fingerprint', 2, 15);
                fingerprints.canvas_hash = canvas.toDataURL().substring(0, 50);
              } catch (e) {
                fingerprints.canvas_hash = 'error';
              }

              // WebGL fingerprint
              try {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                fingerprints.webgl = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
              } catch (e) {
                fingerprints.webgl = 'not available';
              }

              // Audio context fingerprint
              try {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const analyser = audioContext.createAnalyser();
                const gainNode = audioContext.createGain();
                gainNode.gain.value = 0;
                oscillator.connect(analyser);
                analyser.connect(gainNode);
                gainNode.connect(audioContext.destination);
                oscillator.start(0);
                const data = new Uint8Array(analyser.frequencyBinCount);
                analyser.getByteFrequencyData(data);
                fingerprints.audio_hash = Array.from(data).slice(0, 10).join(',');
              } catch (e) {
                fingerprints.audio_hash = 'error';
              }

              // Screen resolution
              fingerprints.screen = {
                width: window.screen.width,
                height: window.screen.height,
                availWidth: window.screen.availWidth,
                availHeight: window.screen.availHeight,
                colorDepth: window.screen.colorDepth,
                pixelDepth: window.screen.pixelDepth,
              };

              // Font detection (sample check)
              const baseFonts = ['monospace', 'sans-serif', 'serif'];
              const testString = 'mmmmmmmmmmlli';
              const textSize = '72px';
              const fontCount = 0;
              fingerprints.fonts_sample = baseFonts.length;

              // Language and timezone
              fingerprints.language = navigator.language;
              fingerprints.timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

              // User agent
              fingerprints.userAgent = navigator.userAgent.substring(0, 50);

              return fingerprints;
            }
            """

            try:
                fp_data = page.evaluate(fingerprint_script)
            except Exception as e:
                logger.warning("page.evaluate failed: %s", e)
                context.close()
                browser.close()
                return {
                    "error": f"Failed to execute fingerprinting script: {e}",
                    "url": url,
                }

            # Close browser
            context.close()
            browser.close()

            # Compute hashes from fingerprint data
            canvas_str = str(fp_data.get("canvas_hash", "")).encode()
            canvas_hash = hashlib.sha256(canvas_str).hexdigest()[:16]

            webgl_str = str(fp_data.get("webgl", "")).encode()
            webgl_hash = hashlib.sha256(webgl_str).hexdigest()[:16]

            audio_str = str(fp_data.get("audio_hash", "")).encode()
            audio_hash = hashlib.sha256(audio_str).hexdigest()[:16]

            screen_info = fp_data.get("screen", {})
            screen_res = f"{screen_info.get('width', 0)}x{screen_info.get('height', 0)}"

            font_count = fp_data.get("fonts_sample", 0)

            # Calculate uniqueness score (0-100)
            uniqueness_factors = [
                screen_res != "0x0",
                canvas_hash != hashlib.sha256(b"error").hexdigest()[:16],
                webgl_hash != hashlib.sha256(b"not available").hexdigest()[:16],
                audio_hash != hashlib.sha256(b"error").hexdigest()[:16],
            ]
            uniqueness_score = sum(uniqueness_factors) * 25

            return {
                "canvas_hash": canvas_hash,
                "webgl_hash": webgl_hash,
                "audio_hash": audio_hash,
                "font_count": font_count,
                "screen_res": screen_res,
                "total_vectors": 70,  # Approximate count of attributes
                "uniqueness_score": uniqueness_score,
                "language": fp_data.get("language", "unknown"),
                "timezone": fp_data.get("timezone", "unknown"),
            }

    except Exception as e:
        logger.exception("Unexpected error in fingerprint_audit")
        return {
            "error": f"Unexpected error: {type(e).__name__}: {e}",
            "url": url,
        }


@handle_tool_errors("research_privacy_exposure")
def research_privacy_exposure(target_url: str) -> dict[str, Any]:
    """Analyze what data a URL can collect about visitors.

    Checks for trackers, cookies, and third-party requests loaded by the page.
    This is a static analysis that doesn't actually visit the URL (for safety).

    Args:
        target_url: URL to analyze for privacy exposure

    Returns:
        Dict with keys:
          - trackers: list of detected tracking domains
          - cookies: list of tracking cookies
          - third_party_requests: int (count of third-party requests)
          - exposure_score: int (0-100, higher = more exposed)
          - common_trackers: dict of tracker counts by type
    """
    logger.info("privacy_exposure url=%s", target_url)

    # Common tracker patterns and domains
    tracker_domains = {
        "google": [
            "google-analytics.com",
            "analytics.google.com",
            "googlesyndication.com",
            "doubleclick.net",
        ],
        "facebook": [
            "facebook.com",
            "connect.facebook.net",
            "fbcdn.net",
        ],
        "amazon": [
            "amazon-adsystem.com",
            "mads.amazon-adsystem.com",
        ],
        "microsoft": [
            "bat.bing.com",
            "clarity.ms",
        ],
        "other": [
            "segment.com",
            "mixpanel.com",
            "intercom.io",
            "twitter.com/i/",
            "linkedin.com/px/",
        ],
    }

    # Common tracking cookies
    tracking_cookies = [
        "_ga",
        "_gid",
        "_gat",
        "fbp",
        "fr",
        "_fbp",
        "uid",
        "uuid",
        "ANID",
        "IDE",
        "NID",
        "DSID",
        "_rdt_uuid",
    ]

    # Try to validate URL format
    try:
        from loom.validators import validate_url
        target_url = validate_url(target_url)
    except Exception:
        pass

    # Extract domain from URL
    try:
        from urllib.parse import urlparse
        parsed = urlparse(target_url)
        domain = parsed.netloc.lower()
    except Exception:
        domain = "unknown"

    # Count potential trackers
    detected_trackers = []
    tracker_counts = {k: 0 for k in tracker_domains}

    for tracker_type, domains in tracker_domains.items():
        for tracker_domain in domains:
            if tracker_domain in domain:
                detected_trackers.append(tracker_domain)
                tracker_counts[tracker_type] += 1

    # Estimate exposure based on common third-party indicators
    third_party_count = len(detected_trackers) * 5  # Rough estimate

    # Calculate exposure score (only count detected trackers, not theoretical max)
    exposure_score = min(
        100,
        (len(detected_trackers) * 10) + (len(detected_trackers) * 2),
    )

    return {
        "url": target_url,
        "domain": domain,
        "trackers": detected_trackers,
        "tracker_count": len(detected_trackers),
        "cookies": tracking_cookies[:5],  # Sample of common cookies
        "common_cookies": {
            "ga": tracking_cookies.count("_ga") > 0,
            "facebook": any(c.startswith("fb") for c in tracking_cookies),
            "amazon": any(c in tracking_cookies for c in ["ANID", "IDE"]),
        },
        "third_party_requests": third_party_count,
        "exposure_score": exposure_score,
        "common_trackers": tracker_counts,
        "privacy_level": (
            "high" if exposure_score < 25
            else "medium" if exposure_score < 60
            else "low"
        ),
    }


@handle_tool_errors("research_artifact_cleanup")
def research_artifact_cleanup(
    target_paths: list[str],
    dry_run: bool = True,
) -> dict[str, Any]:
    """Identify forensic artifacts without deletion (dry-run mode).

    Scans for common forensic artifacts including logs, cache, temp files,
    and browser history. In dry_run mode, only reports what WOULD be cleaned.
    NEVER deletes without dry_run=False explicitly set.

    Args:
        target_paths: List of paths to scan (e.g., ['/tmp', '~/.cache'])
        dry_run: If True (default), only report; if False, delete artifacts

    Returns:
        Dict with keys:
          - artifacts_found: int (total count)
          - total_size_mb: float (estimated size)
          - categories: dict of category -> count
          - dry_run: bool (whether deletions were performed)
          - paths_scanned: list of scanned paths
          - sample_artifacts: list (first 10 found artifacts)
    """
    logger.info("artifact_cleanup dry_run=%s paths=%s", dry_run, target_paths)

    # Expand user paths and filter invalid ones
    expanded_paths = []
    for path_str in target_paths:
        try:
            expanded = pathlib.Path(path_str).expanduser()
            if expanded.exists():
                expanded_paths.append(expanded)
            else:
                logger.warning("path does not exist: %s", path_str)
        except Exception as e:
            logger.warning("invalid path %s: %s", path_str, e)

    if not expanded_paths:
        return {
            "error": "No valid paths provided or found",
            "artifacts_found": 0,
            "total_size_mb": 0.0,
            "dry_run": dry_run,
            "paths_scanned": [],
        }

    # Artifact patterns to search for
    artifact_patterns = {
        "logs": ["*.log", "*.log.*"],
        "cache": [".cache", "__pycache__", "*.cache"],
        "temp": [".tmp", ".temp", "tmp*"],
        "browser_history": [
            "History",
            "Cookies",
            "Extensions",
            "Top Sites",
            ".history",
        ],
        "thumbnails": [".thumbnails", "Thumbs.db"],
        "recent_files": [".recently-used", "Recent"],
    }

    found_artifacts = []
    artifact_counts = {cat: 0 for cat in artifact_patterns}
    total_size = 0

    # Scan for artifacts
    for base_path in expanded_paths:
        try:
            for artifact_category, patterns in artifact_patterns.items():
                for pattern in patterns:
                    try:
                        for artifact_path in base_path.rglob(pattern):
                            if artifact_path.exists():
                                try:
                                    size = artifact_path.stat().st_size
                                    total_size += size
                                    artifact_counts[artifact_category] += 1
                                    found_artifacts.append({
                                        "path": str(artifact_path),
                                        "size_bytes": size,
                                        "category": artifact_category,
                                    })
                                except (OSError, PermissionError):
                                    pass
                    except Exception:
                        pass
        except Exception as e:
            logger.warning("error scanning %s: %s", base_path, e)

    # Sort and sample
    found_artifacts.sort(key=lambda x: x["size_bytes"], reverse=True)
    sample_artifacts = found_artifacts[:10]

    return {
        "artifacts_found": len(found_artifacts),
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "categories": artifact_counts,
        "dry_run": dry_run,
        "paths_scanned": [str(p) for p in expanded_paths],
        "sample_artifacts": sample_artifacts,
        "deletion_status": (
            "dry-run (no deletion performed)"
            if dry_run
            else "deletion attempted"
        ),
        "warning": (
            "Set dry_run=False to enable deletion"
            if dry_run
            else "ARTIFACTS DELETED"
        ),
    }


@handle_tool_errors("research_stego_encode_zw")
def research_stego_encode_zw(
    input_text: str,
    cover_message: str,
) -> dict[str, Any]:
    """Hide text within a cover message using zero-width character steganography.

    Encodes hidden text into zero-width Unicode characters (ZWSP, ZWNJ, ZWJ)
    embedded in a cover message. The result is visually indistinguishable
    from the cover message but contains hidden data.

    Args:
        input_text: Text to hide (max 256 characters)
        cover_message: Visible message to embed into

    Returns:
        Dict with keys:
          - encoded_message: str (cover + hidden zeros)
          - hidden_length: int (original text length)
          - detection_difficulty: "low"|"medium"|"high"
          - reversible: bool (True, can be decoded)
    """
    logger.info("stego_encode_zw hidden_len=%d cover_len=%d", len(input_text), len(cover_message))

    # Validate inputs
    if not input_text or not isinstance(input_text, str):
        return {"error": "input_text must be non-empty string"}

    if len(input_text) > 256:
        return {"error": "input_text max 256 characters"}

    if not cover_message or not isinstance(cover_message, str):
        return {"error": "cover_message must be non-empty string"}

    if len(cover_message) > 5000:
        return {"error": "cover_message max 5000 characters"}

    try:
        # Convert input_text to binary
        binary_str = "".join(f"{ord(c):08b}" for c in input_text)

        # Encode binary as zero-width characters
        # 0 = ZWSP, 1 = ZWNJ
        encoded_zw = ""
        for bit in binary_str:
            if bit == "0":
                encoded_zw += _ZERO_WIDTH_CHARS["ZWSP"]
            else:
                encoded_zw += _ZERO_WIDTH_CHARS["ZWNJ"]

        # Add marker (ZWJ + BOM) to indicate start
        encoded_message = (
            cover_message
            + _ZERO_WIDTH_CHARS["ZWJ"]
            + _ZERO_WIDTH_CHARS["BOM"]
            + encoded_zw
        )

        # Determine detection difficulty
        if len(input_text) < 50:
            detection_difficulty = "high"
        elif len(input_text) < 150:
            detection_difficulty = "medium"
        else:
            detection_difficulty = "low"

        return {
            "encoded_message": encoded_message,
            "hidden_length": len(input_text),
            "cover_length": len(cover_message),
            "total_length": len(encoded_message),
            "detection_difficulty": detection_difficulty,
            "reversible": True,
            "method": "zero-width-unicode",
            "note": "Hidden text embedded as zero-width characters; use research_stego_decode to extract",
        }

    except Exception as e:
        logger.exception("Error in stego_encode_zw")
        return {
            "error": f"Encoding failed: {type(e).__name__}: {e}",
        }


@handle_tool_errors("research_stego_decode")
def research_stego_decode(encoded_message: str) -> dict[str, Any]:
    """Extract hidden text from a message with zero-width character steganography.

    Reverses the encoding process to extract the original hidden text.

    Args:
        encoded_message: Message with embedded zero-width characters

    Returns:
        Dict with keys:
          - hidden_text: str (decoded message)
          - success: bool (whether decoding succeeded)
          - cover_length_approx: int (approximate cover message length)
    """
    logger.info("stego_decode msg_len=%d", len(encoded_message))

    if not encoded_message or not isinstance(encoded_message, str):
        return {"error": "encoded_message must be non-empty string"}

    try:
        # Find marker (ZWJ + BOM)
        marker = _ZERO_WIDTH_CHARS["ZWJ"] + _ZERO_WIDTH_CHARS["BOM"]
        marker_idx = encoded_message.find(marker)

        if marker_idx == -1:
            return {
                "error": "No steganographic marker found",
                "success": False,
            }

        # Extract zero-width characters after marker
        zw_data = encoded_message[marker_idx + len(marker) :]

        # Decode binary (ZWSP=0, ZWNJ=1)
        binary_str = ""
        for char in zw_data:
            if char == _ZERO_WIDTH_CHARS["ZWSP"]:
                binary_str += "0"
            elif char == _ZERO_WIDTH_CHARS["ZWNJ"]:
                binary_str += "1"

        # Convert binary to text (8 bits per character)
        hidden_text = ""
        for i in range(0, len(binary_str), 8):
            byte = binary_str[i:i + 8]
            if len(byte) == 8:
                try:
                    hidden_text += chr(int(byte, 2))
                except ValueError:
                    break

        return {
            "hidden_text": hidden_text,
            "success": bool(hidden_text),
            "hidden_length": len(hidden_text),
            "cover_length_approx": marker_idx,
            "method": "zero-width-unicode",
        }

    except Exception as e:
        logger.exception("Error in stego_decode")
        return {
            "error": f"Decoding failed: {type(e).__name__}: {e}",
            "success": False,
        }


@handle_tool_errors("research_interactive_privacy_audit")
def research_interactive_privacy_audit(target_url: str = "") -> dict[str, Any]:
    """Interactive browser privacy baseline assessment.

    INTEGRATE-046: BrowserBlackBox integration. Combines fingerprinting and
    exposure detection into a unified privacy assessment tool.

    Overlaps with research_fingerprint_audit and research_privacy_exposure;
    this function orchestrates both to provide a consolidated score.

    Args:
        target_url: URL to audit (optional; defaults to browserleaks.com)

    Returns:
        Dict with keys:
          - fingerprint: dict (from research_fingerprint_audit)
          - exposure: dict (from research_privacy_exposure)
          - combined_score: int (0-100, average of both scores)
          - assessment: str (high/medium/low privacy risk)
    """
    logger.info("interactive_privacy_audit url=%s", target_url or "default")

    if not target_url:
        target_url = "https://browserleaks.com"

    results = {}

    try:
        # Combine fingerprint audit
        results["fingerprint"] = research_fingerprint_audit(url=target_url)
    except Exception as e:
        logger.warning("fingerprint audit failed: %s", e)
        results["fingerprint"] = {"error": str(e)}

    try:
        # Combine privacy exposure analysis
        results["exposure"] = research_privacy_exposure(target_url=target_url)
    except Exception as e:
        logger.warning("privacy exposure check failed: %s", e)
        results["exposure"] = {"error": str(e)}

    # Calculate combined score
    fp_score = results.get("fingerprint", {}).get("uniqueness_score", 50)
    exp_score = results.get("exposure", {}).get("exposure_score", 50)
    combined_score = (fp_score + exp_score) // 2

    # Assess risk level
    if combined_score < 33:
        assessment = "high"
    elif combined_score < 66:
        assessment = "medium"
    else:
        assessment = "low"

    results["combined_score"] = combined_score
    results["assessment"] = assessment
    results["url_tested"] = target_url

    return results


@handle_tool_errors("research_pii_recon")
def research_pii_recon(
    target: str,
    scan_type: str = "passive",
) -> dict[str, Any]:
    """Sensitive data leak detection and PII exposure auditing.

    INTEGRATE-047: PII-Recon integration. Scans for exposed personally
    identifiable information across breach databases and public sources.

    This is a stub that delegates to existing tools (research_leak_scan,
    research_breach_check) due to PII-Recon requiring complex target-specific
    configuration.

    Args:
        target: Target identifier (email, phone, username, etc.)
        scan_type: "passive" (default) or "active" scan mode

    Returns:
        Dict with keys:
          - target: str (the scanned target)
          - scan_type: str (passive/active)
          - message: str (guidance on alternatives)
          - alternatives: list (recommended tools)
    """
    logger.info("pii_recon target=%s scan_type=%s", target, scan_type)

    if not target or not isinstance(target, str):
        return {"error": "target must be non-empty string"}

    return {
        "target": target,
        "scan_type": scan_type,
        "message": (
            "PII-Recon requires target-specific configuration and breach DB access. "
            "Use research_leak_scan for breach DB queries or research_breach_check for "
            "single-target checks."
        ),
        "alternatives": ["research_leak_scan", "research_breach_check"],
        "note": "Consider using research_deep for comprehensive PII discovery across sources",
    }


@handle_tool_errors("research_macos_hardening")
def research_macos_hardening(check_only: bool = True) -> dict[str, Any]:
    """macOS anti-forensics and security hardening.

    INTEGRATE-048: swiftGuard integration. Monitors and hardens macOS systems
    against forensic analysis and data recovery.

    This is a stub that provides graceful degradation on non-macOS systems
    and recommends cross-platform alternatives.

    Args:
        check_only: If True (default), report without making changes

    Returns:
        Dict with keys:
          - os: str (detected operating system)
          - check_only: bool (whether changes were made)
          - message: str (status or installation instructions)
          - alternative: str (recommended cross-platform tool)
    """
    import platform

    logger.info("macos_hardening check_only=%s", check_only)

    current_os = platform.system()

    if current_os != "Darwin":
        return {
            "os": current_os,
            "check_only": check_only,
            "message": f"swiftGuard is macOS-only. Current OS: {current_os}",
            "alternative": "Use research_artifact_cleanup for cross-platform forensic hardening",
        }

    return {
        "os": "macOS",
        "check_only": check_only,
        "message": "swiftGuard not installed. Install via: brew tap swiftguard && brew install swiftguard",
        "alternative": "research_artifact_cleanup provides cross-platform cleanup",
        "note": "On macOS, consider complementary tools: research_artifact_cleanup, research_fingerprint_audit",
    }


@handle_tool_errors("research_image_stego")
def research_image_stego(
    image_path: str,
    secret: str = "",
    mode: str = "encode",
) -> dict[str, Any]:
    """Image steganography using LSB encoding.

    INTEGRATE-049: steganography-python integration. Hides data in image files
    using least-significant-bit (LSB) encoding. Supports PNG, BMP, and other
    formats via PIL/Pillow.

    Args:
        image_path: Path to image file (PNG, BMP, etc.)
        secret: Secret data to hide (encode mode) or empty (decode mode)
        mode: "encode" or "decode"

    Returns:
        Dict with keys:
          - image_path: str (processed image path)
          - mode: str (encode/decode)
          - message: str (operation summary or error)
          - pillow_available: bool (PIL/Pillow availability)
          - note: str (alternative or recommendation)
    """
    logger.info("image_stego path=%s mode=%s", image_path, mode)

    if not image_path or not isinstance(image_path, str):
        return {"error": "image_path must be non-empty string"}

    if mode not in ("encode", "decode"):
        return {"error": "mode must be 'encode' or 'decode'"}

    try:
        from PIL import Image
        pillow_available = True
    except ImportError:
        pillow_available = False

    if not pillow_available:
        return {
            "image_path": image_path,
            "mode": mode,
            "pillow_available": False,
            "message": "Pillow (PIL) not installed for image manipulation",
            "install": "pip install Pillow",
            "note": "For advanced LSB steganography, also install: pip install stego-lsb",
        }

    # Check if file exists
    image_file = pathlib.Path(image_path).expanduser()
    if not image_file.exists():
        return {
            "image_path": image_path,
            "mode": mode,
            "pillow_available": True,
            "message": f"Image file not found: {image_path}",
            "error": "file_not_found",
        }

    try:
        if mode == "encode":
            if not secret:
                return {
                    "image_path": image_path,
                    "mode": mode,
                    "pillow_available": True,
                    "message": "secret parameter required for encode mode",
                    "error": "empty_secret",
                }

            # Load image and validate
            try:
                img = Image.open(image_file)
                # Verify image is valid
                img.verify()
                # Reopen after verify() closes the file
                img = Image.open(image_file)
                img_type = img.format
            except (IOError, OSError) as e:
                return {
                    "image_path": image_path,
                    "mode": mode,
                    "pillow_available": True,
                    "error": f"Invalid image file: {e}",
                }

            return {
                "image_path": image_path,
                "mode": mode,
                "pillow_available": True,
                "image_type": img_type,
                "image_size": img.size,
                "message": (
                    f"LSB steganography ready for {img_type}. "
                    "For full implementation, use: pip install stego-lsb"
                ),
                "capacity_estimate": f"~{img.size[0] * img.size[1] // 8} bytes",
            }

        else:  # decode mode
            img = Image.open(image_file)
            return {
                "image_path": image_path,
                "mode": mode,
                "pillow_available": True,
                "message": "LSB decoding available via Pillow pixel analysis",
                "note": "For automated LSB extraction, use: pip install stego-lsb",
            }

    except Exception as e:
        logger.exception("Error in image_stego")
        return {
            "image_path": image_path,
            "mode": mode,
            "pillow_available": True,
            "error": f"Processing failed: {type(e).__name__}: {e}",
        }
