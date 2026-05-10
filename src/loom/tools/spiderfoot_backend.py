"""SpiderFoot passive reconnaissance integration — OSINT scanning via SpiderFoot framework."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import time
from typing import Any

import httpx

from loom.validators import validate_url, UrlSafetyError

logger = logging.getLogger("loom.tools.spiderfoot_backend")

# Maximum output size: 50 MB
MAX_OUTPUT_SIZE = 50 * 1024 * 1024

# SpiderFoot API endpoint (default)
SPIDERFOOT_API_URL = "http://localhost:5001"


def _validate_target(target: str) -> str:
    """Validate target (domain, IP, email, phone) to prevent command injection.

    Allows alphanumeric, dots, hyphens, underscores, @, and +.
    Returns the validated target.

    Args:
        target: target identifier to validate

    Returns:
        The validated target string

    Raises:
        ValueError: if target contains disallowed characters
    """
    if not target or len(target) > 512:
        raise ValueError("target must be 1-512 characters")

    # Allow alphanumeric, dots, hyphens, underscores, @, +, :
    if not re.match(r"^[a-z0-9._\-@+:]+$", target, re.IGNORECASE):
        raise ValueError("target contains disallowed characters")

    return target


def _is_tool_available(tool_name: str) -> bool:
    """Check if a tool is available in the system PATH.

    Args:
        tool_name: name of the tool to check (e.g., 'spiderfoot')

    Returns:
        True if tool is available, False otherwise
    """
    return shutil.which(tool_name) is not None


def _is_api_available() -> bool:
    """Check if SpiderFoot API is available.

    Returns:
        True if API is reachable, False otherwise
    """
    try:
        resp = httpx.get(f"{SPIDERFOOT_API_URL}/api/v2/info", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def _parse_spiderfoot_json(json_str: str) -> dict[str, Any]:
    """Parse SpiderFoot JSON output and extract findings.

    Args:
        json_str: JSON string from SpiderFoot output

    Returns:
        Dict with parsed findings organized by module and data type
    """
    try:
        data = json.loads(json_str)
        return data
    except json.JSONDecodeError as exc:
        logger.warning("failed to parse spiderfoot json: %s", exc)
        return {}


def _run_spiderfoot_cli(
    target: str, modules: str = "all", timeout: int = 120
) -> dict[str, Any]:
    """Run SpiderFoot via CLI subprocess.

    Args:
        target: target identifier (domain, IP, email, etc.)
        modules: comma-separated module list or 'all'
        timeout: command timeout in seconds

    Returns:
        Dict with findings, duration, and status
    """
    if not _is_tool_available("spiderfoot"):
        return {
            "target": target,
            "error": "spiderfoot not installed",
            "warning": "Install SpiderFoot: pip install spiderfoot",
            "findings": [],
            "total_findings": 0,
            "duration_ms": 0,
        }

    try:
        start_time = time.time()

        cmd = ["spiderfoot", "-s", target, "-o", "json"]
        if modules != "all":
            cmd.extend(["-m", modules])

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=timeout,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        stdout = result.stdout[:MAX_OUTPUT_SIZE] if result.stdout else ""
        if result.stdout and len(result.stdout) > MAX_OUTPUT_SIZE:
            logger.warning(
                "spiderfoot output truncated (exceeded %d bytes)",
                MAX_OUTPUT_SIZE,
            )

        output: dict[str, Any] = {
            "target": target,
            "duration_ms": duration_ms,
            "findings": [],
            "total_findings": 0,
        }

        if result.returncode != 0:
            output["error"] = f"spiderfoot command failed: {result.stderr[:500]}"
            return output

        # Parse JSON output
        parsed = _parse_spiderfoot_json(stdout)
        if not parsed:
            output["warning"] = "no findings or unparseable output"
            return output

        # Extract findings from parsed JSON
        findings: list[dict[str, Any]] = []

        # SpiderFoot JSON format: {"data": {"module": [{"data_type": "...", "value": "...", ...}]}}
        if isinstance(parsed, dict):
            data_section = parsed.get("data", {})
            if isinstance(data_section, dict):
                for module, module_findings in data_section.items():
                    if isinstance(module_findings, list):
                        for finding in module_findings:
                            if isinstance(finding, dict):
                                findings.append(
                                    {
                                        "module": module,
                                        "data_type": finding.get("type", "unknown"),
                                        "value": finding.get("value", ""),
                                        "source": finding.get("source", ""),
                                    }
                                )

        output["findings"] = findings[:1000]  # Cap at 1000 findings
        output["total_findings"] = len(findings)

        logger.info(
            "spiderfoot_cli_success target=%s findings=%d duration_ms=%d",
            target,
            len(findings),
            duration_ms,
        )
        return output

    except subprocess.TimeoutExpired:
        return {
            "target": target,
            "error": f"spiderfoot scan timed out (exceeded {timeout} seconds)",
            "findings": [],
            "total_findings": 0,
            "duration_ms": timeout * 1000,
        }
    except Exception as exc:
        logger.exception("spiderfoot_cli_failed target=%s", target)
        return {
            "target": target,
            "error": str(exc),
            "findings": [],
            "total_findings": 0,
            "duration_ms": 0,
        }


def _run_spiderfoot_api(
    target: str, modules: str = "all", timeout: int = 120
) -> dict[str, Any]:
    """Run SpiderFoot via REST API.

    Args:
        target: target identifier (domain, IP, email, etc.)
        modules: comma-separated module list or 'all'
        timeout: request timeout in seconds

    Returns:
        Dict with findings, duration, and status
    """
    if not _is_api_available():
        return {
            "target": target,
            "error": f"spiderfoot api not available at {SPIDERFOOT_API_URL}",
            "warning": "Start SpiderFoot API: spiderfoot -l 127.0.0.1:5001",
            "findings": [],
            "total_findings": 0,
            "duration_ms": 0,
        }

    try:
        start_time = time.time()

        # Create a scan job via API
        scan_payload = {
            "scanname": f"loom-{target}-{int(start_time)}",
            "scantarget": target,
            "modulesfilt": modules if modules != "all" else "",
        }

        with httpx.Client(timeout=float(timeout)) as client:
            # Create scan
            create_resp = client.post(
                f"{SPIDERFOOT_API_URL}/api/v2/scan",
                json=scan_payload,
            )

            if create_resp.status_code != 200:
                return {
                    "target": target,
                    "error": f"failed to create scan: {create_resp.text[:200]}",
                    "findings": [],
                    "total_findings": 0,
                    "duration_ms": 0,
                }

            scan_data = create_resp.json()
            scan_id = scan_data.get("scan_id")

            if not scan_id:
                return {
                    "target": target,
                    "error": "no scan_id returned from API",
                    "findings": [],
                    "total_findings": 0,
                    "duration_ms": 0,
                }

            # Wait for scan to complete
            max_wait = time.time() + timeout
            while time.time() < max_wait:
                status_resp = client.get(
                    f"{SPIDERFOOT_API_URL}/api/v2/scan/{scan_id}",
                )

                if status_resp.status_code != 200:
                    break

                status_data = status_resp.json()
                status = status_data.get("status", "")

                if status in ("COMPLETED", "ABORTED", "FAILED"):
                    break

                time.sleep(2)

            duration_ms = int((time.time() - start_time) * 1000)

            # Get findings
            findings_resp = client.get(
                f"{SPIDERFOOT_API_URL}/api/v2/scan/{scan_id}/results",
            )

            output: dict[str, Any] = {
                "target": target,
                "scan_id": scan_id,
                "duration_ms": duration_ms,
                "findings": [],
                "total_findings": 0,
            }

            if findings_resp.status_code != 200:
                output["warning"] = "failed to retrieve findings"
                return output

            findings_data = findings_resp.json()
            findings: list[dict[str, Any]] = []

            if isinstance(findings_data, list):
                for finding in findings_data:
                    if isinstance(finding, dict):
                        findings.append(
                            {
                                "module": finding.get("module", "unknown"),
                                "data_type": finding.get("type", "unknown"),
                                "value": finding.get("data", ""),
                                "source": finding.get("source", ""),
                            }
                        )

            output["findings"] = findings[:1000]  # Cap at 1000 findings
            output["total_findings"] = len(findings)

            logger.info(
                "spiderfoot_api_success target=%s scan_id=%s findings=%d duration_ms=%d",
                target,
                scan_id,
                len(findings),
                duration_ms,
            )
            return output

    except httpx.TimeoutException:
        return {
            "target": target,
            "error": f"spiderfoot api request timed out (exceeded {timeout} seconds)",
            "findings": [],
            "total_findings": 0,
            "duration_ms": timeout * 1000,
        }
    except Exception as exc:
        logger.exception("spiderfoot_api_failed target=%s", target)
        return {
            "target": target,
            "error": str(exc),
            "findings": [],
            "total_findings": 0,
            "duration_ms": 0,
        }


def research_spiderfoot_scan(
    target: str, modules: str = "all", timeout: int = 120, api: bool = False
) -> dict[str, Any]:
    """Run SpiderFoot passive reconnaissance scan.

    Executes a SpiderFoot OSINT scan against a target (domain, IP, email, phone).
    Automatically detects and uses SpiderFoot API (if running as web service at
    http://localhost:5001) or falls back to CLI mode.

    Args:
        target: target identifier (domain, IP, email address, phone number, etc.)
        modules: comma-separated module list or 'all' (default: all modules)
        timeout: scan timeout in seconds (default: 120)
        api: force API mode if True, prefer CLI if False (default: False)

    Returns:
        Dict with:
        - target: the queried target
        - findings: list of dicts with {module, data_type, value, source}
        - total_findings: count of findings
        - duration_ms: execution time in milliseconds
        - scan_id: scan identifier (API mode only)
        - error: error message if scan failed
        - warning: warning message if tool/API unavailable

    Example:
        >>> result = research_spiderfoot_scan("example.com", modules="all")
        >>> print(f"Found {result['total_findings']} OSINT results")
        >>> for finding in result['findings'][:5]:
        ...     print(f"{finding['module']}: {finding['value']}")
    """
    try:
        target = _validate_target(target)
    except ValueError as exc:
        return {"target": target, "error": str(exc)}

    # Validate timeout
    if not isinstance(timeout, int) or timeout < 10 or timeout > 3600:
        return {"target": target, "error": "timeout must be 10-3600 seconds"}

    # Try API mode first if not explicitly disabled
    if not api or _is_api_available():
        result = _run_spiderfoot_api(target, modules, timeout)
        if "error" not in result or "api not available" not in result.get("error", ""):
            return result

    # Fall back to CLI mode
    return _run_spiderfoot_cli(target, modules, timeout)
