"""SpiderFoot passive reconnaissance integration — OSINT scanning via SpiderFoot framework."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import time
from typing import Any
import httpx

from loom.error_responses import handle_tool_errors
from loom.validators import validate_url, UrlSafetyError
from loom.cli_checker import is_available

try:
    from loom.text_utils import truncate
except ImportError:
    def truncate(text, max_chars=500, *, suffix="..."):
        if len(text) <= max_chars: return text
        return text[:max_chars - len(suffix)] + suffix

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
    return is_available(tool_name)


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

        stdout = truncate(result.stdout, MAX_OUTPUT_SIZE) if result.stdout else ""
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
            output["error"] = f"spiderfoot command failed: {truncate(result.stderr, 500)}"
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
                    "error": f"failed to create scan: {truncate(create_resp.text, 200)}",
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
                output["error"] = f"failed to fetch results: {findings_resp.status_code}"
                return output

            findings_data = findings_resp.json()
            if isinstance(findings_data, list):
                findings = findings_data[:1000]
                output["findings"] = findings
                output["total_findings"] = len(findings)
            else:
                output["warning"] = "unexpected findings format"

            logger.info(
                "spiderfoot_api_success target=%s findings=%d duration_ms=%d",
                target,
                output["total_findings"],
                duration_ms,
            )
            return output

    except httpx.RequestError as exc:
        logger.exception("spiderfoot_api_failed target=%s", target)
        return {
            "target": target,
            "error": str(exc),
            "findings": [],
            "total_findings": 0,
            "duration_ms": 0,
        }


@handle_tool_errors("research_spiderfoot")
async def research_spiderfoot(
    target: str,
    modules: str = "all",
    use_api: bool = False,
    timeout: int = 120,
) -> dict[str, Any]:
    """Run SpiderFoot passive reconnaissance scan on target.

    Args:
        target: target identifier (domain, IP, email, phone, etc.)
        modules: comma-separated SpiderFoot modules or 'all' (default)
        use_api: use REST API instead of CLI (default: False)
        timeout: scan timeout in seconds (default: 120)

    Returns:
        Dict with findings, total_findings, duration_ms, error (if any)
    """
    try:
        _validate_target(target)
    except ValueError as exc:
        return {"error": str(exc), "findings": [], "total_findings": 0}

    import asyncio
    loop = asyncio.get_event_loop()

    if use_api:
        result = await loop.run_in_executor(
            None, _run_spiderfoot_api, target, modules, timeout
        )
    else:
        result = await loop.run_in_executor(
            None, _run_spiderfoot_cli, target, modules, timeout
        )

    return result
