"""research_testssl — TLS/SSL vulnerability audit via testssl.sh.

testssl.sh is a comprehensive SSL/TLS assessment tool that checks for
configuration issues, weak ciphers, certificate problems, and known
vulnerabilities. This module wraps the testssl.sh binary for automated
security auditing of HTTPS services.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
import subprocess
import uuid
from typing import Any

logger = logging.getLogger("loom.tools.testssl_backend")


def _validate_hostname(host: str) -> str:
    """Validate hostname or IP address.

    Args:
        host: Hostname or IP address

    Returns:
        The validated hostname

    Raises:
        ValueError: if hostname is invalid
    """
    host = host.strip() if isinstance(host, str) else ""

    if not host or len(host) > 253:
        raise ValueError("host must be 1-253 characters")

    # Allow hostnames (alphanumeric, dots, hyphens) and IPs
    # Simple check: no spaces, no control chars, no shell metacharacters
    if any(char in host for char in [" ", "\n", "\r", ";", "|", "&", "`", "$"]):
        raise ValueError("host contains disallowed characters")

    # Must look like a hostname or IP
    if not re.match(r"^[a-zA-Z0-9._:-]+$", host):
        raise ValueError("host must be a valid hostname or IP address")

    return host


def _validate_port(port: int) -> int:
    """Validate port number.

    Args:
        port: Port number

    Returns:
        The validated port

    Raises:
        ValueError: if port is invalid
    """
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise ValueError("port must be an integer between 1 and 65535")
    return port


def _validate_timeout(timeout: int) -> int:
    """Validate timeout parameter.

    Args:
        timeout: Timeout in seconds

    Returns:
        The validated timeout

    Raises:
        ValueError: if timeout is invalid
    """
    if not isinstance(timeout, int) or timeout < 10 or timeout > 600:
        raise ValueError("timeout must be an integer between 10 and 600 seconds")
    return timeout


def _validate_checks(checks: list[str] | None) -> list[str] | None:
    """Validate check types.

    Args:
        checks: List of check types

    Returns:
        The validated checks list

    Raises:
        ValueError: if any check is invalid
    """
    if checks is None:
        return None

    valid_checks = {
        "ciphers",
        "protocols",
        "certs",
        "vulnerabilities",
        "compliance",
        "browser",
        "heartbleed",
        "ccs",
    }

    for check in checks:
        if check not in valid_checks:
            raise ValueError(f"invalid check type: {check}. Must be one of {valid_checks}")

    return checks


def _check_testssl_available() -> tuple[bool, str]:
    """Check if testssl.sh binary is available.

    Returns:
        Tuple of (available: bool, message: str)
    """
    # Check for testssl.sh or testssl command
    if shutil.which("testssl.sh") or shutil.which("testssl"):
        return True, "testssl.sh binary found"
    return False, "testssl.sh not installed. Install from: https://github.com/drwetter/testssl.sh"


def _read_json_file(file_path: str) -> str:
    """Read JSON file from disk.

    Args:
        file_path: Path to JSON file

    Returns:
        File contents as string
    """
    with open(file_path) as f:
        return f.read()


def _parse_testssl_json(json_str: str) -> dict[str, Any]:
    """Parse testssl.sh JSON output.

    Args:
        json_str: JSON output from testssl.sh

    Returns:
        Parsed data dict
    """
    try:
        # testssl.sh outputs an array of result objects
        data = json.loads(json_str)
        if isinstance(data, list):
            return {"results": data}
        return data
    except json.JSONDecodeError:
        return {"raw_output": json_str}


async def research_testssl(
    host: str,
    port: int = 443,
    checks: list[str] | None = None,
) -> dict[str, Any]:
    """Audit TLS/SSL configuration for vulnerabilities and weaknesses.

    Uses testssl.sh to perform comprehensive security assessment of TLS/SSL
    services. Checks for weak ciphers, protocol issues, certificate problems,
    and known vulnerabilities like Heartbleed, CCS injection, etc.

    Args:
        host: Hostname or IP address to audit
        port: HTTPS port (1-65535). Default 443.
        checks: Optional list of specific checks to run. Valid values:
                ["ciphers", "protocols", "certs", "vulnerabilities", "compliance",
                 "browser", "heartbleed", "ccs"]. If None, runs all checks.

    Returns:
        Dict with keys:
        - host: the audited hostname/IP
        - port: the audited port
        - success: whether the audit completed
        - grade: overall security grade (A-F)
        - vulnerabilities: list of identified vulnerabilities
        - ciphers: list of supported ciphers with strength assessment
        - certificate: certificate info (subject, issuer, validity, serial)
        - protocols: list of supported TLS/SSL protocols
        - compliance: compliance check results (PCI DSS, HIPAA, etc.)
        - testssl_available: whether testssl.sh was available
        - error: error message if audit failed (optional)
    """
    # Validate inputs
    try:
        host = _validate_hostname(host)
        port = _validate_port(port)
        checks = _validate_checks(checks)
    except ValueError as e:
        return {
            "host": host,
            "port": port,
            "success": False,
            "error": str(e),
            "testssl_available": False,
        }

    logger.info("testssl_scan host=%s port=%d checks=%s", host, port, checks)

    # Check if testssl is available
    testssl_available, testssl_msg = _check_testssl_available()
    if not testssl_available:
        return {
            "host": host,
            "port": port,
            "success": False,
            "error": testssl_msg,
            "testssl_available": False,
        }

    # Determine testssl command
    testssl_cmd = "testssl.sh" if shutil.which("testssl.sh") else "testssl"

    try:
        # Create temp file for JSON output
        tmp_file = f"/tmp/testssl_{uuid.uuid4().hex}.json"

        # Build testssl command
        cmd = [
            testssl_cmd,
            "--jsonfile",
            tmp_file,
            f"{host}:{port}",
        ]

        # Add specific checks if provided
        if checks:
            # Map check names to testssl flags
            check_flags = {
                "ciphers": "--ciphers",
                "protocols": "--protocols",
                "certs": "--certs",
                "vulnerabilities": "--vulnerabilities",
                "compliance": "--compliance",
                "browser": "--browser",
                "heartbleed": "--heartbleed",
                "ccs": "--ccs",
            }

            for check in checks:
                if check in check_flags:
                    cmd.append(check_flags[check])

        # Run testssl with timeout
        timeout_secs = 120  # Fixed timeout for SSL scan
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_secs,
            check=False,
        )

        if result.returncode not in (0, 1):  # testssl.sh exits 0 or 1
            logger.warning("testssl_failed returncode=%d stderr=%s", result.returncode, result.stderr)
            return {
                "host": host,
                "port": port,
                "success": False,
                "error": f"testssl.sh exited with code {result.returncode}",
                "stderr": result.stderr[:500],
                "testssl_available": True,
            }

        # Read JSON output file
        try:
            json_output = await asyncio.to_thread(_read_json_file, tmp_file)
        except FileNotFoundError:
            logger.warning("testssl_json_file_not_created")
            return {
                "host": host,
                "port": port,
                "success": False,
                "error": "testssl.sh did not create JSON output file",
                "testssl_available": True,
            }

        # Parse JSON output
        parsed = _parse_testssl_json(json_output)

        # Extract and structure results
        vulnerabilities = []
        ciphers = []
        certificate = {}
        protocols = []
        compliance = {}
        grade = "UNKNOWN"

        if "results" in parsed:
            for result_item in parsed.get("results", []):
                id_val = result_item.get("id", "")
                severity = result_item.get("severity", "")
                finding = result_item.get("finding", "")

                # Categorize findings
                if id_val.startswith("vuln_"):
                    vulnerabilities.append(
                        {
                            "id": id_val,
                            "severity": severity,
                            "description": finding,
                        }
                    )
                elif id_val.startswith("cipher_"):
                    ciphers.append(
                        {
                            "name": result_item.get("cipher", id_val),
                            "strength": severity,
                            "bits": result_item.get("bits", 0),
                        }
                    )
                elif id_val.startswith("cert_"):
                    certificate.update(
                        {
                            "subject": result_item.get("subject"),
                            "issuer": result_item.get("issuer"),
                            "valid_from": result_item.get("notBefore"),
                            "valid_until": result_item.get("notAfter"),
                            "serial": result_item.get("serialNumber"),
                        }
                    )
                elif id_val.startswith("protocol_"):
                    protocols.append(result_item.get("protocol", id_val))
                elif id_val.startswith("compliance_"):
                    comp_name = result_item.get("compliance_standard", id_val)
                    compliance[comp_name] = {"status": severity, "details": finding}

                # Extract overall grade
                if id_val == "overall":
                    grade = severity

        # Calculate vulnerability score
        high_vulns = len([v for v in vulnerabilities if v.get("severity") == "HIGH"])
        med_vulns = len([v for v in vulnerabilities if v.get("severity") == "MEDIUM"])

        # Clean up temp file
        with contextlib.suppress(Exception):
            os.remove(tmp_file)

        return {
            "host": host,
            "port": port,
            "success": True,
            "grade": grade,
            "vulnerabilities": vulnerabilities,
            "ciphers": ciphers,
            "certificate": certificate if certificate else None,
            "protocols": protocols,
            "compliance": compliance if compliance else None,
            "vulnerability_count": len(vulnerabilities),
            "high_severity_count": high_vulns,
            "medium_severity_count": med_vulns,
            "testssl_available": True,
        }

    except TimeoutError:
        return {
            "host": host,
            "port": port,
            "success": False,
            "error": "testssl.sh scan timeout",
            "testssl_available": True,
        }
    except FileNotFoundError:
        return {
            "host": host,
            "port": port,
            "success": False,
            "error": "testssl.sh binary not found in PATH",
            "testssl_available": False,
        }
    except Exception as e:
        logger.exception("testssl_subprocess_error")
        return {
            "host": host,
            "port": port,
            "success": False,
            "error": f"testssl subprocess error: {type(e).__name__}: {e}",
            "testssl_available": True,
        }
