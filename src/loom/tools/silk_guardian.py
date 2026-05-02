"""Silk Guardian — userspace anti-forensics monitor.

Monitors for forensic analysis activity WITHOUT loading kernel modules.
Uses udev rules, inotify, and /proc scanning to detect:
- USB device insertions (potential write blockers)
- Forensic tool processes (autopsy, sleuthkit, volatility, etc.)
- Suspicious mount operations (read-only mounts typical of forensics)
- Memory acquisition attempts
"""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import re
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

FORENSIC_PROCESSES = [
    "autopsy",
    "sleuthkit",
    "volatility",
    "rekall",
    "bulk_extractor",
    "foremost",
    "scalpel",
    "photorec",
    "testdisk",
    "dc3dd",
    "ewfacquire",
    "ftkimager",
    "guymager",
    "lime",
    "avml",
    "linpmem",
    "dumpit",
    "winpmem",
    "memdump",
    "dd",
]

FORENSIC_MOUNT_INDICATORS = [
    "ro,",
    "noatime",
    "noexec",
    "loop",
    "offset=",
]


async def research_silk_guardian_monitor(
    check_usb: bool = True,
    check_processes: bool = True,
    check_mounts: bool = True,
    trigger_action: str = "alert",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Monitor for forensic analysis activity (userspace, no kernel module).

    Scans for indicators of forensic examination:
    - USB write-blocker devices
    - Running forensic tool processes
    - Suspicious read-only mount patterns
    - Memory acquisition tools

    This is a userspace implementation that does NOT require kernel modules,
    making it safe for production systems. Uses /proc scanning, /sys inspection,
    and basic process monitoring.

    Args:
        check_usb: Monitor USB device activity (scans /sys/bus/usb/devices)
        check_processes: Scan for forensic tool processes (/proc scanning)
        check_mounts: Check for forensic-style mounts (/proc/mounts analysis)
        trigger_action: What to do on detection ('alert'|'log'|'wipe_cache')
        dry_run: If True, only report findings without taking action

    Returns:
        Dict with detection results, risk level, and recommended actions.
        Keys:
        - risk_level: 'critical'|'high'|'medium'|'low'
        - risk_score: Numeric 0-100 risk assessment
        - findings: List of detected forensic indicators
        - findings_count: Number of distinct findings
        - checks_performed: Dict of which checks ran
        - trigger_action: Action specified
        - dry_run: Whether this was a dry run
        - actions_taken: List of actions executed
        - recommendations: List of recommended remediation steps
    """
    findings = []
    risk_score = 0

    # Check 1: Scan running processes for forensic tools
    if check_processes:
        detected_processes = await _scan_forensic_processes()
        if detected_processes:
            findings.append(
                {
                    "type": "forensic_processes",
                    "severity": "critical",
                    "details": detected_processes,
                }
            )
            risk_score += 20 * len(detected_processes)

    # Check 2: USB device monitoring
    if check_usb:
        usb_findings = await _check_usb_devices()
        if usb_findings:
            findings.append(usb_findings)
            risk_score += 30

    # Check 3: Mount analysis
    if check_mounts:
        mount_findings = await _check_forensic_mounts()
        if mount_findings:
            findings.append(mount_findings)
            risk_score += 15

    # Cap risk score at 100
    risk_score = min(risk_score, 100)

    # Determine risk level
    if risk_score >= 50:
        risk_level = "critical"
    elif risk_score >= 30:
        risk_level = "high"
    elif risk_score >= 10:
        risk_level = "medium"
    else:
        risk_level = "low"

    # Actions (dry_run safe)
    actions_taken = []
    if not dry_run and risk_level in ("critical", "high"):
        if trigger_action == "wipe_cache":
            # Safe action: clear loom cache
            cache_dir = Path.home() / ".cache" / "loom"
            if cache_dir.exists():
                import shutil

                try:
                    shutil.rmtree(cache_dir, ignore_errors=True)
                    actions_taken.append("cache_wiped")
                    log.warning("silk_guardian_cache_wiped")
                except Exception as e:
                    log.error("cache_wipe_error: %s", e)
                    actions_taken.append("cache_wipe_failed")
        elif trigger_action == "log":
            actions_taken.append("forensic_activity_logged")
            log.critical("silk_guardian_forensic_detected: risk_level=%s", risk_level)
        else:  # alert
            actions_taken.append("alert_generated")
            log.warning("silk_guardian_alert: risk_level=%s score=%d", risk_level, risk_score)
    elif trigger_action == "alert":
        actions_taken.append("alert_available")

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "findings": findings,
        "findings_count": len(findings),
        "checks_performed": {
            "usb": check_usb,
            "processes": check_processes,
            "mounts": check_mounts,
        },
        "trigger_action": trigger_action,
        "dry_run": dry_run,
        "actions_taken": actions_taken,
        "recommendations": _get_recommendations(risk_level),
        "os_type": platform.system(),
    }


async def _scan_forensic_processes() -> list[dict[str, Any]]:
    """Scan /proc for running forensic tool processes."""
    detected_processes = []

    if platform.system() != "Linux":
        return detected_processes

    try:
        proc_dir = Path("/proc")
        for pid_dir in proc_dir.iterdir():
            if not pid_dir.name.isdigit():
                continue
            try:
                cmdline_file = pid_dir / "cmdline"
                comm_file = pid_dir / "comm"

                if not cmdline_file.exists():
                    continue

                cmdline = cmdline_file.read_bytes().decode("utf-8", errors="ignore")
                comm = comm_file.read_text().strip() if comm_file.exists() else ""

                for tool in FORENSIC_PROCESSES:
                    if tool in cmdline.lower() or tool in comm.lower():
                        detected_processes.append(
                            {
                                "pid": int(pid_dir.name),
                                "tool": tool,
                                "cmdline": cmdline[:200],
                                "comm": comm,
                            }
                        )
                        break
            except (PermissionError, FileNotFoundError, ProcessLookupError, ValueError):
                continue
    except Exception as e:
        log.warning("process_scan_error: %s", e)

    return detected_processes


async def _check_usb_devices() -> dict[str, Any] | None:
    """Check for forensic write-blocker USB devices."""
    usb_devices = []

    if platform.system() != "Linux":
        return None

    try:
        # Check via /sys/bus/usb/devices
        usb_path = Path("/sys/bus/usb/devices")
        if usb_path.exists():
            for device in usb_path.iterdir():
                product_path = device / "product"
                if product_path.exists():
                    try:
                        product = product_path.read_text().strip()
                        # Detect write blockers and forensic hardware
                        forensic_keywords = [
                            "write blocker",
                            "tableau",
                            "forensic",
                            "ultrablock",
                            "wiebetech",
                        ]
                        device_type = (
                            "write_blocker"
                            if any(kw in product.lower() for kw in forensic_keywords)
                            else "normal"
                        )
                        usb_devices.append(
                            {
                                "device": device.name,
                                "product": product,
                                "type": device_type,
                            }
                        )
                    except (PermissionError, OSError):
                        continue
    except Exception as e:
        log.warning("usb_scan_error: %s", e)

    # Return finding if write blockers detected
    blockers = [d for d in usb_devices if d["type"] == "write_blocker"]
    if blockers:
        return {
            "type": "forensic_usb_hardware",
            "severity": "critical",
            "details": blockers,
        }

    return None


async def _check_forensic_mounts() -> dict[str, Any] | None:
    """Analyze mounts for forensic-style patterns."""
    suspicious_mounts = []

    if platform.system() != "Linux":
        return None

    try:
        mounts_file = Path("/proc/mounts")
        if not mounts_file.exists():
            return None

        mounts_content = mounts_file.read_text()
        for line in mounts_content.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue

            device, mount_point, fs_type, options = parts[0], parts[1], parts[2], parts[3]

            # Count forensic mount indicators
            forensic_indicators = sum(1 for ind in FORENSIC_MOUNT_INDICATORS if ind in options)

            # Flag suspicious combinations (2+ indicators + external mount)
            if forensic_indicators >= 2 and (
                "/media" in mount_point or "/mnt" in mount_point or mount_point.startswith("/run/")
            ):
                suspicious_mounts.append(
                    {
                        "device": device,
                        "mount_point": mount_point,
                        "fs_type": fs_type,
                        "options": options,
                        "indicator_count": forensic_indicators,
                    }
                )
    except Exception as e:
        log.warning("mount_scan_error: %s", e)

    if suspicious_mounts:
        return {
            "type": "forensic_mounts",
            "severity": "high",
            "details": suspicious_mounts,
        }

    return None


def _get_recommendations(risk_level: str) -> list[str]:
    """Generate recommendations based on risk level."""
    if risk_level == "critical":
        return [
            "Forensic analysis detected — immediate action recommended",
            "Consider secure data destruction procedures",
            "Disconnect from network to prevent remote acquisition",
            "Invoke emergency wipe protocols if authorized",
            "Review system logs for forensic tool executions",
            "Check /var/log and ~/.bash_history for suspicious activity",
        ]
    elif risk_level == "high":
        return [
            "Suspicious activity detected — monitor closely",
            "Review connected USB devices for write blockers",
            "Check for unauthorized mount operations",
            "Verify all running processes are expected",
            "Consider running full security audit",
        ]
    elif risk_level == "medium":
        return [
            "Minor indicators found — likely benign",
            "Review mounting patterns for legitimacy",
            "Schedule routine security review",
        ]
    return [
        "No forensic indicators detected — system appears clean",
        "Continue routine security monitoring",
    ]
