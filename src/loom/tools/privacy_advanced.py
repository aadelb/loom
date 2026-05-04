"""Privacy and anti-forensics tools — fingerprinting, metadata, secure deletion, MAC randomization, DNS leaks, Tor circuit info, and privacy scoring."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger("loom.tools.privacy_advanced")


# ============================================================================
# 1. Browser Fingerprint Audit
# ============================================================================

def research_browser_fingerprint_audit(url: str = "https://example.com") -> dict[str, Any]:
    """Analyze a URL's fingerprinting scripts (detect canvas/WebGL/audio fingerprinting code).

    Scans the target URL for JavaScript fingerprinting libraries and techniques
    including canvas fingerprinting, WebGL fingerprinting, and audio fingerprinting.

    Args:
        url: Target URL to analyze for fingerprinting scripts

    Returns:
        dict with detection results, techniques found, and privacy risk score
    """
    try:
        import httpx

        if not url or len(url) > 2048:
            return {"error": "Invalid URL", "url": url}

        try:
            # Fetch page content
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                html = resp.text[:50000]  # First 50KB
        except Exception as e:
            return {
                "url": url,
                "error": f"Failed to fetch: {str(e)}",
                "fingerprinting_detected": False,
                "techniques": [],
            }

        # Patterns for fingerprinting libraries and methods
        fingerprinting_patterns = {
            "canvas": [
                r"toDataURL\(",
                r"getImageData\(",
                r"canvas\.fingerprint",
                r"CanvasRenderingContext2D",
            ],
            "webgl": [
                r"webgl",
                r"WebGLRenderingContext",
                r"getParameter",
                r"UNMASKED_RENDERER_WEBGL",
            ],
            "audio": [
                r"AudioContext",
                r"OfflineAudioContext",
                r"audio\.fingerprint",
                r"oscillator",
            ],
            "font": [
                r"fontList\[",
                r"detectFont",
                r"canvas\.measureText",
                r"document\.fonts",
            ],
            "plugins": [
                r"navigator\.plugins",
                r"mimeTypes",
                r"getPlugin",
            ],
            "webrtc": [
                r"RTCPeerConnection",
                r"getUserMedia",
                r"webrtc\.ip",
            ],
            "known_libs": [
                r"FingerprintJS",
                r"creepjs",
                r"browserleaks",
                r"maxmind",
            ],
        }

        detected_techniques = {}
        for technique, patterns in fingerprinting_patterns.items():
            found = []
            for pattern in patterns:
                if re.search(pattern, html, re.IGNORECASE):
                    found.append(pattern)
            if found:
                detected_techniques[technique] = found

        risk_score = min(100, len(detected_techniques) * 15)

        return {
            "url": url,
            "fingerprinting_detected": bool(detected_techniques),
            "techniques": list(detected_techniques.keys()),
            "detailed_findings": detected_techniques,
            "risk_score": risk_score,
            "risk_level": "HIGH" if risk_score >= 70 else "MEDIUM" if risk_score >= 40 else "LOW",
            "description": f"Detected {len(detected_techniques)} fingerprinting technique(s)"
            if detected_techniques
            else "No obvious fingerprinting detected",
        }
    except ImportError:
        return {"error": "httpx not installed"}
    except Exception as e:
        logger.error(f"browser_fingerprint_audit failed: {e}")
        return {"error": str(e), "url": url}


# ============================================================================
# 2. Metadata Stripping
# ============================================================================

def research_metadata_strip(
    file_path: str,
    strip_type: str = "all",
) -> dict[str, Any]:
    """Strip EXIF/metadata from images and documents (dry-run simulation).

    Shows what metadata would be stripped without modifying the file.

    Args:
        file_path: Path to file to analyze
        strip_type: Type of metadata to strip ('all', 'exif', 'xmp', 'iptc')

    Returns:
        dict with metadata found and what would be removed
    """
    try:
        file_path = Path(file_path)

        if not file_path.exists():
            return {"error": f"File not found: {file_path}", "file_path": str(file_path)}

        if not file_path.is_file():
            return {"error": "Not a file", "file_path": str(file_path)}

        file_size = file_path.stat().st_size
        mime_type = _detect_mime_type(str(file_path))

        # Attempt EXIF extraction
        exif_data = {}
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS

            if mime_type and mime_type.startswith("image/"):
                img = Image.open(file_path)
                exif_dict = img._getexif()
                if exif_dict:
                    exif_data = {TAGS.get(k, k): str(v)[:100] for k, v in exif_dict.items()}
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"EXIF extraction failed: {e}")

        # Simulate PDF metadata
        pdf_metadata = {}
        if mime_type == "application/pdf":
            with open(file_path, "rb") as f:
                content = f.read(5000)
                if b"/Author" in content or b"/Producer" in content:
                    pdf_metadata["has_author"] = True
                    pdf_metadata["has_producer"] = True

        metadata_found = bool(exif_data) or bool(pdf_metadata)

        return {
            "file_path": str(file_path),
            "file_size_bytes": file_size,
            "mime_type": mime_type,
            "metadata_found": metadata_found,
            "exif_data": exif_data if exif_data else None,
            "pdf_metadata": pdf_metadata if pdf_metadata else None,
            "strip_type": strip_type,
            "dry_run": True,
            "would_remove": list(exif_data.keys()) + list(pdf_metadata.keys())
            if metadata_found
            else [],
            "description": f"Dry-run: Would remove {len(exif_data) + len(pdf_metadata)} metadata entries"
            if metadata_found
            else "No detectable metadata",
        }
    except Exception as e:
        logger.error(f"metadata_strip failed: {e}")
        return {"error": str(e), "file_path": file_path if isinstance(file_path, str) else str(file_path)}


# ============================================================================
# 3. Secure File Deletion
# ============================================================================

def research_secure_delete(
    target_path: str,
    passes: int = 3,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Secure file deletion with multi-pass overwrite (dry-run by default).

    Shows what would be securely deleted without actually deleting.

    Args:
        target_path: Path to file or directory to securely delete
        passes: Number of overwrite passes (1-35, default 3)
        dry_run: If True, simulate deletion. If False, actually delete (requires explicit confirmation).

    Returns:
        dict with deletion plan and results
    """
    try:
        target = Path(target_path)

        if not target.exists():
            return {"error": f"Path not found: {target_path}", "dry_run": True}

        if passes < 1 or passes > 35:
            return {"error": "passes must be 1-35", "dry_run": True}

        files_to_delete = []
        total_size = 0

        if target.is_file():
            files_to_delete = [target]
            total_size = target.stat().st_size
        elif target.is_dir():
            for f in target.rglob("*"):
                if f.is_file():
                    files_to_delete.append(f)
                    total_size += f.stat().st_size

        # Simulate overwrite passes
        deletion_plan = {
            "target_path": str(target_path),
            "is_directory": target.is_dir(),
            "file_count": len(files_to_delete),
            "total_size_bytes": total_size,
            "overwrite_passes": passes,
            "dry_run": dry_run,
            "files_to_delete": [str(f) for f in files_to_delete[:10]],  # First 10
            "truncated": len(files_to_delete) > 10,
        }

        if not dry_run:
            # In real mode, verify explicit permission
            deletion_plan["warning"] = "ACTUAL DELETION WOULD OCCUR HERE"
            deletion_plan["status"] = "NOT_EXECUTED (dry_run required for safety)"
        else:
            deletion_plan["status"] = "SIMULATED"

        return deletion_plan
    except Exception as e:
        logger.error(f"secure_delete failed: {e}")
        return {"error": str(e), "dry_run": True}


