"""research_masscan — Ultra-fast port scanner using masscan backend.

Masscan is the fastest port scanner in existence (~10M packets/sec).
Requires masscan binary installed and (typically) root privileges.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from typing import Any

logger = logging.getLogger("loom.tools.masscan_backend")


def _is_valid_target(target: str) -> bool:
    """Validate target IP/hostname (basic check).

    Args:
        target: IP address, hostname, or CIDR range to scan

    Returns:
        True if target passes basic validation
    """
    # Simple check: not empty, reasonable length
    if not target or len(target) > 255:
        return False
    # Block loopback and some obvious abuse cases
    if target in ("localhost", "127.0.0.1", "::1"):
        return False
    return True


def _validate_port_range(ports: str) -> bool:
    """Validate port range specification.

    Args:
        ports: Port range string (e.g., "1-1000", "80,443,8080")

    Returns:
        True if valid port specification
    """
    if not ports or len(ports) > 50:
        return False
    # Allowed: digits, comma, hyphen, colon (for ranges)
    allowed_chars = set("0123456789,-:")
    return all(c in allowed_chars for c in ports)


def research_masscan(
    target: str,
    ports: str = "1-1000",
    rate: int = 1000,
    timeout: int = 60,
) -> dict[str, Any]:
    """Fast port scan using masscan.

    Masscan is the fastest port scanner (~10M packets/sec).
    Requires masscan binary installed and typically root privileges.

    Args:
        target: IP address, hostname, or CIDR range (e.g., "192.168.1.0/24")
        ports: Port range (default "1-1000", examples: "80", "80,443", "1-65535")
        rate: Packet rate in packets/sec (default 1000, max ~10000000)
        timeout: Scan timeout in seconds (default 60, max 300)

    Returns:
        Dict with keys:
        - target: Scanned target
        - masscan_available: Boolean indicating if masscan is installed
        - success: Boolean indicating if scan completed
        - open_ports: List of open ports (if successful)
        - total_scanned: Number of ports scanned
        - scan_rate: Actual packet rate achieved
        - scan_time_seconds: Duration of scan
        - error: Error message if failed
        - warning: Warning messages if applicable
    """
    result: dict[str, Any] = {
        "target": target,
        "masscan_available": False,
        "success": False,
        "open_ports": [],
        "total_scanned": 0,
        "scan_rate": 0,
        "scan_time_seconds": 0,
        "error": None,
        "warning": None,
    }

    # Check if masscan is installed
    if not shutil.which("masscan"):
        result["error"] = "masscan binary not found in PATH"
        logger.warning("masscan_not_installed")
        return result

    result["masscan_available"] = True

    # Validate inputs
    if not _is_valid_target(target):
        result["error"] = f"Invalid target: {target}"
        return result

    if not _validate_port_range(ports):
        result["error"] = f"Invalid port range: {ports}"
        return result

    if rate < 1 or rate > 10000000:
        result["error"] = "rate must be 1-10000000 packets/sec"
        return result

    if timeout < 1 or timeout > 300:
        result["error"] = "timeout must be 1-300 seconds"
        return result

    # Prepare temp output file using secure tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tf:
        output_file = tf.name

    try:
        # Build masscan command
        cmd = [
            "masscan",
            target,
            f"-p{ports}",
            f"--rate={rate}",
            f"--output-format=json",
            f"--output-file={output_file}",
        ]

        # Run masscan with timeout
        logger.info("masscan_scan_start target=%s ports=%s rate=%s", target, ports, rate)
        start_time = time.time()

        try:
            # Run without shell for safety
            subprocess.run(
                cmd,
                timeout=timeout,
                capture_output=True,
                text=True,
                check=False,  # Don't raise on non-zero exit
            )
        except subprocess.TimeoutExpired:
            result["error"] = f"Scan timeout after {timeout} seconds"
            logger.warning("masscan_timeout target=%s timeout=%s", target, timeout)
            return result
        except PermissionError:
            result["error"] = "Permission denied — masscan typically requires root/sudo"
            logger.warning("masscan_permission_denied target=%s", target)
            return result

        end_time = time.time()
        scan_time = end_time - start_time
        result["scan_time_seconds"] = round(scan_time, 2)

        # Parse JSON output
        try:
            with open(output_file, "r") as f:
                lines = f.readlines()
        except FileNotFoundError:
            result["error"] = "masscan output file not created"
            logger.warning("masscan_output_not_found target=%s", target)
            return result

        # Parse each JSON line (masscan outputs one JSON object per line)
        open_ports_set = set()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if "ports" in obj and isinstance(obj["ports"], list):
                    for port_obj in obj["ports"]:
                        if port_obj.get("status") == "open":
                            open_ports_set.add(port_obj.get("port"))
            except json.JSONDecodeError:
                logger.debug("Failed to parse masscan JSON line: %s", line)

        result["open_ports"] = sorted(list(open_ports_set))
        result["success"] = True

        # Calculate statistics
        try:
            if "-" in ports:
                # Range like "1-1000"
                parts = ports.split("-")
                if len(parts) != 2:
                    # Malformed range (e.g., "80-443-8080")
                    result["total_scanned"] = 0
                else:
                    start_port = int(parts[0])
                    end_port = int(parts[1])
                    # Validate port numbers are in valid range
                    if not (1 <= start_port <= 65535 and 1 <= end_port <= 65535):
                        result["total_scanned"] = 0
                    else:
                        result["total_scanned"] = end_port - start_port + 1
            elif "," in ports:
                # List like "80,443,8080"
                result["total_scanned"] = len(ports.split(","))
            else:
                # Single port
                result["total_scanned"] = 1
        except (ValueError, IndexError):
            result["total_scanned"] = 0

        if scan_time > 0:
            result["scan_rate"] = round(result["total_scanned"] / scan_time, 2)

        logger.info(
            "masscan_scan_complete target=%s open_ports=%d scan_time=%s",
            target,
            len(result["open_ports"]),
            scan_time,
        )

    except Exception as exc:
        result["error"] = f"Scan failed: {str(exc)}"
        logger.error("masscan_exception target=%s: %s", target, exc, exc_info=True)

    finally:
        # Clean up temp file
        try:
            os.remove(output_file)
        except FileNotFoundError:
            pass
        except Exception as exc:
            logger.debug("Failed to clean up temp file %s: %s", output_file, exc)

    return result
