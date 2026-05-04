"""Anti-forensics tools for privacy/artifact management — USB monitoring and artifact cleanup.

SAFETY CRITICAL: All operations are DRY-RUN by default. No data is deleted without explicit user approval
and verification. These tools report what WOULD happen, not what happens.
"""

from __future__ import annotations

import logging
import platform
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.antiforensics")


def research_usb_kill_monitor(
    trigger_action: str = "alert",
    target_path: str = "/tmp",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Monitor USB device connections and optionally trigger protective actions.

    Dry-run only by default. On dry_run=True, reports what would happen without taking action.
    On Linux uses 'lsusb', on macOS uses 'system_profiler SPUSBDataType'.

    Args:
        trigger_action: action to take on USB detection ('alert' | 'wipe' | 'none')
        target_path: path to protect/monitor (for wipe action simulation)
        dry_run: if True, simulate only; never actually delete anything (default True)

    Returns:
        Dict with keys:
        - usb_devices_detected: list of detected USB devices
        - usb_count: number of devices
        - trigger_action: the action specified
        - target_path: the protected path
        - dry_run: whether this was a simulation
        - status: 'simulated' (dry_run=True) or 'alert_issued'
        - timestamp: ISO timestamp of check
    """
    import datetime

    os_type = platform.system()
    devices = []

    try:
        if os_type == "Linux":
            result = subprocess.run(
                ["lsusb"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Parse: Bus 001 Device 002: ID 1234:5678 Manufacturer Device Name
                for line in result.stdout.strip().split("\n"):
                    if line.strip():
                        devices.append(line.strip())
        elif os_type == "Darwin":
            result = subprocess.run(
                ["system_profiler", "SPUSBDataType"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # Extract device lines (simple heuristic)
                for line in result.stdout.split("\n"):
                    if "Product ID" in line or "Vendor ID" in line or "Device Name" in line:
                        devices.append(line.strip())
        else:
            logger.warning("usb_monitor unsupported_os: %s", os_type)
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning("usb_monitor_failed: %s", e)

    status = "simulated" if dry_run else "alert_issued"

    return {
        "usb_devices_detected": devices,
        "usb_count": len(devices),
        "trigger_action": trigger_action,
        "target_path": target_path,
        "dry_run": dry_run,
        "status": status,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "note": "DRY-RUN MODE: No data was deleted or modified." if dry_run else "",
    }


def research_forensics_cleanup(
    target_paths: list[str] | None = None,
    os_type: str | None = None,
) -> dict[str, Any]:
    """List forensic artifacts that WOULD be cleaned (dry-run only for safety).

    Never actually deletes anything. Scans standard artifact locations and reports
    what would be cleaned if run with dry_run=False (not yet implemented for safety).

    Common artifacts checked:
    - bash_history: ~/.bash_history, ~/.zsh_history
    - recently-used: ~/.recently-used, ~/.recently-used.xbel
    - thumbnails: ~/.cache/thumbnails
    - tmp files: /tmp, /var/tmp
    - browser cache: ~/.cache/chromium, ~/.cache/firefox, ~/Library/Caches/Google/Chrome

    Args:
        target_paths: additional paths to scan (e.g., ['/home/user/sensitive'])
        os_type: OS type ('linux' | 'darwin' | 'windows' | auto-detect if None)

    Returns:
        Dict with keys:
        - artifacts_found: list of dicts {path, type, size_bytes, exists}
        - total_size_mb: sum of all artifact sizes
        - cleanup_plan: list of actions that WOULD be taken (not taken)
        - os_type: detected OS type
        - dry_run: always True (safety guarantee)
        - timestamp: ISO timestamp
    """
    import datetime

    if os_type is None:
        os_type = platform.system().lower()

    artifacts = []
    home = Path.home()

    # Define artifact locations per OS
    if os_type in ("linux", "darwin"):
        artifact_paths = [
            (home / ".bash_history", "history"),
            (home / ".zsh_history", "history"),
            (home / ".recently-used", "recently_used"),
            (home / ".recently-used.xbel", "recently_used"),
            (home / ".cache" / "thumbnails", "thumbnails"),
            (home / ".cache" / "chromium", "browser_cache"),
            (home / ".cache" / "firefox", "browser_cache"),
            (Path("/tmp"), "tmp_files"),
            (Path("/var/tmp"), "tmp_files"),
        ]

        if os_type == "darwin":
            artifact_paths.extend([
                (home / "Library" / "Caches" / "Google" / "Chrome", "browser_cache"),
                (home / "Library" / "Safari", "browser_history"),
                (home / ".local" / "share" / "recently-used.xbel", "recently_used"),
            ])
    elif os_type == "windows":
        artifact_paths = [
            (Path.home() / "AppData" / "Local" / "Temp", "tmp_files"),
            (Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "WebCache", "browser_cache"),
            (Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Recent", "recently_used"),
        ]
    else:
        artifact_paths = []

    # Add user-specified paths
    if target_paths:
        for p in target_paths:
            artifact_paths.append((Path(p), "user_specified"))

    total_size_bytes = 0
    cleanup_plan = []

    for artifact_path, artifact_type in artifact_paths:
        try:
            if artifact_path.exists():
                if artifact_path.is_dir():
                    size_bytes = sum(f.stat().st_size for f in artifact_path.rglob("*") if f.is_file())
                else:
                    size_bytes = artifact_path.stat().st_size

                artifacts.append({
                    "path": str(artifact_path),
                    "type": artifact_type,
                    "size_bytes": size_bytes,
                    "exists": True,
                })
                total_size_bytes += size_bytes
                cleanup_plan.append(f"Would remove: {artifact_path} ({size_bytes} bytes)")
            else:
                artifacts.append({
                    "path": str(artifact_path),
                    "type": artifact_type,
                    "size_bytes": 0,
                    "exists": False,
                })
        except (OSError, PermissionError) as e:
            logger.warning("artifact_scan_error path=%s: %s", artifact_path, e)
            artifacts.append({
                "path": str(artifact_path),
                "type": artifact_type,
                "size_bytes": 0,
                "exists": False,
                "error": str(e),
            })

    total_size_mb = total_size_bytes / (1024 * 1024)

    return {
        "artifacts_found": artifacts,
        "total_size_mb": round(total_size_mb, 2),
        "cleanup_plan": cleanup_plan,
        "os_type": os_type,
        "dry_run": True,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "note": "DRY-RUN MODE: No data was deleted. This is a simulation only.",
    }