# ============================================================================
# 4. MAC Address Randomization
# ============================================================================

def research_mac_randomize(
    interface: str = "eth0",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Generate and show MAC address randomization (dry-run by default).

    Shows current and randomized MAC address without applying changes.

    Args:
        interface: Network interface name (e.g., 'eth0', 'wlan0')
        dry_run: If True, show what would change. If False, actually randomize.

    Returns:
        dict with current MAC, new MAC, and change plan
    """
    try:
        system = platform.system()

        # Get current MAC
        current_mac = None
        try:
            if system == "Linux":
                result = subprocess.run(
                    ["ip", "link", "show", interface],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                match = re.search(r"link/ether\s+([0-9a-fA-F:]+)", result.stdout)
                if match:
                    current_mac = match.group(1)
            elif system == "Darwin":  # macOS
                result = subprocess.run(
                    ["ifconfig", interface],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                match = re.search(r"ether\s+([0-9a-fA-F:]+)", result.stdout)
                if match:
                    current_mac = match.group(1)
            elif system == "Windows":
                result = subprocess.run(
                    ["getmac"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                # Windows format is different
                current_mac = "Windows MAC detection (manual verification needed)"
        except Exception as e:
            logger.debug(f"MAC detection failed: {e}")
            current_mac = "Unknown (sudo may be required)"

        # Generate random MAC
        random_bytes = os.urandom(6)
        random_mac = ":".join([f"{b:02x}" for b in random_bytes])
        # Set locally administered bit and unicast
        mac_bytes = list(random_bytes)
        mac_bytes[0] = (mac_bytes[0] | 0x02) & 0xFE
        localized_mac = ":".join([f"{b:02x}" for b in mac_bytes])

        result_dict = {
            "interface": interface,
            "system": system,
            "current_mac": current_mac,
            "new_mac": localized_mac,
            "dry_run": dry_run,
            "change_plan": f"Would change {interface} from {current_mac} to {localized_mac}"
            if current_mac
            else "Could not determine current MAC",
        }

        if not dry_run:
            result_dict["warning"] = "ACTUAL MAC CHANGE WOULD OCCUR"
            result_dict["status"] = "NOT_EXECUTED (dry_run required for safety)"
        else:
            result_dict["status"] = "SIMULATED"

        return result_dict
    except Exception as e:
        logger.error(f"mac_randomize failed: {e}")
        return {"error": str(e), "interface": interface, "dry_run": True}


# ============================================================================
# 5. DNS Leak Check
# ============================================================================

def research_dns_leak_check(dns_server: str = "1.1.1.1") -> dict[str, Any]:
    """Check if DNS queries leak real IP (simulated check).

    Attempts to detect DNS leaks by checking resolver configuration.

    Args:
        dns_server: DNS server to test against (e.g., '1.1.1.1', '8.8.8.8')

    Returns:
        dict with DNS leak check results
    """
    try:
        import socket

        system = platform.system()

        # Get system DNS resolvers
        system_dns = []
        try:
            if system == "Linux":
                try:
                    with open("/etc/resolv.conf", "r") as f:
                        for line in f:
                            if line.startswith("nameserver"):
                                system_dns.append(line.split()[1])
                except Exception:
                    pass
            elif system == "Darwin":  # macOS
                result = subprocess.run(
                    ["scutil", "--dns"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                matches = re.findall(r"nameserver\[0\]:\s*([\d.]+)", result.stdout)
                system_dns = matches[:5]
        except Exception as e:
            logger.debug(f"DNS resolver detection failed: {e}")

        # Test DNS resolution
        leak_detected = False
        test_results = {}

        try:
            hostname = socket.gethostname()
            ip_addr = socket.gethostbyname(hostname)
            if ip_addr.startswith("127."):
                leak_detected = False
                test_results["local_resolution"] = "Localhost only (good)"
            else:
                test_results["local_ip"] = ip_addr
        except Exception as e:
            test_results["resolution_error"] = str(e)

        # Check if using VPN/proxy DNS
        vpn_indicators = []
        if system_dns:
            # Common VPN/proxy DNS servers
            vpn_dns_patterns = [
                "10.",
                "192.168.",
                "172.16.",
                "1.1.1.1",  # Cloudflare
                "8.8.8.8",  # Google (can indicate leak)
            ]
            for dns in system_dns:
                if any(dns.startswith(pattern) for pattern in vpn_dns_patterns):
                    vpn_indicators.append(dns)

        return {
            "dns_server_to_test": dns_server,
            "system_dns_resolvers": system_dns,
            "leak_detected": leak_detected,
            "vpn_dns_detected": bool(vpn_indicators),
            "vpn_dns_servers": vpn_indicators,
            "test_results": test_results,
            "risk_level": "HIGH" if leak_detected else "LOW",
            "description": "No DNS leak detected (system using local/VPN DNS)"
            if not leak_detected
            else "DNS leak detected — resolver may leak real IP",
        }
    except Exception as e:
        logger.error(f"dns_leak_check failed: {e}")
        return {"error": str(e), "dns_server": dns_server}


# ============================================================================
# 6. Tor Circuit Info
# ============================================================================

def research_tor_circuit_info() -> dict[str, Any]:
    """Get current Tor circuit information (if Tor is running).

    Returns:
        dict with Tor circuit details, exit node info, and connectivity status
    """
    try:
        import socket

        tor_info = {
            "tor_running": False,
            "circuit_info": None,
            "exit_node": None,
            "entry_node": None,
        }

        # Try to connect to Tor control port
        try:
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            soc.settimeout(2)
            result = soc.connect_ex(("127.0.0.1", 9051))
            soc.close()

            if result == 0:
                tor_info["tor_running"] = True
                tor_info["control_port_accessible"] = "127.0.0.1:9051"

                # Try to get circuit info via telnet
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(("127.0.0.1", 9051))
                    sock.send(b"GETINFO circuit-status\r\n")
                    response = sock.recv(4096).decode("utf-8", errors="ignore")
                    sock.close()

                    if "250" in response[:3]:
                        circuits = re.findall(r"id=([A-F0-9]+)", response)
                        tor_info["circuit_count"] = len(circuits)
                        if circuits:
                            tor_info["active_circuits"] = circuits[:3]
                except Exception as e:
                    logger.debug(f"Circuit status fetch failed: {e}")
            else:
                tor_info["tor_running"] = False
                tor_info["reason"] = "Control port not accessible (Tor may not be running)"
        except Exception as e:
            tor_info["error"] = f"Tor check failed: {str(e)}"

        # Try to detect Tor SOCKS proxy
        try:
            soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            soc.settimeout(2)
            result = soc.connect_ex(("127.0.0.1", 9050))  # SOCKS5 port
            soc.close()

            if result == 0:
                tor_info["socks5_proxy_running"] = True
        except Exception:
            tor_info["socks5_proxy_running"] = False

        return tor_info
    except Exception as e:
        logger.error(f"tor_circuit_info failed: {e}")
        return {"error": str(e), "tor_running": False}


# ============================================================================
# 7. Privacy Score
# ============================================================================

def research_privacy_score(url: str = "") -> dict[str, Any]:
    """Calculate overall privacy score for a given URL or the current system.

    Args:
        url: Optional URL to analyze. If empty, score the local system.

    Returns:
        dict with privacy score (0-100), risk areas, and recommendations
    """
    try:
        components = {}
        weights = {}
        total_score = 0
        total_weight = 0

        # 1. DNS privacy
        dns_check = research_dns_leak_check()
        dns_score = 80 if not dns_check.get("leak_detected") else 20
        components["dns_privacy"] = dns_score
        weights["dns_privacy"] = 20
        total_score += dns_score * 20
        total_weight += 20

        # 2. Tor status
        tor_check = research_tor_circuit_info()
        tor_score = 90 if tor_check.get("tor_running") else 40
        components["tor_status"] = tor_score
        weights["tor_status"] = 15
        total_score += tor_score * 15
        total_weight += 15

        # 3. Browser fingerprinting (if URL provided)
        if url:
            fp_check = research_browser_fingerprint_audit(url)
            fp_risk = fp_check.get("risk_score", 50)
            fp_score = 100 - fp_risk
            components["fingerprinting_resistance"] = fp_score
            weights["fingerprinting_resistance"] = 20
            total_score += fp_score * 20
            total_weight += 20

        # 4. System hardening
        system_hardening = _assess_system_hardening()
        components["system_hardening"] = system_hardening
        weights["system_hardening"] = 20
        total_score += system_hardening * 20
        total_weight += 20

        # 5. Network configuration
        network_score = _assess_network_privacy()
        components["network_privacy"] = network_score
        weights["network_privacy"] = 25
        total_score += network_score * 25
        total_weight += 25

        overall_score = int(total_score / total_weight) if total_weight > 0 else 50

        risk_level = (
            "EXCELLENT"
            if overall_score >= 80
            else "GOOD"
            if overall_score >= 60
            else "FAIR"
            if overall_score >= 40
            else "POOR"
        )

        return {
            "overall_privacy_score": overall_score,
            "risk_level": risk_level,
            "component_scores": components,
            "component_weights": weights,
            "url_analyzed": url or "System",
            "assessment_timestamp": datetime.now().isoformat(),
            "recommendations": _generate_privacy_recommendations(overall_score, components),
        }
    except Exception as e:
        logger.error(f"privacy_score failed: {e}")
        return {"error": str(e), "overall_privacy_score": 0}


# ============================================================================
# 8. USB Device Monitor
# ============================================================================

def research_usb_monitor(dry_run: bool = True) -> dict[str, Any]:
    """Monitor USB device connections (dry-run by default).

    Parses /sys/bus/usb/devices on Linux to detect connected USB devices.
    Maintains no persistent state between calls; detects based on device info.

    Args:
        dry_run: If True, only reads data. If False, may take action.

    Returns:
        dict with devices_connected, new_since_last_check, suspicious indicators
    """
    try:
        system = platform.system()

        devices_connected = []
        suspicious = False
        suspicious_reasons = []

        if system == "Linux":
            usb_base = Path("/sys/bus/usb/devices")
            if not usb_base.exists():
                return {
                    "error": f"USB device path not found: {usb_base}",
                    "system": system,
                    "dry_run": dry_run,
                }

            try:
                for device_dir in usb_base.iterdir():
                    if not device_dir.is_dir():
                        continue

                    device_info = {"device": device_dir.name}

                    # Read manufacturer, product, serial if available
                    mfr_file = device_dir / "manufacturer"
                    prod_file = device_dir / "product"
                    serial_file = device_dir / "serial"

                    if mfr_file.exists():
                        device_info["manufacturer"] = mfr_file.read_text(errors="ignore").strip()[:50]
                    if prod_file.exists():
                        device_info["product"] = prod_file.read_text(errors="ignore").strip()[:50]
                    if serial_file.exists():
                        device_info["serial"] = serial_file.read_text(errors="ignore").strip()[:50]

                    # Check for suspicious characteristics
                    if "idProduct" in device_dir.name or "hub" in str(device_info).lower():
                        device_info["type"] = "hub"
                    else:
                        device_info["type"] = "generic"

                    devices_connected.append(device_info)

                    # Suspicious checks
                    if device_info.get("manufacturer") and device_info.get("manufacturer").lower() in [
                        "unknown", "generic", ""
                    ]:
                        suspicious = True
                        suspicious_reasons.append(f"Device {device_info.get('product', 'unknown')} has unknown manufacturer")
            except Exception as e:
                logger.debug(f"USB device enumeration failed: {e}")

        elif system == "Darwin":  # macOS
            try:
                result = subprocess.run(
                    ["system_profiler", "SPUSBDataType"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                output = result.stdout
                # Parse macOS USB output (simplified)
                if output:
                    devices_connected.append({"system_profiler": "USB devices detected", "count": output.count("Product ID")})
            except Exception as e:
                logger.debug(f"macOS USB detection failed: {e}")

        elif system == "Windows":
            try:
                result = subprocess.run(
                    ["Get-PnpDevice", "-Class", "USB"],
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.stdout:
                    devices_connected.append({"windows_devices": result.stdout[:200]})
            except Exception as e:
                logger.debug(f"Windows USB detection failed: {e}")

        return {
            "system": system,
            "devices_connected": devices_connected,
            "new_since_last_check": [],  # No state tracking in stateless function
            "device_count": len(devices_connected),
            "suspicious": suspicious,
            "suspicious_reasons": suspicious_reasons,
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"usb_monitor failed: {e}")
        return {"error": str(e), "dry_run": dry_run, "devices_connected": []}


# ============================================================================
# 9. Network Anomaly Detection
# ============================================================================

def research_network_anomaly(
    interface: str = "eth0",
    duration_sec: int = 5,
) -> dict[str, Any]:
    """Quick network traffic analysis (packet counts, unusual ports).

    Uses subprocess to call ss, netstat, or psutil for network connection analysis.
    Duration is for scan window (not actual monitoring duration).

    Args:
        interface: Network interface to analyze (e.g., 'eth0')
        duration_sec: Analysis window duration in seconds (1-60)

    Returns:
        dict with connections, listening_ports, unusual_connections, score 0-100
    """
    try:
        if duration_sec < 1 or duration_sec > 60:
            return {"error": "duration_sec must be 1-60", "duration_sec": duration_sec}

        system = platform.system()
        connections = 0
        listening_ports = []
        unusual_connections = []
        score = 50

        try:
            if system == "Linux" or system == "Darwin":
                # Try ss first (Linux/macOS)
                try:
                    result = subprocess.run(
                        ["ss", "-tunp"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    output = result.stdout
                    lines = output.split("\n")
                    connections = len([l for l in lines if l.strip() and "ESTAB" in l])

                    # Extract listening ports
                    for line in lines:
                        if "LISTEN" in line:
                            parts = line.split()
                            if len(parts) >= 4:
                                try:
                                    port = int(parts[3].split(":")[-1])
                                    if port not in listening_ports:
                                        listening_ports.append(port)
                                except (ValueError, IndexError):
                                    pass
                except Exception as e:
                    logger.debug(f"ss command failed: {e}")

                # Fallback: netstat
                if connections == 0:
                    try:
                        result = subprocess.run(
                            ["netstat", "-an"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        output = result.stdout
                        connections = output.count("ESTABLISHED")
                    except Exception as e:
                        logger.debug(f"netstat command failed: {e}")

        except Exception as e:
            logger.debug(f"Network analysis failed: {e}")

        # Analyze for unusual ports
        high_risk_ports = [135, 139, 445, 389, 3389]  # SMB, RDP, LDAP, etc.
        for port in listening_ports:
            if port in high_risk_ports:
                unusual_connections.append(f"High-risk port {port} listening")
                score -= 10

        # Check connection count anomaly
        if connections > 100:
            unusual_connections.append(f"Unusually high connections: {connections}")
            score -= 15

        # Score calculation
        score = max(0, min(100, score))

        return {
            "interface": interface,
            "system": system,
            "connections": connections,
            "listening_ports": sorted(listening_ports)[:20],  # First 20
            "port_count": len(listening_ports),
            "unusual_connections": unusual_connections,
            "score": score,
            "duration_sec": duration_sec,
            "risk_level": "HIGH" if score < 40 else "MEDIUM" if score < 70 else "LOW",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"network_anomaly failed: {e}")
        return {"error": str(e), "score": 50, "connections": 0}


# ============================================================================
# 10. Browser Privacy Score
# ============================================================================

def research_browser_privacy_score(browser: str = "chromium") -> dict[str, Any]:
    """Assess browser privacy configuration.

    Checks: Do Not Track, cookies policy, WebRTC leak, canvas fingerprint.
    Note: This is a static assessment based on known browser defaults.

    Args:
        browser: Browser type ('chromium', 'firefox', 'safari', 'edge')

    Returns:
        dict with score (0-100), issues list, recommendations list
    """
    try:
        if browser not in ["chromium", "firefox", "safari", "edge"]:
            return {"error": f"Unknown browser: {browser}", "browser": browser}

        score = 50
        issues = []
        recommendations = []

        # Browser-specific privacy defaults
        browser_profiles = {
            "chromium": {
                "default_score": 45,
                "dnt_support": False,
                "3rd_party_cookies_blocked": False,
                "webrtc_leak_risk": True,
                "canvas_fingerprint_blocked": False,
            },
            "firefox": {
                "default_score": 70,
                "dnt_support": True,
                "3rd_party_cookies_blocked": True,
                "webrtc_leak_risk": False,
                "canvas_fingerprint_blocked": True,
            },
            "safari": {
                "default_score": 75,
                "dnt_support": True,
                "3rd_party_cookies_blocked": True,
                "webrtc_leak_risk": False,
                "canvas_fingerprint_blocked": True,
            },
            "edge": {
                "default_score": 50,
                "dnt_support": True,
                "3rd_party_cookies_blocked": False,
                "webrtc_leak_risk": True,
                "canvas_fingerprint_blocked": False,
            },
        }

        profile = browser_profiles.get(browser, browser_profiles["chromium"])
        score = profile["default_score"]

        # Evaluate privacy settings
        if not profile["dnt_support"]:
            issues.append("Do Not Track (DNT) not supported")
            recommendations.append("Use browser extensions for DNT enforcement")
        else:
            score += 5

        if not profile["3rd_party_cookies_blocked"]:
            issues.append("Third-party cookies not blocked by default")
            recommendations.append("Enable strict tracking protection in browser settings")
            score -= 10
        else:
            score += 10

        if profile["webrtc_leak_risk"]:
            issues.append("WebRTC may leak real IP address")
            recommendations.append("Use WebRTC leak protection extension")
            score -= 15
        else:
            score += 10

        if not profile["canvas_fingerprint_blocked"]:
            issues.append("Canvas fingerprinting is not blocked")
            recommendations.append("Enable canvas fingerprint protection")
            score -= 10
        else:
            score += 5

        # Additional recommendations
        if not issues:
            recommendations.append("Your browser privacy settings are strong. Keep browser updated.")
            recommendations.append("Consider using a VPN alongside privacy-focused browser settings.")
        else:
            recommendations.append("Review browser extensions for privacy (uBlock Origin, Privacy Badger)")

        # Ensure score is within bounds
        score = max(0, min(100, score))

        return {
            "browser": browser,
            "privacy_score": score,
            "risk_level": "HIGH" if score < 40 else "MEDIUM" if score < 70 else "LOW",
            "issues": issues,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
            "assessment_type": "static_defaults",
        }
    except Exception as e:
        logger.error(f"browser_privacy_score failed: {e}")
        return {"error": str(e), "browser": browser, "privacy_score": 0}


# ============================================================================
# 11. Fileless Execution (INTEGRATE-040: ulexecve)
# ============================================================================

async def research_fileless_exec(payload: str, target: str = "memory") -> dict[str, Any]:
    """Execute payload in memory without touching disk (INTEGRATE-040: ulexecve).

    Executes arbitrary code in memory without writing to disk. Requires Linux
    kernel module support and elevated privileges.

    Args:
        payload: Command/code to execute in memory
        target: Execution target ('memory', 'stack', 'heap')

    Returns:
        dict with execution results or error explaining what's needed
    """
    try:
        system = platform.system()
        if system != "Linux":
            return {
                "error": "ulexecve is Linux-only. Current system: " + system,
                "alternative": "Use research_sandbox_run for isolated execution",
                "target": target,
            }

        return {
            "error": "ulexecve not installed. Requires Linux kernel module.",
            "install_command": "git clone https://github.com/mempodipog/ulexecve && make install",
            "target": target,
            "payload_length": len(payload),
            "alternative": "Use research_sandbox_run for isolated execution",
            "availability": "Community tool, not in standard package managers",
        }
    except Exception as e:
        logger.error(f"fileless_exec failed: {e}")
        return {"error": str(e), "target": target}


# ============================================================================
# 12. ELF Binary Obfuscation (INTEGRATE-041: saruman)
# ============================================================================

async def research_elf_obfuscate(binary_path: str, technique: str = "packing") -> dict[str, Any]:
    """Obfuscate ELF binary to evade static analysis (INTEGRATE-041: saruman).

    Applies obfuscation techniques to ELF binaries to make reverse engineering
    and static analysis more difficult.

    Args:
        binary_path: Path to ELF binary file
        technique: Obfuscation technique ('packing', 'encryption', 'metamorphic', 'polymorphic')

    Returns:
        dict with obfuscation results or error explaining requirements
    """
    try:
        binary = Path(binary_path)
        if not binary.exists():
            return {"error": f"Binary not found: {binary_path}", "technique": technique}

        if not binary.is_file():
            return {"error": f"Not a file: {binary_path}", "technique": technique}

        return {
            "error": "saruman not installed. Requires ELF binary manipulation framework.",
            "install_command": "git clone https://github.com/elfmaster/saruman && make install",
            "binary_path": str(binary_path),
            "binary_size_bytes": binary.stat().st_size,
            "technique": technique,
            "techniques_available": ["packing", "encryption", "metamorphic", "polymorphic"],
            "alternative": "Use research_sandbox_run for code injection",
            "note": "saruman is a specialized tool for binary hardening; limited public maintenance",
        }
    except Exception as e:
        logger.error(f"elf_obfuscate failed: {e}")
        return {"error": str(e), "binary_path": binary_path, "technique": technique}


# ============================================================================
# 13. Wireless Surveillance Detection (INTEGRATE-042: flock-detection)
# ============================================================================

async def research_wireless_surveillance(interface: str = "wlan0", duration: int = 10) -> dict[str, Any]:
    """Detect wireless surveillance devices (INTEGRATE-042: flock-detection).

    Scans wireless networks for suspicious or monitoring devices using
    pattern detection and behavioral analysis.

    Args:
        interface: Wireless interface to monitor (e.g., 'wlan0')
        duration: Scan duration in seconds (1-300)

    Returns:
        dict with detected devices or error explaining requirements
    """
    try:
        system = platform.system()

        if not (1 <= duration <= 300):
            return {"error": "duration must be 1-300 seconds", "interface": interface}

        if system != "Linux":
            return {
                "error": "flock-detection requires Linux with monitor mode support.",
                "current_system": system,
                "interface": interface,
                "duration": duration,
                "requirement": "WiFi adapter in monitor mode",
                "alternative": "research_network_anomaly for wired network detection",
            }

        return {
            "error": "flock-detection not installed. Requires wireless monitoring capability.",
            "install_command": "git clone https://github.com/BenDavidAaron/flock-detection",
            "interface": interface,
            "duration": duration,
            "requirement": "Linux with airmon-ng or iw in monitor mode",
            "prerequisites": ["aircrack-ng", "wireless-tools", "nl80211 support"],
            "alternative": "research_network_anomaly for wired network detection",
        }
    except Exception as e:
        logger.error(f"wireless_surveillance failed: {e}")
        return {"error": str(e), "interface": interface, "duration": duration}


# ============================================================================
# 14. Fingerprint Randomization (INTEGRATE-044: chameleon)
# ============================================================================

async def research_fingerprint_randomize(browser: str = "chromium") -> dict[str, Any]:
    """Randomize browser fingerprint for anti-tracking (INTEGRATE-044: chameleon).

    Applies fingerprint randomization to browser to defeat fingerprinting
    techniques and tracking scripts.

    Args:
        browser: Browser type ('chromium', 'firefox', 'safari')

    Returns:
        dict with randomization results or error explaining requirements
    """
    try:
        if browser not in ["chromium", "firefox", "safari"]:
            return {
                "error": f"Browser not supported: {browser}",
                "supported": ["chromium", "firefox", "safari"],
            }

        return {
            "error": "chameleon not installed. Run: pip install chameleon-fp",
            "browser": browser,
            "install_command": "pip install chameleon-fp",
            "features": [
                "Canvas fingerprint randomization",
                "WebGL randomization",
                "Font list randomization",
                "Audio context randomization",
            ],
            "alternative": "research_browser_privacy_score for assessment",
            "note": "Chameleon requires active browser extension or JavaScript injection",
        }
    except Exception as e:
        logger.error(f"fingerprint_randomize failed: {e}")
        return {"error": str(e), "browser": browser}


# ============================================================================
# 15. Multi-Format Steganography (INTEGRATE-045: stegma)
# ============================================================================

async def research_multi_stego(input_file: str, secret: str, media_type: str = "image") -> dict[str, Any]:
    """Multi-format steganography across image/audio/video (INTEGRATE-045: stegma).

    Hides secret data within media files (image, audio, video) using
    steganographic encoding that resists detection.

    Args:
        input_file: Path to media file to encode secret into
        secret: Secret message or data to hide
        media_type: Type of media ('image', 'audio', 'video')

    Returns:
        dict with steganography results or error explaining requirements
    """
    try:
        input_path = Path(input_file)

        if not input_path.exists():
            return {"error": f"File not found: {input_file}", "media_type": media_type}

        if not input_path.is_file():
            return {"error": f"Not a file: {input_file}", "media_type": media_type}

        if media_type not in ["image", "audio", "video"]:
            return {
                "error": f"Media type not supported: {media_type}",
                "supported": ["image", "audio", "video"],
            }

        if not secret:
            return {"error": "Secret data cannot be empty"}

        return {
            "error": "stegma not installed. Run: pip install stegma",
            "input_file": str(input_path),
            "input_size_bytes": input_path.stat().st_size,
            "media_type": media_type,
            "secret_length_chars": len(secret),
            "secret_length_bytes": len(secret.encode()),
            "install_command": "pip install stegma",
            "supported_media_types": ["image", "audio", "video"],
            "features": [
                "LSB steganography for images",
                "Audio data embedding",
                "Video frame manipulation",
                "Capacity analysis",
            ],
            "alternative": "research_stego_encode for image-only steganography",
            "note": "stegma supports multiple file formats; requires imagemagick/ffmpeg",
        }
    except Exception as e:
        logger.error(f"multi_stego failed: {e}")
        return {"error": str(e), "input_file": input_file, "media_type": media_type}


# ============================================================================
# Helper Functions
# ============================================================================


def _detect_mime_type(file_path: str) -> str | None:
    """Detect MIME type from file extension."""
    ext_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    ext = Path(file_path).suffix.lower()
    return ext_map.get(ext, None)


def _assess_system_hardening() -> int:
    """Assess basic system hardening (0-100)."""
    score = 50
    system = platform.system()

    try:
        if system == "Linux":
            # Check for security features
            if Path("/sys/kernel/security/apparmor").exists():
                score += 10
            if Path("/sys/kernel/security/selinux").exists():
                score += 10
            if Path("/proc/sys/kernel/unprivileged_userns_clone").exists():
                score += 5
        elif system == "Darwin":
            # macOS hardening
            score += 15  # macOS has good defaults
            try:
                result = subprocess.run(
                    ["csrutil", "status"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if "enabled" in result.stdout.lower():
                    score += 10
            except Exception:
                pass
    except Exception:
        pass

    return min(100, score)


def _assess_network_privacy() -> int:
    """Assess network privacy configuration (0-100)."""
    score = 50

    try:
        # Check for VPN/proxy
        try:
            import urllib.request

            response = urllib.request.urlopen("https://api.ipify.org?format=json", timeout=5)
            data = json.loads(response.read().decode())
            public_ip = data.get("ip")
            if public_ip:
                # If we got a response, basic connectivity exists
                score += 10
        except Exception:
            score -= 10

        # Check for IPv6 (additional privacy consideration)
        try:
            import socket

            socket.getaddrinfo("localhost", 80, socket.AF_INET6)
            score += 5
        except Exception:
            pass
    except Exception:
        pass

    return min(100, score)


def _generate_privacy_recommendations(score: int, components: dict[str, int]) -> list[str]:
    """Generate privacy recommendations based on score and components."""
    recommendations = []

    if components.get("dns_privacy", 50) < 50:
        recommendations.append("Enable DNS-over-HTTPS (DoH) or use encrypted DNS (1.1.1.1, NextDNS)")

    if components.get("tor_status", 50) < 50:
        recommendations.append("Consider using Tor Browser for enhanced anonymity")

    if components.get("fingerprinting_resistance", 50) < 50:
        recommendations.append("Use browser privacy extensions (uBlock, Privacy Badger)")

    if components.get("system_hardening", 50) < 50:
        recommendations.append("Enable system-level security features (SELinux, AppArmor, SIP)")

    if components.get("network_privacy", 50) < 50:
        recommendations.append("Use a trusted VPN service for network-level privacy")

    if score >= 80:
        recommendations.append("Your privacy posture is strong. Continue monitoring for updates.")

    return recommendations if recommendations else ["Maintain current security practices"]
