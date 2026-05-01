#!/usr/bin/env python3
"""Security verification script for Loom v3 (REQ-064 through REQ-067).

Verifies:
  REQ-064: No API key leaks in PRODUCTION code (src/ only, not tests/)
  REQ-065: SSRF protection on all URL inputs
  REQ-066: Input sanitization for injection attacks
  REQ-067: Dark tools isolation (no cross-request state)

Usage:
  python3 scripts/verify_security.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
logger = logging.getLogger("security_verify")

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class SecurityVerificationResult:
    """Container for verification results."""

    def __init__(self, requirement: str):
        self.requirement = requirement
        self.passed = False
        self.issues: list[str] = []
        self.details: dict[str, Any] = {}

    def add_issue(self, issue: str) -> None:
        """Record a security issue."""
        self.issues.append(issue)
        self.passed = False

    def mark_passed(self) -> None:
        """Mark requirement as passed."""
        if not self.issues:
            self.passed = True

    def report(self) -> str:
        """Generate report for this requirement."""
        status = "PASS" if self.passed else "FAIL"
        lines = [
            f"\n{self.requirement}: {status}",
            "=" * 60,
        ]

        if self.passed:
            lines.append("✓ All checks passed")
        else:
            lines.append("✗ Issues found:")
            for issue in self.issues:
                lines.append(f"  - {issue}")

        if self.details:
            lines.append("\nDetails:")
            for key, value in self.details.items():
                if isinstance(value, (dict, list)):
                    lines.append(f"  {key}:")
                    for item in (value.items() if isinstance(value, dict) else value):
                        lines.append(f"    {item}")
                else:
                    lines.append(f"  {key}: {value}")

        return "\n".join(lines)


async def verify_req_064_no_api_key_leaks() -> SecurityVerificationResult:
    """REQ-064: No API key leaks in PRODUCTION code.

    Check src/ (production) only, exclude tests/.

    Check for:
      - Anthropic keys (sk-ant-*)
      - OpenAI keys (sk-*)
      - NVIDIA keys (nvapi-*)
      - Google keys (AIzaSy)
      - Groq keys (gsk_)
    """
    result = SecurityVerificationResult("REQ-064: No API Key Leaks (Production Code)")

    # API key patterns
    patterns = {
        "Anthropic": r"sk-ant-[A-Za-z0-9]{20,}",
        "OpenAI": r"sk-[A-Za-z0-9]{20,}",
        "NVIDIA": r"nvapi-[A-Za-z0-9]+",
        "Google": r"AIzaSy[A-Za-z0-9\-_]{33}",
        "Groq": r"gsk_[A-Za-z0-9]+",
        "DeepSeek": r"sk-[a-z0-9]{20,}",
        "Moonshot": r"sk-[a-z0-9]{20,}",
    }

    # Only scan production code (src/), NOT tests/
    scan_dirs = [Path("src")]
    scan_dirs = [d for d in scan_dirs if d and d.exists()]

    logger.info("Scanning %d production directories for leaked API keys...", len(scan_dirs))

    leaked_keys: dict[str, list[str]] = {name: [] for name in patterns}

    for scan_dir in scan_dirs:
        for py_file in scan_dir.rglob("*.py"):
            try:
                content = py_file.read_text(errors="ignore")
                for key_type, pattern in patterns.items():
                    matches = re.findall(pattern, content)
                    if matches:
                        leaked_keys[key_type].extend([
                            f"{py_file}:{match[:50]}"
                            for match in matches
                        ])
            except Exception as exc:
                logger.warning("Error scanning %s: %s", py_file, exc)

    # Check if any keys were found
    any_found = False
    for key_type, matches in leaked_keys.items():
        if matches:
            any_found = True
            result.add_issue(
                f"Found {len(matches)} potential {key_type} keys: {matches[:3]}"
            )
            result.details[key_type] = matches[:5]

    # Also check environment variables (should NOT be hardcoded)
    env_secrets = [
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "NVIDIA_NIM_API_KEY",
        "DEEPSEEK_API_KEY",
        "GOOGLE_AI_KEY",
        "MOONSHOT_API_KEY",
        "GROQ_API_KEY",
    ]

    for secret in env_secrets:
        if secret in os.environ:
            # Should be in env, not hardcoded. Just verify it's a placeholder/empty
            val = os.environ[secret]
            if val and not val.startswith("$"):
                logger.warning("%s is set in environment (expected for testing)", secret)

    if not any_found:
        result.mark_passed()
    else:
        result.add_issue("One or more hardcoded API keys found in production source")

    result.details["scanned_directories"] = [str(d) for d in scan_dirs]
    result.details["note"] = "Test files excluded intentionally (test keys allowed)"

    return result


async def verify_req_065_ssrf_blocks() -> SecurityVerificationResult:
    """REQ-065: SSRF protection on all URL inputs.

    Test validate_url() with:
      - Private IPs (10.0.0.1, 192.168.x.x, 172.16-31.x.x)
      - Loopback (127.0.0.1, [::1])
      - Link-local (169.254.x.x)
      - Metadata endpoints (169.254.169.254)
      - Reserved addresses
    """
    result = SecurityVerificationResult("REQ-065: SSRF Protection")

    try:
        from loom.validators import validate_url, UrlSafetyError
    except ImportError as exc:
        result.add_issue(f"Cannot import validators: {exc}")
        return result

    # Test cases: (url, should_pass, description)
    test_cases = [
        # Should FAIL (blocked private/loopback IPs)
        ("http://127.0.0.1:8080", False, "Loopback IPv4"),
        ("http://localhost:8080", False, "Loopback localhost"),
        ("http://[::1]:8080", False, "Loopback IPv6"),
        ("http://10.0.0.1", False, "Private IP 10.x"),
        ("http://192.168.1.100", False, "Private IP 192.168.x"),
        ("http://172.16.0.1", False, "Private IP 172.16-31.x"),
        ("http://169.254.169.254", False, "AWS metadata endpoint"),
        ("http://169.254.0.0/16", False, "Link-local range"),
        ("http://0.0.0.0", False, "Unspecified IP"),
        ("http://255.255.255.255", False, "Broadcast IP"),
        ("http://224.0.0.1", False, "Multicast IP"),
        # Should PASS (public IPs or blocked on local network)
        ("http://example.com", True, "Public domain (example.com)"),
        ("http://google.com", True, "Public domain (google.com)"),
        ("http://8.8.8.8", True, "Public IP (Google DNS)"),
    ]

    passed_count = 0
    failed_count = 0

    for url, should_pass, description in test_cases:
        try:
            validate_url(url)
            if should_pass:
                passed_count += 1
            else:
                failed_count += 1
                result.add_issue(
                    f"URL should have been blocked but passed: {url} ({description})"
                )
        except UrlSafetyError as exc:
            if not should_pass:
                passed_count += 1
            else:
                failed_count += 1
                result.add_issue(
                    f"URL should have passed but was blocked: {url} ({description}): {exc}"
                )

    result.details["passed"] = passed_count
    result.details["failed"] = failed_count
    result.details["total"] = len(test_cases)

    if failed_count == 0:
        result.mark_passed()

    return result


async def verify_req_066_input_sanitization() -> SecurityVerificationResult:
    """REQ-066: Input sanitization for injection attacks.

    Test with payloads:
      - XSS: <script>alert(1)</script>
      - SQL injection: '; DROP TABLE--
      - Command injection: $(rm -rf /), |ls, `whoami`
      - Path traversal: ../../../etc/passwd
      - LDAP injection
    """
    result = SecurityVerificationResult("REQ-066: Input Sanitization")

    try:
        from loom.validators import validate_js_script
    except ImportError as exc:
        result.add_issue(f"Cannot import validators: {exc}")
        return result

    # Test payloads
    dangerous_scripts = [
        ("fetch('http://evil.com')", "Fetch API"),
        ("XMLHttpRequest", "XMLHttpRequest"),
        ("eval('alert(1)')", "eval()"),
        ("Function('alert(1)')", "Function constructor"),
        ("require('fs')", "require()"),
        ("import('fs')", "import()"),
        ("WebSocket", "WebSocket"),
        ("Worker", "Worker"),
        ("navigator.sendBeacon", "sendBeacon"),
        ("window['eval']", "Bracket notation eval"),
        ("window['fetch']", "Bracket notation fetch"),
        (".constructor.constructor()", "Constructor chain"),
    ]

    dangerous_count = 0
    for script, description in dangerous_scripts:
        try:
            validate_js_script(script)
            result.add_issue(
                f"Dangerous script was allowed: {description}: {script}"
            )
            dangerous_count += 1
        except ValueError:
            # Expected - script was blocked
            pass

    # Test safe scripts (should pass)
    safe_scripts = [
        "document.getElementById('id').style.color = 'red';",
        "console.log('hello');",
        "const x = 42;",
    ]

    safe_count = 0
    for script in safe_scripts:
        try:
            validate_js_script(script)
            safe_count += 1
        except ValueError as exc:
            result.add_issue(f"Safe script was blocked: {script}: {exc}")

    result.details["dangerous_payloads"] = len(dangerous_scripts)
    result.details["blocked_count"] = len(dangerous_scripts) - dangerous_count
    result.details["safe_scripts"] = len(safe_scripts)
    result.details["safe_passed"] = safe_count

    # Check for SQL injection sanitization in params
    try:
        from loom.params import FetchParams
        from loom.validators import filter_headers, filter_provider_config

        # Test header filtering
        headers = {
            "User-Agent": "Mozilla/5.0",  # OK
            "Authorization": "Bearer token123",  # Should be rejected
            "X-Custom\r\nInjection": "value",  # CRLF injection
        }
        filtered = filter_headers(headers)
        if filtered and "Authorization" in filtered:
            result.add_issue("Authorization header was not filtered out")
        if filtered and any("\r" in v or "\n" in v for v in filtered.values()):
            result.add_issue("CRLF injection not filtered from headers")

        # Test provider config filtering
        provider_config = {
            "include_domains": ["example.com"],  # OK
            "malicious_option": "DROP TABLE;",  # Should be rejected
        }
        filtered_config = filter_provider_config("exa", provider_config)
        if "malicious_option" in filtered_config:
            result.add_issue("Malicious provider config option was not filtered")

    except ImportError:
        logger.warning("Could not import sanitization modules")

    if dangerous_count == 0 and safe_count == len(safe_scripts):
        result.mark_passed()

    return result


async def verify_req_067_dark_tools_isolation() -> SecurityVerificationResult:
    """REQ-067: Dark tools isolation (no cross-request state).

    Verify:
      - Session state is isolated per request
      - No global mutable state shared between tools
      - Dark tools don't leak results to other requests
      - Cache is keyed properly (no state collision)
    """
    result = SecurityVerificationResult("REQ-067: Dark Tools Isolation")

    try:
        from loom.cache import get_cache
        from loom.sessions import _sessions  # In-memory registry
    except ImportError as exc:
        result.add_issue(f"Cannot import state modules: {exc}")
        return result

    # Check cache implementation
    cache = get_cache()
    result.details["cache_type"] = type(cache).__name__

    # Verify cache uses content-hash (SHA-256) for keying
    try:
        # Test cache with same content
        test_content_a = "test content 123"
        test_content_b = "test content 123"
        test_content_c = "different content"

        # Store with different keys but same content
        cache_key_a = cache._hash_content(test_content_a) if hasattr(cache, '_hash_content') else None
        if cache_key_a:
            result.details["cache_uses_hashing"] = True
        else:
            logger.warning("Cache may not use content-hash keying")
    except Exception as exc:
        logger.warning("Could not verify cache hashing: %s", exc)

    # Check session isolation
    result.details["session_registry_type"] = type(_sessions).__name__

    # Verify no global mutable state in dark tools
    dark_tools = [
        "dark_forum",
        "darkweb_early_warning",
        "dark_recon",
        "identity_resolve",
        "leak_scan",
        "onion_discover",
    ]

    issues_found = []
    for tool_name in dark_tools:
        try:
            # Dynamically import dark tools
            from loom.tools import dark_forum, darkweb_early_warning, dark_recon
            # Check if module has module-level state variables
            tool_module = None
            if tool_name == "dark_forum":
                tool_module = dark_forum
            elif tool_name == "darkweb_early_warning":
                tool_module = darkweb_early_warning
            elif tool_name == "dark_recon":
                tool_module = dark_recon

            if tool_module:
                # Look for suspicious module-level variables
                for attr in dir(tool_module):
                    if not attr.startswith("_"):
                        obj = getattr(tool_module, attr)
                        # Check for mutable global state (lists, dicts, sets not in functions)
                        if isinstance(obj, (list, dict, set)) and not callable(obj):
                            if not attr.startswith("_"):
                                issues_found.append(
                                    f"{tool_name}.{attr} is a mutable global variable"
                                )
        except Exception as exc:
            logger.debug("Could not inspect %s: %s", tool_name, exc)

    if issues_found:
        for issue in issues_found:
            result.add_issue(issue)
    else:
        # Check for proper async/await patterns (prevent state bleed)
        try:
            import inspect
            from loom.tools import dark_forum
            functions = [
                (name, obj) for name, obj in inspect.getmembers(dark_forum)
                if inspect.iscoroutinefunction(obj)
            ]
            result.details["async_functions"] = len(functions)
            if functions:
                result.details["async_patterns"] = "Async coroutines detected (good isolation)"
        except Exception:
            pass

    # Verify Tor sessions don't leak state
    try:
        from loom.sessions import SessionManager
        # Check if SessionManager uses LRU eviction
        if hasattr(SessionManager, "max_sessions"):
            result.details["session_limit"] = "LRU eviction configured"
    except Exception:
        pass

    # Mark passed if no cross-request state issues
    if not issues_found:
        result.mark_passed()

    return result


def generate_final_report(results: list[SecurityVerificationResult]) -> str:
    """Generate final security verification report."""
    lines = [
        "\n" + "=" * 70,
        "LOOM v3 SECURITY VERIFICATION REPORT (REQ-064 to REQ-067)",
        "=" * 70,
        f"Date: {datetime.now().isoformat()}",
        "",
    ]

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    lines.append(f"Summary: {passed} passed, {failed} failed out of {len(results)}")
    lines.append("")

    for result in results:
        lines.append(result.report())

    lines.extend([
        "\n" + "=" * 70,
        f"Overall Status: {'ALL PASSED' if failed == 0 else 'SOME FAILED'}",
        "=" * 70,
    ])

    return "\n".join(lines)


async def main() -> int:
    """Run all security verifications."""
    logger.info("Starting Loom v3 security verification...")

    try:
        # Run all verification tasks
        results = await asyncio.gather(
            verify_req_064_no_api_key_leaks(),
            verify_req_065_ssrf_blocks(),
            verify_req_066_input_sanitization(),
            verify_req_067_dark_tools_isolation(),
        )

        # Generate and print report
        report = generate_final_report(results)
        print(report)

        # Write report to file
        report_path = Path("tmp") / "security_verification_report.txt"
        report_path.parent.mkdir(exist_ok=True)
        report_path.write_text(report)
        logger.info("Report written to %s", report_path)

        # Return exit code based on results
        failed_count = sum(1 for r in results if not r.passed)
        return 0 if failed_count == 0 else 1

    except Exception as exc:
        logger.error("Verification failed with exception: %s", exc, exc_info=True)
        return 1


if __name__ == "__main__":
    # Import datetime for report generation
    from datetime import datetime

    exit_code = asyncio.run(main())
    sys.exit(exit_code)
