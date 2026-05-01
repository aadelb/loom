"""SpiderFoot OSINT backend — modular reconnaissance and footprinting.

SpiderFoot is a reconnaissance and footprinting tool that automates OSINT
data collection from 200+ data sources. This module provides a wrapper around
the SpiderFoot CLI with subprocess execution and output parsing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
import tempfile
import uuid
from typing import Any

logger = logging.getLogger("loom.tools.spiderfoot_backend")


def _validate_target(target: str) -> str:
    """Validate target (IP, domain, email, or username).

    Args:
        target: target to validate

    Returns:
        The validated target string

    Raises:
        ValueError: if target is invalid
    """
    target = target.strip() if isinstance(target, str) else ""

    if not target or len(target) > 255:
        raise ValueError("target must be 1-255 characters")

    # Allow IP addresses, domains, emails, usernames
    # Basic check: alphanumeric, dots, hyphens, underscores, @ symbol
    if not re.match(r"^[a-z0-9._\-@]+$", target, re.IGNORECASE):
        raise ValueError("target contains disallowed characters")

    return target


def _validate_scan_type(scan_type: str) -> str:
    """Validate scan type parameter.

    Args:
        scan_type: scan type (e.g., "passive", "all", "web", etc.)

    Returns:
        The validated scan type

    Raises:
        ValueError: if scan type is invalid
    """
    scan_type = scan_type.strip() if isinstance(scan_type, str) else ""

    if not scan_type or len(scan_type) > 100:
        raise ValueError("scan_type must be 1-100 characters")

    # Allow alphanumeric and underscores
    if not re.match(r"^[a-z0-9_-]+$", scan_type, re.IGNORECASE):
        raise ValueError("scan_type contains disallowed characters")

    return scan_type


def _validate_modules(modules: list[str] | None) -> list[str] | None:
    """Validate module list.

    Args:
        modules: list of module names to use

    Returns:
        The validated module list or None

    Raises:
        ValueError: if modules list is invalid
    """
    if modules is None:
        return None

    if not isinstance(modules, list):
        raise ValueError("modules must be a list of strings")

    if len(modules) > 100:
        raise ValueError("too many modules specified (max 100)")

    validated = []
    for mod in modules:
        mod = mod.strip() if isinstance(mod, str) else ""
        if not mod or len(mod) > 100:
            raise ValueError(f"invalid module name: {mod}")

        if not re.match(r"^[a-z0-9_-]+$", mod, re.IGNORECASE):
            raise ValueError(f"module name contains disallowed characters: {mod}")

        validated.append(mod)

    return validated if validated else None


def _check_spiderfoot_available() -> tuple[bool, str]:
    """Check if SpiderFoot CLI is available.

    Returns:
        Tuple of (available: bool, message: str)
    """
    try:
        # Try sf command (SpiderFoot CLI)
        result = subprocess.run(
            ["sf", "-h"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 or "usage" in result.stdout.lower():
            return True, "SpiderFoot CLI found"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    try:
        # Try spiderfoot command (alternative name)
        result = subprocess.run(
            ["spiderfoot", "-h"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 or "usage" in result.stdout.lower():
            return True, "SpiderFoot CLI found"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return False, (
        "SpiderFoot CLI not found. Install with: pip install spiderfoot"
    )


async def research_spiderfoot_scan(
    target: str,
    scan_type: str = "passive",
    modules: list[str] | None = None,
) -> dict[str, Any]:
    """Perform reconnaissance on a target using SpiderFoot.

    Runs a modular reconnaissance scan on the given target (IP, domain, email,
    or username) and returns findings from 200+ data sources.

    Args:
        target: target to scan (IP address, domain, email, or username)
        scan_type: type of scan - "passive" (default), "web", "dns", "mail", etc.
        modules: optional list of specific modules to run. If None, uses default modules.

    Returns:
        Dict with:
        - target: the scanned target
        - scan_type: the type of scan performed
        - modules_run: list of modules that were executed
        - findings: list of findings from the scan
        - total_findings: count of findings discovered
        - categories: dict mapping finding categories to counts
        - spiderfoot_available: bool indicating if SpiderFoot CLI is available
        - error: error message if scan failed (optional)
    """
    try:
        target = _validate_target(target)
        scan_type = _validate_scan_type(scan_type)
        modules = _validate_modules(modules)
    except ValueError as exc:
        return {
            "target": target,
            "error": str(exc),
            "spiderfoot_available": False,
        }

    # Check if spiderfoot is available
    available, msg = _check_spiderfoot_available()
    if not available:
        return {
            "target": target,
            "error": msg,
            "spiderfoot_available": False,
        }

    try:
        # Create temp file for JSON output
        output_file = f"/tmp/spiderfoot_{uuid.uuid4().hex}.json"

        # Determine which binary to use
        binary = "sf"  # Try sf first, subprocess will fail if not available

        # Build spiderfoot command
        cmd = [
            binary,
            "-s",
            target,
            "-t",
            scan_type,
            "-o",
            "json",
            "-f",
            output_file,
        ]

        # Add specific modules if provided
        if modules:
            cmd.extend(["-m", ",".join(modules)])

        # Run spiderfoot asynchronously
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # SpiderFoot scans can take a while
        )

        # Parse the JSON output
        output: dict[str, Any] = {
            "target": target,
            "scan_type": scan_type,
            "spiderfoot_available": True,
        }

        try:
            with open(output_file, "r") as f:
                scan_data = json.load(f)

            # Extract scan results
            findings = scan_data.get("findings", [])
            modules_run = scan_data.get("modules_run", [])

            # Categorize findings
            categories: dict[str, int] = {}
            for finding in findings:
                cat = finding.get("type", "unknown")
                categories[cat] = categories.get(cat, 0) + 1

            output["findings"] = findings
            output["modules_run"] = modules_run
            output["total_findings"] = len(findings)
            output["categories"] = categories

        except (json.JSONDecodeError, IOError, FileNotFoundError) as exc:
            output["error"] = f"Failed to parse SpiderFoot output: {str(exc)}"
            output["findings"] = []
            output["modules_run"] = []
            output["total_findings"] = 0
            output["categories"] = {}

        return output

    except subprocess.TimeoutExpired:
        return {
            "target": target,
            "error": "SpiderFoot scan timed out after 600 seconds",
            "spiderfoot_available": True,
        }
    except Exception as exc:
        logger.exception("SpiderFoot scan failed")
        return {
            "target": target,
            "error": f"SpiderFoot scan error: {str(exc)}",
            "spiderfoot_available": True,
        }
